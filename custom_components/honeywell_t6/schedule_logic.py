"""Time-of-day band program (no Home Assistant imports).

Data model (what is stored and what the card edits)::

    {
      "layout": "same" | "weekday_weekend" | "each_day",   # editing convenience only
      "days": {
        "mon": {"heat": [period, ...], "cool": [period, ...]},
        ... "sun"
      }
    }
    period = {"name": "Wake", "start": "06:00", "low": 67.0, "high": 70.0}

Every day always holds its own list, so resolving never depends on the
layout; the layout only tells the card which days are edited together.
A period runs from its start time until the next period's start (wrapping
past midnight into the following days).
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

DAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
SEASONS: tuple[str, ...] = ("heat", "cool")
LAYOUTS: tuple[str, ...] = ("same", "weekday_weekend", "each_day")
MAX_PERIODS = 8

LAYOUT_GROUPS: dict[str, list[list[str]]] = {
    "same": [list(DAYS)],
    "weekday_weekend": [list(DAYS[:5]), list(DAYS[5:])],
    "each_day": [[d] for d in DAYS],
}


def default_schedule(celsius: bool = False) -> dict[str, Any]:
    """Honeywell-style Wake / Away / Home / Sleep program."""
    if celsius:
        heat = [("Wake", "06:00", 19.5, 21.0), ("Away", "08:00", 17.0, 18.5),
                ("Home", "17:00", 19.5, 21.0), ("Sleep", "22:00", 17.0, 18.5)]
        cool = [("Wake", "06:00", 23.5, 25.0), ("Away", "08:00", 25.5, 27.0),
                ("Home", "17:00", 23.5, 25.0), ("Sleep", "22:00", 24.5, 26.0)]
    else:
        heat = [("Wake", "06:00", 67, 70), ("Away", "08:00", 62, 65),
                ("Home", "17:00", 67, 70), ("Sleep", "22:00", 62, 65)]
        cool = [("Wake", "06:00", 74, 77), ("Away", "08:00", 78, 81),
                ("Home", "17:00", 74, 77), ("Sleep", "22:00", 76, 79)]

    def plist(rows):
        return [{"name": n, "start": s, "low": float(lo), "high": float(hi)} for n, s, lo, hi in rows]

    return {
        "layout": "same",
        "days": {d: {"heat": plist(heat), "cool": plist(cool)} for d in DAYS},
    }


def parse_hhmm(value: Any) -> time:
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    text = str(value).strip()
    parts = text.split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"Invalid time {value!r}; use HH:MM")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError(f"Invalid time {value!r}")
    return time(hour, minute)


def normalize_schedule(data: dict[str, Any], min_gap: float = 1.0) -> dict[str, Any]:
    """Validate and clean a schedule. Raises ValueError with a readable message."""
    layout = data.get("layout", "same")
    if layout not in LAYOUTS:
        raise ValueError(f"layout must be one of {', '.join(LAYOUTS)}")
    days_in = data.get("days")
    if not isinstance(days_in, dict):
        raise ValueError("days is required")
    out: dict[str, Any] = {"layout": layout, "days": {}}
    for day in DAYS:
        if day not in days_in:
            raise ValueError(f"Missing day {day}")
        out["days"][day] = {}
        for season in SEASONS:
            periods = days_in[day].get(season) if isinstance(days_in[day], dict) else None
            if not periods:
                raise ValueError(f"{day} {season}: at least one period is required")
            if len(periods) > MAX_PERIODS:
                raise ValueError(f"{day} {season}: at most {MAX_PERIODS} periods")
            clean = []
            for p in periods:
                start = parse_hhmm(p["start"])
                low, high = float(p["low"]), float(p["high"])
                if low > high:
                    low, high = high, low
                if high - low < min_gap:
                    raise ValueError(
                        f"{day} {season} {p.get('name') or start.strftime('%H:%M')}: "
                        f"high must be at least {min_gap:g}° above low"
                    )
                clean.append({
                    "name": str(p.get("name") or "").strip()[:20] or start.strftime("%H:%M"),
                    "start": start.strftime("%H:%M"),
                    "low": low,
                    "high": high,
                })
            clean.sort(key=lambda p: p["start"])
            starts = [p["start"] for p in clean]
            if len(set(starts)) != len(starts):
                raise ValueError(f"{day} {season}: two periods start at the same time")
            out["days"][day][season] = clean
    # make grouped days identical so the layout is truthful
    for group in LAYOUT_GROUPS[layout]:
        for day in group[1:]:
            out["days"][day] = deepcopy(out["days"][group[0]])
    return out


@dataclass(frozen=True)
class Resolution:
    name: str
    low: float
    high: float
    since: datetime
    next_at: datetime
    next_name: str
    next_low: float
    next_high: float


def _at(d: date, hhmm: str, tz) -> datetime:
    return datetime.combine(d, parse_hhmm(hhmm), tzinfo=tz)


def resolve(schedule: dict[str, Any], now: datetime, season: str) -> Resolution:
    """Active period at ``now`` (timezone-aware) and the next change."""
    tz = now.tzinfo
    days = schedule["days"]
    today = now.date()
    # Walk backwards (today, then previous days) for the most recent start.
    current = None
    for back in range(8):
        d = today - timedelta(days=back)
        periods = days[DAYS[d.weekday()]][season]
        starts = [(p, _at(d, p["start"], tz)) for p in periods]
        past = [(p, t) for p, t in starts if t <= now]
        if past:
            current = past[-1]
            break
    # Walk forwards for the next start strictly after now.
    nxt = None
    for ahead in range(8):
        d = today + timedelta(days=ahead)
        periods = days[DAYS[d.weekday()]][season]
        future = [(p, _at(d, p["start"], tz)) for p in periods if _at(d, p["start"], tz) > now]
        if future:
            nxt = future[0]
            break
    assert current is not None and nxt is not None  # every day has >= 1 period
    p, since = current
    n, next_at = nxt
    return Resolution(
        name=p["name"], low=p["low"], high=p["high"], since=since,
        next_at=next_at, next_name=n["name"], next_low=n["low"], next_high=n["high"],
    )
