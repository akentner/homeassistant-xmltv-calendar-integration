"""XMLTV timestamp parsing."""

import re
from datetime import UTC, datetime, timedelta, timezone

# Full form only: `YYYYMMDDhhmmss +HHMM`. Plan 01-02 adds the shortened and offset-less variants.
_TS_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2}) ([+-])(\d{2})(\d{2})$")
_TZ_CACHE: dict[int, timezone] = {0: UTC}


def _tz(minutes: int) -> timezone:
    """Return a cached fixed-offset timezone."""
    if (tz := _TZ_CACHE.get(minutes)) is None:
        tz = _TZ_CACHE[minutes] = timezone(timedelta(minutes=minutes))
    return tz


def parse_xmltv_time(value: str | None) -> datetime | None:
    """Return an aware datetime, or None if the value is not a supported XMLTV timestamp."""
    if not value or (match := _TS_RE.match(value.strip())) is None:
        return None
    year, month, day, hour, minute, second, sign, off_h, off_m = match.groups()
    offset = int(off_h) * 60 + int(off_m)
    try:
        return datetime(
            int(year),
            int(month),
            int(day),
            int(hour),
            int(minute),
            int(second),
            tzinfo=_tz(-offset if sign == "-" else offset),
        )
    except ValueError:
        return None
