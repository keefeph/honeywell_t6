"""Honeywell T6 Pro Z-Wave hysteresis control for Home Assistant."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import CARD_URL, CONF_SOURCE, DOMAIN, SIGNAL_STATE
from .schedule import ScheduleManager
from .zwave import T6ZWaveBridge

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
    Platform.SWITCH,
]


@dataclass
class T6RuntimeData:
    bridge: T6ZWaveBridge
    schedule: ScheduleManager


type T6ConfigEntry = ConfigEntry[T6RuntimeData]


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the card file at /honeywell_t6/t6-hysteresis-card.js.

    Add it once under Settings -> Dashboards -> Resources (JavaScript module).
    The integration deliberately does NOT inject it into every page as well:
    two loaders race each other and an older cached copy can win. Responses
    are sent without long-lived cache headers so updates show up on reload.
    """
    if hass.data.get(f"{DOMAIN}_card"):
        return
    hass.data[f"{DOMAIN}_card"] = True
    try:
        from homeassistant.components.http import StaticPathConfig  # noqa: PLC0415

        path = Path(__file__).parent / "www" / "t6-hysteresis-card.js"
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(path), False)]
        )
    except Exception:  # noqa: BLE001 - never block setup because of the card
        _LOGGER.warning("Could not register the T6 dashboard card", exc_info=True)


async def async_setup_entry(hass: HomeAssistant, entry: T6ConfigEntry) -> bool:
    """Set up a T6 hysteresis controller from a config entry."""
    if getattr(hass, "http", None) is not None:
        await _async_register_card(hass)
    bridge = T6ZWaveBridge(hass, entry.data[CONF_SOURCE])
    schedule = ScheduleManager(
        hass, entry.entry_id, hass.config.units.temperature_unit == UnitOfTemperature.CELSIUS
    )
    await schedule.async_load()
    entry.runtime_data = T6RuntimeData(bridge=bridge, schedule=schedule)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_remove_fallback_device(hass, entry)
    # Parameter entities now exist; let the climate entity list them for the card.
    async_dispatcher_send(hass, SIGNAL_STATE.format(entry.entry_id) + "_ready")
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


def _async_remove_fallback_device(hass: HomeAssistant, entry: T6ConfigEntry) -> None:
    """Delete the stand-alone 'T6 Hysteresis' device left by v1.0.0/1.0.1.

    Once the entities are attached to the real Z-Wave device the old device is
    empty; remove it so it doesn't linger in the device list.
    """
    from homeassistant.helpers import device_registry as dr, entity_registry as er  # noqa: PLC0415

    from .entity_param import source_device  # noqa: PLC0415

    if source_device(hass, entry) is None:
        return
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    # Only devices this config entry created itself carry our identifier.
    for old in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if (DOMAIN, entry.entry_id) not in old.identifiers:
            continue
        if er.async_entries_for_device(ent_reg, old.id, include_disabled_entities=True):
            continue
        dev_reg.async_remove_device(old.id)


async def _async_reload(hass: HomeAssistant, entry: T6ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: T6ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        entry.runtime_data.bridge.close()
    return ok
