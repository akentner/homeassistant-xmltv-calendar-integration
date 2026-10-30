---
phase: 02-precise-filters-preview
plan: 06
subsystem: rendering
tags: [templates, string-formatter, calendar-event, description, preview, tdd]

requires:
  - phase: 02-precise-filters-preview
    provides: "02-02 settings keys KEY_TITLE_TEMPLATE / KEY_DESCRIPTION_TEMPLATE, DEFAULT_TITLE_TEMPLATE, with_defaults; 02-04 entity async_apply_subentry and build_preview"
provides:
  - "xmltv/render.py restricted template engine: TITLE_FIELDS, DESCRIPTION_FIELDS, TemplateError(reason, detail), INVALID_TEMPLATE, UNKNOWN_PLACEHOLDER, compile_template, render_template, clean_title, clean_description, template_values, default_description, EventTemplates.from_mapping, DEFAULT_TEMPLATES"
  - "to_event_fields(programme, channel, templates=DEFAULT_TEMPLATES) with templated summary and description; UID unchanged"
  - "XmltvCalendarEntity._templates, rebuilt in async_apply_subentry; build_events/_to_event take templates"
  - "build_preview renders titles through EventTemplates.from_mapping(data)"
affects: [02-07 flow template validation, 02-08, phase 03 diagnostics]

actuals:
  tokens: 5500
  tasks: 3
  commits: 6
plan_head_before: bff1b0b489f6bcc94016f054afbde8fa51b1c2e9
plan_head_after: 715b889566bdd88abf73da10e74f525b1aa1800b

tech-stack:
  added: []
  patterns:
    - "Template compiled once by string.Formatter().parse into (literal, field) pairs, rendered by join; str.format is never called on user text"
    - "EventTemplates value object shared by entity and preview (one rendering path)"
    - "Stored templates re-validated on load; failure logs one WARNING with the field name only and uses the default"

key-files:
  created:
    - tests/test_templates.py
  modified:
    - custom_components/xmltv_calendar/xmltv/render.py
    - custom_components/xmltv_calendar/calendar.py
    - custom_components/xmltv_calendar/xmltv/preview.py
    - tests/test_calendar.py
    - tests/xmltv/test_render.py
    - tests/xmltv/test_preview.py
    - .ruff.toml

key-decisions:
  - "Description edge cleanup keeps a leading dash or middle dot as a bullet; it strips only whitespace and : , ; | / at the start and all separators at the end (resolves the plan's '- {subtitle}' bullet case against 'strip edge separators')"
  - "A template-only subentry edit rebuilds EventTemplates and writes state without a refilter; a filter change still refilters"
  - "Ruff allowed-confusables en/em dash: they are real title separators in templates and tests"
  - "TemplateError reasons exported as INVALID_TEMPLATE / UNKNOWN_PLACEHOLDER constants for the flow (02-07)"

patterns-established:
  - "Behaviour tests for descriptions go through to_event_fields, not the helper alone"

requirements-completed: [EVT-03, EVT-04]

coverage:
  - id: D1
    description: "Title templates with the six placeholders shape calendar event titles; default '{channel}: {title}' unchanged from Phase 1"
    requirement: EVT-03
    verification:
      - kind: integration
        ref: "tests/test_templates.py#test_title_template_end_to_end"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_render.py#test_title_rendering"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_render.py#test_default_templates_reproduce_phase1_summary"
        status: pass
    human_judgment: false
  - id: D2
    description: "Unknown placeholders, attribute/index access, positional fields, format specs, conversions and malformed braces are rejected; feed text is never parsed as a template"
    requirement: EVT-03
    verification:
      - kind: unit
        ref: "tests/xmltv/test_render.py#test_template_error_reasons"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_render.py#test_feed_text_with_braces_renders_literally"
        status: pass
    human_judgment: false
  - id: D3
    description: "Editing a calendar's templates updates titles in place without refetch; UIDs unchanged"
    requirement: EVT-03
    verification:
      - kind: integration
        ref: "tests/test_templates.py#test_template_edit_applies_in_place"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_render.py#test_uid_ignores_templates"
        status: pass
    human_judgment: false
  - id: D4
    description: "Default description (sub-title, Episode, Categories, blank line, feed description) and optional description template"
    requirement: EVT-04
    verification:
      - kind: integration
        ref: "tests/test_templates.py#test_default_description_end_to_end"
        status: pass
      - kind: integration
        ref: "tests/test_templates.py#test_description_template_end_to_end"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_render.py#test_description_template"
        status: pass
    human_judgment: false
  - id: D5
    description: "Preview titles rendered with the calendar's title template (D-17)"
    requirement: EVT-03
    verification:
      - kind: unit
        ref: "tests/xmltv/test_preview.py#test_preview_uses_title_template"
        status: pass
    human_judgment: false
  - id: D6
    description: "A broken stored template falls back to the default with one WARNING"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_render.py#test_broken_stored_template_falls_back"
        status: pass
    human_judgment: false
  - id: D7
    description: "Templated titles and descriptions read well in the HA calendar UI on a real feed"
    verification: []
    human_judgment: true
    rationale: "Readability of cleaned titles and long descriptions in the calendar dashboard is a visual judgment (plan Flagged Assumptions EVT-03/EVT-04)"

duration: 6 min
completed: 2026-10-15
status: complete
---

# Phase 02 Plan 06: Event Title and Description Templates Summary

**Restricted `{placeholder}` templates compiled once with `string.Formatter().parse` and rendered by joining parts. They shape event titles with D-22 edge cleanup and descriptions with the D-23 default layout. The calendar entity and the flow preview share one `EventTemplates` rendering path.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-15T11:18:56Z
- **Completed:** 2026-10-15T11:25:21Z
- **Tasks:** 3
- **Files modified:** 8 source/test/config files (+6 TDD evidence files)

## Accomplishments
- Title templates accept exactly `{channel}`, `{title}`, `{subtitle}`, `{episode}`, `{category}` and `{channel_id}`. `{description}` is accepted only in description templates. Everything else is rejected with `TemplateError` (`unknown_placeholder` / `invalid_template`). Rendering never calls `str.format`, so format specs, conversions and attribute traversal cannot run (T-02-12).
- The default `{channel}: {title}` reproduces the Phase 1 summary exactly (assumption-delta invariant test). UIDs still hash the raw title.
- The default description puts sub-title, episode and categories into every event. A description template replaces it and keeps its line breaks and leading bullets.
- The entity rebuilds its templates in `async_apply_subentry`. A template-only edit rewrites state with no refetch and no refilter.
- The preview's titles now match the calendar's titles (D-17).
- A broken stored template (hand-edited storage) falls back to the default with one WARNING that names only the field.

## Task Commits

1. **Task 1 (tracer): templated titles in HA**: RED `9eb3698` (test), GREEN `66414b8` (feat). Tracer gate: end-of-phase mode with automated-only verify; re-ran, passed, expanded.
2. **Task 2: validation rules + preview titles**: RED `29420ac` (test), GREEN `0e684f5` (feat)
3. **Task 3: default/templated description + broken-template fallback**: RED `c093105` (test), GREEN `715b889` (feat)

No REFACTOR commits were needed.

## TDD Gate Compliance

| Task | RED record | Verdict | Semantic assessment |
|------|-----------|---------|---------------------|
| 1 | tdd-evidence/02-06-red.json (target `test_title_template_end_to_end`) | RED_EVIDENCE_OK | Failed on the summaries assertion: titles were still `Das Erste: ...`. `test_template_edit_applies_in_place` failed the same way. Setup and entity registration were clean. |
| 2 | tdd-evidence/02-06-red-2-preview.json (target `test_preview_uses_title_template`) | RED_EVIDENCE_OK | Failed on the endswith assertion: the preview line carried the default title. No separate validation record. |
| 3 | tdd-evidence/02-06-red-3.json (target `test_default_description_end_to_end`) | RED_EVIDENCE_OK | Failed on the description assertion after the summary assertion passed. The raw feed description was returned. The pure description rows failed on their assertions. `test_default_description_helper` failed with AttributeError, looked up at call time, so collection stayed clean. |

There was no validation RED record for Task 2 because Task 1 implemented `compile_template` in full per Pattern 8. These rows were already green and act as regression guards:
- every `test_title_rendering` case
- every `test_template_error_reasons` case
- `test_description_placeholder_allowed_in_description_fields`
- `test_feed_text_with_braces_renders_literally`
- `test_uid_ignores_templates`
- `test_default_templates_reproduce_phase1_summary`

These also passed at RED time:
- `test_description_template_end_to_end` (Task 3): `{description}` equals the raw description.
- The title half of `test_broken_stored_template_falls_back` (Task 3).

Every task has a `test(02-06)` commit before its `feat(02-06)` commit.

## Files Created/Modified
- `custom_components/xmltv_calendar/xmltv/render.py`: template engine, cleanup, default description, `EventTemplates`, `to_event_fields(..., templates)`
- `custom_components/xmltv_calendar/calendar.py`: `_to_event` / `build_events` take templates; entity holds `self._templates`, rebuilt on edit
- `custom_components/xmltv_calendar/xmltv/preview.py`: preview titles via `EventTemplates.from_mapping(data)`
- `tests/test_templates.py` (new): end-to-end title, edit-in-place and description tests
- `tests/xmltv/test_render.py`: rendering, validation, UID, invariant, description and fallback tests
- `tests/xmltv/test_preview.py`: `test_preview_uses_title_template`
- `tests/test_calendar.py`: flaky stub takes the templates argument
- `.ruff.toml`: `allowed-confusables = ["–", "—"]`

## Decisions Made
- **Description edge cleanup.** A leading `-`, `–`, `—` or `·` is kept as a bullet. Only whitespace and `: , ; | /` are stripped at the start, and all separators at the end. This was the only way to satisfy both behaviour rows: `- {subtitle}\n- {episode}` keeps its bullets, and `{description}\n\n{category}` / `- {subtitle}\n- {episode}` on an empty programme gives None.
- **Template-only edits** rebuild `EventTemplates` and call `async_write_ha_state` without a refilter. Filter changes still refilter as before.
- **`INVALID_TEMPLATE` / `UNKNOWN_PLACEHOLDER` constants** are exported so the flow (02-07) maps reasons to form errors without string duplication.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ruff RUF001 rejected the en dash in tests**
- **Found during:** Task 1 RED commit
- **Issue:** `select = ["ALL"]` flags `–` as an ambiguous character. It is a required separator in templates (`{title} – {subtitle}`) and in the D-22 separator set.
- **Fix:** Added `allowed-confusables = ["–", "—"]` to `.ruff.toml` `[lint]`, rather than scattering `noqa` comments.
- **Files modified:** .ruff.toml
- **Committed in:** 9eb3698

**2. [Rule 1 - Spec conflict] Description edge stripping vs. leading bullets**
- **Found during:** Task 3
- **Issue:** The plan says "edge separators of the whole text are stripped". The behaviour block also requires `- {subtitle}\n- {episode}` to keep its leading `- `, and `-` is in the separator set.
- **Fix:** Separate start and end patterns. Dash and middle-dot bullets survive at the start; everything else follows the plan.
- **Files modified:** custom_components/xmltv_calendar/xmltv/render.py
- **Verification:** `test_description_template` rows, including `{episode}: {description}` with a dangling `: `
- **Committed in:** 715b889

**3. [Scope] Broken-template fallback landed in Task 1, not Task 3**
- Task 1's `EventTemplates.from_mapping` had to stay non-raising for the entity, so the title fallback and its WARNING were in place from Task 1. Task 3 added the description fallback. The title half of `test_broken_stored_template_falls_back` was green at RED time.

---

**Total deviations:** 3 (1 blocking config fix, 1 spec-conflict resolution, 1 ordering note)
**Impact on plan:** None of these change the plan's outcome. No new packages.

## Issues Encountered
- The Bash tool runs zsh, so an unquoted `$CMD` was not word-split and the first RED run recorded exit code 127 against a stale report. That record was discarded and regenerated from a fresh run through a bash wrapper. The committed record has the real exit code 1 and a fresh report.

## Known Stubs
None.

## Threat Flags
None. T-02-12 and T-02-13 are mitigated and tested. T-02-SC: no packages added.

## Verification
- `uv run pytest -q -m "not benchmark"`: 477 passed, 1 skipped (pre-existing skip)
- `uv run pytest -q -m benchmark`: 4 passed, 1 skipped
- `uv run ruff check . && uv run ruff format --check .`: clean
- `uv run pytest tests/xmltv/test_purity.py -q`: 2 passed
- `grep -v '^\s*#' render.py | grep -cE '\.format(_map)?\('`: 0

## User Setup Required
None. No external service configuration is required.

## Next Phase Readiness
- 02-07 can validate templates in the flow with `compile_template(text, TITLE_FIELDS | DESCRIPTION_FIELDS)` and map `TemplateError.reason` to form errors. `detail` goes into a description placeholder.
- Open UAT question (plan Flagged Assumptions): mid-title dangling separators such as `Tatort –  ()` are not cleaned.

## Self-Check: PASSED
- All 6 task commits are ancestors of HEAD (9eb3698, 66414b8, 29420ac, 0e684f5, c093105, 715b889).
- render.py, tests/test_templates.py and the three RED records exist. All three records re-classify as RED_EVIDENCE_OK.
- evaluation-scope for 02-06 resolves to this plan's commits.

---
*Phase: 02-precise-filters-preview*
*Completed: 2026-10-15*
