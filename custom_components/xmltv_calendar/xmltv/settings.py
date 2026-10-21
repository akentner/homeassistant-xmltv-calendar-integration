"""
Stored calendar subentry contract: key names, value vocabularies and defaults (D-06).

These names are persisted in every calendar subentry and double as flow field names and selector option values.
Renaming them needs an async_migrate_entry with a VERSION bump.
"""

import math
import re
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

# Phase 1 keys (values unchanged)
KEY_CHANNELS = "channels"
KEY_CHANNEL_REGEX = "channel_regex"
KEY_INCLUDE = "include"
KEY_EXCLUDE = "exclude"

# Phase 2 keys, flat beside the Phase 1 keys (02-02 Task 2 decision "flat")
KEY_INCLUDE_FIELDS = "include_fields"
KEY_EXCLUDE_FIELDS = "exclude_fields"
KEY_CASE_SENSITIVE = "case_sensitive"
KEY_TIME_FROM = "time_from"
KEY_TIME_TO = "time_to"
KEY_WEEKDAYS = "weekdays"
KEY_MIN_DURATION = "min_duration"
KEY_MAX_DURATION = "max_duration"
KEY_TITLE_TEMPLATE = "title_template"
KEY_DESCRIPTION_TEMPLATE = "description_template"

# Phase 4 key, flat beside the others (D-14): whole days an ended match stays in the calendar after the feed drops it
KEY_RETENTION_DAYS = "retention_days"
DEFAULT_RETENTION_DAYS = 1  # D-15: today's behaviour
MAX_RETENTION_DAYS = 7

FIELD_TITLE = "title"
FIELD_SUBTITLE = "subtitle"
FIELD_DESCRIPTION = "description"
FIELD_CATEGORY = "category"
MATCH_FIELDS = (FIELD_TITLE, FIELD_SUBTITLE, FIELD_DESCRIPTION, FIELD_CATEGORY)
DEFAULT_MATCH_FIELDS = (FIELD_TITLE, FIELD_SUBTITLE)  # D-05

# Same values as homeassistant.const.WEEKDAYS; index == datetime.weekday()
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

DEFAULT_TITLE_TEMPLATE = "{channel}: {title}"  # D-20

# Defaults of the advanced keys (the ten Phase 2 keys, then retention_days), in storage shape; also used for missing,
# None or invalid values. Key order matters: retention_days stays last
ADVANCED_DEFAULTS: Mapping[str, Any] = MappingProxyType(
    {
        KEY_INCLUDE_FIELDS: list(DEFAULT_MATCH_FIELDS),
        KEY_EXCLUDE_FIELDS: list(DEFAULT_MATCH_FIELDS),
        KEY_CASE_SENSITIVE: False,
        KEY_TIME_FROM: None,
        KEY_TIME_TO: None,
        KEY_WEEKDAYS: [],
        KEY_MIN_DURATION: None,
        KEY_MAX_DURATION: None,
        KEY_TITLE_TEMPLATE: DEFAULT_TITLE_TEMPLATE,
        KEY_DESCRIPTION_TEMPLATE: "",
        KEY_RETENTION_DAYS: DEFAULT_RETENTION_DAYS,
    }
)

_TIME_FORMAT = re.compile(r"([01]\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?", re.ASCII)


def normalize_time(value: object) -> str | None:
    """
    Return an "HH:MM" or "HH:MM:SS" string as "HH:MM" (the TimeSelector sends seconds); anything else is None.

    Checked by pattern, not time.fromisoformat, which also accepts "24:00", bare hours and UTC offsets.
    """
    if not isinstance(value, str) or (match := _TIME_FORMAT.fullmatch(value)) is None:
        return None
    return f"{match[1]}:{match[2]}"


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _channels(value: object) -> list[str]:
    """Read selected channel IDs like Phase 1 did: one string is one ID, empty items are skipped."""
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (set, frozenset)):
        return sorted(str(item) for item in value if item)
    if isinstance(value, (list, tuple)):
        return list(dict.fromkeys(str(item) for item in value if item))
    return []


def _choices(value: object, vocabulary: tuple[str, ...]) -> list[str]:
    """Keep known names of a list, deduplicated and in vocabulary order; a non-list reads as empty."""
    if not isinstance(value, (list, tuple)):
        return []
    chosen = {item for item in value if isinstance(item, str)}
    return [name for name in vocabulary if name in chosen]


def _fields(value: object) -> list[str]:
    return _choices(value, MATCH_FIELDS) or list(DEFAULT_MATCH_FIELDS)


def _minutes(value: object) -> int | None:
    """Return a non-negative whole number of minutes; bool, negative, non-finite and non-numeric values are None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return int(value) if value >= 0 else None


def _retention_days(value: object) -> int:
    """Return whole retention days clamped to 0..7; bool, non-numeric and non-finite values read as the default."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return DEFAULT_RETENTION_DAYS
    if isinstance(value, float) and not math.isfinite(value):
        return DEFAULT_RETENTION_DAYS
    return min(max(int(value), 0), MAX_RETENTION_DAYS)


def with_defaults(data: Mapping[str, object]) -> dict[str, Any]:
    """
    Return all stored keys of a calendar subentry in storage shape, with defaults for missing or invalid values.

    Wrong types fall back to the default, unknown field and weekday names are dropped, lists are deduplicated and
    ordered, unknown keys are not returned. It never raises, so hand-edited or Phase 1 data keeps working (D-06).
    """
    title_template = _text(data.get(KEY_TITLE_TEMPLATE))
    description_template = _text(data.get(KEY_DESCRIPTION_TEMPLATE))
    case_sensitive = data.get(KEY_CASE_SENSITIVE)
    return {
        KEY_CHANNELS: _channels(data.get(KEY_CHANNELS)),
        KEY_CHANNEL_REGEX: _text(data.get(KEY_CHANNEL_REGEX)),
        KEY_INCLUDE: _text(data.get(KEY_INCLUDE)),
        KEY_EXCLUDE: _text(data.get(KEY_EXCLUDE)),
        KEY_INCLUDE_FIELDS: _fields(data.get(KEY_INCLUDE_FIELDS)),
        KEY_EXCLUDE_FIELDS: _fields(data.get(KEY_EXCLUDE_FIELDS)),
        KEY_CASE_SENSITIVE: case_sensitive if isinstance(case_sensitive, bool) else False,
        KEY_TIME_FROM: normalize_time(data.get(KEY_TIME_FROM)),
        KEY_TIME_TO: normalize_time(data.get(KEY_TIME_TO)),
        KEY_WEEKDAYS: _choices(data.get(KEY_WEEKDAYS), WEEKDAYS),
        KEY_MIN_DURATION: _minutes(data.get(KEY_MIN_DURATION)),
        KEY_MAX_DURATION: _minutes(data.get(KEY_MAX_DURATION)),
        KEY_TITLE_TEMPLATE: title_template if title_template.strip() else DEFAULT_TITLE_TEMPLATE,
        KEY_DESCRIPTION_TEMPLATE: description_template if description_template.strip() else "",
        KEY_RETENTION_DAYS: _retention_days(data.get(KEY_RETENTION_DAYS)),
    }


def has_advanced(data: Mapping[str, object]) -> bool:
    """Return True when any advanced setting differs from its default; drives the unstored "Advanced" toggle (D-03)."""
    settings = with_defaults(data)
    return any(settings[key] != default for key, default in ADVANCED_DEFAULTS.items())
