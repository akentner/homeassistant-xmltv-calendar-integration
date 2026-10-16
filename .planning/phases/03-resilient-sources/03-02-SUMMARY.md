---
phase: 03-resilient-sources
plan: 02
subsystem: caching
tags: [disk-cache, ha-store, stale-while-revalidate, data-update-coordinator, etag, tdd]

requires:
  - phase: 03-resilient-sources
    provides: "03-01 schedule maths (is_fresh, fresh_until, next_regular, MIN_DELAY), coordinator wall-clock target, per-test temporary config dir"
provides:
  - "cache.py: FeedCache (raw payload in cache_path, CacheMeta in a private Store), cache_key(entry), CacheMeta.as_dict/from_dict"
  - "source.py: Fetched(payload, etag, last_modified), clean_validator, MAX_VALIDATOR_LENGTH; async_fetch_url returns Fetched"
  - "coordinator: first refresh from a valid cache (fresh: no network; stale: refresh ~1 s later), cache write after a non-empty parse, unusable caches dropped, property cache_meta"
  - "__init__.py: async_remove_entry deletes payload and Store"
  - "calendar.py: XmltvCalendarEntity.available = coordinator.data is not None"
affects: [03-03 conditional requests, 03-04 backoff and health, 03-06 options flow, 03-07 diagnostics]

actuals:
  tokens: 7537       # chars/4 over the realized code + test diff; the committed RED evidence (JUnit XML/JSON) adds ~15.5k more (22991 incl. evidence)
  tasks: 3
  commits: 6
plan_head_before: 1f3fc9c979de18845767f202accd317557993d07
plan_head_after: 0c38e9f354c0f40e326d03ccdf55c3d71048e8dd

tech-stack:
  added: []
  patterns:
    - "Payload first, metadata second: write_utf8_file(private=True, mode='wb') replaces the payload atomically, then Store.async_save; a size mismatch means no cache"
    - "Cache validity = stored source_id equals source_unique_id(source_type, locator) of the current entry data AND the payload has exactly the stored size"
    - "Stale-while-revalidate first refresh: any valid cache is parsed and returned; stale sets _next_refresh_at = now so the _schedule_refresh override arms a 1 s refresh"
    - "Every module-level helper the tests patch (parse, write_utf8_file) is looked up at call time"

key-files:
  created:
    - custom_components/xmltv_calendar/cache.py
    - tests/test_cache.py
  modified:
    - custom_components/xmltv_calendar/source.py
    - custom_components/xmltv_calendar/coordinator.py
    - custom_components/xmltv_calendar/__init__.py
    - custom_components/xmltv_calendar/calendar.py
    - tests/test_init.py

key-decisions:
  - "Cache key: entry.unique_id, else entry_id, when it fully matches [0-9A-Za-z]{1,64}; otherwise its SHA-256 hex (no path separator can reach a file name)"
  - "Store 'xmltv_calendar.<key>' holds {meta: {source_id, size, sha256, fetched_at, etag, last_modified}} only; no URL, path or query"
  - "Stale-while-revalidate at start (RESEARCH A5): setup touches the network only without a usable cache; a stale cache is shown at once and refreshed ~1 s after the first calendar subscribes"
  - "A cached payload that is missing, wrong-size, unparsable or empty is dropped (file deleted, meta saved as None) before the unconditional download"
  - "Calendars are available while coordinator.data is not None, independent of last_update_success (D-19 first half)"
  - "Validators stored only when non-empty, <= 1024 chars, printable ASCII 0x20..0x7E (no CR/LF); re-cleaned when read back from the Store"

patterns-established:
  - "test_cache.py _restart(): unload + async_setup with the same hass_storage and config dir stands in for an HA restart"
  - "_serve(aioclient_mock, ...): clear_requests() + re-register to change the response mid-test"

requirements-completed: [SRC-06]

coverage:
  - id: D1
    description: "After an HA restart or an entry reload, a fresh cache fills the calendars with zero HTTP requests"
    requirement: SRC-06
    verification:
      - kind: integration
        ref: "tests/test_cache.py#test_restart_uses_fresh_cache"
        status: pass
      - kind: integration
        ref: "tests/test_cache.py#test_reload_uses_fresh_cache"
        status: pass
    human_judgment: false
  - id: D2
    description: "Changing a source's options reloads the entry and re-parses the fresh cache without a download; next refresh at fetched_at + 12 h"
    requirement: SRC-06
    verification:
      - kind: integration
        ref: "tests/test_init.py#test_options_change_reloads_once"
        status: pass
    human_judgment: false
  - id: D3
    description: "Cache trusted only when it matches the source and its size; a corrupt cache is deleted and re-downloaded unconditionally; an empty parse is never cached"
    requirement: SRC-06
    verification:
      - kind: integration
        ref: "tests/test_cache.py#test_size_mismatch_redownloads"
        status: pass
      - kind: integration
        ref: "tests/test_cache.py#test_missing_payload_redownloads"
        status: pass
      - kind: integration
        ref: "tests/test_cache.py#test_corrupt_cached_payload_is_dropped"
        status: pass
      - kind: integration
        ref: "tests/test_cache.py#test_changed_source_ignores_cache"
        status: pass
      - kind: integration
        ref: "tests/test_cache.py#test_empty_parse_is_not_cached"
        status: pass
    human_judgment: false
  - id: D4
    description: "Cache is private (0o600), URL-free in the Store and logs, cleans ETag/Last-Modified, uses filesystem-safe keys, and a write failure is tolerated"
    verification:
      - kind: integration
        ref: "tests/test_cache.py#test_payload_is_private"
        status: pass
      - kind: integration
        ref: "tests/test_cache.py#test_store_holds_no_url"
        status: pass
      - kind: integration
        ref: "tests/test_cache.py#test_validators_are_cleaned"
        status: pass
      - kind: unit
        ref: "tests/test_cache.py#test_cache_key_is_filesystem_safe"
        status: pass
      - kind: integration
        ref: "tests/test_cache.py#test_cache_write_failure_is_tolerated"
        status: pass
    human_judgment: false
  - id: D5
    description: "Removing a source entry deletes its payload file and its Store"
    requirement: SRC-06
    verification:
      - kind: integration
        ref: "tests/test_cache.py#test_remove_entry_deletes_cache"
        status: pass
    human_judgment: false
  - id: D6
    description: "Stale cache (interval elapsed or daily slot missed) is shown at once and refreshed ~1 s later; a fresh daily cache waits for the next slot; stale + offline still loads and stays available"
    requirement: SRC-06
    verification:
      - kind: integration
        ref: "tests/test_cache.py#test_stale_cache_shown_then_refreshed"
        status: pass
      - kind: integration
        ref: "tests/test_cache.py#test_missed_daily_slot_refreshes_at_start"
        status: pass
      - kind: integration
        ref: "tests/test_cache.py#test_fresh_daily_cache_does_not_refresh"
        status: pass
      - kind: integration
        ref: "tests/test_cache.py#test_stale_cache_offline_start_still_loads"
        status: pass
      - kind: integration
        ref: "tests/test_source.py#test_fetch_failures_retry_setup"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-10-16
status: complete
---

# Phase 3 Plan 02: Disk Cache and Stale-While-Revalidate Start Summary

**Each URL source now caches its raw feed on disk: a private payload file under `.cache` plus URL-free metadata in an HA Store. An HA restart, an entry reload or an options change fills the calendars from that cache with no download while it is fresh. A stale cache is shown at once and refreshed about 1 s later, so an unreachable host never blocks or fails setup when cached data exists.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-10-16T10:16:13Z
- **Completed:** 2026-10-16T10:24:23Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 7 source/test files, plus 9 RED evidence files

## Accomplishments

- **Restart and reload without a download (SRC-06, D-08):**
  - The first refresh parses a cache that belongs to the entry's current source and has its stored size. There is no network call.
  - An options change (D-16 path) re-parses the cache too. `test_options_change_reloads_once` now expects no new request.
- **Stale-while-revalidate start (D-09, D-03, RESEARCH Pattern 3):**
  - A stale cache, including one that missed a daily slot, is shown at once.
  - `_next_refresh_at = now` arms the network refresh 1 s after the first calendar subscribes.
  - Stale cache with the source offline: the entry is LOADED and the calendars keep the cached events.
  - No cache with a failed first download: still `ConfigEntryNotReady`.
- **Cache integrity (T-03-05):**
  - Written only after a parse with at least one programme.
  - A missing, wrong-size, unparsable or empty payload is deleted (`async_drop`), followed by an unconditional download.
  - Payload first, metadata second, so a crash leaves a size mismatch that is never trusted.
- **Privacy and safety (T-03-03, T-03-04, T-03-07, T-03-08):**
  - Payload mode is 0o600.
  - The Store holds `source_id` (a hash), size, sha256, time and the cleaned validators. No URL.
  - Cache keys are limited to `[0-9A-Za-z]{1,64}` or replaced by SHA-256.
  - ETag and Last-Modified are dropped unless they are at most 1024 printable ASCII characters.
- **Cleanup and availability:**
  - `async_remove_entry` deletes the payload and the Store.
  - Calendars stay available while last good data exists (D-19).

## Task Commits

1. **Task 1: Tracer, restart and reload from the disk cache**
   - RED `cad4925` (test)
   - GREEN `8129491` (feat)
2. **Task 2: Cache validity, privacy, removal**
   - RED `6960ff7` (test)
   - GREEN `98d8adf` (feat)
3. **Task 3: Stale-while-revalidate and offline start**
   - RED `4c41b0d` (test)
   - GREEN `0c38e9f` (feat)

No REFACTOR commits; no cleanup was needed.

## TDD Gate Compliance

| Gate | Task 1 | Task 2 | Task 3 |
|------|--------|--------|--------|
| RED commit before GREEN | `cad4925` before `8129491` | `6960ff7` before `98d8adf` | `4c41b0d` before `0c38e9f` |
| RED classifier | `03-02-red.json`: RED_EVIDENCE_OK (target_test_failed) | `03-02-red-2-corrupt.json`, `03-02-red-2-remove.json`: RED_EVIDENCE_OK | `03-02-red-3-stale.json`, `03-02-red-3-offline.json`: RED_EVIDENCE_OK |
| GREEN | Verify set 26 passed; full suite 645 passed | 49 passed | Full suite 675 passed, 1 skipped |

**Tracer feedback gate (Task 1):**
- The run was interactive in `end-of-phase` mode, and the verify step is automated only.
- The verify step re-ran green (26 passed), so execution continued with no checkpoint.

**RED semantic assessments:**
- **Task 1:** `test_restart_uses_fresh_cache` set up normally (1 request, 4 summaries), then failed on the planned request-count assertion after the restart (`assert 2 == 1`). `test_reload_uses_fresh_cache` failed the same way. JUnit errors=0.
- **Task 2:**
  - `test_corrupt_cached_payload_is_dropped` reached SETUP_RETRY with 1 request as expected. It then failed on `assert not path.exists()`: the unparsable payload was ignored but not deleted.
  - `test_remove_entry_deletes_cache` failed on `assert not path.exists()` after `async_remove`, because there was no `async_remove_entry`.
  - JUnit errors=0.
- **Task 3:**
  - `test_stale_cache_shown_then_refreshed` failed on the planned "no request right after setup" assertion (`assert 1 == 0`), because a stale cache was skipped and downloaded during setup.
  - `test_missed_daily_slot_refreshes_at_start` failed the same way.
  - `test_stale_cache_offline_start_still_loads` failed on the entry state (SETUP_RETRY, expected LOADED).
  - JUnit errors=0.
- **Regression guards:** these tests were already green after Task 1, by design:
  - Task 2: `test_size_mismatch_redownloads`, `test_missing_payload_redownloads`, `test_changed_source_ignores_cache`, `test_empty_parse_is_not_cached`, `test_cache_write_failure_is_tolerated`, `test_payload_is_private`, `test_store_holds_no_url`, `test_validators_are_cleaned` (14 rows), `test_cache_key_is_filesystem_safe` (3 rows).
  - Task 3: `test_fresh_daily_cache_does_not_refresh`.

## Files Created/Modified

- `custom_components/xmltv_calendar/cache.py` (new): `STORE_VERSION`, `cache_key`, `CacheMeta`, and `FeedCache` with `async_load`, `meta`, `valid_meta`, `async_read`, `async_write`, `async_drop` and `async_remove`.
- `custom_components/xmltv_calendar/source.py`: `Fetched`, `MAX_VALIDATOR_LENGTH`, `clean_validator`; `async_fetch_url` returns `Fetched`.
- `custom_components/xmltv_calendar/coordinator.py`: `_cache`, `_source_id`, `_async_setup`, `_set_regular_target`, `_async_start_from_cache`, `_parser`, `_async_parse_payload`, `_async_parse_cached` and `cache_meta`. Each outcome sets exactly one refresh target.
- `custom_components/xmltv_calendar/__init__.py`: `async_remove_entry`.
- `custom_components/xmltv_calendar/calendar.py`: `available` override.
- `tests/test_cache.py` (new): 22 test functions (37 cases).
- `tests/test_init.py`: `test_options_change_reloads_once` expects no download.
- `.planning/phases/03-resilient-sources/tdd-evidence/03-02-*`: RED JUnit reports and records.

## Decisions Made

- The cache key is `unique_id`, else `entry_id`, hashed when it is not `[0-9A-Za-z]{1,64}`. `MockConfigEntry` test entries have no `unique_id`, so tests use the `entry_id`.
- `CacheMeta.from_dict` re-applies `clean_validator`, so a hand-edited Store cannot inject header values.
- `FeedCache._read` reads `size + 1` bytes, so an oversized file is detected without reading all of it.
- On a failed `async_write` the in-memory metadata is cleared, so this coordinator never pairs old metadata with a new payload.
- `_feed_errors` debug logs also appear for an unparsable cached payload (`Source <title> returned an invalid feed`). They name the entry title, not the URL.
- A file source also builds a `FeedCache`, but the cache is used and written only on the URL path. `async_remove_entry` is harmless for file entries.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_options_change_reloads_once` updated in Task 1 instead of Task 2**
- **Found during:** Task 1 (GREEN verify)
- **Issue:** The tracer already makes an options reload re-parse the fresh cache. The plan's Task 1 verify, which includes `tests/test_init.py`, therefore failed on the old `calls + 1` assertion.
  - Task 2 planned to change that assertion and produce a RED record, `03-02-red-2-options.json`.
  - That record cannot be produced honestly: the behavior was already green after Task 1, and a RED record for a passing test would be fabricated.
- **Fix:** The assertion was changed to `calls`, with a comment, in the Task 1 GREEN commit. `03-02-red-2-options.json` was not written. The corrupt and remove records cover Task 2's RED gate.
- **Files modified:** `tests/test_init.py`
- **Verification:** `tests/test_init.py::test_options_change_reloads_once` passes, including `next_refresh_at == NOW + 12 h`.
- **Committed in:** `8129491`

**2. [Rule 1 - Bug] Two test assertions corrected before the RED reports were recorded**
- **Found during:** Task 2 and Task 3 RED runs
- **Issue:**
  - `test_changed_source_ignores_cache` looked for a bare title, but summaries carry the channel prefix ("Das Erste: Tagesthemen").
  - In the stale test, the summaries check sat before the planned "no request right after setup" assertion.
- **Fix:** The assertions were corrected or reordered. The RED runs were then repeated, so the committed JUnit reports and records come from the final test code.
- **Files modified:** `tests/test_cache.py`
- **Committed in:** `6960ff7`, `4c41b0d`

**3. [Rule 3 - Lint] `pathlib` instead of `os.makedirs` in `FeedCache._write`**
- **Found during:** Task 1
- **Issue:** Ruff `select = ["ALL"]` rejects `os.makedirs`/`os.path.dirname` (PTH rules).
- **Fix:** `Path.parent.mkdir(parents=True, exist_ok=True)`. Same behavior.
- **Committed in:** `8129491`

---

**Total deviations:** 3 auto-fixed (1 blocking plan-sequencing issue, 1 test-assertion bug, 1 lint-driven equivalent).
**Impact on plan:** No behavior change from the plan. One planned RED record (`03-02-red-2-options.json`) does not exist, because its behavior was delivered by the tracer.

## Issues Encountered

None.

## User Setup Required

None. No external service configuration required.

## Next Phase Readiness

- 03-03 can send `If-None-Match`/`If-Modified-Since` from `self._cache.valid_meta(self._source_id)`. `Fetched` already carries cleaned validators, and `_async_parse_cached` covers the "304 with no data in memory" case (Pitfall 3).
- 03-04 replaces the failure branch of `_set_regular_target` in the URL/file paths with backoff. It also adds Repairs cleanup to `async_remove_entry`.
- 03-07 diagnostics can read `coordinator.cache_meta`.

## Verification

- `uv run pytest -q -m "not benchmark"`: 675 passed, 1 skipped
- `uv run pytest -q -m benchmark`: 4 passed, 1 skipped
- `uv run ruff check . && uv run ruff format --check .`: clean

## Self-Check: PASSED

- Files found: `cache.py`, `tests/test_cache.py`, 5 RED records (`03-02-red.json`, `-red-2-corrupt`, `-red-2-remove`, `-red-3-stale`, `-red-3-offline`).
- Commits found on HEAD: `cad4925`, `8129491`, `6960ff7`, `98d8adf`, `4c41b0d`, `0c38e9f`.
- TDD gate: 3 `test(03-02)` and 3 `feat(03-02)` commits, each RED before its GREEN.

---
*Phase: 03-resilient-sources*
*Completed: 2026-10-16*
