---
phase: 04-automation-extras-release
plan: 11
subsystem: i18n
tags: [home-assistant, translations, diagnostics, tdd]
requires:
  - phase: 04-automation-extras-release
    provides: Last-fetch sensor and code-derived translation collector from 04-05 and 04-08
provides:
  - Six English and German failure_reason state translations served by HA
  - Vocabulary-derived completeness and per-leaf mutation regression coverage
affects: [phase-04-uat, CFG-04, AUT-06]
tech-stack:
  added: []
  patterns: [Code-derived attribute-state requirements with in-memory omission tests]
key-files:
  created:
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-11-red.json
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-11-red.xml
  modified:
    - tests/test_translations.py
    - custom_components/xmltv_calendar/translations/en.json
    - custom_components/xmltv_calendar/translations/de.json
key-decisions:
  - Bind failure_reason directly to coordinator.FAILURE_REASONS in the existing ATTEMPT_VOCABULARIES collector.
requirements-completed: [CFG-04, AUT-06]
actuals:
  tokens: 3737
  tasks: 2
  commits: 3
plan_head_before: fb52845b6ad0c1c18ed73937bf7e10c2fc600819
plan_head_after: 5b986024dc760fc2881d61fd6a67955f25d73dfb
coverage:
  - id: D1
    description: All failure reasons have nonempty en/de state translations, served in German by HA.
    requirement: CFG-04
    verification:
      - kind: integration
        ref: tests/test_translations.py#test_german_ui_is_served_for_every_required_key
        status: pass
      - kind: unit
        ref: tests/test_translations.py#test_failure_reason_vocabulary_is_required
        status: pass
    human_judgment: false
  - id: D2
    description: Missing leaves, paired omissions and synthetic vocabulary additions are detected.
    verification:
      - kind: unit
        ref: uv run pytest tests/test_translations.py tests/test_last_fetch_sensor.py -q
        status: pass
    human_judgment: false
  - id: D3
    description: English/German frontend attribute-state rendering on ha-dev
    verification: []
    human_judgment: true
    rationale: HA string loading does not prove frontend rendering; walkthrough remains pending.
duration: 2min
completed: 2026-10-23
status: complete
---

# Phase 04 Plan 11: Localized Failure Reasons Summary

**Six bilingual diagnostic failure states now load through HA, with code-derived completeness that catches omissions even when locale parity holds.**

## Performance

- Started: 2026-10-23T13:15:50Z
- Completed: 2026-10-23T13:17:28Z
- Tasks: 2; changed deliverable/evidence files: 5
- Actual tokens: realized git diff characters / 4, rounded to nearest integer; commits measured before this metadata commit.

## Accomplishments

- Added the six requested English/German state strings without changing attribute names, machine keys, sensor behavior or production Python.
- Extended the existing collector rather than maintaining a parallel reason inventory. Both state maps must exactly match FAILURE_REASONS.
- Added 12 locale/reason omission cases, six paired-omission cases and a synthetic-vocabulary case. Mutations affect only in-memory copies; monkeypatch restores the mapping automatically.
- Existing HA loader check now verifies all German failure-state leaves differ from English.

## Task Commits

1. Task 1 RED: `56a478e` — require localized failure reason states.
2. Task 1 GREEN: `798e3d7` — translate diagnostic failure reasons in English and German.
3. Task 2: `5b98602` — detect missing and newly introduced failure reasons.

## TDD Gate Compliance

- RED: `uv run pytest tests/test_translations.py -q --junitxml=.planning/phases/04-automation-extras-release/tdd-evidence/04-11-red.xml` exited 1: 3 failed, 6 passed. Target `test_failure_reason_vocabulary_is_required` failed at the planned missing-leaf assertion with all six English reason states missing. Existing vocabulary and German serving checks also failed on those states.
- Classifier returned `RED_EVIDENCE_OK`, format JUnit, errors=0; persisted unchanged XML and JSON record accompany the RED commit.
- Semantic assessment: the target executed its non-vacuity check and failed on the intended missing translation leaves, not imports, collection or fixtures.
- GREEN: 9 translation tests passed. Re-ran the tracer end-to-end before Task 2: 9 passed. No blocking-human gate or task-local human check was present.
- REFACTOR: no separate cleanup needed; existing flattened-key collector and HA serving checks were reused.
- Task 2 is test-only regression/mutation coverage and passed against the GREEN collector; no artificial failing implementation was introduced. The runtime behavior-adding predicate returned false for the plan's JSON/test-only scope, so the implementation runtime gate is exempt; plan-level RED/GREEN sequence is present.

## Verification

- Final scoped verification: `uv run pytest tests/test_translations.py tests/test_last_fetch_sensor.py -q` — **40 passed**, including sensor machine-key/None, diagnostic/default-disabled and privacy regression checks.
- `uv run ruff check tests/test_translations.py` — passed.
- `uv run ruff format --check tests/test_translations.py` — passed.
- `git diff --check` — passed.
- No package installs, new trust boundaries, runtime changes, release tags or pushes. No goal-blocking stubs found; existing placeholder-validation terminology is not stub code.

## Decisions Made

Use the existing ATTEMPT_VOCABULARIES mapping bound directly to coordinator.FAILURE_REASONS. Synthetic-vocabulary coverage patches that mapping, not the already-bound coordinator constant.

## Deviations from Plan

None in scope or behavior. Ruff's parameter-value list convention was corrected during Task 2 verification before committing.

State maintenance: the SDK advanced the numeric pointer to 11 despite plan 10 remaining incomplete; corrected the displayed next-incomplete pointer to 10. `state.update-progress` declined an unscoped recalculation, leaving its existing progress bar unchanged; disk counts and ROADMAP correctly show 10/11 Phase 04 plans complete.

## Pending Human Checks / Next Readiness

On ha-dev enable Last fetch, cause a known fetch failure and compare English/German attribute-state display. This is pending, not accepted by pytest. All existing 04-VERIFICATION.md UI/UAT/release/prohibition judgments remain pending. No phase verification was executed. 04-09 work is preserved; 04-10 remains unexecuted by this plan. The user alone owns release tagging and pushing (D-29).

## Self-Check: PASSED

All five deliverable/evidence files exist and all three task commits are ancestors of HEAD.
