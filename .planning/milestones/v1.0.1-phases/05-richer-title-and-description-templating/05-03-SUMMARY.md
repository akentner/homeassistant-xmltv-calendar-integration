---
phase: 05-richer-title-and-description-templating
plan: 03
subsystem: templating
tags: [jinja2, sandbox, filters, resource-limits, tdd, home-assistant]

requires:
  - phase: 05-richer-title-and-description-templating
    provides: "Sandboxed engine, CUSTOM_FILTERS registry, text-coercion helper, shared pattern cache, compile-time regex checks, EventTemplates facade with warn-once fallback"
provides:
  - "Nine custom filters (first_line, lines, split, regex_search, strip_prefix, strip_suffix, remove, time) plus a size-guarded replace, next to regex_replace"
  - "D-06 vocabulary test that fails when any named filter is missing"
  - "Filter chain cap 16, text literal cap 300, result cap 50000 characters"
  - "Hostile-input corpus with a one second bound per case"
affects: [05-04 local time at call sites (time filter is ready), 05-05 README (filter names and signatures are fixed here)]

actuals:
  tokens: 6300
  tasks: 3
  commits: 6
plan_head_before: 3b3b2f516e5270a7aac1e9a5499f36cf85e2d221
plan_head_after: 9fb1453468cde04e4de63253049e46a77401185d

tech-stack:
  added: []
  patterns:
    - "Every custom filter coerces its text arguments through one helper, so None and undefined are empty text"
    - "Result-size guard raises ValueError; the facade fallback of D-03 turns it into the programme title"
    - "Caps are checked in the allow-list walk, before anything is compiled"

key-files:
  created:
    - tests/xmltv/test_template_filters.py
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-03-red.json
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-03-red-2.json
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-03-red-2-time.json
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-03-red-3-chain.json
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-03-red-3-literal.json
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-03-red-3-replace.json
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-03-red-3-fallback.json
  modified:
    - custom_components/xmltv_calendar/xmltv/template_engine.py
    - tests/xmltv/test_template_engine.py

key-decisions:
  - "time uses an isinstance(datetime) test and a text-format check; strftime is never wrapped, so a bad directive is a render error that the D-03 fallback handles"
  - "split returns an empty list for empty text and the whole text for an empty separator, never raises"
  - "Chain length is counted once per chain: the walk meets the last filter of a chain first and raises there"
  - "The literal cap applies to every string constant in an expression (also in set and if), not only to regex patterns"
  - "replace is the one standard filter overridden (A12): same signature, plus a result-size guard"

patterns-established:
  - "New filters are added as a function plus one CUSTOM_FILTERS entry; the pruned environment and the compile-time check pick them up"
  - "The D-06 name list lives in one test, so removing or renaming a filter fails loudly"

requirements-completed: [EVT-10]

coverage:
  - id: D1
    description: "First description line as a title part and an optional sub-title behind if, through the real EventTemplates facade"
    requirement: EVT-10
    verification:
      - kind: integration
        ref: "tests/xmltv/test_template_filters.py#test_first_description_line_as_title_part"
        status: pass
      - kind: integration
        ref: "tests/xmltv/test_template_filters.py#test_optional_sub_title_behind_if"
        status: pass
    human_judgment: false
  - id: D2
    description: "All D-06 filters exist, behave on missing data, and time formats start and end in the caller's zone; now, states and hass are unknown"
    requirement: EVT-10
    verification:
      - kind: unit
        ref: "tests/xmltv/test_template_filters.py#test_every_d06_filter_is_available"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_template_filters.py#test_time_formats_start_and_end_in_the_zone_the_caller_converted_them_to"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_template_filters.py#test_no_filter_global_or_variable_reads_ha_state_the_clock_or_the_environment"
        status: pass
    human_judgment: false
  - id: D3
    description: "compile_template raises only TemplateError and rejects hostile templates in under a second: chain cap 16, literal cap 300, wrapped Python compile limits"
    requirement: EVT-10
    verification:
      - kind: unit
        ref: "tests/xmltv/test_template_engine.py#test_hostile_templates_are_rejected_quickly"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_template_engine.py#test_a_chain_of_16_filters_compiles_and_17_is_rejected"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_template_engine.py#test_a_text_literal_in_an_expression_is_capped_at_300_characters"
        status: pass
    human_judgment: false
  - id: D4
    description: "replace and regex_replace refuse a result over 50000 characters; the render fallback degrades to the programme title with one WARNING and no feed text"
    requirement: EVT-10
    verification:
      - kind: unit
        ref: "tests/xmltv/test_template_engine.py#test_a_compounding_chain_of_replace_calls_stops_at_the_first_oversized_step"
        status: pass
      - kind: integration
        ref: "tests/xmltv/test_template_filters.py#test_an_oversized_replace_falls_back_with_one_warning_and_no_feed_text"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-10-23
status: complete
---

# Phase 5 Plan 03: Text Filters, Local Time and Resource Bounds Summary

**Nine D-06 template filters (lines, first_line, split, regex_search, strip_prefix, strip_suffix, remove, time, size-guarded replace) with a chain cap of 16, literal cap of 300 and result cap of 50000 characters, proven through EventTemplates and a hostile-input corpus**

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-23T21:36:11Z
- **Completed:** 2026-10-23T21:42:00Z
- **Tasks:** 3 (tracer, then two auto tasks, all TDD)
- **Files modified:** 2 source and test files changed, 1 test file created, 7 RED evidence records

## Accomplishments

- `first_line` and `lines` (A9: blank lines dropped, each line stripped) make the two driving use cases of D-07 work end to end: `{{ channel }}: {{ description | first_line }}` gives "Das Erste: Qualifying" and loses the dangling separator without a description, and `{% set sub = description | first_line %}...{% if sub %}` shows the sub-title only when there is one.
- `split`, `regex_search` (boolean, A8, covered by the 05-01 compile-time pattern checks), `strip_prefix`, `strip_suffix`, `remove` and `time` complete the D-06 list. `time` formats `start` and `end` in the zone the caller converted them to and renders empty for anything that is not a datetime.
- `test_every_d06_filter_is_available` iterates the full D-06 list and renders a smoke template for each; `now`, `states`, `hass`, `environ` and `config` are unknown variables, filters or calls.
- `MAX_FILTER_CHAIN = 16` and `MAX_LITERAL_LENGTH = 300` are enforced in the allow-list walk. The 143 and 286 filter chains are rejected in about 1 and 2 ms (before: 0.7 s and 5.3 s of compile time).
- `replace` is the size-guarded variant (A12); `regex_replace` shares the guard. A 5000 character title with a 300 character replacement stops at the first step and falls back to the programme title with one WARNING per calendar.

## Task Commits

1. **Task 1: Tracer, first description line through EventTemplates** (TDD)
   - RED: `f8afca3` (test), `RED_EVIDENCE_OK`
   - GREEN: `31aa363` (feat)
2. **Task 2: Remaining D-06 filters** (TDD)
   - RED: `e6b7468` (test), `RED_EVIDENCE_OK` for two targets
   - GREEN: `d7bfaef` (feat)
3. **Task 3: Resource bounds** (TDD)
   - RED: `7a55981` (test), `RED_EVIDENCE_OK` for four targets
   - GREEN: `9fb1453` (feat)

**Plan metadata:** committed after this file (docs: complete plan)

## TDD Gate Compliance

- **RED (Task 1):** target `test_first_description_line_as_title_part`, record `tdd-evidence/05-03-red.json`, `RED_EVIDENCE_OK` (`target_test_failed`). Semantic assessment: the target ran through `EventTemplates.from_mapping` and `to_event_fields` and failed on its summary assertion because `first_line` did not exist (compile rejects it as `unknown_filter`, the facade silently falls back to the default title). All 13 new tests failed for that reason; no import or fixture fault.
- **RED (Task 2):** targets `test_every_d06_filter_is_available` (`05-03-red-2.json`, six names missing) and `test_time_formats_start_and_end_in_the_zone_the_caller_converted_them_to` (`05-03-red-2-time.json`), both `RED_EVIDENCE_OK`. 16 of 36 tests failed; the rest are pre-existing guards.
- **RED (Task 3):** targets `test_a_chain_of_16_filters_compiles_and_17_is_rejected` (`-chain`), `test_a_text_literal_in_an_expression_is_capped_at_300_characters` (`-literal`), `test_an_oversized_replace_result_is_a_runtime_error` (`-replace`) and `test_an_oversized_replace_falls_back_with_one_warning_and_no_feed_text` (`-fallback`), all `RED_EVIDENCE_OK`, all failing on DID NOT RAISE or a missing fallback, not on setup. The first attempt imported the new constants at module level and failed at collection (INVALID_RED); the tests were reworked to reach the missing behavior through the registered filters and literal numbers before any record was written.
- **GREEN:** each task's verify command and the full suite pass (1245 passed, 1 skipped, 4 deselected).
- **REFACTOR:** not needed.
- **Guard-only cases green before the change** (regression guards, named per the acceptance criteria): the wrapping of `SyntaxError`, `IndentationError` and `RecursionError` into `invalid_template` was already in place from 05-01, so every entry of the hostile corpus except the 143 filter chain passed before GREEN, including the 130 nested ifs, 500 nested parentheses, huge power, modulo, range, method call, self and star-arguments cases. They stay as the TemplateError-only and one-second contract.
- Gate commits found: `test(05-03)` precedes `feat(05-03)` for each task.

## Files Created/Modified

- `custom_components/xmltv_calendar/xmltv/template_engine.py` - the new filters, `MAX_FILTER_CHAIN`, `MAX_LITERAL_LENGTH`, `MAX_RESULT_CHARS`, `_bounded`, chain and literal checks in the walk
- `tests/xmltv/test_template_filters.py` (new) - filter behavior, D-07 recipes, `test_every_d06_filter_is_available`, oversized-render fallback
- `tests/xmltv/test_template_engine.py` - bounds, hostile corpus (19 cases), guarded replace
- `.planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-03-*` - RED records and JUnit reports

## Decisions Made

- Followed A1, A3 (only numeric strftime directives are meant to be documented), A8, A9 and A12 as planned.
- A malformed strftime directive cannot be provoked on this Python (glibc passes unknown directives through), so the render-error behavior is tested with a datetime subclass whose `strftime` raises; `time` itself does not catch anything.
- Replace does not pre-estimate the result size, it checks after the call. The transient allocation is bounded by input length times the 300 character literal cap.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] First RED run failed at collection**
- **Found during:** Task 3 RED
- **Issue:** The new tests imported `MAX_FILTER_CHAIN`, `MAX_LITERAL_LENGTH`, `MAX_RESULT_CHARS` and `replace` at module level, so the whole module failed at import, which the classifier treats as INVALID_RED.
- **Fix:** Reworked the RED tests to use literal numbers and `ENV.filters["replace"]`; the constants are imported directly in the GREEN commit.
- **Files modified:** `tests/xmltv/test_template_engine.py`
- **Commit:** `7a55981` (RED), `9fb1453` (imports)

**2. [Test design] `|` and `:` are edge separators in clean_title**
- **Found during:** Task 1 GREEN
- **Issue:** `"|0"` rendered through a title template loses its leading `|`.
- **Fix:** The assertion wraps the output in brackets.
- **Files modified:** `tests/xmltv/test_template_filters.py`
- **Commit:** `31aa363`

Plan item adjusted, not a deviation: the plan asked to add the `SyntaxError, IndentationError, RecursionError` wrapper; it already existed from 05-01 (`except SyntaxError, RecursionError`, IndentationError being a subclass), so GREEN only added the two caps and the guards.

**Total deviations:** 2 auto-fixed (1 blocking, 1 test design). **Impact:** none on scope or behavior.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. T-05-10 and T-05-11 are mitigated and tested (hostile corpus, compounding replace chain); T-05-SC holds (no packages added).

## Accepted Residual Risk (T-05-12, for the user)

Reusing a `set` variable many times with the tilde operator can still grow a value exponentially (for example doubling a variable ten times in a row with `~`). It needs a hand-crafted template from a Home Assistant admin, is bounded by the template length caps (2000 and 5000 characters) and cannot be reached from feed content. D-04's sentence "render cost stays linear and small" holds for every template except that adversarial construction. Disposition is accept; no mitigation was added. If you want it closed, a result-size check on the concatenation (the same `MAX_RESULT_CHARS`) would need a custom `Concat` handling, which is a larger change than this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for 05-04: `time` is registered and expects `start` and `end` already converted to the local zone; call sites (`calendar.py`, `matcher.describe_match`, `preview.py`) still pass no `tz`, so `time` shows the feed offset until 05-04.
- Ready for 05-05: filter names and signatures are fixed here (`split(sep, maxsplit)`, `regex_search(find, ignorecase)`, `strip_prefix(text)`, `strip_suffix(text)`, `remove(*parts)`, `time(fmt='%H:%M')`, `lines`, `first_line`, guarded `replace(old, new, count)`).
- No new template error reason was added, so the translation completeness test is unaffected.

## Self-Check: PASSED

- Files exist: `template_engine.py`, `test_template_filters.py`, `test_template_engine.py`, all seven `05-03-red*.json` records.
- Commits found: `f8afca3`, `31aa363`, `e6b7468`, `d7bfaef`, `7a55981`, `9fb1453`.
- Acceptance criteria re-run: verify commands green, `CUSTOM_FILTERS` check exits 0, greps pass (`MAX_*` 11 lines, test names present), `tests/xmltv/test_purity.py` passes; `ruff check .` and `ruff format --check .` clean; `pytest -m "not benchmark"` 1245 passed, 1 skipped.

---
*Phase: 05-richer-title-and-description-templating*
*Completed: 2026-10-23*
