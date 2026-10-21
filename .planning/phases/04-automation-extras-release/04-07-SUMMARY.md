---
phase: 04-automation-extras-release
plan: 07
subsystem: config-flow
tags: [home-assistant, config-subentry, number-selector, retention, translations]

requires:
  - phase: 04-automation-extras-release
    provides: "04-06: KEY_RETENTION_DAYS / DEFAULT_RETENTION_DAYS / MAX_RETENTION_DAYS, ADVANCED_DEFAULTS ending with retention_days, with_defaults clamping, has_advanced, async_apply_subentry re-reading retention in place"
provides:
  - "const.py: CONF_RETENTION_DAYS = KEY_RETENTION_DAYS (in __all__)"
  - "config_flow.py: _retention_selector() (NumberSelector 0..MAX_RETENTION_DAYS, step 1, box, no unit); retention_days as the last field of _advanced_schema; _advanced_values stores int(value) or DEFAULT_RETENTION_DAYS when cleared"
  - "translations en/de: config_subentries.calendar.step.advanced.data.retention_days and data_description.retention_days"
affects: [04-08 README retention docs, UAT on ha-dev (German form check)]

actuals:
  tokens: 4185
  tasks: 2
  commits: 3
plan_head_before: a8c127c0e2ad9277127556c99b9772f00b42ac19
plan_head_after: b1b2a552a22e6697f68937250bd2241aba6aa35d

tech-stack:
  added: []
  patterns:
    - "Bounded integer advanced field: NumberSelector bounds reject out-of-range input in the flow (InvalidData), with_defaults clamps whatever is stored"

key-files:
  created:
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-07-red.json
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-07-red.xml
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-07-red-2.xml
  modified:
    - custom_components/xmltv_calendar/const.py
    - custom_components/xmltv_calendar/config_flow.py
    - custom_components/xmltv_calendar/translations/en.json
    - custom_components/xmltv_calendar/translations/de.json
    - tests/test_advanced_flow.py
    - tests/test_retention.py

key-decisions:
  - "Keep past matches (days) is the last field of the calendar's advanced step, a NumberSelector 0..7 in box mode without unit_of_measurement (the unit is in the translated label); a cleared field stores the default 1, never 0 (D-15)"
  - "No change to _advanced_suggestions: it already skips only None, so a stored 0 is suggested on edit (test_edit_suggests_retention_zero)"

patterns-established:
  - "RED stub for a new CONF_ constant: the alias lands in the test commit so the module imports and the RED run fails on the behaviour assertion, not ImportError (as 04-06 did with MAX_RETAINED)"

requirements-completed: [EVT-07, CFG-04]

coverage:
  - id: D1
    description: "A user sets Keep past matches (days) in a calendar's advanced options; the edit is stored as an int and applies in place (no reload, no download), so a dropped race stays beyond one day with retention 3"
    requirement: EVT-07
    verification:
      - kind: integration
        ref: "tests/test_retention.py#test_retention_set_in_the_ui_applies_in_place"
        status: pass
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_retention_days_in_advanced_step"
        status: pass
    human_judgment: false
  - id: D2
    description: "The field is bounded 0..7 (0 and 7 accepted, -1 and 8 rejected), a cleared field stores 1, a selector float is stored as an int"
    requirement: EVT-07
    verification:
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_retention_boundaries_accepted"
        status: pass
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_retention_out_of_range_rejected"
        status: pass
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_cleared_retention_stores_default"
        status: pass
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_fraction_is_stored_as_int"
        status: pass
    human_judgment: false
  - id: D3
    description: "Editing a calendar pre-fills its stored retention (including 0) and pre-checks Advanced options only when the retention differs from 1"
    requirement: EVT-07
    verification:
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_edit_prefills_retention_and_checks_advanced"
        status: pass
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_edit_suggests_retention_zero"
        status: pass
    human_judgment: false
  - id: D4
    description: "Label and help text exist in English and German with identical digit literals"
    requirement: CFG-04
    verification:
      - kind: unit
        ref: "tests/test_translations.py"
        status: pass
      - kind: other
        ref: "podman run --rm -v $PWD:/github/workspace:ro,Z ghcr.io/home-assistant/hassfest (0 invalid integrations)"
        status: pass
    human_judgment: false
  - id: D5
    description: "On ha-dev in German: editing a calendar with Erweiterte Optionen ticked shows Vergangene Treffer behalten (Tage) with its help text, accepts 0 to 7 and keeps the saved value on the next edit"
    requirement: CFG-04
    verification: []
    human_judgment: true
    rationale: "Task 2 <human-check>: the real frontend rendering of the translated label, help text and box-mode number field is not exercised by the phcc tests"

duration: 4min
completed: 2026-10-21
status: complete
---

# Phase 4 Plan 07: Retention Field in the Calendar Form Summary

**Each calendar's advanced options now include "Keep past matches (days)" / "Vergangene Treffer behalten (Tage)": a 0..7 number box stored as the int `retention_days`, where a cleared field means the default 1. Edits apply in place through the 04-06 update listener, with no reload or download. Editing a calendar pre-fills the stored value and pre-checks Advanced when it isn't 1.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-21T10:12:58Z
- **Completed:** 2026-10-21T10:16:59Z
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files modified:** 6 (2 integration, 2 translations, 2 tests), plus 3 evidence files

## Accomplishments

- `CONF_RETENTION_DAYS` alias in `const.py`.
- `_retention_selector()` and `retention_days` as the last field of the advanced step.
- `_advanced_values` stores `int(value)`, or `DEFAULT_RETENTION_DAYS` when the field is cleared.
- English and German label and help text, with the digits 0, 7 and 1 in both.
- End-to-end proof: setting retention 3 in the edit flow keeps a dropped race 24.5 h after it ended, with the entry still loaded and no new request.
- Edge-case regression suite: bounds, clearing, float to int, edit pre-fill including 0, and the state of the Advanced checkbox.

## Task Commits

1. **Task 1 (tracer): retention 3 set in the UI applies in place.** RED `afe94d6`, GREEN `a5ab97b`
2. **Task 2: edge cases.** Regression tests `b1b2a55` (green before any change, so no feat commit)

Tracer feedback gate after Task 1 (interactive mode, `end-of-phase`, automated-only verify): I re-ran the Task 1 verify command (93 passed) before starting Task 2.

## RED Evidence

- `04-07-red.json`: target `test_retention_days_in_advanced_step`, verdict `RED_EVIDENCE_OK (target_test_failed)`, report `04-07-red.xml` (35 tests, 2 failures, 0 errors).
  - **Semantic assessment:** the flow reached the advanced step, and the assertion `'retention_days' in _schema_keys(...)` failed because the field did not exist yet. `test_retention_set_in_the_ui_applies_in_place` failed on the same gap end to end: `InvalidData: Schema validation failed at 'retention_days'`. All 33 existing tests in both files passed.
- **Task 2:** every new test passed before any code change. Report `04-07-red-2.xml`: 31 tests, 0 failures. Per the plan this task is a regression suite, so there is no RED record.
  - **Mutation check** (temporarily changed `config_flow.py`, then restored it): widening the max to 10 failed `test_retention_out_of_range_rejected[8]`, and storing 0 for a cleared field failed `test_cleared_retention_stores_default`.
  - Removing the `int()` call alone does not fail `test_fraction_is_stored_as_int`, because `_calendar_data()` → `with_defaults` also converts to an int. The test still guards the stored type.

## TDD Gate Compliance

- **Task 1:** the `test(04-07)` commit `afe94d6` comes before the `feat(04-07)` commit `a5ab97b`.
- **Task 2:** has only a `test(04-07)` commit (`b1b2a55`). The TDD gate never tripped, because no implementation step was needed after the tests were green before any change.
- No REFACTOR commit.

## Files Created/Modified

- `custom_components/xmltv_calendar/const.py`: `CONF_RETENTION_DAYS` alias and its `__all__` entry
- `custom_components/xmltv_calendar/config_flow.py`: `_retention_selector`, schema field, value conversion
- `custom_components/xmltv_calendar/translations/en.json`, `de.json`: advanced step label and help text
- `tests/test_advanced_flow.py`: `_save_new` helper and 7 retention tests (10 cases); the `"retention_days"` literal is replaced by `CONF_RETENTION_DAYS`
- `tests/test_retention.py`: `test_retention_set_in_the_ui_applies_in_place`

## Decisions Made

- **Cleared field.** It stores the default 1 rather than 0 (D-15). Users must type 0 explicitly to keep nothing.
- **No unit on the selector.** HA's `unit_of_measurement` is untranslated, so "days" / "Tage" is in the label (RESEARCH Pattern 5).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `CONF_RETENTION_DAYS` alias in the RED commit**
- **Found during:** Task 1 RED
- **Issue:** Both test modules import `CONF_RETENTION_DAYS`. Without the constant, collection would fail with ImportError, which classifies as INVALID_RED.
- **Fix:** I added the plain `const.py` alias in the RED commit, with no form field. GREEN added the field.
- **Files modified:** `custom_components/xmltv_calendar/const.py`
- **Commit:** `afe94d6`

**2. [Rule 2 - Coverage] Extra test `test_edit_suggests_retention_zero`**
- **Found during:** Task 2
- **Issue:** The plan named 0 (falsy but not None) as a suggestion risk, but no listed test covered a stored 0 on edit.
- **Fix:** Added a test that a stored 0 is suggested and pre-checks Advanced. It passed against the existing `_advanced_suggestions`.
- **Commit:** `b1b2a55`

**3. [Process] Commits on `main`**
- `git.allow_default_branch_commits: true` applies. The orchestrator dispatched this executor sequentially on the main working tree.

**Total deviations:** 2 auto-fixed (1 blocking, 1 coverage), 1 process note. **Impact:** none on scope.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. There is no new surface beyond the plan's threat model:
- T-04-20 is mitigated by the selector bounds (`test_retention_out_of_range_rejected`) and the 04-06 `with_defaults` clamp.
- T-04-21 is accepted.
- T-04-SC: no packages were added.

## Verification

- Task 1 verify (`tests/test_retention.py test_advanced_flow.py test_reconfigure.py test_subentry_flow.py test_translations.py`): 93 passed
- `uv run pytest -q -m "not benchmark"`: 977 passed, 1 skipped, 4 deselected
- `uv run ruff check . && uv run ruff format --check .`: clean, 72 files formatted
- hassfest (podman): Invalid integrations 0
- Acceptance checks:
  - `grep -c retention_days` prints 2 for both `en.json` and `de.json`
  - `CONF_RETENTION_DAYS` is in `config_flow.py`
  - `def test_edit_prefills_retention_and_checks_advanced` exists
  - `04-07-red.json` classifies as `RED_EVIDENCE_OK`
- **Human check (deferred to end of phase, D5).** On ha-dev with German as the UI language:
  1. Edit a calendar and tick "Erweiterte Optionen".
  2. Check the field "Vergangene Treffer behalten (Tage)" and its help text.
  3. Check that it accepts 0 to 7.
  4. Edit the calendar again; the saved value should still be there.

## User Setup Required

None.

## Next Phase Readiness

- 04-08 README: document the field ("Keep past matches (days)", 0..7, default 1, a cleared field means 1) together with the retention behaviour from 04-06.

---
*Phase: 04-automation-extras-release*
*Completed: 2026-10-21*

## Self-Check: PASSED
