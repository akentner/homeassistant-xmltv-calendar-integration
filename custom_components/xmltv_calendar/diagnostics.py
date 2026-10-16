"""
Diagnostics of a source entry: structure, state and counts, never feed content or filter patterns (SRC-12, D-21).

The file is meant to be attached to a bug report, so the result is built from an allow-list: every key is written here
by name. The URL keeps its scheme and host only, a local path its file name only, and the cache validators are reported
as presence flags. Programme text and the calendars' filter patterns are never read. `async_redact_data` runs over the
finished result as a safety net for a key that someone adds to the allow-list by mistake.

Diagnostics only read the state recorded so far: they never start a refresh or a download, so asking for them while
the source fails or refreshes returns the last recorded state.
"""

import dataclasses
from pathlib import PurePath
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.redact import REDACTED, async_redact_data
from yarl import URL

from .const import CONF_PATH, CONF_URL

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import HomeAssistant

    from .cache import CacheMeta, SourceHealth
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


def _calendars(entry: XmltvConfigEntry, runtime: XmltvRuntimeData) -> list[dict[str, Any]]:
    """Return title and match count of every calendar of the source, sorted by title; no filter settings."""
    rows = []
    for subentry_id, entity in runtime.calendars.items():
        subentry = entry.subentries.get(subentry_id)
        rows.append({"title": subentry.title if subentry is not None else subentry_id, "matches": entity.match_count})
    return sorted(rows, key=lambda row: row["title"])


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: XmltvConfigEntry) -> dict[str, Any]:  # noqa: ARG001
    """Return the diagnostics of a source entry from a snapshot of its current state (D-21)."""
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    data = coordinator.data
    result = {
        "source": async_redact_data(dict(entry.data), {CONF_URL: _redact_url, CONF_PATH: _redact_path}),
        "options": coordinator.source_options.as_options(),
        "health": _health(coordinator.health),
        "cache": _cache(coordinator.cache_meta),
        "stats": dataclasses.asdict(data.stats) if data is not None else None,
        "calendars": _calendars(entry, runtime),
        "next_refresh": _iso(coordinator.next_refresh_at),
    }
    return async_redact_data(result, TO_REDACT)
