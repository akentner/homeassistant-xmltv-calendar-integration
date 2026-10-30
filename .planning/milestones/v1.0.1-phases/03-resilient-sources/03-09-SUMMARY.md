---
phase: 03-resilient-sources
plan: 09
subsystem: coordinator
tags: [home-assistant, data-update-coordinator, scheduling, backoff, repairs, tdd, gap-closure]

requires:
  - phase: 03-resilient-sources
    provides: "03-01 schedule maths (next_regular, backoff_delay, MIN_DELAY) and _schedule_refresh wall-clock target; 03-04 source health, failure recording and the 24 h Repairs issue"
provides:
  - "xmltv/schedule.py: EARLY_FIRE_TOLERANCE (2 s) and pure refresh_base(now, target)"
  - "XmltvCoordinator._set_regular_target and the failure backoff cap derived from refresh_base (CR-01)"
  - "XmltvCoordinator._async_read_source and _async_handle_failure; _async_update_data handles UpdateFailed and every other Exception, the latter re-raised as UpdateFailed(unable_to_fetch) (CR-02)"
  - "Regression tests for CR-01 (early-fired slot, fast failure, manual-refresh guards) and CR-02 (scheduled unexpected exception, cancellation guard, 24 h issue, cache-parse failure at setup)"
affects: [03-10, phase-03-verification, phase-03-uat]

actuals:
  tokens: 5683
  tasks: 3
  commits: 6
plan_head_before: 9bcdf970979140eaf8f6d45f9c014c47157e52e1
plan_head_after: 4271ad626be0f2d65b087bb59694f944da9f92fe

tech-stack:
  added: []
  patterns:
    - "Served-target base: the next target is computed from refresh_base(now, current target), so only a refresh at most 2 s before its target consumes it"
    - "Single failure handler: UpdateFailed and any other Exception both record the failure and set the backoff; unexpected ones are re-raised as UpdateFailed so HA never re-arms a past target"

key-files:
  created:
    - .planning/phases/03-resilient-sources/tdd-evidence/03-09-red.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-09-red.xml
    - .planning/phases/03-resilient-sources/tdd-evidence/03-09-red-2.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-09-red-2.xml
    - .planning/phases/03-resilient-sources/tdd-evidence/03-09-red-3.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-09-red-3-issue.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-09-red-3-cache.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-09-red-3.xml
  modified:
    - custom_components/xmltv_calendar/xmltv/schedule.py
    - custom_components/xmltv_calendar/coordinator.py
    - tests/xmltv/test_schedule.py
    - tests/test_schedule_refresh.py
    - tests/test_repairs.py

key-decisions:
  - "refresh_base(now, target) returns target only when now < target <= now + 2 s; a plain max(now, target) was rejected because a manual update_entity hours before a daily slot would consume the slot and an interval refresh would be pushed out (D-12)"
  - "Unexpected exceptions while reading the cache, downloading or parsing are recorded as unable_to_fetch, back off like UpdateFailed and reach HA as UpdateFailed(unable_to_fetch); asyncio.CancelledError is not caught and passes through unrecorded"
  - "An unexpected exception logs one WARNING per failed attempt with only the source title and exception class; the traceback is DEBUG only (T-03-28)"

patterns-established:
  - "Early-fire tests: call coordinator.async_refresh() 0.6 s before the target instead of relying on HA's random _microsecond"
  - "Unexpected-exception tests: monkeypatch coordinator_module.parse to raise RuntimeError and serve a changed body (FEED + b'\\n') so the refresh parses"

requirements-completed: [SRC-05, SRC-08, SRC-11]

coverage:
  - id: D1
    description: "A daily source whose refresh runs 0.6 s before the 18:15 slot serves that slot: next target is tomorrow's slot, no second request one second later"
    requirement: SRC-05
    verification:
      - kind: integration
        ref: "tests/test_schedule_refresh.py#test_daily_slot_served_once_when_timer_fires_early"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_schedule.py#test_refresh_base"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_schedule.py#test_early_fire_tolerance"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_schedule.py#test_early_fire_serves_daily_slot"
        status: pass
    human_judgment: false
  - id: D2
    description: "A refresh failing 0.6 s before its slot backs off 5 min, then 15 min; consecutive_failures grows by one per attempt"
    requirement: SRC-05
    verification:
      - kind: integration
        ref: "tests/test_schedule_refresh.py#test_daily_fast_failure_before_slot_backs_off_five_minutes"
        status: pass
    human_judgment: false
  - id: D3
    description: "Manual refreshes keep their semantics: before a daily slot the slot stays, in interval mode the interval restarts from now"
    requirement: SRC-05
    verification:
      - kind: integration
        ref: "tests/test_schedule_refresh.py#test_manual_refresh_before_slot_keeps_the_slot"
        status: pass
      - kind: integration
        ref: "tests/test_schedule_refresh.py#test_manual_refresh_restarts_the_interval"
        status: pass
    human_judgment: false
  - id: D4
    description: "An unexpected exception during a scheduled refresh is recorded as unable_to_fetch, backs off 5 min then 15 min, reaches HA as UpdateFailed, keeps the last good data and calendars available, and logs one content-free WARNING"
    requirement: SRC-08
    verification:
      - kind: integration
        ref: "tests/test_schedule_refresh.py#test_unexpected_exception_backs_off_and_is_recorded"
        status: pass
    human_judgment: false
  - id: D5
    description: "A cancelled refresh records no failure and keeps its target"
    requirement: SRC-08
    verification:
      - kind: integration
        ref: "tests/test_schedule_refresh.py#test_cancelled_refresh_records_no_failure"
        status: pass
    human_judgment: false
  - id: D6
    description: "Unexpected exceptions for more than 24 h raise source_failing_unable_to_fetch, and the next success clears it; a cache-parse failure at setup is recorded without a download (SETUP_RETRY, unable_to_fetch)"
    requirement: SRC-11
    verification:
      - kind: integration
        ref: "tests/test_repairs.py#test_unexpected_exception_raises_issue_after_24h"
        status: pass
      - kind: integration
        ref: "tests/test_repairs.py#test_unexpected_cache_parse_failure_is_recorded"
        status: pass
    human_judgment: false
  - id: D7
    description: "A manual update_entity during a scheduled refresh is serialized by HA's debouncer lock (backstop truth, no test planned)"
    requirement: SRC-08
    verification: []
    human_judgment: true
    rationale: "Relies on Home Assistant's _debounced_refresh.async_lock(); stays the human UAT item from 03-VERIFICATION.md as directed by the plan"

duration: 7min
completed: 2026-10-16
status: complete
---

# Phase 03 Plan 09: One Request Per Refresh Target, Every Failure Backed Off Summary

**`refresh_base` (2 s early-fire tolerance) keeps an early-firing HA timer from requesting a daily slot twice or retrying after 1 s. A single failure handler records every non-cancellation exception as `unable_to_fetch`, backs it off and re-raises it as `UpdateFailed`. That ends the once-per-second download loop (CR-01, CR-02).**

## Performance

- **Duration:** 7 min
- **Started:** 2026-10-16T13:24:44Z
- **Completed:** 2026-10-16T13:31:00Z
- **Tasks:** 3 (1 tracer + 2 TDD)
- **Files modified:** 5 source/test files, plus 8 RED evidence files

## Accomplishments

- CR-01, success path: `_set_regular_target` computes the next target from `refresh_base(now, self._next_refresh_at)`. A refresh that runs up to 2 s before its target serves that target, so the daily slot is requested once.
- CR-01, failure path: the backoff cap is the next regular refresh after the served target. A fast failure just before the slot now waits 5 min, then 15 min, instead of `MIN_DELAY`.
- CR-02: `_async_update_data` has one guarded read (`_async_read_source`: cache start, download or file, plus the parse) and one failure handler (`_async_handle_failure`) shared by `UpdateFailed` and `Exception`. Unexpected exceptions are recorded, backed off, eligible for the 24 h Repairs issue, and reach HA as `UpdateFailed(unable_to_fetch)`.
- Manual-refresh semantics (D-12) are unchanged. Two regression guards pin them.

## Task Commits

1. **Task 1 (tracer): early-fired daily slot served once**
   - RED `6f5a1b3` (test), GREEN `af12ce8` (feat)
2. **Task 2: fast failure before the slot backs off 5 min**
   - RED `118f1eb` (test), GREEN `8283e60` (feat)
3. **Task 3: unexpected exceptions recorded and backed off**
   - RED `d98571d` (test), GREEN `4271ad6` (feat)

There was no REFACTOR commit because none was needed.

## TDD Gate Compliance

Every GREEN commit has a RED `test(03-09)` commit before it. Every RED record was classified `RED_EVIDENCE_OK` by `gsd-tools check tdd-red-evidence`, and every JUnit report had zero `<error>` elements, so no TAP rerun was needed.

| Record | Target | Planned assertion that failed | Semantic assessment |
|--------|--------|-------------------------------|---------------------|
| 03-09-red.json | test_daily_slot_served_once_when_timer_fires_early | `next_refresh_at == 2026-10-14T16:15Z`; actual 2026-10-13T16:15Z (the slot just served) | Target ran, and the early refresh succeeded. It failed because `next_slot` of the early `now` is the slot 0.6 s ahead. The other failures in the run were the planned pure rows (`S.refresh_base` missing). |
| 03-09-red-2.json | test_daily_fast_failure_before_slot_backs_off_five_minutes | `next_refresh_at == failed_at + 5 min`; actual failed_at + 1 s | Failure 1 was recorded. The cap `next_regular(now)` was 0.6 s ahead and got floored to `MIN_DELAY`. The guards passed. |
| 03-09-red-3.json | test_unexpected_exception_backs_off_and_is_recorded | `consecutive_failures == 1`; actual 0 | One request was made. The RuntimeError reached HA's generic handler and nothing was recorded. |
| 03-09-red-3-issue.json | test_unexpected_exception_raises_issue_after_24h | `consecutive_failures == 1`; actual 0 | Same root cause, so the 24 h issue was unreachable. |
| 03-09-red-3-cache.json | test_unexpected_cache_parse_failure_is_recorded | `error_reason_translation_key == "unable_to_fetch"`; actual None | The RuntimeError escaped the cache start and became a plain ConfigEntryNotReady. |

Regression guards that pass before and after: `test_manual_refresh_before_slot_keeps_the_slot`, `test_manual_refresh_restarts_the_interval`, `test_cancelled_refresh_records_no_failure`.

## Files Created/Modified

- `custom_components/xmltv_calendar/xmltv/schedule.py`: `EARLY_FIRE_TOLERANCE` and `refresh_base` (pure stdlib; the purity guard passes).
- `custom_components/xmltv_calendar/coordinator.py`: `_set_regular_target` now uses `refresh_base`. Also adds `_async_read_source`, `_async_handle_failure`, the restructured `_async_update_data` with `UpdateFailed` and `Exception` clauses, and WARNING/DEBUG logging for unexpected exceptions.
- `tests/xmltv/test_schedule.py`: `test_refresh_base` (6 rows), `test_early_fire_tolerance`, `test_early_fire_serves_daily_slot`.
- `tests/test_schedule_refresh.py`: six new end-to-end tests (CR-01 and CR-02).
- `tests/test_repairs.py`: `test_unexpected_exception_raises_issue_after_24h`, `test_unexpected_cache_parse_failure_is_recorded`.

## Decisions Made

- Served-target base instead of `max(now, target)`, with a 2 s tolerance. This follows the plan's planner decisions.
- The cache start sits inside the guarded region. A `MemoryError` while parsing the cache at setup is recorded and counts toward the 24 h issue.

## Deviations from Plan

**1. [Process] No `# noqa: BLE001` on the `Exception` clause**
- **Found during:** Task 3 GREEN
- **Issue:** Ruff does not report BLE001 when the clause re-raises. The plan's conditional `noqa` would have triggered RUF100 (unused noqa).
- **Fix:** I left out the `noqa`, as the plan's "only if Ruff reports BLE001" condition requires. The rationale ("every failure must back off and be recorded, D-10, CR-02; CancelledError passes") is a plain comment above the clause.
- **Commit:** `4271ad6`

**2. [Process] `caplog.clear()` before the failing step**
- **Found during:** Task 3 RED
- **Issue:** The "exactly one WARNING" assertion should count only the failed attempt, not records from setup.
- **Fix:** The test clears caplog right before the scheduled failure. No assertion was weakened.
- **Commit:** `d98571d`

**Total deviations:** 2 minor process adjustments, with no behaviour change against the plan.

## Issues Encountered

- The executor's protected-branch guard reports `main` as protected. Every earlier plan in this project committed directly on `main` (`git.branching_strategy: none`), and the orchestrator dispatched this plan as a sequential executor on the main working tree. So the commits are on `main` as before, and no config was changed.

## Notes

- `actuals.tokens` counts chars/4 over the source and test diff (22,732 chars), the same scale 03-08 used. The JUnit/JSON RED evidence (about 103k chars) is excluded.
- Not covered here: WR-01 stays open per 03-REVIEW-DISPOSITION.md. The parallel-refresh and options-save-during-parse items stay human UAT.

## User Setup Required

None.

## Next Phase Readiness

Ready for 03-10 (WR-02/WR-03: config_flow.py, tests/test_config_flow.py, tests/test_identity.py). This plan did not touch those files, and the FeedCache/SourceHealth APIs are unchanged.

## Verification

- `uv run pytest -q -m "not benchmark"`: 810 passed, 1 skipped, no "Lingering"
- `uv run pytest tests/xmltv/test_purity.py -q`: 2 passed
- `uv run ruff check . && uv run ruff format --check .`: clean
- Every task's acceptance-criteria grep and count check passes: `refresh_base(now, self._next_refresh_at)` appears 2 times, `next_regular(now, self._schedule())` 1 time, `except Exception as err:` 1 time, no `except BaseException`/`CancelledError` clause, and `translation_key=_DEFAULT_REASON) from err` 1 time.

## Self-Check: PASSED

- All 5 modified source/test files and all 8 RED evidence files exist.
- All 6 commits (`6f5a1b3`, `af12ce8`, `118f1eb`, `8283e60`, `d98571d`, `4271ad6`) are ancestors of HEAD. `check evaluation-scope --plan 03-09 --commits-only` resolves them.

---
*Phase: 03-resilient-sources*
*Completed: 2026-10-16*
