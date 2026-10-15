"""Config flow: source entries (menu -> source step -> name) and calendar subentries."""

from pathlib import PurePath
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
    TimeSelector,
)
from homeassistant.util import dt as dt_util
from yarl import URL

from .const import (
    CONF_ADVANCED,
    CONF_CASE_SENSITIVE,
    CONF_CHANNEL_REGEX,
    CONF_CHANNELS,
    CONF_DESCRIPTION_TEMPLATE,
    CONF_EXCLUDE,
    CONF_EXCLUDE_FIELDS,
    CONF_INCLUDE,
    CONF_INCLUDE_FIELDS,
    CONF_MAX_DURATION,
    CONF_MIN_DURATION,
    CONF_NAME,
    CONF_PATH,
    CONF_REFRESH_HOURS,
    CONF_SOURCE_TYPE,
    CONF_TIME_FROM,
    CONF_TIME_TO,
    CONF_TITLE_TEMPLATE,
    CONF_URL,
    CONF_WEEKDAYS,
    DEFAULT_REFRESH_HOURS,
    DOMAIN,
    MAX_DURATION_MINUTES,
    MAX_REFRESH_HOURS,
    MIN_REFRESH_HOURS,
    SOURCE_TYPE_FILE,
    SOURCE_TYPE_URL,
    SUBENTRY_TYPE_CALENDAR,
)
from .source import (
    FileMissingError,
    InvalidFeedError,
    InvalidUrlError,
    PathNotAllowedError,
    SourceError,
    async_probe_url,
    check_file,
    normalize_url,
    probe_file,
    source_unique_id,
)
from .xmltv.filter import first_invalid_pattern
from .xmltv.preview import build_preview
from .xmltv.render import DESCRIPTION_FIELDS, TITLE_FIELDS, TemplateError, compile_template
from .xmltv.settings import (
    ADVANCED_DEFAULTS,
    DEFAULT_TITLE_TEMPLATE,
    MATCH_FIELDS,
    WEEKDAYS,
    has_advanced,
    normalize_time,
    with_defaults,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .data import XmltvConfigEntry


def _refresh_selector() -> NumberSelector:
    """Return the refresh interval selector shared by every source step (D-13: 1 to 168 h)."""
    return NumberSelector(
        NumberSelectorConfig(
            min=MIN_REFRESH_HOURS,
            max=MAX_REFRESH_HOURS,
            step=1,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="h",
        )
    )


class XmltvConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add an XMLTV source; calendars are added afterwards as subentries."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the pending entry data."""
        self._data: dict[str, Any] = {}
        self._options: dict[str, Any] = {}
        self._suggested_name = ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:  # noqa: ARG002
        """Let the user choose the source type."""
        return self.async_show_menu(step_id="user", menu_options=[SOURCE_TYPE_URL, SOURCE_TYPE_FILE])

    async def async_step_url(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the feed URL and the refresh interval; reject bad URLs, duplicates and non-feeds."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                url = normalize_url(str(user_input[CONF_URL]))
            except InvalidUrlError:
                errors[CONF_URL] = "invalid_url"
            else:
                await self.async_set_unique_id(source_unique_id(SOURCE_TYPE_URL, url))
                self._abort_if_unique_id_configured()
                try:
                    await async_probe_url(self.hass, url)
                except InvalidFeedError:
                    errors["base"] = "invalid_feed"
                except SourceError:
                    errors["base"] = "cannot_connect"
                else:
                    self._data = {CONF_SOURCE_TYPE: SOURCE_TYPE_URL, CONF_URL: url}
                    self._options = {CONF_REFRESH_HOURS: int(user_input[CONF_REFRESH_HOURS])}
                    self._suggested_name = URL(url).host or url
                    return await self.async_step_name()

        schema = vol.Schema(
            {
                vol.Required(CONF_URL): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
                vol.Required(CONF_REFRESH_HOURS, default=DEFAULT_REFRESH_HOURS): _refresh_selector(),
            }
        )
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="url", data_schema=schema, errors=errors)

    async def async_step_file(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the local file path and the refresh interval; only allowed directories can be read."""
        errors: dict[str, str] = {}
        if user_input is not None:
            path = str(user_input[CONF_PATH]).strip()
            try:
                real_path = await self.hass.async_add_executor_job(check_file, self.hass.config, path)
            except PathNotAllowedError:
                errors[CONF_PATH] = "path_not_allowed"
            except FileMissingError:
                errors[CONF_PATH] = "file_not_found"
            else:
                await self.async_set_unique_id(source_unique_id(SOURCE_TYPE_FILE, real_path))
                self._abort_if_unique_id_configured()
                try:
                    await self.hass.async_add_executor_job(probe_file, real_path)
                except InvalidFeedError:
                    errors["base"] = "invalid_feed"
                except SourceError:
                    errors[CONF_PATH] = "file_not_found"
                else:
                    self._data = {CONF_SOURCE_TYPE: SOURCE_TYPE_FILE, CONF_PATH: real_path}
                    self._options = {CONF_REFRESH_HOURS: int(user_input[CONF_REFRESH_HOURS])}
                    self._suggested_name = PurePath(real_path).name
                    return await self.async_step_name()

        schema = vol.Schema(
            {
                vol.Required(CONF_PATH): TextSelector(),
                vol.Required(CONF_REFRESH_HOURS, default=DEFAULT_REFRESH_HOURS): _refresh_selector(),
            }
        )
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="file", data_schema=schema, errors=errors)

    async def async_step_name(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the entry name, pre-filled from the source (D-09); shared by every source type."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = str(user_input[CONF_NAME]).strip()
            if name:
                return self.async_create_entry(title=name, data=self._data, options=self._options)
            errors[CONF_NAME] = "name_required"

        schema = self.add_suggested_values_to_schema(
            vol.Schema({vol.Required(CONF_NAME): str}),
            user_input if user_input is not None else {CONF_NAME: self._suggested_name},
        )
        return self.async_show_form(step_id="name", data_schema=schema, errors=errors)

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:  # noqa: ARG003
        """Return the subentry types this integration supports."""
        return {SUBENTRY_TYPE_CALENDAR: CalendarSubentryFlow}


# Free-text filter fields: one pattern per line, blank lines ignored (D-05)
_PATTERN_FIELDS = (CONF_CHANNEL_REGEX, CONF_INCLUDE, CONF_EXCLUDE)

# Placeholder names shown in the advanced step help texts; a literal {channel} in a translation is an ICU placeholder
_TITLE_FIELD_NAMES = "{channel}, {title}, {subtitle}, {episode}, {category}, {channel_id}"
_ADVANCED_PLACEHOLDERS = {
    "title_fields": _TITLE_FIELD_NAMES,
    "description_fields": _TITLE_FIELD_NAMES + ", {description}",
    "default_title": DEFAULT_TITLE_TEMPLATE,
}


def _duration_selector() -> NumberSelector:
    """Return the minutes selector of the duration range (0 to one week)."""
    return NumberSelector(
        NumberSelectorConfig(
            min=0, max=MAX_DURATION_MINUTES, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="min"
        )
    )


def _list_selector(options: tuple[str, ...], *, translation_key: str) -> SelectSelector:
    """Return a multi-select over a fixed vocabulary with translated option labels."""
    return SelectSelector(
        SelectSelectorConfig(
            options=list(options), multiple=True, mode=SelectSelectorMode.LIST, translation_key=translation_key
        )
    )


def _advanced_schema() -> vol.Schema:
    """Return the advanced step schema; no default=, so every field stays clearable (Pattern 6)."""
    return vol.Schema(
        {
            vol.Optional(CONF_INCLUDE_FIELDS): _list_selector(MATCH_FIELDS, translation_key="match_field"),
            vol.Optional(CONF_EXCLUDE_FIELDS): _list_selector(MATCH_FIELDS, translation_key="match_field"),
            vol.Optional(CONF_CASE_SENSITIVE): BooleanSelector(),
            vol.Optional(CONF_TIME_FROM): TimeSelector(),
            vol.Optional(CONF_TIME_TO): TimeSelector(),
            vol.Optional(CONF_WEEKDAYS): _list_selector(WEEKDAYS, translation_key="weekday"),
            vol.Optional(CONF_MIN_DURATION): _duration_selector(),
            vol.Optional(CONF_MAX_DURATION): _duration_selector(),
            vol.Optional(CONF_TITLE_TEMPLATE): TextSelector(),
            vol.Optional(CONF_DESCRIPTION_TEMPLATE): TextSelector(TextSelectorConfig(multiline=True)),
        }
    )


def _advanced_values(user_input: dict[str, Any]) -> dict[str, Any]:
    """
    Build the advanced settings fresh from a submitted form; a missing key means the field was cleared (D-20).

    Never merged over the previous values, or a cleared optional field would come back (Pattern 6).
    """
    minimum = user_input.get(CONF_MIN_DURATION)
    maximum = user_input.get(CONF_MAX_DURATION)
    title_template = str(user_input.get(CONF_TITLE_TEMPLATE, "")).strip()
    return {
        CONF_INCLUDE_FIELDS: list(user_input.get(CONF_INCLUDE_FIELDS, [])),
        CONF_EXCLUDE_FIELDS: list(user_input.get(CONF_EXCLUDE_FIELDS, [])),
        CONF_CASE_SENSITIVE: bool(user_input.get(CONF_CASE_SENSITIVE, False)),
        # The TimeSelector sends "HH:MM:SS"; stored and compared as "HH:MM" (Pitfall 11)
        CONF_TIME_FROM: normalize_time(user_input.get(CONF_TIME_FROM)),
        CONF_TIME_TO: normalize_time(user_input.get(CONF_TIME_TO)),
        CONF_WEEKDAYS: list(user_input.get(CONF_WEEKDAYS, [])),
        # The NumberSelector sends float; stored as whole minutes
        CONF_MIN_DURATION: int(minimum) if minimum is not None else None,
        CONF_MAX_DURATION: int(maximum) if maximum is not None else None,
        CONF_TITLE_TEMPLATE: title_template or DEFAULT_TITLE_TEMPLATE,
        CONF_DESCRIPTION_TEMPLATE: str(user_input.get(CONF_DESCRIPTION_TEMPLATE, "")),
    }


def _advanced_errors(values: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    """
    Return the form errors and their placeholders for built advanced values, all checked in one pass.

    Template errors use their own template_error placeholder, never the regex pattern/error ones (Pitfall 12).
    """
    errors: dict[str, str] = {}
    placeholders: dict[str, str] = {}
    # A6: an empty selection is rejected instead of silently meaning the default fields
    for field in (CONF_INCLUDE_FIELDS, CONF_EXCLUDE_FIELDS):
        if not values[field]:
            errors[field] = "fields_required"
    # D-12: both or neither; compared after normalization, so "22:00" equals "22:00:00" (Pitfall 11)
    time_from, time_to = values[CONF_TIME_FROM], values[CONF_TIME_TO]
    if (time_from is None) != (time_to is None):
        errors[CONF_TIME_TO if time_to is None else CONF_TIME_FROM] = "time_incomplete"
    elif time_from is not None and time_from == time_to:
        errors[CONF_TIME_TO] = "time_equal"
    # D-13: inclusive bounds, so min == max is a valid exact length
    minimum, maximum = values[CONF_MIN_DURATION], values[CONF_MAX_DURATION]
    if minimum is not None and maximum is not None and minimum > maximum:
        errors[CONF_MAX_DURATION] = "duration_order"
    # D-21: only allowed plain placeholders; a blank description template means the default description
    templates = [(CONF_TITLE_TEMPLATE, TITLE_FIELDS)]
    if values[CONF_DESCRIPTION_TEMPLATE].strip():
        templates.append((CONF_DESCRIPTION_TEMPLATE, DESCRIPTION_FIELDS))
    for field, allowed in templates:
        try:
            compile_template(values[field], allowed)
        except TemplateError as err:
            errors[field] = err.reason
            placeholders.setdefault("template_error", err.detail)
    return errors, placeholders


def _advanced_suggestions(pending: dict[str, Any]) -> dict[str, Any]:
    """Return the pending advanced values as form suggestions; times in the TimeSelector's "HH:MM:SS" form."""
    suggestions = {key: pending[key] for key in ADVANCED_DEFAULTS if pending.get(key) is not None}
    for key in (CONF_TIME_FROM, CONF_TIME_TO):
        if key in suggestions:
            suggestions[key] = f"{suggestions[key]}:00"
    return suggestions


class CalendarSubentryFlow(ConfigSubentryFlow):
    """Add or edit a calendar of a loaded source: basic form -> preview -> save | back (D-01, D-19)."""

    def __init__(self) -> None:
        """Initialize the pending calendar values; loaded on first use, they survive Back (D-15)."""
        self._pending: dict[str, Any] | None = None
        # Last submitted state of the "Advanced options" checkbox within this flow; never stored (D-01, D-03)
        self._show_advanced = False

    def _load_pending(self) -> dict[str, Any]:
        """Return the pending values: defaults for a new calendar, the stored calendar for an edit (D-06)."""
        if self._pending is None:
            if self.source == SOURCE_USER:
                self._pending = with_defaults({})
            else:
                subentry = self._get_reconfigure_subentry()
                self._pending = with_defaults(dict(subentry.data))
                self._pending[CONF_NAME] = subentry.title
            # D-03: starts checked when any advanced value differs from its default; runs once, so Back and
            # re-submits keep the user's own choice
            self._show_advanced = has_advanced(self._pending)
        return self._pending

    def _calendar_data(self) -> dict[str, Any]:
        """Return the full stored key set from the pending values; the name is the subentry title (D-06)."""
        return with_defaults(self._load_pending())

    async def async_step_basic(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Ask for name, channels (sorted IDs, D-03), channel regex, include and exclude (D-02, D-05)."""
        entry: XmltvConfigEntry = self._get_entry()
        if entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="source_not_loaded")
        pending = self._load_pending()

        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        if user_input is not None:
            name = str(user_input[CONF_NAME]).strip()
            if not name:
                errors[CONF_NAME] = "name_required"
            # Nothing that fails to compile or exceeds the caps is ever stored (FLT-07, T-01-23)
            for field in _PATTERN_FIELDS:
                # D-08: include/exclude compile with the calendar's case flag; the channel regex always ignores case
                case_sensitive = field != CONF_CHANNEL_REGEX and pending[CONF_CASE_SENSITIVE]
                text = str(user_input.get(field, ""))
                if (bad := first_invalid_pattern(text, case_sensitive=case_sensitive)) is not None:
                    errors[field] = "invalid_regex"
                    placeholders.setdefault("pattern", bad.pattern)
                    placeholders.setdefault("error", bad.message)
            if not errors:
                # A missing key means the field was cleared; keys outside this form keep their pending values
                pending.update({CONF_NAME: name, CONF_CHANNELS: list(user_input.get(CONF_CHANNELS, []))})
                pending.update({field: str(user_input.get(field, "")) for field in _PATTERN_FIELDS})
                self._show_advanced = bool(user_input.get(CONF_ADVANCED, False))
                if self._show_advanced:
                    return await self.async_step_advanced()
                return await self.async_step_preview()

        # Stored IDs missing from the feed stay selectable, so an edit can be saved unchanged (Phase 1 D-04)
        channel_ids = sorted(set(entry.runtime_data.coordinator.data.channels) | set(pending[CONF_CHANNELS]))
        # No default=: optional fields must stay clearable; values come back as suggested values (Pattern 6)
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Optional(CONF_CHANNELS): SelectSelector(
                    SelectSelectorConfig(
                        options=channel_ids,
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                        sort=True,
                    )
                ),
                **{vol.Optional(field): TextSelector(TextSelectorConfig(multiline=True)) for field in _PATTERN_FIELDS},
                vol.Optional(CONF_ADVANCED, default=self._show_advanced): BooleanSelector(),
            }
        )
        # After an error the form shows exactly what was submitted, so a cleared field stays cleared (WR-01)
        suggestions = user_input if user_input is not None else pending
        schema = self.add_suggested_values_to_schema(schema, suggestions)
        return self.async_show_form(
            step_id="basic", data_schema=schema, errors=errors, description_placeholders=placeholders
        )

    async_step_user = async_step_basic
    # Same form for edits; self.source tells add and edit apart (FLT-11)
    async_step_reconfigure = async_step_basic

    async def async_step_advanced(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Ask for field scope, case, time window, weekdays, duration range and templates (D-02)."""
        entry: XmltvConfigEntry = self._get_entry()
        if entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="source_not_loaded")
        pending = self._load_pending()

        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        if user_input is not None:
            values = _advanced_values(user_input)
            errors, placeholders = _advanced_errors(values)
            # Nothing reaches the pending values, and so the preview and storage, until every check passes
            if not errors:
                pending.update(values)
                return await self.async_step_preview()

        # After an error the form shows exactly what was submitted, cleared fields included
        suggestions = user_input if user_input is not None else _advanced_suggestions(pending)
        schema = self.add_suggested_values_to_schema(_advanced_schema(), suggestions)
        return self.async_show_form(
            step_id="advanced",
            data_schema=schema,
            errors=errors,
            description_placeholders=_ADVANCED_PLACEHOLDERS | placeholders,
        )

    async def async_step_preview(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:  # noqa: ARG002
        """Show the match count from now on and the next matches, then offer Save or Back (FLT-10, D-15..D-17)."""
        entry: XmltvConfigEntry = self._get_entry()
        if entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="source_not_loaded")
        # A full feed scan takes up to a second: never on the event loop (T-02-06)
        result = await self.hass.async_add_executor_job(
            build_preview,
            self._calendar_data(),
            entry.runtime_data.coordinator.data,
            dt_util.utcnow(),
            dt_util.get_default_time_zone(),
            self.hass.config.language,
        )
        # D-18: zero matches warn but still allow saving; the warning lives in translations
        return self.async_show_menu(
            step_id="preview" if result.count else "preview_empty",
            menu_options=["save", "back"],
            description_placeholders={
                "count": str(result.count),
                "matches": "\n".join(f"- {line}" for line in result.lines),
            },
        )

    # HA requires a handler for every shown step id; the empty variant only differs in its translated text
    async_step_preview_empty = async_step_preview

    async def async_step_save(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:  # noqa: ARG002
        """Create or update the calendar; only reachable from the preview (D-01)."""
        entry: XmltvConfigEntry = self._get_entry()
        if entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="source_not_loaded")
        name = self._load_pending()[CONF_NAME]
        if self.source == SOURCE_USER:
            return self.async_create_entry(title=name, data=self._calendar_data())
        # Update only: the entry's update listener applies the change in place, with no reload and no
        # new download (D-04); the reloading variant raises when an update listener exists (Pitfall 1)
        return self.async_update_and_abort(
            entry, self._get_reconfigure_subentry(), title=name, data=self._calendar_data()
        )

    async def async_step_back(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:  # noqa: ARG002
        """Return to the form, pre-filled with the pending values (D-15)."""
        return await self.async_step_basic()
