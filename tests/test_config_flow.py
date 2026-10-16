"""Source config flow: URL and local-file sources, validation, duplicates, name default and refresh bounds."""

import gzip
from datetime import timedelta
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import aiohttp
import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState, ConfigSubentry
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util import aiohttp as aiohttp_mock

from custom_components.xmltv_calendar import source

from .conftest import DOMAIN, FEED_URL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

NOW = "2026-10-13T06:00:00+00:00"
pytestmark = pytest.mark.freeze_time(NOW)

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


# --- URL step validation -------------------------------------------------------------------------------


async def _url_form(hass: HomeAssistant) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "url"})


async def _submit_url(hass: HomeAssistant, url: str, refresh_hours: float = 24) -> dict[str, Any]:
    result = await _url_form(hass)
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"url": url, "refresh_hours": refresh_hours}
    )


async def test_url_with_other_scheme_is_invalid(hass: HomeAssistant, forbid_loop_io: None) -> None:
    result = await _submit_url(hass, "ftp://x")
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "url"
    assert result["errors"] == {"url": "invalid_url"}


@pytest.mark.parametrize(
    "mock_kwargs",
    [{"exc": aiohttp.ClientError()}, {"exc": TimeoutError()}, {"status": 404}, {"status": 500}],
    ids=["client-error", "timeout", "http-404", "http-500"],
)
async def test_unreachable_url_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None, mock_kwargs: dict[str, Any]
) -> None:
    aioclient_mock.get(FEED_URL, **mock_kwargs)
    result = await _submit_url(hass, FEED_URL)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_non_feed_body_is_invalid_feed(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None
) -> None:
    aioclient_mock.get(FEED_URL, content=b"hello")
    result = await _submit_url(hass, FEED_URL)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_feed"}


async def test_bom_and_whitespace_before_xml_pass(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None
) -> None:
    aioclient_mock.get(FEED_URL, content=b"\xef\xbb\xbf \r\n\t" + BASIC_FEED)
    result = await _submit_url(hass, FEED_URL)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "name"


async def test_probe_reads_at_most_probe_bytes(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    monkeypatch: pytest.MonkeyPatch,
    forbid_loop_io: None,
) -> None:
    body = BASIC_FEED + b"<!-- " + b"x" * (1024 * 1024) + b" -->\n"  # valid XML, over 1 MiB
    streams: list[tuple[int, Any]] = []
    real_mock_stream = aiohttp_mock.mock_stream

    def recording_stream(data: bytes) -> Any:
        stream = real_mock_stream(data)
        streams.append((len(data), stream))
        return stream

    monkeypatch.setattr(aiohttp_mock, "mock_stream", recording_stream)
    aioclient_mock.get(FEED_URL, content=body)

    result = await _submit_url(hass, FEED_URL)
    assert result["step_id"] == "name"
    assert streams, "the url step made no probe request"
    size, probe_stream = streams[0]
    consumed = size - len(await probe_stream.read())
    assert 0 < consumed <= source.PROBE_BYTES
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "Big"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


# --- File step validation ------------------------------------------------------------------------------


async def _submit_file(hass: HomeAssistant, path: str) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "file"})
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"path": path, "refresh_hours": 24})


@pytest.fixture
def layout(allowed_dir: Path) -> dict[str, Path]:
    """Create allowed/ and outside/ directories with a feed, a non-feed and an escaping symlink."""
    inside = allowed_dir / "allowed"
    outside = allowed_dir / "outside"
    inside.mkdir()
    outside.mkdir()
    (inside / "guide.xml").write_bytes(BASIC_FEED)
    (inside / "notes.txt").write_bytes(b"SENTINEL-content-7q2 is not XML")
    (outside / "secret.xml").write_bytes(BASIC_FEED)
    (inside / "escape.xml").symlink_to(outside / "secret.xml")
    return {"inside": inside, "outside": outside}


@pytest.mark.parametrize(
    ("relative", "field", "error"),
    [
        ("guide.xml", "path", "path_not_allowed"),  # relative path
        ("@outside/secret.xml", "path", "path_not_allowed"),  # existing file, directory not allowed
        ("@inside/escape.xml", "path", "path_not_allowed"),  # symlink inside pointing outside
        ("@inside/../outside/secret.xml", "path", "path_not_allowed"),  # traversal
        ("@inside/missing.xml", "path", "file_not_found"),
        ("@inside", "path", "file_not_found"),  # a directory is not a file
        ("@inside/notes.txt", "base", "invalid_feed"),
    ],
    ids=["relative", "outside", "symlink-escape", "traversal", "missing", "directory", "not-xml"],
)
async def test_file_step_errors(
    hass: HomeAssistant,
    layout: dict[str, Path],
    forbid_loop_io: None,
    relative: str,
    field: str,
    error: str,
) -> None:
    hass.config.allowlist_external_dirs = {str(layout["inside"])}
    path = relative
    for name, directory in layout.items():
        path = path.replace(f"@{name}", str(directory))
    result = await _submit_file(hass, path)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "file"
    assert result["errors"] == {field: error}
    assert "SENTINEL" not in str(result)


# --- Name step and titles ------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["", "   "])
async def test_blank_name_is_rejected(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None, name: str
) -> None:
    aioclient_mock.get(FEED_URL, content=BASIC_FEED)
    result = await _submit_url(hass, FEED_URL)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": name})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"name": "name_required"}


async def test_same_name_different_urls_both_created(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None
) -> None:
    other_url = "https://other.example.org/epg.xml"
    aioclient_mock.get(FEED_URL, content=BASIC_FEED)
    aioclient_mock.get(other_url, content=BASIC_FEED)
    for url in (FEED_URL, other_url):
        result = await _submit_url(hass, url)
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "EPG"})
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
    entries = hass.config_entries.async_entries(DOMAIN)
    assert [entry.title for entry in entries] == ["EPG", "EPG"]
    assert len({entry.unique_id for entry in entries}) == 2


# --- Refresh interval (SRC-04, D-13) -------------------------------------------------------------------


async def test_minimum_refresh_is_one_hour(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None
) -> None:
    aioclient_mock.get(FEED_URL, content=BASIC_FEED)
    result = await _submit_url(hass, FEED_URL, refresh_hours=1)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "Hourly"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {"refresh_hours": 1}
    await hass.async_block_till_done()
    assert result["result"].runtime_data.coordinator.update_interval == timedelta(hours=1)


@pytest.mark.parametrize("refresh_hours", [0, 169])
async def test_refresh_out_of_bounds_is_rejected(hass: HomeAssistant, forbid_loop_io: None, refresh_hours: int) -> None:
    result = await _url_form(hass)
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {"url": FEED_URL, "refresh_hours": refresh_hours}
        )


async def test_refresh_default_is_24_hours(hass: HomeAssistant) -> None:
    result = await _url_form(hass)
    marker = _schema_key(result, "refresh_hours")
    assert marker.default() == 24


async def test_missing_refresh_option_means_24_hours(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(FEED_URL, content=BASIC_FEED)
    entry = MockConfigEntry(domain=DOMAIN, title="EPG", data={"source_type": "url", "url": FEED_URL}, options={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.coordinator.update_interval == timedelta(hours=24)


# --- File sources at setup time ------------------------------------------------------------------------


async def test_truncated_file_retries_setup(hass: HomeAssistant, allowed_dir: Path, forbid_loop_io: None) -> None:
    feed = allowed_dir / "guide.xml"
    cut = BASIC_FEED.index(b"<programme") + 25  # inside the first <programme> start tag
    feed.write_bytes(BASIC_FEED[:cut])
    hass.config.allowlist_external_dirs = {str(allowed_dir)}
    entry = MockConfigEntry(
        domain=DOMAIN, title="Local", data={"source_type": "file", "path": str(feed)}, options={"refresh_hours": 24}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.error_reason_translation_key == "invalid_feed"


async def test_file_outside_allowlist_is_refused_at_setup(
    hass: HomeAssistant, layout: dict[str, Path], forbid_loop_io: None
) -> None:
    hass.config.allowlist_external_dirs = {str(layout["inside"])}
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Secret",
        data={"source_type": "file", "path": str(layout["outside"] / "secret.xml")},
        options={"refresh_hours": 24},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.error_reason_translation_key == "path_not_allowed"
