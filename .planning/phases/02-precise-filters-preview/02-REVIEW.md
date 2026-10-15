---
phase: 02-precise-filters-preview
reviewed: 2026-10-15T19:33:18Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - custom_components/xmltv_calendar/translations/de.json
  - custom_components/xmltv_calendar/xmltv/preview.py
  - tests/test_subentry_flow.py
  - tests/test_translations.py
  - tests/xmltv/test_preview.py
findings:
  critical: 0
  warning: 5
  info: 9
  total: 14
status: issues_found
---

# Phase 2: Code Review Report (incremental re-review after 02-10 and quick task 261015-su3)

**Reviewed:** 2026-10-15T19:33:18Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

This is an incremental re-review of `git diff 7252772..HEAD`. It covers two changes:

- **Gap closure 02-10.** `escape_markdown` now escapes the autolink triggers (the `:` of `://`, the `.` after `www`, every `@`) and `~`.
- **Quick task 261015-su3.** Adds a German `de.json` plus parity tests in `tests/test_translations.py`.

**IN-04 is RESOLVED.** `preview.py:33` adds `"~"` to `_MARKDOWN_CHARS`, and `tests/xmltv/test_preview.py` covers both `~x~` and `~~x~~`. The ID is retired and not reused.

**G-02-2 (autolinks) is fixed for the forms marked recognises.** I rendered the escaped output with a real marked install (17.0.5, `gfm: true, breaks: true`, the options `ha-markdown` uses):

- `\[link\](http\://x.y)`, `https\://www\.ard.de/a\_b`, `www\.ard.de`, `user\@example.de`, `mailto:user\@x.de` and `\~\~x\~\~` all render as plain text, with no `<a>` and no `<del>`.
- The escape order is sound: the autolink substitution runs after the backslash loop, so a feed backslash followed by `@` or `://` round-trips correctly (`a\@b` renders `a\@b`).
- Tests and lint pass: `uv run pytest tests` gives 539 passed, 1 skipped, and `ruff check .` is clean.

**New findings:**

- **WR-05:** `escape_markdown` still lets line breaks through. A channel display name or a title containing a line break breaks the preview list. Verified in marked: the list splits into `<ul>`/`<ol>`/`<ul>`, or an `<hr>` is inserted.
- **IN-08:** `de.json` now makes a mix of languages in one preview reachable.
- **IN-09:** "1 passende Sendungen" is grammatically wrong (same problem in en).
- **IN-10:** The literal-parity test has a vacuous substring check.

**Carried forward:**

- **Changed scope:** WR-02, IN-02 and IN-03 now also concern `de.json`, which copies the en text and its gaps exactly. `test_de_has_same_keys_as_en` and `test_de_keeps_literals` lock en/de parity, so each fix must update both files.
- **Unchanged files:** WR-01, WR-03, WR-04, IN-01, IN-05, IN-06 and IN-07 sit in files this diff does not touch (`config_flow.py`, `filter.py`, `calendar.py`, `parser.py`, `render.py`, `tests/test_calendar.py`, `tests/test_reconfigure.py`). `git diff 7252772..HEAD` is empty for all of them, so they are still open exactly as previously reported and keep their IDs.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Basic step brings cleared fields back after a validation error (carried forward, still open)

**File:** `custom_components/xmltv_calendar/config_flow.py:405` (outside this re-review's file scope; unchanged since 7252772)

**Issue:** The form is still rebuilt with `pending | (user_input or {})`. A field the user cleared is missing from `user_input`, so the merge suggests the old pending value again, and the next valid submit saves it again.

**Fix:**
```python
        suggestions = user_input if user_input is not None else pending
        schema = self.add_suggested_values_to_schema(schema, suggestions)
```

### WR-02: Missing `reconfigure_successful` abort translation for the calendar edit flow, now in en and de (carried forward, still open)

**File:** `custom_components/xmltv_calendar/translations/de.json:138-140`, `custom_components/xmltv_calendar/translations/en.json:138-140` (used by `config_flow.py:478`)

**Issue:** `config_subentries.calendar.abort` defines only `source_not_loaded` in both languages. Every successful calendar edit ends on an abort that has no text. The new parity test (`test_de_has_same_keys_as_en`) fails if the key is added to only one file.

**Fix:** Add the key to both files in the same position:
```json
      "abort": {
        "source_not_loaded": "Die Quelle ist nicht geladen. Warte, bis sie heruntergeladen wurde, und versuche es dann erneut.",
        "reconfigure_successful": "Der Kalender wurde aktualisiert."
      }
```
The en value is "The calendar was updated."

### WR-03: Nested-repetition guard rejects harmless fixed-count repeats (carried forward, still open)

**File:** `custom_components/xmltv_calendar/xmltv/filter.py:149-151` (outside this re-review's file scope; unchanged since 7252772)

**Issue:** `unbounded = high > 1` treats `{2}` as variable. `(\d{2}:)+` is therefore rejected in the flow, although the entity accepts it at runtime.

**Fix:**
```python
            low, high, body = av
            variable = high > 1 and high != low
            if (variable and inside) or _nested_repeat(body, inside=inside or variable):
                return True
```

### WR-04: Several invalid fields share one error placeholder (carried forward, still open)

**File:** `custom_components/xmltv_calendar/config_flow.py:376-377`, `config_flow.py:316` (outside this re-review's file scope; unchanged since 7252772)

**Issue:** `placeholders.setdefault("pattern"/"error", ...)` keeps only the first invalid field's detail, so the second field shows the first field's message. This now applies to both languages, because de.json's `invalid_regex` uses the same `{pattern}`/`{error}` placeholders.

**Fix:** Use per-field placeholders and error keys (for example `include_pattern`/`include_error` with an `invalid_regex_include` translation in en and de). Alternatively, report only the first invalid field.

### WR-05: `escape_markdown` lets line breaks through, so feed text can break the preview list (new)

**File:** `custom_components/xmltv_calendar/xmltv/preview.py:37-44`, `preview.py:62`

**Issue:** The docstring promises "feed text that renders literally". It escapes inline syntax only. Block syntax becomes reachable as soon as a value contains a line break, and the preview list is built as `"\n".join(f"- {line}" ...)` (`config_flow.py:461`). Two inputs carry line breaks unchanged:

- **`channel_name`** is `channel.display_name`. The parser keeps it as `_text()` returns it, which only strips the edges, so an internal `\n` survives (`parser.py:56-58,75`). It never passes through `clean_title`.
- **`title`** passes through `clean_title`, which replaces only `\n` (`render.py:88`). A `\r` (for example from `&#13;` in the feed) survives, and marked treats a lone `\r` as a line ending.

Verified with marked 17.0.5 (`gfm: true, breaks: true`):

| Input | Rendered |
|---|---|
| `- Tue 13.10. 14:00 · Sport\n1. Liga · T\n- Tue …` | `<ul>…Sport</ul><ol><li>Liga · T</li></ol><ul>…</ul>` |
| `- Tue 13.10. 14:00 · Sport\r1. Liga · Tagesschau\n- …` | same split |
| `- … · Sport\n+ Plus · T\n- …` | three separate `<ul>` |
| `- … · Sport\n---\n- …` | `<hr>` inserted |

There is no XSS: `<` is entity-escaped and js-xss sanitises. But the preview no longer shows "one line per match", and part of a channel name gets swallowed as a list marker. This is the same class of defect G-02-2 fixed for autolinks.

**Fix:** Collapse every line break and whitespace run to one space before escaping. A preview line is single-line by definition.
```python
_LINE_BREAKS = re.compile(r"\s+")  # \s covers \n, \r, \v, \f, \x1c-\x1e, \x85, \u2028, \u2029

def escape_markdown(text: str) -> str:
    text = _LINE_BREAKS.sub(" ", text).strip()
    for char, entity in _HTML_ESCAPES:
        ...
```
Add test cases `("Das\nErste", "Das Erste")`, `("Sport\r1. Liga", "Sport 1. Liga")` and `("A\n---", "A ---")`. Separately, consider making `clean_title` (`render.py:88`) replace `\r` as well, because calendar summaries have the same gap.

## Info

### IN-01: "Templates only, no refilter" path is effectively dead; the comment is misleading (carried forward, still open)

**File:** `custom_components/xmltv_calendar/calendar.py:171-179` (unchanged since 7252772)

**Issue:** Any data change with compilable patterns sets `refilter = True`, including a template-only edit.

**Fix:** Refilter only when the rebuilt spec differs from `self._spec`, or correct the comment.

### IN-02: Unchecking "Advanced options" leaves hidden filters active without any hint, now in en and de (carried forward, still open)

**File:** `custom_components/xmltv_calendar/config_flow.py:382-385`, `translations/en.json:81`, `translations/de.json:81`

**Issue:** Neither language's `advanced` help text says that unchecking keeps the stored advanced filters active.

**Fix:** Extend both texts. de: "Abwählen blendet das Formular aus, die erweiterten Einstellungen bleiben aber aktiv; leere sie im Formular, um sie zu entfernen."

### IN-03: Basic step help texts are stale after Phase 2, now in en and de (carried forward, still open)

**File:** `translations/en.json:79-80`, `translations/de.json:79-80`

**Issue:** Both languages still say "title or sub-title (case-insensitive)" / "Titel oder Untertitel (ohne Beachtung der Groß-/Kleinschreibung)". Both the fields and the case sensitivity are configurable now.

**Fix:** de: "…wenn einer davon auf die ausgewählten Felder passt (standardmäßig Titel oder Untertitel, ohne Beachtung der Groß-/Kleinschreibung)…". Make the matching change in en. `test_de_keeps_literals` stays green as long as the example regexes are kept.

### IN-05: Channel regex lines are NFC-normalised, but channel IDs are not (carried forward, still open)

**File:** `custom_components/xmltv_calendar/xmltv/filter.py:124-126,252`, `xmltv/parser.py:71,79` (unchanged since 7252772)

**Issue:** The channel regex lines are normalised and the IDs they are matched against are not.

**Fix:** NFC-normalise the channel ID in the parser, or skip NFC for `KEY_CHANNEL_REGEX`.

### IN-06: Description cleanup strips legitimate trailing characters (carried forward, still open)

**File:** `custom_components/xmltv_calendar/xmltv/render.py:32,38,93` (unchanged since 7252772)

**Issue:** `_DESCRIPTION_END` strips any trailing `[\s\-–—:,;|·/]` run.

**Fix:** Limit the end strip to whitespace plus `:,;|`, or clean only around placeholders that rendered empty.

### IN-07: Deep-nesting test fixture depends on the interpreter's recursion limit and is duplicated (carried forward, still open)

**File:** `tests/test_calendar.py:27-29`, `tests/test_reconfigure.py:34-36` (unchanged since 7252772)

**Issue:** `DEEP_NESTING = "(" * 2000 + ")" * 2000` raises `RecursionError` only at the default recursion limit.

**Fix:** Derive the depth from `sys.getrecursionlimit()` and define the constant once in `tests/conftest.py`.

### IN-08: Preview weekday language follows the server, the surrounding text follows the user (new, made reachable by de.json)

**File:** `custom_components/xmltv_calendar/xmltv/preview.py:59`, `custom_components/xmltv_calendar/config_flow.py:453`

**Issue:** `build_preview` picks the weekday abbreviations from `hass.config.language` (the server language). The frontend picks the `de.json`/`en.json` description by the user's profile language.

Before su3 every UI string was English, so only the weekday could vary. Now a German profile on a server configured as `en` sees "3 passende Sendungen ab jetzt. Als Nächstes: - Tue 13.10. …". The reverse setup shows "Di" inside English text. The flow handler has no access to the user's frontend language.

**Fix:** Use a language-neutral stamp, for example `13.10. 14:00` without a weekday, or a numeric ISO date. Alternatively, document that the weekday follows the server language.

### IN-09: "1 passende Sendungen" / "1 matching programmes" (new)

**File:** `custom_components/xmltv_calendar/translations/de.json:113` (also `en.json:113`)

**Issue:** `{count}` is substituted into a plural noun phrase. A count of 1 is a normal state: `test_preview_shows_feed_urls_as_plain_text` asserts `count == "1"`. In that case both languages render ungrammatical text.

**Fix:** Rephrase so the count stands alone. That keeps the plain `{count}` placeholder, which the parity tests and HA's `_validate_placeholders` expect:
```json
"description": "Passende Sendungen ab jetzt: {count}. Als Nächstes:\n\n{matches}"
```
en: `"Matching programmes from now on: {count}. Next:\n\n{matches}"`.

### IN-10: `test_de_keeps_literals` uses substring matching, so short numeric literals pass vacuously (new)

**File:** `tests/test_translations.py:141`

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

_Reviewed: 2026-10-15T19:33:18Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
