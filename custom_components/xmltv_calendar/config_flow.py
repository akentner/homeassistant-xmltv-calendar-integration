"""Config flow: source entries (menu -> source step -> name) and calendar subentries."""

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
from yarl import URL

from .const import (
    CONF_CHANNELS,
    CONF_NAME,
    CONF_REFRESH_HOURS,
    CONF_SOURCE_TYPE,
    CONF_URL,
    DEFAULT_REFRESH_HOURS,
    DOMAIN,
    MAX_REFRESH_HOURS,
    MIN_REFRESH_HOURS,
    SOURCE_TYPE_URL,
    SUBENTRY_TYPE_CALENDAR,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .data import XmltvConfigEntry

_URL_SCHEMES = frozenset({"http", "https"})


def _host_of(url: str) -> str | None:
    """Return the host of an http(s) URL, or None when the URL is not usable."""
    try:
        parsed = URL(url)
    except ValueError:
        return None
    if parsed.scheme not in _URL_SCHEMES or not parsed.host:
        return None
    return parsed.host


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
        return self.async_show_menu(step_id="user", menu_options=[SOURCE_TYPE_URL])

    async def async_step_url(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the feed URL and the refresh interval."""
        errors: dict[str, str] = {}
        if user_input is not None:
            url = str(user_input[CONF_URL]).strip()
            if (host := _host_of(url)) is None:
                errors[CONF_URL] = "invalid_url"
            else:
                self._data = {CONF_SOURCE_TYPE: SOURCE_TYPE_URL, CONF_URL: url}
                self._options = {CONF_REFRESH_HOURS: int(user_input[CONF_REFRESH_HOURS])}
                self._suggested_name = host
                return await self.async_step_name()

        schema = vol.Schema(
            {
                vol.Required(CONF_URL): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
                vol.Required(CONF_REFRESH_HOURS, default=DEFAULT_REFRESH_HOURS): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_REFRESH_HOURS,
                        max=MAX_REFRESH_HOURS,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement="h",
                    )
                ),
            }
        )
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="url", data_schema=schema, errors=errors)

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


class CalendarSubentryFlow(ConfigSubentryFlow):
    """Add a calendar to a loaded source."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Ask for the calendar name and the channels; the picker lists channel IDs (D-02, D-03)."""
        entry: XmltvConfigEntry = self._get_entry()
        if entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="source_not_loaded")

        errors: dict[str, str] = {}
        if user_input is not None:
            name = str(user_input[CONF_NAME]).strip()
            if name:
                return self.async_create_entry(
                    title=name, data={CONF_CHANNELS: list(user_input.get(CONF_CHANNELS, []))}
                )
            errors[CONF_NAME] = "name_required"

        channel_ids = sorted(entry.runtime_data.coordinator.data.channels)
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Optional(CONF_CHANNELS, default=[]): SelectSelector(
                    SelectSelectorConfig(
                        options=channel_ids,
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                        sort=True,
                    )
                ),
            }
        )
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
