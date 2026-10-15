---
phase: 02-precise-filters-preview
plan: 03
subsystem: config-flow
tags: [config-subentry, menu-step, preview, markdown-escaping, executor, tdd]

requires:
  - phase: 02-precise-filters-preview
    provides: "02-02 FilterSpec.from_mapping(data).apply(epg) with stored settings contract (with_defaults)"
  - phase: 01
    provides: "CalendarSubentryFlow form, render.to_event_fields, coordinator.data (EpgData)"
provides:
  - "xmltv/preview.py: PREVIEW_LIMIT, PreviewResult, WEEKDAY_NAMES, escape_markdown, format_line, build_preview"
  - "CalendarSubentryFlow basic -> preview | preview_empty (menu) -> save | back; save only from the preview (D-01)"
  - "translations: config_subentries.calendar.step.basic (renamed from user), preview, preview_empty"
  - "tests/conftest.py complete_calendar_flow(hass, entry, basic) helper for every calendar-creating test"
affects: [02-04, 02-05, 02-06, 02-07, 02-08, reconfigure flow, advanced step, templates]

actuals:
  tokens: 16000
  tasks: 3
  commits: 6
plan_head_before: c968234b2f8cec257e69f5e3315a80e710e846f6
plan_head_after: 6df3fecc98598269fdab286909381f28f68223e5

tech-stack:
  added: []
  patterns:
    - "Menu step as preview: async_show_menu(step_id=preview|preview_empty, menu_options=[save, back]) with description_placeholders"
    - "Every shown step id needs an async_step_<id> handler (HA raises UnknownStep): async_step_preview_empty = async_step_preview"
    - "Optional selectors without default=; form filled via add_suggested_values_to_schema(schema, self._pending | user_input)"
    - "Feed text placed in Markdown descriptions goes through escape_markdown (HTML entities first, then backslash-escapes)"

key-files:
  created:
    - custom_components/xmltv_calendar/xmltv/preview.py
    - tests/xmltv/test_preview.py
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-03-red.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-03-red-2-empty.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-03-red-3-escape.json
  modified:
    - custom_components/xmltv_calendar/config_flow.py
    - custom_components/xmltv_calendar/translations/en.json
    - tests/conftest.py
    - tests/test_tracer.py
    - tests/test_subentry_flow.py
    - tests/test_init.py

key-decisions:
  - "02-03: preview_empty is a separate menu step id (translatable warning) whose handler aliases async_step_preview, because HA requires a handler for every shown step id"
  - "02-03: the subentry still stores only the four Phase 1 keys (channels, channel_regex, include, exclude); later plans extend _pending/_filter_data"
  - "02-03: weekday names keyed by the primary subtag of hass.config.language (de -> Mo..So, anything else -> Mon..Sun); no locale use"
  - "02-03: escape_markdown neutralises & < > as entities, then backslash-escapes \\ ` * _ [ ] # |; parentheses stay (no [ ] means no link)"

patterns-established:
  - "complete_calendar_flow(hass, entry, basic): drive basic -> preview/preview_empty -> save in tests; _submit stays for validation-error tests"

requirements-completed: [FLT-10]

coverage:
  - id: D1
    description: "Adding a calendar shows a preview menu with the match count from now on and the next matches as '<weekday> <dd.mm.> <HH:MM> · <channel> · <title>' in local time; Save creates the calendar without an extra download"
    requirement: FLT-10
    verification:
      - kind: integration
        ref: "tests/test_tracer.py#test_url_source_to_calendar_events"
        status: pass
    human_judgment: false
  - id: D2
    description: "Back returns the pre-filled form; zero matches show the preview_empty warning and still save; save on an unloaded source aborts; a form submit never creates the calendar directly"
    requirement: FLT-10
    verification:
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_back_returns_prefilled_form"
        status: pass
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_empty_preview_still_saves"
        status: pass
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_save_on_unloaded_source_aborts"
        status: pass
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_form_submit_never_creates_directly"
        status: pass
    human_judgment: false
  - id: D3
    description: "Pure preview edges: airing included, stop == now excluded, start == now included, 10-line limit, equal starts in feed order, same filter path as the entity, en/de weekdays, minute truncation, zero padding, missing channel shows its ID, Markdown/HTML escaped"
    requirement: FLT-10
    verification:
      - kind: unit
        ref: "tests/xmltv/test_preview.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "The preview reads well in the real HA frontend (Markdown list rendering of the menu description, escaped characters shown literally)"
    verification: []
    human_judgment: true
    rationale: "Frontend rendering of the menu description (ha-markdown with breaks) is not exercised by any test; check it in ha-dev during phase UAT"

duration: 7min
completed: 2026-10-15
status: complete
---

# Phase 2 Plan 03: Calendar Preview Step Summary

**Calendar subentry flow now goes basic -> preview menu (match count from now on plus the next 10 lines in local HA time, German or English weekdays, escaped feed text) -> Save | Back, with a translatable empty-preview warning. The preview is computed in the executor using the entity's own FilterSpec.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-10-15T10:53:05Z
- **Completed:** 2026-10-15T11:00:39Z
- **Tasks:** 3
- **Files modified:** 14 (incl. 6 TDD evidence files)

## Accomplishments

- `xmltv/preview.py` (pure; no homeassistant import): `build_preview` keeps the `FilterSpec.from_mapping(data).apply(epg)` matches with `stop > now`, counts them and formats the first `limit` (10). The summary comes from `render.to_event_fields`.
- `CalendarSubentryFlow`:
  - `async_step_basic` (aliased as `async_step_user`) stores valid input in `_pending`.
  - `async_step_preview` runs `build_preview` through `hass.async_add_executor_job` and shows the `preview` or `preview_empty` menu.
  - `async_step_save` is the only place that creates the entry. `async_step_back` re-shows the form pre-filled.
  - basic, preview and save each abort with `source_not_loaded` unless the source is LOADED.
- Every test that used to create a calendar in one shot now goes through `complete_calendar_flow`, and four new flow tests cover Back, the empty preview, the unloaded-source abort and "a form submit never creates the calendar".

## Task Commits

1. **Task 1: Tracer: preview of upcoming matches, save from it**: `5109dbf` (test, RED), `9d51d8d` (feat, GREEN)
2. **Task 2: Back, empty preview, unloaded guard; migrate one-shot submits**: `4460a92` (test, RED), `100e543` (feat, GREEN)
3. **Task 3: Safe, localized preview lines; count from now on**: `a6c6e2e` (test, RED), `6df3fec` (feat, GREEN)

No REFACTOR commits were needed.

## TDD Gate Compliance

- **Task 1 RED** (`02-03-red.json`, RED_EVIDENCE_OK / target_test_failed): `test_url_source_to_calendar_events` failed on `assert 'user' == 'basic'`, which is the planned step-id assertion. No collection or fixture fault. GREEN: preview.py plus the multi-step flow. The tracer gate re-ran `<verify>` and passed.
- **Task 2 RED** (`02-03-red-2-empty.json`, RED_EVIDENCE_OK / target_test_failed): `test_empty_preview_still_saves` failed on `assert 'preview' == 'preview_empty'`. It was the only failure among 35 tests. Regression guards that already passed against Task 1: `test_back_returns_prefilled_form`, `test_save_on_unloaded_source_aborts`, `test_form_submit_never_creates_directly`, plus all migrated tests. GREEN: the `preview_empty` step id with its handler alias and translation.
- **Task 3 RED** (`02-03-red-3-escape.json`, RED_EVIDENCE_OK / target_test_failed): `test_markdown_and_html_in_feed_text_are_escaped` failed because the raw feed text appeared in the line. The sibling `test_backslash_and_backtick_are_escaped_and_parentheses_kept` failed for the same missing behaviour. Regression guards: the other 17 preview cases (now edges, limits, feed order, filter path, missing channel ID, en/de/de-CH/DE/fr weekdays, truncation, zero padding). GREEN: `escape_markdown`.

## Files Created/Modified

- `custom_components/xmltv_calendar/xmltv/preview.py`: pure preview (count, lines, weekday tables, escaping)
- `custom_components/xmltv_calendar/config_flow.py`: multi-step `CalendarSubentryFlow` (basic, preview, preview_empty, save, back)
- `custom_components/xmltv_calendar/translations/en.json`: step `user` renamed to `basic`; new `preview` and `preview_empty` steps
- `tests/conftest.py`: `complete_calendar_flow` helper
- `tests/test_tracer.py`: tracer drives basic -> preview -> save and asserts count and lines
- `tests/test_subentry_flow.py`: migrated tests plus four new preview tests
- `tests/test_init.py`: two migrated call sites (unused `SOURCE_USER` import dropped)
- `tests/xmltv/test_preview.py`: 19 pure preview cases

## Decisions Made

See key-decisions in the frontmatter. In short:
- `preview_empty` is its own step id, with a handler alias.
- Only the four Phase 1 keys are stored.
- Weekday names come from the primary language subtag.
- Escaping order: HTML entities first, then Markdown.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] HA rejects a shown step id that has no handler**
- **Found during:** Task 2 GREEN
- **Issue:** Showing the menu with `step_id="preview_empty"` raised `UnknownStep: Handler CalendarSubentryFlow doesn't support step preview_empty`. The data_entry_flow manager checks that `async_step_<step_id>` exists for every returned form or menu.
- **Fix:** Added `async_step_preview_empty = async_step_preview`. Menu choices still route through `next_step_id`, so the alias only satisfies the check.
- **Files modified:** custom_components/xmltv_calendar/config_flow.py
- **Verification:** full suite passes (366 passed)
- **Committed in:** 100e543

**2. [Rule 1 - Bug] The behaviour-block inputs of test_back_returns_prefilled_form match nothing in the test feed**
- **Found during:** Task 2 GREEN
- **Issue:** On MOTORSPORT_FEED, `include "formel"` plus `exclude "rennen"` matches zero programmes: ZDF has "Formula 1 Highlights" and Das Erste has "Formel 1: Rennen". The resubmit therefore reached `preview_empty`, not the expected `preview`.
- **Fix:** Changed include to `"formula"` (with a comment) so the resubmit lands on `preview`. Name, channels, channel_regex and exclude are as planned.
- **Files modified:** tests/test_subentry_flow.py
- **Committed in:** 100e543

**3. [Rule 3 - Blocking] Ruff ALL rules on the planned build_preview signature**
- **Found during:** Task 1 GREEN
- **Issue:** The planned six-parameter positional signature trips PLR0913/PLR0917. `async_add_executor_job` only passes positional arguments.
- **Fix:** Added `# noqa: PLR0913, PLR0917` with the reason, and used `split("-", maxsplit=1)` (PLC0207).
- **Committed in:** 9d51d8d

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 test bug). **Impact:** none on scope. Behaviour matches the plan.

## Issues Encountered

None beyond the deviations.

## Verification

- `uv run pytest -q -m "not benchmark"`: 366 passed, 1 skipped, 4 deselected
- `uv run ruff check . && uv run ruff format --check .`: clean
- `podman run --rm -v "$PWD":/github/workspace:ro,Z ghcr.io/home-assistant/hassfest`: Integrations 1, invalid 0 (translations valid)
- Acceptance greps all pass:
  - `async_step_user = async_step_basic` is present.
  - `async_add_executor_job` appears within 6 lines of `async_step_preview`.
  - en.json has `basic`, `preview` and `preview_empty` with save/back, and no longer has `user`.
  - `complete_calendar_flow` count is 3 in test_init.py and 6 in test_subentry_flow.py.
  - `setlocale` count is 0.
  - `def escape_markdown` is present.
  - The purity test passes.

## User Setup Required

None.

## Next Phase Readiness

- 02-04 and 02-06 extend `_pending`/`_filter_data` and the preview title (template, time zone). `build_preview` already takes the stored data mapping, so the preview stays on the entity's match path.
- The reconfigure flow can reuse `async_step_basic` and the preview. `async_step_save` must branch to `async_update_and_abort` when `self.source != SOURCE_USER` (RESEARCH Pattern 6).

## Self-Check: PASSED

- All six created files exist (preview.py, test_preview.py, three RED records, plus modified conftest).
- All six commits (5109dbf, 9d51d8d, 4460a92, 100e543, a6c6e2e, 6df3fec) are ancestors of HEAD.
- No commit deleted any tracked file.
