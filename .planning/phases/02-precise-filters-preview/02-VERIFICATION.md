---
phase: 02-precise-filters-preview
verified: 2026-10-15T11:56:38Z
status: gaps_found
score: 83/85 must-haves verified
covered_files: [".planning/phases/02-precise-filters-preview/02-01-PLAN.md", ".planning/phases/02-precise-filters-preview/02-01-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-02-PLAN.md", ".planning/phases/02-precise-filters-preview/02-02-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-03-PLAN.md", ".planning/phases/02-precise-filters-preview/02-03-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-04-PLAN.md", ".planning/phases/02-precise-filters-preview/02-04-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-05-PLAN.md", ".planning/phases/02-precise-filters-preview/02-05-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-06-PLAN.md", ".planning/phases/02-precise-filters-preview/02-06-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-07-PLAN.md", ".planning/phases/02-precise-filters-preview/02-07-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-08-PLAN.md", ".planning/phases/02-precise-filters-preview/02-08-SUMMARY.md", ".ruff.toml", "custom_components/xmltv_calendar/__init__.py", "custom_components/xmltv_calendar/calendar.py", "custom_components/xmltv_calendar/config_flow.py", "custom_components/xmltv_calendar/const.py", "custom_components/xmltv_calendar/translations/en.json", "custom_components/xmltv_calendar/xmltv/filter.py", "custom_components/xmltv_calendar/xmltv/parser.py", "custom_components/xmltv_calendar/xmltv/preview.py", "custom_components/xmltv_calendar/xmltv/render.py", "custom_components/xmltv_calendar/xmltv/settings.py", "custom_components/xmltv_calendar/xmltv/window.py", "tests/conftest.py", "tests/test_advanced_flow.py", "tests/test_calendar.py", "tests/test_filtering.py", "tests/test_init.py", "tests/test_reconfigure.py", "tests/test_subentry_flow.py", "tests/test_templates.py", "tests/test_tracer.py", "tests/xmltv/test_filter.py", "tests/xmltv/test_parser.py", "tests/xmltv/test_preview.py", "tests/xmltv/test_render.py", "tests/xmltv/test_settings.py", "tests/xmltv/test_window.py"]
covered_digest: "v3:sha256:7193f23df268604451a3df1df62617db9704102503eb3e47ebf4c75b187e9937"
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "A stored pattern that does not compile (hand-edited storage) makes only that calendar keep its previous matches and logs a WARNING naming the calendar; other calendars changed in the same listener call are still updated (02-01 truth 6, T-02-01)"
    status: failed
    reason: "Only re.error is caught. A pattern whose repeat count is too large (e.g. 'a{99999999999}', 14 chars, under the 300-char cap) makes re.compile raise OverflowError. Reproduced in a scratch copy: the copy of test_corrupt_pattern_keeps_previous_matches with this pattern fails. The update listener raises ('Task exception was never retrieved'), no WARNING is logged, and the sibling calendar B is not updated. The same exception from XmltvCalendarEntity.__init__ breaks calendar-platform setup for every calendar of the source. The same root cause (review CR-01) also lets the pattern crash the calendar form with 'Unknown error' instead of invalid_regex."
    artifacts:
      - path: "custom_components/xmltv_calendar/calendar.py"
        issue: "_build_spec (line 51-57) catches only re.error; OverflowError propagates out of __init__ and async_apply_subentry"
      - path: "custom_components/xmltv_calendar/xmltv/filter.py"
        issue: "first_invalid_pattern (line 182-185) catches only re.error; OverflowError escapes the basic-step validation"
    missing:
      - "Catch (re.error, OverflowError, RecursionError) in first_invalid_pattern and map it to InvalidPattern(message=str(err))"
      - "Catch the same set in calendar._build_spec, so the bad calendar keeps its matches and logs the WARNING"
      - "Regression tests: 'a{99999999999}' in the basic form gives invalid_regex; the same pattern in stored subentry data during a listener call and at platform setup"
human_verification:
  - test: "ha-dev UAT walkthrough steps 1-9 from 02-08-SUMMARY.md (Add calendar form, Advanced step widgets/help texts, 22:00-02:00 window + weekday + '{title} – {subtitle}' preview incl. German weekday names, Back keeps values + Save matches preview, Edit calendar pre-checked + in-place update without download, uncheck keeps advanced values, '^(\\w+\\s?)+$' rejected, empty-preview warning still saves, logs clean)"
    expected: "Every step behaves as written in 02-08-SUMMARY.md 'UAT Walkthrough'; additionally, at step 5, note what the success dialog after 'Edit calendar' -> Save shows (WR-02: no reconfigure_successful translation)"
    why_human: "No frontend in phcc: selector rendering, translated labels, menu buttons, Markdown preview and live logs need the real UI (02-08 human-check, human_verify_mode end-of-phase)"
  - test: "02-03 D4: open a preview whose feed contains Markdown/HTML characters in channel names or titles"
    expected: "The preview list renders as a Markdown list; *, _, [, <, & and backticks show literally (note: '~~x~~' renders struck through, review IN-04)"
    why_human: "ha-markdown rendering of the menu description is not exercised by any test"
  - test: "Backstop truth (02-02): executor threads filtering several calendars at the same time cannot change each other's matches; a case_sensitive flag on one calendar never affects another"
    expected: "Accept on structure: FilterSpec is a frozen dataclass, patterns compiled per calendar in from_mapping, EpgData immutable; or request a concurrency test"
    why_human: "verification: backstop -> insufficient_spec. Only presence evidence exists (filter.py:212-244, test_field_selection_does_not_leak_between_specs is sequential, not concurrent)"
  - test: "Judgment-tier prohibitions (non-authoritative LLM verdict: all three hold). Confirm: (a) 02-02 no programme-specific matching logic; (b) 02-02 no change to a user's pattern beyond NFC (no case-folding, escaping, anchoring); (c) 02-03 the preview's match set and titles equal the saved calendar's"
    expected: "(a) 'formel'/'Tatort' appear only as help-text examples in translations/en.json:76,79; (b) filter.py _lines/compile_patterns only strip and NFC-normalize each line; (c) preview.py build_preview uses FilterSpec.from_mapping(data).apply(epg, tz=tz) and EventTemplates.from_mapping(data), the same calls as calendar.py, with the same dt_util.get_default_time_zone()"
    why_human: "Judgment-tier prohibitions need explicit human resolution (ADR-550 D4)"
---

# Phase 2: Precise Filters & Preview Verification Report

**Phase Goal:** User can pinpoint specific shows with field-scoped, Unicode-safe regex plus duration and time-window filters, shape event title and description via templates, check the result in a live preview before saving, and retune any calendar instantly without touching the source.
**Verified:** 2026-10-15T11:56:38Z
**Status:** gaps_found
**Re-verification:** No (initial verification)
**Mode:** mvp (ROADMAP). The goal is a capability statement, not a user story (`user-story.validate` returns `valid: false`), and no phase 2 plan restates it as one. Following the Phase 1 precedent, verification uses the goal text and the five roadmap Success Criteria. Strict MVP framing would need `/gsd-mvp-phase 2`.

## User Flow Coverage

| Step | Expected | Evidence | Status |
|------|----------|----------|--------|
| Open "Add calendar" | Basic form with name, channels, regex fields, "Advanced options" checkbox | config_flow.py:356-408; tests/test_subentry_flow.py | ✓ (render: human) |
| Check "Advanced options" | Field scopes, case toggle, window, weekdays, durations, templates | config_flow.py:242-257, 414-439; tests/test_advanced_flow.py::test_advanced_options_end_to_end | ✓ (render: human) |
| Submit | Preview: count plus up to 10 lines `<wd> <dd.mm.> <HH:MM> · <channel> · <title>` | config_flow.py:441-463 → preview.py:build_preview; tests/xmltv/test_preview.py (15 tests) | ✓ |
| Back / Save | Back refills the form; Save creates the calendar | config_flow.py:468-484; test_back_returns_prefilled_form, test_back_keeps_advanced_values | ✓ |
| Calendar shows matches | Only programmes passing every constraint, templated titles, default description | calendar.py:187-213, 99-104; tests/test_filtering.py, tests/test_templates.py | ✓ |
| "Edit calendar" → change → Save | Updated events in place: no download, no parse, no reload, siblings untouched | config_flow.py:412, 478; __init__.py:32-51; test_reconfigure_flow_end_to_end | ✓, with a ✗ edge (stored OverflowError pattern breaks the listener, see Gaps) |

## Goal Achievement

### Observable Truths: Roadmap Success Criteria

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | Include and exclude field scopes set separately; case-insensitive by default with a toggle; umlauts match in NFC and NFD | ✓ VERIFIED | filter.py:191-205, 235-239 (separate `include_fields`/`exclude_fields`, `_flags`), parser.py:56-58 + filter.py:120-122 (NFC on both sides); test_umlaut_pattern_matches_decomposed_feed, test_category_field_selection_end_to_end, test_field_and_case_table, test_unicode_matching |
| SC2 | Min/max duration, time-of-day window (also across midnight), weekdays; every constraint must pass | ✓ VERIFIED | filter.py:84-117 (TimeWindow.anchor_date), 252-268, 275-299; calendar.py:200-202 (HA time zone); test_friday_night_window_end_to_end (Berlin + New York), test_duration_bounds, test_duration_across_dst_fall_back, test_every_constraint_must_pass |
| SC3 | Before saving, the flow shows match count and next ~10 matches with channel and start time | ✓ VERIFIED | preview.py:356-375 (PREVIEW_LIMIT 10, stop > now), config_flow.py:447-463 (executor, menu save/back), en.json preview/preview_empty; test_count_and_line_limit, test_form_submit_never_creates_directly, test_empty_preview_still_saves. Frontend rendering routed to human |
| SC4 | Title template with the six placeholders; optional description template; unknown placeholders rejected; default description shows sub-title, episode, categories, description | ✓ VERIFIED | render.py:20-21, 61-77 (format specs, conversions, `.`/`[` rejected), 96-108, 133-158; config_flow.py:307-316; test_title_template_end_to_end, test_default_description_end_to_end, test_description_template_end_to_end, test_template_error_reasons, test_unknown_placeholder_names_the_offending_text |
| SC5 | Reconfigure all filters and templates of a calendar; updated events with no re-download, no re-parse, no reload of sibling calendars | ✓ VERIFIED (with warnings) | config_flow.py:412 (`async_step_reconfigure = async_step_basic`), 478 (`async_update_and_abort`), __init__.py:32-51 (diffing listener, reload only on source change), calendar.py:219-253; test_reconfigure_flow_end_to_end, test_data_change_applies_in_place and test_template_edit_applies_in_place assert `call_count` unchanged, `runtime_data is runtime`, `coordinator.data is epg`, `calendars[b_id] is entity_b`. Warnings: WR-01, WR-03 (see Anti-Patterns) |

### Observable Truths: Plan must_haves (80)

| Plan | Truths | Status | Notes |
|------|--------|--------|-------|
| 02-01 (FLT-11 in place) | 9 | 8 ✓, 1 ✗ | #6 (stored non-compiling pattern) is **FAILED** for OverflowError patterns, reproduced (see Gaps). #1-5 and #7-9: test_data_change_applies_in_place, test_title_change_renames_device, test_unchanged_update_is_a_no_op, test_two_calendars_changed_together, test_last_of_two_updates_wins (generation counter, behavioral), test_apply_before_added_stores_settings, test_queries_near_datetime_min_do_not_overflow; Phase 1 reload test in test_init.py |
| 02-02 (NFC, fields, case, settings) | 13 | 12 ✓, 1 ⚠ insufficient_spec | #13 is `verification: backstop` (concurrency); only presence evidence, so it goes to human. All others are covered by test_parser.py::test_text_is_nfc_and_ids_are_untouched, test_filter.py tables, test_settings.py (idempotency, tolerant read), test_filtering.py end-to-end |
| 02-03 (preview) | 10 | 10 ✓ | test_preview.py boundary/precision/escaping/language tests; test_subentry_flow.py flow tests; executor call at config_flow.py:447 |
| 02-04 (duration/window/weekday) | 13 | 13 ✓ | test_window_and_weekday_table (DST nights), test_duration_bounds, test_absurd_stop_hidden_by_max_duration, test_nested_repetition_table, test_preview_uses_window_in_given_tz |
| 02-05 (edit flow) | 8 | 8 ✓ | test_reconfigure.py: end_to_end, phase1_calendar_edit_keeps_events, missing_channel_stays_selectable, rename_via_edit_flow, edit_to_empty_filters_shows_all, edit_on_unloaded_source_aborts |
| 02-06 (templates) | 11 | 11 ✓ | test_render.py (15), test_templates.py (4), test_uid_ignores_templates, test_broken_stored_template_falls_back, test_preview_uses_title_template |
| 02-07 (advanced step) | 8 | 8 ✓ | test_advanced_flow.py (advanced_options_end_to_end, advanced_validation, cleared_time_window_is_stored_as_none_on_edit); `advanced` never stored because with_defaults drops unknown keys (settings.py:401-426) |
| 02-08 (edit + advanced, gate) | 8 | 8 ✓ | test_advanced_checkbox_prechecked_on_edit, test_unchecking_advanced_keeps_stored_values, test_back_keeps_advanced_values, test_case_sensitive_in_flow, test_nested_repetition_rejected_in_form, test_translation_placeholders_are_provided; gate re-run by the verifier (below) |

**Score:** 83/85 truths verified (5/5 roadmap SC, 78/80 plan truths). 1 FAILED, 1 insufficient_spec (backstop, human), 0 present-but-behavior-unverified.

### Required Artifacts

`verify.artifacts` across all 8 plans: **30/30 passed** (exist, substantive, contain the expected markers).

| Artifact | Status | Details |
|----------|--------|---------|
| xmltv/settings.py | ✓ VERIFIED | with_defaults, has_advanced, normalize_time; used by filter, render, config_flow |
| xmltv/filter.py | ✓ VERIFIED (gap) | TimeWindow, durations, weekdays, nested-repetition guard; OverflowError gap in first_invalid_pattern |
| xmltv/parser.py | ✓ VERIFIED | `_text` NFC-normalizes all element text; ids stripped only |
| xmltv/preview.py | ✓ VERIFIED | build_preview, format_line, escape_markdown |
| xmltv/render.py | ✓ VERIFIED | EventTemplates, compile_template, default_description |
| xmltv/window.py | ✓ VERIFIED | `_lower` OverflowError clamp |
| calendar.py | ✓ VERIFIED (gap) | async_apply_subentry, differs_from, templates; `_build_spec` OverflowError gap |
| __init__.py | ✓ VERIFIED | single diffing update listener |
| config_flow.py | ✓ VERIFIED | basic → advanced → preview → save/back, reconfigure alias |
| const.py, translations/en.json | ✓ VERIFIED | CONF_ADVANCED, advanced step texts, selectors; missing `reconfigure_successful` abort text (WR-02) |

### Key Link Verification

`verify.key-links` across all 8 plans: **16/16 verified**. Spot-checked by reading the code: listener → `entity.async_apply_subentry(subentry)` (__init__.py:44); entity → `partial(self._spec.apply, epg, tz=dt_util.get_default_time_zone())` (calendar.py:200-202); flow → `async_add_executor_job(build_preview, ...)` (config_flow.py:447); preview → `FilterSpec.from_mapping` + `EventTemplates.from_mapping` (preview.py:366-367); save → `async_update_and_abort` (config_flow.py:478); `_load_pending` → `has_advanced` (config_flow.py:349).

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| Calendar entity events | `self._index` | `coordinator.data` (parsed feed) → `FilterSpec.apply` in executor | Yes | ✓ FLOWING |
| Preview placeholders | `count`, `matches` | `entry.runtime_data.coordinator.data` → `build_preview` | Yes | ✓ FLOWING |
| Edit form suggestions | `pending` | `with_defaults(subentry.data)` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite (run once) | `uv run pytest tests -q` | 505 passed, 1 skipped, 40 s | ✓ PASS |
| Lint/format | `ruff check .` / `ruff format --check .` | clean, 48 files | ✓ PASS |
| hassfest | `podman run ... ghcr.io/home-assistant/hassfest` | Integrations 1, invalid 0 | ✓ PASS |
| Overflow pattern in form validation | `first_invalid_pattern("a{99999999999}")` | raises OverflowError | ✗ FAIL |
| Overflow pattern in stored data (listener) | scratch copy of test_corrupt_pattern_keeps_previous_matches with `a{99999999999}` | listener task exception, 0 warnings, sibling not updated | ✗ FAIL |
| Fixed-count inner repeat | `first_invalid_pattern(r"(\d{2}:)+")`, `r"^(\d{2}\.){2}"` | rejected as nested repetition | ⚠ WARN (WR-03) |
| Accepted patterns | `first_invalid_pattern(r"(formel\|formula)\s*1")` | None | ✓ PASS |

### Probe Execution

Step 7c: no probes are declared, and the repo has no `scripts/*/tests/probe-*.sh`. Not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FLT-05 | 02-02, 02-07 | Separate field scopes for include/exclude | ✓ SATISFIED | SC1 evidence |
| FLT-06 | 02-02, 02-07, 02-08 | Case toggle, Unicode-normalization-safe umlauts | ✓ SATISFIED | SC1 evidence |
| FLT-08 | 02-04, 02-07 | Min/max duration | ✓ SATISFIED | SC2 evidence |
| FLT-09 | 02-04, 02-07 | Time window across midnight, weekdays | ✓ SATISFIED | SC2 evidence |
| FLT-10 | 02-03, 02-07, 02-08 | Preview with count and next ~10 matches | ✓ SATISFIED (render: human) | SC3 evidence |
| FLT-11 | 02-01, 02-05, 02-08 | Edit all filters without re-download/re-parse | ✓ SATISFIED with gap | Main path verified (SC5); hand-edited OverflowError pattern breaks the in-place listener (gap) |
| EVT-03 | 02-06, 02-07 | Title template, unknown placeholders rejected | ✓ SATISFIED | SC4 evidence |
| EVT-04 | 02-06, 02-07 | Default description plus description template | ✓ SATISFIED | SC4 evidence |

All 8 phase IDs are claimed by at least one plan. REQUIREMENTS.md maps no other ID to Phase 2, so there are no orphans. FLT-07 (Phase 1) is affected by CR-01, a pre-existing gap: `a{99999999999}` is not rejected with an error, it crashes the form.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| xmltv/filter.py | 182-185 | `except re.error` only (CR-01) | 🛑 Blocker | Form shows "Unknown error"; this is the 02-01 truth 6 gap |
| calendar.py | 109-113 | `except re.error` only (CR-01) | 🛑 Blocker | Platform setup / listener crash for every calendar of the source |
| config_flow.py | 405 | `pending \| (user_input or {})` on error path (WR-01) | ⚠️ Warning | In an edit, a cleared field comes back as a suggestion after a validation error; re-saving restores the old value. It is visible in the form, but it undermines "retune instantly" on that path |
| xmltv/filter.py | 142 | `unbounded = high > 1` (WR-03) | ⚠️ Warning | `(\d{2}:)+` and `^(\d{2}\.){2}` are rejected; a Phase 1 calendar with such a pattern cannot be saved unchanged in the edit flow |
| translations/en.json | 138-140 | no `reconfigure_successful` abort text (WR-02) | ⚠️ Warning | The success dialog after every edit has no text; the save itself works. Check in UAT step 5 |
| config_flow.py | 316, 376-377 | shared `template_error` / `pattern` placeholder (WR-04) | ℹ️ Info | The second invalid field shows the first field's detail |

No TBD, FIXME or XXX markers in the phase files. The "PLACEHOLDER" grep hits are identifiers, not debt markers.

### Human Verification Required

These are listed in the frontmatter `human_verification`. They are deferred until the gap is closed:

1. **ha-dev UAT walkthrough (9 steps, 02-08-SUMMARY.md):** check the form, advanced step, preview, Back, edit, unchecking, nested repetition, empty preview and logs. At step 5, also note what the edit success dialog shows (WR-02).
2. **Preview Markdown rendering (02-03 D4):** feed text with special characters must render literally.
3. **Backstop concurrency truth (02-02):** accept it on structure, or ask for a concurrency test.
4. **Three judgment-tier prohibitions:** the LLM verdict (non-authoritative) is that all hold. They need human confirmation.

### Gaps Summary

There is one root cause (review CR-01). `re.compile` raises `OverflowError`, not `re.error`, for repeat counts of 2^32-1 or more. The code catches only `re.error` in two places:

- **Flow:** `first_invalid_pattern` lets the exception escape. The calendar form crashes with "Unknown error" instead of showing `invalid_regex`.
- **Entity:** `_build_spec` lets the same exception escape. The declared must-have "a stored pattern that does not compile keeps only that calendar on its previous matches, logs a WARNING, and still updates the other calendars" is false for this class of pattern. The listener aborts, siblings later in the loop are not updated, and at setup the whole calendar platform of the source fails.

Reproduced deterministically with a variant of the phase's own `test_corrupt_pattern_keeps_previous_matches`. The fix is two `except` tuples plus regression tests. No later phase covers it, so nothing is deferred.

**Recommended for the same gap-closure round** (warnings, not blocking on their own; both touch the "retune any calendar" promise):

- **WR-01:** after a validation error, use only `user_input` as suggestions in the basic step.
- **WR-03:** treat `{n}` (min == max) as a fixed count in `_nested_repeat`.
- **WR-02:** add the `reconfigure_successful` abort text.

---

_Verified: 2026-10-15T11:56:38Z_
_Verifier: Claude (gsd-verifier)_
