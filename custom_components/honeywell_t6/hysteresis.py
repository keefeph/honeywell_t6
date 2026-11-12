"""Two-set-point hysteresis state machine (no Home Assistant imports).

Heating:  equipment RUNS until the HIGH set point is reached, then RESTS until
          the temperature falls to the LOW set point.
Cooling:  equipment RUNS until the LOW set point is reached, then RESTS until
          the temperature rises to the HIGH set point.

The controller decides a *phase* (``running`` / ``resting``) and translates it
into a command for the physical thermostat:

* ``setpoint`` strategy (default, fail-safe): the T6 stays in HEAT/COOL and only
  its set point is moved.  Running phase = the far edge of the band pushed by
  ``drive_offset`` so the T6's own cycle-rate logic keeps calling; resting
  phase = the near edge of the band, so the T6 will not call again until the
  band is crossed.  If Home Assistant goes down, the T6 still regulates inside
  the band.
* ``mode`` strategy: running phase = HEAT/COOL with the driven set point;
  resting phase = thermostat mode OFF.  Hard guarantee that nothing runs while
  resting, but if Home Assistant stops while resting the T6 stays off.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math


class Mode(StrEnum):
    OFF = "off"
    HEAT = "heat"
    COOL = "cool"


class Phase(StrEnum):
    RUNNING = "running"
    RESTING = "resting"
    OFF = "off"


class Strategy(StrEnum):
    SETPOINT = "setpoint"
    MODE = "mode"


class InitialPhase(StrEnum):
    """What to do when (re)entering a mode with the temperature inside the band."""

    RESTING = "resting"  # energy saver: wait for the band edge
    RUNNING = "running"  # comfort: drive to the far edge first


@dataclass(frozen=True)
class DeviceCommand:
    """What the physical thermostat should be set to."""

    hvac_mode: str  # "heat" | "cool" | "off"
    setpoint: float | None


@dataclass
class HysteresisController:
    low: float = 67.0
    high: float = 71.0
    mode: Mode = Mode.OFF
    phase: Phase = Phase.OFF
    strategy: Strategy = Strategy.SETPOINT
    drive_offset: float = 1.0
    initial_phase: InitialPhase = InitialPhase.RESTING
    min_gap: float = 1.0
    step: float = 1.0
    device_min: float = 40.0
    device_max: float = 99.0
    cycles: int = 0  # number of RESTING -> RUNNING transitions

    # ------------------------------------------------------------------ band
    def set_band(self, low: float, high: float) -> None:
        """Set the band; keeps at least ``min_gap`` between the edges."""
        if low > high:
            low, high = high, low
        if high - low < self.min_gap:
            high = low + self.min_gap
        self.low = float(low)
        self.high = float(high)

    # ------------------------------------------------------------------ mode
    def set_mode(self, mode: Mode, temperature: float | None) -> Phase:
        mode = Mode(mode)
        if mode == self.mode and self.phase != Phase.OFF:
            return self.phase
        self.mode = mode
        if mode == Mode.OFF:
            self.phase = Phase.OFF
            return self.phase
        self.phase = self._entry_phase(temperature)
        return self.phase

    def _entry_phase(self, t: float | None) -> Phase:
        if t is None:
            return Phase.RESTING if self.initial_phase == InitialPhase.RESTING else Phase.RUNNING
        if self.mode == Mode.HEAT:
            if t <= self.low:
                return Phase.RUNNING
            if t >= self.high:
                return Phase.RESTING
        elif self.mode == Mode.COOL:
            if t >= self.high:
                return Phase.RUNNING
            if t <= self.low:
                return Phase.RESTING
        return Phase(self.initial_phase.value)

    # ------------------------------------------------------------ evaluation
    def evaluate(self, t: float | None) -> bool:
        """Advance the state machine. Returns True if the phase changed."""
        if t is None or self.mode == Mode.OFF:
            return False
        if self.phase == Phase.OFF:  # e.g. restored without a phase
            self.phase = self._entry_phase(t)
            return True
        new = self.phase
        if self.mode == Mode.HEAT:
            if self.phase == Phase.RUNNING and t >= self.high:
                new = Phase.RESTING
            elif self.phase == Phase.RESTING and t <= self.low:
                new = Phase.RUNNING
        else:  # COOL
            if self.phase == Phase.RUNNING and t <= self.low:
                new = Phase.RESTING
            elif self.phase == Phase.RESTING and t >= self.high:
                new = Phase.RUNNING
        if new != self.phase:
            if new == Phase.RUNNING:
                self.cycles += 1
            self.phase = new
            return True
        return False

    # -------------------------------------------------------------- command
    def _round(self, value: float, direction: int) -> float:
        """Round to the device step, away from the band centre."""
        step = self.step or 1.0
        n = value / step
        n = math.ceil(n - 1e-9) if direction > 0 else math.floor(n + 1e-9)
        value = round(n * step, 2)
        return min(max(value, self.device_min), self.device_max)

    def command(self) -> DeviceCommand:
        if self.mode == Mode.OFF or self.phase == Phase.OFF:
            return DeviceCommand("off", None)
        if self.mode == Mode.HEAT:
            if self.phase == Phase.RUNNING:
                return DeviceCommand("heat", self._round(self.high + self.drive_offset, +1))
            if self.strategy == Strategy.MODE:
                return DeviceCommand("off", None)
            # Resting: the T6 must not call before LOW is crossed.
            return DeviceCommand("heat", self._round(self.low, -1))
        # COOL
        if self.phase == Phase.RUNNING:
            return DeviceCommand("cool", self._round(self.low - self.drive_offset, -1))
        if self.strategy == Strategy.MODE:
            return DeviceCommand("off", None)
        return DeviceCommand("cool", self._round(self.high, +1))

    # -------------------------------------------------------------- display
    def describe(self) -> str:
        if self.mode == Mode.OFF:
            return "Off"
        if self.mode == Mode.HEAT:
            return (
                f"Heating until {self.high:g}°"
                if self.phase == Phase.RUNNING
                else f"Resting until it drops to {self.low:g}°"
            )
        return (
            f"Cooling until {self.low:g}°"
            if self.phase == Phase.RUNNING
            else f"Resting until it rises to {self.high:g}°"
        )
