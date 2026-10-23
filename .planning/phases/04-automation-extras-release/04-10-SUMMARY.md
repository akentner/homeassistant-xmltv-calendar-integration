---
phase: 04-automation-extras-release
plan: 10
subsystem: automation
tags: [home-assistant, concurrency, matcher, events, retention, tdd]
requires:
  - phase: 04-automation-extras-release
    provides: "04-09 runtime-owned matcher, registry identity and lifecycle invalidation"
provides:
  - "Ordered silent configuration baselines and retained rechecks before newer DATA announcements"
  - "Latest-edit convergence and template-only rendering without full-feed scans"
  - "Deterministic executor-gated configuration/data and teardown regression tests"
affects: [phase-04-verification, phase-04-uat]
tech-stack:
  added: []
  patterns:
    - "Async refilter lock serializes commits; immutable revision snapshots preserve config-time feed baselines"
    - "Template equality is independent of normalized FilterSpec and retention equality"
key-files:
  created:
    - tests/test_matcher_races.py
  modified:
    - custom_components/xmltv_calendar/matcher.py
key-decisions:
  - "Pending configuration owns its config-time feed snapshot; newer DATA is diffed only after that baseline commits silently"
  - "Superseded DATA and stale configuration workers do not persist, signal or announce; only the latest accepted configuration revision clears its obligation"
  - "Template-only edits signal consumers without changing the configuration revision, preserving concurrent legitimate feed events"
requirements-completed: [EVT-08, EVT-07, AUT-03]
actuals:
  tokens: 15698
  tasks: 2
  commits: 7
plan_head_before: d5d4b6f385ee486b05ebf05afa992b18cf917961
plan_head_after: b79dacb762cfcaeff7c64eacdfc3a62367843262
coverage:
  - id: D1
    description: "Blocked CONFIG followed by DATA silently baselines edit-only matches, rejects retained candidates and announces only genuine feed additions"
    requirement: EVT-08
    verification:
      - kind: integration
        ref: "tests/test_matcher_races.py#test_data_during_config_preserves_baseline_and_retention"
        status: pass
    human_judgment: false
  - id: D2
    description: "Latest edits converge, retention 0/7 applies in place and held workers cannot write after removal/unload"
    requirement: EVT-07
    verification:
      - kind: integration
        ref: "tests/test_matcher_races.py#test_newer_edit_keeps_pending_config_semantics"
        status: pass
      - kind: integration
        ref: "tests/test_matcher_races.py#test_retention_only_edits_zero_and_seven"
        status: pass
      - kind: integration
        ref: "tests/test_matcher_races.py#test_held_config_teardown_does_not_commit"
        status: pass
    human_judgment: false
  - id: D3
    description: "Template edits update current, retained and next-match text without scanning or losing a concurrent DATA announcement"
    requirement: AUT-03
    verification:
      - kind: integration
        ref: "tests/test_matcher_races.py#test_template_only_edit_does_not_scan"
        status: pass
      - kind: integration
        ref: "tests/test_matcher_races.py#test_template_edit_during_data_preserves_new_event"
        status: pass
    human_judgment: false
  - id: D4
    description: "No-edit-notification prohibition judgment, live HA walkthroughs and release acceptance"
    verification: []
    human_judgment: true
    rationale: "Deterministic regressions support the prohibition but do not establish human acceptance; all existing Phase 04 human checks remain pending"
duration: 12 min
completed: 2026-10-23
status: complete
---

# Phase 4 Plan 10: Configuration/Data Ordering Summary

**Configuration-time feed snapshots now establish silent baselines and recheck raw retention before newer feed programmes can announce; template-only edits render immediately without a scan.**

## Performance

- Started: 2026-10-23T13:44:58Z; completed: 2026-10-23T13:56:00Z (approximately 12 minutes).
- Tasks: 2; production/test files: 2; evidence: four JSON records and four unchanged JUnit reports.
- Actual tokens: ceiling of 62,789 realized task-diff characters / 4, including committed evidence. Seven commits measured from the persisted plan HEAD ledger, before documentation commits.

## Accomplishments

- An asyncio lock serializes semantic commits. Accepted filter/retention edits capture immutable spec, feed, raw recheck candidates, retention and timezone inputs before awaiting. Revision checks discard stale workers without clearing a newer obligation. The edit's silent baseline commits before queued newer DATA; genuine new programmes still announce once.
- Enabled and registry-disabled widening tests reproduce the verifier's exact race. Pre-existing ZDF programmes enter seen silently; only the new Das Erste Rennen programme fires with the exact published payload. Narrowing drops both stored raw retention and rejected ended previous-feed candidates. Repetition and reload are silent; a later Sprint announces once.
- CONFIG→DATA, DATA→CONFIG, CONFIG→CONFIG→DATA and CONFIG→DATA→CONFIG converge to the latest accepted filter, templates and retention. DATA already present when a filter edit is accepted is part of that edit's silent baseline. Later widening cannot resurrect the raw retained programme dropped by completed narrowing.
- Template-only and normalized-equivalent edits make zero full-feed calls, update airing/current calendar text, retained event text and next-match sensor text, and preserve UIDs and seen records. Invalid edits keep the valid spec/matches, update templates and record the bad diff base once. A template edit during held DATA preserves exactly one genuine event with the current template and unchanged keys.
- Held CONFIG removal/unload and existing held-DATA stop/remove/reload lifecycle tests forbid late Store writes, signals and events. Superseded DATA remains coalesced; initially invalid filters finish empty configuration obligations rather than leaving them pending forever.

## Task Commits / TDD Gate Compliance

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 1: blocked CONFIG tracer | `5a6702b` | `814d59f` | Commit-path extraction included in GREEN; no separate cleanup needed |
| 2: latest edits/template-only | `363dfc4`, `c65cf18` | `876ba9b` | No additional change needed |
| 2: invalid-initial empty-obligation backstop | `7f62ff9` | `b79dacb` | No additional change needed |

All implementation changes follow committed failing behavioral tests. Four persisted records under `tdd-evidence/04-10-red-{1,2,3,4}.json` passed `check tdd-red-evidence` with `RED_EVIDENCE_OK (target_test_failed)`. Each embeds the unchanged actual JUnit XML, command, real exit code 1, target, expected/actual, freshness metadata and semantic assessment:

1. `test_data_during_config_preserves_baseline_and_retention[widen-enabled]`: actual worker-entry/feed-refresh/release ordering completed; exact event payload assertion found two spurious ZDF programmes before Rennen instead of only Rennen.
2. `test_template_only_edit_does_not_scan[valid]`: real listener completed with one full-feed call instead of zero; retained, airing and next-match setup succeeded.
3. `test_newer_data_supersedes_held_data`: both real distinct HTTP refreshes completed; stale Rennen announced before Sprint instead of only latest-feed Sprint.
4. `test_invalid_initial_filter_retention_edit_finishes`: setup and retention edit completed; empty baseline left `_config_pending=True` instead of completing revision 1.

None failed on imports, fixtures, discovery or timeouts. Gate waits are bounded and released in `finally`; no timing sleeps establish ordering. Task 1 verify passed twice before expansion. Existing latest-edit behaviors already supplied by Task 1 are regression backstops, not falsely claimed REDs.

## Verification

- Tracer: `uv run pytest tests/test_matcher_races.py::test_data_during_config_preserves_baseline_and_retention tests/test_matcher_runtime.py tests/test_new_match_event.py tests/test_retention.py -q` — **39 passed**, repeated successfully at tracer feedback gate.
- Expansion: `uv run pytest tests/test_matcher_races.py tests/test_matcher_runtime.py tests/test_sensor.py tests/test_retention.py tests/test_reconfigure.py tests/test_new_match_event.py -q` — **90 passed** in final run, including all **17** new race/edit cases.
- Full suite: `uv run pytest -q -m "not benchmark" -ra` — **1025 passed, 4 skipped, 4 deselected** in 20.29 s.
- `uv run ruff check . && uv run ruff format --check .` — **clean**, 75 files formatted.
- Evaluation scope resolved all seven task commits on this branch. No tracked-file deletions, packages, pushes, tags or hook bypasses.

## Deviations from Plan

1. **[Rule 1 - Test correction]** Task 1's narrowing test initially used the nonexistent stored key `include_regex`. Corrected it to the existing `include` contract; otherwise the old retained race legitimately still matched. The widening RED evidence was unaffected. File: `tests/test_matcher_races.py`; verified by four passing variants; commit `814d59f`.
2. **[Rule 1 - Introduced regression]** Serializing DATA removed the old generation-based DATA supersession. Added a deterministic DATA→DATA test and feed-identity check so an obsolete feed cannot announce or persist after a newer feed arrives. Files: matcher and race tests; RED `c65cf18`, GREEN `876ba9b`.
3. **[Rule 1 - Empty-obligation completion]** Inspection of the new pending state identified the initially invalid-filter branch leaving a retention edit pending indefinitely. Added RED coverage and synchronously completed that empty revision. Files: matcher and race tests; RED `7f62ff9`, GREEN `b79dacb`.

All adjustments directly preserve correctness of the planned ordering change. No unrelated review findings were fixed.

## Known Stubs / Deferred Verification

No introduced stubs, placeholders, TODOs, skipped tests or new security surface. Empty initialization is wired to real coordinator/Store data.

The full verification command ran, but its existing environment gates remain:
- `tests/xmltv/test_real_feed.py:26`: 04-10 full-suite verification: licensed real-feed fixture deferred and XMLTV_REAL_FEED not supplied.
- `tests/test_repo_structure.py:388`: 04-10 full-suite verification: three existing shellcheck cases skipped because shellcheck is not installed.

Recorded in `.planning/WINDOWS.md` entries 5 and 6; prior entries remain unchanged. Benchmark deselection is explicitly required by the plan. No installs were attempted.

## Threat Mitigations

- T-04-28: exact CONFIG→DATA event/seen/retained assertions, enabled and disabled, prove silent baselines before genuine new-feed events.
- T-04-29: asyncio serialization never blocks the HA loop on a thread lock; bounded gate cleanup, DATA coalescing and lifecycle tests detect deadlocks/stale commits.
- T-04-30: immutable revision snapshots, final accepted-revision/record assertions and no-resurrection tests prevent stale completion from clearing newer obligations.
- T-04-SC: no packages or dependency changes. Public event keys, entity identity, caps, stored fields and Store schema unchanged.

## Pending Human Verification / Next Readiness

WR-01 and related IN-01 now have passing deterministic evidence. Ready for end-of-phase verification, **not** automatic human acceptance or release. Keep every human item in `04-VERIFICATION.md`, EDGE-01..EDGE-17 assumptions and judgment-tier prohibitions pending. In particular the no-edit-notification prohibition remains **flagged-unverified for human judgment**.

Live HA restart/disk persistence, enabled/disabled presentation walkthroughs, real notifications, blueprint/frontend behavior, translated UI, README accuracy, AUT-06 cancellation backstop, review dispositions and user-only release/HACS pickup remain pending. IN-02/IN-03/IN-04/IN-06 are untouched. No pushes or tags (D-29).

## Self-Check: PASSED

Both production/test files, all eight RED evidence files and this summary exist. All seven task commits are ancestors of HEAD and evaluation scope resolves them on this branch. Every automated task/plan verification ran successfully; existing environment-gated skips are recorded above and in the cross-phase ledger.
