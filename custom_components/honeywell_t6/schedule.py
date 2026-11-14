"""Persistent schedule + hold state shared by the climate and switch entities."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .schedule_logic import default_schedule, normalize_schedule

STORAGE_VERSION = 1

HOLD_NEXT = "next"            # until the next period starts
HOLD_PERMANENT = "permanent"  # until resumed


class ScheduleManager:
    """Owns the program, the on/off flag and the hold; persists them."""

    def __init__(self, hass: HomeAssistant, entry_id: str, celsius: bool) -> None:
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.schedule.{entry_id}"
        )
        self._celsius = celsius
        self.enabled: bool = False
        self.schedule: dict[str, Any] = default_schedule(celsius)
        self.hold_type: str | None = None
        self.hold_until: datetime | None = None
        self._listeners: list[Callable[[], None]] = []

    # ---------------------------------------------------------------- store
    async def async_load(self) -> None:
        data = await self._store.async_load()
        if not data:
            return
        self.enabled = bool(data.get("enabled", False))
        try:
            self.schedule = normalize_schedule(data["schedule"], min_gap=0)
        except (KeyError, ValueError, TypeError):
            self.schedule = default_schedule(self._celsius)
        self.hold_type = data.get("hold_type")
        until = data.get("hold_until")
        self.hold_until = dt_util.parse_datetime(until) if until else None

    @callback
    def _save(self) -> None:
        self._store.async_delay_save(
            lambda: {
                "enabled": self.enabled,
                "schedule": self.schedule,
                "hold_type": self.hold_type,
                "hold_until": self.hold_until.isoformat() if self.hold_until else None,
            },
            1,
        )

    # ------------------------------------------------------------ listeners
    @callback
    def add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(cb)
        return lambda: self._listeners.remove(cb)

    @callback
    def _changed(self) -> None:
        self._save()
        for cb in list(self._listeners):
            cb()

    # -------------------------------------------------------------- actions
    @callback
    def set_schedule(self, data: dict[str, Any], min_gap: float) -> None:
        self.schedule = normalize_schedule(data, min_gap)  # ValueError on bad input
        self._changed()

    @callback
    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.hold_type = None
        self.hold_until = None
        self._changed()

    @callback
    def set_hold(self, hold_type: str, until: datetime | None) -> None:
        self.hold_type = hold_type
        self.hold_until = until if hold_type == HOLD_NEXT else None
        self._changed()

    @callback
    def clear_hold(self, notify: bool = True) -> None:
        self.hold_type = None
        self.hold_until = None
        if notify:
            self._changed()
        else:
            self._save()

    @property
    def held(self) -> bool:
        return self.enabled and self.hold_type is not None
