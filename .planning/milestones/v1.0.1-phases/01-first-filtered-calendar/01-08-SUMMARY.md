---
phase: 01-first-filtered-calendar
plan: 08
subsystem: config-flow
tags: [home-assistant, config-subentry, regex, validation, calendar, lifecycle]
requires:
  - phase: 01-01
    provides: "CalendarSubentryFlow (name + channels, source_not_loaded abort, name_required), diffing update listener, setup_xmltv harness"
  - phase: 01-03
    provides: "first_invalid_pattern, MAX_PATTERN_LENGTH=300, MAX_PATTERN_LINES=50, FilterSpec channel/regex/include/exclude semantics"
  - phase: 01-07
    provides: "Validated url/file source steps (unchanged here)"
provides:
  - "Add calendar form with name, channels (sorted ID picker), channel_regex, include, exclude (multiline)"
  - "Flow-side pattern validation: invalid_regex per field with pattern/error placeholders; nothing invalid is stored"
  - "Stored subentry data schema {channels, channel_regex, include, exclude}"
  - "Multi-calendar lifecycle regression suite (tests/test_init.py)"
affects: [01-09, 01-10, phase-02-reconfigure]
actuals:
  tokens: 39267   # chars/4 over the full realized diff (157,068 chars); code + tests alone are 27,055 chars (~6,764), the rest is JUnit/JSON RED evidence
  tasks: 3
  commits: 5
plan_head_before: 7130822ab4d4c9ee1103410f5dbc7e4d7721c546
plan_head_after: 689f22a476f60a9aa2e0ca58efd3bcc69b9e6ec2
tech-stack:
  added: []
  patterns:
    - "Pattern fields share one tuple _PATTERN_FIELDS for schema, validation and stored data"
    - "Flow collects every field error at once (name + patterns); first bad pattern fills the placeholders"
    - "Device lookups in tests use async_get_device_by_identifier(identifier, entry_id); async_get_device raises on HA 2026.10"
key-files:
  created:
    - tests/test_subentry_flow.py
    - tests/test_init.py
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-08-red.{xml,json}
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-08-red-2.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-08-red-2-{invalid,caps,suggested}.json
  modified:
    - custom_components/xmltv_calendar/config_flow.py
    - custom_components/xmltv_calendar/translations/en.json
key-decisions:
  - "01-08: pattern fields are stored as raw text (blank lines kept); FilterSpec strips and skips them at filter time"
  - "01-08: when several pattern fields are invalid, every field gets invalid_regex but the placeholders show the first bad pattern (field order channel_regex, include, exclude)"
  - "01-08: the 01-01 diffing listener already met FLT-01; tests/test_init.py is its regression suite and __init__.py is unchanged"
patterns-established:
  - "Subentry form: all filter inputs optional with default empty string; empty channels + empty channel_regex means all channels"
requirements-completed: [FLT-01, FLT-02, FLT-03, FLT-04, FLT-07, CFG-01]
coverage:
  - id: D1
    description: "A calendar with an include pattern is created entirely through the Add calendar form and shows only the matching programmes; exclude, channel regex and channels-OR-regex are applied"
    requirement: "FLT-03"
    verification:
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_include_calendar_via_form_end_to_end"
        status: pass
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_form_filters_are_applied"
        status: pass
    human_judgment: false
  - id: D2
    description: "Invalid, over-long (301 chars) or excessive (51 lines) pattern lines keep the form open with invalid_regex and the offending line; blank lines are ignored; input is kept as suggested values"
    requirement: "FLT-07"
    verification:
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_invalid_pattern_line_keeps_form_open"
        status: pass
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_oversized_patterns_are_rejected"
        status: pass
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_blank_lines_only_are_ignored"
        status: pass
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_input_is_kept_after_a_validation_error"
        status: pass
    human_judgment: false
  - id: D3
    description: "Subentry flow on an unloaded (SETUP_RETRY) source aborts with source_not_loaded"
    requirement: "CFG-01"
    verification:
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_unloaded_source_aborts"
        status: pass
    human_judgment: false
  - id: D4
    description: "Channel picker lists plain channel IDs sorted ascending; selection order does not change matches"
    requirement: "FLT-02"
    verification:
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_channel_picker_lists_sorted_ids"
        status: pass
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_channel_selection_order_does_not_change_matches"
        status: pass
    human_judgment: false
  - id: D5
    description: "Several calendars per source share one download; add/remove live without refetch; rename does not reload; data/options change reloads once; one entity per pre-existing subentry; identical filters give two entities; zero calendars loads"
    requirement: "FLT-01"
    verification:
      - kind: integration
        ref: "tests/test_init.py (10 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The new form fields, data_description examples and invalid_regex message render readably in the real HA frontend (multiline text areas, placeholders filled)"
    verification: []
    human_judgment: true
    rationale: "No frontend in the test harness; checked by hand on the ha-dev container in plan 01-09"
duration: 4min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 08: Calendar Filters in the Form Summary

**The Add calendar form now takes channel regex, include and exclude as multiline pattern fields. Each line is validated with `first_invalid_pattern` before anything is stored, so a bad line shows `invalid_regex` with the line and the regex error. A 10-test lifecycle suite proves that several calendars share one download and can be added, removed and renamed live.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-13T23:51:57Z
- **Completed:** 2026-10-13T23:56:40Z
- **Tasks:** 3
- **Files modified:** 4 code/test files plus 6 RED-evidence artifacts

## Accomplishments

- `CalendarSubentryFlow` offers name, channels (sorted ID picker), channel regex, include and exclude. The last three are optional `TextSelector(multiline=True)` fields. Subentry data is `{channels, channel_regex, include, exclude}`, with the raw text stored.
- Flow validation (FLT-07, T-01-23):
  - every pattern field goes through `first_invalid_pattern` (compile check, 300-character cap, 50-line cap)
  - errors are reported per field as `invalid_regex`, with `{pattern}` / `{error}` placeholders
  - a blank name and bad patterns are reported together
  - the form is re-shown with the user's input as suggested values
- The translations give examples for every field: `formel\s*1|formula\s*1`, `^Tatort$`, `^sky`, `\.de$`. They also explain the OR between channels and channel regex.
- `tests/test_init.py` pins the multi-calendar lifecycle: one download for several calendars, live add/remove, rename without reload, a single reload on data or options change, one entity per subentry, `calendar.same_2` for identical filters, and a zero-calendar source that still loads.

## Task Commits

1. **Task 1: Tracer, include calendar through the form** (type tracer)
   - `9853694` test(01-08): RED, tracer plus exclude/channel-regex cases and evidence
   - `f25a425` feat(01-08): GREEN, three multiline fields, stored data, translations
   - Tracer feedback gate: interactive, `end-of-phase`, automated-only verify. Re-ran `uv run pytest tests/test_subentry_flow.py tests/test_tracer.py -q` (5 passed), then expanded.
2. **Task 2: Pattern validation, unloaded-source abort, picker ordering**
   - `9650b86` test(01-08): RED, validation tests plus evidence
   - `bca7b1f` feat(01-08): GREEN, `first_invalid_pattern` in the flow plus the `invalid_regex` translation
3. **Task 3: Several calendars per source**
   - `689f22a` test(01-08): regression suite only (all green against the 01-01 listener)

## TDD Gate Compliance

| Cycle | RED | GREEN | REFACTOR |
|-------|-----|-------|----------|
| Task 1 (tracer) | `9853694` | `f25a425` | none needed |
| Task 2 | `9650b86` | `bca7b1f` | none needed |
| Task 3 | `689f22a` (regression suite) | none needed: no production change | none |

**RED 1:** `test_include_calendar_via_form_end_to_end` (`01-08-red.json`). Classifier verdict: RED_EVIDENCE_OK (target_test_failed).
- Semantic assessment: the target was collected and ran with `forbid_loop_io` active. The source loaded with no calendars and the subentry flow returned a FORM. The test then failed on the planned schema-key assertion, because `channel_regex`, `include` and `exclude` were missing. The three `test_form_filters_are_applied` cases failed with `InvalidData at 'include'`, for the same missing-field reason. There was no import, collection or fixture fault.

**RED 2:** one report (`01-08-red-2.xml`) with 8 failures and 10 passes. All three targets were RED_EVIDENCE_OK:
- `test_invalid_pattern_line_keeps_form_open[include]`
- `test_oversized_patterns_are_rejected[channel-regex-51-lines]`
- `test_input_is_kept_after_a_validation_error`

Each one failed on the planned `result type is FORM` assertion: the flow returned CREATE_ENTRY because nothing validated the patterns. Of the 10 passes:
- 4 are Task 1 tests
- 6 are characterization tests (see Deviations, item 1)

**GREEN:** every target passes. `uv run pytest -q -m "not benchmark"` gives 209 passed.

**Task 3:** RED is not applicable. All 10 behaviour tests passed against the 01-01 listener, so per the plan they are recorded as the FLT-01 regression suite. A mutation check confirmed that they bite:
- making the listener always reload fails 3 tests
- dropping the live `add_entities` call fails 2 tests

## Files Created/Modified

- `custom_components/xmltv_calendar/config_flow.py`: `_PATTERN_FIELDS`, the three multiline fields, `first_invalid_pattern` validation with placeholders, the combined name and pattern error handling, and the stored data schema.
- `custom_components/xmltv_calendar/translations/en.json`:
  - `config_subentries.calendar.step.user.data` and `data_description` for `channel_regex`, `include` and `exclude`, plus a reworded `channels` description
  - `error.invalid_regex`: "Invalid pattern {pattern}: {error}. …" (placeholders unquoted, per Pitfall 12)
- `tests/test_subentry_flow.py`: 18 tests covering the form tracer, filters through the form, validation and caps, blank lines, suggested values, `name_required`, `source_not_loaded`, the sorted picker, and selection order.
- `tests/test_init.py`: 10 multi-calendar lifecycle tests.

## Decisions Made

- Pattern text is stored raw, blank lines included (D-05, D-06). `FilterSpec` strips the text and skips blank lines when it compiles, so the flow and the filter agree on what counts as a line.
- When several pattern fields are invalid, every one of them gets `invalid_regex`. The description placeholders show the first bad line, in field order channel_regex, include, exclude. HA has a single placeholder namespace per form.
- `abort.source_not_loaded`, `error.name_required` and the LOADED-state check already existed from 01-01, so they were kept unchanged.
- `__init__.py` is unchanged: the 01-01 diffing listener already meets FLT-01.

## Deviations from Plan

### Auto-fixed Issues

**1. [Plan inconsistency] 6 Task 2 tests were green in RED**
- **Found during:** Task 2 RED
- **Issue:** 01-01 had already built the `source_not_loaded` abort, `name_required` and the sorted ID picker. The blank-lines-ignored behaviour, the 50x300 limit acceptance and selection-order independence came from the Task 1 GREEN plus the 01-03 filter engine.
- **Fix:** Kept them as characterization tests. The Task 2 RED evidence rests on the three validation targets, which failed.
- **Committed in:** 9650b86

**2. [Plan detail] Tracer feed built inline instead of extending basic.xml**
- **Found during:** Task 1 RED
- **Issue:** `basic.xml` already contains "Formel 1: Großer Preis von Mexiko". Adding the two planned programmes would give three motorsport matches, which contradicts "exactly the two motorsport programmes".
- **Fix:** `MOTORSPORT_FEED` keeps basic.xml's channels and non-motorsport titles and has exactly the two planned programmes ("Formel 1: Rennen" on daserste.de, "Formula 1 Highlights" on zdf.de).
- **Committed in:** 9853694

**3. [Rule 3 - Blocking] Device lookup API in tests**
- **Found during:** Task 3
- **Issue:** On HA 2026.10, `DeviceRegistry.async_get_device(identifiers=…)` raises `RuntimeError` in tests: it is deprecated because identifiers are no longer globally unique.
- **Fix:** The tests use `async_get_device_by_identifier((DOMAIN, subentry_id), entry.entry_id)`. Production code does not look up devices.
- **Committed in:** 689f22a

**4. [Rule 2 - Coverage] Extra lifecycle and limit cases**
- **Found during:** Tasks 2 and 3
- **Issue:** The must-haves name several things without a dedicated test:
  - "changing the source's data … reloads it once"
  - the add/remove order backstop
  - the accepting side of the caps
- **Fix:** Added `test_data_change_reloads_once`, `test_add_and_remove_order_does_not_change_events` and `test_fifty_patterns_and_300_chars_are_accepted`.
- **Committed in:** 9650b86, 689f22a

---

**Total deviations:** 4 (1 plan inconsistency, 1 plan detail, 1 blocking test API, 1 coverage addition)
**Impact on plan:** None of these changed an interface or added scope. `__init__.py` was listed in files_modified but needed no change, and `calendar.py` was not touched.

## Issues Encountered

- The mutation check showed that the platform-side duplicate guard in `calendar.async_setup_entry` (`subentry_id in runtime.calendars`) is defensive only. The listener never fires during the initial platform setup, so no test can make that guard matter today. It is left in place; 01-04 owns `calendar.py`.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- 01-09 (the manual check on ha-dev) should look at:
  - how the multiline fields and the `invalid_regex` message render
  - the channel picker with a large real feed (RESEARCH A4; the channel regex field is the agreed fallback)
- Phase 2 reconfigure (FLT-11) can reuse `_PATTERN_FIELDS` and the validation block. With the update listener registered, it must use `async_update_and_abort`.

## Self-Check: PASSED

- FOUND: tests/test_subentry_flow.py, tests/test_init.py, config_flow.py, translations/en.json, tdd-evidence/01-08-red.json, tdd-evidence/01-08-red-2.xml
- FOUND commits: 9853694, f25a425, 9650b86, bca7b1f, 689f22a (evaluation-scope resolved 5 plan commits on this branch)
- Plan verification: `uv run pytest -q -m "not benchmark"` 209 passed; `uv run ruff check . && uv run ruff format --check .` clean

---
*Phase: 01-first-filtered-calendar*
*Completed: 2026-10-14*
