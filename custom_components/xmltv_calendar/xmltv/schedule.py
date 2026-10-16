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
REFRESH_MODES = (REFRESH_MODE_INTERVAL, REFRESH_MODE_DAILY)

KEY_REFRESH_HOURS = "refresh_hours"
DEFAULT_REFRESH_HOURS = 24  # D-13 (Phase 1)
MIN_REFRESH_HOURS = 1
MAX_REFRESH_HOURS = 168

KEY_REFRESH_TIME = "refresh_time"  # "HH:MM" in the HA time zone

# How feed times without a UTC offset are read (D-14)
KEY_NAIVE_TIMEZONE = "naive_timezone"
NAIVE_TZ_UTC = "utc"
NAIVE_TZ_LOCAL = "local"
NAIVE_TIMEZONES = (NAIVE_TZ_UTC, NAIVE_TZ_LOCAL)

# Correction added to every programme time (D-15)
KEY_OFFSET_MINUTES = "offset_minutes"
DEFAULT_OFFSET_MINUTES = 0
MIN_OFFSET_MINUTES = -720
MAX_OFFSET_MINUTES = 720

# Failure backoff (D-10): one step per consecutive failure, the last step repeats
BACKOFF_STEPS = (
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(hours=1),
    timedelta(hours=3),
    timedelta(hours=6),
)
# A failure streak older than this is persistent (D-17, measured from the first failure of the streak)
PERSISTENT_FAILURE = timedelta(hours=24)

# update_interval must never be zero: Home Assistant treats a falsy interval as "no polling"
MIN_DELAY = timedelta(seconds=1)

# A coordinator timer may fire slightly before its target (Home Assistant truncates loop.time(), up to about 1 s
# early); a refresh that ends this close before its target stands for that target (CR-01)
EARLY_FIRE_TOLERANCE = timedelta(seconds=2)


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
    naive_timezone: str = NAIVE_TZ_UTC
    offset_minutes: int = DEFAULT_OFFSET_MINUTES

    @classmethod
    def from_mapping(cls, options: Mapping[str, object]) -> Self:
        """Tolerant reader: unknown or invalid values fall back to defaults; daily without a valid time is interval."""
        hours = _int_in_range(
            options.get(KEY_REFRESH_HOURS), DEFAULT_REFRESH_HOURS, MIN_REFRESH_HOURS, MAX_REFRESH_HOURS
        )
        refresh_time = normalize_time(options.get(KEY_REFRESH_TIME))
        naive = options.get(KEY_NAIVE_TIMEZONE)
        naive_timezone = naive if isinstance(naive, str) and naive in NAIVE_TIMEZONES else NAIVE_TZ_UTC
        offset = _int_in_range(
            options.get(KEY_OFFSET_MINUTES), DEFAULT_OFFSET_MINUTES, MIN_OFFSET_MINUTES, MAX_OFFSET_MINUTES
        )
        daily = options.get(KEY_REFRESH_MODE) == REFRESH_MODE_DAILY and refresh_time is not None
        return cls(
            refresh_mode=REFRESH_MODE_DAILY if daily else REFRESH_MODE_INTERVAL,
            refresh_hours=hours,
            refresh_time=refresh_time if daily else None,
            naive_timezone=naive_timezone,
            offset_minutes=offset,
        )

    def as_options(self) -> dict[str, object]:
        """Return the storage shape; `refresh_time` only when set. `from_mapping(o.as_options()) == o`."""
        options: dict[str, object] = {
            KEY_REFRESH_MODE: self.refresh_mode,
            KEY_REFRESH_HOURS: self.refresh_hours,
            KEY_NAIVE_TIMEZONE: self.naive_timezone,
            KEY_OFFSET_MINUTES: self.offset_minutes,
        }
        if self.refresh_time is not None:
            options[KEY_REFRESH_TIME] = self.refresh_time
        return options

    def schedule(self, tz: tzinfo) -> Schedule:
        """Return the schedule in `tz` (the HA time zone, read by the caller each time)."""
        if self.refresh_mode == REFRESH_MODE_DAILY and self.refresh_time is not None:
            return Schedule(interval=None, daily_at=time.fromisoformat(self.refresh_time), tz=tz)
        return Schedule(interval=timedelta(hours=self.refresh_hours), daily_at=None, tz=tz)


def _slot_on(day_offset: int, local: datetime, schedule: Schedule, daily_at: time) -> datetime:
    """Return the slot on the local date of `local` plus `day_offset` days, as UTC."""
    day = local.date() + timedelta(days=day_offset)
    return datetime.combine(day, daily_at, tzinfo=schedule.tz).astimezone(UTC)


def _daily_at(schedule: Schedule, name: str) -> time:
    if schedule.daily_at is None:
        msg = f"{name} needs a daily schedule"
        raise ValueError(msg)
    return schedule.daily_at


def last_slot(now: datetime, schedule: Schedule) -> datetime:
    """Most recent daily slot at or before `now`, in UTC."""
    daily_at = _daily_at(schedule, "last_slot")
    local = now.astimezone(schedule.tz)
    for day_offset in (0, -1, -2):
        slot = _slot_on(day_offset, local, schedule, daily_at)
        if slot <= now:
            return slot
    msg = "no daily slot within two days"  # pragma: no cover - unreachable for real time zones
    raise AssertionError(msg)


def next_slot(now: datetime, schedule: Schedule) -> datetime:
    """First daily slot strictly after `now`, in UTC."""
    daily_at = _daily_at(schedule, "next_slot")
    local = now.astimezone(schedule.tz)
    # Offset 2 covers a slot that a DST transition pushes back across `now`
    for day_offset in (0, 1, 2):
        slot = _slot_on(day_offset, local, schedule, daily_at)
        if slot > now:
            return slot
    msg = "no daily slot within two days"  # pragma: no cover - unreachable for real time zones
    raise AssertionError(msg)


def next_regular(now: datetime, schedule: Schedule) -> datetime:
    """Return the refresh after one at `now`: now + interval, or the next daily slot."""
    if schedule.interval is not None:
        return now.astimezone(UTC) + schedule.interval
    return next_slot(now, schedule)


def refresh_base(now: datetime, target: datetime) -> datetime:
    """
    Return the instant a refresh at `now` stands for, given the refresh `target` it was armed for.

    Late or on time: `now`. Early fire, at most `EARLY_FIRE_TOLERANCE` before the target: the target, so the slot or
    interval being served is not scheduled again. More than the tolerance early (e.g. a manual refresh): `now`, so the
    target is not consumed.
    """
    if now < target <= now + EARLY_FIRE_TOLERANCE:
        return target
    return now


def is_fresh(fetched_at: datetime, now: datetime, schedule: Schedule) -> bool:
    """
    Whether data fetched at `fetched_at` is still current at `now` (D-03, D-09).

    Interval: younger than the interval. Daily: fetched at or after the most recent slot, so a missed slot is stale.
    A fetch time in the future (clock went backwards) is never fresh.
    """
    if fetched_at > now:
        return False
    if schedule.interval is not None:
        return now - fetched_at < schedule.interval
    return fetched_at >= last_slot(now, schedule)


def fresh_until(fetched_at: datetime, now: datetime, schedule: Schedule) -> datetime:
    """Return when fresh data fetched at `fetched_at` turns stale: fetched_at + interval, or the next daily slot."""
    if schedule.interval is not None:
        return fetched_at.astimezone(UTC) + schedule.interval
    return next_slot(now, schedule)


def backoff_delay(failures: int, now: datetime, regular_next: datetime) -> timedelta:
    """
    Delay before the retry after `failures` consecutive failures (D-10).

    5 min, 15 min, 1 h, 3 h, 6 h, then 6 h; never past the next regular refresh and never below `MIN_DELAY`.
    A count below 1 counts as the first failure.
    """
    step = BACKOFF_STEPS[min(max(failures, 1), len(BACKOFF_STEPS)) - 1]
    return max(min(step, regular_next - now), MIN_DELAY)


def is_persistently_failing(failing_since: datetime | None, now: datetime) -> bool:
    """Return whether the current failure streak began more than `PERSISTENT_FAILURE` before `now` (D-17)."""
    return failing_since is not None and now - failing_since > PERSISTENT_FAILURE
