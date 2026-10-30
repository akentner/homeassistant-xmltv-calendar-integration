---
phase: 02-precise-filters-preview
plan: 04
subsystem: filtering
tags: [filter, time-window, weekdays, duration, dst, redos, tdd]
status: complete

requires:
  - phase: 02-precise-filters-preview
    provides: "02-02 settings.py KEY_TIME_FROM/KEY_TIME_TO/KEY_WEEKDAYS/KEY_MIN_DURATION/KEY_MAX_DURATION, WEEKDAYS, with_defaults"
  - phase: 02-precise-filters-preview
    provides: "02-03 preview.build_preview(data, epg, now, tz, language)"
  - phase: 02-precise-filters-preview
    provides: "02-01 XmltvCalendarEntity._async_refilter in the executor"
provides:
  - "xmltv/filter.py: TimeWindow(start, end) with anchor_date(local) and from_times(time_from, time_to)"
  - "FilterSpec.min_duration, max_duration (timedelta | None), window (TimeWindow | None), weekdays (frozenset[int])"
  - "FilterSpec.apply(epg, *, tz=UTC): channel, duration, window/weekday, include, exclude"
  - "has_nested_repeat(pattern) and first_invalid_pattern message 'nested repetition can be very slow' (NESTED_REPETITION_MESSAGE)"
  - "calendar.py refilters with partial(spec.apply, epg, tz=dt_util.get_default_time_zone())"
  - "preview.build_preview filters with apply(epg, tz=tz)"
affects: [02-05, 02-06, 02-07, 02-08, advanced step, reconfigure flow]

actuals:
  tokens: 7900
  tasks: 3
  commits: 6
plan_head_before: 2a903f0227e8ec0f816e1e60e0e98e83de6d619b
plan_head_after: 667766b4c76d4100776bb68c794162a37f16dbda

tech-stack:
  added: []
  patterns:
    - "Executor calls with kwargs go through functools.partial (async_add_executor_job takes no kwargs)"
    - "Local-time checks convert with astimezone(tz) only when a window or weekdays are set; durations always use the parser's fixed-offset datetimes"
    - "Private stdlib modules are imported in try/except ImportError, read at call time, and every walk is fail-open"

key-files:
  created:
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-04-red.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-04-red.xml
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-04-red-2.xml
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-04-red-2-duration.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-04-red-2-wr07.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-04-red-3.xml
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-04-red-3.json
  modified:
    - custom_components/xmltv_calendar/xmltv/filter.py
    - custom_components/xmltv_calendar/calendar.py
    - custom_components/xmltv_calendar/xmltv/preview.py
    - tests/test_filtering.py
    - tests/xmltv/test_filter.py
    - tests/xmltv/test_preview.py

key-decisions:
  - "02-04: stored durations above timedelta.max in minutes are clamped to timedelta.max // 1 min (a huge min hides everything, a huge max is effectively unbounded); from_mapping never raises OverflowError"
  - "02-04: a repeat counts as unbounded for the nested-repetition check when its max > 1 (RESEARCH Pattern 9), so (a{2,3})* is rejected too; GROUPREF_EXISTS branches are walked in addition to SUBPATTERN, BRANCH, ASSERT and ASSERT_NOT"
  - "02-04: weekdays without a window use the local start date; with a window the weekday is that of the day the window opened (D-11)"

patterns-established:
  - "Pure filter tests use fixed-offset timezone objects (CEST/CET) for programme times, as the parser does, and ZoneInfo only for the evaluation tz"

requirements-completed: [FLT-08, FLT-09]

coverage:
  - id: D1
    description: "A calendar with window 22:00-02:00 and weekday Friday shows Friday 22:00 and Saturday 01:00 and hides Friday 01:00 and Saturday 02:00, in Europe/Berlin and America/New_York"
    requirement: FLT-09
    verification:
      - kind: integration
        ref: "tests/test_filtering.py#test_friday_night_window_end_to_end[berlin]"
        status: pass
      - kind: integration
        ref: "tests/test_filtering.py#test_friday_night_window_end_to_end[new-york]"
        status: pass
    human_judgment: false
  - id: D2
    description: "The flow preview applies the same window and weekday filter in the same time zone as the entity"
    requirement: FLT-09
    verification:
      - kind: unit
        ref: "tests/xmltv/test_preview.py#test_preview_uses_window_in_given_tz"
        status: pass
    human_judgment: false
  - id: D3
    description: "Half-open window, midnight anchoring, DST nights 2026-10-25 and 2027-03-28, and tolerance for incomplete/equal bounds and unknown weekdays"
    requirement: FLT-09
    verification:
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_window_and_weekday_table"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_apply_without_tz_evaluates_in_utc"
        status: pass
    human_judgment: false
  - id: D4
    description: "Inclusive min/max duration as exact timedeltas, empty = unbounded, DST-spanning duration is real time, WR-07 absurd stop hidden, huge stored values do not raise"
    requirement: FLT-08
    verification:
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_duration_bounds"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_duration_across_dst_fall_back"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_absurd_stop_hidden_by_max_duration"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_huge_stored_duration_does_not_raise"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every constraint must pass (D-14) and filtering keeps feed order, also for equal starts"
    requirement: FLT-09
    verification:
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_every_constraint_must_pass"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_filtering_keeps_feed_order_for_equal_starts"
        status: pass
    human_judgment: false
  - id: D6
    description: "Patterns with nested unbounded repetition are rejected with 'nested repetition can be very slow'; atomic/possessive/bounded patterns accepted; caps checked first; fail-open; (a|aa)+ residual documented"
    requirement: FLT-08
    verification:
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_nested_repetition_table"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_first_invalid_pattern_rejects_nested_repetition"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_shape_check_fails_open"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_caps_checked_before_shape"
        status: pass
    human_judgment: false

duration: 6 min
completed: 2026-10-15
---

# Phase 2 Plan 04: Duration, Time Window, Weekdays and Nested-Repetition Guard Summary

**Half-open local start-time window with midnight anchoring, weekdays and inclusive min/max duration, all evaluated in HA's time zone for both entity and preview, plus a fail-open `re._parser` walk that rejects nested unbounded repetition.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-15T11:03:47Z
- **Completed:** 2026-10-15T11:09:58Z
- **Tasks:** 3 (tracer + 2 TDD tasks)
- **Files modified:** 6 source/test files, 7 TDD evidence files

## Accomplishments

- `TimeWindow` with `from_times` (one bound missing or `from == to` means no window, D-12) and `anchor_date` (half-open `[from, to)`, after-midnight part anchors to the previous day, D-11)
- `FilterSpec.apply(epg, *, tz=UTC)` checks channel, duration, window/weekday, include, exclude, cheapest first (D-14). Local time conversion only happens when a window or weekdays are set. Without `tz`, evaluation is in UTC, so every Phase 1 test still passes.
- Duration bounds are inclusive and computed as `stop - start` on the parser's fixed-offset datetimes. A 2 h programme across the 2026-10-25 fall-back counts as 120 min. WR-07 (an absurd 72 h stop) is hidden by a max duration.
- The calendar entity refilters with `partial(spec.apply, epg, tz=dt_util.get_default_time_zone())`, and `build_preview` uses `apply(epg, tz=tz)`, so the preview and the calendar agree (D-10)
- `has_nested_repeat` plus the `first_invalid_pattern` message "nested repetition can be very slow" (WR-01, T-02-08)

## Task Commits

1. **Task 1 (tracer): Friday-night window end to end**
   - RED `3ce3747` test(02-04): add failing Friday-night window tracer tests
   - GREEN `50b6560` feat(02-04): filter by local time-of-day window and weekdays
   - Tracer gate: verify re-run passed (93 tests), expanded
2. **Task 2: Duration bounds plus window/weekday edge tables**
   - RED `b3e4b46` test(02-04): add duration, window, weekday and DST edge tables
   - GREEN `1dffbfd` feat(02-04): filter by inclusive min and max programme duration
3. **Task 3: Nested-repetition rejection**
   - RED `e28e154` test(02-04): add failing nested-repetition pattern tests
   - GREEN `667766b` feat(02-04): reject patterns with nested unbounded repetition

No REFACTOR commits were needed.

## TDD Gate Compliance

Each `test(02-04)` commit comes before its `feat(02-04)` commit. All RED records classify as `RED_EVIDENCE_OK (target_test_failed)`.

- **RED 1** (`02-04-red.json`, target `test_friday_night_window_end_to_end[berlin]`)
  - Failed on the summaries assertion: all four programmes were returned (first diff `'Das Erste: Freitag früh'`).
  - `[new-york]` and `test_preview_uses_window_in_given_tz` (count 4 != 2) failed for the same reason.
  - Semantic assessment: intended failure, no load or fixture fault.
- **RED 2 duration** (`02-04-red-2-duration.json`, target `test_duration_bounds[min30-max90-29]`)
  - A 29-minute programme passed min 30 / max 90 because there were no duration bounds yet.
  - These failed for the same reason: rows 91, 59m59s and 90m01s, DST max119/min121, huge-min-hides, and `test_every_constraint_must_pass`.
- **RED 2 WR-07** (`02-04-red-2-wr07.json`, target `test_absurd_stop_hidden_by_max_duration`)
  - A 72 h programme passed max 600.
- **Regression guards already green after Task 1** (listed per the plan):
  - All 20 `test_window_and_weekday_table` rows:
    - `fri-night-*`, `morning-*` and `weekend-*`
    - the DST rows `dst-2026-10-25-02:30-cest`, `dst-2026-10-25-02:30-cet`, `dst-2026-10-25-04:30-cet` and `dst-2027-03-28-03:30-cest`
    - `from-only`, `to-only`, `from-eq-to`, `unknown-weekday` and `empty-weekdays`
  - Plus the inclusive duration rows, `test_filtering_keeps_feed_order_for_equal_starts`, `test_apply_without_tz_evaluates_in_utc` and `huge-max-unbounded`.
  - The plan's DST "RED targets" were therefore already satisfied by Task 1's anchoring. Only the DST *duration* rows max119/min121 were genuinely red.
- **RED 3** (`02-04-red-3.json`, target `test_first_invalid_pattern_rejects_nested_repetition`)
  - `first_invalid_pattern` returned None. The three rejected table rows failed the same way.
  - Accepted rows, caps-first, fail-open and the `(a|aa)+` residual passed as guards.

## Decisions Made

- Huge stored durations are clamped to `timedelta.max // timedelta(minutes=1)` (orchestrator carry-over from 02-02). A huge min hides everything, a huge max is effectively unbounded, and nothing raises.
- The nested-repetition walk treats max > 1 as unbounded (RESEARCH Pattern 9), so `(a{2,3})*` is also rejected. It also descends `GROUPREF_EXISTS` branches, which closes a conditional-group bypass the research sketch left open. `RecursionError` is part of the fail-open set.
- Weekdays without a window use the local start date. With a window, the weekday is the day the window opened.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Clamp huge stored durations**
- **Found during:** Task 2
- **Issue:** `with_defaults` keeps any non-negative int, and `timedelta(minutes=10**16)` raises OverflowError. That would break `FilterSpec.from_mapping`, and with it the calendar entity and the preview.
- **Fix:** `_duration()` clamps to `_MAX_MINUTES`. New test `test_huge_stored_duration_does_not_raise` (huge-min-hides / huge-max-unbounded).
- **Files modified:** custom_components/xmltv_calendar/xmltv/filter.py, tests/xmltv/test_filter.py
- **Commit:** b3e4b46 (test), 1dffbfd (fix)

**2. [Rule 3 - Blocking] RED record target named with its parametrize id**
- **Found during:** Task 1
- **Issue:** The classifier matches exact JUnit test names. With the plain name `test_friday_night_window_end_to_end` it returned `INVALID_RED (no_target_test_failure)`.
- **Fix:** targetTest set to `test_friday_night_window_end_to_end[berlin]`, as in earlier records (e.g. `test_umlaut_pattern_matches_decomposed_feed[nfd-feed]`). The `[new-york]` failure is covered in the semantic assessment.
- **Commit:** 3ce3747

**Total deviations:** 2 auto-fixed (1 missing critical, 1 blocking). **Impact:** no scope change. The clamp hardens from_mapping against hand-edited data.

## Verification

- `uv run pytest -q -m "not benchmark"`: 423 passed, 1 skipped
- `uv run pytest -q -m benchmark`: 4 passed, 1 skipped (60 MB parse 2.83 s, max loop gap 115.4 ms, limit 250 ms)
- `uv run ruff check . && uv run ruff format --check .`: clean
- `uv run pytest tests/xmltv/test_purity.py -q`: 2 passed
- Acceptance greps: `get_default_time_zone` and `apply, epg, tz=` in calendar.py, `apply(epg, tz=tz)` in preview.py, `max_duration` and `nested repetition can be very slow` in filter.py, `2026-10-25`/`2027-03-28` parametrize ids in tests/xmltv/test_filter.py: all present

## Issues Encountered

None.

## Next Phase Readiness

- The calendar subentry flow still stores only the four Phase 1 keys (02-03 decision). The window, weekday and duration filters therefore act only on stored data until the advanced/reconfigure steps (02-05 onwards) write those keys.
- The flow already shows the new message for nested-repetition patterns through the existing `invalid_regex` error and its `error` placeholder.
- `build_preview` keeps its signature (coupling with 02-05).

## Self-Check: PASSED

- Key files exist: filter.py, calendar.py, preview.py, the three test files, and all seven tdd-evidence files
- Commits 3ce3747, 50b6560, b3e4b46, 1dffbfd, e28e154 and 667766b are ancestors of HEAD
- `git rev-list --count 2a903f0..HEAD` = 6
