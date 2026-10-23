"""
Diagnostics of a source entry: structure, state and counts, never feed content or filter patterns (SRC-12, D-21).

The file is meant to be attached to a bug report, so the result is built from an allow-list: every key is written here
by name. The URL keeps its scheme and host only, a local path its file name only, and the cache validators are reported
as presence flags. Programme text and the calendars' filter patterns are never read. `async_redact_data` runs over the
finished result as a safety net for a key that someone adds to the allow-list by mistake.

Diagnostics only read the state recorded so far: they never start a refresh or a download, so asking for them while
the source fails or refreshes returns the last recorded state. `last_attempt` is the source's last refresh run with
the same fields, in the same order, as the last-fetch sensor (AUT-06, D-22): vocabulary strings, flags and counts.
"""

import dataclasses
from pathlib import PurePath
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.redact import REDACTED, async_redact_data
from yarl import URL

from .cache import FeedCache, cache_key
from .const import CONF_PATH, CONF_URL
from .xmltv.schedule import SourceOptions

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import HomeAssistant

    from .cache import CacheMeta, RefreshAttempt, SourceHealth
    from .data import XmltvConfigEntry, XmltvRuntimeData

# Safety net, not the mechanism: keys that would carry credentials or raw validators. They are not part of the result,
# and one that shows up anyway is replaced by the redaction marker
TO_REDACT = frozenset({"etag", "last_modified", "password", "username", "token"})


def _redact_url(url: object) -> str:
    """Keep the scheme and host; user info, password, path, query and fragment are dropped."""
    if not isinstance(url, str):
        return REDACTED
    try:
        parsed = URL(url)
    except ValueError:
        return REDACTED
    if not parsed.scheme or not parsed.host:
        return REDACTED
    return f"{parsed.scheme}://{parsed.host}/{REDACTED}"


def _redact_path(path: object) -> str:
    """Keep the file name; the directories are dropped."""
    if not isinstance(path, str):
        return REDACTED
    return f"{REDACTED}/{PurePath(path).name}"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _health(health: SourceHealth) -> dict[str, Any]:
    last_failure = (
        {"time": _iso(health.last_failure_at), "reason": health.last_failure_reason}
        if health.last_failure_at is not None
        else None
    )
    return {
        "last_success": _iso(health.last_success),
        "failing_since": _iso(health.failing_since),
        "last_failure": last_failure,
        "consecutive_failures": health.consecutive_failures,
    }


def _cache(meta: CacheMeta | None) -> dict[str, Any] | None:
    """Describe the cached payload by time, size and validator presence; never the validator values."""
    if meta is None:
        return None
    return {
        "fetched_at": _iso(meta.fetched_at),
        "size": meta.size,
        "has_etag": meta.etag is not None,
        "has_last_modified": meta.last_modified is not None,
    }


def _attempt(attempt: RefreshAttempt | None) -> dict[str, Any] | None:
    return attempt.as_dict() if attempt is not None else None


def _calendars(entry: XmltvConfigEntry, runtime: XmltvRuntimeData) -> list[dict[str, Any]]:
    """
    Return title and counts of every calendar of the source, sorted by title; no filter settings.

    `matches` counts the feed's matches, `retained` the past matches shown from the store in addition (D-19).
    """
    rows = []
    for subentry_id, matcher in runtime.matchers.items():
        subentry = entry.subentries.get(subentry_id)
        rows.append(
            {
                "title": subentry.title if subentry is not None else subentry_id,
                "matches": matcher.match_count,
                "retained": matcher.retained_count,
            }
        )
    return sorted(rows, key=lambda row: row["title"])


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: XmltvConfigEntry) -> dict[str, Any]:
    """
    Return the diagnostics of a source entry from a snapshot of its current state (D-21).

    An entry that is not loaded (for example SETUP_RETRY) has no coordinator: its options are read from the entry and
    its health, last run and cache metadata from the Store, so a source that never loaded can still be diagnosed.
    """
    source = async_redact_data(dict(entry.data), {CONF_URL: _redact_url, CONF_PATH: _redact_path})
    runtime: XmltvRuntimeData | None = getattr(entry, "runtime_data", None)
    if runtime is None:
        cache = FeedCache(hass, cache_key(entry))
        await cache.async_load()
        result: dict[str, Any] = {
            "loaded": False,
            "source": source,
            "options": SourceOptions.from_mapping(entry.options).as_options(),
            "health": _health(cache.health),
            "last_attempt": _attempt(cache.attempt),
            "cache": _cache(cache.meta),
            "stats": None,
            "calendars": [],
            "next_refresh": None,
        }
        return async_redact_data(result, TO_REDACT)
    coordinator = runtime.coordinator
    data = coordinator.data
    result = {
        "loaded": True,
        "source": source,
        "options": coordinator.source_options.as_options(),
        "health": _health(coordinator.health),
        "last_attempt": _attempt(coordinator.last_attempt),
        "cache": _cache(coordinator.cache_meta),
        "stats": dataclasses.asdict(data.stats) if data is not None else None,
        "calendars": _calendars(entry, runtime),
        "next_refresh": _iso(coordinator.next_refresh_at),
    }
    return async_redact_data(result, TO_REDACT)
