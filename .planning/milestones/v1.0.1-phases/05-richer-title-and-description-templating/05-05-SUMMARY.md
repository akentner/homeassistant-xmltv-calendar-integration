---
phase: 05-richer-title-and-description-templating
plan: 05
subsystem: documentation
tags: [readme, jinja2, templates, recipes, docs-as-tests, tdd, home-assistant]

requires:
  - phase: 05-richer-title-and-description-templating
    provides: "template_engine ENV, VARIABLE_ORDER and limits; EventTemplates and to_event_fields with tz; local start and end on every surface; en.json template error texts"
provides:
  - "README Templates section: variables, syntax, whitespace, standard and custom filter tables, time directives, limits, form messages, upgrade note, four recipes"
  - "tests/test_readme_recipes.py: every recipe template appears verbatim in the README and renders to its documented result; every registered filter, variable and limit is documented"
  - "STACK.md and .claude/CLAUDE.md describe the sandboxed Jinja engine; FEATURES.md, ARCHITECTURE.md and SUMMARY.md mark the old advice against Jinja as superseded"
affects: [phase 5 verification, future filter or variable additions (the completeness tests force a README update)]

actuals:
  tokens: 11400
  tasks: 3
  commits: 5
plan_head_before: 142093a54b71dec7ae588ce614a58078ad4086ac
plan_head_after: 545d7016b58416ecaa3e3ea7528bf2a9886c1d6d

tech-stack:
  added: []
  patterns:
    - "Docs verified against code: README recipes live in fenced blocks and a test renders each one through the real engine"
    - "Completeness tests derive their expectations from ENV.filters, VARIABLE_ORDER and the MAX_* constants, scoped to one README subsection each"

key-files:
  created:
    - tests/test_readme_recipes.py
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-05-red.json
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-05-red.xml
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-05-red-2.xml
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-05-red-2-recipes.json
    - .planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-05-red-2-completeness.json
  modified:
    - README.md
    - .planning/research/STACK.md
    - .claude/CLAUDE.md
    - .planning/research/FEATURES.md
    - .planning/research/ARCHITECTURE.md
    - .planning/research/SUMMARY.md

key-decisions:
  - "Recipes sit in fenced code blocks, not tables, so the pipe character needs no escaping and the verbatim check compares exact text; filter tables use the existing README convention of an escaped pipe"
  - "The filter column of each table holds the bare backticked name and the signature has its own column, so the completeness test can match the name without ambiguity"
  - "Completeness checks read one README subsection each (Filters, Variables, Limits), not the whole file, so a name mentioned elsewhere does not hide a missing table row"
  - "The README documents the group reference of regex_replace as g<1> in angle form, because Jinja turns a plain backslash-one inside quotes into a control character"

patterns-established:
  - "A new filter or variable fails test_every_registered_filter_is_documented or test_every_variable_is_documented until the README lists it"

requirements-completed: [EVT-03, EVT-04, EVT-10]

coverage:
  - id: D1
    description: "README Templates section with variables, syntax, whitespace, filters, time directives, limits, form messages and the upgrade note for the retired single-brace syntax"
    requirement: EVT-03
    verification:
      - kind: unit
        ref: "tests/test_readme_recipes.py#test_every_registered_filter_is_documented"
        status: pass
      - kind: unit
        ref: "tests/test_readme_recipes.py#test_every_variable_is_documented"
        status: pass
      - kind: unit
        ref: "tests/test_readme_recipes.py#test_limits_are_documented"
        status: pass
    human_judgment: true
    rationale: "Completeness is machine-checked, but whether the prose is clear to a user is a judgment call"
  - id: D2
    description: "Four worked recipes (Formel 1 prefix, first description line as sub-title, conditional sub-title, local start time) appear verbatim in the README and render to the documented results"
    requirement: EVT-04
    verification:
      - kind: unit
        ref: "tests/test_readme_recipes.py#test_recipe_is_documented_verbatim"
        status: pass
      - kind: unit
        ref: "tests/test_readme_recipes.py#test_recipe_renders_as_documented"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Formel 1 recipe and the local-time recipe, stored as calendar templates, return the documented text through calendar.get_events (the latter for a UTC feed under Europe/Berlin)"
    requirement: EVT-10
    verification:
      - kind: integration
        ref: "tests/test_readme_recipes.py#test_formula_one_recipe_end_to_end"
        status: pass
      - kind: integration
        ref: "tests/test_readme_recipes.py#test_local_start_time_recipe_end_to_end"
        status: pass
    human_judgment: false
  - id: D4
    description: "STACK.md and .claude/CLAUDE.md no longer say titles use a restricted formatter and not Jinja; the three research records carry a supersession note"
    requirement: EVT-03
    verification:
      - kind: other
        ref: "! grep -q 'restricted `str.format`' .claude/CLAUDE.md .planning/research/STACK.md && grep -q ImmutableSandboxedEnvironment .claude/CLAUDE.md .planning/research/STACK.md"
        status: pass
    human_judgment: false
  - id: D5
    description: "German UI walkthrough on ha-dev and CI hassfest and HACS validation"
    verification: []
    human_judgment: true
    rationale: "Needs a real Home Assistant instance and the Validate workflow after the user pushes; neither can run here (no podman, the assistant never pushes)"

duration: 5min
completed: 2026-10-23
status: complete
---

# Phase 5 Plan 05: README Templates Section and Stack Notes Summary

**README Templates section (variables, syntax, whitespace, 37 filters, time directives, limits, form messages, upgrade note) with four recipes that a test renders through the real engine, completeness tests that fail when a filter, variable or limit is undocumented, and the stack notes rewritten for the sandboxed Jinja engine**

## Performance

- **Duration:** 5 min
- **Started:** 2026-10-23T21:54:27Z
- **Completed:** 2026-10-23T21:59:30Z
- **Tasks:** 3 (a tracer, a completeness task, a notes-and-gate task)
- **Files modified:** 6 existing files, 1 test file and 5 RED evidence files created

## Accomplishments

- `README.md`: new `### Templates` section between Advanced options and Entities. Subsections: Variables (all 12), Syntax (allowed parts and the rejected list), Whitespace, Filters (28 standard filters in one table, 10 custom ones with use, meaning and example in another), Time directives, Limits, Checking templates (the six form messages in plain words), Upgrading, Recipes. The two Advanced options bullets are short and point at the section; the default title shows in double-brace form.
- `tests/test_readme_recipes.py`: `RECIPES` table, `test_recipe_is_documented_verbatim` (templates and documented results), `test_recipe_renders_as_documented` (parametrized per case), three completeness tests driven by `ENV.filters`, `VARIABLE_ORDER` and the `MAX_*` constants, and two end-to-end tests through `calendar.get_events` (Formel 1 recipe; local-time recipe for a UTC feed under Europe/Berlin).
- `.planning/research/STACK.md` and `.claude/CLAUDE.md`: the TL;DR bullet, the supporting-library row and the Alternatives row now describe `jinja2.sandbox.ImmutableSandboxedEnvironment` with identical wording; HA's `Template` is named as the alternative only for state access. `FEATURES.md`, `ARCHITECTURE.md` and `SUMMARY.md` carry a one-line "Superseded in Phase 5 (D-01, D-02)" note at the passages that advised against Jinja.

## Task Commits

1. **Task 1: Tracer, the Formel 1 recipe documented and rendered by a test** (TDD)
   - RED: `04a91e1` (test), `RED_EVIDENCE_OK`
   - GREEN: `7be9f12` (feat)
2. **Task 2: Complete the Templates section with completeness checks** (TDD)
   - RED: `dcfe004` (test), two records, both `RED_EVIDENCE_OK`
   - GREEN: `cca5f5f` (feat)
3. **Task 3: Stack notes, supersession notes, final gate** - `545d701` (docs)

**Plan metadata:** committed after this file (docs: complete plan)

## TDD Gate Compliance

- **RED (Task 1):** target `test_recipe_is_documented_verbatim`, record `tdd-evidence/05-05-red.json`, `RED_EVIDENCE_OK` (`target_test_failed`). Semantic assessment: the target ran and failed on the planned assertion (`['formula-one-prefix'] == []`) because the README had no recipe; no import or fixture fault. `test_recipe_renders_as_documented` and `test_formula_one_recipe_end_to_end` passed (the engine is complete) and are recorded as guards.
- **RED (Task 2):** two records from `05-05-red-2.xml`. Recipes target `test_recipe_is_documented_verbatim` failed naming the three new recipes (`05-05-red-2-recipes.json`); completeness target `test_every_registered_filter_is_documented` failed listing 37 undocumented filters (`05-05-red-2-completeness.json`). Both `RED_EVIDENCE_OK`. `test_limits_are_documented` also failed on its assertion (five numbers). `test_every_variable_is_documented` already passed because Task 1 had documented all 12 variables, so it is a guard rather than a RED test; the plan expected it to fail, but the Task 1 variables table made that impossible. The end-to-end local-time test passed as a guard.
- **GREEN:** verify command passes after each README step (55 passed with `tests/test_repo_structure.py`); full suite 1264 passed, 1 skipped, 4 deselected.
- **REFACTOR:** not needed.
- Gate commits found: `test(05-05)` precedes `feat(05-05)` for both tasks. Task 3 is a plain `auto` task (docs only).

## Files Created/Modified

- `README.md` - Templates section, shortened Advanced options bullets
- `tests/test_readme_recipes.py` (new) - recipes, verbatim and rendering checks, completeness tests, two end-to-end tests
- `.planning/research/STACK.md`, `.claude/CLAUDE.md` - sandboxed Jinja stack notes
- `.planning/research/FEATURES.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/SUMMARY.md` - supersession notes
- `.planning/phases/05-richer-title-and-description-templating/tdd-evidence/05-05-*` - RED records and JUnit reports

## Decisions Made

- Recipes in fenced code blocks, filter examples in tables with an escaped pipe (the convention the README already uses for filter patterns).
- Bare backticked filter names in their own table column, signature in another, so the completeness check is unambiguous.
- Completeness checks scoped to one subsection each.
- Documented the regex group reference as the angle form of `g<1>` after probing: a plain backslash-one inside a Jinja string becomes a control character and silently breaks the replacement. This is Jinja's own behavior (the same as Home Assistant's `regex_replace`), not a defect of this engine.
- The README states the accepted residual risk T-05-12 plainly, in the Limits section: deliberately crafted templates that grow a text exponentially by reusing a variable with the tilde are not a supported use and are not reachable from feed content.

## Deviations from Plan

None - plan executed exactly as written. Two small additions inside plan scope: the supersession note was added to every passage that advises against Jinja (two in SUMMARY.md, the TS-E2 row and AF-6 in FEATURES.md, the module row and Anti-Pattern 10 in ARCHITECTURE.md), not only the one the plan named per file; and the README states the behavior of the group reference found by probing.

**Total deviations:** 0
**Impact on plan:** none.

## Issues Encountered

- `gsd_run` is not on PATH in the executor shell; it was resolved with the documented resolver snippet saved to a script, and all `gsd_run` calls ran through it.
- The Task 2 behavior note expected `test_every_variable_is_documented` to fail in RED; see TDD Gate Compliance.

## Known Stubs

None.

## Threat Flags

None. T-05-16 (documentation drift) is mitigated by the verbatim, render and completeness tests; T-05-SC holds (no packages added, `requirements` stays empty).

## User Setup Required

None - no external service configuration required.

## Pending Human Steps

1. **German UI walkthrough on ha-dev** (from the plan's `<human-check>`): add a calendar on a real or fixture feed with the Formel 1 recipe as title template and confirm the preview line and the calendar view show the stripped title; set the local-time description recipe and confirm the wall time; restart Home Assistant and confirm that calendars created before this phase (they store the old default) log no template warning; store a custom old-syntax template through the developer tools or the storage file and confirm one warning naming the calendar and the default title in the calendar.
2. **Hassfest and HACS validation** run in the Validate workflow after the user pushes (the assistant never pushes; podman is not installed here). Pending the push.

## Accepted Residual Risk (T-05-12, carried from plan 03)

A hand-crafted template that reuses a set variable many times with the tilde operator can still grow a value exponentially. It needs an HA admin writing it on purpose, is bounded by the template length cap, and cannot be reached from feed content. The README says so in the Limits section.

## Next Phase Readiness

- Phase 5 plans are all executed. Ready for phase verification (`/gsd-verify-work 5`) and the two pending human steps above.

## Self-Check: PASSED

- Files exist: `tests/test_readme_recipes.py`, the five `05-05-*` evidence files, `README.md` with `### Templates`.
- Commits found: `04a91e1`, `7be9f12`, `dcfe004`, `cca5f5f`, `545d701`.
- Acceptance criteria re-run: task verify commands green (55 passed); `grep -q "^### Templates" README.md` succeeds; `regex_replace` appears in the README; `first_line`, `strip_prefix` and `regex_search` lines count 6; `Upgrading` present; the restricted-formatter sentence is gone from both stack files and `ImmutableSandboxedEnvironment` is present in both; `05-CONTEXT.md` counts 3, 2 and 2 in SUMMARY.md, FEATURES.md and ARCHITECTURE.md; `TITLE_FIELDS|DESCRIPTION_FIELDS` and `string.Formatter|_FORMATTER|render_template` print nothing; `tests/xmltv/test_purity.py` and `tests/test_repo_structure.py` pass (45); manifest `requirements` is `[]` with no jinja entry.
- Plan verification: `uv run pytest -q -m "not benchmark"` 1264 passed, 1 skipped; `ruff check .` and `ruff format --check .` clean.

---
*Phase: 05-richer-title-and-description-templating*
*Completed: 2026-10-23*
