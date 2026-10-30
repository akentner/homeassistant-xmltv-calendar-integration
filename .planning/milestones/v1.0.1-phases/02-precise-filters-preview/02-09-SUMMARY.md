---
phase: 02-precise-filters-preview
plan: 09
subsystem: filter-engine
tags: [home-assistant, regex, re.compile, overflowerror, recursionerror, gap-closure, tdd]

requires:
  - phase: 02-precise-filters-preview
    provides: "02-01 _build_spec / keep-previous-matches listener (T-02-01), 02-04 nested-repetition check, 02-05 in-place edit save"
provides:
  - "PATTERN_ERRORS = (re.error, OverflowError, RecursionError) in xmltv/filter.py, the one shared definition of 'does not compile'"
  - "calendar._build_spec contains every re.compile failure of stored patterns: platform setup and update listener keep working"
  - "first_invalid_pattern maps every re.compile failure to InvalidPattern, so the calendar form shows invalid_regex instead of Unknown error"
  - "Regression tests at listener, platform-setup, pure-validation, add-form and edit-form level"
affects: [phase-02-verification, phase-02-review-disposition, phase-03]

actuals:
  tokens: 3600
  tasks: 2
  commits: 4
plan_head_before: 8849935078fb14944c0e3db2f09fda2b9f2516c9
plan_head_after: 1ca6646458a64c72b6f064ef293064f5722ea797

tech-stack:
  added: []
  patterns:
    - "One module-level exception tuple (PATTERN_ERRORS) caught by both the entity and the flow, so they agree on what counts as uncompilable"
    - "RED evidence for tests whose defect escapes as an uncaught loop exception: TAP rerun via a stdlib pytest reporter plugin (source kept in the record)"

key-files:
  created:
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-09-red.xml
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-09-red.tap
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-09-red-listener.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-09-red-setup.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-09-red-2.xml
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-09-red-2-validate.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-09-red-2-form.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-09-red-2-edit.json
  modified:
    - custom_components/xmltv_calendar/xmltv/filter.py
    - custom_components/xmltv_calendar/calendar.py
    - tests/test_reconfigure.py
    - tests/test_calendar.py
    - tests/test_subentry_flow.py
    - tests/xmltv/test_filter.py

key-decisions:
  - "02-09: PATTERN_ERRORS = (re.error, OverflowError, RecursionError) is the single definition of an uncompilable pattern; _build_spec and first_invalid_pattern both catch it (CR-01)"
  - "02-09: first_invalid_pattern keeps err.msg for re.error (unchanged Phase 1 text) and uses str(err) for OverflowError/RecursionError"
  - "02-09: pytest JUnit reports of a test that fails in call and errors at teardown are rejected by the RED classifier (tests= excludes double fails); such RED records use a TAP rerun from a stdlib pytest reporter plugin, with the JUnit report kept beside it"

patterns-established:
  - "Stored-data corruption tests: hand-edit subentry data with object.__setattr__(..., MappingProxyType(...)) and parametrize over every exception class re.compile raises"

requirements-completed: [FLT-11, FLT-07]

coverage:
  - id: D1
    description: "A stored pattern that re.compile rejects (syntax error, repeat overflow, deep nesting) keeps that calendar's previous matches on an edit, logs one WARNING, and sibling calendars still update"
    requirement: FLT-11
    verification:
      - kind: integration
        ref: "tests/test_reconfigure.py#test_corrupt_pattern_keeps_previous_matches[syntax-error|repeat-overflow|deep-nesting]"
        status: pass
    human_judgment: false
  - id: D2
    description: "A calendar subentry stored with such a pattern does not break platform setup: entry LOADED, that calendar exists and is empty, one WARNING, siblings show their matches"
    requirement: FLT-11
    verification:
      - kind: integration
        ref: "tests/test_calendar.py#test_invalid_stored_pattern_does_not_break_platform_setup[syntax-error|repeat-overflow|deep-nesting]"
        status: pass
    human_judgment: false
  - id: D3
    description: "first_invalid_pattern returns InvalidPattern for repeat-overflow lines and still accepts a{4294967294}"
    requirement: FLT-07
    verification:
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_first_invalid_pattern_reports_compile_overflow[repeat-count|repeat-range]"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_first_invalid_pattern_accepts_valid_input[a{4294967294}]"
        status: pass
    human_judgment: false
  - id: D4
    description: "The add form rejects repeat-overflow patterns in include, exclude and channel regex with invalid_regex and the offending line"
    requirement: FLT-07
    verification:
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_invalid_pattern_line_keeps_form_open[include-repeat-overflow|exclude-repeat-overflow|channel-regex-repeat-overflow]"
        status: pass
    human_judgment: false
  - id: D5
    description: "The edit form of a corrupt stored calendar shows invalid_regex on unchanged submit; saving a valid pattern repairs it in place (no download, no reload)"
    requirement: FLT-11
    verification:
      - kind: integration
        ref: "tests/test_reconfigure.py#test_edit_repairs_overflowing_stored_pattern"
        status: pass
    human_judgment: false

duration: 7min
completed: 2026-10-15
status: complete
---

# Phase 2 Plan 09: Every regex compile failure is contained (CR-01) Summary

**One shared `PATTERN_ERRORS = (re.error, OverflowError, RecursionError)` tuple, caught in `calendar._build_spec` and `first_invalid_pattern`. A stored `a{99999999999}` or 2,000-deep nesting no longer breaks calendar-platform setup or the update listener, and a typed one shows `invalid_regex` instead of "Unknown error".**

## Performance

- **Duration:** 7 min
- **Started:** 2026-10-15T15:10:57Z
- **Completed:** 2026-10-15T15:17:59Z
- **Tasks:** 2
- **Files modified:** 6 source/test files (+ 8 TDD evidence files)

## Accomplishments

- Closed 02-VERIFICATION.md `gaps[0]`. 02-01 truth 6 (T-02-01) now holds for every pattern `re.compile` rejects: a syntax error, a repeat count ≥ 2**32 - 1 (OverflowError) and nesting deep enough to hit the recursion limit (RecursionError). It holds in the update listener and at platform setup.
- CR-01 is fixed at both sites through one tuple, so the entity and the flow agree on what "does not compile" means. The CR-01 review disposition can move to `fixed`.
- FLT-07 now covers repeat-overflow patterns in the add and edit form. FLT-11 edits can repair a corrupt stored calendar in place.
- No change to config_flow.py, preview.py, `__init__.py`, the stored data contract (D-06) or the case-flag handling (D-08).

## TDD Cycle

### Task 1 (tracer): stored patterns, entity side

- **RED** (`07bb291`):
  - `test_corrupt_pattern_keeps_previous_matches` is now parametrized over syntax-error, repeat-overflow and deep-nesting.
  - New `test_invalid_stored_pattern_does_not_break_platform_setup` (same three ids).
  - Run result: 4 failed, 26 passed, 2 teardown errors. Exactly the repeat-overflow and deep-nesting ids failed.
  - Records: `02-09-red-listener.json` and `02-09-red-setup.json`, both RED_EVIDENCE_OK (target_test_failed).
  - *Semantic assessment, listener:* the target failed on the planned WARNING-count assertion (0 instead of 1). `_build_spec` caught only `re.error`, so the OverflowError aborted the listener task before any WARNING and before calendar B was applied. The phcc `hass` fixture re-raised it at teardown. The deep-nesting id fails the same way with RecursionError. The syntax-error id passed. No collection, import or fixture fault.
  - *Semantic assessment, setup:* the target failed on the planned `hass.states.get("calendar.a") is not None` assertion. `XmltvCalendarEntity.__init__` raised out of `_build_spec`, so the platform added no entity. The deep-nesting id fails the same way. The syntax-error id passed.
- **GREEN** (`b84cd95`):
  - filter.py: module constant `PATTERN_ERRORS`; the docstrings of `compile_patterns` and `FilterSpec.from_mapping` name it.
  - calendar.py: `_build_spec` uses `except PATTERN_ERRORS:` and its docstring names the three causes. The unused `import re` is removed.
  - Results: verify gives 40 passed, `-k test_corrupt_pattern_keeps_previous_matches` gives 3 passed, `-k test_invalid_stored_pattern_does_not_break_platform_setup` gives 3 passed.
- **Tracer gate:** `human_verify_mode` is end-of-phase and the verify step is automated-only. Re-running verify was green, so expansion went ahead with no checkpoint.
- **REFACTOR:** none needed.

### Task 2: typed and pre-filled patterns, flow side

- **RED** (`550d1a2`):
  - New `test_first_invalid_pattern_reports_compile_overflow` (repeat-count, repeat-range).
  - `"a{4294967294}"` added to the accepted inputs.
  - Three repeat-overflow ids added to `test_invalid_pattern_line_keeps_form_open`.
  - New `test_edit_repairs_overflowing_stored_pattern`.
  - Run result: 6 failed, 147 passed. The JUnit report is complete (153/153).
  - Records: `02-09-red-2-validate.json`, `02-09-red-2-form.json` and `02-09-red-2-edit.json`, all RED_EVIDENCE_OK (target_test_failed).
  - *Semantic assessment:* every failure is `OverflowError: the repetition number is too large` escaping `first_invalid_pattern` (filter.py:191, the re.compile call). In the flow tests it escapes through `async_step_basic` (config_flow.py:374) out of `async_configure`, which is the "Unknown error" path of CR-01.
  - The edit test got past setup, the empty `calendar.a` and the pre-filled include before failing at the unchanged submit (test_reconfigure.py:333).
  - The three original form ids and `a{4294967294}` passed. No collection, import or fixture fault.
- **GREEN** (`1ca6646`):
  - `first_invalid_pattern` uses `except PATTERN_ERRORS as err` in place of the single re.error clause. The message is `err.msg` for re.error and `str(err)` for the other two.
  - The check order is unchanged: line cap, length cap, compile, nested repetition.
  - filter.py is the only file this commit touches.
  - Results: verify gives 174 passed, `-k repeat-overflow` gives 3 passed, `-k compile_overflow` gives 2 passed.
- **REFACTOR:** none needed.

### Regression guards that passed before the change

- `test_corrupt_pattern_keeps_previous_matches[syntax-error]` and `test_invalid_stored_pattern_does_not_break_platform_setup[syntax-error]`: the `re.error` path already worked.
- `test_first_invalid_pattern_accepts_valid_input[a{4294967294}]`: the largest repeat count re.compile accepts. It shows the fix does not over-reject.
- The original `include`, `exclude` and `channel-regex` ids of `test_invalid_pattern_line_keeps_form_open`.

## Task Commits

1. **Task 1 RED:** `07bb291` test(02-09): add failing tests for uncompilable stored patterns at listener and setup
2. **Task 1 GREEN:** `b84cd95` feat(02-09): contain every re.compile failure of stored patterns in _build_spec
3. **Task 2 RED:** `550d1a2` test(02-09): add failing tests for repeat-overflow patterns in the calendar form
4. **Task 2 GREEN:** `1ca6646` feat(02-09): reject every uncompilable pattern line with invalid_regex in the flow

## Files Created/Modified

- `custom_components/xmltv_calendar/xmltv/filter.py`: `PATTERN_ERRORS`; `first_invalid_pattern` catches it; docstrings updated
- `custom_components/xmltv_calendar/calendar.py`: `_build_spec` catches `PATTERN_ERRORS`; `import re` removed
- `tests/test_reconfigure.py`: `import pytest` moved to runtime; `DEEP_NESTING`; listener test parametrized; new edit-repair test
- `tests/test_calendar.py`: `DEEP_NESTING`; new platform-setup test
- `tests/test_subentry_flow.py`: three repeat-overflow ids
- `tests/xmltv/test_filter.py`: `import re`; new overflow test; `a{4294967294}` accepted
- `tdd-evidence/02-09-red.{xml,tap}`, `02-09-red-listener.json`, `02-09-red-setup.json`, `02-09-red-2.xml`, `02-09-red-2-{validate,form,edit}.json`

## Decisions Made

- See key-decisions in the frontmatter. The main one: `PATTERN_ERRORS` is the single definition of "uncompilable", shared by the entity and the flow.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 1 RED records use a TAP rerun instead of the JUnit report**
- **Found during:** Task 1 RED, step 4
- **Issue:** The classifier returned `INVALID_RED (invalid_record: "Incomplete JUnit test suite")` for both records built from `02-09-red.xml`. The listener ids fail in call *and* error at teardown, because the phcc `hass` fixture re-raises the uncaught OverflowError/RecursionError of the listener task. For such a test, pytest's JUnit writer emits two `<testcase>` elements but subtracts the double fail from `tests=` (30 against 32 elements). The classifier treats that mismatch as incomplete, and no JUnit run that includes the RED listener ids can avoid it. Installing `pytest-tap` would be a package install, which is excluded from auto-fixing.
- **Fix:** Followed the tdd.md RED step 4 reporter-rerun route.
  - Reporter: a stdlib-only pytest plugin (about 30 lines). It writes one TAP test point per test item and marks a test "not ok" if any phase failed.
  - Rerun: the same two test files, written to `02-09-red.tap`.
  - Same outcome as the JUnit run: the same 4 tests fail and 26 pass.
  - Each record keeps the plugin source (`reporterSource`), the console failure summary and the path of the original JUnit report, along with a note on why it was rejected.
  - Both records now classify as RED_EVIDENCE_OK.
  - Task 2 had no teardown errors, so its records use the planned JUnit report unchanged.
- **Files modified:** tdd-evidence/02-09-red.tap, 02-09-red-listener.json, 02-09-red-setup.json
- **Commit:** `07bb291`

**Total deviations:** 1 auto-fixed (Rule 3, evidence tooling only).
- **Impact:** No change to production code or test scope. The JUnit report is still committed as planned.

### Other notes

- `ruff format` wrapped one long `async_configure` call in the new edit test. Formatting only.
- **Commits on `main`:** the gsd-tools protected-branch query flags `main`. The project uses `git.branching_strategy: none`, every earlier phase-02 plan committed to `main`, and the orchestrator dispatched this plan as a sequential executor on the main working tree.
- **REQUIREMENTS.md not touched:** `a6e95b0` reverted the premature `Complete` status for phase-02 requirements after the verifier found gaps. FLT-11 stays at "Gaps Found" until `/gsd-verify-work` re-verifies phase 02. FLT-07 was already Complete from Phase 1.

## Issues Encountered

None beyond the RED-evidence tooling deviation above.

## TDD Gate Compliance

- Task 1: `test(02-09)` `07bb291` precedes `feat(02-09)` `b84cd95`.
- Task 2: `test(02-09)` `550d1a2` precedes `feat(02-09)` `1ca6646`.
- No refactor commits (none needed).
- All five RED records classify as RED_EVIDENCE_OK.

## Verification

- `uv run pytest -q`: 517 passed, 1 skipped (the existing real-feed module skip), exit 0
- `uv run ruff check . && uv run ruff format --check .`: exit 0
- Spot check: `first_invalid_pattern('a{99999999999}')` prints `InvalidPattern(pattern='a{99999999999}', message='the repetition number is too large')`, with no traceback

## Next Phase Readiness

- All 9 phase-02 plans have SUMMARYs. Phase 02 is ready for re-verification (`/gsd-verify-work 02`) to close `gaps[0]` and set the CR-01 disposition to `fixed`.
- WR-01..WR-04 and IN-01..IN-06 stay open in 02-REVIEW-DISPOSITION.md (out of scope for this plan).

## Self-Check: PASSED

- All 6 modified source/test files and 8 evidence files exist on disk.
- Commits `07bb291`, `b84cd95`, `550d1a2` and `1ca6646` are ancestors of HEAD.
- The acceptance criteria for both tasks were re-run and pass.
