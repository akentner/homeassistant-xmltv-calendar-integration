---
phase: 03-resilient-sources
plan: 07
subsystem: diagnostics
tags: [home-assistant, diagnostics, redaction, async_redact_data, yarl, tdd]

requires:
  - phase: 03-resilient-sources
    provides: "coordinator.source_options (03-01), cache_meta (03-02), health + stored SourceHealth (03-04), next_refresh_at (03-01)"
provides:
  - "diagnostics.py: async_get_config_entry_diagnostics with allow-listed keys loaded, source, options, health, cache, stats, calendars, next_refresh"
  - "_redact_url (scheme + host only) and _redact_path (file name only); TO_REDACT safety net"
  - "XmltvCalendarEntity.match_count (len of the MatchIndex)"
  - "Diagnostics for entries that are not loaded (SETUP_RETRY): options from the entry, health/cache from the Store"
affects: [03-08, phase-04, bug-reports]

actuals:
  tokens: 3535
  tasks: 2
  commits: 4
plan_head_before: 447579ca1c1f0d2c0e884f2bad18741d59f95e56
plan_head_after: 83cd920b5826d9a086e992e2efb18e17a6e5cec3

tech-stack:
  added: []
  patterns:
    - "Diagnostics as an allow-list ('structure, never content'), async_redact_data with a key->callable mapping for the source block and a key set as safety net over the result"
    - "Not-loaded entries read state through a fresh FeedCache(hass, cache_key(entry)).async_load(); loaded entries read coordinator properties only (no awaits, no network)"

key-files:
  created:
    - custom_components/xmltv_calendar/diagnostics.py
    - tests/test_diagnostics.py
    - .planning/phases/03-resilient-sources/tdd-evidence/03-07-red.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-07-red.xml
    - .planning/phases/03-resilient-sources/tdd-evidence/03-07-red-2.xml
    - .planning/phases/03-resilient-sources/tdd-evidence/03-07-red-2-notloaded.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-07-red-2-loaded.json
  modified:
    - custom_components/xmltv_calendar/calendar.py

key-decisions:
  - "03-07: diagnostics keys fixed: loaded, source, options, health {last_success, failing_since, last_failure {time, reason} | None, consecutive_failures}, cache {fetched_at, size, has_etag, has_last_modified} | None, stats (ParseStats asdict) | None, calendars [{title, matches}] sorted by title, next_refresh"
  - "03-07: calendar titles come from entry.subentries[subentry_id].title (subentry id as fallback), so no filter data is read"
  - "03-07: not-loaded entries (no runtime_data) report options via SourceOptions.from_mapping(entry.options), health and cache presence from the Store, stats None, calendars [], next_refresh None"
  - "03-07: _redact_url / _redact_path return **REDACTED** for non-string or host-less values instead of raising"

patterns-established:
  - "Diagnostics read a snapshot only: never a refresh or download (test_diagnostics_never_refresh asserts HTTP call count and data identity)"

requirements-completed: [SRC-12]

coverage:
  - id: D1
    description: "Diagnostics download for a URL source with URL reduced to scheme and host, effective options, health, cache presence flags, parse stats, per-calendar match counts and next refresh; no credentials, token, path, ETag value or programme text"
    requirement: SRC-12
    verification:
      - kind: integration
        ref: "tests/test_diagnostics.py#test_diagnostics_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "File source diagnostics show only the file name; no cache block; full directory absent"
    requirement: SRC-12
    verification:
      - kind: integration
        ref: "tests/test_diagnostics.py#test_file_source_diagnostics"
        status: pass
    human_judgment: false
  - id: D3
    description: "Failing source: consecutive failures, failing_since, last failure time and reason, stats of the last good data"
    requirement: SRC-12
    verification:
      - kind: integration
        ref: "tests/test_diagnostics.py#test_failing_source_diagnostics"
        status: pass
    human_judgment: false
  - id: D4
    description: "Entry in SETUP_RETRY returns loaded False, redacted source, options and stored health without raising"
    requirement: SRC-12
    verification:
      - kind: integration
        ref: "tests/test_diagnostics.py#test_diagnostics_for_not_loaded_entry"
        status: pass
    human_judgment: false
  - id: D5
    description: "Diagnostics never refresh or download (snapshot only)"
    requirement: SRC-12
    verification:
      - kind: integration
        ref: "tests/test_diagnostics.py#test_diagnostics_never_refresh"
        status: pass
    human_judgment: false
  - id: D6
    description: "skipped_malformed reported (Phase 1 review WR-08) and option defaults filled in for older entries"
    requirement: SRC-12
    verification:
      - kind: integration
        ref: "tests/test_diagnostics.py#test_skipped_malformed_is_reported"
        status: pass
      - kind: integration
        ref: "tests/test_diagnostics.py#test_daily_and_timezone_options_are_shown"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-10-16
status: complete
---

# Phase 3 Plan 07: Source Diagnostics Summary

**Config entry diagnostics per source (SRC-12): URL cut to scheme+host or path to file name, effective schedule/timezone options, failure health, cache presence flags, ParseStats incl. skipped_malformed and per-calendar match counts, also for entries stuck in SETUP_RETRY**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-16T11:12:32Z
- **Completed:** 2026-10-16T11:16:33Z
- **Tasks:** 2 (Task 1 tracer, Task 2 TDD)
- **Files modified:** 8 (2 source, 1 test, 5 RED evidence)

## Accomplishments

- `diagnostics.py` with `async_get_config_entry_diagnostics`. The result is built from an allow-list. `async_redact_data` gets `{CONF_URL: _redact_url, CONF_PATH: _redact_path}` for the source block, and `TO_REDACT` (`etag`, `last_modified`, `password`, `username`, `token`) runs over the finished result as a safety net.
- The diagnostics show the cache by `fetched_at`, `size`, `has_etag` and `has_last_modified` only. The raw validators are never included.
- `XmltvCalendarEntity.match_count` gives the per-calendar match counts. Calendars are sorted by subentry title, and no filter patterns are read.
- Entries that are not loaded still return the redacted source, the effective options and the stored health, read from the Store. This is the case where a bug report is most needed.

## Task Commits

1. **Task 1 (tracer): URL source diagnostics end-to-end**
   - RED `3396b67` (test)
   - GREEN `17e064e` (feat)
2. **Task 2: file, failing, not-loaded, malformed and option cases**
   - RED `a10c624` (test)
   - GREEN `83cd920` (feat)

**Plan metadata:** see the final docs(03-07) commit.

## TDD Gate Compliance

- **RED 1** (`03-07-red.json`, RED_EVIDENCE_OK): `test_diagnostics_end_to_end` failed on the phcc helper's `assert 404 == HTTPStatus.OK`, because there was no diagnostics platform yet.
  - Semantic assessment: this is the planned failure reason. Setup and the diagnostics component both loaded; there was no fixture or import fault.
- **RED 2** (`03-07-red-2-notloaded.json`, RED_EVIDENCE_OK): `test_diagnostics_for_not_loaded_entry` failed with `AttributeError: 'MockConfigEntry' object has no attribute 'runtime_data'` inside the diagnostics call.
  - This is the planned failure. The entry reached SETUP_RETRY as asserted before the call.
- **RED 2b** (`03-07-red-2-loaded.json`, RED_EVIDENCE_OK): `test_diagnostics_never_refresh` failed with `KeyError: 'loaded'`, because the loaded flag was still missing.
- **Regression guards:** these were already green at RED 2, since Task 1's builder already covered them:
  - `test_file_source_diagnostics`
  - `test_failing_source_diagnostics`
  - `test_skipped_malformed_is_reported`
  - `test_daily_and_timezone_options_are_shown` (both parameter cases)
- **GREEN:** `17e064e` and `83cd920` both pass. There was no refactor commit (none needed).
- **Tracer gate:** the run was interactive in `end-of-phase` mode with an automated-only verify. The Task 1 verify was re-run, passed, and execution expanded to Task 2.

## Files Created/Modified

- `custom_components/xmltv_calendar/diagnostics.py`: allow-listed, redacted diagnostics for loaded and not-loaded entries.
- `custom_components/xmltv_calendar/calendar.py`: `match_count` property.
- `tests/test_diagnostics.py`: 8 tests (end-to-end via the HTTP view, plus direct calls).
- `.planning/phases/03-resilient-sources/tdd-evidence/03-07-*`: RED reports and records.

## Decisions Made

- Calendar titles come from `entry.subentries[...]`, not from entity internals. Only `match_count` is new on the entity.
- For an option entry stored as daily, `refresh_hours` stays in `options`, because `as_options()` always includes it. The daily test therefore compares only the keys it sets.
- The redaction helpers never raise on hand-edited data (non-string or host-less values become `**REDACTED**`).

## Deviations from Plan

None. The plan was executed as written. The only extra was a second RED record (`03-07-red-2-loaded.json`) for the second target that failed in RED 2.

## Issues Encountered

- In the first full-suite run I passed `-p no:logging`, which broke every `caplog` test with "recursive dependency". This came from my command line, not the code. A rerun without the flag gave 784 passed, 1 skipped.
- During the end-to-end test, aiohttp's access logger logs a `TypeError` under `freeze_time`, from its local-time cache. It is logged, not raised, and does not affect results.

## Threat Model Coverage

- T-03-22 is mitigated by `_redact_url`, `_redact_path` and the presence flags. Negative `json.dumps` checks cover `hunter2`, `user:`, `s3cret`, `guide.xml`, the ETag value and the tmp directory.
- T-03-23 is mitigated by the allow-list. `Tagesschau` and `No start` (programme text) are asserted absent, and no filter keys are read.
- T-03-SC: no packages added.

## User Setup Required

None. No external service configuration required.

## Next Phase Readiness

- SRC-12 is done. 03-08 is the last plan of Phase 3.
- A manual check (downloading diagnostics from the HA UI on ha-dev) is optional. HA's own diagnostics view already serves the result end-to-end in `test_diagnostics_end_to_end`.

## Verification

- `uv run pytest -q -m "not benchmark"`: 784 passed, 1 skipped, 4 deselected.
- `uv run ruff check . && uv run ruff format --check .`: all checks passed, 61 files formatted.

---
*Phase: 03-resilient-sources*
*Completed: 2026-10-16*

## Self-Check: PASSED
