---
phase: 03-resilient-sources
plan: 10
subsystem: config-flow
tags: [home-assistant, config-flow, cache, diagnostics, repairs, tests, tdd, gap-closure]
status: complete

requires:
  - phase: 03-resilient-sources
    provides: "03-02 FeedCache/CacheMeta, 03-04 SourceHealth and the 24 h Repairs issue, 03-06 flow-seeded cache (D-13), 03-07 diagnostics"
provides:
  - "config_flow._async_seed_cache saves SourceHealth(last_success=fetched_at) after a successful FeedCache.async_write, with the same fetched_at as the CacheMeta (WR-02)"
  - "tests/test_config_flow.py: step 7 of the URL end-to-end test (coordinator health + diagnostics last_success/fetched_at) and test_seeded_source_issue_names_setup_download"
  - "tests/test_identity.py frozen at 2026-10-13T06:00:00+00:00, LOADED assertions on the three flow tests, single-download assertion on the URL variant (WR-03)"
affects: [phase-03-verification, phase-03-uat]

actuals:
  tokens: 1826
  tasks: 2
  commits: 4
plan_head_before: 6c25498fa106fb8bd3a4e6b6f82d3a7e76d874a1
plan_head_after: 77c9a14c5763e08201a0f14445a5edb1a862eadb

tech-stack:
  added: []
  patterns:
    - "Seed health where the success happens: the setup flow records the download as last_success together with the cache it actually wrote, so the coordinator loads it in _async_setup"

key-files:
  created:
    - .planning/phases/03-resilient-sources/tdd-evidence/03-10-red.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-10-red-issue.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-10-red.xml
    - .planning/phases/03-resilient-sources/tdd-evidence/03-10-red-2.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-10-red-2.xml
  modified:
    - custom_components/xmltv_calendar/config_flow.py
    - tests/test_config_flow.py
    - tests/test_identity.py

key-decisions:
  - "The setup flow seeds SourceHealth(last_success=fetched_at) only when FeedCache.async_write returned True; a failed cache write seeds nothing and the coordinator records its own first success (T-03-29)"
  - "A brand-new entry's seeded health holds only last_success (no failure history exists yet); coordinator.py, cache.py and diagnostics.py are unchanged"

patterns-established:
  - "Every test module that sets up entries from fixtures/basic.xml freezes the clock at 2026-10-13 and asserts the created entry is LOADED, so expired fixtures fail loudly"

requirements-completed: [SRC-12, CFG-03]

coverage:
  - id: D1
    description: "A URL source created through the setup flow reports the setup download as last_success (coordinator health and diagnostics), consecutive_failures 0, cache.fetched_at equal, one download in total"
    requirement: SRC-12
    verification:
      - kind: integration
        ref: "tests/test_config_flow.py#test_url_source_end_to_end_with_progress_and_seeded_cache"
        status: pass
    human_judgment: false
  - id: D2
    description: "A failure streak of more than 24 h after a flow-created source raises a Repairs issue naming the setup download ('2026-10-13 08:00' Europe/Berlin), not '-'"
    requirement: SRC-12
    verification:
      - kind: integration
        ref: "tests/test_config_flow.py#test_seeded_source_issue_names_setup_download"
        status: pass
    human_judgment: false
  - id: D3
    description: "Identity flow tests run at the fixture date and assert the created entries are LOADED; the URL variant downloads once"
    requirement: CFG-03
    verification:
      - kind: integration
        ref: "tests/test_identity.py#test_url_variant_identity_invariant"
        status: pass
      - kind: integration
        ref: "tests/test_identity.py#test_url_entry_stores_normalized_url_and_hashed_id"
        status: pass
      - kind: integration
        ref: "tests/test_identity.py#test_file_variant_identity_invariant"
        status: pass
    human_judgment: false

duration: 3 min
completed: 2026-10-16
---

# Phase 3 Plan 10: Setup Download as Last Success, Frozen Identity Tests Summary

**The setup flow now saves `SourceHealth(last_success=fetched_at)` together with the seeded cache. Diagnostics and the Repairs text name the setup download instead of `null` / `-` (WR-02). `tests/test_identity.py` runs frozen at the fixture date and asserts LOADED entries (WR-03).**

## Performance

- **Duration:** 3 min
- **Started:** 2026-10-16T13:33:38Z
- **Completed:** 2026-10-16T13:36:16Z
- **Tasks:** 2
- **Files modified:** 3 source/test files (+5 RED evidence files)

## Accomplishments

- WR-02 closed. `_async_seed_cache` reads `fetched_at` once and passes it to `async_write`. Only when that write returns True does it also save `SourceHealth(last_success=fetched_at)`. The new entry's coordinator loads this health in `_async_setup`, so `health.last_success` is the setup download from the first minute. Diagnostics report it, and a later failure streak names it in Repairs.
- CFG-03 unchanged: the flow still downloads once, and the first refresh parses the seeded cache. Step 7 asserts `call_count == 1`.
- WR-03 closed. `tests/test_identity.py` has `NOW` plus `pytestmark = pytest.mark.freeze_time(NOW)`, and its three flow tests assert `ConfigEntryState.LOADED`. On the real clock they had been passing against entries in SETUP_RETRY.

## Task Commits

| Task | RED | GREEN | RED evidence |
|------|-----|-------|--------------|
| 1 (tracer) | `82823e6` test(03-10): add failing tests for the setup download as the last success | `f0cefd7` feat(03-10): record the setup download as the source's last success | `03-10-red.json` + `03-10-red-issue.json`: RED_EVIDENCE_OK (JUnit). Step 7 failed on `coordinator.health.last_success == datetime.fromisoformat(NOW)` (actual None). The issue test failed on the placeholders (actual `last_success: '-'`). The other 36 tests passed; no teardown errors. |
| 2 | `bb521c1` test(03-10): assert flow-created identity entries load | `77c9a14` test(03-10): run the identity tests at the fixture date | `03-10-red-2.json`: RED_EVIDENCE_OK (JUnit). On the real clock (2026-10-16) all three flow tests failed on `entry.state is ConfigEntryState.LOADED` with SETUP_RETRY (expired fixture → empty_feed). The 8 pure tests passed. |

Tracer gate (Task 1): `human_verify_mode` is end-of-phase and the verify is automated-only. I re-ran the verify (90 passed) before Task 2, so no checkpoint was needed.

## TDD Gate Compliance

- RED: `82823e6` and `bb521c1` (`test(03-10)`), each before its GREEN commit and each backed by RED_EVIDENCE_OK.
- GREEN: `f0cefd7` (`feat(03-10)`) for Task 1. Task 2's GREEN is `77c9a14`, committed as `test(03-10)` as the plan specifies, because it is a test-only change.
- REFACTOR: none needed.

## Files Created/Modified

- `custom_components/xmltv_calendar/config_flow.py`: imports `SourceHealth`; `_async_seed_cache` now saves the seeded health after a successful cache write, and its docstring is extended.
- `tests/test_config_flow.py`: new imports (`datetime`, `issue_registry`, `async_get_config_entry_diagnostics`), step 7, and `test_seeded_source_issue_names_setup_download`.
- `tests/test_identity.py`: new `ConfigEntryState` import, `NOW`/`pytestmark` freeze, three LOADED assertions and one `call_count == 1` assertion.
- `.planning/phases/03-resilient-sources/tdd-evidence/03-10-red{,-issue,-2}.json`, `03-10-red{,-2}.xml`.

## Decisions Made

- Seed only together with a cache write that succeeded: the flow never claims a success whose payload is not on disk (T-03-29).
- The seeded health contains only `last_success`. A new entry has no failure history to preserve.

## Deviations from Plan

None - plan executed exactly as written. (The new test types `freezer` as `Any`, the convention in `tests/test_repairs.py` and `tests/test_cache.py`.)

## Issues Encountered

None.

## Notes

- `coordinator.py`, `cache.py` and `diagnostics.py` are untouched (`git show --stat f0cefd7` lists only `config_flow.py`).
- REQUIREMENTS.md statuses are left at "Gaps Found" until phase re-verification (commit 21e69d6).

## User Setup Required

None.

## Next Phase Readiness

This was the last open gap-closure plan for phase 03. Phase 03 is ready for re-verification (`/gsd-verify-work 03`).

## Verification

- `uv run pytest tests/test_config_flow.py tests/test_diagnostics.py tests/test_cache.py tests/test_repairs.py -q`: 90 passed, no "Lingering".
- `uv run pytest tests/test_config_flow.py -q -k seeded`: 2 passed.
- `uv run pytest tests/test_identity.py -q`: 11 passed.
- `uv run pytest -q -m "not benchmark"`: 811 passed, 1 skipped, 4 deselected.
- `uv run ruff check . && uv run ruff format --check .`: clean.
- The acceptance greps print 1 (`SourceHealth(last_success=fetched_at)`), 1 (`if await cache.async_write(`), 1 (`^pytestmark = pytest.mark.freeze_time(NOW)`) and 3 (`ConfigEntryState.LOADED`).

## Self-Check: PASSED
