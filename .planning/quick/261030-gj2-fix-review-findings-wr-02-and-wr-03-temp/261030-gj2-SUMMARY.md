---
phase: quick-261030-gj2
plan: 01
quick_id: 261030-gj2
subsystem: config-flow, template-engine
tags: [review-fix, templates, config-flow, jinja]
requires: []
provides:
  - "Advanced-unticked edits validate stored templates before the preview (WR-02)"
  - "Retired single-brace names are rejected in the literal text of mixed Jinja templates (WR-03)"
affects: [custom_components/xmltv_calendar/config_flow.py, custom_components/xmltv_calendar/xmltv/template_engine.py]
tech-stack:
  added: []
  patterns: ["literal-text check over parsed TemplateData nodes", "shared _template_errors helper"]
key-files:
  created: []
  modified:
    - custom_components/xmltv_calendar/config_flow.py
    - custom_components/xmltv_calendar/xmltv/template_engine.py
    - tests/test_reconfigure.py
    - tests/xmltv/test_template_engine.py
    - tests/xmltv/test_render.py
decisions:
  - "D-08 detection condition narrowed: a retired name in literal text outside Jinja tags is detected even when tags are present; closed set of seven names, error key and fallback unchanged"
  - "Template errors found on the basic step reuse the existing reason keys and the advanced form; no translation key added"
metrics:
  duration: ~12 min
  completed: 2026-10-30
status: complete
commits: 2
plan_head_before: 2f479b62c417333101d560b023ae7dc96e15c831
plan_head_after: 56794e595cfa8992da4ad5ba13f1cc10f366ba50
actuals:
  tokens: 3850
  tasks: 2
  commits: 2
---

# Quick 261030-gj2: Fix review findings WR-02 and WR-03 Summary

Stored unusable templates can no longer be saved by unticking "Advanced options" (the advanced form opens with the template's error), and `{channel} - {{ title }}` style mixed templates are now rejected as `legacy_placeholder` by checking the parsed tree's literal text.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | WR-02 validate stored templates when Advanced is unticked | e2d7b84 | config_flow.py, tests/test_reconfigure.py |
| 2 | WR-03 detect retired placeholders next to Jinja | 56794e5 | template_engine.py, tests/xmltv/test_template_engine.py, tests/xmltv/test_render.py |

### Task 1 (WR-02)
- `_template_errors(values)` extracted from `_advanced_errors` (advanced step behaves as before).
- `_advanced_step_form(suggestions, errors, placeholders)` extracted from `async_step_advanced`.
- `async_step_basic` now ends in `_preview_or_templates()`: it validates the pending templates and, on errors, sets `_show_advanced = True` and shows the advanced form; otherwise it goes to the preview.
- Tests: `test_unchecking_advanced_cannot_save_a_stored_legacy_template` (full path to a corrected save) and a parametrized test for a legacy description template and an unknown title filter.

### Task 2 (WR-03)
- `_check_legacy(tree)` searches `nodes.TemplateData` nodes only; called in `compile_template` after `_check_tree` and before `_check_variables`, so hostile-template reasons are unchanged.
- Tests: the review's reproduction, new detection cases, the two flipped cases moved from the old "pure legacy" test, no-false-positive cases (comments, string literals, filter arguments), expression-brace cases, `validate_template` reason and a load-time fallback with exactly one WARNING.

## TDD evidence
RED runs were done before each fix and classified `RED_EVIDENCE_OK`; records are in `tdd-evidence/gj2-red-wr02.{json,xml}` and `gj2-red-wr03.{json,xml}` (left uncommitted per orchestrator instruction; the plan had asked to stage them in the task commits).

## Deviations from Plan

- **Evidence files not staged:** the plan said to commit the tdd-evidence files with each task; the orchestrator's constraints say not to commit them, so the constraint was followed. They remain untracked in the quick directory.
- Otherwise none; plan executed as written. No translation, README, manifest or ROADMAP change.

## Verification
- `uv run --frozen pytest -q`: 1283 passed, 1 skipped (baseline 1268 passed, 1 skipped).
- `uv run --frozen ruff check .`: all checks passed; `ruff format --check .`: 80 files already formatted.
- Task-level suites green (129 and 230 tests).

## Known Stubs
None.

## Threat Flags
None.

## Self-Check: PASSED
- Commits e2d7b84 and 56794e5 exist on main.
- Modified files present; evidence records present.
