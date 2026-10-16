"""
Refresh schedule maths and the stored source-options contract (SRC-05, D-02, D-06).

Pure stdlib: every function takes `now` as an aware datetime and returns aware UTC datetimes. Arithmetic runs on
UTC values only; a wall-clock time is turned into an instant once, through `datetime.combine(..., tzinfo=tz)`.

The KEY_* names and their values are persisted in every source entry's options. Renaming them needs an
async_migrate_entry with a VERSION bump.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta, tzinfo
from typing import TYPE_CHECKING, Self

from .settings import normalize_time

if TYPE_CHECKING:
    from collections.abc import Mapping

KEY_REFRESH_MODE = "refresh_mode"
REFRESH_MODE_INTERVAL = "interval"
REFRESH_MODE_DAILY = "daily"

KEY_REFRESH_HOURS = "refresh_hours"
DEFAULT_REFRESH_HOURS = 24  # D-13 (Phase 1)
MIN_REFRESH_HOURS = 1
MAX_REFRESH_HOURS = 168

KEY_REFRESH_TIME = "refresh_time"  # "HH:MM" in the HA time zone

# update_interval must never be zero: Home Assistant treats a falsy interval as "no polling"
MIN_DELAY = timedelta(seconds=1)


@dataclass(frozen=True, slots=True)
class Schedule:
    """Either every `interval`, or once a day at `daily_at` wall-clock time in `tz`."""

    interval: timedelta | None
    daily_at: time | None
    tz: tzinfo


def _int_in_range(value: object, default: int, low: int, high: int) -> int:
    """Read an int (or an integral float) and clamp it; anything else, bool included, is `default`."""
    if isinstance(value, bool):
        return default
    if isinstance(value, float):
        if not value.is_integer():
            return default
        value = int(value)
    if not isinstance(value, int):
        return default
    return max(low, min(high, value))


@dataclass(frozen=True, slots=True)
class SourceOptions:
    """Validated source options; `from_mapping` accepts anything a stored entry may hold."""

    refresh_mode: str = REFRESH_MODE_INTERVAL
    refresh_hours: int = DEFAULT_REFRESH_HOURS
    refresh_time: str | None = None

    @classmethod
    def from_mapping(cls, options: Mapping[str, object]) -> Self:
        """Tolerant reader: unknown or invalid values fall back to defaults; daily without a valid time is interval."""
        hours = _int_in_range(
            options.get(KEY_REFRESH_HOURS), DEFAULT_REFRESH_HOURS, MIN_REFRESH_HOURS, MAX_REFRESH_HOURS
        )
        refresh_time = normalize_time(options.get(KEY_REFRESH_TIME))
        if options.get(KEY_REFRESH_MODE) == REFRESH_MODE_DAILY and refresh_time is not None:
            return cls(refresh_mode=REFRESH_MODE_DAILY, refresh_hours=hours, refresh_time=refresh_time)
        return cls(refresh_mode=REFRESH_MODE_INTERVAL, refresh_hours=hours)

    def schedule(self, tz: tzinfo) -> Schedule:
        """Return the schedule in `tz` (the HA time zone, read by the caller each time)."""
        if self.refresh_mode == REFRESH_MODE_DAILY and self.refresh_time is not None:
            return Schedule(interval=None, daily_at=time.fromisoformat(self.refresh_time), tz=tz)
        return Schedule(interval=timedelta(hours=self.refresh_hours), daily_at=None, tz=tz)


def _slot_on(day_offset: int, local: datetime, schedule: Schedule, daily_at: time) -> datetime:
    """Return the slot on the local date of `local` plus `day_offset` days, as UTC."""
    day = local.date() + timedelta(days=day_offset)
    return datetime.combine(day, daily_at, tzinfo=schedule.tz).astimezone(UTC)


def next_slot(now: datetime, schedule: Schedule) -> datetime:
    """First daily slot strictly after `now`, in UTC."""
    if schedule.daily_at is None:
        msg = "next_slot needs a daily schedule"
        raise ValueError(msg)
    local = now.astimezone(schedule.tz)
    # Offset 2 covers a slot that a DST transition pushes back across `now`
    for day_offset in (0, 1, 2):
        slot = _slot_on(day_offset, local, schedule, schedule.daily_at)
        if slot > now:
            return slot
    msg = "no daily slot within two days"  # pragma: no cover - unreachable for real time zones
    raise AssertionError(msg)


def next_regular(now: datetime, schedule: Schedule) -> datetime:
    """Return the refresh after one at `now`: now + interval, or the next daily slot."""
    if schedule.interval is not None:
        return now.astimezone(UTC) + schedule.interval
    return next_slot(now, schedule)
