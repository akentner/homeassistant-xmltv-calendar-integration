---
phase: 03-resilient-sources
plan: 01
subsystem: scheduling
tags: [datetime, zoneinfo, dst, data-update-coordinator, freezegun, tdd]

requires:
  - phase: 01-ingestion-tracer
    provides: XmltvCoordinator (one per source), refresh_hours option, tests/conftest.py setup_xmltv
  - phase: 02-precise-filters-preview
    provides: xmltv/settings.py normalize_time, tolerant-reader style of stored contracts
provides:
  - Pure schedule module xmltv/schedule.py (Schedule, SourceOptions, last_slot, next_slot, next_regular, is_fresh, fresh_until, backoff_delay, is_persistently_failing)
  - Stored source-options contract (refresh_mode, refresh_hours, refresh_time, naive_timezone, offset_minutes) with CONF_* aliases in const.py
  - Coordinator wall-clock refresh target (_next_refresh_at) converted to update_interval in a _schedule_refresh override
  - Daily-at refresh in the HA time zone (SRC-05)
  - Clock-independent test modules (freeze_time markers) and a per-test temporary HA config dir
affects: [03-02 cache, 03-03 manual refresh, 03-04 backoff and empty-feed failure, 03-05 timezone, 03-06 options flow, 03-07 diagnostics]

actuals:
  tokens: 9825       # chars/4 over the realized code + test diff; the committed RED evidence (JUnit XML/JSON) adds ~97.8k more (107588 incl. evidence)
  tasks: 3
  commits: 5
plan_head_before: bfcd455111b2ae31839e209607ea37fed0363945
plan_head_after: 08b1b430beae8b9becd43dfffd2c4cf3369e0cbd

tech-stack:
  added: []
  patterns:
    - "Pure time maths on aware UTC datetimes; a wall-clock time becomes an instant only via datetime.combine(day, t, tzinfo=tz).astimezone(UTC)"
    - "Coordinator keeps an absolute target (_next_refresh_at) and converts it to update_interval at arm time, clamped to MIN_DELAY = 1 s"
    - "Tests stepping scheduled coordinator refreshes wait with async_block_till_done(wait_background_tasks=True)"

key-files:
  created:
    - custom_components/xmltv_calendar/xmltv/schedule.py
    - tests/xmltv/test_schedule.py
    - tests/test_schedule_refresh.py
  modified:
    - custom_components/xmltv_calendar/coordinator.py
    - custom_components/xmltv_calendar/const.py
    - tests/conftest.py
    - tests/test_init.py
    - tests/test_config_flow.py
    - tests/test_reconfigure.py
    - tests/test_source.py
    - tests/test_subentry_flow.py

key-decisions:
  - "Stored source-option names fixed (D-06, costly): refresh_mode (interval|daily), refresh_hours, refresh_time (HH:MM), naive_timezone (utc|local), offset_minutes (-720..720)"
  - "_next_refresh_at is recomputed with next_regular after every refresh, success or failure (try/finally); 03-04 replaces the failure branch with backoff_delay"
  - "Backoff 5 min / 15 min / 1 h / 3 h / 6 h, then 6 h, capped at the next regular refresh, floor 1 s; persistent failure = failing_since more than 24 h before now"
  - "Daily slot in a DST gap fires at the shifted instant (02:30 -> 01:30 UTC), in a fold at its first occurrence (00:30 UTC); pinned by tests"

patterns-established:
  - "SourceOptions.from_mapping is a never-raising tolerant reader; as_options() is its exact inverse"
  - "Fixture-dated test modules carry pytestmark = pytest.mark.freeze_time(NOW)"

requirements-completed: [SRC-05]

coverage:
  - id: D1
    description: "A source stored as daily 18:15 refreshes at 18:15 Europe/Berlin (16:15 UTC), again the next day, and not before"
    requirement: SRC-05
    verification:
      - kind: integration
        ref: "tests/test_schedule_refresh.py#test_daily_slot_refreshes_at_local_time"
        status: pass
    human_judgment: false
  - id: D2
    description: "Interval sources keep refreshing every refresh_hours; a Phase 1 entry ({refresh_hours: N}) behaves as before"
    requirement: SRC-05
    verification:
      - kind: integration
        ref: "tests/test_schedule_refresh.py#test_interval_source_refreshes_every_interval"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_schedule.py#test_phase1_entry"
        status: pass
      - kind: integration
        ref: "tests/test_init.py#test_options_change_reloads_once"
        status: pass
    human_judgment: false
  - id: D3
    description: "Removing the only calendar and adding a new one re-arms the timer at the wall-clock slot"
    requirement: SRC-05
    verification:
      - kind: integration
        ref: "tests/test_schedule_refresh.py#test_rearm_after_calendar_readded"
        status: pass
    human_judgment: false
  - id: D4
    description: "Slot maths across DST end, DST start, gap and fold in Europe/Berlin; every result aware UTC"
    requirement: SRC-05
    verification:
      - kind: unit
        ref: "tests/xmltv/test_schedule.py#test_next_slot"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_schedule.py#test_last_slot"
        status: pass
    human_judgment: false
  - id: D5
    description: "is_fresh / fresh_until / next_regular, backoff_delay table, is_persistently_failing (24 h from failing_since)"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_schedule.py#test_is_fresh"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_schedule.py#test_backoff_delay"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_schedule.py#test_is_persistently_failing"
        status: pass
    human_judgment: false
  - id: D6
    description: "Stored source-options contract: tolerant reader, clamping, round trip, never raises; CONF_* aliases in const.py"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_schedule.py#test_options_round_trip"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_schedule.py#test_from_mapping_never_raises"
        status: pass
    human_judgment: false
  - id: D7
    description: "Fixture-dated test modules run frozen at 2026-10-13T06:00Z; every test gets a temporary HA config dir"
    verification:
      - kind: other
        ref: "uv run pytest -q -m 'not benchmark' (643 passed, 1 skipped)"
        status: pass
    human_judgment: false

duration: 13min
completed: 2026-10-16
status: complete
---

# Phase 3 Plan 01: Refresh Schedule Engine Summary

**A source now refreshes either every N hours or once a day at a fixed time in the HA time zone. The time maths (DST slots, freshness, capped backoff, the 24 h failure test) lives in the pure, table-tested `xmltv/schedule.py`. The coordinator keeps an absolute target and converts it into `update_interval` each time HA arms its timer.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-10-16T09:59:18Z
- **Completed:** 2026-10-16T10:12:24Z
- **Tasks:** 3 (1 tracer, 1 TDD, 1 auto)
- **Files modified:** 11 source/test files, plus 6 RED evidence files

## Accomplishments

- **Daily refresh in the HA time zone (SRC-05, D-02):**
  - `{"refresh_mode": "daily", "refresh_time": "18:15"}` refreshes at 16:15 UTC in October Berlin, then again the next day.
  - Interval sources and Phase 1 entries behave as before.
- **Wall-clock target in the coordinator:**
  - `_next_refresh_at` is set after every refresh.
  - The `_schedule_refresh` override arms `max(target - utcnow, 1 s)`.
  - So a calendar added after all others were removed still fires at the slot.
- **Pure schedule module, all exact at their boundaries:**
  - `last_slot` and `next_slot`: across DST end, DST start, the 02:30 gap and the fold.
  - `is_fresh` and `fresh_until`: missed daily slot is stale, a future fetch is never fresh.
  - `backoff_delay`: 5m / 15m / 1h / 3h / 6h, capped, floor 1 s.
  - `is_persistently_failing`: true only when `failing_since` is more than 24 h before now.
- **Stored source-options contract fixed (D-06):**
  - `SourceOptions.from_mapping` never raises and clamps values; `as_options` round-trips.
  - `const.py` aliases the keys as `CONF_*` and holds the only definition of the refresh-hours constants.
- **Clock-independent suite (Wave 0 for 03-02..03-04):**
  - Five fixture-dated modules run frozen at 2026-10-13T06:00Z.
  - Every test gets its own temporary HA config dir.

## Task Commits

1. **Task 1: Tracer, daily at 18:15 end to end**
   - RED `ddb0742` (test)
   - GREEN `69230b6` (feat)
2. **Task 2: Pure schedule tables and stored options contract**
   - RED `5962504` (test)
   - GREEN `5e072e7` (feat)
3. **Task 3: Pin the clock of fixture-dated test modules** - `08b1b43` (test)

No REFACTOR commits; no cleanup was needed.

## TDD Gate Compliance

| Gate | Task 1 | Task 2 |
|------|--------|--------|
| RED commit before GREEN | `ddb0742` before `69230b6` | `5962504` before `5e072e7` |
| RED classifier | `03-01-red.json`: RED_EVIDENCE_OK (target_test_failed) | `03-01-red-2-slots.json`, `-backoff.json`, `-options.json`: all RED_EVIDENCE_OK (target_test_failed) |
| GREEN | 3/3 tracer tests pass | 84/84 table rows pass |

**RED semantic assessments:**
- **Task 1:** `test_daily_slot_refreshes_at_local_time` ran normally. Setup passed and the 16:14:59 step kept the count at 1. It then failed on the planned assertion at the 16:15:01 step (`assert 1 == 2`), because the coordinator still used a fixed 24 h interval.
  - JUnit shows errors=0, so there was no teardown or fixture fault.
  - The interval test passed by design: it is a regression guard.
- **Task 2:** each target failed inside its test body with `AttributeError`, because the function or key does not exist yet. The targets were `last_slot`, `backoff_delay` and `KEY_OFFSET_MINUTES`.
  - The module was imported as `schedule` and looked up per test, so collection succeeded (84 tests, errors=0).

## Files Created/Modified

- `custom_components/xmltv_calendar/xmltv/schedule.py`: schedule maths and the stored source-options contract (stdlib only).
- `custom_components/xmltv_calendar/coordinator.py`: the scheduling changes:
  - `_options` and `_next_refresh_at`, plus `_schedule()`.
  - The `source_options` and `next_refresh_at` properties.
  - The `_schedule_refresh` override, and a `try/finally` target update in `_async_update_data`.
- `custom_components/xmltv_calendar/const.py`: `CONF_REFRESH_MODE/TIME`, `CONF_NAIVE_TIMEZONE`, `CONF_OFFSET_MINUTES` and the value constants, re-exported from `schedule.py`.
- `tests/conftest.py`: autouse `hass_config_dir` → `hass_tmp_config_dir`, plus `setup_xmltv(..., options=, headers=)`.
- `tests/test_schedule_refresh.py`: tests for the daily slot, the interval and the re-arm through HA.
- `tests/xmltv/test_schedule.py`: pure tables (84 cases).
- `tests/test_init.py`, `test_config_flow.py`, `test_reconfigure.py`, `test_source.py`, `test_subentry_flow.py`: each now has `pytestmark = pytest.mark.freeze_time(NOW)`.
  - `test_init` asserts `next_refresh_at` instead of `update_interval`.
  - `test_edit_on_unloaded_source_aborts` unloads the entry before faking SETUP_RETRY.
- `.planning/phases/03-resilient-sources/tdd-evidence/03-01-red{,-2}.xml` and the 4 RED records.

## Decisions Made

- **Option key names:** fixed exactly as RESEARCH A2 proposed. This choice is costly to change: renaming later needs `async_migrate_entry` plus a VERSION bump.
- **Mode and time stored together:** `from_mapping` stores `refresh_time` only when the mode is daily. A daily mode without a valid time reads as interval with no time, so `as_options()` round-trips exactly.
- **Failed refreshes:** a failure also moves the target to the next regular slot or interval. This is a placeholder until 03-04 replaces that branch with `backoff_delay`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrong DST-start expectation in the plan's behaviour block**
- **Found during:** Task 2 RED.
- **Issue:** the plan expected `next_slot(2026-03-28T17:00Z) == 2026-03-29T16:15Z`.
  - 2026-03-28 is still CET, so 17:00Z is 18:00 local. That day's 18:15 slot (17:15Z) has not passed yet.
  - The correct result is therefore `2026-03-28T17:15Z`.
- **Fix:** the `dst-start-2026-03-29` row now probes `now = 2026-03-28T18:00Z` (19:00 CET), which gives the CEST slot `2026-03-29T16:15Z`. A new row, `eve-of-dst-start-cet`, pins the same-day CET case.
- **Files modified:** `tests/xmltv/test_schedule.py`
- **Committed in:** `5962504`

**2. [Rule 1 - Bug] Flaky tracer assertion on `next_refresh_at`**
- **Found during:** Task 1 GREEN. It failed 1 run in about 30.
- **Issue:** HA runs scheduled coordinator refreshes as background tasks: a download, then a parse in the executor. `async_block_till_done()` does not wait for those. The assertion could therefore see the request count but not the `finally` that sets `_next_refresh_at`.
- **Fix:** `_step_to` in `tests/test_schedule_refresh.py` awaits `async_block_till_done(wait_background_tasks=True)`. After the fix, 20+ repeated runs were green.
- **Files modified:** `tests/test_schedule_refresh.py`
- **Committed in:** `69230b6`

**3. [Deviation - RED target choice] Slot RED target is a `last_slot` DST row, not a `next_slot` DST row**
- **Found during:** Task 2 RED.
- **Issue:** Task 1 already implemented `next_slot` per RESEARCH Pattern 1, so its DST rows were green. Using one as the target would have been an unexpected GREEN.
- **Fix:** `03-01-red-2-slots.json` targets `test_last_slot[dst-end-2026-10-25]` instead. `last_slot` did not exist yet.
- **Committed in:** `5962504`

---

**Total deviations:** 3: two auto-fixed bugs in test data and timing, and one change of RED target.
**Impact on plan:** no scope change. All three keep the tests honest.

## Issues Encountered

- **Protected branch:** `gsd-tools query git.base-branch --is-protected main` returns `true`. The project runs with `git.branching_strategy: none` and the orchestrator dispatched this plan on `main`. The execute-phase `"none"` arm (protected-branch.md, #3552) warns and continues on the current branch, so commits went to `main` as in Phases 1 and 2.
- **Wave 0 probe (temporary, reverted, not committed):** I made the coordinator fail on a 0-programme parse and ran the full suite. Only two tests failed, and neither is a clock problem:
  - `tests/test_calendar.py::test_calendar_with_no_matches[feed-without-programmes]`: already planned for removal in 03-04 (RESEARCH Pitfall 2).
  - `tests/test_subentry_flow.py::test_channel_picker_lists_sorted_ids`: its feed has channels and no programmes by construction. 03-04 (D-20) must give it a programme, or set it up another way.
  - No other module needed the freeze marker.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- 03-02 (cache) can use `is_fresh`, `fresh_until` and `next_refresh_at`. The temporary config dir keeps cache files out of phcc's shared testing_config.
- 03-04 (backoff, Repairs) can use `backoff_delay`, `is_persistently_failing` and the `try/finally` target branch in `_async_update_data`. It must also handle the channels-only feed in `test_channel_picker_lists_sorted_ids`.
- 03-05 and 03-06 can read `SourceOptions.naive_timezone` and `offset_minutes`, and the `CONF_*` keys are ready for the options flow.

## Self-Check: PASSED

- FOUND: `custom_components/xmltv_calendar/xmltv/schedule.py`, `tests/xmltv/test_schedule.py`, `tests/test_schedule_refresh.py`, 4 RED records
- FOUND commits: `ddb0742`, `69230b6`, `5962504`, `5e072e7`, `08b1b43`, each an ancestor of HEAD
- Plan verification: `pytest -m "not benchmark"` gave 643 passed, 1 skipped. `pytest -m benchmark` gave 4 passed, 1 skipped. `ruff check` and `ruff format --check` are clean.

---
*Phase: 03-resilient-sources*
*Completed: 2026-10-16*
