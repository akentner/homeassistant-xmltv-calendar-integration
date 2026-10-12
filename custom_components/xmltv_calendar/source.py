"""Feed download, size- and time-bounded. Logs and errors name only the host: path and query may carry credentials."""

import logging
from typing import TYPE_CHECKING

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from yarl import URL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024  # 256 MiB on the wire (SRC-09)
DOWNLOAD_TIMEOUT = aiohttp.ClientTimeout(total=300, sock_read=60)
_CHUNK_SIZE = 1 << 16
_HTTP_ERROR_MIN = 400


class SourceError(Exception):
    """The source could not be read."""


class SourceUnavailableError(SourceError):
    """The source is unreachable or answered with an HTTP error."""


class SourceTooLargeError(SourceError):
    """The download exceeds `MAX_DOWNLOAD_BYTES`."""


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
