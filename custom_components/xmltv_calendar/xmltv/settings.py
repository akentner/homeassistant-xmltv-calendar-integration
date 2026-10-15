"""
Stored calendar subentry contract: key names, value vocabularies and defaults (D-06).

These names are persisted in every calendar subentry and double as flow field names and selector option values.
Renaming them needs an async_migrate_entry with a VERSION bump.
"""

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

FIELD_TITLE = "title"
FIELD_SUBTITLE = "subtitle"
FIELD_DESCRIPTION = "description"
FIELD_CATEGORY = "category"
MATCH_FIELDS = (FIELD_TITLE, FIELD_SUBTITLE, FIELD_DESCRIPTION, FIELD_CATEGORY)
DEFAULT_MATCH_FIELDS = (FIELD_TITLE, FIELD_SUBTITLE)  # D-05

# Same values as homeassistant.const.WEEKDAYS; index == datetime.weekday()
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

DEFAULT_TITLE_TEMPLATE = "{channel}: {title}"  # D-20
