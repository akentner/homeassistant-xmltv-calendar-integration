---
phase: 01-first-filtered-calendar
verified: 2026-10-18T19:54:16Z
status: passed
score: 5/5 roadmap success criteria verified (automated evidence plus prior accepted UAT)
execution_mode: inline
source_head: 19e262dab163da4114809a248883102c93ceb9a8
covered_files: [".github/workflows/ci.yml",".github/workflows/validate.yml",".planning/phases/01-first-filtered-calendar/01-01-PLAN.md",".planning/phases/01-first-filtered-calendar/01-01-SUMMARY.md",".planning/phases/01-first-filtered-calendar/01-02-PLAN.md",".planning/phases/01-first-filtered-calendar/01-02-SUMMARY.md",".planning/phases/01-first-filtered-calendar/01-03-PLAN.md",".planning/phases/01-first-filtered-calendar/01-03-SUMMARY.md",".planning/phases/01-first-filtered-calendar/01-04-PLAN.md",".planning/phases/01-first-filtered-calendar/01-04-SUMMARY.md",".planning/phases/01-first-filtered-calendar/01-05-PLAN.md",".planning/phases/01-first-filtered-calendar/01-05-SUMMARY.md",".planning/phases/01-first-filtered-calendar/01-06-PLAN.md",".planning/phases/01-first-filtered-calendar/01-06-SUMMARY.md",".planning/phases/01-first-filtered-calendar/01-07-PLAN.md",".planning/phases/01-first-filtered-calendar/01-07-SUMMARY.md",".planning/phases/01-first-filtered-calendar/01-08-PLAN.md",".planning/phases/01-first-filtered-calendar/01-08-SUMMARY.md",".planning/phases/01-first-filtered-calendar/01-09-PLAN.md",".planning/phases/01-first-filtered-calendar/01-09-SUMMARY.md",".planning/phases/01-first-filtered-calendar/01-10-PLAN.md",".planning/phases/01-first-filtered-calendar/01-10-SUMMARY.md",".planning/phases/01-first-filtered-calendar/01-11-PLAN.md",".planning/phases/01-first-filtered-calendar/01-11-SUMMARY.md",".ruff.toml","LICENSE","README.md","custom_components/xmltv_calendar/__init__.py","custom_components/xmltv_calendar/brand/icon.png","custom_components/xmltv_calendar/brand/icon@2x.png","custom_components/xmltv_calendar/cache.py","custom_components/xmltv_calendar/calendar.py","custom_components/xmltv_calendar/config_flow.py","custom_components/xmltv_calendar/const.py","custom_components/xmltv_calendar/coordinator.py","custom_components/xmltv_calendar/data.py","custom_components/xmltv_calendar/diagnostics.py","custom_components/xmltv_calendar/manifest.json","custom_components/xmltv_calendar/source.py","custom_components/xmltv_calendar/translations/de.json","custom_components/xmltv_calendar/translations/en.json","custom_components/xmltv_calendar/xmltv/__init__.py","custom_components/xmltv_calendar/xmltv/filter.py","custom_components/xmltv_calendar/xmltv/model.py","custom_components/xmltv_calendar/xmltv/normalize.py","custom_components/xmltv_calendar/xmltv/parser.py","custom_components/xmltv_calendar/xmltv/preview.py","custom_components/xmltv_calendar/xmltv/render.py","custom_components/xmltv_calendar/xmltv/schedule.py","custom_components/xmltv_calendar/xmltv/settings.py","custom_components/xmltv_calendar/xmltv/timeparse.py","custom_components/xmltv_calendar/xmltv/window.py","docs/assets/icon.svg","hacs.json","pyproject.toml","renovate.json","scripts/generate_benchmark_feed.py","tests/__init__.py","tests/conftest.py","tests/fixtures/basic.xml","tests/fixtures/edge_cases.xml","tests/fixtures/latin1.xml","tests/test_advanced_flow.py","tests/test_cache.py","tests/test_calendar.py","tests/test_config_flow.py","tests/test_diagnostics.py","tests/test_empty_feed.py","tests/test_file_source.py","tests/test_filtering.py","tests/test_identity.py","tests/test_ingestion.py","tests/test_init.py","tests/test_options_flow.py","tests/test_reconfigure.py","tests/test_refresh.py","tests/test_repairs.py","tests/test_repo_structure.py","tests/test_schedule_refresh.py","tests/test_source.py","tests/test_subentry_flow.py","tests/test_templates.py","tests/test_timezone_options.py","tests/test_timing.py","tests/test_tracer.py","tests/test_translations.py","tests/xmltv/__init__.py","tests/xmltv/conftest.py","tests/xmltv/test_benchmark.py","tests/xmltv/test_filter.py","tests/xmltv/test_normalize.py","tests/xmltv/test_parser.py","tests/xmltv/test_preview.py","tests/xmltv/test_purity.py","tests/xmltv/test_real_feed.py","tests/xmltv/test_render.py","tests/xmltv/test_schedule.py","tests/xmltv/test_settings.py","tests/xmltv/test_timeparse.py","tests/xmltv/test_window.py","uv.lock"]
covered_digest: "v3:sha256:9927d106e558a86c72c6bf9b90ffa3d6b52cfb43952ae63c66b5c91054287fea"
behavior_unverified: 0
overrides_applied: 0
decision_coverage:
  honored: 16
  total: 16
  not_honored: []
re_verification:
  previous_status: stale
  gaps_remaining: []
  regressions: []
human_verification: []
---

# Phase 01: First Filtered Calendar — Re-verification

**Phase goal:** As a Home Assistant user, I want to add an XMLTV source (URL or local file) in the HA UI and attach calendars filtered by channel and include/exclude regex, so that I see exactly the matching programmes as correctly timed calendar events that drive calendar triggers.

**Verdict:** Passed, retaining the previously accepted live-trigger deferral in 01-UAT.md.
This refreshes the stale Phase 1 report against the current implementation; it does not re-accept every historical
review warning, certify Phase 3, or claim a new live walkthrough. All eleven plans have summaries.
The goal's wording was converted to User Story format with user approval on 2026-10-18; scope is unchanged.
Native subagent tools were unavailable, so verification and review ran inline.

## User Flow Coverage

| Step | Evidence | Result |
|------|----------|--------|
| Add URL or allowed local file through HA UI | config_flow.py source menu, URL validation, executor file check; test_config_flow.py and test_tracer.py | VERIFIED |
| Decode plain/gzip data regardless of extension | parser.parse magic sniff; test_ingestion.py and parser tests | VERIFIED |
| Reject duplicate sources | typed normalized SHA-256 identity; test_identity.py asserts entries are LOADED | VERIFIED |
| Add independent filtered calendars sharing the source | runtime_data coordinator and subentry reconciliation; test_init.py and test_subentry_flow.py | VERIFIED |
| Read exactly matching programmes with channel location | FilterSpec.apply and render.to_event_fields; test_filtering.py, xmltv/test_filter.py and test_render.py | VERIFIED |
| Expose correct events, state and calendar triggers | aware timestamp parser, stable UID, MatchIndex, CalendarEvent; test_timing.py and test_calendar.py | VERIFIED |

## Roadmap Success Criteria

| Criterion | Current evidence | Result |
|-----------|------------------|--------|
| SC1: UI source/calendar setup, gzip and duplicate rejection | Real HA flow-manager tracer; URL/file/identity/subentry tests; prior UAT tests 1 and 7 passed | VERIFIED |
| SC2: channel AND include AND NOT exclude, one event per programme, UID/location/title, invalid and blank regex handling | Filter truth tables; dedup/render tests; flow validation; test_init.py source-sharing assertions | VERIFIED |
| SC3: timestamp variants, inferred stop, stable UID, malformed-programme isolation | timeparse/parser/normalize/render tables; malformed timestamp end-to-end tracer; event-building guard tests | VERIFIED |
| SC4: start/end/offset triggers, overlapping get_events and live state | test_start_offset_and_end_triggers_fire asserts firing time and payload; state and overlap tests | VERIFIED; live wall-clock test remains deferred |
| SC5: large-feed responsiveness/memory and HACS/CI structure | Four benchmark tests; test_repo_structure.py; prior UAT 2/4/6 passed | VERIFIED within the evidence limits below |

## Requirement Traceability

Every requirement ID in the eleven PLAN frontmatters is accounted for.

| Requirement IDs | Evidence |
|-----------------|----------|
| SRC-01, SRC-02, SRC-03, SRC-04, SRC-13 | test_config_flow.py, test_identity.py, test_ingestion.py, test_file_source.py, test_schedule_refresh.py |
| SRC-09 | Four 60 MB benchmark tests; executor paths in coordinator/calendar/config_flow; forbid_loop_io fixture |
| FLT-01, FLT-02, FLT-03, FLT-04, FLT-07 | test_init.py, test_subentry_flow.py, test_filtering.py, xmltv/test_filter.py |
| EVT-01, EVT-02, EVT-05, EVT-06 | xmltv/test_normalize.py, test_render.py, test_timeparse.py, test_parser.py; test_timing.py |
| AUT-01, AUT-02 | test_calendar.py actual HA automation trigger/state tests and overlap/cap tests |
| CFG-01 | test_tracer.py and source/subentry config-flow tests |
| DST-01, DST-02 | test_repo_structure.py; workflow inspection; prior completed UAT test 6 |

## Automated Checks

Executed during this same re-verification session, before the format-gate checkpoint. Source HEAD did not change
across the user's approval; only documentation changed afterward, so a duplicate test run was unnecessary.

- `.venv/bin/pytest -q --junitxml=/tmp/xmltv-phase01-reverification.xml`: **821 passed, 1 skipped**, 52.65 s.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/ruff format --check .`: passed; 62 files formatted.
- `check tdd.review-checkpoint 01 --raw`: all 5 TDD plans passed, zero violations.
- `query check.decision-coverage-verify`: 16/16 trackable decisions honored (heuristic/advisory).
- User Story validator: valid after the approved wording-only correction.
- No prior-phase regression gate applies to Phase 1. The full suite nevertheless covers implemented Phases 1–3.

| Feed | Parse under tracemalloc | Peak memory | Plain parse / heartbeat run | Max loop gap |
|------|------------------------|-------------|-----------------------------|--------------|
| 60 MB XML, 80,773 programmes | 9.25 s | 101.9 MB | 2.84 s | 176.9 ms |
| Same feed gzip-compressed | 9.89 s | 102.0 MB | 2.99 s | 121.0 ms |

Limits: parse <30 s, peak <150 MB, heartbeat gap <250 ms. All pass.
Four pytest warnings concern record_property with xunit2 reporting, not integration behavior.

## Plans, Artifacts and Wiring

| Plans | Checked contract / substantive wiring |
|-------|--------------------------------------|
| 01-01 | Flow-created source -> entry runtime_data -> coordinator -> calendar platform -> actual get_events and state |
| 01-02 | Timestamp parsing -> normalize/dedup/inferred stops -> deterministic UTC/title-derived UID |
| 01-03 | Stored channel/include/exclude data -> FilterSpec -> executor refilter -> MatchIndex |
| 01-04 | MatchIndex bisect overlap -> capped event construction; large slices off loop; HA automation trigger dispatch |
| 01-05 | Bounded async download -> gzip-magic parser -> guarded streaming iterparse -> complete EpgData publication |
| 01-06 | HACS manifest/icons/license; pinned least-privilege CI; reproducible generator and measured benchmark |
| 01-07 | Allowed absolute file path -> canonical identity; file checks at setup/refresh; normalized URL duplicate rejection |
| 01-08 | Loaded-source guard -> selector/regex validation -> one entity/device per subentry; one shared source download |
| 01-09 | Historical live UI acceptance retained; generated-feed acceptance active; third-party excerpt explicitly deferred |
| 01-10 | Historical public/HACS acceptance retained; repository references now use homeassistant-xmltv-calendar-integration |
| 01-11 | Offset/year bounds, per-programme conversion containment and per-event guard remain covered by passing regressions |

Later approved phases intentionally supersede literal Phase 1 details: setup now performs a bounded full download
behind progress rather than a separate 64 KiB network probe; preview/reconfigure, NFC normalization and selectable
field scope are present; empty sources fail per Phase 3 D-20 rather than loading an empty EpgData. These are
documented successor contracts, not regressions of the user outcome.

## Security, Review and Test Quality

The plan-time threat register remains at zero open high/critical threats; 01-SECURITY.md updates the removed probe
helper's mitigation to the current bounded downloader. No new risk acceptance or dependency install occurred.
01-REVIEW.md records the current inline regression review separately from its historical findings.
Known memory amplification, regex runtime and extreme-duration concerns remain visible; passing the generated-feed
benchmark does not establish a universal memory or CPU bound for every adversarial feed.

No TODO/FIXME/XXX/TBD debt markers were found under source/tests. The only disabled requirement-related test is
the real-feed acceptance module: the user declined redistributing a real excerpt (D-15). Synthetic/parser/tracer
coverage remains active; the open skipped-test window is unchanged. Assertions inspected include exact matched
events, LOADED entry state, HTTP call counts, concrete trigger times/payloads and benchmark thresholds.
Expected synthetic feed values and UTC instants are specified independently rather than captured from the parser.

The native HA UI source review is in 01-UI-REVIEW.md; no unsupported visual score or screenshot claim is made.
General reference: [HA quality rules](https://contributors.home-assistant.io/core/quality-scale/rules/).

## Prior Human Acceptance and Remaining Debt

01-UAT.md remains authoritative: **8 passed, 0 issues, 1 skipped**.
Test 3 (live calendar trigger with -5-minute offset) was explicitly deferred by the user on 2026-10-15.
It remains skipped, not relabeled as passed, and remains visible to audit-uat.
Judgment-tier prohibitions were accepted by prior UAT test 8; prior warning decisions are in test 9.
No new human acceptance was inferred from the user's approval of the User Story wording.

Historical UI/HACS acceptance and green remote checks were not rerun here. This run does not certify current remote
CI, live HA rendering, HA 2026.3 compatibility, or performance on ha-host hardware. Phase 3's outstanding live checks
remain outstanding. No push or deployment was performed.

## Advisory (New Scope, Unevidenced)

None added as blockers. Existing non-blocking warnings remain in REVIEW.md and REVIEW-DISPOSITION.md.

## Completion and Routing

Phase 1 was already marked complete on 2026-10-15; its canonical verification is now refreshed.
Do not rewind STATE.md's existing Phase 03 position or rerun the Phase 1 -> Phase 2 transition.
The remaining stale earlier-phase verification is Phase 02: `$gsd-execute-phase 02`.
