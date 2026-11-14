"""End-to-end schedule tests: real HA core, simulated T6, clock moved forward."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import ServiceValidationError

from custom_components.honeywell_t6.const import DOMAIN
from custom_components.honeywell_t6.schedule_logic import default_schedule

from .test_integration import (  # noqa: F401 - fixtures
    SRC,
    auto_enable_custom_integrations,
    call,
    setup,
    wrapper_id,
)

TZ = ZoneInfo("America/Detroit")


@pytest.fixture
async def noon(hass, freezer):
    """Friday 2026-11-13 12:00 in Detroit."""
    await hass.config.async_set_time_zone("America/Detroit")
    freezer.move_to(datetime(2026, 11, 13, 12, 0, tzinfo=TZ))
    return freezer


async def t6(hass, service, **data):
    wid = wrapper_id(hass)
    await hass.services.async_call(DOMAIN, service, {ATTR_ENTITY_ID: wid, **data}, blocking=True)
    await hass.async_block_till_done()


async def advance(hass, freezer, to: datetime):
    freezer.move_to(to)
    async_fire_time_changed(hass, to)
    await hass.async_block_till_done()


def band(hass):
    a = hass.states.get(wrapper_id(hass)).attributes
    return a["target_temp_low"], a["target_temp_high"]


async def test_schedule_drives_band_through_the_day(hass, noon, setup):
    wid = wrapper_id(hass)
    await call(hass, "set_hvac_mode", entity_id=wid, hvac_mode="heat")
    await t6(hass, "set_schedule_enabled", enabled=True)

    a = hass.states.get(wid).attributes
    assert band(hass) == (62, 65)                      # Away
    assert a["schedule_period"] == "Away"
    assert a["schedule_status"] == "Away until 17:00, then Home 67–70°"
    assert a["schedule_next"]["name"] == "Home"
    assert setup.fake.target_temperature == 62         # room 66 is above the band: resting at low

    await advance(hass, noon, datetime(2026, 11, 13, 17, 0, 1, tzinfo=TZ))
    assert band(hass) == (67, 70)                      # Home
    assert hass.states.get(wid).attributes["schedule_period"] == "Home"
    # room 66 <= new low 67 -> heating, driven to high + 1
    assert hass.states.get(wid).attributes["phase"] == "running"
    assert setup.fake.target_temperature == 71

    await advance(hass, noon, datetime(2026, 11, 13, 22, 0, 1, tzinfo=TZ))
    assert band(hass) == (62, 65)                      # Sleep
    await advance(hass, noon, datetime(2026, 11, 14, 6, 0, 1, tzinfo=TZ))
    assert band(hass) == (67, 70)                      # Saturday Wake


async def test_manual_change_holds_until_next_period(hass, noon, setup):
    wid = wrapper_id(hass)
    await call(hass, "set_hvac_mode", entity_id=wid, hvac_mode="heat")
    await t6(hass, "set_schedule_enabled", enabled=True)
    await t6(hass, "set_band", low=66, high=69)        # e.g. dragged on the card
    a = hass.states.get(wid).attributes
    assert band(hass) == (66, 69)
    assert a["hold"] == "next"
    assert a["schedule_status"] == "Hold until 17:00, then Home 67–70°"

    await advance(hass, noon, datetime(2026, 11, 13, 14, 0, tzinfo=TZ))
    assert band(hass) == (66, 69)                      # still held
    await advance(hass, noon, datetime(2026, 11, 13, 17, 0, 1, tzinfo=TZ))
    assert band(hass) == (67, 70)                      # hold ended, schedule resumed
    assert hass.states.get(wid).attributes["hold"] is None


async def test_permanent_hold_and_resume(hass, noon, setup):
    wid = wrapper_id(hass)
    await call(hass, "set_hvac_mode", entity_id=wid, hvac_mode="heat")
    await t6(hass, "set_schedule_enabled", enabled=True)
    await t6(hass, "set_hold", type="permanent")
    await t6(hass, "set_band", low=64, high=66)
    await advance(hass, noon, datetime(2026, 11, 14, 9, 0, tzinfo=TZ))
    assert band(hass) == (64, 66)
    assert hass.states.get(wid).attributes["hold"] == "permanent"
    await t6(hass, "resume_schedule")
    assert band(hass) == (62, 65)                      # Saturday 9:00 = Away
    assert hass.states.get(wid).attributes["hold"] is None


async def test_cool_mode_uses_cool_bands(hass, noon, setup):
    setup.fake.set_room(80)
    wid = wrapper_id(hass)
    await t6(hass, "set_schedule_enabled", enabled=True)
    await call(hass, "set_hvac_mode", entity_id=wid, hvac_mode="cool")
    assert band(hass) == (78, 81)                      # cool Away
    assert setup.fake.hvac_mode == "cool"
    await call(hass, "set_hvac_mode", entity_id=wid, hvac_mode="heat")
    assert band(hass) == (62, 65)


async def test_set_schedule_service_and_validation(hass, noon, setup):
    wid = wrapper_id(hass)
    await call(hass, "set_hvac_mode", entity_id=wid, hvac_mode="heat")
    sch = default_schedule()
    sch["layout"] = "weekday_weekend"
    sch["days"]["mon"]["heat"] = [
        {"name": "Day", "start": "07:00", "low": 68, "high": 70},
        {"name": "Night", "start": "21:00", "low": 63, "high": 65},
    ]
    await t6(hass, "set_schedule", layout=sch["layout"], days=sch["days"])
    await t6(hass, "set_schedule_enabled", enabled=True)
    a = hass.states.get(wid).attributes
    assert a["schedule"]["days"]["fri"]["heat"][0]["name"] == "Day"   # copied across Mon-Fri
    assert a["schedule"]["days"]["sat"]["heat"][0]["name"] == "Wake"
    assert band(hass) == (68, 70)

    bad = default_schedule()
    bad["days"]["tue"]["heat"][0]["high"] = bad["days"]["tue"]["heat"][0]["low"]
    with pytest.raises(ServiceValidationError):
        await t6(hass, "set_schedule", layout="same", days=bad["days"])


async def test_switch_and_persistence(hass, noon, setup):
    sw = next(s.entity_id for s in hass.states.async_all("switch"))
    assert hass.states.get(sw).state == "off"
    await hass.services.async_call("switch", "turn_on", {ATTR_ENTITY_ID: sw}, blocking=True)
    await hass.async_block_till_done()
    wid = wrapper_id(hass)
    assert hass.states.get(wid).attributes["schedule_enabled"] is True
    assert hass.states.get(wid).attributes["schedule_period"] == "Away"

    # flush the delayed save, reload, and the schedule is still on
    await advance(hass, noon, datetime(2026, 11, 13, 12, 0, 10, tzinfo=TZ))
    assert await hass.config_entries.async_reload(setup.entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(sw).state == "on"
    assert hass.states.get(wrapper_id(hass)).attributes["schedule_period"] == "Away"

    await hass.services.async_call("switch", "turn_off", {ATTR_ENTITY_ID: sw}, blocking=True)
    await hass.async_block_till_done()
    a = hass.states.get(wrapper_id(hass)).attributes
    assert a["schedule_status"] == "Schedule off" and a["schedule_period"] is None


async def test_schedule_off_band_is_untouched(hass, noon, setup):
    wid = wrapper_id(hass)
    await call(hass, "set_temperature", entity_id=wid, target_temp_low=66, target_temp_high=68)
    await advance(hass, noon, datetime(2026, 11, 13, 17, 30, tzinfo=TZ))
    assert band(hass) == (66, 68)
    assert hass.states.get(wid).attributes["hold"] is None
