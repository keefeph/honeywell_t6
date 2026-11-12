"""Numeric configuration parameters of the T6 (cycle rates, limits, lockouts...)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import T6ConfigEntry
from .entity_param import T6ParamEntity
from .parameters import PARAMETERS

# Parameters the installer manual restricts to 5-degree steps (0 = disabled).
_STEP_5 = {18, 19}


async def async_setup_entry(
    hass: HomeAssistant, entry: T6ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(T6ParamNumber(entry, p) for p in PARAMETERS if not p.is_enum)


class T6ParamNumber(T6ParamEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    @property
    def native_min_value(self) -> float:
        return float(self.param.minimum)

    @property
    def native_max_value(self) -> float:
        return float(self.param.maximum)

    @property
    def native_step(self) -> float:
        return 5.0 if self._param.number in _STEP_5 else 1.0

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self.param.unit

    @property
    def native_value(self) -> float | None:
        raw = self._bridge.get(self._param.number)
        return None if raw is None else float(raw)

    @property
    def extra_state_attributes(self):
        attrs = super().extra_state_attributes
        if self.param.options:
            attrs["special_values"] = {str(k): v for k, v in self.param.options.items()}
        return attrs

    async def async_set_native_value(self, value: float) -> None:
        await self._bridge.async_set(self._param.number, int(round(value)))
