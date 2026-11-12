"""Hysteresis phase sensor (handy for history graphs and automations)."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import T6ConfigEntry
from .const import ATTR_CYCLES, ATTR_STATUS, SIGNAL_STATE
from .entity_param import attach_to_device


async def async_setup_entry(
    hass: HomeAssistant, entry: T6ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([T6PhaseSensor(entry)])


class T6PhaseSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "phase"
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["off", "running", "resting", "override"]
    _attr_icon = "mdi:sine-wave"

    def __init__(self, entry: T6ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_phase"
        attach_to_device(self, entry.runtime_data.bridge.hass, entry)
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_STATE.format(self._entry.entry_id), self._update
            )
        )

    @callback
    def _update(self, phase: str, status: str, cycles: int) -> None:
        self._attr_native_value = phase
        self._attr_extra_state_attributes = {ATTR_STATUS: status, ATTR_CYCLES: cycles}
        self.async_write_ha_state()
