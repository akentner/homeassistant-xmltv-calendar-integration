---
phase: 04-automation-extras-release
plan: 09
subsystem: automation
tags: [home-assistant, matcher, disabled-entities, sensors, events, retention, lifecycle]
requires:
  - phase: 04-automation-extras-release
    provides: "04-01/04-04/04-05/04-06 sensors, event payload, persisted match records and retention rules"
provides:
  - "Runtime-owned CalendarMatcher per calendar subentry, initialized before platforms"
  - "Disabled-calendar sensors, new-match events and persisted ended-match retention"
  - "Matcher-backed diagnostics and teardown-safe executor completion"
affects: [04-10, 04-11, phase-04-uat]
tech-stack:
  added: []
  patterns:
    - "Entities present a runtime-owned matcher; disabling a presentation never stops automation"
    - "Activity, generation, runtime identity and membership guard executor results before mutation"
key-files:
  created:
    - custom_components/xmltv_calendar/matcher.py
    - tests/test_matcher_runtime.py
  modified:
    - custom_components/xmltv_calendar/__init__.py
    - custom_components/xmltv_calendar/data.py
    - custom_components/xmltv_calendar/calendar.py
    - custom_components/xmltv_calendar/sensor.py
    - custom_components/xmltv_calendar/diagnostics.py
key-decisions:
  - "Matching belongs to each runtime subentry, not an enabled calendar entity; registry identity supplies event entity_id"
  - "Successful unload captures and invalidates matchers before flushing; failed platform unload leaves matchers active"
  - "Runtime active flag also guards suspended subentry reconciliation after removal or unload"
requirements-completed: [AUT-03, AUT-06, EVT-07, EVT-08]
actuals:
  tokens: 24053
  tasks: 3
  commits: 6
plan_head_before: fed95a3ca42bc4044e7ff035949c451077106d87
plan_head_after: 5ee470040b50ace32cfe4163025859dbdfcfac7d
coverage:
  - id: D1
    description: "Disabled calendar still updates its next sensor, emits the exact event and persists seen UIDs"
    verification:
      - kind: integration
        ref: "tests/test_matcher_runtime.py#test_disabled_calendar_keeps_matching"
        status: pass
    human_judgment: false
  - id: D2
    description: "Sensors and diagnostics read matcher counts without presentation objects; disabled retention survives reload and re-enable"
    verification:
      - kind: integration
        ref: "tests/test_matcher_runtime.py#test_disabled_counts_without_calendar_objects"
        status: pass
      - kind: integration
        ref: "tests/test_matcher_runtime.py#test_disabled_edits_and_retained_reenable"
        status: pass
    human_judgment: false
  - id: D3
    description: "Stop/remove/reload discard held workers; failed unload remains functional; late additions and registry renames preserve one matcher"
    verification:
      - kind: integration
        ref: "tests/test_matcher_runtime.py#test_stop_captures_and_invalidates_worker"
        status: pass
      - kind: integration
        ref: "tests/test_matcher_runtime.py#test_blocked_worker_teardown"
        status: pass
      - kind: integration
        ref: "tests/test_matcher_runtime.py#test_removed_during_initial_filter_does_not_recreate_presentation"
        status: pass
      - kind: integration
        ref: "tests/test_matcher_runtime.py#test_failed_unload_keeps_runtime_live"
        status: pass
      - kind: integration
        ref: "tests/test_matcher_runtime.py#test_late_add_rename_and_entity_toggle_keep_one_matcher"
        status: pass
    human_judgment: false
  - id: D4
    description: "Real HA disabled-calendar walkthrough, restart persistence and product/prohibition judgments"
    verification: []
    human_judgment: true
    rationale: "All existing Phase 04 human items and flagged assumptions remain pending; pytest does not establish frontend or real restart behavior"
duration: 14 min
completed: 2026-10-23
status: complete
---

# Phase 4 Plan 09: Entity-Independent Matching Summary

**Calendar subentries now keep matching, updating sensors, announcing new programmes and retaining ended matches even when their calendar presentation is disabled.**

## Performance

- Started: 2026-10-23T12:58:47Z
- Completed: 2026-10-23T13:12:00Z (approximately 14 minutes)
- Tasks: 3; implementation/test files: 7; RED evidence: 3 JSON records and 3 unchanged JUnit reports.
- Actual tokens use realized task diff characters / 4, rounded up; commits measured from the persisted plan ledger before the documentation commit.

## Accomplishments

- `CalendarMatcher` owns filter/index, templates, feed and retained matches, seen-set updates, announcements, coordinator subscription and stop capture. Initialization precedes platform forwarding. The calendar is a view with compatibility delegations, not a second engine.
- Both sensors and diagnostics consume `runtime.matchers` directly. Strict-future lookup, next-start timer, recorder exclusions, privacy allow-lists, entity/device identifiers, event keys, UID and Store schema remain unchanged.
- Successful unload captures ended matches, detaches listeners and invalidates workers before flushing. Removal forgets only after invalidation. Generation, activity, runtime identity and subentry membership prevent late Store/event/signal mutations. Failed platform unload preserves active matching.

## Task Commits / TDD Gate Compliance

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 1: disabled-calendar tracer | `47214fc` | `425d005` | Not needed |
| 2: direct sensor/diagnostic consumers | `a50b57d` | `fb9176a` | Not needed |
| 3: teardown and reconciliation | `aa085d3` | `5ee4700` | Cleanup included in GREEN |

Every task's RED commit precedes its implementation. All three evidence records in `tdd-evidence/04-09-red-{1,2,3}.json` return `RED_EVIDENCE_OK (target_test_failed)` and include semantic assessments. Reports are unmodified JUnit XML from actual runs; freshness metadata records console-log creation time and report modification time.

1. `test_disabled_calendar_keeps_matching`: actual setup, registry disable and reload completed; sensor state was `unknown` instead of `2026-10-13T10:00:00+00:00`.
2. `test_disabled_counts_without_calendar_objects`: actual refresh completed without the disabled presentation facade; Last fetch reported `matches=None` instead of 3.
3. `test_stop_captures_and_invalidates_worker`: explicit worker-entry and stop-event gates completed; the released worker called Store.put once after stop instead of zero times. No sleeps supply ordering evidence; bounded gates are released in `finally`.

Task 1 verification passed twice (42 tests each), including the mandatory tracer feedback rerun before expansion. Additional lifecycle tests were regression backstops where the extraction already supplied the required guards.

## Verification

- Task 1: `uv run pytest tests/test_matcher_runtime.py::test_disabled_calendar_keeps_matching tests/test_new_match_event.py tests/test_sensor.py tests/test_retention.py -q` — **42 passed**, repeated successfully at tracer gate.
- Task 2: `uv run pytest tests/test_matcher_runtime.py tests/test_sensor.py tests/test_last_fetch_sensor.py tests/test_diagnostics.py tests/test_retention.py -q` — **53 passed** at Task 2 completion.
- Task 3: `uv run pytest tests/test_matcher_runtime.py tests/test_init.py tests/test_new_match_event.py tests/test_retention.py -q` — **45 passed**.
- Plan regression command: `uv run pytest tests/test_schedule_refresh.py tests/test_init.py tests/test_calendar.py tests/test_config_flow.py -q` — **72 passed**.
- Plan full non-benchmark suite: `uv run pytest -q -m "not benchmark"` — **988 passed, 4 skipped, 4 deselected**, confirmed with skip reasons.
- `uv run ruff check .` and `uv run ruff format --check .` — **clean**, 74 files formatted.
- No package installations, release tags, pushes or end-of-phase verifier/UAT execution.

## Decisions Made

- Registry lookup uses `(calendar, xmltv_calendar, subentry_id)`, including user-renamed disabled entities. No title-derived identity is fabricated. Runs starting before registry identity exists establish a silent baseline.
- HA stop now captures and invalidates, rather than merely capturing while allowing a pending worker to publish afterwards.
- A runtime-level active flag prevents an update listener suspended in its initial filter from creating presentations after successful teardown. The same continuation rechecks current runtime and subentry membership.

## Deviations from Plan

**1. [Rule 2 - Critical lifecycle guard] Task 3 also updates `data.py`.** The file is in the plan's overall scope but not Task 3's file list. Added `XmltvRuntimeData.active` so suspended reconciliation cannot resume into an unloaded runtime. The deterministic removal-during-initial-filter regression also exposed stale presentation creation (KeyError before the guard); it now passes. Commit: `5ee4700`.

**2. [Rule 1 - Test correction] An ended ZDF feed programme is legitimately captured after changing the disabled calendar's filter.** Corrected the Task 2 assertion to require removal of the old F1 retained programme rather than an entirely empty retained list. No production retention policy changed. Commit: `fb9176a`.

Temporary integration issues found during extraction (sensor setup preceding the calendar facade) were fixed with post-platform match readiness signaling before the tracer was committed. The temporary facade remains harmless compatibility for existing callers/tests; production sensors and diagnostics do not use it.

## Deferred Issues / Known Stubs

No introduced stubs, TODOs, skipped tests or new security surface outside the threat model. Empty initial indexes/maps are initialized from real coordinator/Store data, not placeholders.

Existing environment skips remain unchanged:
- One licensed real-feed acceptance case skips without `XMLTV_REAL_FEED` (prior user deferral).
- Three shellcheck cases skip because shellcheck is not installed; no installation authorized.

Recorded in phase `deferred-items.md` and `.planning/WINDOWS.md` (entries 3 and 4). Benchmark tests are intentionally deselected by the plan's command, not omitted task verification.

## Threat Mitigations

- T-04-24: held-worker removal/reload/source-removal and HA-stop tests prove no late old-Store puts or events; removed subentries never recreate records/presentations.
- T-04-25: idempotent start/stop, listener cleanup, repeated reload tests and unchanged 50-event burst-cap regression.
- T-04-26: exact event payload, recorder exclusions and existing no-secret sensor/diagnostic tests pass.
- T-04-27: disabled user-renamed registry identity is asserted through a live refresh.
- T-04-SC: no dependency changes or installs.

## Pending Human Verification / Next Readiness

Ready for dependent 04-10; its WR-01 configuration/data race and template-only scan optimization are **not** claimed closed. 04-11 remains separately owned. Shared requirement completion is gated on those sibling summaries.

Keep all eleven human entries in `04-VERIFICATION.md`, every EDGE-01..EDGE-17 assumption and prohibition judgment pending. Add this walkthrough to end-of-phase UAT: disable the calendar, reload, verify its next sensor and one new-match event using the disabled registry ID; disable sensors too, drop an ended match, restart HA, re-enable the calendar and check retained events and diagnostics under the current template. Real frontend rendering, final disk writes, blueprint behavior, translated frontend values, README accuracy, AUT-06 cancellation backstop and user-only release/HACS pickup still require their existing judgments.

## Self-Check: PASSED

All seven implementation/test files and six RED evidence files exist. All six task commits are ancestors of HEAD. No tracked-file deletions were introduced.
