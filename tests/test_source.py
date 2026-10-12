"""Download robustness: byte cap, HTTP and network failures retry setup with a translated reason, host-only logs."""

import gzip
import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
import pytest
from homeassistant.config_entries import ConfigEntryState

from custom_components.xmltv_calendar import coordinator, source
from custom_components.xmltv_calendar.xmltv import parser

from .conftest import FEED_URL

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

BASIC_FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
SECRET_URL = "https://epg.example.com/guide.xml?token=s3cret"  # noqa: S105 - fake token the logs must not show


def _padded_feed(size: int) -> bytes:
    """Return basic.xml followed by an XML comment so the body is exactly `size` bytes and still valid."""
    padding = size - len(BASIC_FEED) - len(b"<!---->")
    return BASIC_FEED + b"<!--" + b"x" * padding + b"-->"


async def test_download_cap_retries_setup(
    monkeypatch: pytest.MonkeyPatch,
    forbid_loop_io: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    monkeypatch.setattr(source, "MAX_DOWNLOAD_BYTES", 1024, raising=False)
    body = _padded_feed(4096)
    assert len(body) == 4096

    entry = await setup_xmltv(body)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.error_reason_translation_key == "feed_too_large"


async def test_body_within_download_cap_loads(
    monkeypatch: pytest.MonkeyPatch,
    forbid_loop_io: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    monkeypatch.setattr(source, "MAX_DOWNLOAD_BYTES", 4096, raising=False)

    entry = await setup_xmltv(_padded_feed(4096))

    assert entry.state is ConfigEntryState.LOADED


async def test_decompressed_cap_retries_setup(
    monkeypatch: pytest.MonkeyPatch,
    forbid_loop_io: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    monkeypatch.setattr(coordinator, "parse", partial(parser.parse, max_bytes=1024))

    entry = await setup_xmltv(gzip.compress(_padded_feed(4096)))

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.error_reason_translation_key == "feed_too_large"


@pytest.mark.parametrize(
    "response",
    [
        pytest.param({"status": 500}, id="http-500"),
        pytest.param({"status": 404}, id="http-404"),
        pytest.param({"exc": TimeoutError()}, id="timeout"),
        pytest.param({"exc": aiohttp.ClientError()}, id="client-error"),
    ],
)
async def test_fetch_failures_retry_setup(
    aioclient_mock: AiohttpClientMocker,
    forbid_loop_io: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
    response: dict[str, Any],
) -> None:
    # Registered first, so it wins over setup_xmltv's own mock
    aioclient_mock.get(FEED_URL, **response)

    entry = await setup_xmltv(BASIC_FEED)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.error_reason_translation_key == "unable_to_fetch"


async def test_logs_name_host_only(
    caplog: pytest.LogCaptureFixture,
    forbid_loop_io: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    caplog.set_level(logging.DEBUG)

    entry = await setup_xmltv(BASIC_FEED, url=SECRET_URL)

    assert entry.state is ConfigEntryState.LOADED
    assert "s3cret" not in caplog.text
    assert "/guide.xml" not in caplog.text
    assert any("epg.example.com" in record.getMessage() for record in caplog.records)


async def test_failure_logs_name_host_only(
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
    forbid_loop_io: None,
    setup_xmltv: Callable[..., Awaitable[Any]],
) -> None:
    caplog.set_level(logging.DEBUG)
    aioclient_mock.get(SECRET_URL, exc=aiohttp.ClientError(SECRET_URL))

    entry = await setup_xmltv(BASIC_FEED, url=SECRET_URL)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert "s3cret" not in caplog.text
    assert "/guide.xml" not in caplog.text
    assert any("epg.example.com" in record.getMessage() for record in caplog.records)
