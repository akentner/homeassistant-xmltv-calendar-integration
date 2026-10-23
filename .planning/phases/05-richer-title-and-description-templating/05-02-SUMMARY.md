---
phase: 05-richer-title-and-description-templating
plan: 02
subsystem: templating
tags: [jinja2, config-flow, translations, validation, tdd, home-assistant]

requires:
  - phase: 05-richer-title-and-description-templating
    provides: "Sandboxed engine, TemplateError reasons, TEMPLATE_ERROR_REASONS, validate_template, flow wiring of err.reason and err.detail"
provides:
  - "Translated form errors (en, de) for all six template reasons, guarded by TEMPLATE_ERROR_REASONS"
  - "Advanced step placeholders reduced to variables and default_title; title_fields and description_fields removed"
  - "validate_template trial render of a full and a sparse synthetic programme (template_runtime_error)"
  - "Edit flow refuses to re-save a stored legacy single-brace template"
affects: [05-03 text filters (new filter names reach the flow through the same reasons), 05-05 README (help texts point at it)]

actuals:
  tokens: 30000
  tasks: 2
  commits: 4
plan_head_before: fa3787605d0015c10120842a355ef2afbe394bd1
plan_head_after: 4b507b1ea908d30301ceb1758901713cd7fdfb71

tech-stack:
  added: []
  patterns:
    - "Translation completeness derives required error keys from the engine's reason tuple, not a hand list"
    - "Flow validation renders synthetic samples only, so exception details never carry feed content"

key-files:
  created:
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-02-red.json
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-02-red.xml
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-02-red-2.json
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-02-red-2b.json
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-02-red-2.xml
  modified:
    - custom_components/xmltv_calendar/xmltv/render.py
    - custom_components/xmltv_calendar/config_flow.py
    - custom_components/xmltv_calendar/translations/en.json
    - custom_components/xmltv_calendar/translations/de.json
    - tests/test_translations.py
    - tests/test_advanced_flow.py
    - tests/test_reconfigure.py
    - tests/xmltv/test_render.py

key-decisions:
  - "Help texts show the default title and the variable list through placeholder values, never a literal double brace (ICU rules)"
  - "Trial render uses the strict compiled template with no fallback; the runtime fallback in EventTemplates is untouched"
  - "Runtime error detail is exception type, colon, message, cut to 200 characters"

patterns-established:
  - "Adding a reason to TEMPLATE_ERROR_REASONS without en.json and de.json text now fails test_every_flow_key_is_translated"

requirements-completed: [EVT-03, EVT-04]

coverage:
  - id: D1
    description: "Every engine error reason has an English and German form error text; the completeness test iterates TEMPLATE_ERROR_REASONS"
    requirement: EVT-03
    verification:
      - kind: unit
        ref: "tests/test_translations.py#test_every_flow_key_is_translated"
        status: pass
      - kind: unit
        ref: "tests/test_translations.py#test_german_ui_is_served_for_every_required_key"
        status: pass
      - kind: unit
        ref: "tests/test_translations.py#test_template_error_reasons_guard_is_not_vacuous"
        status: pass
    human_judgment: false
  - id: D2
    description: "Legacy single-brace input is rejected with legacy_placeholder, naming the first retired placeholder, with variables and default_title placeholders"
    requirement: EVT-03
    verification:
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_legacy_template_is_rejected_with_the_placeholder_named"
        status: pass
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_every_compile_time_reason_reaches_the_form"
        status: pass
    human_judgment: false
  - id: D3
    description: "A template that compiles but raises on a synthetic programme is rejected with template_runtime_error naming the exception; empty optional fields never fail"
    requirement: EVT-04
    verification:
      - kind: unit
        ref: "tests/xmltv/test_render.py#test_validate_template_rejects_a_zero_division_at_render"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_render.py#test_empty_optional_fields_never_fail_the_trial_render"
        status: pass
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_runtime_failure_on_a_sample_programme_is_rejected"
        status: pass
    human_judgment: false
  - id: D4
    description: "A stored legacy title template opens pre-checked in the edit flow, cannot be saved unchanged, and a rewritten Jinja template saves and renders"
    requirement: EVT-03
    verification:
      - kind: integration
        ref: "tests/test_reconfigure.py#test_stored_legacy_template_cannot_be_saved_again"
        status: pass
    human_judgment: false
  - id: D5
    description: "German error texts read naturally in the live form for loop, unknown filter, typo, legacy syntax and runtime error"
    requirement: EVT-03
    verification:
      - kind: manual
        ref: "Task 2 human-check on ha-dev with German UI"
        status: not_run
    human_judgment: true
    rationale: "Wording quality and the form rendering of the placeholders need a person in the real UI; automated tests only prove keys, placeholder names and literals"

duration: 7min
completed: 2026-10-23
status: complete
---

# Phase 5 Plan 02: Translated Template Errors and Trial Render Summary

**Six template error reasons translated in English and German behind a TEMPLATE_ERROR_REASONS-driven completeness guard, plus a two-sample trial render in validate_template that rejects templates which compile but fail at render time**

## Performance

- **Duration:** 7 min
- **Completed:** 2026-10-23
- **Tasks:** 2 (both TDD, tracer then auto)
- **Files modified:** 8 source and test files, 5 RED evidence files

## Accomplishments

- `en.json` and `de.json` carry `unknown_placeholder` (reworded), `unsupported_syntax`, `unknown_filter`, `legacy_placeholder` and `template_runtime_error` under the calendar subentry errors, same key order in both files, no literal double brace.
- `_ADVANCED_PLACEHOLDERS` is now exactly `variables` and `default_title`; `title_fields`, `description_fields` and the helper constant are gone. The title and description help texts are short and point at the README.
- `tests/test_translations.py` takes its required template error keys from `render.TEMPLATE_ERROR_REASONS`, plus a non-vacuity test (six entries, named).
- `validate_template` renders `SAMPLE_FULL` and `SAMPLE_SPARSE` (synthetic, UTC) after a successful compile; any exception becomes `template_runtime_error` with `Type: message` cut to 200 characters.
- Edit flow: a stored `{title} ({channel})` pre-checks Advanced, is rejected unchanged with `legacy_placeholder` (stored data unchanged), and a rewritten Jinja template saves and renders.

## Task Commits

1. **Task 1: Tracer, legacy input shows a translated error**
   - RED: `945607f` (test), `RED_EVIDENCE_OK`
   - GREEN: `623b711` (feat)
2. **Task 2: Trial render**
   - RED: `bf939ea` (test), `RED_EVIDENCE_OK` for two targets
   - GREEN: `4b507b1` (feat)

**Plan metadata:** committed after this file (docs: complete plan)

## TDD Gate Compliance

- **RED (Task 1):** target `tests/test_translations.py::test_every_flow_key_is_translated`, record `tdd-evidence/05-02-red.json`, classifier `RED_EVIDENCE_OK` (`target_test_failed`). Semantic assessment: it failed on the planned assertion, four keys (unsupported_syntax, unknown_filter, legacy_placeholder, template_runtime_error) missing from `en.json`; the served-German test failed for the same reason and the legacy flow test on the missing `variables` placeholder. The parametrized compile-time reason tests already passed because the 05-01 engine emits those reasons; no import or fixture fault.
- **RED (Task 2):** targets `test_validate_template_rejects_a_zero_division_at_render` (`05-02-red-2.json`) and `test_runtime_failure_on_a_sample_programme_is_rejected` (`05-02-red-2b.json`), both `RED_EVIDENCE_OK`. Six tests failed (DID NOT RAISE / errors None) because `validate_template` only compiled; the legacy edit-flow test passed in RED as the plan predicted (its legacy half exists from 05-01).
- **GREEN:** the verify commands pass; full suite 1174 passed, 1 skipped, 4 deselected.
- **REFACTOR:** not needed.
- Gate commits found: `test(05-02)` precedes `feat(05-02)` for both tasks.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Dropped the `noqa: BLE001` on the trial-render except clause**
- **Found during:** Task 2 GREEN, ruff run
- **Issue:** The plan asked for a `noqa: BLE001` comment, but the clause re-raises as `TemplateError`, so BLE001 does not fire and RUF100 (unused noqa) failed the lint.
- **Fix:** Kept the explanatory comment, removed the directive.
- **Files modified:** `custom_components/xmltv_calendar/xmltv/render.py`
- **Commit:** `4b507b1`

**2. [Test design] The 200-character cut is tested with a monkeypatched template**
- **Found during:** Task 2 RED
- **Issue:** No allowed filter produces a long exception message from a literal, so a real template cannot exercise the cut.
- **Fix:** The test swaps `render.compile_template` for a stub whose `render` raises a 500-character `ValueError`.
- **Files modified:** `tests/xmltv/test_render.py`
- **Commit:** `bf939ea`

Otherwise the plan was executed as written.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. T-05-07 is mitigated by the trial render (flow and unit tests), T-05-08 holds because the samples are synthetic and the detail is capped, T-05-09 holds because the compile whitelist and length caps bound the render cost.

## User Setup Required

The Task 2 human check (German UI on ha-dev: for loop, unknown filter, typo variable, single-brace syntax and `{{ 1 / 0 }}` each show their own German text with the offending part named, nothing saved until valid) was not run by the executor. It is deferred to the end-of-phase human verification (`human_verify_mode: end-of-phase`).

## Next Phase Readiness

- Ready for 05-03: new filters register in the engine and reach the flow through the existing reasons; any new reason must be added to `TEMPLATE_ERROR_REASONS` and both translation files or the completeness test fails.
- `start` and `end` still render in the feed offset at call sites until 05-04 (unchanged from 05-01).

## Self-Check: PASSED

- Files exist: `05-02-red.json`, `05-02-red-2.json`, `05-02-red-2b.json`, modified source files.
- Commits found: `945607f`, `623b711`, `bf939ea`, `4b507b1`.
- Acceptance greps: `legacy_placeholder` 1 per translation file, `title_fields|description_fields` 0 in all three files, `{{` 0 in both translation files, `SAMPLE_SPARSE` present, `template_runtime_error` 4 in `test_advanced_flow.py`, purity test passes, ruff clean.

---
*Phase: 05-richer-title-and-description-templating*
*Completed: 2026-10-23*
