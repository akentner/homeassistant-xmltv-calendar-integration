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
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.util import dt as dt_util
from yarl import URL

from .const import (
    CONF_CHANNEL_REGEX,
    CONF_CHANNELS,
    CONF_EXCLUDE,
    CONF_INCLUDE,
    CONF_NAME,
    CONF_PATH,
    CONF_REFRESH_HOURS,
    CONF_SOURCE_TYPE,
    CONF_URL,
    DEFAULT_REFRESH_HOURS,
    DOMAIN,
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
from .xmltv.settings import with_defaults

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


class CalendarSubentryFlow(ConfigSubentryFlow):
    """Add or edit a calendar of a loaded source: basic form -> preview -> save | back (D-01, D-19)."""

    def __init__(self) -> None:
        """Initialize the pending calendar values; loaded on first use, they survive Back (D-15)."""
        self._pending: dict[str, Any] | None = None

    def _load_pending(self) -> dict[str, Any]:
        """Return the pending values: defaults for a new calendar, the stored calendar for an edit (D-06)."""
        if self._pending is None:
            if self.source == SOURCE_USER:
                self._pending = with_defaults({})
            else:
                subentry = self._get_reconfigure_subentry()
                self._pending = with_defaults(dict(subentry.data))
                self._pending[CONF_NAME] = subentry.title
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
                if (bad := first_invalid_pattern(str(user_input.get(field, "")))) is not None:
                    errors[field] = "invalid_regex"
                    placeholders.setdefault("pattern", bad.pattern)
                    placeholders.setdefault("error", bad.message)
            if not errors:
                # A missing key means the field was cleared; keys outside this form keep their pending values
                pending.update({CONF_NAME: name, CONF_CHANNELS: list(user_input.get(CONF_CHANNELS, []))})
                pending.update({field: str(user_input.get(field, "")) for field in _PATTERN_FIELDS})
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
            }
        )
        schema = self.add_suggested_values_to_schema(schema, pending | (user_input or {}))
        return self.async_show_form(
            step_id="basic", data_schema=schema, errors=errors, description_placeholders=placeholders
        )

    async_step_user = async_step_basic
    # Same form for edits; self.source tells add and edit apart (FLT-11)
    async_step_reconfigure = async_step_basic

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
