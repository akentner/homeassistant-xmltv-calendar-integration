---
phase: 02-precise-filters-preview
plan: 05
subsystem: config-flow
tags: [home-assistant, config-subentry, reconfigure, flow, tdd]
status: complete

requires:
  - phase: 02-precise-filters-preview
    provides: "02-01 in-place update listener (entity.async_apply_subentry, device rename); 02-02 with_defaults() stored contract; 02-03 basic -> preview -> save subentry flow"
provides:
  - "Calendar edit flow (async_step_reconfigure alias of the basic step) ending in async_update_and_abort"
  - "Every save (add or edit) stores the full 14-key with_defaults() set (D-06)"
  - "Stored channel IDs missing from the feed stay selectable in the form"
  - "'Edit calendar' initiate_flow label"
affects: [02-06, 02-07, 02-08, advanced-options-step]

actuals:
  tokens: 4500
  tasks: 2
  commits: 4
plan_head_before: 821392f3aead768c5593cbb57ade6aafcb1a9624
plan_head_after: 861843cf1ff4af0cc61725ec84b9cae3e674184c

tech-stack:
  added: []
  patterns:
    - "One shared step for add and edit: async_step_user = async_step_reconfigure = async_step_basic, self.source tells them apart"
    - "Lazy _load_pending() loads defaults (add) or the stored subentry plus title (edit) exactly once per flow, so Back keeps edits"
    - "Form submit updates pending values instead of replacing them, so keys outside the form (Phase 2 advanced keys) survive an edit"

key-files:
  created:
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-05-red.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-05-red.xml
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-05-red-2-missing.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-05-red-2.xml
  modified:
    - custom_components/xmltv_calendar/config_flow.py
    - custom_components/xmltv_calendar/translations/en.json
    - tests/test_reconfigure.py
    - tests/test_subentry_flow.py

key-decisions:
  - "Calendar edits save via async_update_and_abort only; the entry's update listener applies them in place, no reload and no re-download (D-04, Pitfall 1)"
  - "The basic form submit merges into the pending values rather than replacing them, so stored keys the form does not show survive an edit"
  - "Channel selector options = sorted(feed IDs | stored IDs) so a calendar whose channel left the feed can be saved unchanged"

patterns-established:
  - "Edit-flow test helper _edit(hass, entry, subentry_id, basic) in tests/test_reconfigure.py: form -> preview -> save -> reconfigure_successful"

requirements-completed: [FLT-11]

coverage:
  - id: D1
    description: "Users edit a calendar from its menu (pre-filled form, preview, save) and the change applies instantly with no download, parse or reload; sibling calendars untouched"
    requirement: FLT-11
    verification:
      - kind: integration
        ref: "tests/test_reconfigure.py#test_reconfigure_flow_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every save stores the full with_defaults() key set; a Phase 1 calendar edited unchanged keeps identical events"
    requirement: FLT-11
    verification:
      - kind: integration
        ref: "tests/test_reconfigure.py#test_phase1_calendar_edit_keeps_events"
        status: pass
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_include_calendar_via_form_end_to_end"
        status: pass
    human_judgment: false
  - id: D3
    description: "Edit flow edge cases: missing channel selectable, rename keeps entity_id, empty filters show all, unloaded source aborts, Back keeps edits"
    requirement: FLT-11
    verification:
      - kind: integration
        ref: "tests/test_reconfigure.py#test_missing_channel_stays_selectable"
        status: pass
      - kind: integration
        ref: "tests/test_reconfigure.py#test_rename_via_edit_flow"
        status: pass
      - kind: integration
        ref: "tests/test_reconfigure.py#test_edit_to_empty_filters_shows_all"
        status: pass
      - kind: integration
        ref: "tests/test_reconfigure.py#test_edit_on_unloaded_source_aborts"
        status: pass
      - kind: integration
        ref: "tests/test_reconfigure.py#test_back_in_edit_flow_keeps_edits"
        status: pass
    human_judgment: false
  - id: D4
    description: "'Edit calendar' appears in the HA UI calendar subentry menu"
    requirement: FLT-11
    human_judgment: true
    rationale: "supports_reconfigure is asserted in tests; the rendered frontend label is only visible in the HA UI"

duration: 4 min
completed: 2026-10-15
---

# Phase 2 Plan 05: Calendar Edit Flow Summary

**Calendars can now be edited from the HA UI. `async_step_reconfigure` reuses the basic -> preview -> save path, pre-filled from the stored subentry, and saves through `async_update_and_abort`, so the 02-01 in-place listener applies the change without re-downloading, re-parsing, reloading or touching sibling calendars. Every save now writes the full 14-key stored contract.**

## Performance

- **Duration:** about 4 min
- **Started:** 2026-10-15T11:12:26Z
- **Completed:** 2026-10-15T11:15:41Z
- **Tasks:** 2
- **Files modified:** 8 (4 source/test, 4 TDD evidence)

## Accomplishments

- `CalendarSubentryFlow` handles both add and edit:
  - `_load_pending()` returns `with_defaults({})` for a new calendar. For an edit it returns `with_defaults(stored data)` plus the subentry title as the name. It loads only once per flow.
  - `_calendar_data()` is used by both the preview and save.
  - `async_step_reconfigure = async_step_basic`.
  - `async_step_save` branches: `async_create_entry` when the source is user, `async_update_and_abort` otherwise.
- `en.json` gains `config_subentries.calendar.initiate_flow.reconfigure: "Edit calendar"`.
- Stored channel IDs that are no longer in the feed stay in the selector options (sorted union with the feed IDs).
- Seven new end-to-end edit-flow tests. The add-flow test now asserts the full `with_defaults()` key set.

## Task Commits

1. **Task 1 (tracer): edit a calendar's include pattern, source untouched**
   - RED `fed8e95` (test)
   - GREEN `009fc40` (feat)
2. **Task 2: Phase 1 calendars, full-key saves, missing channels, rename, unloaded source**
   - RED `4276529` (test)
   - GREEN `861843c` (feat)

No refactor commits; nothing needed cleanup.

## TDD Gate Compliance

- **Task 1 RED:** `test_reconfigure_flow_end_to_end` failed on the planned first assertion, `supports_reconfigure` (`assert False is True`), because the flow class had no reconfigure step. Classifier: `RED_EVIDENCE_OK (target_test_failed)`, record `tdd-evidence/02-05-red.json`.
  - Semantic assessment: the target executed and failed for the intended reason. The 7 existing 02-01 listener tests in the same file passed. No collection or fixture fault.
- **Task 1 GREEN:** the verify command `pytest tests/test_reconfigure.py tests/test_tracer.py` gave 9 passed.
  - Expected intermediate failure: `test_include_calendar_via_form_end_to_end`, with its old 4-key assertion. Task 2 fixed it.
  - Tracer feedback gate (end-of-phase mode, automated-only verify): the verify re-run passed, so expansion went ahead.
- **Task 2 RED:** `test_missing_channel_stays_selectable` failed on the channel-options assertion: options were `['daserste.de', 'zdf.de']`, without `gone.de`. Classifier: `RED_EVIDENCE_OK (target_test_failed)`, record `tdd-evidence/02-05-red-2-missing.json`.
  - No fullkeys RED record exists. Task 1 already routes the add flow through `_calendar_data`, so the updated full-key assertion passed at RED time.
  - Regression guards that passed after Task 1:
    - `test_include_calendar_via_form_end_to_end` (behaviour test_new_calendar_stores_full_key_set)
    - `test_phase1_calendar_edit_keeps_events`
    - `test_rename_via_edit_flow`
    - `test_edit_to_empty_filters_shows_all`
    - `test_edit_on_unloaded_source_aborts`
    - `test_back_in_edit_flow_keeps_edits`
- **Task 2 GREEN:** `uv run pytest -q -m "not benchmark"` gave 430 passed, 1 skipped.

## Verification

- `uv run pytest -q -m "not benchmark"`: 430 passed, 1 skipped, 4 deselected. No failures, no lingering timers.
- `uv run ruff check . && uv run ruff format --check .`: all checks passed, 46 files already formatted.
- `podman run --rm -v "$PWD":/github/workspace:ro,Z ghcr.io/home-assistant/hassfest`: "Invalid integrations: 0".
- Acceptance greps:
  - `async_step_reconfigure = async_step_basic` is present.
  - `reload_and_abort` occurs 0 times.
  - `with_defaults(` is present.
  - The `initiate_flow.reconfigure` translation exists.

## Files Created/Modified

- `custom_components/xmltv_calendar/config_flow.py`: adds `_load_pending`, `_calendar_data`, the reconfigure alias, save branching and the stored-channel options.
- `custom_components/xmltv_calendar/translations/en.json`: the "Edit calendar" label.
- `tests/test_reconfigure.py`: helpers `_suggested`, `_channel_options` and `_edit`, plus seven edit-flow tests.
- `tests/test_subentry_flow.py`: the add flow asserts the full `with_defaults()` key set.

## Decisions Made

- An edit merges the form values into the pending values instead of replacing them. Stored Phase 2 keys that the basic form does not show (field sets, time window, templates) therefore survive an edit. A replace would silently reset them to defaults.
- `async_update_and_abort` is the only save path for edits. The comment avoids the literal name of the reload variant so the acceptance grep stays at 0.

## Deviations from Plan

None. The plan was executed as written.

The plan's Task 2 step 2 ("`_load_pending` runs only once per flow") was already met by the Task 1 implementation, so `test_back_in_edit_flow_keeps_edits` serves as a regression guard rather than a RED target. The plan explicitly allowed for this.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

The edit flow uses the shared basic step, so the upcoming advanced-options step automatically applies to both add and edit. Pending values already carry all 14 keys. Ready for 02-06.

## Self-Check: PASSED

- All created and modified files exist on disk.
- Commits fed8e95, 009fc40, 4276529 and 861843c are ancestors of HEAD.
- No stubs found in the modified files.
