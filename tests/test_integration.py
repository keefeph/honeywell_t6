"""End-to-end tests against a real Home Assistant core with a simulated T6."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    setup_test_component_platform,
)

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_ENTITY_ID, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.honeywell_t6.const import DOMAIN

SRC = "climate.fake_t6"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


class FakeT6(ClimateEntity):
    """Simulated T6 as Z-Wave JS would expose it."""

    _attr_name = "Fake T6"
    _attr_unique_id = "fake_t6"
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL]
    _attr_fan_modes = ["Auto low", "Low", "Circulation"]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_min_temp = 40
    _attr_max_temp = 99
    _attr_target_temperature_step = 1

    def __init__(self) -> None:
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 68
        self._attr_current_temperature = 66
        self._attr_fan_mode = "Auto low"
        self.calls: list[tuple] = []

    @property
    def hvac_action(self):
        t, sp = self._attr_current_temperature, self._attr_target_temperature
        if self._attr_hvac_mode == HVACMode.HEAT:
            return HVACAction.HEATING if t < sp else HVACAction.IDLE
        if self._attr_hvac_mode == HVACMode.COOL:
            return HVACAction.COOLING if t > sp else HVACAction.IDLE
        return HVACAction.OFF

    async def async_set_hvac_mode(self, hvac_mode):
        self.calls.append(("mode", hvac_mode))
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        self.calls.append(("sp", kwargs["temperature"]))
        self._attr_target_temperature = kwargs["temperature"]
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        self._attr_fan_mode = fan_mode
        self.async_write_ha_state()

    def set_room(self, t):
        self._attr_current_temperature = t
        self.async_write_ha_state()


class FakeValue:
    def __init__(self, num, val, states=None):
        self.command_class = 112
        self.property_ = num
        self.value = val
        self.metadata = SimpleNamespace(
            states=states, min=None, max=None, default=None, unit=None,
            label=None, description=None, allow_manual_entry=None,
        )


class FakeNode:
    node_id = 7
    status = "alive"

    def __init__(self):
        self.values = {f"7-112-0-{n}": FakeValue(n, 0) for n in range(1, 43)}
        self.values["7-112-0-20"].value = 3
        self.values["7-112-0-4"].value = 2
        self._cbs = {}

    def on(self, event, cb):
        self._cbs.setdefault(event, []).append(cb)
        return lambda: self._cbs[event].remove(cb)

    def report(self, num, val):
        v = self.values[f"7-112-0-{num}"]
        v.value = val
        for cb in self._cbs.get("value updated", []):
            cb({"value": v})


@pytest.fixture
async def setup(hass: HomeAssistant, request):
    link = getattr(request, "param", False)
    hass.config.units = __import__(
        "homeassistant.util.unit_system", fromlist=["US_CUSTOMARY_SYSTEM"]
    ).US_CUSTOMARY_SYSTEM
    for comp in ("http", "frontend", "zwave_js"):
        hass.config.components.add(comp)
    fake = FakeT6()
    setup_test_component_platform(hass, "climate", [fake])
    assert await async_setup_component(hass, "climate", {"climate": {"platform": "test"}})
    await hass.async_block_till_done()

    zdev = None
    if link:  # make the fake T6 belong to a Z-Wave JS device, like the real one
        from homeassistant.helpers import device_registry as dr, entity_registry as er
        zw = MockConfigEntry(domain="zwave_js")
        zw.add_to_hass(hass)
        zdev = dr.async_get(hass).async_get_or_create(
            config_entry_id=zw.entry_id, identifiers={("zwave_js", "123-7")},
            name="Dining Room Thermostat", manufacturer="Honeywell",
        )
        er.async_get(hass).async_update_entity(SRC, device_id=zdev.id)

    node = FakeNode()
    set_param = AsyncMock(side_effect=lambda n, v, p: node.report(p, v))
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"source_entity_id": SRC, "name": "T6"},
        options={
            "strategy": "setpoint", "drive_offset": 1.0, "min_gap": 1.0,
            "initial_phase": "resting", "follow_wall_changes": True,
        },
        unique_id=SRC,
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "homeassistant.components.zwave_js.helpers.async_get_node_from_entity_id",
            return_value=node,
        ),
        patch("zwave_js_server.util.node.async_set_config_parameter", set_param),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        yield SimpleNamespace(fake=fake, node=node, entry=entry, set_param=set_param, zdev=zdev)


def wrapper_id(hass):
    ids = [s.entity_id for s in hass.states.async_all("climate") if s.entity_id != SRC]
    assert len(ids) == 1, ids
    return ids[0]


async def call(hass, service, **data):
    await hass.services.async_call("climate", service, data, blocking=True)
    await hass.async_block_till_done()


async def test_heating_hysteresis_drives_device(hass, setup):
    fake = setup.fake
    wid = wrapper_id(hass)
    await call(hass, "set_temperature", entity_id=wid, target_temp_low=67, target_temp_high=71)
    await call(hass, "set_hvac_mode", entity_id=wid, hvac_mode="heat")

    st = hass.states.get(wid)
    assert st.state == "heat"
    assert st.attributes["phase"] == "running"          # 66 <= low
    assert fake.hvac_mode == HVACMode.HEAT
    assert fake.target_temperature == 72                # high + drive offset
    assert hass.states.get(SRC).attributes["hvac_action"] == "heating"

    for t in (68, 69, 70):
        fake.set_room(t)
        await hass.async_block_till_done()
        assert hass.states.get(wid).attributes["phase"] == "running"

    fake.set_room(71)                                   # high reached
    await hass.async_block_till_done()
    assert hass.states.get(wid).attributes["phase"] == "resting"
    assert fake.target_temperature == 67
    assert hass.states.get(SRC).attributes["hvac_action"] == "idle"

    for t in (70, 69, 68):                        # coasts down, no heat
        fake.set_room(t)
        await hass.async_block_till_done()
        assert hass.states.get(SRC).attributes["hvac_action"] == "idle"
        assert hass.states.get(wid).attributes["phase"] == "resting"

    fake.set_room(67)                                   # low reached
    await hass.async_block_till_done()
    assert hass.states.get(wid).attributes["phase"] == "running"
    assert fake.target_temperature == 72
    assert hass.states.get(wid).attributes["cycles"] == 1
    phase_sensor = [s for s in hass.states.async_all("sensor") if s.entity_id.endswith("phase")]
    assert phase_sensor and phase_sensor[0].state == "running"


async def test_cooling_hysteresis(hass, setup):
    fake = setup.fake
    fake.set_room(75)
    wid = wrapper_id(hass)
    await call(hass, "set_temperature", entity_id=wid, target_temp_low=72, target_temp_high=76,
               hvac_mode="cool")
    assert hass.states.get(wid).attributes["phase"] == "resting"   # inside band
    assert fake.hvac_mode == HVACMode.COOL and fake.target_temperature == 76

    fake.set_room(76)
    await hass.async_block_till_done()
    assert hass.states.get(wid).attributes["phase"] == "running"
    assert fake.target_temperature == 71                            # low - drive
    fake.set_room(73)
    await hass.async_block_till_done()
    assert hass.states.get(SRC).attributes["hvac_action"] == "cooling"
    fake.set_room(72)
    await hass.async_block_till_done()
    assert hass.states.get(wid).attributes["phase"] == "resting"
    assert fake.target_temperature == 76
    fake.set_room(74.5)
    await hass.async_block_till_done()
    assert hass.states.get(SRC).attributes["hvac_action"] == "idle"


async def test_off_and_fan_passthrough(hass, setup):
    fake = setup.fake
    wid = wrapper_id(hass)
    await call(hass, "set_hvac_mode", entity_id=wid, hvac_mode="heat")
    await call(hass, "set_hvac_mode", entity_id=wid, hvac_mode="off")
    assert fake.hvac_mode == HVACMode.OFF
    await call(hass, "set_fan_mode", entity_id=wid, fan_mode="Circulation")
    assert hass.states.get(wid).attributes["fan_mode"] == "Circulation"
    await call(hass, "turn_on", entity_id=wid)
    assert hass.states.get(wid).state == "heat"


async def test_band_service_and_single_temperature_rejected(hass, setup):
    wid = wrapper_id(hass)
    await hass.services.async_call(DOMAIN, "set_band", {ATTR_ENTITY_ID: wid, "low": 65, "high": 69},
                                   blocking=True)
    st = hass.states.get(wid)
    assert (st.attributes["target_temp_low"], st.attributes["target_temp_high"]) == (65, 69)
    with pytest.raises(Exception):
        await call(hass, "set_temperature", entity_id=wid, temperature=70)


async def test_all_parameters_exposed_and_writable(hass, setup):
    params = [
        s for s in hass.states.async_all(("select", "number"))
        if "parameter" in s.attributes
    ]
    enabled = {s.attributes["parameter"] for s in params}
    from homeassistant.helpers import entity_registry as er
    reg = er.async_get(hass)
    all_regs = [e for e in er.async_entries_for_config_entry(reg, setup.entry.entry_id)
                if e.domain in ("select", "number")]
    assert len(all_regs) == 42
    assert {4, 5, 6, 7}.isdisjoint(enabled)        # installer-risky ones start disabled
    assert len(enabled) == 42 - 8

    cyc = next(s for s in params if s.attributes["parameter"] == 20)
    assert cyc.state == "3.0"
    await hass.services.async_call(
        "number", "set_value", {ATTR_ENTITY_ID: cyc.entity_id, "value": 5}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(cyc.entity_id).state == "5.0"

    sched = next(s for s in params if s.attributes["parameter"] == 1)
    assert sched.state == "No schedule on thermostat"
    await hass.services.async_call(
        "select", "select_option",
        {ATTR_ENTITY_ID: sched.entity_id, "option": "5-2 schedule"}, blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(sched.entity_id).state == "5-2 schedule"
    setup.set_param.assert_awaited()

    # Device-side change shows up via the Z-Wave value-updated event
    setup.node.report(39, 4)
    await hass.async_block_till_done()
    bright = next(s for s in hass.states.async_all("number") if s.attributes.get("parameter") == 39)
    assert bright.state == "4.0"

    wid = wrapper_id(hass)
    assert len(hass.states.get(wid).attributes["parameter_entities"]) == 34


async def test_unload(hass, setup):
    assert await hass.config_entries.async_unload(setup.entry.entry_id)


async def test_wall_mode_change_is_followed(hass, setup, monkeypatch):
    import custom_components.honeywell_t6.climate as climate_mod
    monkeypatch.setattr(climate_mod, "WALL_CHANGE_GRACE", 0)
    fake = setup.fake
    wid = wrapper_id(hass)
    await call(hass, "set_hvac_mode", entity_id=wid, hvac_mode="heat")
    await call(hass, "set_hvac_mode", entity_id=SRC, hvac_mode="cool")   # someone at the wall
    assert hass.states.get(wid).state == "cool"
    await call(hass, "set_hvac_mode", entity_id=SRC, hvac_mode="heat_cool")
    st = hass.states.get(wid)
    assert st.attributes["phase"] == "override"
    assert fake.hvac_mode == HVACMode.HEAT_COOL       # we leave it alone
    await call(hass, "set_hvac_mode", entity_id=wid, hvac_mode="heat")
    assert hass.states.get(wid).attributes["override"] is None
    assert fake.hvac_mode == HVACMode.HEAT


async def test_mode_strategy_turns_device_off_while_resting(hass, setup):
    hass.config_entries.async_update_entry(
        setup.entry, options={**setup.entry.options, "strategy": "mode"}
    )
    await hass.async_block_till_done()   # reload
    fake = setup.fake
    wid = wrapper_id(hass)
    await call(hass, "set_temperature", entity_id=wid, target_temp_low=67, target_temp_high=71,
               hvac_mode="heat")
    assert fake.hvac_mode == HVACMode.HEAT and fake.target_temperature == 72
    fake.set_room(71)
    await hass.async_block_till_done()
    assert fake.hvac_mode == HVACMode.OFF
    fake.set_room(67)
    await hass.async_block_till_done()
    assert fake.hvac_mode == HVACMode.HEAT and fake.target_temperature == 72


async def test_config_flow(hass, setup):
    from custom_components.honeywell_t6.const import DOMAIN as D
    result = await hass.config_entries.flow.async_init(D, context={"source": "user"})
    assert result["type"] == "form"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"source_entity_id": SRC, "name": "Again"}
    )
    assert result["type"] == "abort" and result["reason"] == "already_configured"
    result = await hass.config_entries.options.async_init(setup.entry.entry_id)
    assert result["type"] == "form"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"strategy": "setpoint", "drive_offset": 2, "min_gap": 2,
         "initial_phase": "running", "follow_wall_changes": False},
    )
    assert result["type"] == "create_entry"


async def test_climate_on_same_device_as_parameters(hass, setup):
    from homeassistant.helpers import entity_registry as er
    reg = er.async_get(hass)
    ents = er.async_entries_for_config_entry(reg, setup.entry.entry_id)
    devices = {e.device_id for e in ents}
    assert len(devices) == 1 and None not in devices


@pytest.mark.parametrize("setup", [True], indirect=True)
async def test_entities_join_zwave_device(hass, setup):
    from homeassistant.helpers import device_registry as dr, entity_registry as er
    reg = er.async_get(hass)
    ents = er.async_entries_for_config_entry(reg, setup.entry.entry_id)
    assert ents and {e.device_id for e in ents} == {setup.zdev.id}
    assert not [d for d in dr.async_entries_for_config_entry(dr.async_get(hass), setup.entry.entry_id)
                if (DOMAIN, setup.entry.entry_id) in d.identifiers]
    # control still works
    wid = wrapper_id(hass)
    await call(hass, "set_hvac_mode", entity_id=wid, hvac_mode="heat")
    assert setup.fake.hvac_mode == HVACMode.HEAT


async def test_upgrade_moves_entities_and_removes_old_device(hass, setup):
    from homeassistant.helpers import device_registry as dr, entity_registry as er
    dev_reg, ent_reg = dr.async_get(hass), er.async_get(hass)
    old = next(d for d in dr.async_entries_for_config_entry(dev_reg, setup.entry.entry_id)
               if (DOMAIN, setup.entry.entry_id) in d.identifiers)
    assert old is not None  # v1.0.1 situation: stand-alone device
    zw = MockConfigEntry(domain="zwave_js")
    zw.add_to_hass(hass)
    zdev = dev_reg.async_get_or_create(config_entry_id=zw.entry_id, identifiers={("zwave_js", "1-7")})
    ent_reg.async_update_entity(SRC, device_id=zdev.id)
    assert await hass.config_entries.async_reload(setup.entry.entry_id)
    await hass.async_block_till_done()
    ents = er.async_entries_for_config_entry(ent_reg, setup.entry.entry_id)
    assert {e.device_id for e in ents} == {zdev.id}
    assert dev_reg.async_get(old.id) is None
