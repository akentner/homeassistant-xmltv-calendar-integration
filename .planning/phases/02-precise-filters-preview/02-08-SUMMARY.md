---
phase: 02-precise-filters-preview
plan: 08
subsystem: config-flow
tags: [home-assistant, config-subentry, reconfigure, voluptuous, regex, translations]

requires:
  - phase: 02-precise-filters-preview
    provides: "02-02 has_advanced/with_defaults, 02-04 nested-repetition check, 02-05 in-place edit save, 02-07 advanced step and _show_advanced"
provides:
  - "D-03 pre-check: editing a calendar with non-default advanced values opens with 'Advanced options' checked"
  - "Edit/Back/form-safety regression tests (pre-check, unchecking keeps values, Back, case flag, nested repetition, translation placeholders)"
  - "Basic-step include/exclude validation uses the calendar's case flag (D-08 alignment)"
affects: [phase-02-uat, phase-03, phase-04]

actuals:
  tokens: 7600
  tasks: 2
  commits: 4
plan_head_before: c9adf19e452229c00f381cf65fdcdfd759945d79
plan_head_after: 729bf04231c13a4809ca0c02b4b8e8e536a92181

tech-stack:
  added: []
  patterns:
    - "Read a vol.Optional default in tests through key.default() on result['data_schema'].schema"
    - "Translation placeholder audit: regex {name} over en.json texts against the flow's description_placeholders"

key-files:
  created: []
  modified:
    - custom_components/xmltv_calendar/config_flow.py
    - tests/test_reconfigure.py
    - tests/test_advanced_flow.py
    - tests/test_subentry_flow.py

key-decisions:
  - "02-08: _show_advanced = has_advanced(self._pending) inside the run-once _load_pending, so Back and re-submits keep the user's own checkbox choice"
  - "02-08: Task 2 is a regression suite: all four cases passed before any change; the case-flag validation alignment is a refactor commit because re.compile acceptance of str patterns does not depend on IGNORECASE"

patterns-established:
  - "Edit-flow tests assert in-place application: unchanged aioclient_mock.call_count, entry.runtime_data is runtime, runtime.coordinator.data is epg, sibling entity identity"

requirements-completed: [FLT-06, FLT-10, FLT-11]

coverage:
  - id: D1
    description: "Editing a calendar with advanced settings pre-checks 'Advanced options', pre-fills the stored values, and the save applies in place (no download, no parse, no reload, sibling untouched)"
    requirement: FLT-11
    verification:
      - kind: integration
        ref: "tests/test_reconfigure.py#test_advanced_checkbox_prechecked_on_edit"
        status: pass
    human_judgment: false
  - id: D2
    description: "Unchecking 'Advanced options' in an edit skips the advanced step and keeps every stored advanced value"
    requirement: FLT-11
    verification:
      - kind: integration
        ref: "tests/test_reconfigure.py#test_unchecking_advanced_keeps_stored_values"
        status: pass
    human_judgment: false
  - id: D3
    description: "Back from the preview keeps the checkbox state and the entered advanced values"
    requirement: FLT-10
    verification:
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_back_keeps_advanced_values"
        status: pass
    human_judgment: false
  - id: D4
    description: "Case-sensitive toggle applies to include in the preview; nested-repetition patterns are refused in the form"
    requirement: FLT-06
    verification:
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_case_sensitive_in_flow"
        status: pass
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_nested_repetition_rejected_in_form"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every {name} placeholder in the advanced step texts and Phase 2 error texts is supplied by the flow"
    verification:
      - kind: unit
        ref: "tests/test_advanced_flow.py#test_translation_placeholders_are_provided"
        status: pass
    human_judgment: false
  - id: D6
    description: "Hands-on UI walkthrough on ha-dev (9 steps from the plan's human-check: add/advanced/preview/Back/edit/uncheck/nested repetition/no matches/logs)"
    verification: []
    human_judgment: true
    rationale: "Real frontend rendering (selectors, translated weekday names, help texts, menu buttons) and live log inspection are not covered by phcc tests; queued for the end-of-phase UAT batch (human_verify_mode end-of-phase)"

duration: 5min
completed: 2026-10-15
status: complete
---

# Phase 2 Plan 08: Advanced Options in Edits, Form Safety and Phase Gate Summary

**Editing a calendar with stored advanced settings now opens with "Advanced options" checked (has_advanced in the run-once _load_pending), backed by regression tests for unchecking, Back, the case flag, nested-repetition rejection and translation placeholders; full suite, benchmarks, Ruff and hassfest are green and the ha-dev UAT walkthrough is queued.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-10-15T11:36:53Z
- **Completed:** 2026-10-15T11:41:53Z
- **Tasks:** 2
- **Files modified:** 4 (plus TDD evidence files)

## Accomplishments

- D-03: `CalendarSubentryFlow._load_pending` sets `self._show_advanced = has_advanced(self._pending)`. New calendars and default-only (Phase 1) calendars still start unchecked. The value is set once per flow, so Back keeps the user's choice.
- End-to-end edit test of an advanced calendar: the box starts pre-checked, the stored values are pre-filled, weekdays change sat→tue, the preview shows 2 matches, Save gives `reconfigure_successful`, and the events update in place. The call count is unchanged, `entry.runtime_data is runtime`, `runtime.coordinator.data is epg`, and the sibling entity object is unchanged.
- Regression guards for D-03 (unchecking keeps stored values), D-15 (Back keeps the checkbox and the advanced values), D-08 (the case-sensitive include changes the preview), T-02-16 (nested repetition rejected with `invalid_regex`) and the translation placeholder audit.
- Basic-step validation now compiles include/exclude with the calendar's case flag. The channel regex still validates case-insensitively.

## TDD Record

### Task 1 (tracer)
- **RED:** `test_advanced_checkbox_prechecked_on_edit` failed on `assert _default(result, CONF_ADVANCED) is True` (`assert False is True`). Record: `tdd-evidence/02-08-red.json`. Classifier: `RED_EVIDENCE_OK (target_test_failed)`, 16 tests, 1 failure. Semantic assessment: the target ran and failed on its first planned assertion after setup and flow init succeeded, so this is not a fixture, import or collection fault. `test_unchecking_advanced_keeps_stored_values` already passed after 02-07 and is listed as a regression guard.
- **GREEN:** one-line swap in `_load_pending` plus the `has_advanced` import. Verify command: 59 passed, no "Lingering".
- **Tracer gate:** end-of-phase mode with automated-only verify. Re-ran it, passed, then went on to expansion.

### Task 2
- **RED:** none. All four new cases passed on the first run (`tdd-evidence/02-08-red-2.xml`, 47 passed), so no RED records were written. Per the plan, this task is a **regression suite**: the tests were committed as `test(02-08)` with no feat commit.
- **REFACTOR:** the basic-step `case_sensitive` alignment (`729bf04`). Behaviour is unchanged (checked: `(?-i:a)`, `(?i-i:a)`, `(?L)a` and the others compile identically with and without `re.IGNORECASE`). It is committed as refactor, not feat, because no test can observe it.

## Task Commits

1. **Task 1 RED:** `cdc207e` (test): failing test for the pre-checked advanced box on edit
2. **Task 1 GREEN:** `2ef5b8b` (feat): pre-check advanced options when editing an advanced calendar
3. **Task 2 tests:** `c3302fb` (test): regression tests for Back, case flag, nested repetition and placeholders
4. **Task 2 refactor:** `729bf04` (refactor): validate include/exclude with the calendar's case flag

## Files Created/Modified

- `custom_components/xmltv_calendar/config_flow.py`: `has_advanced` pre-check in `_load_pending`; case flag passed to `first_invalid_pattern` for include/exclude
- `tests/test_reconfigure.py`: `_default` / `_suggestions` helpers, `test_advanced_checkbox_prechecked_on_edit`, `test_unchecking_advanced_keeps_stored_values`
- `tests/test_advanced_flow.py`: `test_back_keeps_advanced_values`, `test_case_sensitive_in_flow` (2 cases), `test_translation_placeholders_are_provided`
- `tests/test_subentry_flow.py`: `test_nested_repetition_rejected_in_form`
- `.planning/phases/02-precise-filters-preview/tdd-evidence/02-08-red.{json,xml}`, `02-08-red-2.xml`

`translations/en.json` is unchanged: the placeholder audit found no mismatch.

## Phase Gate

| Check | Result |
|-------|--------|
| `uv run pytest -q -m "not benchmark"` | 501 passed, 1 skipped (pre-existing real-feed module skip), 4 deselected |
| `uv run pytest -q -m benchmark` | 4 passed, 1 skipped. 60 MB feed: parse 2.83 s, max loop gap 190.4 ms (limit 250 ms) |
| `uv run ruff check . && uv run ruff format --check .` | clean (48 files) |
| hassfest container | exit 0, `Invalid integrations: 0`, no ERROR lines |
| ha-dev deploy | `podman restart ha-dev` done. Port 18123 answers 200, and the log has no xmltv_calendar errors after the restart |

## UAT Walkthrough (pending human verification, end-of-phase batch)

On ha-dev at http://localhost:18123 (already restarted with this code), check each step and note the result:

1. On an XMLTV source, choose "Add calendar". The form shows Name, Channels, Channel regex, Include, Exclude and an "Advanced options" checkbox.
2. Check "Advanced options". The advanced step shows the field multi-selects (Title, Sub-title, Description, Category), the case-sensitive toggle, two time pickers, a weekday multi-select with day names, two duration boxes with "min", and both template fields. The help texts show the placeholder names with their braces.
3. Enter a window that crosses midnight (e.g. 22:00-02:00), one weekday, and a title template such as "{title} – {subtitle}". The preview lists matches as "<weekday> <dd.mm.> <HH:MM> · <channel> · <title>" in local time, with the templated titles. Switch HA's language to German and check that the weekday names read Mo..So.
4. Use Back. The form and the advanced step keep every entered value. Save. The calendar shows the same events as the preview.
5. On the calendar, choose "Edit calendar" (Reconfigure). "Advanced options" starts checked. Change the include pattern and save. The calendar updates within a few seconds, and `podman logs ha-dev` shows no new feed download for this source at that time.
6. In another edit, uncheck "Advanced options" and save. The window and template still apply.
7. Enter include "^(\w+\s?)+$". The form rejects it with a "nested repetition" message.
8. Enter a filter with no matches. The preview shows the "no matches" warning, and Save still works.
9. `podman logs ha-dev` shows no xmltv_calendar tracebacks and no "Detected blocking call" warning for xmltv_calendar during the walkthrough.

## Decisions Made

- `_show_advanced` is derived inside the run-once `_load_pending`, never again later in the flow, so a user's own checkbox choice survives Back (D-03, D-15).
- Task 2 counts as a regression suite. The D-08 validation alignment is a refactor commit, not a feat commit, because it is not observable.

## Deviations from Plan

None. The plan was executed as written. Task 2's "regression suite" outcome is a branch the plan itself provides for, so it is not a deviation.

## Issues Encountered

- `gsd_run` / `gsd-tools` are not on PATH in this shell. The classifier ran via `node ~/.claude/gsd-core/bin/gsd-tools.cjs`.
- The benchmark loop gap was 190.4 ms this run (earlier runs: 86-164 ms). It is still under the 250 ms limit, but it adds to the existing concern about flaky CI benchmarks in STATE.md.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- All 8 plans of Phase 2 have summaries. Next are the end-of-phase TDD review, verifier, code review, and the UAT walkthrough above.
- No blockers.

---
*Phase: 02-precise-filters-preview*
*Completed: 2026-10-15*

## Self-Check: PASSED

- Modified files and the RED record exist; commits cdc207e, 2ef5b8b, c3302fb, 729bf04 are ancestors of HEAD
- evaluation-scope resolves the plan commits on this branch
- Acceptance criteria re-run: verify suites green, RED_EVIDENCE_OK, `has_advanced(` in config_flow.py, in-place assertions present, Ruff clean, benchmarks and hassfest pass
