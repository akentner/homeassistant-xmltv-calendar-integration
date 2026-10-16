"""
Disk cache of a URL source's raw feed (SRC-06, D-08).

The cache is disposable and keyed by entry identifiers only: the payload is the body exactly as downloaded (gzip stays
gzip) in `<config>/.cache/xmltv_calendar/<key>.feed`, which HA excludes from backups; its metadata lives in the Store
`xmltv_calendar.<key>`. Neither the file name, the Store nor the logs hold the URL.

The payload is replaced atomically before the metadata is saved (RESEARCH Pitfall 5). A payload whose size differs from
the stored size is never trusted, so a crash between the two writes cannot leave a cache that is used.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.util.file import write_utf8_file

from .const import DOMAIN
from .source import clean_validator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

STORE_VERSION = 1
_SAFE_KEY = re.compile(r"[0-9A-Za-z]{1,64}")


def cache_key(entry: ConfigEntry) -> str:
    """Return the entry's unique_id (else its entry_id) when it is a safe file name, else that value's SHA-256 hex."""
    raw = entry.unique_id or entry.entry_id
    if _SAFE_KEY.fullmatch(raw):
        return raw
    return hashlib.sha256(raw.encode()).hexdigest()


def payload_sha256(payload: bytes) -> str:
    """Return the SHA-256 hex digest the metadata stores for `payload`; run it in the executor for large payloads."""
    return hashlib.sha256(payload).hexdigest()


def _aware_datetime(value: object) -> datetime | None:
    """Parse a stored ISO 8601 time; None unless it is a string holding an aware datetime."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


@dataclass(frozen=True, slots=True)
class CacheMeta:
    """What is known about the cached payload; `source_id` is the hashed source, never the URL."""

    source_id: str
    size: int
    sha256: str
    fetched_at: datetime
    etag: str | None = None
    last_modified: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the stored shape (ISO 8601 `fetched_at`)."""
        return {
            "source_id": self.source_id,
            "size": self.size,
            "sha256": self.sha256,
            "fetched_at": self.fetched_at.isoformat(),
            "etag": self.etag,
            "last_modified": self.last_modified,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self | None:
        """Tolerant reader: anything malformed gives None (no cache)."""
        if not isinstance(value, dict):
            return None
        source_id = value.get("source_id")
        size = value.get("size")
        digest = value.get("sha256")
        fetched = _aware_datetime(value.get("fetched_at"))
        if (
            not isinstance(source_id, str)
            or not source_id
            or not isinstance(digest, str)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or fetched is None
        ):
            return None
        etag = value.get("etag")
        last_modified = value.get("last_modified")
        return cls(
            source_id=source_id,
            size=size,
            sha256=digest,
            fetched_at=fetched,
            etag=clean_validator(etag) if isinstance(etag, str) else None,
            last_modified=clean_validator(last_modified) if isinstance(last_modified, str) else None,
        )


class FeedCache:
    """The cached payload of one source entry plus its metadata."""

    def __init__(self, hass: HomeAssistant, key: str) -> None:
        """Bind to the payload file and Store of `key` (see `cache_key`)."""
        self._hass = hass
        self._key = key
        self._store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, f"{DOMAIN}.{key}", private=True)
        self._path = Path(hass.config.cache_path(DOMAIN, f"{key}.feed"))
        self._meta: CacheMeta | None = None

    @property
    def meta(self) -> CacheMeta | None:
        """The metadata of the cached payload, None when there is no cache."""
        return self._meta

    async def async_load(self) -> None:
        """Load the metadata; stored data that is unreadable or malformed counts as no cache."""
        try:
            data = await self._store.async_load()
        except HomeAssistantError as err:
            _LOGGER.debug("Cache %s metadata unreadable: %s", self._key, type(err).__name__)
            data = None
        self._meta = CacheMeta.from_dict(data.get("meta")) if isinstance(data, dict) else None

    def valid_meta(self, source_id: str) -> CacheMeta | None:
        """Return the metadata only when it belongs to `source_id` (RESEARCH Pitfall 4)."""
        meta = self._meta
        if meta is None or meta.source_id != source_id:
            return None
        return meta

    async def async_read(self) -> bytes | None:
        """Return the payload, or None when it is missing, unreadable or not exactly the stored size."""
        meta = self._meta
        if meta is None:
            return None
        return await self._hass.async_add_executor_job(self._read, meta.size)

    def _read(self, size: int) -> bytes | None:
        try:
            with open(self._path, "rb") as file:  # noqa: PTH123 - builtin open keeps tests' forbid_loop_io guard effective
                payload = file.read(size + 1)  # one byte more reveals a longer file without reading all of it
        except OSError:
            return None
        return payload if len(payload) == size else None

    async def async_write(
        self,
        payload: bytes,
        *,
        source_id: str,
        fetched_at: datetime,
        etag: str | None,
        last_modified: str | None,
    ) -> bool:
        """Replace the payload atomically, then save its metadata; False (logged at DEBUG) when either fails."""
        try:
            digest = await self._hass.async_add_executor_job(self._write, payload)
            meta = CacheMeta(
                source_id=source_id,
                size=len(payload),
                sha256=digest,
                fetched_at=fetched_at,
                etag=etag,
                last_modified=last_modified,
            )
            await self._store.async_save({"meta": meta.as_dict()})
        except (OSError, HomeAssistantError) as err:
            _LOGGER.debug("Cache %s not written: %s", self._key, type(err).__name__)
            self._meta = None
            return False
        self._meta = meta
        return True

    async def async_touch(
        self, fetched_at: datetime, *, etag: str | None = None, last_modified: str | None = None
    ) -> None:
        """
        Record that the source confirmed the cached payload at `fetched_at` (304 or identical body); no payload IO.

        A validator that is given replaces the stored one; one that is not given is kept. A failed save is logged at
        DEBUG and leaves the in-memory metadata updated.
        """
        meta = self._meta
        if meta is None:
            return
        etag = clean_validator(etag)
        last_modified = clean_validator(last_modified)
        meta = replace(
            meta,
            fetched_at=fetched_at,
            etag=etag if etag is not None else meta.etag,
            last_modified=last_modified if last_modified is not None else meta.last_modified,
        )
        self._meta = meta
        try:
            await self._store.async_save({"meta": meta.as_dict()})
        except (OSError, HomeAssistantError) as err:
            _LOGGER.debug("Cache %s metadata not updated: %s", self._key, type(err).__name__)

    async def async_drop(self) -> None:
        """Forget a cache that turned out unusable: delete the payload and save empty metadata."""
        self._meta = None
        await self._hass.async_add_executor_job(self._unlink)
        await self._store.async_save({"meta": None})

    async def async_remove(self) -> None:
        """Delete the payload file and the Store, when the entry is removed (D-08)."""
        self._meta = None
        await self._hass.async_add_executor_job(self._unlink)
        await self._store.async_remove()

    def _unlink(self) -> None:
        try:
            self._path.unlink(missing_ok=True)
        except OSError as err:
            _LOGGER.debug("Cache %s payload not deleted: %s", self._key, type(err).__name__)

    def _write(self, payload: bytes) -> str:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        write_utf8_file(str(self._path), payload, private=True, mode="wb")
        return payload_sha256(payload)
