"""Schedule on/off switch (handy for automations, e.g. vacation mode)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import T6ConfigEntry
from .entity_param import attach_to_device


async def async_setup_entry(
    hass: HomeAssistant, entry: T6ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([T6ScheduleSwitch(entry)])


class T6ScheduleSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "schedule"
    _attr_should_poll = False
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, entry: T6ConfigEntry) -> None:
        self._sched = entry.runtime_data.schedule
        self._attr_unique_id = f"{entry.entry_id}_schedule"
        attach_to_device(self, entry.runtime_data.bridge.hass, entry)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._sched.add_listener(self.async_write_ha_state))

    @property
    def is_on(self) -> bool:
        return self._sched.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._sched.set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._sched.set_enabled(False)
