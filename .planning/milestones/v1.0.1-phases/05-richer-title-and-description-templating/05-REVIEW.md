---
phase: 05-richer-title-and-description-templating
reviewed: 2026-10-30T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - custom_components/xmltv_calendar/calendar.py
  - custom_components/xmltv_calendar/config_flow.py
  - custom_components/xmltv_calendar/matcher.py
  - custom_components/xmltv_calendar/xmltv/preview.py
  - custom_components/xmltv_calendar/xmltv/render.py
  - custom_components/xmltv_calendar/xmltv/settings.py
  - custom_components/xmltv_calendar/xmltv/template_engine.py
  - custom_components/xmltv_calendar/translations/de.json
  - custom_components/xmltv_calendar/translations/en.json
  - tests/test_template_runtime.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-10-30
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

The sandboxed engine is sound. The node allow-list runs before compile and constant folding, filters and tests are pruned, star-arguments are rejected, regex literals are probed, and result and literal sizes are capped. Local-time handling is consistent across the entity, `get_events`, the sensor, the new-match event and the preview. `tz` is resolved on the event loop before the executor path. `ruff check` passes on all reviewed source files. T-05-03 and T-05-12 are known and excluded.

I found no critical issues. The four warnings are validation or cleanup gaps where the documented behaviour (D-08, D-10, "at most one blank line") is not fully achieved. I confirmed each one against the code or by running it in the project venv.

## Warnings

### WR-01: A second template error shows the first template's detail

**File:** `custom_components/xmltv_calendar/config_flow.py:545-550`
**Issue:** `_advanced_errors` uses `placeholders.setdefault("template_error", err.detail)`. HA applies one `description_placeholders` dict to the whole form. When the title and the description template are both invalid, both field errors render with the title's detail. For example, the description field would read "`foo` is not a known variable" about a different problem. The same single-slot pattern is used for `invalid_regex` in `async_step_basic`, but there the message embeds the pattern, so it is less misleading.
**Fix:** Give each field its own placeholder key and its own translation text. Alternatively, report only the first failing template and skip validating the other:
```python
for field, description in templates:
    try:
        validate_template(values[field], description=description)
    except TemplateError as err:
        errors[field] = err.reason
        placeholders["template_error"] = err.detail
        break  # one detail slot: report one template at a time
```

### WR-02: Unchecking "Advanced options" saves a stored template without validating it

**File:** `custom_components/xmltv_calendar/config_flow.py:612-619, 704-716`
**Issue:** `_load_pending` copies the stored template text into `pending`. If the stored title or description template is unusable (an old single-brace template such as `{title}` from Phase 2-4, or hand-edited storage), the user can untick "Advanced options" on the basic step. The flow then goes straight to preview and save, and `_calendar_data()` writes the legacy text back to storage with no `validate_template` call. At runtime that template logs a WARNING and falls back to the default title, so D-10's "nothing invalid is stored" does not hold on this path. The box is pre-checked in that case because `has_advanced` is true, but the user can still untick it.
**Fix:** Validate the templates in `pending` before `async_step_preview` or `async_step_save`, whichever step is reached without passing through `async_step_advanced`. If validation fails, route to the advanced step with the error:
```python
if not self._show_advanced:
    errors, placeholders = _advanced_errors(with_defaults(pending))
    if any(k in errors for k in (CONF_TITLE_TEMPLATE, CONF_DESCRIPTION_TEMPLATE)):
        self._show_advanced = True
        return await self.async_step_advanced()
```
`async_step_advanced` would need to show those errors on first display.

### WR-03: The legacy-syntax check is bypassed by any text containing `{{` or `{%`

**File:** `custom_components/xmltv_calendar/xmltv/template_engine.py:411-416`
**Issue:** `_check_legacy` returns early when `"{{"` or `"{%"` appears anywhere in the text. A partly migrated template such as `{channel} - {{ title }}` passes `compile_template` and `validate_template`. It then renders the literal text `{channel}` into every event title. I confirmed this with `validate_template("{channel} - {{ title }}")`, which returned without error. This defeats the purpose of D-08, which is to stop literal braces from silently appearing in titles.
**Fix:** Check the literal template text after parsing instead of the raw source. Search only `nodes.TemplateData` nodes (and string `Const`s if desired):
```python
def _check_legacy_tree(tree: nodes.Template) -> None:
    for data in tree.find_all(nodes.TemplateData):
        if (match := _LEGACY_PLACEHOLDER.search(data.data)) is not None:
            raise TemplateError(LEGACY_PLACEHOLDER, match[0])
```
Call this after `ENV.parse`, in place of the early-return string check.

### WR-04: `clean_description` does not honour "at most one blank line" or strip line edges

**File:** `custom_components/xmltv_calendar/xmltv/render.py:64-70, 87-90`
**Issue:** `_BLANK_LINES = \n{3,}` and `_SPACES = [ \t]{2,}` do not touch whitespace-only lines or trailing spaces. Running `clean_description("A\n \n \n \nB \n C")` returns `'A\n \n \n \nB \n C'` unchanged, so several visually blank lines and trailing spaces survive. This is easy to hit. A template line such as `{{ subtitle }} ` (trailing space) or an indented `{% if %}` body that renders empty leaves single-space lines, which `\n{3,}` never matches. `clean_title` also leaves `\r` in place, since only `\n` is replaced and `\r` is not matched by `_SPACES`. `clean_title("Foo\r\nBar")` returns `'Foo\r Bar'`.
**Fix:** Strip each line's edges and then collapse blank lines. In `clean_description`, add:
```python
text = "\n".join(line.strip(" \t") for line in text.splitlines())
```
before `_BLANK_LINES.sub`. In `clean_title`, normalise all line breaks with `" ".join(text.split())` or a `\r?\n|\r` replace.

## Info

### IN-01: Customised Phase 2-4 title templates are dropped silently on upgrade

**File:** `custom_components/xmltv_calendar/xmltv/settings.py:49-52, 138-140`, `render.py:196-205`
**Issue:** Only the exact legacy default `{channel}: {title}` is mapped to the new default. Any other stored single-brace template (for example `{title} ({channel})`) is treated as unusable. It logs one WARNING and the calendar shows the default title until the user edits it. The old syntax has a closed set of seven names, so converting `{name}` to `{{ name }}` on read would be lossless.
**Fix:** Optionally migrate on read in `with_defaults`: replace each `_LEGACY_PLACEHOLDER` match with `{{ name }}` when the text contains no `{{` or `{%`. If this is intentionally a documented break (D-08), mention it in the release notes.

### IN-02: The preview renders descriptions and UIDs it never uses

**File:** `custom_components/xmltv_calendar/xmltv/preview.py:87`
**Issue:** `to_event_fields(...)["summary"]` also renders the description template and computes the UID for each of up to 10 programmes, then discards both. A failing description template is only logged at DEBUG for the nameless preview templates, so nothing breaks. The work is wasted and it couples the preview to description rendering.
**Fix:** Call `templates.render_title(programme, template_values(programme, channel, tz=tz))` directly.

### IN-03: Misleading comment and an unsynchronised flag

**File:** `custom_components/xmltv_calendar/xmltv/template_engine.py:312-313`, `render.py:179-192`
**Issue:** The docstring on `_check_chain_length` says "this runs once", but it runs for every filter link in a chain and re-counts each time. It is harmless because it is capped at 16, but the comment is wrong. Separately, `_RenderLog.failed` does a check-then-set on `warned` from executor threads (`build_events` runs templates in the executor for more than 200 programmes). Two threads can both log the WARNING, so "one WARNING per calendar" is only best-effort.
**Fix:** Reword the docstring. For the flag, either accept the race and document it, or guard it with a `threading.Lock`.

### IN-04: Edge-separator stripping can eat legitimate trailing characters, and the default description path is not cleaned

**File:** `custom_components/xmltv_calendar/xmltv/render.py:62-69, 259-264`
**Issue:** `_DESCRIPTION_END` and `_TITLE_EDGES` strip `- – — : , ; | · /` from the ends. A feed description that legitimately ends with `-`, `:` or `/` loses it. I confirmed that `clean_description("A\n\n\n\nB-")` returns `'A\n\nB'`. `default_description` is never passed through `clean_description`, so the same feed text is cut or kept depending on whether a template is set.
**Fix:** This is acceptable if intended, since D-22 describes it as dangling separators. Consider limiting the strip to separators that a template itself produced, or document the behaviour in the README.

---

_Reviewed: 2026-10-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
