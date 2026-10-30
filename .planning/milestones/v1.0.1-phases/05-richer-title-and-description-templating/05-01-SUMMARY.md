---
phase: 05-richer-title-and-description-templating
plan: 01
subsystem: templating
tags: [jinja2, sandbox, templates, config-flow, tdd, home-assistant]

requires:
  - phase: 02-precise-filters-preview
    provides: EventTemplates, TemplateError, clean_title/clean_description, advanced flow step and preview
provides:
  - "Pure sandboxed Jinja engine xmltv/template_engine.py (allow-list compile, error vocabulary, regex_replace)"
  - "render.py facade: source-equality EventTemplates, warn-once fallbacks, typed template_values with tz, validate_template"
  - "Double-brace default title template and silent normalization of the stored legacy default"
  - "Formel 1 prefix recipe working through flow, preview, storage and calendar.get_events"
  - "EVT-03, EVT-04 reopened and EVT-10 added; reversed Phase 2 decision recorded"
affects: [05-02 flow texts and translations, 05-03 text filters, 05-04 local time at call sites, 05-05 README]

actuals:
  tokens: 31000
  tasks: 2
  commits: 3
plan_head_before: 5dcaf5d19f96b4335e7e2bc3d62a116a797a2a4d
plan_head_after: 06b9fe8cc1744d70c262df44c59fbf64a400b48e

tech-stack:
  added: []
  patterns:
    - "Explicit AST node allow-list walked before compile (nothing constant-folded or evaluated)"
    - "Compile-time validation of literal regex arguments, reusing the include/exclude caps"
    - "Facade equality on template sources; compiled templates and warn-once holder are compare=False"

key-files:
  created:
    - custom_components/xmltv_calendar/xmltv/template_engine.py
    - tests/xmltv/test_template_engine.py
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-01-red.json
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-01-red.xml
  modified:
    - custom_components/xmltv_calendar/xmltv/render.py
    - custom_components/xmltv_calendar/xmltv/settings.py
    - custom_components/xmltv_calendar/config_flow.py
    - custom_components/xmltv_calendar/matcher.py
    - tests/xmltv/test_render.py
    - tests/xmltv/test_settings.py
    - tests/test_templates.py
    - tests/test_advanced_flow.py
    - .planning/REQUIREMENTS.md
    - .planning/PROJECT.md

key-decisions:
  - "ImmutableSandboxedEnvironment with ChainableUndefined, trim_blocks and lstrip_blocks, pruned filters/tests, empty globals (A2, A5)"
  - "Reject every expression Call and the operators multiply, power, modulo and plus; filters cover every operation (A6, A7)"
  - "Keep the unknown_placeholder error key for undeclared variables so typos like titel are still rejected (A4)"
  - "Hard break without migration: the stored subentry shape and flow VERSION 1 stay; legacy text falls back at read time (A10)"
  - "One render WARNING per EventTemplates (calendar), exception type only, later failures at DEBUG (A11)"

patterns-established:
  - "Engine in a pure module, facade re-exports its names so importers keep working"
  - "Stored-template failure mode: one WARNING with calendar name, kind and reason key, never template or feed text"

requirements-completed: [EVT-03, EVT-04, EVT-10]

coverage:
  - id: D1
    description: "Stored Jinja title template strips the Formel 1 prefix and reaches calendar.get_events, with unchanged UIDs"
    requirement: EVT-03
    verification:
      - kind: integration
        ref: "tests/test_templates.py#test_formula_one_prefix_stripped_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "Add-calendar flow accepts the Jinja template, previews the stripped title, stores the text unchanged"
    requirement: EVT-03
    verification:
      - kind: integration
        ref: "tests/test_templates.py#test_formula_one_template_through_the_calendar_flow"
        status: pass
      - kind: integration
        ref: "tests/test_advanced_flow.py#test_advanced_validation"
        status: pass
    human_judgment: false
  - id: D3
    description: "Sandbox allow-list: loops, macros, includes, calls, heavy operators and pruned filters rejected with the planned reasons; unsafe attributes render empty"
    requirement: EVT-03
    verification:
      - kind: unit
        ref: "tests/xmltv/test_template_engine.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Stored legacy single-brace templates fall back to the default with one WARNING; the exact legacy default is normalized silently"
    requirement: EVT-03
    verification:
      - kind: integration
        ref: "tests/test_templates.py#test_legacy_stored_template_falls_back_with_one_warning"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_settings.py#test_exact_legacy_default_maps_to_the_new_default"
        status: pass
    human_judgment: false
  - id: D5
    description: "Render-time failures fall back to the programme title or default description with one WARNING per calendar and no feed text"
    requirement: EVT-04
    verification:
      - kind: unit
        ref: "tests/xmltv/test_render.py#test_template_that_raises_at_render_falls_back_with_one_warning"
        status: pass
    human_judgment: false
  - id: D6
    description: "REQUIREMENTS.md and PROJECT.md state the reversed decision; EVT-10 added, EVT-03/04/10 mapped to Phase 5"
    requirement: EVT-10
    verification:
      - kind: other
        ref: "grep checks of the Task 2 verify command"
        status: pass
    human_judgment: true
    rationale: "Wording of planning records is a documentation judgment; the grep checks only prove the structural edits"

duration: 11min
completed: 2026-10-23
status: complete
---

# Phase 5 Plan 01: Sandboxed Jinja Title and Description Templates Summary

**Sandboxed Jinja2 engine (node/filter allow-list, literal-regex validation, legacy-syntax fallback) replacing str.format, proven by a Formel 1 prefix template through the flow, preview, storage and calendar.get_events**

## Performance

- **Duration:** 11 min
- **Started:** 2026-10-23T21:18:24Z
- **Completed:** 2026-10-23T21:29:33Z
- **Tasks:** 2 (Task 1 tracer with RED/GREEN, Task 2 records)
- **Files modified:** 20 (including 2 RED evidence files)

## Accomplishments

- New pure module `xmltv/template_engine.py`: `ImmutableSandboxedEnvironment`, allow-list of 27 node classes, pruned filters and tests, empty globals, `compile_template` with length cap, legacy detection, whitelist walk before compile, undeclared-variable check, and the six flow error reasons.
- `render.py` is now a facade: `EventTemplates` equality compares template sources only (a filter-only edit never looks like a template change), `from_mapping(data, name)` falls back with one WARNING for legacy or unusable stored text, `template_values(..., tz=None)` builds the 12 flat typed variables, `validate_template` backs the flow.
- `regex_replace` ships with compile-time validation (text literal, 300-character cap, nested repetition rejected, bad replacement group rejected) reusing the include/exclude caps.
- New default `{{ channel }}: {{ title }}` renders exactly what the old default did; every existing calendar storing the literal `{channel}: {title}` is normalized silently in `with_defaults`.
- Planning records updated: EVT-03 and EVT-04 reopened, EVT-10 added, the Jinja out-of-scope row removed, the key decision recorded.

## Task Commits

1. **Task 1: Tracer (Formel 1 prefix end to end)**, TDD
   - RED: `06f7cf6` (test) - classifier verdict `RED_EVIDENCE_OK`
   - GREEN: `0918894` (feat)
   - REFACTOR: none needed
2. **Task 2: Record the reversed templating decision** - `06b9fe8` (docs)

**Plan metadata:** committed after this file (docs: complete plan)

## TDD Gate Compliance

- **RED:** `tests/test_templates.py::test_formula_one_prefix_stripped_end_to_end` was written against the old engine. JUnit report `tdd-evidence/05-01-red.xml`, record `05-01-red.json`, `gsd_run check tdd-red-evidence` returned `RED_EVIDENCE_OK` (reason `target_test_failed`). Semantic assessment: the target executed and failed on its planned assertion (the `get_events` summary comparison) because the Phase 2 str.format engine treats doubled braces as escaped literals and prints the template text; no import, fixture or syntax fault. Five other migrated or new tests also failed for the same reason; the new `test_template_engine.py` module failed at import, which is expected and was not used as evidence.
- **GREEN:** the same target and the whole suite pass (1151 passed, 1 skipped).
- **REFACTOR:** not needed.
- Gate commits found: `test(05-01)` then `feat(05-01)`.

## Files Created/Modified

- `custom_components/xmltv_calendar/xmltv/template_engine.py` - pure sandboxed engine, reasons, variables, caps, allow-lists, `regex_replace`
- `custom_components/xmltv_calendar/xmltv/render.py` - facade (`EventTemplates`, `template_values`, `validate_template`, `to_event_fields` with `tz`)
- `custom_components/xmltv_calendar/xmltv/settings.py` - new default and `LEGACY_DEFAULT_TITLE_TEMPLATE` normalization
- `custom_components/xmltv_calendar/config_flow.py` - validation through `validate_template`; placeholders filled with the variable names
- `custom_components/xmltv_calendar/matcher.py` - calendar title passed to `from_mapping` at both sites
- `tests/xmltv/test_template_engine.py` (new), `tests/xmltv/test_render.py` (rewritten), `tests/xmltv/test_settings.py`, `tests/test_templates.py`, `tests/test_advanced_flow.py` and the migrated matcher, sensor, retention, reconfigure and preview tests
- `.planning/REQUIREMENTS.md`, `.planning/PROJECT.md` - reversed decision recorded

## Decisions Made

- Followed the plan's assumptions A1 to A12 for this plan's share (A1 length caps, A2 trim/lstrip blocks, A4 `unknown_placeholder` kept, A5 immutable sandbox, A6 and A7 call and operator rejection, A10 no VERSION bump, A11 warn once).
- Documented placement of the regex checks: the first-positional or `find=` argument is validated for both `regex_replace` and the not yet registered `regex_search`, so plan 03 only registers the second function.

## Deviations from Plan

None - plan executed exactly as written.

The skipped-test count differs from the plan's baseline note (1 skipped now, 4 in the plan): the remaining skip is the real-feed check; the others are environment-dependent (`shellcheck`, `bash`, `jq` availability) and unrelated to this plan. The passed count grew from 1025 to 1151.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None - the template compiler, the feed-to-context boundary and the log content are all covered by the plan's threat model (T-05-01 to T-05-06), each with a test.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for plan 05-02. Open follow-up it owns: the new form error keys `unsupported_syntax`, `unknown_filter`, `legacy_placeholder` and `template_runtime_error` have no `en.json`/`de.json` text yet (the flow already emits them), the `title_fields`/`description_fields` placeholders still exist as two names (both carry the same variable list), and `tests/test_translations.py` still lists the reasons by hand instead of iterating `TEMPLATE_ERROR_REASONS`.
- Call sites still pass no `tz` (`calendar.py`, `matcher.describe_match`, `preview.py`): `start` and `end` render in the feed offset until plan 04.

## Self-Check: PASSED

- Created files exist: `template_engine.py`, `test_template_engine.py`, `05-01-red.json`.
- Commits found: `06f7cf6`, `0918894`, `06b9fe8`; evaluation scope resolves with no missing or unreachable files.
- All acceptance criteria re-run: verify command green, baseline greps empty/passing, purity test and manifest guards pass.

---
*Phase: 05-richer-title-and-description-templating*
*Completed: 2026-10-23*
