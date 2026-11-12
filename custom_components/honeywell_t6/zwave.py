"""Bridge to the T6's Z-Wave Configuration CC values via the Z-Wave JS integration."""
from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .parameters import PARAMS_BY_NUMBER, T6Param

_LOGGER = logging.getLogger(__name__)

CC_CONFIGURATION = 112


class T6ZWaveBridge:
    """Reads, writes and watches the thermostat's configuration parameters.

    The Z-Wave node is resolved lazily from the source climate entity so the
    integration still loads while Z-Wave JS is starting or the node is asleep.
    """

    def __init__(self, hass: HomeAssistant, source_entity_id: str) -> None:
        self.hass = hass
        self.source_entity_id = source_entity_id
        self._node: Any | None = None
        self._unsubs: list[Callable[[], None]] = []
        self._listeners: dict[int, list[Callable[[], None]]] = {}

    # ----------------------------------------------------------------- node
    @property
    def node(self) -> Any | None:
        if self._node is None:
            self._resolve()
        return self._node

    def _resolve(self) -> None:
        try:
            from homeassistant.components.zwave_js.helpers import (  # noqa: PLC0415
                async_get_node_from_entity_id,
            )

            node = async_get_node_from_entity_id(self.hass, self.source_entity_id)
        except Exception as err:  # noqa: BLE001 - Z-Wave JS not ready / not a Z-Wave entity
            _LOGGER.debug("Z-Wave node for %s not available yet: %s", self.source_entity_id, err)
            return
        self._node = node
        try:
            for event in ("value updated", "metadata updated"):
                self._unsubs.append(node.on(event, self._on_value_updated))
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not subscribe to value updates", exc_info=True)
        self._notify_all()

    def close(self) -> None:
        while self._unsubs:
            self._unsubs.pop()()
        self._node = None

    # -------------------------------------------------------------- values
    def _value(self, number: int) -> Any | None:
        node = self.node
        if node is None:
            return None
        return node.values.get(f"{node.node_id}-{CC_CONFIGURATION}-0-{number}")

    def available(self, number: int) -> bool:
        node = self.node
        if node is None:
            return False
        if str(getattr(node, "status", "")).lower().endswith("dead"):
            return False
        return self._value(number) is not None

    def get(self, number: int) -> int | None:
        value = self._value(number)
        if value is None or value.value is None:
            return None
        try:
            return int(value.value)
        except (TypeError, ValueError):
            return None

    def describe(self, number: int) -> T6Param:
        """Static definition merged with live metadata from Z-Wave JS."""
        static = PARAMS_BY_NUMBER[number]
        value = self._value(number)
        meta = getattr(value, "metadata", None)
        if meta is None:
            return static
        states = getattr(meta, "states", None) or {}
        options = {int(k): v for k, v in states.items()} if states else static.options
        allow_manual = getattr(meta, "allow_manual_entry", None)
        return T6Param(
            number=number,
            label=getattr(meta, "label", None) or static.label,
            category=static.category,
            minimum=meta.min if getattr(meta, "min", None) is not None else static.minimum,
            maximum=meta.max if getattr(meta, "max", None) is not None else static.maximum,
            default=meta.default if getattr(meta, "default", None) is not None else static.default,
            unit=getattr(meta, "unit", None) or static.unit,
            options=options,
            manual_entry=static.manual_entry if allow_manual is None else bool(allow_manual),
            description=getattr(meta, "description", None) or static.description,
        )

    async def async_set(self, number: int, new_value: int) -> None:
        node = self.node
        if node is None:
            raise HomeAssistantError("Thermostat's Z-Wave node is not available")
        from zwave_js_server.util.node import async_set_config_parameter  # noqa: PLC0415

        try:
            await async_set_config_parameter(node, int(new_value), number)
        except Exception as err:
            raise HomeAssistantError(
                f"Setting T6 parameter {number} to {new_value} failed: {err}"
            ) from err

    async def async_refresh(self) -> None:
        node = self.node
        if node is None:
            raise HomeAssistantError("Thermostat's Z-Wave node is not available")
        from zwave_js_server.const import CommandClass  # noqa: PLC0415

        await node.async_refresh_cc_values(CommandClass.CONFIGURATION)

    # ------------------------------------------------------------ listeners
    @callback
    def subscribe(self, number: int, cb: Callable[[], None]) -> Callable[[], None]:
        self._listeners.setdefault(number, []).append(cb)

        def _unsub() -> None:
            self._listeners[number].remove(cb)

        return _unsub

    @callback
    def _on_value_updated(self, event: dict) -> None:
        value = event.get("value")
        if value is None or getattr(value, "command_class", None) != CC_CONFIGURATION:
            return
        for cb in list(self._listeners.get(int(value.property_), [])):
            cb()

    @callback
    def _notify_all(self) -> None:
        for cbs in self._listeners.values():
            for cb in list(cbs):
                cb()
