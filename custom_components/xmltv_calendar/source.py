"""
Feed sources: bounded URL download and allowed-path file reads.

Logs and errors name only the host: path and query may carry credentials. File helpers do blocking IO and
`hass.config.is_allowed_path` and must only run in an executor job.
"""

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from yarl import URL

from .xmltv.parser import GZIP_MAGIC, parse

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    from homeassistant.core import HomeAssistant
    from homeassistant.core_config import Config

    from .xmltv.model import EpgData

_LOGGER = logging.getLogger(__name__)

MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024  # 256 MiB on the wire (SRC-09)
DOWNLOAD_TIMEOUT = aiohttp.ClientTimeout(total=300, sock_read=60)
_CHUNK_SIZE = 1 << 16
_HTTP_ERROR_MIN = 400
PROBE_BYTES = 64 * 1024  # flow-time sniff of a source; the full read happens at setup
_UTF8_BOM = b"\xef\xbb\xbf"
_URL_SCHEMES = frozenset({"http", "https"})


class SourceError(Exception):
    """The source could not be read."""


class SourceUnavailableError(SourceError):
    """The source is unreachable or answered with an HTTP error."""


class SourceTooLargeError(SourceError):
    """The download exceeds `MAX_DOWNLOAD_BYTES`."""


class PathNotAllowedError(SourceError):
    """The path is relative or outside the directories Home Assistant allows (allowlist_external_dirs, media)."""


class FileMissingError(SourceError):
    """The path does not name a regular file."""


class InvalidFeedError(SourceError):
    """The first bytes of the source are neither gzip nor XML."""


class InvalidUrlError(SourceError):
    """The URL is not an http(s) URL with a host."""


def normalize_url(url: str) -> str:
    """
    Return the canonical form of an http(s) URL; raise `InvalidUrlError` for anything else.

    yarl lower-cases scheme and host, drops the default port and removes dot segments; the fragment is
    dropped here. The query is kept as is (order matters, it may be part of the source's identity).
    """
    try:
        parsed = URL(url.strip())
    except ValueError:
        msg = "not a URL"
        raise InvalidUrlError(msg) from None
    if parsed.scheme not in _URL_SCHEMES or not parsed.host:
        msg = "only http and https URLs with a host are supported"
        raise InvalidUrlError(msg)
    return str(parsed.with_fragment(None))


def source_unique_id(source_type: str, normalized: str) -> str:
    """
    Return the persisted config entry unique_id: SHA-256 hex of "<source_type>:<normalized locator>".

    Hashed (01-07 Task 2 decision) so query tokens of a URL are not copied into a second persisted field.
    Changing this scheme needs an entry migration.
    """
    return hashlib.sha256(f"{source_type}:{normalized}".encode()).hexdigest()


def looks_like_feed(head: bytes) -> bool:
    """Return True when `head` starts with the gzip magic or, after a UTF-8 BOM and whitespace, with '<'."""
    if head.startswith(GZIP_MAGIC):
        return True
    return head.removeprefix(_UTF8_BOM).lstrip().startswith(b"<")


async def async_probe_url(hass: HomeAssistant, url: str) -> None:
    """
    Read at most `PROBE_BYTES` of the URL and check that it starts like a feed.

    Raises `SourceUnavailableError` when the source cannot be reached or answers with an HTTP error, and
    `InvalidFeedError` when the first bytes are neither gzip nor XML. The connection is released after the
    probe; the full download happens at setup.
    """
    host = URL(url).host
    session = async_get_clientsession(hass)
    head = b""
    try:
        async with session.get(url, timeout=DOWNLOAD_TIMEOUT) as response:
            if response.status >= _HTTP_ERROR_MIN:
                _LOGGER.debug("Probe of source host %s answered HTTP %s", host, response.status)
                msg = f"HTTP {response.status} from {host}"
                raise SourceUnavailableError(msg)
            stream = response.content  # bind once, see async_fetch_url
            async for chunk in stream.iter_chunked(_CHUNK_SIZE):
                head += chunk
                if len(head) >= PROBE_BYTES:
                    break
    except (aiohttp.ClientError, TimeoutError) as err:
        _LOGGER.debug("Probe of source host %s failed: %s", host, type(err).__name__)
        msg = f"cannot fetch from {host}: {type(err).__name__}"
        raise SourceUnavailableError(msg) from None
    if not looks_like_feed(head[:PROBE_BYTES]):
        _LOGGER.debug("Source host %s did not answer with gzip or XML", host)
        msg = f"response from {host} is neither gzip nor XML"
        raise InvalidFeedError(msg)


def check_file(config: Config, path: str) -> str:
    """Return the real path of an allowed, existing file. Executor only (blocking IO)."""
    candidate = Path(path)
    if not candidate.is_absolute() or not config.is_allowed_path(path):
        msg = "path is not in an allowed directory"
        raise PathNotAllowedError(msg)
    if not candidate.is_file():
        msg = "path is not a file"
        raise FileMissingError(msg)
    return str(candidate.resolve())


def probe_file(path: str) -> None:
    """Raise `InvalidFeedError` unless the file starts like a feed. Executor only (blocking IO)."""
    try:
        with open(path, "rb") as file:  # noqa: PTH123 - builtin open keeps tests' forbid_loop_io guard effective
            head = file.read(PROBE_BYTES)
    except OSError as err:
        msg = f"cannot read file: {type(err).__name__}"
        raise SourceUnavailableError(msg) from None
    if not looks_like_feed(head):
        msg = "file is neither gzip nor XML"
        raise InvalidFeedError(msg)


def read_and_parse_file(
    config: Config, path: str, *, keep_after: datetime | None, default_duration: timedelta
) -> EpgData:
    """
    Check the path against the allowed directories, then parse the file. Executor only (blocking IO).

    The allowed-path check runs on every read, not only in the flow: the allowlist or the file may have changed.
    """
    real_path = check_file(config, path)
    try:
        with open(real_path, "rb") as file:  # noqa: PTH123 - see probe_file
            return parse(file, keep_after=keep_after, default_duration=default_duration)
    except OSError as err:
        msg = f"cannot read file: {type(err).__name__}"
        raise SourceUnavailableError(msg) from None


async def async_fetch_url(hass: HomeAssistant, url: str) -> bytes:
    """Stream the feed body into memory, bounded by `MAX_DOWNLOAD_BYTES` and `DOWNLOAD_TIMEOUT`."""
    host = URL(url).host
    max_bytes = MAX_DOWNLOAD_BYTES
    session = async_get_clientsession(hass)
    chunks: list[bytes] = []
    received = 0
    try:
        async with session.get(url, timeout=DOWNLOAD_TIMEOUT) as response:
            if response.status >= _HTTP_ERROR_MIN:
                _LOGGER.debug("Source host %s answered HTTP %s", host, response.status)
                msg = f"HTTP {response.status} from {host}"
                raise SourceUnavailableError(msg)
            stream = response.content  # bind once: some readers build a new stream per attribute access
            async for chunk in stream.iter_chunked(_CHUNK_SIZE):
                received += len(chunk)
                if received > max_bytes:
                    _LOGGER.debug("Download from source host %s exceeds %s bytes", host, max_bytes)
                    msg = f"download from {host} exceeds {max_bytes} bytes"
                    raise SourceTooLargeError(msg)
                chunks.append(chunk)
    except (aiohttp.ClientError, TimeoutError) as err:
        # The error text of aiohttp can contain the full URL, so only its type is logged
        _LOGGER.debug("Fetching from source host %s failed: %s", host, type(err).__name__)
        msg = f"cannot fetch from {host}: {type(err).__name__}"
        raise SourceUnavailableError(msg) from None
    _LOGGER.debug("Downloaded %s bytes from source host %s", received, host)
    return b"".join(chunks)
