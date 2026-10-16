"""XMLTV timestamp parsing (EVT-05)."""

import re
from datetime import UTC, datetime, timedelta, timezone, tzinfo

# `YYYYMMDD[hhmm[ss]]`, then an optional numeric offset (`+HHMM`, `+HH:MM`, with or without a space) or an alpha zone.
# Anchored with bounded quantifiers only, so hostile input cannot cause backtracking blowups (T-01-04).
_TS_RE = re.compile(
    r"^\s*(\d{4})(\d{2})(\d{2})(?:(\d{2})(\d{2})(\d{2})?)?\s*"
    r"(?:([+-])(\d{2}):?(\d{2})|(Z|UTC|GMT|[A-Z]{3,4}))?\s*$"
)
# Alpha zones seen in real feeds, as minutes east of UTC; anything else is rejected
_ALPHA = {"Z": 0, "UTC": 0, "GMT": 0, "BST": 60, "CET": 60, "CEST": 120, "EET": 120, "EEST": 180}
_TZ_CACHE: dict[int, timezone] = {0: UTC}
# Real-world offsets lie within -12..+14 h; anything beyond 18 h is broken data (CR-01)
_MAX_OFFSET_MINUTES = 18 * 60
# Year window keeping start + default_duration (D-12), astimezone(UTC) in normalize and
# dt_util.as_local in the calendar inside datetime's range (CR-01)
_MIN_YEAR = 1900
_MAX_YEAR = 2200


def _tz(minutes: int) -> timezone:
    """Return a cached fixed-offset timezone."""
    if (tz := _TZ_CACHE.get(minutes)) is None:
        tz = _TZ_CACHE[minutes] = timezone(timedelta(minutes=minutes))
    return tz


def _fixed(offset: timedelta) -> timezone:
    """Return the fixed-offset timezone for a UTC offset, cached when it is a whole number of minutes."""
    minutes, rest = divmod(offset, timedelta(minutes=1))
    return timezone(offset) if rest else _tz(minutes)


def parse_xmltv_time(value: str | None, naive_tz: tzinfo = UTC) -> datetime | None:
    """
    Return an aware datetime with a fixed-offset tzinfo, or None if the value is not a valid XMLTV timestamp.

    A timestamp without numeric offset or alpha zone is read in `naive_tz` (UTC by default). A DST-aware zone resolves
    gap and fold wall times with fold=0 (the offset before the transition), and the result is re-attached to that
    fixed offset, so no zone object leaves the parser and datetime arithmetic stays absolute.

    None is returned for unmatched input, unknown alpha zones, offset minutes >= 60, offsets beyond 18 hours,
    written years outside 1900..2200, and any invalid date or time field. This function never raises.
    """
    if not value or (match := _TS_RE.match(value)) is None:
        return None
    year, month, day, hour, minute, second, sign, off_h, off_m, alpha = match.groups()
    if not _MIN_YEAR <= int(year) <= _MAX_YEAR:
        return None
    if sign:
        offset = int(off_h) * 60 + int(off_m)
        if int(off_m) >= 60 or offset > _MAX_OFFSET_MINUTES:  # noqa: PLR2004
            return None
        tz = _tz(-offset if sign == "-" else offset)
    elif alpha:
        if alpha not in _ALPHA:
            return None
        tz = _tz(_ALPHA[alpha])
    else:
        tz = naive_tz  # D-14, SRC-10: no offset means UTC, or the source's configured zone
    try:
        result = datetime(
            int(year), int(month), int(day), int(hour or 0), int(minute or 0), int(second or 0), tzinfo=tz
        )
        return result if isinstance(tz, timezone) else _pin_offset(result)
    except ValueError, OverflowError:
        return None


def _pin_offset(value: datetime) -> datetime | None:
    """Re-attach a datetime in a zone (e.g. ZoneInfo) to its fixed UTC offset at that instant."""
    offset = value.utcoffset()
    return None if offset is None else value.replace(tzinfo=_fixed(offset))
