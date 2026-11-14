"""Unit tests for the time-of-day band program (no Home Assistant needed)."""
import importlib.util
import pathlib
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

_path = pathlib.Path(__file__).parents[1] / "custom_components/honeywell_t6/schedule_logic.py"
_spec = importlib.util.spec_from_file_location("t6_schedule_under_test", _path)
s = importlib.util.module_from_spec(_spec)
sys.modules["t6_schedule_under_test"] = s
_spec.loader.exec_module(s)

TZ = ZoneInfo("America/Detroit")


def at(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=TZ)


def test_default_is_valid_and_resolves():
    sch = s.normalize_schedule(s.default_schedule())
    r = s.resolve(sch, at(2026, 11, 13, 12, 0), "heat")  # Friday noon
    assert (r.name, r.low, r.high) == ("Away", 62, 65)
    assert r.next_name == "Home" and r.next_at == at(2026, 11, 13, 17, 0)


def test_before_first_period_uses_previous_days_last():
    sch = s.normalize_schedule(s.default_schedule())
    r = s.resolve(sch, at(2026, 11, 13, 3, 0), "heat")
    assert r.name == "Sleep" and r.since == at(2026, 11, 12, 22, 0)
    assert r.next_name == "Wake" and r.next_at == at(2026, 11, 13, 6, 0)


def test_after_last_period_next_is_tomorrow():
    sch = s.normalize_schedule(s.default_schedule())
    r = s.resolve(sch, at(2026, 11, 13, 23, 0), "cool")
    assert (r.name, r.low, r.high) == ("Sleep", 76, 79)
    assert r.next_at == at(2026, 11, 14, 6, 0)


def test_exact_boundary_belongs_to_new_period():
    sch = s.normalize_schedule(s.default_schedule())
    r = s.resolve(sch, at(2026, 11, 13, 17, 0), "heat")
    assert r.name == "Home" and r.next_at == at(2026, 11, 13, 22, 0)


def test_weekday_weekend_layout_differs_on_saturday():
    raw = s.default_schedule()
    raw["layout"] = "weekday_weekend"
    raw["days"]["sat"]["heat"] = [
        {"name": "Lazy", "start": "08:30", "low": 68, "high": 71},
        {"name": "Sleep", "start": "23:00", "low": 63, "high": 66},
    ]
    sch = s.normalize_schedule(raw)
    assert sch["days"]["sun"]["heat"][0]["name"] == "Lazy"      # copied to whole group
    assert sch["days"]["mon"]["heat"][0]["name"] == "Wake"
    r = s.resolve(sch, at(2026, 11, 14, 7, 0), "heat")          # Saturday 7:00
    assert r.name == "Sleep" and r.since == at(2026, 11, 13, 22, 0)  # Friday's sleep
    assert r.next_name == "Lazy" and r.next_at == at(2026, 11, 14, 8, 30)
    r = s.resolve(sch, at(2026, 11, 15, 23, 30), "heat")        # Sunday night
    assert r.next_name == "Wake" and r.next_at == at(2026, 11, 16, 6, 0)


def test_single_period_day_wraps_to_itself():
    raw = s.default_schedule()
    for d in s.DAYS:
        raw["days"][d]["cool"] = [{"name": "All day", "start": "00:00", "low": 74, "high": 78}]
    sch = s.normalize_schedule(raw)
    r = s.resolve(sch, at(2026, 11, 13, 15, 0), "cool")
    assert r.name == "All day" and r.next_at == at(2026, 11, 14, 0, 0)


def test_validation_errors():
    raw = s.default_schedule()
    raw["days"]["tue"]["heat"][1]["high"] = 62.5
    with pytest.raises(ValueError, match="at least 1"):
        s.normalize_schedule(raw)
    raw = s.default_schedule()
    raw["days"]["wed"]["cool"][2]["start"] = "06:00"
    with pytest.raises(ValueError, match="same time"):
        s.normalize_schedule(raw)
    raw = s.default_schedule()
    raw["days"]["thu"]["heat"] = []
    with pytest.raises(ValueError, match="at least one"):
        s.normalize_schedule(raw)
    raw = s.default_schedule()
    raw["days"]["fri"]["heat"][0]["start"] = "25:00"
    with pytest.raises(ValueError):
        s.normalize_schedule(raw)


def test_sorting_and_swapped_band():
    raw = s.default_schedule()
    raw["layout"] = "each_day"
    raw["days"]["mon"]["heat"] = [
        {"name": "B", "start": "18:00", "low": 70, "high": 66},
        {"name": "A", "start": "7:05", "low": 64, "high": 66},
    ]
    sch = s.normalize_schedule(raw)
    assert [p["name"] for p in sch["days"]["mon"]["heat"]] == ["A", "B"]
    assert sch["days"]["mon"]["heat"][0]["start"] == "07:05"
    assert (sch["days"]["mon"]["heat"][1]["low"], sch["days"]["mon"]["heat"][1]["high"]) == (66, 70)
    assert sch["days"]["tue"]["heat"][0]["name"] == "Wake"      # each_day: untouched


def test_dst_spring_forward():
    sch = s.normalize_schedule(s.default_schedule())
    # 2027-03-14: clocks jump 02:00 -> 03:00 in Detroit
    r = s.resolve(sch, at(2027, 3, 14, 1, 30), "heat")
    assert r.next_at.hour == 6 and r.next_at.utcoffset().total_seconds() == -4 * 3600
