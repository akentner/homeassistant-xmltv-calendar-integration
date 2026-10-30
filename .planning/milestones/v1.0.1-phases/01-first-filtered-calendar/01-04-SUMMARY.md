---
phase: 01-first-filtered-calendar
plan: 04
subsystem: calendar
tags: [calendar-entity, bisect, calendar-trigger, executor, tdd]

requires:
  - phase: 01-first-filtered-calendar
    provides: "01-01 walking skeleton: XmltvCalendarEntity with _async_refilter, linear window helpers, render.to_event_fields, setup_xmltv/berlin_tz fixtures"
provides:
  - "window.MatchIndex: bisect-based, end-inclusive overlapping() and current_or_next() with a max-duration lookback"
  - "calendar.py: MAX_EVENTS_PER_QUERY = 5000, EXECUTOR_BUILD_THRESHOLD = 200, module-level build_events() that skips invalid matches"
  - "HA-level tests that drive real calendar triggers (start with -5 min offset, end exactly on a 15-minute window boundary) and live on/off state"
affects: [01-05, 01-06, 01-07, 01-08, 01-09, 01-10, calendar, triggers]

actuals:
  tokens: 16258   # chars/4 over the full realized diff (code + tests: 5299; the rest is the JUnit/JSON RED evidence)
  tasks: 2
  commits: 5
plan_head_before: da0f84e75779e2884345e93e8e86801a16222f4f
plan_head_after: 24268911eb7285d54f053c879f7feb17825d561c

tech-stack:
  added: []
  patterns:
    - "Calendar reads go through a MatchIndex (start-sorted tuple + parallel starts list + max_duration) instead of scanning all matches"
    - "CalendarEvents are built only for the requested slice; above 200 they are built in hass.async_add_executor_job"
    - "Calendar trigger tests step one minute at a time with async_fire_time_changed and turn off all automations at the end"

key-files:
  created:
    - tests/test_calendar.py
    - tests/xmltv/test_window.py
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-04-red.json
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-04-red.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-04-red-2.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-04-red-2-current-or-next.json
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-04-red-2-build-events.json
  modified:
    - custom_components/xmltv_calendar/xmltv/window.py
    - custom_components/xmltv_calendar/calendar.py

key-decisions:
  - "01-04: get_events truncation keeps the earliest-starting 5,000 matches of the range (slice of the start-sorted overlap) and logs at debug level"
  - "01-04: MatchIndex sorts its input itself (stable, near-linear on the start-ordered filter output) instead of trusting caller order"
  - "01-04: the end-trigger test asserts the event end is 11:30 and that it fired by 11:31; under freezer the 11:30 window refresh schedules an already-due alarm that runs on the next tick"

patterns-established:
  - "Read path: _async_refilter -> MatchIndex(result.matches) -> overlapping()/current_or_next() -> build_events()"
  - "Strict-overlap mutation check: changing stop >= start to stop > start makes the boundary end-trigger test fail (0 end calls)"

requirements-completed: [AUT-01, AUT-02]

coverage:
  - id: D1
    description: "get_events on a busy all-channels calendar (6,000 matches/day) returns exactly 5,000 events sorted by start, without raising"
    requirement: AUT-01
    verification:
      - kind: integration
        ref: "tests/test_calendar.py#test_busy_calendar_get_events_is_capped"
        status: pass
    human_judgment: false
  - id: D2
    description: "MatchIndex end-inclusive boundary semantics, long-programme lookback, start ordering, empty index and airing-or-next lookup"
    requirement: AUT-01
    verification:
      - kind: unit
        ref: "tests/xmltv/test_window.py (9 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Calendar state turns on at a matching programme's start and off at its stop without a feed refresh; attributes show message, location, start_time, end_time of the airing or next match"
    requirement: AUT-02
    verification:
      - kind: integration
        ref: "tests/test_calendar.py#test_state_turns_on_and_off_without_refresh"
        status: pass
    human_judgment: false
  - id: D4
    description: "Calendar trigger automations: start with offset -0:05:00 fires at 09:55Z; end fires for a programme ending exactly on a 15-minute trigger-window boundary"
    requirement: AUT-01
    verification:
      - kind: integration
        ref: "tests/test_calendar.py#test_start_offset_and_end_triggers_fire"
        status: pass
    human_judgment: false
  - id: D5
    description: "Calendars with no matches (channel not in feed, feed without programmes) load, return [] from get_events and have state off"
    verification:
      - kind: integration
        ref: "tests/test_calendar.py#test_calendar_with_no_matches"
        status: pass
    human_judgment: false
  - id: D6
    description: "build_events skips a match whose CalendarEvent construction raises HomeAssistantError (debug log) and keeps the rest"
    verification:
      - kind: unit
        ref: "tests/test_calendar.py#test_build_events_skips_invalid"
        status: pass
    human_judgment: false
  - id: D7
    description: "Slices of more than 200 events are built in an executor job, never on the event loop"
    verification: []
    human_judgment: true
    rationale: "No test asserts the executor hop; it is visible only in calendar.py async_get_events (EXECUTOR_BUILD_THRESHOLD branch) and needs code review"

duration: 6min
completed: 2026-10-13
status: complete
---

# Phase 1 Plan 04: Indexed, Bounded, End-Inclusive Calendar Reads Summary

**A bisect-based MatchIndex now serves calendar reads. get_events is capped at 5,000 events, and slices over 200 are built in the executor. Invalid matches are skipped. HA tests drive real calendar triggers (start with -5 min offset, end exactly on a 15-minute window boundary) and live on/off state.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-12T22:53:31Z
- **Completed:** 2026-10-12T22:59:07Z
- **Tasks:** 2
- **Files modified:** 9 (4 code/test, 5 RED-evidence artifacts)

## Accomplishments
- `MatchIndex` (window.py) keeps matches start-sorted with a parallel `starts` list and `max_duration`:
  - `overlapping(start, end)` bisects from `start - max_duration` to `end` and keeps matches with `stop >= start` (end-inclusive).
  - `current_or_next(now)` scans forward from the lookback position to the first match whose stop is after now.
- `async_get_events`:
  - slices the overlap and caps it at `MAX_EVENTS_PER_QUERY = 5000` (debug log when truncated)
  - builds events on the loop up to `EXECUTOR_BUILD_THRESHOLD = 200`, and through `hass.async_add_executor_job` above that
- `build_events` is module-level and skips any match that fails `CalendarEvent` validation (debug log), so one bad match cannot break a read or a trigger poll.
- Automation-level proof of AUT-01 and AUT-02:
  - the start trigger with offset fires at 09:55Z
  - the end trigger fires for a programme ending at 11:30Z, exactly on a window boundary
  - the state goes on at 10:00Z and off at 11:30Z with no extra HTTP request
- Strict-overlap mutation check: with `stop > start`, the boundary end-trigger test fails (0 end calls). This proves the test guards the end-inclusive semantics.

## Task Commits

1. **Task 1: Tracer: capped, executor-built get_events on a busy calendar**
   - `22a96a6` test(01-04): RED, busy-calendar cap tracer plus evidence
   - `070e4f4` feat(01-04): GREEN, MatchIndex.overlapping, cap, build_events, executor threshold
2. **Task 2: Boundary semantics, live state, triggers and error tolerance**
   - `3f95d56` test(01-04): RED, window, build_events, state, trigger and empty-calendar tests plus evidence
   - `9fe3d32` feat(01-04): GREEN, MatchIndex.current_or_next, event property switch, build_events skip
   - `2426891` refactor(01-04): REFACTOR, removed the linear 01-01 helpers and the unused `_matches`

## TDD Gate Compliance

| Cycle | RED | GREEN | REFACTOR |
|-------|-----|-------|----------|
| Task 1 (tracer) | `22a96a6` | `070e4f4` | none needed |
| Task 2 | `3f95d56` | `9fe3d32` | `2426891` |

**RED 1:** `test_busy_calendar_get_events_is_capped`
- Evidence: `tdd-evidence/01-04-red.json`. Classifier: RED_EVIDENCE_OK (target_test_failed).
- Semantic assessment: the test was collected, setup succeeded and the 6,000-programme feed was parsed. It failed on the planned count assertion `6000 == 5000`, because the 01-01 linear `overlapping()` has no cap. There was no import, collection or fixture fault.
- The feed generator was reformatted (line length) after the first run, so the evidence was regenerated from the committed file.

**RED 2:**
- `test_current_or_next_boundaries` (`01-04-red-2-current-or-next.json`). Classifier: RED_EVIDENCE_OK.
  - Semantic: the module imported and 12 other tests in the run passed. The target failed inside its body on the first call of the API under test (`MatchIndex` has no `current_or_next`), so the planned behavior was absent. It did not fail on a value assertion, because the method did not exist yet.
- `test_build_events_skips_invalid` (`01-04-red-2-build-events.json`). Classifier: RED_EVIDENCE_OK.
  - Semantic: `build_events` raised `HomeAssistantError` ("Expected minimum event duration") on the end < start programme. That is exactly the planned failure.
- The run had 4 failures and 12 passes. The other two failures (`test_empty_index` and `test_current_or_next_prefers_earliest_airing_match`) fail for the same missing method.

**GREEN:** all target tests pass. The full suite has 81 passed (not benchmark).

**REFACTOR:** removed `window.overlapping` / `window.current_or_next` (no callers left) and `XmltvCalendarEntity._matches`. All tests still pass.

## Files Created/Modified
- `custom_components/xmltv_calendar/xmltv/window.py`: `MatchIndex` with `__len__`, `overlapping`, `current_or_next`. The linear helpers are removed.
- `custom_components/xmltv_calendar/calendar.py`:
  - constants `MAX_EVENTS_PER_QUERY` and `EXECUTOR_BUILD_THRESHOLD`
  - `_to_event` and `build_events` at module level
  - the entity stores `_index`
  - `event` uses `_index.current_or_next`
  - `async_get_events` caps and offloads
- `tests/test_calendar.py`:
  - busy-feed generator and cap tracer
  - `build_events` skip test
  - live state test
  - start/end trigger test
  - parametrized empty-calendar test
- `tests/xmltv/test_window.py`: 9 `MatchIndex` unit tests (boundaries, lookback, ordering, empty, current_or_next).
- `tdd-evidence/01-04-red*.{xml,json}`: RED reports and classified evidence records.

## Decisions Made
- When a range has more than 5,000 matches, the earliest-starting 5,000 are returned: a slice of the start-sorted overlap.
- `MatchIndex` sorts its input itself rather than relying on the filter's output order. The sort is stable and near-linear on already-sorted input.
- Under freezer, the end trigger at a window boundary fires on the tick after 11:30. The 11:30 refresh registers an alarm for an instant that has already been reached, and it runs on the next `async_fire_time_changed`. The test asserts the event end (11:30Z) and a firing time no later than 11:31Z. In a real loop the due alarm runs immediately.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The plan's expected `message` attribute omitted the channel prefix**
- **Found during:** Task 2 (live state test)
- **Issue:** the behavior block expected message `"Formel 1: Großer Preis von Mexiko"`. EVT-02 rendering (01-01/01-02) produces the summary `"Das Erste: Formel 1: Großer Preis von Mexiko"`, and the plan's own trigger test expects that summary.
- **Fix:** the state test asserts the rendered summary `"Das Erste: Formel 1: Großer Preis von Mexiko"`. After 11:30 it also asserts that the next match (`"Das Erste: Tagesschau"`) is shown.
- **Files modified:** tests/test_calendar.py
- **Committed in:** 3f95d56

**2. [Rule 1 - Bug] The end-trigger timing assertion was relaxed to one tick**
- **Found during:** Task 2 (trigger test, first RED run)
- **Issue:** the end call arrived at 11:31Z, not 11:30Z. This is a test-harness artifact: the boundary refresh at 11:30 schedules an alarm that is already due, and it fires on the next time-changed tick.
- **Fix:** the test asserts exactly one end call with location "Das Erste", the event end at 11:30Z, and a firing time in [11:30Z, 11:31Z]. Verified by mutation: strict overlap gives 0 end calls.
- **Files modified:** tests/test_calendar.py
- **Committed in:** 3f95d56

**3. [Plan inconsistency] `test_overlapping_long_programme_lookback` was not RED**
- **Found during:** Task 2 RED
- **Issue:** the plan names it as a RED target, but Task 1 GREEN already implemented the max-duration lookback, as Task 1 instructs.
- **Fix:** it is kept as a characterization test. RED evidence for Task 2 rests on `test_current_or_next_boundaries` and `test_build_events_skips_invalid`.
- **Committed in:** 3f95d56

**4. [Rule 3 - Blocking] Lint fixes**
- **Issue:** D213 multi-line docstrings, E501 in the feed generator, and F401 on the `window` module import once the entity stopped using it.
- **Fix:** single-line docstrings with comments, wrapped lines, and the import removed.
- **Committed in:** 070e4f4, 9fe3d32

**Also note:** between `070e4f4` and `9fe3d32`, `build_events` had no try/except, because the plan sequences the skip behavior as the Task 2 RED target. Pitfall 6 tolerance was missing for those two commits only.

---

**Total deviations:** 4 (2 test-expectation corrections, 1 plan inconsistency, 1 lint)
**Impact on plan:** none on scope. All must-have truths hold except the executor-hop truth, which is implemented but covered only by code review (coverage D7).

## Issues Encountered
None.

## User Setup Required
None. No external service configuration is required.

## Next Phase Readiness
- Calendar reads are O(log n) plus the slice size, capped, and never raise. Later plans (refresh/listener, diagnostics, subentry reconfigure) can rely on `_index` being swapped atomically in `_async_refilter`.
- AUT-01 and AUT-02 are covered by automation-level tests.

---
*Phase: 01-first-filtered-calendar*
*Completed: 2026-10-13*

## Self-Check: PASSED
