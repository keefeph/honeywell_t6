"""Constants for the Honeywell T6 Hysteresis integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "honeywell_t6"
VERSION: Final = "1.0.4"

CONF_SOURCE: Final = "source_entity_id"
CONF_STRATEGY: Final = "strategy"
CONF_DRIVE_OFFSET: Final = "drive_offset"
CONF_INITIAL_PHASE: Final = "initial_phase"
CONF_MIN_GAP: Final = "min_gap"
CONF_TEMP_SENSOR: Final = "temperature_sensor"
CONF_FOLLOW_WALL: Final = "follow_wall_changes"

DEFAULT_STRATEGY: Final = "setpoint"
DEFAULT_INITIAL_PHASE: Final = "resting"
DEFAULT_FOLLOW_WALL: Final = True
# (°F, °C)
DEFAULT_DRIVE_OFFSET: Final = (1.0, 0.5)
DEFAULT_MIN_GAP: Final = (1.0, 0.5)
DEFAULT_BAND_HEAT: Final = ((67.0, 71.0), (19.5, 21.5))

# Seconds to wait before re-sending an identical command (Z-Wave reports lag).
COMMAND_HOLDOFF: Final = 60
# Seconds after our last command during which device changes are assumed ours.
WALL_CHANGE_GRACE: Final = 90
# Periodic reconcile interval (seconds).
RECONCILE_INTERVAL: Final = 120

ATTR_PHASE: Final = "phase"
ATTR_STATUS: Final = "status"
ATTR_DEVICE_MODE: Final = "device_hvac_mode"
ATTR_DEVICE_SETPOINT: Final = "device_setpoint"
ATTR_CYCLES: Final = "cycles"
ATTR_OVERRIDE: Final = "override"
ATTR_STRATEGY: Final = "strategy"
ATTR_PARAM_ENTITIES: Final = "parameter_entities"
ATTR_PARAMETER: Final = "parameter"
ATTR_CATEGORY: Final = "category"

SERVICE_SET_BAND: Final = "set_band"
SERVICE_FORCE_PHASE: Final = "force_phase"
SERVICE_REFRESH_PARAMS: Final = "refresh_parameters"

CARD_URL: Final = f"/{DOMAIN}/t6-hysteresis-card.js"
SIGNAL_STATE: Final = f"{DOMAIN}_state_{{}}"
