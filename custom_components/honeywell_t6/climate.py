"""Hysteresis climate entity that drives a Honeywell T6 Pro Z-Wave thermostat."""
from __future__ import annotations

from datetime import timedelta
import logging
import time
from typing import Any

import voluptuous as vol

from homeassistant.components.climate import (
    ATTR_CURRENT_HUMIDITY,
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_FAN_MODES,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TARGET_TEMP_STEP,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_platform, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from . import T6ConfigEntry
from .const import (
    ATTR_CYCLES,
    ATTR_DEVICE_MODE,
    ATTR_DEVICE_SETPOINT,
    ATTR_OVERRIDE,
    ATTR_PARAM_ENTITIES,
    ATTR_PHASE,
    ATTR_STATUS,
    ATTR_STRATEGY,
    COMMAND_HOLDOFF,
    CONF_DRIVE_OFFSET,
    CONF_FOLLOW_WALL,
    CONF_INITIAL_PHASE,
    CONF_MIN_GAP,
    CONF_SOURCE,
    CONF_STRATEGY,
    CONF_TEMP_SENSOR,
    DEFAULT_BAND_HEAT,
    RECONCILE_INTERVAL,
    SERVICE_FORCE_PHASE,
    SERVICE_REFRESH_PARAMS,
    SERVICE_SET_BAND,
    SIGNAL_STATE,
    WALL_CHANGE_GRACE,
)
from .entity_param import attach_to_device
from .hysteresis import DeviceCommand, HysteresisController, InitialPhase, Mode, Phase, Strategy

_LOGGER = logging.getLogger(__name__)

_ACTION_MAP = {a.value: a for a in HVACAction}


async def async_setup_entry(
    hass: HomeAssistant, entry: T6ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([T6HysteresisClimate(hass, entry)])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_BAND,
        {
            vol.Required("low"): vol.Coerce(float),
            vol.Required("high"): vol.Coerce(float),
        },
        "async_set_band",
    )
    platform.async_register_entity_service(
        SERVICE_FORCE_PHASE,
        {vol.Required("phase"): vol.In(["running", "resting"])},
        "async_force_phase",
    )
    platform.async_register_entity_service(SERVICE_REFRESH_PARAMS, {}, "async_refresh_parameters")


class T6HysteresisClimate(ClimateEntity, RestoreEntity):
    """Two set-point (band) thermostat with heat/cool hysteresis."""

    _attr_has_entity_name = True
    _attr_translation_key = "hysteresis"
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    _attr_should_poll = False
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, hass: HomeAssistant, entry: T6ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._source: str = entry.data[CONF_SOURCE]
        opts = entry.options
        self._sensor: str | None = opts.get(CONF_TEMP_SENSOR) or None
        self._follow_wall: bool = opts.get(CONF_FOLLOW_WALL, True)
        celsius = hass.config.units.temperature_unit == UnitOfTemperature.CELSIUS
        low, high = DEFAULT_BAND_HEAT[1 if celsius else 0]
        self._ctl = HysteresisController(
            low=low,
            high=high,
            strategy=Strategy(opts.get(CONF_STRATEGY, "setpoint")),
            drive_offset=float(opts.get(CONF_DRIVE_OFFSET, 0.5 if celsius else 1.0)),
            initial_phase=InitialPhase(opts.get(CONF_INITIAL_PHASE, "resting")),
            min_gap=float(opts.get(CONF_MIN_GAP, 0.5 if celsius else 1.0)),
            step=0.5 if celsius else 1.0,
        )
        self._last_on_mode = Mode.HEAT
        self._override: str | None = None  # device put in a mode we don't drive
        self._last_cmd: DeviceCommand | None = None
        self._last_cmd_time = 0.0
        self._applying = False
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_temperature_unit = hass.config.units.temperature_unit
        self._attr_target_temperature_step = self._ctl.step
        # Live on the Z-Wave T6's device page (fallback: own device).
        attach_to_device(self, hass, entry)
        self._attr_fan_modes = None
        self._attr_fan_mode = None
        self._attr_current_humidity = None
        self._attr_current_temperature = None
        self._sync_from_source()

    # ------------------------------------------------------------ lifecycle
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self._restore(last)

        tracked = [self._source] + ([self._sensor] if self._sensor else [])
        self.async_on_remove(
            async_track_state_change_event(self.hass, tracked, self._async_on_source_change)
        )
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_reconcile, timedelta(seconds=RECONCILE_INTERVAL)
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_STATE.format(self._entry.entry_id) + "_ready", self._publish
            )
        )

        @callback
        def _registry_filter(data: Any) -> bool:
            ent = er.async_get(self.hass).async_get(data["entity_id"])
            return ent is not None and ent.config_entry_id == self._entry.entry_id

        @callback
        def _registry_changed(_event: Event) -> None:
            self._publish()

        self.async_on_remove(
            self.hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED, _registry_changed, event_filter=_registry_filter
            )
        )
        self._sync_from_source()
        await self._async_control()

    def _restore(self, last: State) -> None:
        a = last.attributes
        try:
            if a.get(ATTR_TARGET_TEMP_LOW) is not None and a.get(ATTR_TARGET_TEMP_HIGH) is not None:
                self._ctl.set_band(float(a[ATTR_TARGET_TEMP_LOW]), float(a[ATTR_TARGET_TEMP_HIGH]))
        except (TypeError, ValueError):
            pass
        if last.state in (Mode.HEAT, Mode.COOL, Mode.OFF):
            self._ctl.mode = Mode(last.state)
            if self._ctl.mode != Mode.OFF:
                self._last_on_mode = self._ctl.mode
        phase = a.get(ATTR_PHASE)
        if phase in (Phase.RUNNING, Phase.RESTING) and self._ctl.mode != Mode.OFF:
            self._ctl.phase = Phase(phase)
        self._ctl.cycles = int(a.get(ATTR_CYCLES) or 0)
        self._override = a.get(ATTR_OVERRIDE)

    # --------------------------------------------------------- source state
    def _source_state(self) -> State | None:
        st = self.hass.states.get(self._source)
        if st is None or st.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        return st

    def _temperature(self) -> float | None:
        if self._sensor:
            st = self.hass.states.get(self._sensor)
            if st is not None:
                try:
                    return float(st.state)
                except ValueError:
                    pass
        st = self._source_state()
        if st is None:
            return None
        t = st.attributes.get(ATTR_CURRENT_TEMPERATURE)
        return float(t) if t is not None else None

    @callback
    def _update_features(self) -> None:
        feats = (
            ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        st = self.hass.states.get(self._source)
        if st is not None and st.attributes.get(ATTR_FAN_MODES):
            feats |= ClimateEntityFeature.FAN_MODE
        self._attr_supported_features = feats

    @callback
    def _sync_from_source(self) -> None:
        st = self.hass.states.get(self._source)
        self._update_features()
        self._attr_available = st is not None and st.state != STATE_UNAVAILABLE
        if st is None:
            return
        a = st.attributes
        self._attr_current_temperature = self._temperature()
        self._attr_current_humidity = a.get(ATTR_CURRENT_HUMIDITY)
        self._attr_fan_modes = a.get(ATTR_FAN_MODES)
        self._attr_fan_mode = a.get(ATTR_FAN_MODE)
        if a.get(ATTR_MIN_TEMP) is not None:
            self._attr_min_temp = float(a[ATTR_MIN_TEMP])
            self._ctl.device_min = self._attr_min_temp
        if a.get(ATTR_MAX_TEMP) is not None:
            self._attr_max_temp = float(a[ATTR_MAX_TEMP])
            self._ctl.device_max = self._attr_max_temp
        if a.get(ATTR_TARGET_TEMP_STEP):
            self._ctl.step = max(float(a[ATTR_TARGET_TEMP_STEP]), self._ctl.step)
            self._attr_target_temperature_step = self._ctl.step

    @callback
    def _detect_wall_change(self, st: State) -> bool:
        """Adopt a mode change made on the thermostat itself. Returns True if adopted."""
        if not self._follow_wall or self._applying:
            return False
        if time.monotonic() - self._last_cmd_time < WALL_CHANGE_GRACE:
            return False
        dev_mode = st.state
        expected = self._last_cmd.hvac_mode if self._last_cmd else None
        if expected is None or dev_mode == expected:
            return False
        if dev_mode in (Mode.HEAT, Mode.COOL):
            _LOGGER.info("%s: mode changed on the thermostat to %s; following", self._source, dev_mode)
            self._override = None
            self._ctl.set_mode(Mode(dev_mode), self._temperature())
            self._last_on_mode = Mode(dev_mode)
            return True
        if dev_mode == Mode.OFF and not (
            self._ctl.strategy == Strategy.MODE and self._ctl.phase == Phase.RESTING
        ):
            _LOGGER.info("%s: thermostat turned off at the wall; following", self._source)
            self._override = None
            self._ctl.set_mode(Mode.OFF, None)
            return True
        if dev_mode not in (Mode.OFF,):
            # auto / emergency heat / etc. – hand control to the thermostat.
            _LOGGER.info("%s: thermostat set to %s at the wall; suspending", self._source, dev_mode)
            self._override = dev_mode
            return True
        return False

    async def _async_on_source_change(self, event: Event[EventStateChangedData]) -> None:
        self._sync_from_source()
        new = event.data["new_state"]
        if (
            new is not None
            and event.data["entity_id"] == self._source
            and new.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)
        ):
            self._detect_wall_change(new)
        await self._async_control()

    async def _async_reconcile(self, _now: Any = None) -> None:
        self._sync_from_source()
        await self._async_control()

    # ------------------------------------------------------------- control
    async def _async_control(self) -> None:
        if self._override is None:
            changed = self._ctl.evaluate(self._temperature())
            if changed:
                _LOGGER.debug("%s: phase -> %s at %s (band %s-%s)", self._source, self._ctl.phase, self._temperature(), self._ctl.low, self._ctl.high)
            await self._async_apply(self._ctl.command())
        self._publish()

    async def _async_apply(self, cmd: DeviceCommand) -> None:
        st = self._source_state()
        if st is None:
            return
        cur_mode = st.state
        cur_sp = st.attributes.get(ATTR_TEMPERATURE)
        need_mode = cur_mode != cmd.hvac_mode
        need_sp = cmd.setpoint is not None and (
            cur_sp is None or abs(float(cur_sp) - cmd.setpoint) > 0.01
        )
        if not (need_mode or need_sp):
            self._last_cmd = cmd
            return
        recently = time.monotonic() - self._last_cmd_time < COMMAND_HOLDOFF
        if cmd == self._last_cmd and recently:
            return  # identical command in flight; wait for the Z-Wave report
        self._applying = True
        try:
            if need_mode:
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_SET_HVAC_MODE,
                    {ATTR_ENTITY_ID: self._source, ATTR_HVAC_MODE: cmd.hvac_mode},
                    blocking=True,
                )
            if cmd.setpoint is not None and (need_sp or need_mode):
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_SET_TEMPERATURE,
                    {ATTR_ENTITY_ID: self._source, ATTR_TEMPERATURE: cmd.setpoint},
                    blocking=True,
                )
            _LOGGER.debug("%s: commanded %s", self._source, cmd)
        except (HomeAssistantError, vol.Invalid) as err:
            _LOGGER.warning("%s: could not command thermostat (%s); will retry", self._source, err)
        finally:
            self._applying = False
            self._last_cmd = cmd
            self._last_cmd_time = time.monotonic()

    @callback
    def _publish(self) -> None:
        async_dispatcher_send(
            self.hass,
            SIGNAL_STATE.format(self._entry.entry_id),
            self._phase_value(),
            self._status(),
            self._ctl.cycles,
        )
        if self.hass and self.entity_id:
            self.async_write_ha_state()

    def _phase_value(self) -> str:
        return "override" if self._override else str(self._ctl.phase)

    def _status(self) -> str:
        if self._override:
            return f"Thermostat is in {self._override} mode (set at the wall)"
        return self._ctl.describe()

    # ------------------------------------------------------------ properties
    @property
    def hvac_mode(self) -> HVACMode:
        return HVACMode(self._ctl.mode.value)

    @property
    def target_temperature_low(self) -> float:
        return self._ctl.low

    @property
    def target_temperature_high(self) -> float:
        return self._ctl.high

    @property
    def hvac_action(self) -> HVACAction | None:
        st = self.hass.states.get(self._source)
        if st is not None and (action := st.attributes.get(ATTR_HVAC_ACTION)) in _ACTION_MAP:
            return _ACTION_MAP[action]
        if self._ctl.mode == Mode.OFF:
            return HVACAction.OFF
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        st = self.hass.states.get(self._source)
        return {
            ATTR_PHASE: self._phase_value(),
            ATTR_STATUS: self._status(),
            ATTR_STRATEGY: str(self._ctl.strategy),
            ATTR_CYCLES: self._ctl.cycles,
            ATTR_OVERRIDE: self._override,
            ATTR_DEVICE_MODE: st.state if st else None,
            ATTR_DEVICE_SETPOINT: st.attributes.get(ATTR_TEMPERATURE) if st else None,
            "source_entity_id": self._source,
            "temperature_sensor": self._sensor,
            ATTR_PARAM_ENTITIES: self._param_entities(),
        }

    def _param_entities(self) -> list[str]:
        reg = er.async_get(self.hass)
        ents = [
            e
            for e in er.async_entries_for_config_entry(reg, self._entry.entry_id)
            if e.domain in ("select", "number") and e.disabled_by is None
        ]

        def _num(e: er.RegistryEntry) -> int:
            try:
                return int(e.unique_id.rsplit("_param_", 1)[1])
            except (IndexError, ValueError):
                return 999

        return [e.entity_id for e in sorted(ents, key=_num)]

    # -------------------------------------------------------------- actions
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        mode = Mode(hvac_mode.value if isinstance(hvac_mode, HVACMode) else hvac_mode)
        self._override = None
        self._ctl.set_mode(mode, self._temperature())
        if mode != Mode.OFF:
            self._last_on_mode = mode
        await self._async_control()

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode(self._last_on_mode.value))

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        low = kwargs.get(ATTR_TARGET_TEMP_LOW)
        high = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        if low is None or high is None:
            raise ServiceValidationError(
                "This thermostat uses a band: provide target_temp_low and target_temp_high"
            )
        if (mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            self._ctl.set_band(float(low), float(high))
            await self.async_set_hvac_mode(HVACMode(mode))
            return
        await self.async_set_band(float(low), float(high))

    async def async_set_band(self, low: float, high: float) -> None:
        self._ctl.set_band(low, high)
        # A band change can put the temperature outside the band – re-enter.
        t = self._temperature()
        if t is not None and self._ctl.mode != Mode.OFF and self._override is None:
            if t <= self._ctl.low or t >= self._ctl.high:
                self._ctl.phase = self._ctl._entry_phase(t)  # noqa: SLF001
        await self._async_control()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_FAN_MODE,
            {ATTR_ENTITY_ID: self._source, ATTR_FAN_MODE: fan_mode},
            blocking=True,
        )

    async def async_force_phase(self, phase: str) -> None:
        if self._ctl.mode == Mode.OFF:
            raise ServiceValidationError("Set heat or cool mode first")
        self._override = None
        self._ctl.phase = Phase(phase)
        await self._async_control()

    async def async_refresh_parameters(self) -> None:
        await self._entry.runtime_data.bridge.async_refresh()
