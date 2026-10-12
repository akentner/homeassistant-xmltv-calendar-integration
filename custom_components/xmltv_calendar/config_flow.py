"""Config flow for XMLTV Calendar (not implemented yet)."""

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult


class XmltvConfigFlow(ConfigFlow, domain="xmltv_calendar"):
    """Placeholder flow so the tracer test fails on a flow-result assertion."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:  # noqa: ARG002
        """Abort until the real flow exists."""
        return self.async_abort(reason="not_implemented")
