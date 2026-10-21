---
phase: 04-automation-extras-release
plan: 02
subsystem: automation
tags: [blueprint, calendar-trigger, notify, home-assistant, pytest]

requires:
  - phase: 03
    provides: "calendar.* entities with rendered summary ({channel}: {title}) and location = channel display name"
provides:
  - "blueprints/automation/xmltv_calendar/notify_before_programme.yaml: notify-before-programme automation blueprint (mode queued, max 20)"
  - "tests/test_blueprint.py: HA schema validation, raw contract and end-to-end use_blueprint tests"
affects: [04-08 README (import button, 15-minute trigger window note), release]

actuals:
  tokens: 5487
  tasks: 2
  commits: 3
plan_head_before: 2ad78c5c544c9a9ec3a5546f4f6611e864e32fb5
plan_head_after: 59d2a08e98e0d205b10a05157528d028fb7c6109

tech-stack:
  added: []
  patterns:
    - "Blueprint e2e test: copy the shipped YAML into hass.config.path('blueprints/automation/<dir>') and set up automation via use_blueprint"
    - "Calendar-trigger tests step one minute at a time and turn automations off at the end so the 900 s refresh timer does not linger"

key-files:
  created:
    - blueprints/automation/xmltv_calendar/notify_before_programme.yaml
    - tests/test_blueprint.py
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-02-red.json
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-02-red.xml
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-02-red-2.xml
  modified: []

key-decisions:
  - "Blueprint notify_entity stays optional (default []); the default action is an if-guard on notify_entity | count > 0, so users who replace the actions need no notify entity (RESEARCH Pitfall 8 option 2)"
  - "Blueprint description variable uses trigger.calendar_event.description | default(''), because CalendarEvent.as_dict() omits a missing description and the bare lookup logs a template warning on every run"

patterns-established:
  - "Blueprint inputs calendar_entity, lead_time, notify_entity, actions are a public contract (one-way): renaming breaks user automations on re-import"

requirements-completed: [AUT-05]

coverage:
  - id: D1
    description: "Shipped blueprint notifies once per matching programme a lead time before it starts; two programmes starting together each notify once (mode queued)"
    requirement: AUT-05
    verification:
      - kind: integration
        ref: "tests/test_blueprint.py#test_overlapping_programmes_notify_once_each"
        status: pass
    human_judgment: false
  - id: D2
    description: "Blueprint is accepted by Home Assistant's automation blueprint schema with the fixed inputs, min_version 2026.3.0 and main-branch source_url; raw contract (queued, calendar start trigger, filtered selector, negative lead-time default) is pinned"
    requirement: AUT-05
    verification:
      - kind: unit
        ref: "tests/test_blueprint.py#test_blueprint_passes_home_assistant_schema"
        status: pass
      - kind: unit
        ref: "tests/test_blueprint.py#test_blueprint_contract"
        status: pass
    human_judgment: false
  - id: D3
    description: "Custom actions get title, channel, start, end, start_time; lead time 0 fires at the start; no notify entity skips the default action without errors"
    requirement: AUT-05
    verification:
      - kind: integration
        ref: "tests/test_blueprint.py#test_custom_actions_get_programme_variables"
        status: pass
      - kind: integration
        ref: "tests/test_blueprint.py#test_lead_time_zero_fires_at_start"
        status: pass
      - kind: integration
        ref: "tests/test_blueprint.py#test_default_action_without_notify_entity_does_nothing"
        status: pass
    human_judgment: false
  - id: D4
    description: "Frontend duration field with a negative value (e.g. minus 2 minutes) reaches the trigger as a valid offset and a mobile app notification arrives on a real instance (RESEARCH A1)"
    requirement: AUT-05
    verification: []
    human_judgment: true
    rationale: "Task 2 human-check on ha-dev: the frontend duration selector and a real notify entity cannot be exercised by pytest"

duration: 41min
completed: 2026-10-21
status: complete
---

# Phase 4 Plan 02: Notify-Before-Programme Blueprint Summary

**Automation blueprint that runs actions once per matching XMLTV programme a negative lead time (default minus 10 min) before it starts, using the legacy calendar start trigger with mode queued. The default action is an if-guarded notify.send_message, and all of it is tested end to end through use_blueprint.**

## Performance

- **Duration:** 41 min wall clock (first RED run 08:36Z, then a checkpoint wait for the protected-branch decision; about 4 min of active work in this continuation)
- **Started:** 2026-10-21T08:36:27Z
- **Completed:** 2026-10-21T09:17:04Z
- **Tasks:** 2
- **Files modified:** 5 (2 source/test, 3 TDD evidence)

## Accomplishments

- `blueprints/automation/xmltv_calendar/notify_before_programme.yaml`:
  - Inputs `calendar_entity` (filtered to integration `xmltv_calendar`, domain `calendar`), `lead_time` (duration, `allow_negative: true`, default `{hours: 0, minutes: -10, seconds: 0}`), `notify_entity` (optional list), `actions` (action selector).
  - `mode: queued`, `max: 20`, `max_exceeded: warning`.
  - Variables: `title`, `channel`, `start`, `end`, `start_time`, `description`.
  - `homeassistant.min_version: 2026.3.0` and a main-branch `source_url`.
- Overlapping programmes (Formel 1 on Das Erste and heute on ZDF, both at 12:00 Berlin) each send exactly one notification at 11:50.
- Test module with 6 tests: HA schema, raw contract, custom-action variables, empty notify target, lead time 0, and overlap.

## Task Commits

1. **Task 1: Tracer: two programmes starting together each send one notification**
   - `a2a6f38` (test, RED)
   - `c5c0680` (feat, GREEN)
2. **Task 2: Blueprint contract: schema, custom actions, lead time, no default notify target**
   - `59d2a08` (test; the new tests were a regression suite and were already green)

**Plan metadata:** see the final docs(04-02) commit.

## TDD Record

- **Task 1 RED:** `test_overlapping_programmes_notify_once_each` failed in the test body on the planned blueprint-file-existence assertion. The integration had set up `calendar.test`, the JUnit report showed `errors=0` and 1 test collected, and the classifier returned `RED_EVIDENCE_OK (target_test_failed)` (`tdd-evidence/04-02-red.json`, re-classified in this continuation). Semantic assessment: a genuine missing-behaviour failure, with no collection, import or fixture fault.
- **Task 1 GREEN:** the blueprint was created. `uv run pytest tests/test_blueprint.py tests/test_calendar.py -q` gave 12 passed. Tracer gate: `human_verify_mode` is end-of-phase and the verify step is automated only, so the gate re-ran the verify command (pass) and the task expanded.
- **Task 2:** all five new tests were green against the Task 1 blueprint once the lead-time-0 test started off the 15-minute grid (see Deviations). They are a **regression suite**, so there is no RED record; the all-green run is in `tdd-evidence/04-02-red-2.xml`. Regression guards:
  - `test_blueprint_passes_home_assistant_schema`
  - `test_blueprint_contract`
  - `test_custom_actions_get_programme_variables`
  - `test_default_action_without_notify_entity_does_nothing`
  - `test_lead_time_zero_fires_at_start`
- **Mutation check:** removing the `if` guard from the default action makes `test_default_action_without_notify_entity_does_nothing` fail; the file was restored afterwards.
- **REFACTOR:** none needed.
- **Gate commits:** RED `a2a6f38`, then GREEN `c5c0680`, in that order.

## Files Created/Modified

- `blueprints/automation/xmltv_calendar/notify_before_programme.yaml`: the blueprint.
- `tests/test_blueprint.py`: schema, contract and end-to-end tests.
- `.planning/phases/04-automation-extras-release/tdd-evidence/04-02-red.json`, `04-02-red.xml`: Task 1 RED evidence.
- `.planning/phases/04-automation-extras-release/tdd-evidence/04-02-red-2.xml`: Task 2 all-green run.

## Decisions Made

- `notify_entity` is optional, and the default action is wrapped in `if: notify_entity | count > 0` (the planner's choice under D-27, RESEARCH Pitfall 8 option 2). An import that only replaces the actions works without notify entities.
- RESEARCH A2: the default action uses the blueprint variable `notify_entity` (`!input` inside another input's default is avoided). This worked as planned.
- RESEARCH A1 (dict form): the duration dict `{hours: 0, minutes: -10, seconds: 0}` is accepted by the legacy calendar trigger offset and fires 10 minutes early, as the e2e test shows. The frontend side is still open for the ha-dev human check.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Template warning for programmes without a description**
- **Found during:** Task 1 GREEN
- **Issue:** `CalendarEvent.as_dict()` omits `description` when there is none, so `{{ trigger.calendar_event.description }}` logged "Template variable warning: 'dict object' has no attribute 'description'" on every run.
- **Fix:** the variable is now `{{ trigger.calendar_event.description | default('') }}`.
- **Files modified:** blueprints/automation/xmltv_calendar/notify_before_programme.yaml
- **Verification:** the blueprint test run logs 0 template variable warnings.
- **Committed in:** c5c0680

**2. [Rule 3 - Blocking] Lingering calendar-trigger timer failed the test teardown**
- **Found during:** Task 1 GREEN
- **Issue:** the test body passed, but phcc's `verify_cleanup` failed on the calendar trigger's 900 s `async_track_time_interval` refresh timer.
- **Fix:** `_run_until` turns all automations off after stepping, as `tests/test_calendar.py::test_start_offset_and_end_triggers_fire` already does. The test assertions are unchanged.
- **Files modified:** tests/test_blueprint.py
- **Committed in:** c5c0680

**3. [Rule 1 - Test bug] Lead-time-0 test started on a trigger-window boundary**
- **Found during:** Task 2 RED
- **Issue:** with setup at 09:45Z, 10:00Z is a 15-minute window boundary. The refresh schedules the already-due alarm, and minute stepping only runs it on the next tick (10:01). This is the same harness artifact that `test_calendar.py` documents for its 11:30 end trigger. It is not a blueprint defect: in real HA, `call_at(now)` runs immediately.
- **Fix:** this test starts at 09:50Z, so 10:00 lies inside the first fetched window. A comment in the test explains why.
- **Files modified:** tests/test_blueprint.py
- **Committed in:** 59d2a08

---

**Total deviations:** 3 auto-fixed (2 Rule 1, 1 Rule 3)
**Impact on plan:** test-harness hygiene plus one log-noise fix in the blueprint. Inputs, trigger, mode and default action are as planned. No scope creep.

## Issues Encountered

- The previous executor stopped at a decision checkpoint because the pre-commit guard refused to commit on `main`. The user approved commits on `main` (`git.allow_default_branch_commits: true`), and this continuation committed from the RED step onwards.

## User Setup Required

None. The ha-dev human check for Task 2 (import the blueprint, set the lead time to minus 2 minutes, pick a mobile app notify entity) is left for end-of-phase verification.

## Next Phase Readiness

- The blueprint path and `source_url` are fixed for the README import button (04-08).
- The README should state that a programme which appears in the calendar less than 15 minutes before its trigger time may not notify (calendar trigger window, Pitfall 9).

## Self-Check: PASSED

- FOUND: blueprints/automation/xmltv_calendar/notify_before_programme.yaml
- FOUND: tests/test_blueprint.py
- FOUND: tdd-evidence/04-02-red.json, 04-02-red.xml, 04-02-red-2.xml
- FOUND commits: a2a6f38, c5c0680, 59d2a08 (ancestors of HEAD)
- Plan verification: `uv run pytest -q -m "not benchmark"` gave 849 passed, 1 skipped; `ruff check .` and `ruff format --check .` are clean.
- Acceptance: `mode: queued`, `allow_negative: true`, `integration: xmltv_calendar` and `min_version: 2026.3.0` are present; `grep -c '^mode: queued'` gives 1.
