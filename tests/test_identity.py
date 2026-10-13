"""Source identity (SRC-13): normalization and the persisted unique_id for every source variant.

Task 2 of plan 01-07 chose sha256: unique_id = SHA-256 hex of "<source_type>:<normalized locator>".
"""

import hashlib
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.xmltv_calendar import source

from .conftest import DOMAIN, FEED_URL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

BASIC_FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()


def test_normalize_url_canonical_form() -> None:
    url = "HTTPS://EPG.Example.com:443/a/../guide.xml?k=1#frag"
    assert source.normalize_url(url) == "https://epg.example.com/guide.xml?k=1"


def test_normalize_url_keeps_query_order() -> None:
    assert source.normalize_url("http://h:80/x?b=2&a=1") == "http://h/x?b=2&a=1"


@pytest.mark.parametrize(
    "url", ["ftp://h/x", "file:///etc/passwd", "https:///nohost", "not a url", "data:text/xml,<a/>"]
)
def test_normalize_url_rejects(url: str) -> None:
    with pytest.raises(source.InvalidUrlError):
        source.normalize_url(url)


def test_source_unique_id_is_sha256_of_typed_locator() -> None:
    normalized = "https://epg.example.com/guide.xml?k=secret"
    unique_id = source.source_unique_id("url", normalized)
    assert re.fullmatch(r"[0-9a-f]{64}", unique_id)
    assert unique_id == hashlib.sha256(f"url:{normalized}".encode()).hexdigest()
    assert unique_id == source.source_unique_id("url", normalized)
    assert unique_id != source.source_unique_id("file", normalized)
    assert "secret" not in unique_id


async def _add_url_source(hass: HomeAssistant, url: str) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "url"})
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"url": url, "refresh_hours": 24})


async def _add_file_source(hass: HomeAssistant, path: str) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "file"})
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"path": path, "refresh_hours": 24})


async def test_url_variant_identity_invariant(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None
) -> None:
    aioclient_mock.get(FEED_URL, content=BASIC_FEED)
    result = await _add_url_source(hass, FEED_URL)
    assert result["step_id"] == "name"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "EPG"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    entry = result["result"]
    assert entry.unique_id == source.source_unique_id("url", FEED_URL)

    # Same source, different spelling: upper-case scheme and host, default port, dot segment, fragment
    calls_before = aioclient_mock.call_count
    result = await _add_url_source(hass, "HTTPS://EPG.EXAMPLE.COM:443/x/../guide.xml#now")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert aioclient_mock.call_count == calls_before  # duplicate aborts before the probe


async def test_url_entry_stores_normalized_url_and_hashed_id(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, forbid_loop_io: None
) -> None:
    token_url = "https://epg.example.com/guide.xml?apikey=s3cret"  # noqa: S105 - fake token
    aioclient_mock.get(token_url, content=BASIC_FEED)
    result = await _add_url_source(hass, "HTTPS://EPG.example.com/guide.xml?apikey=s3cret#top")
    assert result["step_id"] == "name"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "EPG"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"source_type": "url", "url": token_url}
    assert "s3cret" not in result["result"].unique_id
    await hass.async_block_till_done()


@pytest.fixture
def allowed_dir(tmp_path: Path) -> Path:
    """Return the resolved temporary directory (is_allowed_path compares resolved paths)."""
    return tmp_path.resolve()


async def test_file_variant_identity_invariant(hass: HomeAssistant, allowed_dir: Path, forbid_loop_io: None) -> None:
    feed = allowed_dir / "guide.xml"
    feed.write_bytes(BASIC_FEED)
    link = allowed_dir / "alias.xml"
    link.symlink_to(feed)
    hass.config.allowlist_external_dirs = {str(allowed_dir)}

    result = await _add_file_source(hass, str(feed))
    assert result["step_id"] == "name"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "Local"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert result["result"].unique_id == source.source_unique_id("file", str(feed))

    # Same file through a symlink resolves to the same real path
    result = await _add_file_source(hass, str(link))
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
