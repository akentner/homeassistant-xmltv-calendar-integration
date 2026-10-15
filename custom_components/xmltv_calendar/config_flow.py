"""Config flow: source entries (menu -> source step -> name) and calendar subentries."""

from pathlib import PurePath
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import (
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
    """Add a calendar to a loaded source: basic form -> preview -> save | back (D-01)."""

    def __init__(self) -> None:
        """Initialize the pending calendar values; they survive Back (D-15)."""
        self._pending: dict[str, Any] = {}

    def _filter_data(self) -> dict[str, Any]:
        """Return the stored filter keys from the pending values."""
        return {key: self._pending[key] for key in (CONF_CHANNELS, *_PATTERN_FIELDS)}

    async def async_step_basic(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Ask for name, channels (sorted IDs, D-03), channel regex, include and exclude (D-02, D-05)."""
        entry: XmltvConfigEntry = self._get_entry()
        if entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="source_not_loaded")

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
                # A missing key means the field was cleared
                self._pending = {CONF_NAME: name, CONF_CHANNELS: list(user_input.get(CONF_CHANNELS, []))}
                self._pending.update({field: str(user_input.get(field, "")) for field in _PATTERN_FIELDS})
                return await self.async_step_preview()

        channel_ids = sorted(entry.runtime_data.coordinator.data.channels)
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
        schema = self.add_suggested_values_to_schema(schema, self._pending | (user_input or {}))
        return self.async_show_form(
            step_id="basic", data_schema=schema, errors=errors, description_placeholders=placeholders
        )

    async_step_user = async_step_basic

    async def async_step_preview(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:  # noqa: ARG002
        """Show the match count from now on and the next matches, then offer Save or Back (FLT-10, D-15..D-17)."""
        entry: XmltvConfigEntry = self._get_entry()
        if entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="source_not_loaded")
        # A full feed scan takes up to a second: never on the event loop (T-02-06)
        result = await self.hass.async_add_executor_job(
            build_preview,
            self._filter_data(),
            entry.runtime_data.coordinator.data,
            dt_util.utcnow(),
            dt_util.get_default_time_zone(),
            self.hass.config.language,
        )
        return self.async_show_menu(
            step_id="preview",
            menu_options=["save", "back"],
            description_placeholders={
                "count": str(result.count),
                "matches": "\n".join(f"- {line}" for line in result.lines),
            },
        )

    async def async_step_save(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:  # noqa: ARG002
        """Create the calendar; only reachable from the preview (D-01)."""
        if self._get_entry().state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="source_not_loaded")
        return self.async_create_entry(title=self._pending[CONF_NAME], data=self._filter_data())

    async def async_step_back(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:  # noqa: ARG002
        """Return to the form, pre-filled with the pending values (D-15)."""
        return await self.async_step_basic()
