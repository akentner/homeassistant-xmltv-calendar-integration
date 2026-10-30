---
phase: 02-precise-filters-preview
plan: 07
subsystem: config-flow
tags: [home-assistant, config-subentry-flow, selectors, translations, validation]

requires:
  - phase: 02-precise-filters-preview
    provides: "02-02 settings.py keys, with_defaults, normalize_time; 02-04 filter semantics; 02-05 basic/preview/save flow; 02-06 render.compile_template and TemplateError"
provides:
  - "CalendarSubentryFlow.async_step_advanced (step_id advanced) with field scopes, case, window, weekdays, duration range, title and description templates"
  - "Unstored basic-form checkbox 'advanced' backed by self._show_advanced (starts False in _load_pending; 02-08 replaces it with has_advanced)"
  - "Advanced validation errors fields_required, time_incomplete, time_equal, duration_order, invalid_template, unknown_placeholder with placeholder template_error"
  - "const.py CONF_* aliases for the ten Phase 2 keys, CONF_ADVANCED, MAX_DURATION_MINUTES"
  - "en.json step.advanced, selector.match_field, selector.weekday, new error texts"
  - "tests/conftest.py complete_calendar_flow(hass, entry, basic, advanced=None)"
affects: [02-08, phase-02-uat]

actuals:
  tokens: 6608
  tasks: 2
  commits: 4
plan_head_before: 02a02fc817c0b4bbd66dceb6fb49c03237056a78
plan_head_after: f01f00b210b248c58ddd4a6a6c20705b087cad29

tech-stack:
  added: []
  patterns:
    - "Advanced values are built fresh from the submit (_advanced_values); a missing key means cleared, never merged over old values"
    - "All advanced checks run in one pass (_advanced_errors); pending values are updated only when there are no errors"
    - "Help texts get placeholder names via description_placeholders (title_fields, description_fields, default_title), never as literal ICU braces"

key-files:
  created:
    - tests/test_advanced_flow.py
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-07-red.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-07-red-2-time.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-07-red-2-template.json
  modified:
    - custom_components/xmltv_calendar/config_flow.py
    - custom_components/xmltv_calendar/const.py
    - custom_components/xmltv_calendar/translations/en.json
    - tests/conftest.py

key-decisions:
  - "02-07: the title template is stored stripped; a blank title template stores DEFAULT_TITLE_TEMPLATE, a blank description template stores '' (default description)"
  - "02-07: a missing include_fields/exclude_fields key counts as an empty selection and is rejected with fields_required, like an explicit []"
  - "02-07: time_incomplete goes on the missing side (only From set -> error on To, and the other way round); time_equal and duration_order go on To and Maximum"
  - "02-07: after a validation error the advanced form suggests exactly the submitted input, so cleared fields stay cleared"
  - "02-07: unknown_placeholder text names both allowed sets through the title_fields and description_fields placeholders; with two bad templates template_error shows the title's offending text (setdefault, as planned)"

patterns-established:
  - "Clearable advanced fields: vol.Optional without default=, suggested values from pending (times as HH:MM:00)"
  - "Fixed-vocabulary multi-selects: SelectSelector LIST mode with translation_key and a top-level selector.<key>.options block in en.json"

requirements-completed: [FLT-05, FLT-06, FLT-08, FLT-09, FLT-10, EVT-03, EVT-04]

coverage:
  - id: D1
    description: "Advanced options checkbox leads to the advanced step; its values show in the preview and are stored in storage form (HH:MM times, int minutes, ordered lists), 'advanced' never stored"
    requirement: FLT-08
    verification:
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_advanced_options_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "Advanced input validation: fields_required, time_incomplete, time_equal, duration_order, invalid_template, unknown_placeholder with template_error and submitted values kept"
    requirement: EVT-03
    verification:
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_advanced_validation"
        status: pass
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_unknown_placeholder_names_the_offending_text"
        status: pass
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_both_templates_invalid_get_their_own_errors"
        status: pass
    human_judgment: false
  - id: D3
    description: "Clearing the stored time window on edit stores None (D-20)"
    requirement: FLT-09
    verification:
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_cleared_time_window_is_stored_as_none_on_edit"
        status: pass
    human_judgment: false
  - id: D4
    description: "Advanced step labels, help texts and selector option labels read well in the HA UI"
    verification:
      - kind: other
        ref: "podman run ghcr.io/home-assistant/hassfest (0 invalid integrations)"
        status: pass
    human_judgment: true
    rationale: "Wording and layout of the rendered form can only be judged in the HA frontend; covered by the 02-08 UAT walkthrough on ha-dev"

duration: 6min
completed: 2026-10-15
status: complete
---

# Phase 2 Plan 07: Advanced Options Step Summary

**"Advanced options" subentry step with field-scope, case, time-window, weekday, duration and template inputs, plus one-pass validation (fields_required, time_incomplete, time_equal, duration_order, invalid_template, unknown_placeholder) and translated selector labels.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-15T11:28:37Z
- **Completed:** 2026-10-15T11:34:44Z
- **Tasks:** 2
- **Files modified:** 5 source/test files (+5 TDD evidence files)

## Accomplishments

- The basic calendar form has an unstored "Advanced options" checkbox. When it is checked, `async_step_advanced` follows and then the preview (D-01, D-02).
- The advanced form covers all ten Phase 2 settings: include and exclude field lists, case-sensitive, From/To, weekdays, min/max duration, title template and description template. Every field is clearable. Values are built fresh from the submit, so clearing a field stores None or an empty value (D-20).
- Validation runs every check in one pass, and nothing reaches the preview or storage until all of them pass (T-02-14). Template errors use their own `template_error` placeholder, never the regex `pattern`/`error` placeholders (Pitfall 12).
- en.json has the advanced step texts, the new errors and the top-level `selector.match_field` / `selector.weekday` option labels. hassfest is clean.

## Task Commits

1. **Task 1 (tracer): advanced options in the flow, end to end**
   - RED `fc8819f` (test)
   - GREEN `77b2b1a` (feat)
2. **Task 2: validation of advanced input**
   - RED `ad9beb7` (test)
   - GREEN `f01f00b` (feat)

The plan metadata commit follows this SUMMARY.

## TDD Gate Compliance

- **Task 1 RED:** `test_advanced_options_end_to_end` failed on `assert 'advanced' in ['name', 'channels', 'channel_regex', 'include', 'exclude']`. The classifier returned RED_EVIDENCE_OK (target_test_failed) for `02-07-red.json`.
  - Semantic assessment: setup and flow init worked, and the target failed on the planned first assertion. This was not a fixture, import or collection fault.
- **Task 1 GREEN:** the verify command (advanced, subentry, reconfigure and tracer tests) passed 41 tests, with no "Lingering" output.
  - Tracer feedback gate: interactive run, end-of-phase mode, automated-only verify. I re-ran the verify, it passed, and work continued to Task 2.
- **Task 2 RED:** all 13 validation tests failed on `assert None == {...}`, because the flow went straight to the preview menu. Four regression guards passed as expected: the Task 1 end-to-end test, equal durations, a `{description}` description template, and the edit that clears the time window.
  - `02-07-red-2-time.json` (target `test_advanced_validation[time_equal]`): RED_EVIDENCE_OK.
  - `02-07-red-2-template.json` (target `test_unknown_placeholder_names_the_offending_text`): RED_EVIDENCE_OK.
- **Task 2 GREEN:** all 17 tests in `tests/test_advanced_flow.py` pass. The full suite gives 494 passed, 1 skipped.
- **REFACTOR:** none needed.

## Files Created/Modified

- `custom_components/xmltv_calendar/config_flow.py`
  - Advanced checkbox and `self._show_advanced`.
  - `async_step_advanced`.
  - Helpers `_advanced_schema`, `_advanced_values`, `_advanced_errors` and `_advanced_suggestions`.
  - Placeholder map `_ADVANCED_PLACEHOLDERS`.
- `custom_components/xmltv_calendar/const.py`: keys are now imported from `xmltv/settings.py`. Adds the ten CONF_* aliases, `CONF_ADVANCED` and `MAX_DURATION_MINUTES = 10080`.
- `custom_components/xmltv_calendar/translations/en.json`:
  - `step.basic` advanced field
  - `step.advanced`
  - six new error texts
  - `selector.match_field` and `selector.weekday`
- `tests/conftest.py`: `complete_calendar_flow` takes an optional `advanced` mapping.
- `tests/test_advanced_flow.py`: the end-to-end test, 10 parametrized validation cases, template placeholder tests, valid edge input, and clearing the time window on edit.

## Decisions Made

See the key-decisions list in the frontmatter. In short:

- The title template is stored stripped, and a blank one falls back to the default.
- A missing field-list key counts as an empty selection, so it is rejected.
- Each error sits on the field the user has to fix.
- After an error the form shows the input exactly as submitted.

## Deviations from Plan

None. The plan was executed as written.

## Issues Encountered

- `translation_key` was first passed positionally to the `_list_selector` helper. That did not match the acceptance grep `translation_key="weekday"`, so I made it keyword-only before the Task 1 commit.

## Notes for 02-08

- `_load_pending` sets `self._show_advanced = False`. Replace that one assignment with `has_advanced(self._pending)` for the D-03 pre-check.
- `async_step_back` still returns to the basic form. D-15 (Back keeps the advanced values) is already met, because the advanced values live in `self._pending` and the advanced form suggests them from there.
- If both templates are invalid, both error texts show the title template's offending text, because `template_error` is set with `setdefault` as the plan specified. A per-field placeholder would need a second placeholder name.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- Every Phase 2 setting can now be reached through the UI. 02-08 owns the D-03 pre-check, the Back behaviour with advanced values, form-level pattern safety and the UAT walkthrough on ha-dev.

## Self-Check: PASSED

- FOUND: tests/test_advanced_flow.py, config_flow.py, const.py, en.json, conftest.py, and the three RED records
- FOUND commits: fc8819f, 77b2b1a, ad9beb7, f01f00b

---
*Phase: 02-precise-filters-preview*
*Completed: 2026-10-15*
