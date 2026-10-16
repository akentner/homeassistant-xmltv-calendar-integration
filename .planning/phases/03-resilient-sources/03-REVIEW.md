---
phase: 03-resilient-sources
reviewed: 2026-10-16T11:42:21Z
depth: standard
files_reviewed: 35
files_reviewed_list:
  - custom_components/xmltv_calendar/__init__.py
  - custom_components/xmltv_calendar/cache.py
  - custom_components/xmltv_calendar/calendar.py
  - custom_components/xmltv_calendar/config_flow.py
  - custom_components/xmltv_calendar/const.py
  - custom_components/xmltv_calendar/coordinator.py
  - custom_components/xmltv_calendar/diagnostics.py
  - custom_components/xmltv_calendar/source.py
  - custom_components/xmltv_calendar/translations/de.json
  - custom_components/xmltv_calendar/translations/en.json
  - custom_components/xmltv_calendar/xmltv/parser.py
  - custom_components/xmltv_calendar/xmltv/schedule.py
  - custom_components/xmltv_calendar/xmltv/timeparse.py
  - tests/conftest.py
  - tests/test_cache.py
  - tests/test_calendar.py
  - tests/test_config_flow.py
  - tests/test_diagnostics.py
  - tests/test_empty_feed.py
  - tests/test_file_source.py
  - tests/test_filtering.py
  - tests/test_identity.py
  - tests/test_init.py
  - tests/test_options_flow.py
  - tests/test_reconfigure.py
  - tests/test_refresh.py
  - tests/test_repairs.py
  - tests/test_schedule_refresh.py
  - tests/test_source.py
  - tests/test_subentry_flow.py
  - tests/test_timezone_options.py
  - tests/test_tracer.py
  - tests/xmltv/test_parser.py
  - tests/xmltv/test_schedule.py
  - tests/xmltv/test_timeparse.py
findings:
  critical: 2
  warning: 3
  info: 5
  total: 10
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-10-16T11:42:21Z
**Depth:** standard
**Files Reviewed:** 35
**Status:** issues_found

## Summary

I reviewed the Phase 3 changes since `bfcd455`: refresh schedule, disk cache, conditional refresh, failure health with Repairs and backoff, timezone options, the setup flow with download progress, diagnostics and the options flow. Integration code was checked against the installed HA 2026.10.1 sources (`helpers/update_coordinator.py`, `config_entries.py`, `util/file.py`, `helpers/redact.py`). The full suite passes (794 passed).

Parsing, file IO and hashing stay off the event loop. Logs and diagnostics name only the host. Translations are complete and consistent between `en.json` and `de.json`.

Two scheduling defects are confirmed with throwaway tests run against the real coordinator. Neither is covered by the existing suite:

- **CR-01:** a daily source often refreshes twice per slot, because HA's coordinator timer can fire up to about 1 s before the target.
- **CR-02:** any unexpected exception in `_async_update_data` makes the coordinator re-download the feed every second. The failure is never recorded, so no backoff and no Repairs issue follow.

There are also three warnings:

- **WR-01:** a source that stops updating is never reported, because the "unchanged" shortcuts skip the empty-feed check.
- **WR-02:** a source set up through the flow reports `last_success: None`.
- **WR-03:** the clock has already passed the fixture dates, so `test_identity.py` now silently tests an entry stuck in SETUP_RETRY.

## Critical Issues

### CR-01: Daily refresh fires before its slot and runs twice (and burns a backoff step on failure)

**File:** `custom_components/xmltv_calendar/coordinator.py:313-317, 324-325, 349-355`
**Issue:** `_schedule_refresh` turns the wall-clock target into `update_interval`. HA then arms the timer at `int(loop.time()) + self._microsecond + interval` (`helpers/update_coordinator.py:283`). Because `int()` truncates and `_microsecond` is only 0.05–0.5 s, the timer fires up to about 0.95 s **before** `_next_refresh_at` in most cases.

- **Interval mode:** harmless.
- **Daily mode, success:** `_set_regular_target()` calls `next_slot(utcnow())`, which returns the first slot strictly after now. If the refresh finishes before the slot (a 304, an unchanged file or a fast download), that is the **same** slot, less than 1 s ahead. `_schedule_refresh` clamps it to `MIN_DELAY`, and a second refresh follows one second later.
- **Daily mode, failure:** a fast failure (DNS error, connection refused, missing file) gets `regular_next - now < 1 s`, so the backoff is `MIN_DELAY`. The source fails twice within a second. `consecutive_failures` goes up by 2, and the first backoff step (5 min) is skipped.

Reproduced with HA's real timer: daily 18:15 Berlin, step to `16:14:59.99Z`. The refresh runs, `next_refresh_at` stays `16:15:00Z`, and stepping to `16:15:01Z` downloads a second time (`call_count` 1 → 2 → 3). `tests/test_schedule_refresh.py` always steps 1 s **past** each target, which hides this.
**Fix:** Derive the next target from the slot that was due, not from the slightly-early `now`:
```python
def _set_regular_target(self) -> None:
    now = dt_util.utcnow()
    # The HA timer may fire up to ~1 s early; never re-target the slot that is being served
    self._next_refresh_at = next_regular(max(now, self._next_refresh_at), self._schedule())

# failure path in _async_update_data
base = max(now, self._next_refresh_at)
self._next_refresh_at = now + backoff_delay(failures, now, next_regular(base, self._schedule()))
```
Add a test that steps to `slot - 0.01 s` and asserts there is exactly one download for the slot.

### CR-02: An unexpected exception retries every second with a full download, unrecorded

**File:** `custom_components/xmltv_calendar/coordinator.py:346-357`
**Issue:** Only `UpdateFailed` updates `_next_refresh_at`, the health and the Repairs issue. Any other exception falls through to HA's generic `except Exception` in `_async_refresh`, which logs a traceback and then calls `_schedule_refresh()`. `_next_refresh_at` still holds the target that was just served (now in the past), so `update_interval = MIN_DELAY` and the source is downloaded again every second, indefinitely.

The parser documents that "other exceptions propagate unchanged". `MemoryError` on a large feed on small hardware is a realistic trigger, and so is any latent bug in `normalize`. Reproduced by patching `coordinator.parse` to raise `MemoryError`: one download per second, `consecutive_failures` stays 0, no backoff, no Repairs issue, and a stack trace every second. That hammers the EPG provider.
**Fix:** Treat every exception as a failure for scheduling and health purposes, and re-raise it as `UpdateFailed`:
```python
try:
    epg = await (self._async_update_file() if is_file else self._async_update_url())
except Exception as err:  # noqa: BLE001 - every failure must back off (D-10)
    now = dt_util.utcnow()
    key = err.translation_key if isinstance(err, UpdateFailed) else _DEFAULT_REASON
    await self._async_record_failure(now, key)
    failures = self._cache.health.consecutive_failures
    self._next_refresh_at = now + backoff_delay(failures, now, next_regular(now, self._schedule()))
    if isinstance(err, UpdateFailed):
        raise
    _LOGGER.debug("Source %s: unexpected %s", self.config_entry.title, type(err).__name__)
    raise UpdateFailed(translation_domain=DOMAIN, translation_key=_DEFAULT_REASON) from err
```
Do not catch `asyncio.CancelledError`: it is not an `Exception` subclass, so the code above already leaves it alone.

## Warnings

### WR-01: "Unchanged" shortcuts skip the empty-feed check, so a feed that stops updating is never reported

**File:** `custom_components/xmltv_calendar/coordinator.py:505-509, 520-529, 571-573`
**Issue:** D-20 says a feed without current programmes fails. That check (`_require_programmes`) runs only after a fresh parse. A 304, an identical body or an unchanged file returns the old `self.data` object and is recorded as a **success**.

A very common real-world failure is a grabber or provider that stops updating: the file keeps its mtime and size, or the server keeps answering 304 for the old ETag. The source then reports success forever and `consecutive_failures` stays 0. No Repairs issue is ever raised, while every calendar quietly runs out of events once the last programme ends.
**Fix:** Before returning the unchanged data, check that it still holds a current programme, using the same cut-off the parser uses:
```python
def _still_current(epg: EpgData) -> bool:
    cutoff = dt_util.utcnow() - KEEP_PAST
    return any(p.stop >= cutoff for p in reversed(epg.programmes))  # sorted by start: the tail ends last

# in each unchanged branch
if not _still_current(self.data):
    raise UpdateFailed(translation_domain=DOMAIN, translation_key="empty_feed")
```
Alternatively, store the feed's maximum `stop` on `EpgData` at parse time and compare against it.

### WR-02: Setup from the flow-seeded cache never records a success (`last_success` stays None)

**File:** `custom_components/xmltv_calendar/coordinator.py:340-345` (with `config_flow.py:344-361`)
**Issue:** The flow downloads the feed and seeds the cache. The first refresh then takes `_async_start_from_cache`, which returns the data without calling `_async_record_success`.

Verified: right after the flow, `coordinator.health` is `SourceHealth(last_success=None, ...)`, and diagnostics report `"last_success": null` with 4 programmes loaded. If the first scheduled refresh (up to 168 h or a day later) starts a failure streak, the Repairs issue shows "Last successful refresh: -" even though the setup download succeeded. Diagnostics also look like a source that has never worked.
**Fix:** Record the seeded fetch as a success. Either have `_async_seed_cache` write `SourceHealth(last_success=fetched_at)` along with the payload, or have `_async_start_from_cache` set `last_success = meta.fetched_at` when `health.last_success is None` or is older than `meta.fetched_at`.

### WR-03: `test_identity.py` is unfrozen and its fixtures have expired, so it tests an entry in SETUP_RETRY

**File:** `tests/test_identity.py:52-121`
**Issue:** These are the only fixture-based integration tests without `freeze_time`. `fixtures/basic.xml` holds programmes on 2026-10-13, and today (2026-10-16) the parser's `keep_after = now - 1 day` drops all of them. The seeded cache is dropped and re-downloaded, and setup fails with `empty_feed`.

Verified: after `test_url_variant_identity_invariant`'s flow, `entry.state` is `SETUP_RETRY` and the feed was downloaded twice. The tests still pass because they only assert on flow results, but they no longer exercise a loaded source, and they leave a setup retry pending.
**Fix:** Add `pytestmark = pytest.mark.freeze_time("2026-10-13T06:00:00+00:00")`, as the other modules do. Optionally assert `entry.state is ConfigEntryState.LOADED` so the suite fails loudly the next time time-dependent data expires.

## Info

### IN-01: Repairs issue survives unload and disable of the entry

**File:** `custom_components/xmltv_calendar/__init__.py:56-58`
**Issue:** `async_unload_entry` keeps the `source_failing_<entry_id>` issue. A user who disables a failing source keeps seeing "keeps failing" until HA restarts (the issue is non-persistent). Only `async_remove_entry` deletes it.
**Fix:** Call `ir.async_delete_issue(hass, DOMAIN, issue_id(entry.entry_id))` after a successful unload. `_sync_issue` re-creates it on the next failure after setup or restart anyway.

### IN-02: Cache seeding writes before the duplicate check of `async_create_entry`

**File:** `custom_components/xmltv_calendar/config_flow.py:333-335, 353`
**Issue:** `_async_seed_cache` runs before `async_create_entry`. The duplicate check at url-step time can be outdated by then: the download can take up to 5 min and the user can wait at the schedule/name steps. If a second flow for the same source finishes first, this flow overwrites that entry's payload and Store (same key) and is then aborted as `already_configured`. The live coordinator's in-memory meta then disagrees with disk. The seed also builds the key directly from `self.unique_id` instead of going through `cache_key()`, which bypasses the file-name safety check (safe today only because the unique_id is always SHA-256 hex).
**Fix:** Call `self._abort_if_unique_id_configured()` again right before seeding, and derive the key through a shared helper (e.g. `cache_key_for(unique_id)`) instead of passing the raw unique_id.

### IN-03: `sha256` is stored but never verified on read

**File:** `custom_components/xmltv_calendar/cache.py:218-231`
**Issue:** The module docstring presents the size check as the integrity guarantee. `_read` checks only the length, and `CacheMeta.sha256` is used only for the identical-body shortcut. A same-size corrupted or foreign payload is accepted and parsed, and `_async_parse_cached` only drops it if parsing fails or finds no programmes.
**Fix:** Verify `payload_sha256(payload) == meta.sha256` in `_read` (already in the executor), or document that the hash serves only the identical-body comparison.

### IN-04: 304 path without data reads the cache without the source check

**File:** `custom_components/xmltv_calendar/coordinator.py:510-514`
**Issue:** `_async_parse_cached()` reads whatever `self._cache.meta` refers to. Unlike `_async_start_from_cache`, it never checks `valid_meta(self._source_id)`. The branch can only be reached when a server answers 304 to an unconditional request (`meta` was None, so no validators were sent). In that case a cache from a different source would be adopted and touched.
**Fix:** Guard with `if self._cache.valid_meta(self._source_id) is not None` before parsing the cache, or treat a 304 to a request without validators as `unable_to_fetch` right away.

### IN-05: Diagnostics report `next_refresh` even when no timer is armed

**File:** `custom_components/xmltv_calendar/diagnostics.py:331`
**Issue:** `coordinator.next_refresh_at` is reported unconditionally. A source with no calendars has no listeners, so HA never arms the refresh timer, yet diagnostics show a concrete next-refresh time. That is misleading in a bug report.
**Fix:** Report `None` (or add `"polling": False`) when `not coordinator._listeners`, or expose a public `is_polling` property on the coordinator.

---

_Reviewed: 2026-10-16T11:42:21Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
