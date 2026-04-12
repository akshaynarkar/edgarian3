from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any


def to_date(val: Any) -> date | None:
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        if val.tzinfo is None:
            val = val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc).date()
    if isinstance(val, str):
        cleaned = val.strip()
        if not cleaned:
            return None
        try:
            return date.fromisoformat(cleaned[:10])
        except ValueError:
            return None
    return None


def within_days(dt: datetime | date | None, days: int) -> bool:
    if dt is None:
        return False
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)
    delta = now_utc - dt.astimezone(timezone.utc)
    return delta.days <= days


def in_window(dt: datetime | date | None, start: date | datetime | None, end: date | datetime | None) -> bool:
    if dt is None:
        return False

    def _normalize(value: date | datetime | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    current = _normalize(dt)
    window_start = _normalize(start)
    window_end = _normalize(end)
    if current is None:
        return False
    if window_start is not None and current < window_start:
        return False
    if window_end is not None and current > window_end:
        return False
    return True
