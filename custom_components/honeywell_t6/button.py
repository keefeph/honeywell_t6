"""Button to re-read all configuration parameters from the thermostat."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import T6ConfigEntry
from .entity_param import attach_to_device


async def async_setup_entry(
    hass: HomeAssistant, entry: T6ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([T6RefreshButton(entry)])


class T6RefreshButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "refresh_parameters"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:refresh"

    def __init__(self, entry: T6ConfigEntry) -> None:
        self._bridge = entry.runtime_data.bridge
        self._attr_unique_id = f"{entry.entry_id}_refresh"
        attach_to_device(self, entry.runtime_data.bridge.hass, entry)

    async def async_press(self) -> None:
        await self._bridge.async_refresh()
