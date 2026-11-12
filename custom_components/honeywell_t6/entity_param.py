"""Shared base for T6 configuration-parameter entities."""
from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device import async_entity_id_to_device
from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import ATTR_CATEGORY, ATTR_PARAMETER, CONF_SOURCE, DOMAIN
from .parameters import T6Param
from .zwave import T6ZWaveBridge

# Installer-level parameters that can break an HVAC system if set wrongly start
# disabled in the entity registry; enable them deliberately.
RISKY = {4, 5, 6, 7, 8, 9, 10, 11}


def device_info(entry: Any) -> DeviceInfo:
    """Fallback device used only when the Z-Wave T6 device can't be found."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_NAME, "T6 Hysteresis"),
        manufacturer="Honeywell",
        model="T6 Pro Z-Wave (TH6320ZW)",
    )


def source_device(hass: HomeAssistant, entry: Any) -> dr.DeviceEntry | None:
    """The Z-Wave JS device that owns the T6 climate entity."""
    return async_entity_id_to_device(hass, entry.data[CONF_SOURCE])


def attach_to_device(entity: Entity, hass: HomeAssistant, entry: Any) -> None:
    """Put the entity on the T6's own Z-Wave device page.

    Uses the current Home Assistant pattern for helper integrations
    (``entity.device_entry``) rather than a device_info that borrows another
    integration's identifiers, which newer releases refuse.
    """
    if (device := source_device(hass, entry)) is not None:
        entity.device_entry = device
    else:
        entity._attr_device_info = device_info(entry)  # noqa: SLF001


class T6ParamEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: Any, param: T6Param) -> None:
        self._bridge: T6ZWaveBridge = entry.runtime_data.bridge
        self._param = param
        self._attr_unique_id = f"{entry.entry_id}_param_{param.number}"
        self._attr_name = f"P{param.number:02d} {param.label}"
        attach_to_device(self, entry.runtime_data.bridge.hass, entry)
        self._attr_entity_registry_enabled_default = param.number not in RISKY

    @property
    def param(self) -> T6Param:
        return self._bridge.describe(self._param.number)

    @property
    def available(self) -> bool:
        return self._bridge.available(self._param.number)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        p = self.param
        return {
            ATTR_PARAMETER: p.number,
            ATTR_CATEGORY: p.category,
            "default": p.default,
            "raw_value": self._bridge.get(p.number),
            "description": p.description,
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._bridge.subscribe(self._param.number, self.async_write_ha_state)
        )
