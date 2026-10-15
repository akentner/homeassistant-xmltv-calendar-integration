---
phase: 02-precise-filters-preview
reviewed: 2026-10-15T11:50:42Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - custom_components/xmltv_calendar/__init__.py
  - custom_components/xmltv_calendar/calendar.py
  - custom_components/xmltv_calendar/config_flow.py
  - custom_components/xmltv_calendar/const.py
  - custom_components/xmltv_calendar/translations/en.json
  - custom_components/xmltv_calendar/xmltv/filter.py
  - custom_components/xmltv_calendar/xmltv/parser.py
  - custom_components/xmltv_calendar/xmltv/preview.py
  - custom_components/xmltv_calendar/xmltv/render.py
  - custom_components/xmltv_calendar/xmltv/settings.py
  - custom_components/xmltv_calendar/xmltv/window.py
  - .ruff.toml
  - tests/conftest.py
  - tests/test_advanced_flow.py
  - tests/test_calendar.py
  - tests/test_filtering.py
  - tests/test_init.py
  - tests/test_reconfigure.py
  - tests/test_subentry_flow.py
  - tests/test_templates.py
  - tests/test_tracer.py
  - tests/xmltv/test_filter.py
  - tests/xmltv/test_parser.py
  - tests/xmltv/test_preview.py
  - tests/xmltv/test_render.py
  - tests/xmltv/test_settings.py
  - tests/xmltv/test_window.py
findings:
  critical: 1
  warning: 4
  info: 6
  total: 11
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-10-15T11:50:42Z
**Depth:** standard
**Files Reviewed:** 27
**Status:** issues_found

## Summary

I reviewed the Phase 2 diff (`git diff 5a8952e HEAD`): the advanced filters (fields, case, time window, weekdays, duration), title and description templates, the preview step, and in-place reconfigure.

- Baseline: `uv run pytest tests` gives 505 passed, 1 skipped. `ruff check .` is clean.
- The filter, window, settings normalisation and template sandboxing are solid. Template compilation correctly rejects attribute/index access, conversions and format specs.
- I reproduced CR-01 and WR-01 with throwaway tests in a scratch copy of the repo. The repo itself was not modified.

Key concerns:

- **CR-01:** A user-typed regex escapes pattern validation and crashes the flow handler.
- **WR-01:** The basic step brings cleared fields back after a validation error. This is a Phase 2 regression.
- **WR-02:** The edit flow's success abort has no translation.
- **WR-03:** The new nested-repetition guard rejects harmless fixed-count patterns, including stored Phase 1 patterns on edit.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `OverflowError` from `re.compile` escapes pattern validation and crashes the flow (and entity setup)

**File:** `custom_components/xmltv_calendar/xmltv/filter.py:182-185`, `custom_components/xmltv_calendar/calendar.py:51-57`

**Issue:** `first_invalid_pattern` only catches `re.error`. A pattern with a repeat count of 2^32 - 1 or more raises `OverflowError: the repetition number is too large` from `re.compile`, for example `a{99999999999}` (13 characters, well under the 300-character cap). Reproduced in a scratch probe: submitting `{"name": "X", "include": "a{99999999999}"}` to the basic step raised `OverflowError` out of `async_configure`. The user gets an "Unknown error" and a traceback in the log instead of the `invalid_regex` form error.

The same gap is in `_build_spec` (`calendar.py:55`), which also catches only `re.error`. If such a pattern ever reaches storage (hand-edited `.storage`, the case T-02-01 is meant to cover), `FilterSpec.from_mapping` raises inside `XmltvCalendarEntity.__init__`. That breaks `async_setup_entry` of the calendar platform for **every** calendar of the source, not just the bad one. Inside `async_apply_subentry`, it raises out of the update listener. The `invalid_regex` check itself predates Phase 2, but Phase 2 changed both functions without closing the gap.

**Fix:**
```python
# filter.py, first_invalid_pattern
        try:
            re.compile(line, flags)
        except (re.error, OverflowError, RecursionError) as err:
            return InvalidPattern(pattern=line, message=getattr(err, "msg", None) or str(err))

# calendar.py, _build_spec
    try:
        return FilterSpec.from_mapping(data)
    except (re.error, OverflowError, RecursionError):
        _LOGGER.warning("Calendar %s: stored filter pattern is invalid", name)
        return None
```
Add a regression test with `a{99999999999}` in the basic form and in stored subentry data.

## Warnings

### WR-01: Basic step brings cleared fields back after a validation error

**File:** `custom_components/xmltv_calendar/config_flow.py:405`

**Issue:** On a validation error the form is rebuilt with `pending | (user_input or {})`. A field the user cleared is missing from `user_input`; the code itself treats a missing key as "cleared" (line 379). So the merge refills that field with its old pending value as the suggested value. Reproduced: edit a calendar stored with `exclude: "old-exclude"`, clear Exclude, and submit an invalid include. The re-shown form suggests `exclude = "old-exclude"`. When the user fixes the include and submits, the old exclude is saved again, silently undoing their edit.

This applies to channels, channel regex, include and exclude on every edit, and on any new-calendar flow after Back. Phase 1 used only `user_input` on the error path, so this is a regression. The advanced step already handles it correctly (line 432); `test_input_is_kept_after_a_validation_error` only covers a full submission, not a cleared field.

**Fix:**
```python
        # After an error, show exactly what was submitted (cleared fields stay cleared), like the advanced step
        suggestions = user_input if user_input is not None else pending
        schema = self.add_suggested_values_to_schema(schema, suggestions)
```
Add a reconfigure test: clear `exclude`, submit an invalid `include`, and assert `exclude` has no suggested value.

### WR-02: Missing `reconfigure_successful` abort translation for the calendar edit flow

**File:** `custom_components/xmltv_calendar/translations/en.json:138-140` (used by `config_flow.py:478`)

**Issue:** `async_update_and_abort` ends the edit flow with the default reason `reconfigure_successful`, and five tests assert that reason. But `config_subentries.calendar.abort` only defines `source_not_loaded`. The `[%key:common::...%]` references used by core integrations are not resolved for a custom integration's `translations/en.json`, so the key must be spelled out. Without it, the frontend has no text for the success dialog after every calendar edit and falls back to the raw reason or an empty message. No test catches missing translations: phcc does not enable HA core's translation check.

**Fix:**
```json
      "abort": {
        "source_not_loaded": "The source is not loaded. Wait until it has been downloaded, then try again.",
        "reconfigure_successful": "The calendar was updated."
      }
```

### WR-03: Nested-repetition guard rejects harmless fixed-count repeats, which blocks saving Phase 1 calendars unchanged

**File:** `custom_components/xmltv_calendar/xmltv/filter.py:141-143`

**Issue:** `unbounded = high > 1` treats any repeat with a maximum above 1 as variable, including exact counts such as `{2}`. Probe results:

- `(\d{2}:)+` and `(a{2})+` → rejected as "nested repetition can be very slow".
- Date/time patterns like `^(\d{2}\.){2}` → also rejected.

A fixed-count inner repeat (`min == max`) cannot cause catastrophic backtracking.

On edit, the basic step re-validates the stored include/exclude/channel-regex lines. A Phase 1 calendar whose pattern passed the old validator can now no longer be saved, not even unchanged, until the user rewrites a pattern that worked before. At runtime the pattern still compiles and matches, so the flow and the entity disagree about validity.

**Fix:** Only treat a repeat as variable when its count can vary:
```python
            low, high, body = av
            variable = high > 1 and high != low  # {n} is a fixed count, not ambiguous
            if (variable and inside) or _nested_repeat(body, inside=inside or variable):
                return True
```
Add test cases `(\d{2}:)+` and `^(\d{2}\.){2}` (must pass) next to `(\w+\s?)+$` (must fail).

### WR-04: Several invalid fields share one error placeholder, so the second field shows the first field's detail

**File:** `custom_components/xmltv_calendar/config_flow.py:311-316` (also `config_flow.py:370-377`)

**Issue:** `placeholders.setdefault("template_error", err.detail)` keeps only the first detail. When both templates are invalid, the description field's error says "`{foo}` is not an allowed placeholder", even though the description contains `{bar[0]}`. `test_both_templates_invalid_get_their_own_errors` asserts `template_error == "{foo}"`, so the test locks in the misleading message despite its name. The same applies to the regex fields in the basic step: with include and exclude both invalid, the exclude error names the include pattern. The basic step pattern dates from Phase 1; the advanced step repeats it in new code.

**Fix:** Use per-field placeholder names and error keys, for example `title_template_error` / `description_template_error` with matching error translations (`unknown_placeholder_title`, `unknown_placeholder_description`). Alternatively, report only the first invalid field so the shown detail always belongs to the marked field. Update the test to assert each field's own detail.

## Info

### IN-01: "Templates only, no refilter" path is effectively dead; the comment is misleading

**File:** `custom_components/xmltv_calendar/calendar.py:167-197`

**Issue:** Whenever `subentry.data` changes and the stored patterns compile, `refilter = True`, even if only a template changed. The comment "Templates only change the event text: rebuilt without a refilter (EVT-03, EVT-04)" never holds: a template-only edit triggers a full executor re-scan. `elif write_state` only runs when the new spec fails to compile.

**Fix:** Refilter only when the rebuilt spec differs (`spec != self._spec`), which needs comparable fields because `re.Pattern` compares by pattern and flags. Otherwise, correct the comment.

### IN-02: Unchecking "Advanced options" leaves hidden filters active without any hint

**File:** `custom_components/xmltv_calendar/config_flow.py:382-385`, `translations/en.json:81`

**Issue:** By design (`test_unchecking_advanced_keeps_stored_values`), unchecking only skips the second form. The stored time window, weekdays, durations and case flag still apply and are saved. The checkbox help text says only "Show a second form…", so a user who unchecks it to turn the extra filters off gets an unexplained preview count.

**Fix:** Extend the `advanced` data_description, for example: "Unchecking hides the form but keeps the advanced settings; clear them in the form to remove them."

### IN-03: Basic step help texts are stale after Phase 2

**File:** `custom_components/xmltv_calendar/translations/en.json:79-80`

**Issue:** The include and exclude descriptions still say patterns match "title or sub-title (case-insensitive)". Both the fields and the case are now configurable in the advanced step.

**Fix:** Change the help text to "…matches the selected fields (by default title or sub-title, case-insensitive)…".

### IN-04: `escape_markdown` does not escape `~`

**File:** `custom_components/xmltv_calendar/xmltv/preview.py:27`

**Issue:** HA's `ha-markdown` renders GFM, so a feed title like `~~Abgesagt~~` shows struck through in the preview, contrary to the "renders literally" contract (T-02-05).

**Fix:** Add `"~"` to `_MARKDOWN_CHARS`.

### IN-05: Channel regex lines are NFC-normalised, but channel IDs are not

**File:** `custom_components/xmltv_calendar/xmltv/filter.py:122,235`, `custom_components/xmltv_calendar/xmltv/parser.py:71,79`

**Issue:** `_lines` now NFC-normalises every pattern line, including the channel regex. The parser normalises element text only; `channel`/`id` attributes are only stripped. A feed with decomposed non-ASCII channel IDs would stop matching a channel regex that matched in Phase 1.

**Fix:** NFC-normalise the channel ID in the parser, or skip NFC for `KEY_CHANNEL_REGEX` in `from_mapping`.

### IN-06: Description cleanup strips legitimate trailing characters

**File:** `custom_components/xmltv_calendar/xmltv/render.py:38,93`

**Issue:** `_DESCRIPTION_END` removes any trailing run of `[\s\-–—:,;|·/]` from the whole rendered description. With a custom template such as `{description}`, a feed description ending in a URL (`…/`) or a dash loses those characters. The default description path is not affected.

**Fix:** Only strip separators that come from a placeholder that rendered empty (for example, render with a sentinel and clean around it), or limit the end strip to whitespace plus `:,;|`.

---

_Reviewed: 2026-10-15T11:50:42Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
