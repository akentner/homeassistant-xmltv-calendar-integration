---
phase: 02-precise-filters-preview
reviewed: 2026-10-15T20:03:16Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - custom_components/xmltv_calendar/xmltv/preview.py
  - tests/test_subentry_flow.py
  - tests/xmltv/test_preview.py
findings:
  critical: 0
  warning: 4
  info: 9
  total: 13
status: issues_found
---

# Phase 2: Code Review Report (incremental re-review after quick task 261015-u6j)

**Reviewed:** 2026-10-15T20:03:16Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

This is an incremental re-review of `git diff 13b427c..HEAD`. The only source change is quick task 261015-u6j:

- `escape_markdown` (`preview.py:41-49`) now collapses every `\s+` run to one space and strips the edges before the HTML and Markdown escaping.
- `tests/xmltv/test_preview.py` adds 12 whitespace cases, one `format_line` case and 4 byte-identity cases.
- `tests/test_subentry_flow.py` adds an end-to-end flow test with a `\n` in a channel display name and a `&#13;` (`\r`) in a title.

**WR-05 is RESOLVED.** The ID is retired and not reused.

- `_WHITESPACE_RUNS = re.compile(r"\s+")` is a `str` pattern, so it matches every line ending marked recognises (`\n`, `\r`, `\r\n`) plus `\v`, `\f`, `\x1c-\x1f`, `\x85`, `\u2028`, `\u2029`. A preview line can no longer contain a line break, so no feed value can start a list, an ordered list, a thematic break or a setext heading.
- Order is sound. The collapse runs first, so it cannot create or undo any escape. It also cannot create an autolink trigger: `www\n.x` becomes `www .x` and `http:\n//x` becomes `http: //x`, and neither matches the autolink forms.
- Collapsing internal runs also removes the "two trailing spaces" hard-break form, which is harmless with `breaks: true` anyway.
- The end-to-end test uses raw `_programme` interpolation, so `&#13;` really reaches the parser as a character reference and arrives as `\r`. `clean_title` (`render.py:88`) passes it through and `escape_markdown` collapses it. The test checks the full `matches` string and `splitlines()`, which also splits on `\x85`/`\u2028`, so it actually exercises the fix.
- Verified locally: `uv run pytest tests` gives 557 passed, 1 skipped. `ruff check .` and `ruff format --check .` are clean.

**No new findings in the changed files.** I checked these and found nothing that needs fixing:

- NBSP and other Unicode spaces are now normalised to a plain space. This is intentional (locked by the `nbsp` case), and it only changes the preview text, not the stored data or the calendar.
- A display name that is only whitespace would collapse to `""`. The parser's `_text()` already strips such values to `""` (`str.strip` covers the same Unicode whitespace), so this behaviour is not new.

**Residual note, outside this scope (not a finding):** the calendar entity's `summary` still goes through `clean_title`, which replaces only `\n` (`render.py:88`). A `\r` in a title, or a `\u2028`, still reaches calendar summaries. A summary is plain text, not Markdown, so the impact is cosmetic. The previous WR-05 fix note already suggested that follow-up.

**Carried forward:** `git diff 13b427c..HEAD` is empty for `config_flow.py`, `filter.py`, `calendar.py`, `parser.py`, `render.py`, `translations/en.json`, `translations/de.json`, `tests/test_translations.py`, `tests/test_calendar.py` and `tests/test_reconfigure.py`. WR-01..WR-04, IN-01..IN-03, IN-05..IN-07, IN-09 and IN-10 are therefore still open exactly as previously reported and keep their IDs. IN-08 also stays open. The code it points at is unchanged, but its `preview.py` line reference moved from 59 to 64 because of the new comment and constant.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Basic step brings cleared fields back after a validation error (carried forward, still open)

**File:** `custom_components/xmltv_calendar/config_flow.py:405` (outside this re-review's file scope; unchanged since 13b427c)

**Issue:** The form is still rebuilt with `pending | (user_input or {})`. A field the user cleared is missing from `user_input`, so the merge suggests the old pending value again, and the next valid submit saves it again.

**Fix:**
```python
        suggestions = user_input if user_input is not None else pending
        schema = self.add_suggested_values_to_schema(schema, suggestions)
```

### WR-02: Missing `reconfigure_successful` abort translation for the calendar edit flow, in en and de (carried forward, still open)

**File:** `custom_components/xmltv_calendar/translations/de.json:138-140`, `custom_components/xmltv_calendar/translations/en.json:138-140` (used by `config_flow.py:478`; unchanged since 13b427c)

**Issue:** `config_subentries.calendar.abort` defines only `source_not_loaded` in both languages. Every successful calendar edit ends on an abort that has no text. The parity test (`test_de_has_same_keys_as_en`) fails if the key is added to only one file.

**Fix:** Add the key to both files in the same position:
```json
      "abort": {
        "source_not_loaded": "Die Quelle ist nicht geladen. Warte, bis sie heruntergeladen wurde, und versuche es dann erneut.",
        "reconfigure_successful": "Der Kalender wurde aktualisiert."
      }
```
The en value is "The calendar was updated."

### WR-03: Nested-repetition guard rejects harmless fixed-count repeats (carried forward, still open)

**File:** `custom_components/xmltv_calendar/xmltv/filter.py:149-151` (outside this re-review's file scope; unchanged since 13b427c)

**Issue:** `unbounded = high > 1` treats `{2}` as variable. `(\d{2}:)+` is therefore rejected in the flow, although the entity accepts it at runtime.

**Fix:**
```python
            low, high, body = av
            variable = high > 1 and high != low
            if (variable and inside) or _nested_repeat(body, inside=inside or variable):
                return True
```

### WR-04: Several invalid fields share one error placeholder (carried forward, still open)

**File:** `custom_components/xmltv_calendar/config_flow.py:376-377`, `config_flow.py:316` (outside this re-review's file scope; unchanged since 13b427c)

**Issue:** `placeholders.setdefault("pattern"/"error", ...)` keeps only the first invalid field's detail, so the second field shows the first field's message. This applies to both languages, because de.json's `invalid_regex` uses the same `{pattern}`/`{error}` placeholders.

**Fix:** Use per-field placeholders and error keys (for example `include_pattern`/`include_error` with an `invalid_regex_include` translation in en and de). Alternatively, report only the first invalid field.

## Info

### IN-01: "Templates only, no refilter" path is effectively dead; the comment is misleading (carried forward, still open)

**File:** `custom_components/xmltv_calendar/calendar.py:171-179` (unchanged since 13b427c)

**Issue:** Any data change with compilable patterns sets `refilter = True`, including a template-only edit.

**Fix:** Refilter only when the rebuilt spec differs from `self._spec`, or correct the comment.

### IN-02: Unchecking "Advanced options" leaves hidden filters active without any hint, in en and de (carried forward, still open)

**File:** `custom_components/xmltv_calendar/config_flow.py:382-385`, `translations/en.json:81`, `translations/de.json:81` (unchanged since 13b427c)

**Issue:** Neither language's `advanced` help text says that unchecking keeps the stored advanced filters active.

**Fix:** Extend both texts. de: "Abwählen blendet das Formular aus, die erweiterten Einstellungen bleiben aber aktiv; leere sie im Formular, um sie zu entfernen."

### IN-03: Basic step help texts are stale after Phase 2, in en and de (carried forward, still open)

**File:** `translations/en.json:79-80`, `translations/de.json:79-80` (unchanged since 13b427c)

**Issue:** Both languages still say "title or sub-title (case-insensitive)" / "Titel oder Untertitel (ohne Beachtung der Groß-/Kleinschreibung)". Both the fields and the case sensitivity are configurable now.

**Fix:** de: "…wenn einer davon auf die ausgewählten Felder passt (standardmäßig Titel oder Untertitel, ohne Beachtung der Groß-/Kleinschreibung)…". Make the matching change in en. `test_de_keeps_literals` stays green as long as the example regexes are kept.

### IN-05: Channel regex lines are NFC-normalised, but channel IDs are not (carried forward, still open)

**File:** `custom_components/xmltv_calendar/xmltv/filter.py:124-126,252`, `xmltv/parser.py:71,79` (unchanged since 13b427c)

**Issue:** The channel regex lines are normalised and the IDs they are matched against are not.

**Fix:** NFC-normalise the channel ID in the parser, or skip NFC for `KEY_CHANNEL_REGEX`.

### IN-06: Description cleanup strips legitimate trailing characters (carried forward, still open)

**File:** `custom_components/xmltv_calendar/xmltv/render.py:32,38,93` (unchanged since 13b427c)

**Issue:** `_DESCRIPTION_END` strips any trailing `[\s\-–—:,;|·/]` run.

**Fix:** Limit the end strip to whitespace plus `:,;|`, or clean only around placeholders that rendered empty.

### IN-07: Deep-nesting test fixture depends on the interpreter's recursion limit and is duplicated (carried forward, still open)

**File:** `tests/test_calendar.py:27-29`, `tests/test_reconfigure.py:34-36` (unchanged since 13b427c)

**Issue:** `DEEP_NESTING = "(" * 2000 + ")" * 2000` raises `RecursionError` only at the default recursion limit.

**Fix:** Derive the depth from `sys.getrecursionlimit()` and define the constant once in `tests/conftest.py`.

### IN-08: Preview weekday language follows the server, the surrounding text follows the user (carried forward, still open)

**File:** `custom_components/xmltv_calendar/xmltv/preview.py:64`, `custom_components/xmltv_calendar/config_flow.py:453`

**Issue:** `build_preview` picks the weekday abbreviations from `hass.config.language` (the server language). The frontend picks the `de.json`/`en.json` description by the user's profile language.

A German profile on a server configured as `en` therefore sees "3 passende Sendungen ab jetzt. Als Nächstes: - Tue 13.10. …". The reverse setup shows "Di" inside English text. The flow handler has no access to the user's frontend language. Quick task u6j did not change the lookup; only the line number moved.

**Fix:** Use a language-neutral stamp, for example `13.10. 14:00` without a weekday, or a numeric ISO date. Alternatively, document that the weekday follows the server language.

### IN-09: "1 passende Sendungen" / "1 matching programmes" (carried forward, still open)

**File:** `custom_components/xmltv_calendar/translations/de.json:113` (also `en.json:113`; unchanged since 13b427c)

**Issue:** `{count}` is substituted into a plural noun phrase. A count of 1 is a normal state: `test_preview_shows_feed_urls_as_plain_text` asserts `count == "1"`. In that case both languages render ungrammatical text.

**Fix:** Rephrase so the count stands alone. That keeps the plain `{count}` placeholder, which the parity tests and HA's `_validate_placeholders` expect:
```json
"description": "Passende Sendungen ab jetzt: {count}. Als Nächstes:\n\n{matches}"
```
en: `"Matching programmes from now on: {count}. Next:\n\n{matches}"`.

### IN-10: `test_de_keeps_literals` uses substring matching, so short numeric literals pass vacuously (carried forward, still open)

**File:** `tests/test_translations.py:141` (unchanged since 13b427c)

**Issue:** `token not in german` is a substring test, so short tokens pass even when the German text changes them:

- The en token `1` from "(1 to 168)" is satisfied by the `1` inside `168`, or by any other `1`.
- `50` would be satisfied by `500`.

A German text that changed "1 bis 168" to "2 bis 168" would therefore pass.

**Fix:** Match on token boundaries but still allow German compound suffixes such as `http://-`:
```python
missing = [
    token for token in _literals(text)
    if not re.search(rf"(?<![0-9A-Za-z]){re.escape(token)}(?![0-9A-Za-z])", german)
]
```

---

_Reviewed: 2026-10-15T20:03:16Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
