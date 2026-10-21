---
phase: 04-automation-extras-release
plan: 05
subsystem: diagnostics
tags: [home-assistant, sensor, diagnostics, storage, dispatcher, data-update-coordinator, last-fetch]

requires:
  - phase: 04-automation-extras-release
    provides: "04-01: sensor platform with async_add_subentry_sensors, device_info, signal_matches, entity translations"
  - phase: 03-resilient-sources
    provides: "FeedCache Store {meta, health}, SourceHealth, FAILURE_REASONS, refresh targets and backoff, diagnostics allow-list"
provides:
  - "cache.py: ATTEMPT_TRIGGERS/OUTCOMES/CACHE, RefreshAttempt (as_dict fixed order, strict tolerant from_dict), FeedCache.attempt, async_save_attempt, async_save_health(health, attempt=None); Store {meta, health, attempt}"
  - "coordinator.py: signal_attempt(entry_id), last_attempt, _Run recorder, _target_kind/_run_trigger, _handle_refresh_interval override"
  - "source.py: Fetched.status, SourceError.status"
  - "sensor.py: LastFetchSensor (sensor.<calendar>_last_fetch, unique ID <subentry_id>_last_fetch)"
  - "diagnostics.py: last_attempt (loaded and not loaded)"
  - "AUT-06 in REQUIREMENTS.md and the ROADMAP Phase 4 requirement list"
affects: [04-06 retention (diagnostics shape), 04-07/04-08 release docs (sensor and attribute list), UAT on ha-dev]

actuals:
  tokens: 18780
  tasks: 3
  commits: 7
plan_head_before: f20d83301b8968e6720cf15ca5595ada578be1b3
plan_head_after: e56c43b716e9cc479ed305291afcbec01513640a

tech-stack:
  added: []
  patterns:
    - "Per-run recorder (_Run) filled by the read paths and finished into a frozen record saved with the health in one Store save"
    - "Run trigger from the kind of the armed target (_target_kind) captured in a _handle_refresh_interval override"
    - "Dispatcher signal after every recorded run, because always_update=False skips listeners on unchanged data"

key-files:
  created:
    - tests/test_last_fetch_sensor.py
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-05-red*.json / *.xml
  modified:
    - custom_components/xmltv_calendar/cache.py
    - custom_components/xmltv_calendar/coordinator.py
    - custom_components/xmltv_calendar/source.py
    - custom_components/xmltv_calendar/sensor.py
    - custom_components/xmltv_calendar/diagnostics.py
    - custom_components/xmltv_calendar/translations/en.json
    - custom_components/xmltv_calendar/translations/de.json
    - tests/test_cache.py
    - tests/test_diagnostics.py
    - tests/test_source.py
    - tests/test_init.py
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "Last-fetch attribute keys and vocabularies fixed: trigger (startup, scheduled, retry, revalidate, manual), outcome (downloaded, not_modified, unchanged, read, cache_start, failed), cache (fresh_hit, stale_hit, written, touched, write_failed, dropped, none); run fields in RefreshAttempt.as_dict order, then last_success, next_refresh, consecutive_failures, matches"
  - "Trigger = startup while coordinator.data is None, else the kind of the target HA's timer serves (set next to every _next_refresh_at assignment), else manual; read before the cancellation fallback marks the target retry"
  - "bytes = body length of a download or identical body, cached payload length for a cache start, file size for file sources; None for a 304 with data; parse_duration is timed inside _async_parse_payload (and around the file executor job), None when nothing was parsed"
  - "A failed run keeps the last good data's programme/channel counts and http_status from SourceError.status (None for network errors and too-large downloads)"
  - "LastFetchSensor is always available and computes value and attributes live on every write (signal_attempt, signal_matches, coordinator updates)"

patterns-established:
  - "New Store fields go through FeedCache._stored, so drop/write/touch keep them; Phase 3 stores without the field load as none"

requirements-completed: [AUT-06, CFG-04]

coverage:
  - id: D1
    description: "Each calendar device has a disabled-by-default diagnostic Last fetch sensor whose state is the last run's start time and whose attributes show trigger, outcome, HTTP status, cache handling, validators sent and counts after a download"
    requirement: AUT-06
    verification:
      - kind: integration
        ref: "tests/test_last_fetch_sensor.py#test_download_shows_last_fetch"
        status: pass
      - kind: integration
        ref: "tests/test_last_fetch_sensor.py#test_last_fetch_is_diagnostic_and_disabled_by_default"
        status: pass
      - kind: integration
        ref: "tests/test_init.py#test_preexisting_subentries_get_one_entity_each"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every run kind and outcome is recorded, also when nothing changed and no coordinator listener runs: 304, identical body, scheduled, failed with retry, cache start with revalidate and fresh hit, file read and unchanged file, same-instant runs"
    requirement: AUT-06
    verification:
      - kind: integration
        ref: "tests/test_last_fetch_sensor.py#test_not_modified_run"
        status: pass
      - kind: integration
        ref: "tests/test_last_fetch_sensor.py#test_identical_body_run"
        status: pass
      - kind: integration
        ref: "tests/test_last_fetch_sensor.py#test_scheduled_run"
        status: pass
      - kind: integration
        ref: "tests/test_last_fetch_sensor.py#test_failed_run_and_retry"
        status: pass
      - kind: integration
        ref: "tests/test_last_fetch_sensor.py#test_cache_start_and_revalidate"
        status: pass
      - kind: integration
        ref: "tests/test_last_fetch_sensor.py#test_file_source_runs"
        status: pass
      - kind: integration
        ref: "tests/test_last_fetch_sensor.py#test_same_instant_runs_keep_the_latest"
        status: pass
      - kind: unit
        ref: "tests/test_source.py#test_http_status_is_reported"
        status: pass
    human_judgment: false
  - id: D3
    description: "The last run is persisted as {meta, health, attempt}, survives a restart, is shown in diagnostics (loaded and not loaded) with the sensor's field order, malformed or Phase 3 stores read as no run, and nothing shows the URL, host or credentials"
    requirement: AUT-06
    verification:
      - kind: integration
        ref: "tests/test_cache.py#test_attempt_is_stored_with_health"
        status: pass
      - kind: integration
        ref: "tests/test_cache.py#test_phase3_store_without_attempt_loads"
        status: pass
      - kind: unit
        ref: "tests/test_cache.py#test_malformed_attempt_reads_as_none"
        status: pass
      - kind: integration
        ref: "tests/test_diagnostics.py#test_diagnostics_end_to_end"
        status: pass
      - kind: integration
        ref: "tests/test_diagnostics.py#test_diagnostics_for_not_loaded_entry"
        status: pass
      - kind: integration
        ref: "tests/test_last_fetch_sensor.py#test_record_survives_restart"
        status: pass
      - kind: integration
        ref: "tests/test_last_fetch_sensor.py#test_no_run_yet_is_unknown"
        status: pass
      - kind: integration
        ref: "tests/test_last_fetch_sensor.py#test_no_secrets_in_last_fetch"
        status: pass
    human_judgment: false
  - id: D4
    description: "Sensor name, attribute names and attribute value states in English and German (CFG-04 part), accepted by hassfest"
    requirement: CFG-04
    verification:
      - kind: integration
        ref: "tests/test_translations.py#test_home_assistant_serves_german_strings"
        status: pass
      - kind: unit
        ref: "tests/test_translations.py#test_de_has_same_keys_as_en"
        status: pass
      - kind: other
        ref: "podman run --rm -v $PWD:/github/workspace:ro,Z ghcr.io/home-assistant/hassfest (Invalid integrations: 0)"
        status: pass
    human_judgment: false
  - id: D5
    description: "On ha-dev the enabled Last fetch entity updates after homeassistant.update_entity (trigger Manual) and reads Letzter Abruf / Auslöser / Ergebnis in German"
    requirement: AUT-06
    verification: []
    human_judgment: true
    rationale: "Task 3 <human-check>: the real frontend rendering of entity names, attribute names and translated attribute states is not covered by the test harness"

duration: 15min
completed: 2026-10-21
status: complete
---

# Phase 4 Plan 05: Last Fetch Diagnostic Sensor Summary

**Each calendar device now has a disabled-by-default "Last fetch" diagnostic sensor. It shows when the source last ran a refresh, what started it (startup, scheduled, retry, revalidate, manual) and how the run ended (outcome, HTTP status, cache handling, validators sent, bytes, programmes, channels, parse time). The record is persisted next to the source health and also appears in diagnostics as `last_attempt`.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-10-21T09:37:21Z
- **Completed:** 2026-10-21T09:52:27Z
- **Tasks:** 3
- **Files modified:** 13 code, test and planning files, plus 10 RED evidence files

## Accomplishments

- `RefreshAttempt` record with fixed vocabularies and a fixed key order. One `as_dict()` feeds the sensor attributes and diagnostics. It is saved in the existing cache Store, so the Store shape is now `{meta, health, attempt}`. A success or a failure saves the run together with its health in one Store save. A start from the cache saves only the run.
- Every run is recorded in the coordinator: download, 304 with or without data, identical body, file read, unchanged file, cache start (fresh or stale), and failure. The trigger comes from the kind of the armed target, read in a `_handle_refresh_interval` override. `signal_attempt` is sent after each recorded run, so the sensor also updates when unchanged data calls no listeners. A cancelled run records nothing.
- `Fetched.status` and `SourceError.status` carry the HTTP status. The error message text is unchanged.
- `LastFetchSensor` details: always available; `device_class` timestamp; diagnostic category; disabled by default. Counters, sizes, durations, cache handling and schedule attributes are left out of history.
- Diagnostics show `last_attempt` after `health`, read from the coordinator or, for an entry that is not loaded, from the Store. The reader for a stored attempt validates every field and returns None for anything malformed.
- AUT-06 is added to REQUIREMENTS.md (requirement, traceability, coverage 46/46) and to the ROADMAP Phase 4 requirement list.

## Task Commits

1. **Task 1 (tracer): the download is shown on the Last fetch sensor.** RED `5db1e68`, GREEN `ff7be2b`
2. **Task 2: every run kind and outcome is recorded.** RED `dc8cd6e`, GREEN `5aee22f`
3. **Task 3: runs are persisted, diagnosable and secret-free; AUT-06 bookkeeping.** RED `8b6d29a`, GREEN `38337d7`, docs `e56c43b`

Tracer feedback gate after Task 1: the run was interactive with `end-of-phase` and an automated-only `<verify>`. The verify command was re-run and passed (64 passed), and Task 2 started after that.

## RED Evidence

Every record classifies as `RED_EVIDENCE_OK (target_test_failed)` and carries a `semanticAssessment`:

- `04-05-red.json`, target `test_download_shows_last_fetch`. `hass.states.get("sensor.test_last_fetch")` returned None after a normal setup. The enabling fixture tolerated the missing class in RED. GREEN replaced it with a direct import.
- `04-05-red-2-304.json`, target `test_not_modified_run`. The run had outcome `failed`, cache `none` and http_status None, which are the recorder defaults; the 304 path filled nothing.
- `04-05-red-2-scheduled.json`, target `test_scheduled_run`. The timer-served run was recorded as `manual`.
- `04-05-red-2-failed.json`, target `test_failed_run_and_retry`. The failed run was not recorded, and the sensor kept the setup time.
- `04-05-red-2-cache.json`, target `test_cache_start_and_revalidate`. The cache start was not recorded, and the sensor showed the persisted pre-restart download.
- `04-05-red-3-tolerant.json`, target `test_malformed_attempt_reads_as_none[unknown_trigger]`. A `RefreshAttempt` with trigger `cron` loaded. The other invalid-value cases failed the same way: unknown outcome, bool status, status 99, negative bytes, bad reason.
- `04-05-red-3-diagnostics.json`, target `test_diagnostics_end_to_end`. `KeyError: 'last_attempt'`; all earlier diagnostics assertions passed.

These tests were already green in RED and act as regression guards:

- `test_http_status_is_reported` (the status plumbing landed with the Task 1 tracer)
- `test_identical_body_run`, `test_file_source_runs` and `test_same_instant_runs_keep_the_latest` failed in RED alongside the targets
- in Task 3, `test_attempt_is_stored_with_health`, `test_phase3_store_without_attempt_loads`, `test_valid_attempt_round_trips`, `test_no_run_yet_is_unknown` and `test_no_secrets_in_last_fetch`, plus the `none`, `int` and `bad_time` malformed cases

## TDD Gate Compliance

Each task has a `test(04-05)` commit before its `feat(04-05)` commit. No REFACTOR commits: the small cleanups (moving the bytes count into `_async_fetch`, removing a `type: ignore`) were made before each GREEN commit.

## Files Created/Modified

- `custom_components/xmltv_calendar/cache.py`: vocabularies, `RefreshAttempt`, attempt persistence, strict field validators
- `custom_components/xmltv_calendar/coordinator.py`: `signal_attempt`, `_Run`, run recording on every path, trigger detection
- `custom_components/xmltv_calendar/source.py`: `Fetched.status`, `SourceError(status=...)`
- `custom_components/xmltv_calendar/sensor.py`: `LastFetchSensor`, added next to `NextMatchSensor`
- `custom_components/xmltv_calendar/diagnostics.py`: `last_attempt`
- `custom_components/xmltv_calendar/translations/{en,de}.json`: `entity.sensor.last_fetch` with name, attribute names and the trigger, outcome and cache states
- `tests/test_last_fetch_sensor.py` (new), and additions to `tests/test_cache.py`, `tests/test_diagnostics.py` and `tests/test_source.py`
- `tests/test_init.py`: the expectation now includes the second sensor per calendar
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`: AUT-06

## Decisions Made

- **Attribute order.** Run fields come in `as_dict` order without `time`, then `last_success`, `next_refresh`, `consecutive_failures`, `matches`. `last_success` and `next_refresh` are local ISO strings.
- **`bytes` and `parse_duration`.** These describe what this run read and parsed:
  - `bytes`: the body for a download or an identical body, the cached payload for a cache start, the file size for a file source.
  - Both are None for a 304 with data in memory.
- **`http_status` on failure.** It comes from `SourceError.status`, so an HTTP error gives its status. A network error or a too-large download gives None. A parse failure after a 200 keeps the 200.
- **Failed runs.** Counts describe the last good data, which stays in effect (SRC-08).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Entity-count expectation in tests/test_init.py**
- **Found during:** Task 1 (full-suite run after GREEN)
- **Issue:** `test_preexisting_subentries_get_one_entity_each` asserted exactly one `_next_match` sensor per calendar. The new last-fetch sensor is a second sensor per calendar device.
- **Fix:** The test now expects both `_next_match` and `_last_fetch` unique IDs, and strips either suffix when checking `config_subentry_id`.
- **Files modified:** tests/test_init.py
- **Verification:** full suite 893 passed
- **Committed in:** ff7be2b (Task 1 GREEN)

**2. [Rule 3 - Blocking] RED fixture tolerant of the missing class**
- **Found during:** Task 1 RED
- **Issue:** A fixture that imports `LastFetchSensor` would have errored at setup before the class existed. The classifier rejects that as INVALID_RED (fixture_or_load_failure).
- **Fix:** In RED, the fixture enabled the class only when it existed, so the target failed on its assertion. GREEN switched it to the planned direct import inside the fixture.
- **Files modified:** tests/test_last_fetch_sensor.py
- **Committed in:** 5db1e68 (RED), ff7be2b (GREEN)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both were needed to keep the suite and the RED evidence valid. There was no scope creep.

## Issues Encountered

None.

## Verification

- `uv run pytest -q -m "not benchmark"`: 916 passed, 1 skipped, 4 deselected
- `uv run pytest -q -m benchmark`: 4 passed, 1 skipped
- `uv run ruff check . && uv run ruff format --check .`: clean
- `podman run --rm -v "$PWD":/github/workspace:ro,Z ghcr.io/home-assistant/hassfest`: Invalid integrations: 0
- Acceptance greps:
  - `"last_fetch"` appears once in both en.json and de.json
  - `class RefreshAttempt`, `EntityCategory.DIAGNOSTIC`, `async def _handle_refresh_interval`, `status=response.status` and `"last_attempt"` are present
  - the AUT-06 requirement, traceability row and ROADMAP line each match once

## User Setup Required

None. The human check runs on ha-dev at end of phase:

1. Enable "Last fetch" on a calendar device.
2. Run `homeassistant.update_entity` and confirm the time, trigger (Manual) and outcome update.
3. With German as the user language, the labels should read "Letzter Abruf", "Auslöser" and "Ergebnis".

## Next Phase Readiness

- 04-06 (retention) extends diagnostics. Its exact-shape tests now include `last_attempt` after `health`.
- Release docs (04-07/04-08) can list the Last fetch sensor and its vocabularies from `ATTEMPT_TRIGGERS`, `ATTEMPT_OUTCOMES` and `ATTEMPT_CACHE`.

---
*Phase: 04-automation-extras-release*
*Completed: 2026-10-21*

## Self-Check: PASSED

- Key files exist on disk (tests/test_last_fetch_sensor.py, cache.py, sensor.py, RED records)
- All 8 plan commits are ancestors of HEAD; `check evaluation-scope --plan 04-05 --commits-only` resolved them on this branch
