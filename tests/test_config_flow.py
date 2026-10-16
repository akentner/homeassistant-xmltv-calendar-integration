"""Source config flow: URL and local-file sources, validation, duplicates, name default and refresh bounds."""

import asyncio
import gzip
import logging
from datetime import timedelta
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import aiohttp
import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState, ConfigSubentry
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xmltv_calendar import source

from .conftest import DOMAIN, FEED_URL, add_file_source, add_url_source

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


def _cache_file(hass: HomeAssistant, key: str) -> Path:
    """Return the cached payload file of a source (the 64-hex unique_id is used as the key unchanged)."""
    return Path(hass.config.cache_path(DOMAIN, f"{key}.feed"))


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

    # 2. file -> schedule directly: a local file is not downloaded, so there is no progress step
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"path": str(feed), "refresh_mode": "interval", "timezone": {"naive_timezone": "utc", "offset_minutes": 0}},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "schedule"

    # 3. schedule -> name, pre-filled with the file name (D-09)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"refresh_hours": 12})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "name"
    assert _schema_key(result, "name").description["suggested_value"] == "guide.xml"

    # 4. Submitting the suggested name unchanged creates the entry with the complete option contract
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "guide.xml"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "guide.xml"
    assert result["data"] == {"source_type": "file", "path": str(feed)}
    assert result["options"] == {
        "refresh_mode": "interval",
        "refresh_hours": 12,
        "naive_timezone": "utc",
        "offset_minutes": 0,
    }
    await hass.async_block_till_done()
    entry = result["result"]
    assert entry.state is ConfigEntryState.LOADED

    # 5. A calendar without filters shows every programme of the file; no cache file was seeded (D-11)
    assert not _cache_file(hass, entry.unique_id).exists()
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(data=MappingProxyType({}), subentry_type="calendar", title="All", unique_id=None),
    )
    await hass.async_block_till_done()
    events = await _get_events(hass, "calendar.all", "2026-10-13T00:00:00+00:00", 24)
    assert len(events) == 4


# --- URL source: download progress, schedule step, seeded cache (CFG-03, D-01, D-13) ---------------------


async def test_url_source_end_to_end_with_progress_and_seeded_cache(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None
) -> None:
    aioclient_mock.get(FEED_URL, content=BASIC_FEED)

    # 1. Menu -> url form: URL, refresh mode (default interval) and the collapsed timezone section
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "url"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "url"
    _schema_key(result, "url")
    assert _schema_key(result, "refresh_mode").default() == "interval"
    _schema_key(result, "timezone")

    # 2. Submitting starts the download behind a progress step
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"url": FEED_URL, "refresh_mode": "interval", "timezone": {"naive_timezone": "utc", "offset_minutes": 0}},
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    assert result["progress_action"] == "download"

    # 3. Download done -> schedule step with only the interval field
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "schedule"
    assert _schema_key(result, "refresh_hours").default() == 24
    assert "refresh_time" not in result["data_schema"].schema

    # 4. schedule -> name, pre-filled with the host (D-09)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"refresh_hours": 24})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "name"
    assert _schema_key(result, "name").description["suggested_value"] == "epg.example.com"

    # 5. name -> entry with the unchanged data and the complete option contract
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "Test EPG"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"source_type": "url", "url": FEED_URL}
    assert result["options"] == {
        "refresh_mode": "interval",
        "refresh_hours": 24,
        "naive_timezone": "utc",
        "offset_minutes": 0,
    }
    await hass.async_block_till_done()
    entry = result["result"]
    assert entry.state is ConfigEntryState.LOADED

    # 6. The setup download seeded the cache: the first refresh parsed it, nothing was downloaded twice (D-13)
    assert _cache_file(hass, entry.unique_id).is_file()
    assert aioclient_mock.call_count == 1
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(data=MappingProxyType({}), subentry_type="calendar", title="All", unique_id=None),
    )
    await hass.async_block_till_done()
    events = await _get_events(hass, "calendar.all", "2026-10-13T00:00:00+00:00", 24)
    assert len(events) == 4
    assert aioclient_mock.call_count == 1


async def test_daily_mode_asks_only_for_a_time(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None
) -> None:
    aioclient_mock.get(FEED_URL, content=BASIC_FEED)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "url"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"url": FEED_URL, "refresh_mode": "daily", "timezone": {"naive_timezone": "utc", "offset_minutes": 0}},
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "schedule"
    _schema_key(result, "refresh_time")
    assert "refresh_hours" not in result["data_schema"].schema

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"refresh_time": "18:15:00"})
    assert result["step_id"] == "name"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "Daily EPG"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"]["refresh_mode"] == "daily"
    assert result["options"]["refresh_time"] == "18:15"
    await hass.async_block_till_done()


# --- Shared settings fields (D-05, D-06) ----------------------------------------------------------------


async def _source_form(hass: HomeAssistant, step: str) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": step})


@pytest.mark.parametrize("step", ["url", "file"])
async def test_url_and_file_steps_share_settings_fields(hass: HomeAssistant, step: str) -> None:
    result = await _source_form(hass, step)
    assert result["step_id"] == step
    assert _schema_key(result, "refresh_mode").default() == "interval"
    timezone = result["data_schema"].schema[_schema_key(result, "timezone")]
    assert timezone.options == {"collapsed": True}
    fields = {str(key): key.default() for key in timezone.schema.schema}
    assert fields == {"naive_timezone": "utc", "offset_minutes": 0}
    assert "refresh_hours" not in result["data_schema"].schema


async def test_timezone_section_is_stored_flat(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None
) -> None:
    aioclient_mock.get(FEED_URL, content=BASIC_FEED)
    result = await add_url_source(hass, naive_timezone="local", offset_minutes=-60)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "EPG"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"]["naive_timezone"] == "local"
    assert result["options"]["offset_minutes"] == -60
    assert "timezone" not in result["options"]
    await hass.async_block_till_done()


@pytest.mark.parametrize("offset_minutes", [-721, 721])
async def test_offset_out_of_bounds_is_rejected(hass: HomeAssistant, forbid_loop_io: None, offset_minutes: int) -> None:
    result = await _source_form(hass, "url")
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "url": FEED_URL,
                "refresh_mode": "interval",
                "timezone": {"naive_timezone": "utc", "offset_minutes": offset_minutes},
            },
        )


# --- URL step validation and download errors -------------------------------------------------------------

SECRET_URL = "https://epg.example.com/guide.xml?token=s3cret"  # noqa: S105 - fake token the logs must not show


def _cache_files(hass: HomeAssistant) -> list[str]:
    """Return the names in the integration's cache directory (empty when it does not exist)."""
    directory = Path(hass.config.cache_path(DOMAIN))
    return sorted(path.name for path in directory.iterdir()) if directory.is_dir() else []


def _assert_url_form_error(result: dict[str, Any], error: str, url: str = FEED_URL) -> None:
    """Assert the flow is back on the url form with `error` and the entered URL kept."""
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "url"
    assert result["errors"] == {"base": error}
    assert _schema_key(result, "url").description["suggested_value"] == url


async def test_url_with_other_scheme_is_invalid(hass: HomeAssistant, forbid_loop_io: None) -> None:
    result = await add_url_source(hass, "ftp://x")
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "url"
    assert result["errors"] == {"url": "invalid_url"}


@pytest.mark.parametrize(
    "mock_kwargs", [{"exc": aiohttp.ClientError()}, {"exc": TimeoutError()}], ids=["client-error", "timeout"]
)
async def test_unreachable_url_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None, mock_kwargs: dict[str, Any]
) -> None:
    aioclient_mock.get(FEED_URL, **mock_kwargs)
    result = await add_url_source(hass)
    _assert_url_form_error(result, "cannot_connect")


@pytest.mark.parametrize("status", [404, 500])
async def test_http_error_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None, status: int
) -> None:
    aioclient_mock.get(FEED_URL, status=status)
    result = await add_url_source(hass)
    _assert_url_form_error(result, "cannot_connect")


async def test_non_feed_body_is_invalid_feed(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None
) -> None:
    aioclient_mock.get(FEED_URL, content=b"hello")
    result = await add_url_source(hass)
    _assert_url_form_error(result, "invalid_feed")


async def test_bom_and_whitespace_before_xml_pass(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None
) -> None:
    aioclient_mock.get(FEED_URL, content=b"\xef\xbb\xbf \r\n\t" + BASIC_FEED)
    result = await add_url_source(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "name"


async def test_too_large_download_shows_feed_too_large(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, monkeypatch: pytest.MonkeyPatch, forbid_loop_io: None
) -> None:
    monkeypatch.setattr(source, "MAX_DOWNLOAD_BYTES", 1024)
    aioclient_mock.get(FEED_URL, content=b"<" + b"x" * 4095)
    result = await add_url_source(hass)
    _assert_url_form_error(result, "feed_too_large")


async def test_retry_after_download_error_downloads_again(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None
) -> None:
    aioclient_mock.get(FEED_URL, status=500)
    result = await add_url_source(hass)
    _assert_url_form_error(result, "cannot_connect")

    # The url form shown again starts a new download on submit
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, content=BASIC_FEED)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"url": FEED_URL, "refresh_mode": "interval", "timezone": {"naive_timezone": "utc", "offset_minutes": 0}},
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["step_id"] == "schedule"
    assert aioclient_mock.call_count == 1


async def test_abandoned_download_writes_no_cache(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None
) -> None:
    started = asyncio.Event()

    async def hang(*_: Any) -> Any:
        started.set()
        await asyncio.Event().wait()  # never set: the download only ends by cancellation

    aioclient_mock.get(FEED_URL, side_effect=hang)
    result = await _source_form(hass, "url")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"url": FEED_URL, "refresh_mode": "interval", "timezone": {"naive_timezone": "utc", "offset_minutes": 0}},
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    await started.wait()

    # Closing the dialog removes the flow; the flow manager cancels the download task
    hass.config_entries.flow.async_abort(result["flow_id"])
    await hass.async_block_till_done()
    assert hass.config_entries.flow.async_progress() == []
    assert hass.config_entries.async_entries(DOMAIN) == []
    assert _cache_files(hass) == []


async def test_duplicate_source_aborts_before_download(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None
) -> None:
    MockConfigEntry(
        domain=DOMAIN,
        title="EPG",
        data={"source_type": "url", "url": FEED_URL},
        unique_id=source.source_unique_id("url", FEED_URL),
    ).add_to_hass(hass)
    aioclient_mock.get(FEED_URL, content=BASIC_FEED)
    result = await add_url_source(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert aioclient_mock.call_count == 0


async def test_flow_download_logs_host_only(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, caplog: pytest.LogCaptureFixture, forbid_loop_io: None
) -> None:
    caplog.set_level(logging.DEBUG)
    aioclient_mock.get(SECRET_URL, exc=aiohttp.ClientError(SECRET_URL))
    result = await add_url_source(hass, SECRET_URL)
    _assert_url_form_error(result, "cannot_connect", SECRET_URL)
    messages = [record.getMessage() for record in caplog.records if record.name.startswith(source.__name__)]
    assert any("epg.example.com" in message for message in messages)
    assert "s3cret" not in caplog.text
    assert "guide.xml" not in caplog.text


# --- File step validation ------------------------------------------------------------------------------


async def _submit_file(hass: HomeAssistant, path: str) -> dict[str, Any]:
    return await add_file_source(hass, path)


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
    result = await add_url_source(hass)
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
        result = await add_url_source(hass, url)
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
    result = await add_url_source(hass, refresh_hours=1)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "Hourly"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"]["refresh_hours"] == 1
    await hass.async_block_till_done()
    assert result["result"].runtime_data.coordinator.update_interval == timedelta(hours=1)


async def _schedule_form(hass: HomeAssistant) -> dict[str, Any]:
    """Drive a URL source up to the interval schedule step."""
    result = await _source_form(hass, "url")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"url": FEED_URL, "refresh_mode": "interval", "timezone": {"naive_timezone": "utc", "offset_minutes": 0}},
    )
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["step_id"] == "schedule"
    return result


@pytest.mark.parametrize("refresh_hours", [0, 169])
async def test_refresh_out_of_bounds_is_rejected(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None, refresh_hours: int
) -> None:
    aioclient_mock.get(FEED_URL, content=BASIC_FEED)
    result = await _schedule_form(hass)
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(result["flow_id"], {"refresh_hours": refresh_hours})


async def test_refresh_default_is_24_hours(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(FEED_URL, content=BASIC_FEED)
    result = await _schedule_form(hass)
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
