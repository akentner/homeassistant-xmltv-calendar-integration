"""Source config flow: URL and local-file sources, validation, duplicates, name default and refresh bounds."""

import gzip
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState, ConfigSubentry
from homeassistant.data_entry_flow import FlowResultType

from .conftest import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

BASIC_FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()


def _schema_key(result: Any, name: str) -> Any:
    """Return the voluptuous marker for `name` in a form result."""
    for key in result["data_schema"].schema:
        if key == name:
            return key
    msg = f"{name} not in form"
    raise AssertionError(msg)


async def _get_events(hass: HomeAssistant, entity_id: str, start: str, hours: float) -> list[dict[str, Any]]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": start, "duration": {"hours": hours}},
        blocking=True,
        return_response=True,
    )
    return response[entity_id]["events"]


@pytest.fixture
def allowed_dir(tmp_path: Path) -> Path:
    """Return the resolved temporary directory (is_allowed_path compares resolved paths)."""
    return tmp_path.resolve()


async def test_file_source_end_to_end(
    hass: HomeAssistant,
    allowed_dir: Path,
    freezer: Any,
    forbid_loop_io: None,
) -> None:
    freezer.move_to("2026-10-13T08:00:00+00:00")
    allowed = allowed_dir
    feed = allowed / "guide.xml"
    feed.write_bytes(gzip.compress(BASIC_FEED))  # gzip data under a .xml name (SRC-03)
    hass.config.allowlist_external_dirs = {str(allowed)}

    # 1. Menu offers url first, then file
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    assert list(result["menu_options"]) == ["url", "file"]
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "file"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "file"

    # 2. file -> name, pre-filled with the file name (D-09)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"path": str(feed), "refresh_hours": 24})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "name"
    assert _schema_key(result, "name").description["suggested_value"] == "guide.xml"

    # 3. Submitting the suggested name unchanged creates the entry
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "guide.xml"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "guide.xml"
    assert result["data"] == {"source_type": "file", "path": str(feed)}
    assert result["options"] == {"refresh_hours": 24}
    await hass.async_block_till_done()
    entry = result["result"]
    assert entry.state is ConfigEntryState.LOADED

    # 4. A calendar without filters shows every programme of the file
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(data=MappingProxyType({}), subentry_type="calendar", title="All", unique_id=None),
    )
    await hass.async_block_till_done()
    events = await _get_events(hass, "calendar.all", "2026-10-13T00:00:00+00:00", 24)
    assert len(events) == 4
