---
phase: quick-261016-1ox
plan: 01
status: complete
subsystem: config-flow
tags: [config-subentry-flow, translations, review-disposition, tdd, WR-01, WR-02]

requires:
  - phase: 02-precise-filters-preview
    provides: CalendarSubentryFlow basic step and edit flow (async_update_and_abort), translations en/de
provides:
  - Basic form after a validation error suggests exactly the submitted input, so cleared fields stay cleared (WR-01)
  - Integration text for the reconfigure_successful abort in en and de (WR-02)
  - 02-REVIEW-DISPOSITION.md with WR-01/WR-02 fixed and WR-03/WR-04 deferred with reasons
affects: [phase-02 review disposition, /gsd-ship]

actuals:
  tasks: 2
  commits: 2
plan_head_before: 3cf1241
plan_head_after: 03c2f9b

key-files:
  created:
    - .planning/quick/261016-1ox-fix-review-findings-wr-01-and-wr-02-defe/tdd-evidence/1ox-red.xml
    - .planning/quick/261016-1ox-fix-review-findings-wr-01-and-wr-02-defe/tdd-evidence/1ox-red-wr01.json
    - .planning/quick/261016-1ox-fix-review-findings-wr-01-and-wr-02-defe/tdd-evidence/1ox-red-wr02.json
  modified:
    - custom_components/xmltv_calendar/config_flow.py
    - custom_components/xmltv_calendar/translations/en.json
    - custom_components/xmltv_calendar/translations/de.json
    - tests/test_reconfigure.py
    - .planning/phases/02-precise-filters-preview/02-REVIEW-DISPOSITION.md

key-decisions:
  - "WR-01: the basic form suggests user_input when re-shown after an error, pending only on first show (same rule the advanced step already follows)"
  - "WR-02: reconfigure_successful sits after source_not_loaded in both files, so the en/de key-order parity test holds"
  - "WR-03 deferred: over-rejection fails in the safe direction; WR-04 deferred: cosmetic, needs per-field placeholders"

requirements-completed: [FLT-11]

coverage:
  - id: D1
    description: "A field cleared in a submit that fails validation is not suggested again, and the next valid submit stores it empty"
    requirement: FLT-11
    verification:
      - kind: integration
        ref: "tests/test_reconfigure.py#test_cleared_field_stays_cleared_after_error"
        status: pass
    human_judgment: false
  - id: D2
    description: "Home Assistant serves the integration's own text for the edit flow's reconfigure_successful abort in en and de"
    requirement: FLT-11
    verification:
      - kind: integration
        ref: "tests/test_reconfigure.py#test_edit_flow_abort_reason_is_translated[en|de]"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-10-16
---

# Quick 261016-1ox: Fix review findings WR-01 and WR-02, defer WR-03 and WR-04 Summary

**A field cleared in the calendar form stays cleared after a validation error. "Edit calendar" -> Save now shows the integration's own success text in English and German. WR-03 and WR-04 are deferred with reasons.**

## Accomplishments

- `config_flow.py` `async_step_basic`: the form is re-shown with `user_input` after an error, and with the pending values only on first show. Before, `pending | user_input` brought a cleared field's old value back, and the next valid submit saved it again (WR-01).
- `translations/en.json` and `de.json`: `config_subentries.calendar.abort.reconfigure_successful` with the texts "The calendar was updated." and "Der Kalender wurde aktualisiert." (WR-02).
- `02-REVIEW-DISPOSITION.md`: WR-01 and WR-02 are `fixed` (03c2f9b). WR-03 and WR-04 are `deferred`, with the reason in the Source cell. The open count went from 13 to 9.

## Task Commits

1. **RED** `9a9c1c3` test(quick-261016-1ox): add failing tests for cleared fields after errors and the edit success text
2. **GREEN** `03c2f9b` fix(quick-261016-1ox): keep cleared calendar fields cleared after errors and translate the edit success

No REFACTOR commit was needed.

## TDD Gate Compliance

- RED run: `uv run pytest tests/test_reconfigure.py -q` exited 1 with 3 failed and 19 passed. Report: `tdd-evidence/1ox-red.xml`.
- `1ox-red-wr01.json`, target `test_cleared_field_stays_cleared_after_error`: RED_EVIDENCE_OK (target_test_failed).
  - The test failed on `assert 'tagesschau' is None` at test_reconfigure.py:592.
  - The cleared include came back from the pending values.
  - Setup and the `name_required` assertion passed.
- `1ox-red-wr02.json`, target `test_edit_flow_abort_reason_is_translated[en]`: RED_EVIDENCE_OK (target_test_failed).
  - The edit flow ran through to `reconfigure_successful`.
  - The test then failed on the served translation (`None`).
  - The `[de]` case failed the same way.
- The test commit comes before the fix commit.

## Verification

- `uv run pytest tests -q`: 560 passed, 1 skipped. The baseline was 557, plus 3 new tests.
- `uv run ruff check .` and `uv run ruff format --check .`: clean.
- hassfest (podman): Invalid integrations: 0.
- `test_de_has_same_keys_as_en`, `test_de_keeps_placeholders` and `test_home_assistant_serves_german_strings` pass with the new key.

## Deviations from Plan

None in code or tests.

Process note: the planner and executor subagents could not be spawned from this context, so this quick task ran inline. It still produced the same artifacts: PLAN, a RED record per target, atomic test and fix commits, this SUMMARY, the STATE row and a docs commit.

## Not addressed

- WR-03 and WR-04 (deferred, see the disposition file). IN-01..IN-03 and IN-05..IN-10 stay `open` as Info.
- The `clean_title` handling of `\r` in calendar summaries (render.py:88) is a residual note in 02-REVIEW.md, not a finding.
- The titles in 02-REVIEW.md still say "still open". That file is the reviewer's report; the next code-review run regenerates it from the disposition.

## Self-Check: PASSED

- Commits 9a9c1c3 and 03c2f9b are on main. The modified files and the evidence files exist.
