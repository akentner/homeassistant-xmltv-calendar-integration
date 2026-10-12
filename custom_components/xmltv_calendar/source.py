"""Feed download. Logs and errors name only the host: path and query may carry credentials."""

import logging
from typing import TYPE_CHECKING

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from yarl import URL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=300, sock_read=60)
_HTTP_ERROR_MIN = 400


class SourceError(Exception):
    """The source could not be read."""


class SourceUnavailableError(SourceError):
    """The source is unreachable or answered with an HTTP error."""


async def async_fetch_url(hass: HomeAssistant, url: str) -> bytes:
    """Download the feed and return the body bytes. Plan 01-05 adds size caps and gzip handling."""
    host = URL(url).host
    session = async_get_clientsession(hass)
    try:
        async with session.get(url, timeout=_TIMEOUT) as response:
            if response.status >= _HTTP_ERROR_MIN:
                _LOGGER.debug("Source host %s answered HTTP %s", host, response.status)
                msg = f"HTTP {response.status} from {host}"
                raise SourceUnavailableError(msg)
            return await response.read()
    except (aiohttp.ClientError, TimeoutError) as err:
        # The error text of aiohttp can contain the full URL, so only its type is logged
        _LOGGER.debug("Fetching from source host %s failed: %s", host, type(err).__name__)
        msg = f"cannot fetch from {host}: {type(err).__name__}"
        raise SourceUnavailableError(msg) from None
