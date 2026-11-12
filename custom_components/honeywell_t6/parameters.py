"""Honeywell T6 Pro Z-Wave (TH6320ZW) configuration parameters.

Generated from the Z-Wave JS device database
(packages/config/config/devices/0x0039/th6320zw.json + Honeywell templates).
Live metadata reported by Z-Wave JS takes precedence at runtime; this table is
the fallback so that every parameter is exposed even before the node interview
finishes.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class T6Param:
    number: int
    label: str
    category: str
    minimum: int
    maximum: int
    default: int
    unit: str | None = None
    options: dict[int, str] = field(default_factory=dict)
    manual_entry: bool = True
    description: str | None = None

    @property
    def is_enum(self) -> bool:
        """Parameter is a pick-list (no free numeric entry)."""
        return bool(self.options) and not self.manual_entry


PARAMETERS: tuple[T6Param, ...] = (
    T6Param(1, 'Schedule Type', 'Display & schedule', 0, 4, 2, None, {0: 'No schedule on thermostat', 1: 'Single schedule', 2: '5-2 schedule', 3: '5-1-1 schedule', 4: 'Every day unique schedule'}, False, 'On-thermostat schedule type'),
    T6Param(2, 'Temperature Scale', 'Display & schedule', 0, 1, 0, None, {0: 'Fahrenheit', 1: 'Celsius'}, False, None),
    T6Param(3, 'Outdoor Temperature Sensor', 'Equipment', 0, 1, 0, None, {0: 'Disable', 1: 'Enable'}, False, None),
    T6Param(4, 'Equipment Type', 'Equipment', 0, 9, 2, None, {0: 'None', 1: 'Standard Gas', 2: 'High Efficiency Gas', 3: 'Oil', 4: 'Electric', 5: 'Fan Coil', 6: 'Air to Air Heat pump', 7: 'Geothermal Heat Pump', 8: 'Hot Water', 9: 'Steam'}, False, None),
    T6Param(5, 'Reversing Valve', 'Equipment', 0, 1, 0, None, {0: 'O/B on Cool', 1: 'O/B on Heat'}, False, None),
    T6Param(6, 'Cool Stages', 'Equipment', 0, 2, 1, None, {}, True, None),
    T6Param(7, 'Heat Stages', 'Equipment', 0, 2, 1, None, {}, True, 'Heat stages or auxiliary/emergency stages'),
    T6Param(8, 'Auxiliary/Emergency Control', 'Equipment', 0, 1, 0, None, {0: 'Both auxiliary and emergency', 1: 'Either auxiliary or emergency'}, False, None),
    T6Param(9, 'Auxiliary Heat Type', 'Equipment', 0, 1, 0, None, {0: 'Electric', 1: 'Gas/Oil'}, False, None),
    T6Param(10, 'Emergency Heat Type', 'Equipment', 0, 1, 0, None, {0: 'Electric', 1: 'Gas/Oil'}, False, None),
    T6Param(11, 'Fossil Kit Control', 'Equipment', 0, 1, 0, None, {0: 'Thermostat', 1: 'External'}, False, None),
    T6Param(12, 'Auto Changeover', 'Staging & limits', 0, 1, 0, None, {0: 'Disable', 1: 'Enable'}, False, None),
    T6Param(13, 'Auto Differential', 'Staging & limits', 0, 5, 0, '°F', {}, True, None),
    T6Param(14, 'High Cool Stage Finish', 'Staging & limits', 0, 1, 0, None, {0: 'Disable', 1: 'Enable'}, False, None),
    T6Param(15, 'High Heat Stage Finish', 'Staging & limits', 0, 1, 0, None, {0: 'Disable', 1: 'Enable'}, False, None),
    T6Param(16, 'Auxiliary Heat Droop', 'Staging & limits', 0, 15, 0, None, {0: 'Comfort', 2: '2 °F', 3: '3 °F', 4: '4 °F', 5: '5 °F', 6: '6 °F', 7: '7 °F', 8: '8 °F', 9: '9 °F', 10: '10 °F', 11: '11 °F', 12: '12 °F', 13: '13 °F', 14: '14 °F', 15: '15 °F'}, False, None),
    T6Param(17, 'Up Stage Timer Aux Heat', 'Staging & limits', 0, 15, 0, None, {0: 'Off', 1: '30 minutes', 2: '45 minutes', 3: '60 minutes', 4: '75 minutes', 5: '90 minutes', 6: '2 hours', 7: '3 hours', 8: '4 hours', 9: '5 hours', 10: '6 hours', 11: '8 hours', 12: '10 hours', 13: '12 hours', 14: '14 hours', 15: '16 hours'}, False, None),
    T6Param(18, 'Balance Point', 'Staging & limits', 0, 65, 0, '°F', {0: 'Disable'}, True, 'Compressor Lockout allowable range: 5-65 in 5 degree increments'),
    T6Param(19, 'Aux Heat Outdoor Lockout', 'Staging & limits', 0, 65, 0, '°F', {0: 'Disable'}, True, 'Allowable range: 5-65 in 5 degree increments'),
    T6Param(20, 'Cool Stage 1 Cycle Rate', 'Cycle rates', 1, 6, 3, 'Cycles per hour', {}, True, None),
    T6Param(21, 'Cool Stage 2 Cycle Rate', 'Cycle rates', 1, 6, 3, 'Cycles per hour', {}, True, None),
    T6Param(22, 'Heat Stage 1 Cycle Rate', 'Cycle rates', 1, 12, 3, 'Cycles per hour', {}, True, None),
    T6Param(23, 'Heat Stage 2 Cycle Rate', 'Cycle rates', 1, 12, 3, 'Cycles per hour', {}, True, None),
    T6Param(24, 'Aux Heat Cycle Rate', 'Cycle rates', 1, 12, 9, 'Cycles per hour', {}, True, None),
    T6Param(25, 'Emergency Heat Cycle Rate', 'Cycle rates', 1, 12, 9, 'Cycles per hour', {}, True, None),
    T6Param(26, 'Compressor Protection', 'Staging & limits', 0, 5, 5, 'minutes', {0: 'Disable'}, True, None),
    T6Param(27, 'Adaptive Intelligent Recovery', 'Staging & limits', 0, 1, 0, None, {0: 'Disable', 1: 'Enable'}, False, None),
    T6Param(28, 'Minimum Cool Temperature', 'Staging & limits', 50, 99, 50, '°F', {}, True, None),
    T6Param(29, 'Maximum Heat Temperature', 'Staging & limits', 40, 90, 90, '°F', {}, True, None),
    T6Param(30, 'Air Filters', 'Maintenance reminders', 0, 2, 0, None, {}, True, None),
    T6Param(31, 'Air Filter 1 Reminder', 'Maintenance reminders', 0, 19, 0, None, {0: 'Disable', 1: '10 run time days', 2: '20 run time days', 3: '30 run time days', 4: '45 run time days', 5: '60 run time days', 6: '90 run time days', 7: '120 run time days', 8: '150 run time days', 9: '30 days', 10: '45 days', 11: '60 days', 12: '75 days', 13: '3 months', 14: '4 months', 15: '5 months', 16: '6 months', 17: '9 months', 18: '12 months', 19: '15 months'}, False, None),
    T6Param(32, 'Air Filter 2 Reminder', 'Maintenance reminders', 0, 19, 0, None, {0: 'Disable', 1: '10 run time days', 2: '20 run time days', 3: '30 run time days', 4: '45 run time days', 5: '60 run time days', 6: '90 run time days', 7: '120 run time days', 8: '150 run time days', 9: '30 days', 10: '45 days', 11: '60 days', 12: '75 days', 13: '3 months', 14: '4 months', 15: '5 months', 16: '6 months', 17: '9 months', 18: '12 months', 19: '15 months'}, False, None),
    T6Param(33, 'Humidification Pad Reminder', 'Maintenance reminders', 0, 2, 0, None, {0: 'Disable', 1: '6 months', 2: '12 months'}, False, None),
    T6Param(34, 'Dehumidification Filter Reminder', 'Maintenance reminders', 0, 12, 0, 'months', {0: 'Disable'}, True, None),
    T6Param(35, 'Ventilation Filter Reminder', 'Maintenance reminders', 0, 12, 0, None, {0: 'Disable', 3: '3 months', 6: '6 months', 9: '9 months', 12: '12 months'}, False, None),
    T6Param(36, 'UV Devices', 'Maintenance reminders', 0, 2, 0, None, {}, True, None),
    T6Param(37, 'UV Bulb 1 Reminder', 'Maintenance reminders', 0, 24, 0, None, {0: 'Disable', 6: '6 months', 12: '12 months', 24: '24 months'}, False, None),
    T6Param(38, 'UV Bulb 2 Reminder', 'Maintenance reminders', 0, 24, 0, None, {0: 'Disable', 6: '6 months', 12: '12 months', 24: '24 months'}, False, None),
    T6Param(39, 'Idle Brightness', 'Display & schedule', 0, 5, 0, None, {}, True, None),
    T6Param(40, 'Clock Format', 'Display & schedule', 0, 1, 0, None, {0: '12 hour', 1: '24 hour'}, False, None),
    T6Param(41, 'Daylight Saving', 'Display & schedule', 0, 1, 0, None, {0: 'Disable', 1: 'Enable'}, False, None),
    T6Param(42, 'Temperature Offset', 'Display & schedule', -3, 3, 0, None, {0: 'Off', -1: '-1 °F / -0.5 °C', -2: '-2 °F / -1.0 °C', -3: '-3 °F / -1.5 °C', 1: '+1 °F / +0.5 °C', 2: '+2 °F / +1.0 °C', 3: '+3 °F / +1.5 °C'}, False, None),
)

PARAMS_BY_NUMBER: dict[int, T6Param] = {p.number: p for p in PARAMETERS}

CATEGORIES: tuple[str, ...] = (
    "Equipment",
    "Staging & limits",
    "Cycle rates",
    "Maintenance reminders",
    "Display & schedule",
)
