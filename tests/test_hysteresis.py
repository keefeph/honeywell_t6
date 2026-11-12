"""Unit tests for the hysteresis state machine (no Home Assistant needed)."""
import importlib.util
import pathlib
import sys

_path = pathlib.Path(__file__).parents[1] / "custom_components/honeywell_t6/hysteresis.py"
_spec = importlib.util.spec_from_file_location("t6_hysteresis_under_test", _path)
h = importlib.util.module_from_spec(_spec)
sys.modules["t6_hysteresis_under_test"] = h
_spec.loader.exec_module(h)

Mode, Phase, Strategy = h.Mode, h.Phase, h.Strategy


def ctl(**kw):
    c = h.HysteresisController(low=67, high=71, **kw)
    return c


def run(c, temps):
    out = []
    for t in temps:
        c.evaluate(t)
        out.append(c.phase)
    return out


def test_heating_cycle():
    c = ctl()
    assert c.set_mode(Mode.HEAT, 66) == Phase.RUNNING
    phases = run(c, [67, 69, 70.5, 71, 70, 68, 67.5, 67, 68, 71.2])
    R, S = Phase.RUNNING, Phase.RESTING
    assert phases == [R, R, R, S, S, S, S, R, R, S]
    assert c.cycles == 1


def test_cooling_cycle():
    c = ctl()
    assert c.set_mode(Mode.COOL, 73) == Phase.RUNNING
    R, S = Phase.RUNNING, Phase.RESTING
    phases = run(c, [72, 70, 67.5, 67, 68, 70, 70.9, 71, 69, 66.8])
    assert phases == [R, R, R, S, S, S, S, R, R, S]


def test_entry_inside_band_respects_initial_phase():
    assert ctl().set_mode(Mode.HEAT, 69) == Phase.RESTING
    assert ctl(initial_phase=h.InitialPhase.RUNNING).set_mode(Mode.HEAT, 69) == Phase.RUNNING
    assert ctl().set_mode(Mode.COOL, 69) == Phase.RESTING


def test_heat_commands_setpoint_strategy():
    c = ctl(drive_offset=1)
    c.set_mode(Mode.HEAT, 60)
    assert c.command() == h.DeviceCommand("heat", 72)  # high + drive
    c.evaluate(71)
    assert c.command() == h.DeviceCommand("heat", 67)  # rest at low


def test_cool_commands_setpoint_strategy():
    c = ctl(drive_offset=1)
    c.set_mode(Mode.COOL, 80)
    assert c.command() == h.DeviceCommand("cool", 66)
    c.evaluate(67)
    assert c.command() == h.DeviceCommand("cool", 71)


def test_mode_strategy_turns_device_off_while_resting():
    c = ctl(strategy=Strategy.MODE)
    c.set_mode(Mode.HEAT, 72)
    assert c.phase == Phase.RESTING
    assert c.command() == h.DeviceCommand("off", None)


def test_celsius_rounding_and_clamp():
    c = h.HysteresisController(low=19.3, high=21.2, step=0.5, drive_offset=0.5,
                               device_min=4.5, device_max=32)
    c.set_mode(Mode.HEAT, 18)
    assert c.command().setpoint == 22.0  # 21.7 rounded up
    c.evaluate(21.2)
    assert c.command().setpoint == 19.0  # 19.3 rounded down (never call early)
    c.set_band(31, 33)
    c.mode = Mode.HEAT
    c.phase = Phase.RUNNING
    assert c.command().setpoint == 32  # clamped to device max


def test_band_min_gap_and_swap():
    c = ctl(min_gap=2)
    c.set_band(70, 69)
    assert (c.low, c.high) == (69, 71)


def test_off():
    c = ctl()
    c.set_mode(Mode.HEAT, 60)
    c.set_mode(Mode.OFF, 60)
    assert c.phase == Phase.OFF
    assert not c.evaluate(50)
    assert c.command() == h.DeviceCommand("off", None)
