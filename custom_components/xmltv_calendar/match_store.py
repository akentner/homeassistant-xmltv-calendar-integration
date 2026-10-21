"""
Persisted per-calendar match records of one source (EVT-08 seen-set, D-10).

One Store per source, `xmltv_calendar.matches.<cache key>`, holding one record per calendar subentry. Saves are delayed
and serialized off the event loop, so the records mapping is replaced copy-on-write and never mutated: a pending save
may be reading it in a worker thread. `async_flush` writes at once and must run on unload, because a reload builds a new
Store object that would not see the old object's pending data (RESEARCH Pitfall 3).
"""

import logging
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .xmltv.matches import CalendarMatches, records_from_dict, records_to_dict

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

MATCH_STORE_VERSION = 1
MATCH_STORE_SAVE_DELAY = 10  # seconds


class MatchStore:
    """The match records of all calendars of one source."""

    def __init__(self, hass: HomeAssistant, key: str) -> None:
        """Bind to the Store of `key` (see `cache.cache_key`); the `matches.` infix keeps it apart from the cache."""
        self._key = key
        self._store: Store[dict[str, Any]] = Store(
            hass, MATCH_STORE_VERSION, f"{DOMAIN}.matches.{key}", private=True, serialize_in_event_loop=False
        )
        self._records: Mapping[str, CalendarMatches] = {}
        self._fingerprint: Mapping[str, object] = {}

    async def async_load(self, fingerprint: Mapping[str, object]) -> None:
        """
        Load the records; stored data that is unreadable or malformed counts as none.

        `fingerprint` holds the source's timezone options. Retained programmes carry times corrected with the options
        they were parsed under, so when the stored fingerprint differs they are all dropped; the seen-sets are kept
        (RESEARCH Open Question 2).
        """
        try:
            data = await self._store.async_load()
        except HomeAssistantError as err:
            _LOGGER.debug("Match store %s unreadable: %s", self._key, type(err).__name__)
            data = None
        self._fingerprint = dict(fingerprint)
        records = records_from_dict(data)
        stored = data.get("source") if isinstance(data, dict) else None
        if stored is not None and stored != self._fingerprint:
            records = {sid: replace(record, retained=()) for sid, record in records.items()}
        self._records = records

    def get(self, subentry_id: str) -> CalendarMatches:
        """Return the calendar's record, an empty one when there is none."""
        return self._records.get(subentry_id) or CalendarMatches()

    def put(self, subentry_id: str, record: CalendarMatches) -> None:
        """Replace the calendar's record and schedule a delayed save."""
        self._records = {**self._records, subentry_id: record}
        self._store.async_delay_save(self._data_to_save, MATCH_STORE_SAVE_DELAY)

    def forget(self, subentry_id: str) -> None:
        """Drop the record of a removed calendar and schedule a delayed save."""
        if subentry_id in self._records:
            self._records = {sid: record for sid, record in self._records.items() if sid != subentry_id}
            self._store.async_delay_save(self._data_to_save, MATCH_STORE_SAVE_DELAY)

    def retain_only(self, subentry_ids: Iterable[str]) -> None:
        """Drop the records of calendars that no longer exist, e.g. removed while the entry was not loaded."""
        keep = set(subentry_ids)
        if not keep.issuperset(self._records):
            self._records = {sid: record for sid, record in self._records.items() if sid in keep}
            self._store.async_delay_save(self._data_to_save, MATCH_STORE_SAVE_DELAY)

    def _data_to_save(self) -> dict[str, Any]:
        # Runs in a worker thread: read the mapping once, it is never mutated after being replaced
        return {**records_to_dict(self._records), "source": dict(self._fingerprint)}

    async def async_flush(self) -> None:
        """Write the records now, cancelling a pending delayed save; a failed save is logged at DEBUG only."""
        try:
            await self._store.async_save(self._data_to_save())
        except (OSError, HomeAssistantError) as err:
            _LOGGER.debug("Match store %s not saved: %s", self._key, type(err).__name__)

    async def async_remove(self) -> None:
        """Delete the stored records with the source; a failed removal is logged at DEBUG only."""
        self._records = {}
        try:
            await self._store.async_remove()
        except (OSError, HomeAssistantError) as err:
            _LOGGER.debug("Match store %s not removed: %s", self._key, type(err).__name__)
