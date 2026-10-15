---
phase: 02-precise-filters-preview
reviewed: 2026-10-15T15:24:46Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - custom_components/xmltv_calendar/calendar.py
  - custom_components/xmltv_calendar/xmltv/filter.py
  - tests/test_calendar.py
  - tests/test_reconfigure.py
  - tests/test_subentry_flow.py
  - tests/xmltv/test_filter.py
findings:
  critical: 0
  warning: 4
  info: 7
  total: 11
status: issues_found
---

# Phase 2: Code Review Report (incremental re-review after gap closure 02-09)

**Reviewed:** 2026-10-15T15:24:46Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

This is an incremental re-review of gap-closure plan 02-09 (`git diff 3c53e0f..HEAD`). The plan targets the previous review's CR-01: uncompilable regex patterns raising `OverflowError`/`RecursionError`, which escaped `except re.error`.

**CR-01 is RESOLVED.** Evidence:

- `filter.py:55` adds `PATTERN_ERRORS = (re.error, OverflowError, RecursionError)`. Both compile sites that face users or storage now catch it:
  - `first_invalid_pattern` (`filter.py:194-198`, the flow validator for include, exclude and channel regex)
  - `_build_spec` (`calendar.py:57-61`, entity `__init__` and `async_apply_subentry`)
- **No other unguarded compile path.** `build_preview` (`preview.py:67`) calls `FilterSpec.from_mapping` without a guard. It only sees `pending` data, and the basic step writes pattern fields into `pending` only after `first_invalid_pattern` passes for all three fields (`config_flow.py:371-380`). Every path to the preview goes through that submit.
- **The exception set is complete for the reachable input space.**
  - Fuzzed 400k random short patterns under both flag settings (0 and `IGNORECASE`) with Python 3.14.7. No exception type outside `PATTERN_ERRORS` occurred.
  - No pattern compiled under one flag but failed under the other. So validating include/exclude with the *pending* case flag stays sound even when the advanced step changes the flag afterwards without re-validating.
- **The `RecursionError` path is reachable only through storage.** The first failing depth is about 500 nesting levels at the default recursion limit, while the flow's 300-character cap allows at most 150.
- `with_defaults` coerces non-string pattern values to `""`, so hand-edited non-string data cannot raise `AttributeError` from `splitlines()`.
- **Tests and lint pass.** `uv run pytest tests`: 517 passed, 1 skipped. `ruff check .` is clean.

The new tests cover:

- Syntax errors, repeat overflow (count and range) and deep nesting.
- Flow validation of all three pattern fields.
- Platform setup with a bad stored pattern, isolated to its own calendar.
- The live-apply path, which keeps the previous matches.
- Repairing a stored overflow pattern through the edit flow.

**New in this re-review:** one Info item (IN-07), a test-reliability detail in the new deep-nesting fixtures. No new Critical or Warning defects in the 02-09 diff.

**Carried forward.** All other prior findings are still open and verified present in the current code. 02-09 changed only `calendar.py` and `filter.py` under `custom_components/`. Findings in `config_flow.py`, `translations/en.json`, `preview.py`, `parser.py` and `render.py` are therefore unchanged since `3c53e0f`. They keep their original IDs so the disposition record stays aligned. CR-01 is not carried and its ID is not reused.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Basic step brings cleared fields back after a validation error (carried forward, still open)

**File:** `custom_components/xmltv_calendar/config_flow.py:405` (outside this re-review's file scope; unchanged since 3c53e0f)

**Issue:** The form is still rebuilt with `pending | (user_input or {})`. A field the user cleared is missing from `user_input`, and line 379 itself treats a missing key as "cleared". The merge therefore re-suggests the old pending value, and the next valid submit saves it again.

02-09 makes this more likely to hit. The new repair path (`test_edit_repairs_overflowing_stored_pattern`) is exactly "submit, get `invalid_regex`, fix, resubmit". Clearing exclude in the first submit of that path silently restores it.

**Fix:**
```python
        suggestions = user_input if user_input is not None else pending
        schema = self.add_suggested_values_to_schema(schema, suggestions)
```
Add a reconfigure test: clear `exclude`, submit an invalid `include`, and assert that `exclude` has no suggested value.

### WR-02: Missing `reconfigure_successful` abort translation for the calendar edit flow (carried forward, still open)

**File:** `custom_components/xmltv_calendar/translations/en.json:138-140` (used by `config_flow.py:478`; outside this re-review's file scope)

**Issue:** `config_subentries.calendar.abort` still defines only `source_not_loaded`. Every successful calendar edit, including the new CR-01 repair flow (`test_edit_repairs_overflowing_stored_pattern` asserts `reason == "reconfigure_successful"`), ends on an abort with no text.

**Fix:**
```json
      "abort": {
        "source_not_loaded": "The source is not loaded. Wait until it has been downloaded, then try again.",
        "reconfigure_successful": "The calendar was updated."
      }
```

### WR-03: Nested-repetition guard rejects harmless fixed-count repeats, which blocks saving Phase 1 calendars unchanged (carried forward, still open)

**File:** `custom_components/xmltv_calendar/xmltv/filter.py:149-151`

**Issue:** `unbounded = high > 1` still treats exact counts like `{2}` as variable. `(\d{2}:)+` and `^(\d{2}\.){2}` are rejected as "nested repetition can be very slow", although a fixed-count inner repeat cannot cause catastrophic backtracking.

The edit flow re-validates stored lines, so a Phase 1 calendar with such a pattern cannot be saved unchanged. The runtime still compiles and uses the pattern, so the flow and the entity disagree about validity.

**Fix:**
```python
            low, high, body = av
            variable = high > 1 and high != low  # {n} is a fixed count, not ambiguous
            if (variable and inside) or _nested_repeat(body, inside=inside or variable):
                return True
```
Add `(\d{2}:)+` and `^(\d{2}\.){2}` (must pass) next to `(\w+\s?)+$` (must fail).

### WR-04: Several invalid fields share one error placeholder, so the second field shows the first field's detail (carried forward, still open)

**File:** `custom_components/xmltv_calendar/config_flow.py:376-377` and `config_flow.py:316` (outside this re-review's file scope)

**Issue:** `placeholders.setdefault("pattern"/"error", ...)` keeps only the first invalid field's detail. 02-09 widens the set of messages that land here. For example, with include `a{99999999999}` and exclude `(`, both fields are marked `invalid_regex`, but both show "Invalid pattern a{99999999999}: the repetition number is too large". The same happens for the two template fields in the advanced step.

**Fix:** Use per-field placeholders and error keys, for example `include_pattern`/`include_error` with an `invalid_regex_include` translation. Alternatively, report only the first invalid field. Assert each field's own detail in the tests.

## Info

### IN-01: "Templates only, no refilter" path is effectively dead; the comment is misleading (carried forward, still open)

**File:** `custom_components/xmltv_calendar/calendar.py:171-179`

**Issue:** Any data change with compilable patterns sets `refilter = True`, including a template-only edit. The comment "rebuilt without a refilter (EVT-03, EVT-04)" never holds, and `elif write_state` runs only when the new spec fails to compile.

**Fix:** Refilter only when the rebuilt spec differs from `self._spec`. Otherwise, correct the comment.

### IN-02: Unchecking "Advanced options" leaves hidden filters active without any hint (carried forward, still open)

**File:** `custom_components/xmltv_calendar/config_flow.py:382-385`, `custom_components/xmltv_calendar/translations/en.json:81`

**Issue:** Unchanged. The `advanced` help text does not say that unchecking keeps the stored advanced filters active.

**Fix:** Extend the `advanced` data_description: "Unchecking hides the form but keeps the advanced settings; clear them in the form to remove them."

### IN-03: Basic step help texts are stale after Phase 2 (carried forward, still open)

**File:** `custom_components/xmltv_calendar/translations/en.json:79-80`

**Issue:** Unchanged. The include and exclude help still says "title or sub-title (case-insensitive)", but both the fields and the case are configurable now.

**Fix:** Change the text to "…matches the selected fields (by default title or sub-title, case-insensitive)…".

### IN-04: `escape_markdown` does not escape `~` (carried forward, still open)

**File:** `custom_components/xmltv_calendar/xmltv/preview.py:27`

**Issue:** Unchanged. `_MARKDOWN_CHARS` lacks `~`, so `~~Abgesagt~~` renders struck through in the preview.

**Fix:** Add `"~"` to `_MARKDOWN_CHARS`.

### IN-05: Channel regex lines are NFC-normalised, but channel IDs are not (carried forward, still open)

**File:** `custom_components/xmltv_calendar/xmltv/filter.py:124-126,252`, `custom_components/xmltv_calendar/xmltv/parser.py:71,79`

**Issue:** Unchanged. `_lines` NFC-normalises channel regex lines, while the parser only strips the `id`/`channel` attributes.

**Fix:** NFC-normalise the channel ID in the parser, or skip NFC for `KEY_CHANNEL_REGEX`.

### IN-06: Description cleanup strips legitimate trailing characters (carried forward, still open)

**File:** `custom_components/xmltv_calendar/xmltv/render.py:32,38,93`

**Issue:** Unchanged. `_DESCRIPTION_END` strips any trailing `[\s\-–—:,;|·/]` run, so a description ending in a URL `/` or a dash loses it under a custom `{description}` template.

**Fix:** Only clean around placeholders that rendered empty, or limit the end strip to whitespace plus `:,;|`.

### IN-07: Deep-nesting test fixture depends on the interpreter's recursion limit and is duplicated (new)

**File:** `tests/test_calendar.py:27-29`, `tests/test_reconfigure.py:34-36`

**Issue:** `DEEP_NESTING = "(" * 2000 + ")" * 2000` only raises `RecursionError` because the process runs at the default limit of 1000. In practice the first failing depth is about 500 levels.

Verified in a scratch probe: after `sys.setrecursionlimit(5000)`, the same 2000-level pattern compiles. Under a raised limit, both `deep-nesting` parametrisations would then fail. They would show matches for calendar A and the warning count would be 0. The test would stop exercising the `RecursionError` branch of `PATTERN_ERRORS` without saying why. Such a limit could come from a plugin, a debugger or a future HA test harness.

The constant and its three-line comment are also copied verbatim into two modules.

**Fix:** Derive the depth from the active limit and define it once in `tests/conftest.py` (or a shared helper):
```python
import sys

# Each nesting level costs at least two parser frames, so this always exceeds the active recursion limit
DEEP_NESTING = "(" * (2 * sys.getrecursionlimit()) + ")" * (2 * sys.getrecursionlimit())
```

---

_Reviewed: 2026-10-15T15:24:46Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
