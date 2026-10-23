---
phase: 05-richer-title-and-description-templating
plan: 04
subsystem: templating
tags: [jinja2, time-zone, calendar, matcher, preview, tdd, home-assistant]

requires:
  - phase: 05-richer-title-and-description-templating
    provides: "render.template_values and to_event_fields with a tz keyword, EventTemplates equality on sources, warn-once holder, time filter"
provides:
  - "start and end in templates are tz-aware datetimes in the Home Assistant zone on every surface: get_events, live event, next-match sensor, new-match event, flow preview"
  - "Zone resolved once on the event loop and passed into the executor build; build_events and _to_event take an optional tz"
  - "tests/test_template_runtime.py: tracer plus four runtime regression tests"
affects: [05-05 README (time zone behavior of start and end is now final)]

actuals:
  tokens: 3400
  tasks: 2
  commits: 3
plan_head_before: 0e9395c67fc662c9098a7cf8ef6464409beb64b5
plan_head_after: 7d04a14d2116540e241f3dae6586c403af617633

tech-stack:
  added: []
  patterns:
    - "Zone is a keyword/optional parameter resolved once per call (dt_util.get_default_time_zone) and handed to executor jobs as an argument"
    - "Runtime guarantees pinned at the entity level through the real subentry listener"

key-files:
  created:
    - tests/test_template_runtime.py
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-04-red.json
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-04-red.xml
  modified:
    - custom_components/xmltv_calendar/calendar.py
    - custom_components/xmltv_calendar/matcher.py
    - custom_components/xmltv_calendar/xmltv/preview.py
    - tests/test_calendar.py
    - tests/xmltv/test_preview.py

key-decisions:
  - "build_events defaults tz=None to dt_util.get_default_time_zone(), resolved once at the start of the call, so existing positional callers keep working"
  - "async_get_events resolves the zone on the loop before the size decision and passes it as one more executor argument"
  - "The monkeypatched _to_event in an existing test now forwards extra positional arguments, so it holds before and after the signature change"

patterns-established:
  - "Every call site that renders templates passes the Home Assistant zone explicitly; the engine never reads global time zone state"

requirements-completed: [EVT-03, EVT-04, EVT-10]

coverage:
  - id: D1
    description: "A UTC feed under Europe/Berlin shows Berlin wall time with +02:00 for start and end in get_events, the live event, the sensor summary and the new-match event summary"
    requirement: EVT-10
    verification:
      - kind: integration
        ref: "tests/test_template_runtime.py#test_start_variable_is_local_time_everywhere"
        status: pass
    human_judgment: false
  - id: D2
    description: "The flow preview and build_events render start in the given zone, defaulting to the Home Assistant zone"
    requirement: EVT-10
    verification:
      - kind: unit
        ref: "tests/xmltv/test_preview.py#test_preview_title_template_shows_the_local_start"
        status: pass
      - kind: unit
        ref: "tests/test_calendar.py#test_build_events_converts_start_for_templates_in_the_given_zone"
        status: pass
    human_judgment: false
  - id: D3
    description: "A stored template that raises at render time returns every event with fallback title and default description and logs one WARNING naming the calendar and the exception type, without feed text"
    requirement: EVT-04
    verification:
      - kind: integration
        ref: "tests/test_template_runtime.py#test_runtime_failure_warns_once_per_calendar"
        status: pass
    human_judgment: false
  - id: D4
    description: "Template edits never re-announce matches, change UIDs or the seen-set; equal-source data edits send no signal; a hand-edited legacy template warns once"
    requirement: EVT-03
    verification:
      - kind: integration
        ref: "tests/test_template_runtime.py#test_template_edit_does_not_reannounce_matches"
        status: pass
      - kind: integration
        ref: "tests/test_template_runtime.py#test_noop_data_change_sends_no_template_signal"
        status: pass
      - kind: integration
        ref: "tests/test_template_runtime.py#test_stored_edit_to_legacy_text_warns_once_and_renders_default"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-10-23
status: complete
---

# Phase 5 Plan 04: Local Time at Every Call Site and Runtime Regressions Summary

**Home Assistant zone threaded through calendar events, the live event, the sensor and new-match summaries and the flow preview, so a UTC feed prints Berlin wall time in `{{ start }}` and `{{ end }}` everywhere; runtime fallbacks, single warnings and edit side effects pinned by entity-level tests**

## Performance

- **Duration:** 10 min
- **Started:** 2026-10-23T21:43:00Z
- **Completed:** 2026-10-23T21:53:00Z
- **Tasks:** 2 (tracer with RED/GREEN, then a regression suite)
- **Files modified:** 5 changed, 1 test file created, 2 RED evidence files

## Accomplishments

- `calendar.py`: `_to_event` and `build_events` take an optional `tz` (default `None`, resolved once per `build_events` call), the live `event` property passes the default zone, and `async_get_events` resolves the zone on the event loop before the size decision and hands it to the executor job as one more argument.
- `matcher.describe_match` renders with `tz=dt_util.get_default_time_zone()`, which feeds the next-match sensor summary and the new-match event summary.
- `preview.build_preview` passes the `tz` it already held to `to_event_fields`.
- `tests/test_template_runtime.py::test_start_variable_is_local_time_everywhere`: a UTC feed under Europe/Berlin (10:00 UTC prints as 12:00 with +02:00) checked on get_events (start via the title, end via the description template), the calendar's live `message` attribute, the sensor `summary` attribute and the new-match event.
- Four regression tests cover warn-once per calendar, no re-announce on a template edit, no signal for an equal-source data edit, and one WARNING for hand-edited legacy text.

## Task Commits

1. **Task 1: Tracer, local start and end everywhere** (TDD)
   - RED: `66b3a5c` (test), `RED_EVIDENCE_OK`
   - GREEN: `c13b440` (feat)
2. **Task 2: Runtime regressions** (TDD, regression suite) - `7d04a14` (test); no production change needed

**Plan metadata:** committed after this file (docs: complete plan)

## TDD Gate Compliance

- **RED (Task 1):** target `test_start_variable_is_local_time_everywhere`, record `tdd-evidence/05-04-red.json`, `RED_EVIDENCE_OK` (`target_test_failed`). Semantic assessment: the target ran a full setup with a UTC feed under Europe/Berlin and failed on the planned summary assertion (`Live @ 2026-10-13 05:00:00+00:00` instead of `07:00:00+02:00`) because no call site passed a zone; no import or fixture fault. The preview test failed on the same offset assertion; the `build_events` zone test failed with a TypeError on the missing fourth parameter (accepted as part of the RED set, not used as the target).
- **GREEN:** the verify command passes (96 passed) and the full suite passes (1252 passed, 1 skipped, 4 deselected).
- **Task 2:** all four new tests were green before any production change (the plan anticipated this: 05-01 already implements source equality, warn-once and UID independence), so no RED record was written and the task is a regression suite, the same pattern as Phases 2 and 4. The one failure seen while writing them was a wrong expected value in my test (the summary list was missing the Tagesschau row and the channel prefix), not a behavior failure.
- **REFACTOR:** not needed.
- Gate commits found: `test(05-04)` precedes `feat(05-04)` for Task 1.

## Files Created/Modified

- `custom_components/xmltv_calendar/calendar.py` - zone resolved once and passed to `build_events`, `_to_event`, the live event and the executor job
- `custom_components/xmltv_calendar/matcher.py` - `describe_match` passes the local zone to `template_values`
- `custom_components/xmltv_calendar/xmltv/preview.py` - `to_event_fields(..., tz=tz)`
- `tests/test_template_runtime.py` (new) - tracer and four regressions
- `tests/test_calendar.py` - `build_events` zone test; the `flaky` monkeypatch forwards extra positional arguments
- `tests/xmltv/test_preview.py` - local start in the preview line
- `.planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-04-red.*` - RED record and JUnit report

## Decisions Made

- Followed the plan as written. `build_events` keeps the three-argument call working by resolving the default zone itself.
- The live-event path and the sensor read the zone per call on the event loop; only the batch path resolves it once and passes it explicitly, because that one can run in an executor thread.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing monkeypatch of `_to_event` rejected the new fourth argument**
- **Found during:** Task 1 RED
- **Issue:** `test_build_events_skips_value_error` replaced `_to_event` with a three-parameter function, which `build_events` now calls with the zone.
- **Fix:** The stand-in takes `*zone` and forwards it, so it works before and after the signature change.
- **Files modified:** `tests/test_calendar.py`
- **Commit:** `66b3a5c`

**Total deviations:** 1 auto-fixed (blocking, test-only). **Impact:** none on scope or behavior.

## Issues Encountered

One foreground full-suite run stalled its tool call (the same suite finishes in about 22 seconds when run detached with output to a file); no test was hung or flaky.

## Known Stubs

None.

## Threat Flags

None. T-05-13 (warnings carry only the calendar name and exception type or reason key) and T-05-14 (UIDs, seen-set and announcements unchanged by template edits) are covered by tests; T-05-15 holds (zone resolved once per call, large slices stay in the executor); T-05-SC holds (no packages added).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for 05-05: `start`, `end` and the `time` filter now show Home Assistant local time on every surface, so the README can document local time without exceptions. The zone is the Home Assistant configured zone, not the feed's offset.

## Self-Check: PASSED

- Files exist: `tests/test_template_runtime.py`, `05-04-red.json`, `05-04-red.xml`, and the three modified source files.
- Commits found: `66b3a5c`, `c13b440`, `7d04a14`.
- Acceptance criteria re-run: verify commands green, `get_default_time_zone` appears 3 times in `calendar.py`, `tz=tz` appears twice in `preview.py`, 5 `async def test_` in `test_template_runtime.py`, `ruff check .` and `ruff format --check .` clean, `pytest -m "not benchmark"` 1252 passed, 1 skipped.

---
*Phase: 05-richer-title-and-description-templating*
*Completed: 2026-10-23*
