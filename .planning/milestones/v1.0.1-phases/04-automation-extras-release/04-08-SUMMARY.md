---
phase: 04-automation-extras-release
plan: 08
subsystem: docs-i18n-release
tags: [home-assistant, translations, i18n, ast, readme, hacs, release, blueprint]

requires:
  - phase: 04-automation-extras-release
    provides: "04-01..04-07: sensors (next_match, last_fetch), xmltv_calendar_new_match event, release workflow, blueprint, last-fetch vocabularies, retention, Keep past matches (days) field, and their en/de strings"
provides:
  - "tests/test_translations.py: AST collector over config_flow.py (per flow class plus the module functions it calls), test_every_flow_key_is_translated, test_every_vocabulary_and_entity_key_is_translated, test_german_ui_is_served_for_every_required_key"
  - "translations en/de: config.step.download.title (the setup download's progress dialog title)"
  - "README.md rewritten for 0.1.0: requirements, HACS install, sources, calendars with regex examples, advanced options, entities, event payload, automation examples, blueprint import button, limitations, diagnostics, releases"
  - "tests/test_repo_structure.py: test_readme_documents_automation_and_limitations"
affects: [phase 04 UAT (German UI walkthrough, README import button), v0.1.0 release by the user]

actuals:
  tokens: 9426
  tasks: 2
  commits: 3
plan_head_before: 4c0ec86a3fb33e4582a10648d55d5da74330ab96
plan_head_after: 676242611cee1568ec699be801f6648b9a79d2c2

tech-stack:
  added: []
  patterns:
    - "Translation completeness is derived from the code (ast walk of config_flow.py, vocabularies imported from settings/schedule/coordinator/cache, _attr_translation_key from sensor.py), so a new key without a string fails CI"
    - "A step ID requires <section>.step.<id>.title as a leaf, so every dialog has a translated title"

key-files:
  created:
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-08-red.json
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-08-red.xml
  modified:
    - tests/test_translations.py
    - custom_components/xmltv_calendar/translations/en.json
    - custom_components/xmltv_calendar/translations/de.json
    - README.md
    - tests/test_repo_structure.py

key-decisions:
  - "The completeness test requires <section>.step.<id>.title for every step ID (not just the step node); the download progress step was the one step without it and got 'Downloading the feed' / 'Feed wird heruntergeladen'"
  - "Flow keys are collected per flow class, including the literals of the module-level functions a class calls (transitively); HA-generated aborts are derived from _abort_if_unique_id_configured (already_configured) and async_update_and_abort (reconfigure_successful); subentry initiate_flow.user/reconfigure and entry_type are required too"
  - "The vocabulary test also asserts that the selector translation_keys in config_flow.py equal the mapped vocabularies and that every literal UpdateFailed translation_key in coordinator.py is in FAILURE_REASONS, so a new selector or failure reason cannot slip past"
  - "The German check requires every required key to be served by async_get_translations(hass, 'de', ...) and to differ from English unless it is a literal or in SAME_IN_GERMAN ({'UTC'})"
  - "README states the interval refresh is anchored to the last refresh, restart or reload, and documents the language-dependent sensor entity IDs (German: sensor.<name>_nachste_sendung, sensor.<name>_letzter_abruf; HA's NATIVE_ENTITY_IDS includes de)"

patterns-established:
  - "Code-derived i18n completeness: add a vocabulary to SELECTOR_VOCABULARIES / ATTEMPT_VOCABULARIES when adding a translated selector or state attribute"

requirements-completed: [CFG-04, DST-04, DST-03]

coverage:
  - id: D1
    description: "Every flow step, error, abort, menu option and progress text of the config, options and calendar subentry flows, every selector option, coordinator failure (exception and Repairs issue), sensor name and Last fetch attribute state has an English string"
    requirement: CFG-04
    verification:
      - kind: unit
        ref: "tests/test_translations.py#test_every_flow_key_is_translated"
        status: pass
      - kind: unit
        ref: "tests/test_translations.py#test_every_vocabulary_and_entity_key_is_translated"
        status: pass
    human_judgment: false
  - id: D2
    description: "Home Assistant serves a German string for every required key; en/de keep the same keys in the same order, placeholders and literals"
    requirement: CFG-04
    verification:
      - kind: integration
        ref: "tests/test_translations.py#test_german_ui_is_served_for_every_required_key"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/test_translations.py -q -k 'same_keys or keeps_placeholders or keeps_literals'"
        status: pass
    human_judgment: false
  - id: D3
    description: "German UI walkthrough on ha-dev: adding a source (URL and file), its options, adding and editing a calendar incl. advanced step and preview, one validation error per form, both sensors; no raw key anywhere"
    requirement: CFG-04
    verification: []
    human_judgment: true
    rationale: "Task 1 <human-check>: how the frontend renders the served strings (dialog titles, section labels, selector options) needs a person looking at the German UI"
  - id: D4
    description: "README documents installation, sources, calendars with regex examples, advanced options incl. Keep past matches, both sensors, the event payload, automation examples, blueprint import button, limitations (15-minute trigger window, overlapping events, one-event state), diagnostics and releases"
    requirement: DST-04
    verification:
      - kind: unit
        ref: "tests/test_repo_structure.py#test_readme_documents_automation_and_limitations"
        status: pass
      - kind: unit
        ref: "tests/test_repo_structure.py#test_readme_documents_hacs_install_and_floor"
        status: pass
    human_judgment: true
    rationale: "The test checks that the required content is present; whether the prose is accurate and readable, and whether the Import blueprint button opens the import dialog, needs a reader and a browser"
  - id: D5
    description: "Release readiness: full test suite, benchmarks, Ruff lint and format, hassfest green; manifest version 0.1.0; no v0.1.0 tag created by the assistant"
    requirement: DST-03
    verification:
      - kind: other
        ref: "uv run pytest -q -m 'not benchmark' (981 passed, 1 skipped) && uv run pytest -q -m benchmark (4 passed) && uv run ruff check . && uv run ruff format --check ."
        status: pass
      - kind: other
        ref: "podman run --rm -v $PWD:/github/workspace:ro,Z ghcr.io/home-assistant/hassfest (exit 0, Invalid integrations: 0)"
        status: pass
    human_judgment: false
  - id: D6
    description: "User pushes main and tag v0.1.0; the Release workflow publishes GitHub release v0.1.0 (not prerelease, not draft) and HACS offers XMLTV Calendar 0.1.0"
    requirement: DST-03
    verification: []
    human_judgment: true
    rationale: "D-29 and the project rule: only the user pushes and tags; the publish can only be observed after that push"

duration: 11min
completed: 2026-10-21
status: complete
---

# Phase 04 Plan 08: Translations, README and Release Readiness Summary

**Code-derived en/de translation completeness test (AST over config_flow.py plus the vocabularies) that found and fixed the untitled download step, a full user README for 0.1.0 with automation examples, blueprint import button and calendar limitations, and a green release gate waiting for the user's v0.1.0 tag push**

## Performance

- **Duration:** 11 min
- **Started:** 2026-10-21T10:19:41Z
- **Completed:** 2026-10-21T10:30:30Z
- **Tasks:** 2
- **Files modified:** 7 (5 source/docs/test files plus 2 RED evidence files)

## Accomplishments

- CI now fails when any flow step, error, abort, menu option, progress action, selector option, failure reason, Repairs issue, sensor name or Last fetch state is missing in English, or is not served in German by Home Assistant.
- The collector found one gap: the setup download's progress step (`step_id="download"`) had no title. It now shows "Downloading the feed" / "Feed wird heruntergeladen".
- README.md rewritten (47 to about 400 lines): requirements, HACS install, sources (refresh modes and why the daily time is preferable, timezone options, cache, conditional requests, limits, retries and Repairs), calendars (channels, channel regex, include/exclude with `formel\s*1|formula\s*1`, `^Tatort$`, `Wiederholung`, case and umlauts), advanced options including Keep past matches (days) and its limits, the calendar and both sensors with attribute tables, the `xmltv_calendar_new_match` event with payload table and ISO 8601 local-time note, three automation examples, the blueprint with the my.home-assistant.io import button, limitations, diagnostics, releases.
- Release gate green: 981 tests passed (1 skipped: real-feed check, deferred since 01-09), 4 benchmarks passed, Ruff lint and format clean, hassfest exit 0 with 0 invalid integrations, manifest version 0.1.0, no `v0.1.0` tag exists.

## Task Commits

1. **Task 1: Tracer: every flow, error, abort, selector, failure and sensor key is served in English and German**
   - `7c9dce4` test(04-08): add code-derived translation completeness tests (RED)
   - `933cebf` feat(04-08): add the download step title in English and German (GREEN)
2. **Task 2: README for setup, filters, automations and limitations; release readiness for v0.1.0** - `6762426` (docs)

**Plan metadata:** see the docs(04-08) completion commit.

## TDD Gate Compliance (Task 1)

- **RED** (`7c9dce4`): `uv run pytest tests/test_translations.py -q -p no:cacheprovider --junitxml=.planning/phases/04-automation-extras-release/tdd-evidence/04-08-red.xml` exited 1 with 2 failed, 6 passed. Target `test_every_flow_key_is_translated` failed on `assert ['config.step.download.title'] == []`; `test_german_ui_is_served_for_every_required_key` failed on the same key. Classifier: `RED_EVIDENCE_OK (target_test_failed)` (record `tdd-evidence/04-08-red.json`).
- **Semantic assessment:** the target ran (JUnit errors=0, failure in the call phase) after its own non-vacuity assertions passed (all eleven known step IDs found; already_configured, reconfigure_successful, progress.download and menu option url derived), and failed on the planned completeness assertion for exactly one derived key. No import, fixture or collection fault. The vocabulary test and the six existing translation tests passed, so all selector, failure, issue and sensor keys were already present.
- **Non-vacuity of the vocabulary test** (no RED of its own, because nothing was missing): deleted `entity.sensor.last_fetch.state_attributes.cache.state.stale_hit` and `selector.weekday.options.sun` from en.json in the working tree, ran `uv run pytest tests/test_translations.py -q -p no:cacheprovider -k vocabulary`. It failed with `AssertionError: assert ['entity.sens....options.sun'] == []`, `Left contains 2 more items, first extra item: 'entity.sensor.last_fetch.state_attributes.cache.state.stale_hit'`. Restored with `git checkout -- custom_components/xmltv_calendar/translations/en.json`; `git diff --stat` on the file was empty afterwards.
- **GREEN** (`933cebf`): `uv run pytest tests/test_translations.py -q` 8 passed.
- **REFACTOR:** none needed.

## README test before the rewrite (Task 2, step 1)

`test_readme_documents_automation_and_limitations` against the old README failed (`1 failed, 1 passed, 41 deselected`). 13 of the 15 required strings were missing: `xmltv_calendar_new_match`, `redirect/blueprint_import`, `15 minutes`, `mode: queued`, `Next programme`, `Last fetch`, `Keep past matches`, `homeassistant.update_entity`, `ISO 8601`, `unknown`, `overlapping`, `daily`, `channel_id`. `allowlist_external_dirs` was already documented, and `uid` occurred as a substring. After the rewrite: `uv run pytest tests/test_repo_structure.py -q -k readme` gives 2 passed. All five YAML examples in the README parse with `yaml.safe_load`.

## Acceptance Criteria

| Criterion | Result |
|-----------|--------|
| `uv run pytest tests/test_translations.py -q` exits 0 | PASS (8 passed) |
| 04-08-red.json is RED_EVIDENCE_OK | PASS |
| `grep -q 'def test_every_flow_key_is_translated' tests/test_translations.py` | PASS |
| `-k "same_keys or keeps_placeholders or keeps_literals"` exits 0 | PASS (3 passed) |
| Both Task 2 verify commands exit 0 | PASS (pytest, benchmarks, ruff, hassfest exit 0 / 0 invalid) |
| `uv run pytest tests/test_repo_structure.py -q -k readme` exits 0, and it failed before the rewrite | PASS (see above) |
| `grep -c 'redirect/blueprint_import' README.md` >= 1 | PASS (1) |
| `grep -c '15 minutes' README.md` >= 1 | PASS (3) |
| `grep -ci 'later release' README.md` = 0 | PASS (0) |
| `git tag --list 'v0.1.0'` prints nothing | PASS |

## Files Created/Modified

- `tests/test_translations.py` - AST collector and the three completeness tests
- `custom_components/xmltv_calendar/translations/en.json`, `de.json` - `config.step.download.title`
- `README.md` - full user documentation for 0.1.0
- `tests/test_repo_structure.py` - `README_REQUIRED_TEXT` and `test_readme_documents_automation_and_limitations`
- `.planning/phases/04-automation-extras-release/tdd-evidence/04-08-red.json`, `04-08-red.xml` - RED evidence

## Decisions Made

See key-decisions in the frontmatter. In short, the tests are stricter than the plan's minimum: a step needs a title leaf, keys are checked per flow class, the selector keys and UpdateFailed keys have to match their vocabularies, and German texts must differ from English unless they are literals or "UTC".

## Deviations from Plan

### Process

**1. Tracer feedback gate continued instead of stopping**
- **Found during:** after Task 1 (`type="tracer"`)
- **Issue:** the tracer's `<verify>` has a `<human-check>`, so the precedence table (interactive, end-of-phase, row 4) would stop for a `checkpoint:human-verify` before Task 2.
- **What was done:** re-ran the tracer verify (8 passed) and went on to Task 2. The orchestrator's dispatch asks for the whole plan plus SUMMARY and for human steps to be written into the SUMMARY/report. Task 2 (README, gates) does not depend on how the German UI renders.
- **Effect:** the German UI walkthrough (D3) is still open for the phase UAT, together with the release steps below.

---

**Total deviations:** 1 (process; no code deviations)
**Impact on plan:** None on code. One human check moved to the end-of-phase UAT.

## Issues Encountered

None.

## User Setup Required

None. The release is a manual step for the user (below).

## Release Steps for the User (D-29, not done by the assistant)

Do this after the phase UAT and code review pass:

```bash
git push origin main
git tag v0.1.0 && git push origin v0.1.0
gh run list --workflow release.yml --limit 1
gh release view v0.1.0 --json tagName,isPrerelease,isDraft
```

Expected: the Release workflow run succeeds, and the release shows tagName v0.1.0, isPrerelease false, isDraft false. Then refresh the repository in HACS on ha-host and confirm it offers XMLTV Calendar 0.1.0. Also confirm that the README's "Import blueprint" button opens the blueprint import dialog.

## Human Checks for the Phase UAT

- **German UI (CFG-04):** on ha-dev with the user profile language set to German, add a source (URL and file, including the download progress dialog), open its options (schedule, timezone), add and edit a calendar including the advanced step and the preview, trigger one validation error per form, and open both sensors on a calendar device. Every title, label, help text, error and abort reason must be German, with no raw key.
- **README:** read it for accuracy, and try the Import blueprint button.

## Next Phase Readiness

All 8 plans of phase 04 are complete. Next: phase verification and UAT (`/gsd-verify-work 04`), then the user's v0.1.0 tag push.

---
*Phase: 04-automation-extras-release*
*Completed: 2026-10-21*

## Self-Check: PASSED
