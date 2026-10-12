"""XMLTV timestamp parsing (EVT-05)."""

import re
from datetime import UTC, datetime, timedelta, timezone

# `YYYYMMDD[hhmm[ss]]`, then an optional numeric offset (`+HHMM`, `+HH:MM`, with or without a space) or an alpha zone.
# Anchored with bounded quantifiers only, so hostile input cannot cause backtracking blowups (T-01-04).
_TS_RE = re.compile(
    r"^\s*(\d{4})(\d{2})(\d{2})(?:(\d{2})(\d{2})(\d{2})?)?\s*"
    r"(?:([+-])(\d{2}):?(\d{2})|(Z|UTC|GMT|[A-Z]{3,4}))?\s*$"
)
# Alpha zones seen in real feeds, as minutes east of UTC; anything else is rejected
_ALPHA = {"Z": 0, "UTC": 0, "GMT": 0, "BST": 60, "CET": 60, "CEST": 120, "EET": 120, "EEST": 180}
_TZ_CACHE: dict[int, timezone] = {0: UTC}


def _tz(minutes: int) -> timezone:
    """Return a cached fixed-offset timezone."""
    if (tz := _TZ_CACHE.get(minutes)) is None:
        tz = _TZ_CACHE[minutes] = timezone(timedelta(minutes=minutes))
    return tz


def parse_xmltv_time(value: str | None) -> datetime | None:
    """Return an aware datetime, or None if the value is not a valid XMLTV timestamp."""
    if not value or (match := _TS_RE.match(value)) is None:
        return None
    year, month, day, hour, minute, second, sign, off_h, off_m, alpha = match.groups()
    if sign:
        offset = int(off_h) * 60 + int(off_m)
        tz = _tz(-offset if sign == "-" else offset)
    elif alpha:
        if alpha not in _ALPHA:
            return None
        tz = _tz(_ALPHA[alpha])
    else:
        tz = UTC  # D-14: no offset means UTC
    try:
        return datetime(int(year), int(month), int(day), int(hour or 0), int(minute or 0), int(second or 0), tzinfo=tz)
    except ValueError:
        return None
