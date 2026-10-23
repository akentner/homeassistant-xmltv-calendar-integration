# Phase 5: Richer title and description templating - Pattern Map

**Mapped:** 2026-10-23
**Files analyzed:** 12 (1 new library module, 6 modified source files, 2 translations, tests, docs)
**Analogs found:** 12 / 12 (all tracked under `custom_components/` and `tests/`; no gitignored mirrors involved)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `custom_components/xmltv_calendar/xmltv/template_engine.py` (NEW) | utility (pure library) | transform | `xmltv/render.py` (`TemplateError`, `compile_template`) + `xmltv/filter.py` (regex safety) | role-match |
| `custom_components/xmltv_calendar/xmltv/render.py` (MOD) | service (facade) | transform | itself (swap engine inside `EventTemplates`) | exact |
| `custom_components/xmltv_calendar/xmltv/settings.py` (MOD) | config | transform | itself (`DEFAULT_TITLE_TEMPLATE`, `with_defaults`) | exact |
| `custom_components/xmltv_calendar/xmltv/preview.py` (MOD) | utility | request-response | itself (line 81, 87) | exact |
| `custom_components/xmltv_calendar/calendar.py` (MOD) | component | request-response | itself (`_to_event`, `build_events`) | exact |
| `custom_components/xmltv_calendar/matcher.py` (MOD) | service | event-driven | itself (lines 130, 416-418, `describe_match`) | exact |
| `custom_components/xmltv_calendar/config_flow.py` (MOD) | controller (flow) | request-response | itself (`_advanced_errors`, `_ADVANCED_PLACEHOLDERS`) | exact |
| `translations/en.json`, `de.json` (MOD) | config | n/a | existing `error.*` / help text keys | exact |
| `tests/xmltv/test_render.py`, new `tests/xmltv/test_template_engine.py` | test | transform | `tests/xmltv/test_render.py` | exact |
| `tests/test_translations.py` (MOD) | test | n/a | itself (line 304) | exact |
| `tests/xmltv/test_purity.py` | test | n/a | unchanged, covers new module via `rglob` | exact |
| `README.md`, `REQUIREMENTS.md`, `PROJECT.md`, `.claude/CLAUDE.md` (MOD) | docs | n/a | existing sections | exact |

## Pattern Assignments

### `xmltv/template_engine.py` (NEW, utility, transform)

**Analog:** `xmltv/render.py` lines 23-27, 51-77 for the error type and compile shape, `xmltv/filter.py` for regex safety.

**TemplateError to carry over** (render.py 51-58; re-export from render.py so `config_flow.py` imports barely change):
```python
class TemplateError(ValueError):
    """A template that cannot be used; `reason` is a flow error key, `detail` the offending part."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail
```
Reason constants follow render.py 23-25 (`INVALID_TEMPLATE = "invalid_template"`, `UNKNOWN_PLACEHOLDER = "unknown_placeholder"`). Add `UNSUPPORTED_SYNTAX`, `UNKNOWN_FILTER`, `LEGACY_PLACEHOLDER`, `TEMPLATE_RUNTIME_ERROR` and export a `TEMPLATE_ERROR_REASONS` tuple (RESEARCH Pitfall 9).

**Regex safety to reuse** (filter.py 48-55, 169-180): import `MAX_PATTERN_LENGTH`, `PATTERN_ERRORS`, `has_nested_repeat` from `.filter`.
```python
MAX_PATTERN_LENGTH = 300
PATTERN_ERRORS: tuple[type[Exception], ...] = (re.error, OverflowError, RecursionError)
def has_nested_repeat(pattern: str) -> bool: ...
```
Multi-exception clauses use the unparenthesized PEP 758 form (filter.py `except ImportError, AttributeError, ...:`).

**Core pattern:** no in-repo Jinja analog. Use RESEARCH Pattern 1 (env), Pattern 2 (`ALLOWED_NODES`, `_check_ast`, `compile_template`) and Pattern 6 (filters) verbatim. Purity rule: `tests/xmltv/test_purity.py` forbids `homeassistant` imports under `xmltv/`; jinja2 is allowed.

### `xmltv/render.py` (MOD, facade, transform)

**Keep unchanged:** `clean_title`/`clean_description` (85-93), `default_description` (96-108), `event_uid` (164-168, hashes raw title, must stay), the regexes at 31-39.

**Remove:** `TITLE_FIELDS`/`DESCRIPTION_FIELDS` (20-21, merge into one `VARIABLES`), `CompiledTemplate`, `_FORMATTER`, old `compile_template(text, allowed)`, `render_template` (61-82).

**Stored-template pattern to keep** (124-130):
```python
def _stored[T](text, allowed, default, name) -> CompiledTemplate | T:
    try:
        return compile_template(text, allowed)
    except TemplateError:
        _LOGGER.warning("Invalid stored %s template, using the default", name)
        return default
```
New `from_mapping(data, name=None)` keeps this failure mode; legacy and uncompilable text fall back with one WARNING (silent when `name is None`, as preview needs).

**Class boundary to preserve** (133-158): frozen slots dataclass with `from_mapping`, `render_title(programme, values)`, `render_description(programme, values)`. Change: compare on source strings, `compiled` fields `compare=False` (matcher.py 416-418 does `templates != self._templates`). Render methods catch `Exception  # noqa: BLE001`, warn once, fall back to `programme.title` / `default_description(programme)`.

**Signature to preserve** (171-181):
```python
def to_event_fields(programme, channel, templates: EventTemplates = DEFAULT_TEMPLATES) -> EventFields:
    values = template_values(programme, channel)
    return EventFields(summary=templates.render_title(programme, values), location=values["channel"],
                       description=templates.render_description(programme, values), uid=event_uid(programme))
```
Add keyword `tz: tzinfo | None = None` (also on `template_values`); `location=values["channel"]` stays. `template_values` (111-121) gains `titles`, `subtitles`, `categories` (lists), `start`, `end`, with `description` in both templates. `DEFAULT_TEMPLATES` (161) must be rebuilt with the new compile.

### `xmltv/settings.py` (MOD, config)

**Lines 49, 150-153:**
```python
DEFAULT_TITLE_TEMPLATE = "{channel}: {title}"  # D-20
...
KEY_TITLE_TEMPLATE: title_template if title_template.strip() else DEFAULT_TITLE_TEMPLATE,
```
Set `DEFAULT_TITLE_TEMPLATE = "{{ channel }}: {{ title }}"`, add `LEGACY_DEFAULT_TITLE_TEMPLATE = "{channel}: {title}"` and map that exact stored string to the new default silently inside `with_defaults` (otherwise `has_advanced()` at 157-160 flips on and every start warns; RESEARCH Pattern 5). Storage keys unchanged, no VERSION bump.

### `xmltv/preview.py` (MOD)

**Lines 81-87:** `templates = EventTemplates.from_mapping(data)` (no name, stays quiet) and `to_event_fields(programme, channel, templates)["summary"]`. Pass the already available `tz=tz` into `to_event_fields`.

### `calendar.py` (MOD)

**Lines 37-57:** `_to_event` calls `render.to_event_fields(programme, channels.get(...), templates)` and `build_events` loops with `except HomeAssistantError, OverflowError, ValueError`. Add a `tz` argument to `build_events`; resolve `dt_util.get_default_time_zone()` once on the loop and pass down, since `build_events` runs in the executor above `EXECUTOR_BUILD_THRESHOLD = 200`. Pass `name` (calendar title) into `from_mapping` at the construction site in `matcher.py`.

### `matcher.py` (MOD)

**Lines 130, 416-418:** `render.EventTemplates.from_mapping(subentry.data)` at both sites; `write_state = templates != self._templates` depends on source-string equality. `describe_match` (about 368-387) reads rendered `summary`: pass `tz` there. No template-dependent persisted state (`matches.py` 68 uses `event_uid`). Add regression test: edit title template, no `xmltv_calendar_new_match`, UIDs unchanged.

### `config_flow.py` (MOD, controller)

**Placeholders** (441-447): collapse `title_fields`/`description_fields` into one `variables` value passed as a placeholder value because a literal `{{ x }}` in a translation breaks ICU parity:
```python
_ADVANCED_PLACEHOLDERS = {"title_fields": ..., "description_fields": ..., "default_title": DEFAULT_TITLE_TEMPLATE}
```

**Validation** (543-551), keep the shape, drop `allowed`:
```python
templates = [(CONF_TITLE_TEMPLATE, TITLE_FIELDS)]
if values[CONF_DESCRIPTION_TEMPLATE].strip():
    templates.append((CONF_DESCRIPTION_TEMPLATE, DESCRIPTION_FIELDS))
for field, allowed in templates:
    try:
        compile_template(values[field], allowed)
    except TemplateError as err:
        errors[field] = err.reason
        placeholders.setdefault("template_error", err.detail)
```
Add trial render (full and sparse sample programme) after successful compile, mapping to `template_runtime_error`. Line 513 `CONF_TITLE_TEMPLATE: title_template or DEFAULT_TITLE_TEMPLATE` stays.

### `translations/en.json`, `de.json` (MOD)

Add `error` keys for every entry in `TEMPLATE_ERROR_REASONS` under the subentry flow (same location as existing `invalid_template`/`unknown_placeholder`; locate with `grep -n unknown_placeholder`). Update field help to point at the README, no literal `{{ }}`.

### Tests (MOD/NEW)

**Analog:** `tests/xmltv/test_render.py` 122-124:
```python
def _title(template: str, programme: Programme) -> str:
    templates = EventTemplates(title=compile_template(template, TITLE_FIELDS))
    return to_event_fields(programme, CHANNELS.get(programme.channel_id), templates)["summary"]
```
Rewrite with the new compile signature and the parametrized `("template","programme","expected")` table (128-143) plus the error table (148). `tests/test_translations.py` line 304 replace the hand list `(render.INVALID_TEMPLATE, render.UNKNOWN_PLACEHOLDER, "invalid_regex")` with iteration over `TEMPLATE_ERROR_REASONS` plus `"invalid_regex"`. Other files needing syntax updates: `tests/test_advanced_flow.py`, `tests/xmltv/test_settings.py`, `tests/test_templates.py`, `tests/test_matcher_races.py`, `tests/test_reconfigure.py`, `tests/xmltv/test_preview.py`, `tests/xmltv/test_parser.py`.

## Shared Patterns

### Fail-soft on stored data
**Source:** `xmltv/render.py` 124-130. **Apply to:** `EventTemplates.from_mapping`, legacy detection. WARNING contains no feed text.

### Flow error = key + `template_error` placeholder
**Source:** `config_flow.py` 543-551. **Apply to:** all new reasons.

### Broad-except with justification
**Source:** Phase 3 `_async_update_data` pattern (`# noqa: BLE001 - reason`). **Apply to:** render fallbacks.

### Purity
**Source:** `tests/xmltv/test_purity.py` 23-33. **Apply to:** `template_engine.py` (no `homeassistant` imports; local zone passed in as `tzinfo`).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `template_engine.py` Jinja env, AST whitelist, custom filters | utility | transform | No Jinja usage in the repo; use RESEARCH Patterns 1, 2, 6 (prototype-verified). Regex-validation parts do have analogs in `filter.py`. |

## Metadata

**Analog search scope:** `custom_components/xmltv_calendar/`, `tests/`
**Files scanned:** about 15 read or grepped
**Pattern extraction date:** 2026-10-23
