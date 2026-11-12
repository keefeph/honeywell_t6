"""Pick-list configuration parameters of the T6 (e.g. equipment type, reminders)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import T6ConfigEntry
from .entity_param import T6ParamEntity
from .parameters import PARAMETERS


async def async_setup_entry(
    hass: HomeAssistant, entry: T6ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(T6ParamSelect(entry, p) for p in PARAMETERS if p.is_enum)


class T6ParamSelect(T6ParamEntity, SelectEntity):
    @property
    def options(self) -> list[str]:
        return list(self.param.options.values())

    @property
    def current_option(self) -> str | None:
        raw = self._bridge.get(self._param.number)
        if raw is None:
            return None
        return self.param.options.get(raw, str(raw))

    async def async_select_option(self, option: str) -> None:
        for raw, label in self.param.options.items():
            if label == option:
                await self._bridge.async_set(self._param.number, raw)
                return
        raise ServiceValidationError(f"Unknown option {option!r}")
