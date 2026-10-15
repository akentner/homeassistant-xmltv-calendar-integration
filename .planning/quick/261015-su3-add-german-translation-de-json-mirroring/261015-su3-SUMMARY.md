---
phase: quick-261015-su3
plan: 01
status: complete
subsystem: i18n
tags: [translations, de.json, home-assistant, hassfest, tdd]

requires:
  - phase: 02-precise-filters-preview
    provides: translations/en.json (config, config_subentries, exceptions, selector), SelectSelector translation keys match_field and weekday
provides:
  - custom_components/xmltv_calendar/translations/de.json mirroring all 95 en.json leaves in order
  - tests/test_translations.py (HA loader end-to-end test, hassfest value rules, key/placeholder/literal parity with en.json)
affects: [phase-03 options flow strings, phase-04 entity strings, CFG-04]

actuals:
  tokens: 8886
  tasks: 2
  commits: 4
plan_head_before: d41ef62509c0245279bf8a8be15c265bc1b88780
plan_head_after: 4345d537afb84cb212fcf1c3d0581e99da25cdfa

tech-stack:
  added: []
  patterns:
    - "en.json is the source of truth; de.json mirrors it key by key, enforced by parity tests"
    - "Translation verified through homeassistant.helpers.translation.async_get_translations, the frontend's path"

key-files:
  created:
    - custom_components/xmltv_calendar/translations/de.json
    - tests/test_translations.py
    - .planning/quick/261015-su3-add-german-translation-de-json-mirroring/tdd-evidence/su3-red-1.json
    - .planning/quick/261015-su3-add-german-translation-de-json-mirroring/tdd-evidence/su3-red-1.xml
    - .planning/quick/261015-su3-add-german-translation-de-json-mirroring/tdd-evidence/su3-red-2.json
    - .planning/quick/261015-su3-add-german-translation-de-json-mirroring/tdd-evidence/su3-red-2.xml
  modified: []

key-decisions:
  - "channel(s) -> Sender (TV context), never Kanal; Channel regex -> Sender-Regex"
  - "Include searches / Exclude searches labels -> Suchfelder (Einschließen) / Suchfelder (Ausschließen)"
  - "HA du-style German, literal umlauts, no [%key:] references (nothing resolves them for custom integrations)"
  - "CFG-04 only partially delivered (strings existing today); stays Pending in REQUIREMENTS.md"

requirements-completed: []  # CFG-04 deliberately NOT ticked: partial delivery, Phase 3/4 strings still to come

duration: ~4 min
completed: 2026-10-15
---

# Phase quick-261015-su3 Plan 01: German translation de.json Summary

German translations/de.json covering every en.json key (source flow, calendar subentry flow, errors, aborts, selectors, exceptions), served by HA's own translation loader for language "de" and locked to en.json by key, placeholder and literal parity tests.

## Accomplishments

- HA serves Montag..Sonntag and Titel/Untertitel/Beschreibung/Kategorie for the advanced form selectors: the UAT 02 test 1 symptom (English weekday names in a German UI) is fixed.
- All 95 leaves of en.json translated in identical key order, du-style, with regex examples (`^sky`, `\.de$`, `formel\s*1|formula\s*1`, `^Tatort$`), `/media/epg/guide.xml`, `allowlist_external_dirs`, `calendar.formel_1`, `http://`, `https://`, `22:00`, `02:00`, limits and all placeholders verbatim.
- tests/test_translations.py (5 tests):
  - `test_home_assistant_serves_german_strings`: every de.json string served unchanged through `async_get_translations(hass, "de", section, [DOMAIN])`, no ERROR from `homeassistant.helpers.translation`.
  - `test_de_values_follow_hassfest_rules`: non-empty, trimmed, no `[%`, no single-quoted placeholder, no HTML tag, no URL, parseable identifier placeholders.
  - `test_de_has_same_keys_as_en`, `test_de_keeps_placeholders`, `test_de_keeps_literals`: any en.json change without a de.json update fails CI.

## Task Commits

1. Task 1 RED: `73cff7b` test(quick-261015-su3): add failing German translation tests
2. Task 1 GREEN: `449bc80` feat(quick-261015-su3): German selector and exception strings
3. Task 2 RED: `7dbdb30` test(quick-261015-su3): lock de.json to en.json keys, placeholders and literals
4. Task 2 GREEN: `4345d53` feat(quick-261015-su3): German translation for source and calendar flows

## TDD Gate Compliance

### RED 1 (`tdd-evidence/su3-red-1.json`, classifier: RED_EVIDENCE_OK / target_test_failed)

- Target: `test_home_assistant_serves_german_strings` (tests/test_translations.py), exit 1, 2 failed / 0 passed.
- semanticAssessment: Target executed (hass fixture up, xmltv_calendar loaded by HA's translation helper) and failed on the planned weekday assertion (`assert weekdays == GERMAN_WEEKDAYS`): HA served the English fallback 'Monday'..'Sunday' because translations/de.json is missing (DEBUG 'JSON file not found'), exactly the UAT 02 test 1 symptom. No import, collection or fixture fault. The sibling `test_de_values_follow_hassfest_rules` failed on its planned `DE_JSON.is_file()` assertion.

### RED 2 (`tdd-evidence/su3-red-2.json`, classifier: RED_EVIDENCE_OK / target_test_failed)

- Target: `test_de_has_same_keys_as_en` (tests/test_translations.py), exit 1, 3 failed / 2 passed.
- semanticAssessment: Target executed and failed on its planned first assertion (missing keys == []): 79 keys of the config and config_subentries sections missing, first `config.abort.already_configured`. No import, collection or fixture fault. `test_de_keeps_placeholders` failed on exactly the six placeholder-bearing config_subentries strings; `test_de_keeps_literals` reported 15 keys including `^Tatort$` and `/media/epg/guide.xml`. The two Task 1 tests stayed green.

### GREEN

- After Task 1: 2 passed. After Task 2: 5 passed; full suite 518 passed, 1 skipped, 4 deselected (baseline 513 + 5). `ruff check .` and `ruff format --check .` clean.
- No REFACTOR step needed.

## Verification

- `uv run pytest tests/test_translations.py -q`: 5 passed
- `uv run pytest -q -m "not benchmark"`: 518 passed, 1 skipped, 4 deselected
- `uv run ruff check .`: All checks passed; `uv run ruff format --check .`: 49 files already formatted
- `git diff --exit-code .../translations/en.json .../xmltv/preview.py`: exit 0
- `list(de) == list(en)` -> True, `entry_type` -> Kalender; `grep -cF '\u00' de.json` -> 0
- Human check pending (end of task): German HA UI shows the flow texts in German (see plan Task 2 human-check).

## Glossary Decisions

- Sender (not Kanal) for TV channels; Sender-IDs, Sender-Regex.
- Sendung for programme; Einschließen / Ausschließen; Muster; regulärer Ausdruck.
- Suchfelder (Einschließen) / Suchfelder (Ausschließen) for "Include searches" / "Exclude searches".
- Titelvorlage / Beschreibungsvorlage, Platzhalter, Standard; Mindestdauer / Höchstdauer; Von / Bis; Vorschau, Speichern, Zurück.
- "bereits konfiguriert" (HA core wording); "entpackt" for uncompressed; "exklusiv" / "einschließlich" for exclusive / inclusive.

## Deviations from Plan

None in scope. Process note: the pre-commit protected-branch probe (`git.base-branch --is-protected main`) reports `main` as protected, but this project runs `branching_strategy: none`, all earlier plan commits (e.g. 02-09) land on main, and the orchestrator dispatched this quick task explicitly into the main working tree. Commits were therefore made on main as directed.

## Requirements

CFG-04 ("UI is available in English and German") is partially delivered: every string existing today is German. It stays Pending in REQUIREMENTS.md; Phase 3 and 4 strings will be forced into de.json by the parity tests.

## Self-Check: PASSED

- FOUND: custom_components/xmltv_calendar/translations/de.json
- FOUND: tests/test_translations.py
- FOUND: tdd-evidence/su3-red-1.json, su3-red-1.xml, su3-red-2.json, su3-red-2.xml
- FOUND commits: 73cff7b, 449bc80, 7dbdb30, 4345d53 (ancestors of HEAD)
