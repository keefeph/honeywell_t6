"""Config and options flow for Honeywell T6 Hysteresis."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    CONF_DRIVE_OFFSET,
    CONF_FOLLOW_WALL,
    CONF_INITIAL_PHASE,
    CONF_MIN_GAP,
    CONF_SOURCE,
    CONF_STRATEGY,
    CONF_TEMP_SENSOR,
    DEFAULT_DRIVE_OFFSET,
    DEFAULT_FOLLOW_WALL,
    DEFAULT_INITIAL_PHASE,
    DEFAULT_MIN_GAP,
    DEFAULT_STRATEGY,
    DOMAIN,
)


def _celsius(hass: HomeAssistant) -> bool:
    return hass.config.units.temperature_unit == UnitOfTemperature.CELSIUS


def default_options(hass: HomeAssistant) -> dict[str, Any]:
    i = 1 if _celsius(hass) else 0
    return {
        CONF_STRATEGY: DEFAULT_STRATEGY,
        CONF_DRIVE_OFFSET: DEFAULT_DRIVE_OFFSET[i],
        CONF_MIN_GAP: DEFAULT_MIN_GAP[i],
        CONF_INITIAL_PHASE: DEFAULT_INITIAL_PHASE,
        CONF_FOLLOW_WALL: DEFAULT_FOLLOW_WALL,
    }


def _options_schema(hass: HomeAssistant, current: dict[str, Any]) -> vol.Schema:
    unit = hass.config.units.temperature_unit
    step = 0.5 if _celsius(hass) else 1.0
    opts = {**default_options(hass), **current}
    sensor_key = (
        vol.Optional(CONF_TEMP_SENSOR, description={"suggested_value": opts.get(CONF_TEMP_SENSOR)})
    )
    return vol.Schema(
        {
            vol.Required(CONF_STRATEGY, default=opts[CONF_STRATEGY]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["setpoint", "mode"],
                    translation_key=CONF_STRATEGY,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required(CONF_DRIVE_OFFSET, default=opts[CONF_DRIVE_OFFSET]): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=5, step=step, unit_of_measurement=unit,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_MIN_GAP, default=opts[CONF_MIN_GAP]): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=step, max=10, step=step, unit_of_measurement=unit,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_INITIAL_PHASE, default=opts[CONF_INITIAL_PHASE]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["resting", "running"],
                    translation_key=CONF_INITIAL_PHASE,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required(CONF_FOLLOW_WALL, default=opts[CONF_FOLLOW_WALL]): selector.BooleanSelector(),
            sensor_key: selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            ),
        }
    )


class T6ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Pick the Z-Wave JS climate entity of the T6."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            source = user_input[CONF_SOURCE]
            await self.async_set_unique_id(source)
            self._abort_if_unique_id_configured()
            if self.hass.states.get(source) is None:
                errors[CONF_SOURCE] = "entity_not_found"
            else:
                name = user_input.get(CONF_NAME) or "T6 Hysteresis"
                return self.async_create_entry(
                    title=name,
                    data={CONF_SOURCE: source, CONF_NAME: name},
                    options=default_options(self.hass),
                )
        schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="climate", integration="zwave_js")
                ),
                vol.Optional(CONF_NAME, default="T6 Hysteresis"): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return T6OptionsFlow()


class T6OptionsFlow(OptionsFlow):
    """Tune the hysteresis behaviour."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(self.hass, dict(self.config_entry.options)),
        )
