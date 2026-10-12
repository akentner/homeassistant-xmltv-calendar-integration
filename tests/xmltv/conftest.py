"""Fixtures for pure-library tests: never start Home Assistant."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations() -> None:
    """Override the root autouse fixture so pure-library tests do not need a hass instance."""
