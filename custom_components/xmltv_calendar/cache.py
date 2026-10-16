"""
Disk cache of a URL source's raw feed (SRC-06, D-08).

The cache is disposable and keyed by entry identifiers only: the payload is the body exactly as downloaded (gzip stays
gzip) in `<config>/.cache/xmltv_calendar/<key>.feed`, which HA excludes from backups; its metadata lives in the Store
`xmltv_calendar.<key>`. Neither the file name, the Store nor the logs hold the URL.

The payload is replaced atomically before the metadata is saved (RESEARCH Pitfall 5). A payload whose size differs from
the stored size is never trusted, so a crash between the two writes cannot leave a cache that is used.

The same Store also holds the source's refresh health (`SourceHealth`, SRC-11, D-17), for file sources too, so a
failure streak survives restarts and setup retries.
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
# Failure reasons are translation keys (snake_case); a hand-edited Store cannot inject text into an issue
_REASON = re.compile(r"[a-z_]{1,64}")


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


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


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


@dataclass(frozen=True, slots=True)
class SourceHealth:
    """Refresh outcomes of a source: last success, the current failure streak and the last failure (D-17)."""

    last_success: datetime | None = None
    failing_since: datetime | None = None
    last_failure_at: datetime | None = None
    last_failure_reason: str | None = None
    consecutive_failures: int = 0

    def as_dict(self) -> dict[str, Any]:
        """Return the stored shape (ISO 8601 times)."""
        return {
            "last_success": _isoformat(self.last_success),
            "failing_since": _isoformat(self.failing_since),
            "last_failure_at": _isoformat(self.last_failure_at),
            "last_failure_reason": self.last_failure_reason,
            "consecutive_failures": self.consecutive_failures,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        """Tolerant reader: anything malformed gives the default (healthy) state, never an exception (T-03-14)."""
        if not isinstance(value, dict):
            return cls()
        failures = value.get("consecutive_failures")
        reason = value.get("last_failure_reason")
        if isinstance(failures, bool) or not isinstance(failures, int) or failures < 0:
            return cls()
        if reason is not None and (not isinstance(reason, str) or not _REASON.fullmatch(reason)):
            return cls()
        times = [value.get(key) for key in ("last_success", "failing_since", "last_failure_at")]
        parsed = [_aware_datetime(stored) for stored in times]
        if any(stored is not None and result is None for stored, result in zip(times, parsed, strict=True)):
            return cls()
        last_success, failing_since, last_failure_at = parsed
        return cls(
            last_success=last_success,
            failing_since=failing_since,
            last_failure_at=last_failure_at,
            last_failure_reason=reason,
            consecutive_failures=failures,
        )


class FeedCache:
    """The cached payload of one source entry plus its metadata and the source's refresh health."""

    def __init__(self, hass: HomeAssistant, key: str) -> None:
        """Bind to the payload file and Store of `key` (see `cache_key`)."""
        self._hass = hass
        self._key = key
        self._store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, f"{DOMAIN}.{key}", private=True)
        self._path = Path(hass.config.cache_path(DOMAIN, f"{key}.feed"))
        self._meta: CacheMeta | None = None
        self._health = SourceHealth()

    @property
    def meta(self) -> CacheMeta | None:
        """The metadata of the cached payload, None when there is no cache."""
        return self._meta

    @property
    def health(self) -> SourceHealth:
        """The source's refresh health as last loaded or saved."""
        return self._health

    def _stored(self, meta: CacheMeta | None) -> dict[str, Any]:
        return {"meta": meta.as_dict() if meta is not None else None, "health": self._health.as_dict()}

    async def async_save_health(self, health: SourceHealth) -> None:
        """Replace the health and save it next to the metadata; a failed save is logged at DEBUG only."""
        self._health = health
        try:
            await self._store.async_save(self._stored(self._meta))
        except (OSError, HomeAssistantError) as err:
            _LOGGER.debug("Cache %s health not saved: %s", self._key, type(err).__name__)

    async def async_load(self) -> None:
        """Load the metadata and health; stored data that is unreadable or malformed counts as none."""
        try:
            data = await self._store.async_load()
        except HomeAssistantError as err:
            _LOGGER.debug("Cache %s metadata unreadable: %s", self._key, type(err).__name__)
            data = None
        self._meta = CacheMeta.from_dict(data.get("meta")) if isinstance(data, dict) else None
        self._health = SourceHealth.from_dict(data.get("health")) if isinstance(data, dict) else SourceHealth()

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
            await self._store.async_save(self._stored(meta))
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
            await self._store.async_save(self._stored(meta))
        except (OSError, HomeAssistantError) as err:
            _LOGGER.debug("Cache %s metadata not updated: %s", self._key, type(err).__name__)

    async def async_drop(self) -> None:
        """Forget a cache that turned out unusable: delete the payload and save empty metadata."""
        self._meta = None
        await self._hass.async_add_executor_job(self._unlink)
        await self._store.async_save(self._stored(None))

    async def async_remove(self) -> None:
        """Delete the payload file and the Store, when the entry is removed (D-08)."""
        self._meta = None
        self._health = SourceHealth()
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
