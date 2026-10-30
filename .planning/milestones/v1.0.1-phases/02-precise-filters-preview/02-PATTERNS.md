# Phase 2: Precise Filters & Preview - Pattern Map

**Mapped:** 2026-10-15
**Files analyzed:** 17 (9 source, 8 test)
**Analogs found:** 17 / 17. Every file is a modification of, or a sibling to, existing tracked code. The only new module, `xmltv/preview.py`, is optional.

All analog paths are git-tracked (verified with `git ls-files`).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `custom_components/xmltv_calendar/xmltv/filter.py` (mod) | utility (pure lib) | transform/batch | itself (`FilterSpec`, `compile_patterns`, `first_invalid_pattern`) | exact |
| `custom_components/xmltv_calendar/xmltv/render.py` (mod) | utility (pure lib) | transform | itself (`to_event_fields`, `event_uid`) | exact |
| `custom_components/xmltv_calendar/xmltv/window.py` (mod) | utility (pure lib) | query | `MatchIndex.current_or_next` (lines 39-44) | exact |
| `custom_components/xmltv_calendar/xmltv/parser.py` (mod, `_text`) | utility (pure lib) | streaming parse | `_text` lines 55-56 | exact |
| `custom_components/xmltv_calendar/xmltv/preview.py` (new, optional) | utility (pure lib) | transform | `xmltv/render.py` | role-match |
| `custom_components/xmltv_calendar/const.py` (mod) | config | — | lines 7, 21-24, `__all__` | exact |
| `custom_components/xmltv_calendar/config_flow.py` (mod, `CalendarSubentryFlow`) | controller (flow) | request-response, multi-step | `CalendarSubentryFlow.async_step_user` (189-237) + `XmltvConfigFlow` multi-step `_data` state (84-176) + menu (90-92) | exact |
| `custom_components/xmltv_calendar/calendar.py` (mod) | entity/provider | event-driven | `XmltvCalendarEntity._async_refilter` (111-131) | exact |
| `custom_components/xmltv_calendar/__init__.py` (mod, listener) | service glue | event-driven | `_async_entry_updated` (32-46) | exact |
| `custom_components/xmltv_calendar/translations/en.json` (mod) | config | — | `config_subentries.calendar` block | exact |
| `tests/conftest.py` (mod: `complete_calendar_flow` helper) | test fixture | — | `setup_xmltv` factory fixture (lines 53-79) | exact |
| `tests/xmltv/test_filter.py` (mod) | test (pure) | — | itself, parametrized truth table | exact |
| `tests/xmltv/test_render.py` (mod) | test (pure) | — | itself | exact |
| `tests/xmltv/test_window.py` (mod) | test (pure) | — | itself | exact |
| `tests/xmltv/test_parser.py` (mod, NFD fixture) | test (pure) | — | itself | exact |
| `tests/test_subentry_flow.py`, `tests/test_init.py`, `tests/test_tracer.py` (mod) | test (HA) | — | `test_subentry_flow.py` lines 85-140 | exact |
| `tests/test_reconfigure.py` (new, or part of test_subentry_flow.py) | test (HA) | — | `test_subentry_flow.py` + RESEARCH "Reconfigure test" example | role-match |

---

## Pattern Assignments

### `xmltv/filter.py` (pure lib, transform)

**Analog:** itself. Keep all existing names (`KEY_*`, `MAX_PATTERN_*`, `InvalidPattern`, `FilterResult`, `FilterSpec.from_mapping`, `apply`). Extend; never rename (D-06 stored contract).

**Key constants pattern** (lines 11-18). Add the new keys in the same style (`KEY_INCLUDE_FIELDS = "include_fields"` and so on), then re-export them from `const.py`:
```python
KEY_CHANNELS = "channels"
KEY_CHANNEL_REGEX = "channel_regex"
KEY_INCLUDE = "include"
KEY_EXCLUDE = "exclude"

# Cheap ReDoS dampener for admin-supplied patterns (T-01-06); matching runs in the executor anyway
MAX_PATTERN_LENGTH = 300
MAX_PATTERN_LINES = 50
```

**Compile + validate pair** (lines 41-57). Add `case_sensitive: bool = False` to both, NFC each line with `unicodedata.normalize`, and add the nested-repeat check (RESEARCH Pattern 9) inside the `try`. Reuse the `InvalidPattern(pattern=, message=)` return shape:
```python
def compile_patterns(text: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(line, re.IGNORECASE) for line in _lines(text))

def first_invalid_pattern(text: str) -> InvalidPattern | None:
    for index, line in enumerate(_lines(text)):
        if index >= MAX_PATTERN_LINES:
            return InvalidPattern(pattern=line, message=f"more than {MAX_PATTERN_LINES} patterns")
        ...
        try:
            re.compile(line, re.IGNORECASE)
        except re.error as err:
            return InvalidPattern(pattern=line, message=err.msg)
    return None
```

**Tolerant readers** (lines 60-78). Read new keys with the same approach: wrong type means default (`_str_set`, `_text`). Add `_int_or_none` and `_time_or_none` helpers in the same style.

**Field extraction to replace** (lines 68-74). `_fields(programme)` becomes `_field_values(programme, fields)` (RESEARCH Pattern 2), and `_any_match` takes an iterable. Keep short-circuiting with `any()`, and keep description last.

**Frozen dataclass + `from_mapping`** (lines 81-98). Add fields with defaults so existing `FilterSpec(channels=...)` tests remain valid:
```python
@dataclass(frozen=True)
class FilterSpec:
    channels: frozenset[str]
    channel_patterns: tuple[re.Pattern[str], ...] = ()
    include: tuple[re.Pattern[str], ...] = ()
    exclude: tuple[re.Pattern[str], ...] = ()

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> FilterSpec:
        return cls(
            channels=_str_set(data.get(KEY_CHANNELS)),
            channel_patterns=compile_patterns(_text(data.get(KEY_CHANNEL_REGEX))),
            ...
```
Note: `channel_patterns` must stay case-insensitive regardless of the `case_sensitive` flag, because D-08 scopes that flag to include/exclude only.

**apply loop with per-channel cache** (lines 112-123). Add `*, tz: tzinfo = UTC`, and insert duration and window/weekday checks between `channel_ok` and `_text_matches` (cheapest first). Compute duration on the raw `programme.stop - programme.start`, never on local datetimes (Pitfall 6):
```python
for programme in epg.programmes:
    channel_ok = selected.get(programme.channel_id)
    if channel_ok is None:
        channel_ok = selected[programme.channel_id] = self._channel_selected(programme.channel_id)
    if channel_ok and self._text_matches(programme):
        matches.append(programme)
```
`TimeWindow` (RESEARCH Pattern 4) goes in this module as a `@dataclass(frozen=True, slots=True)`, the same decorator as `InvalidPattern` (line 21).

---

### `xmltv/render.py` (pure lib, transform)

**Analog:** itself.

**Signature to extend** (lines 26-34). Add `templates: EventTemplates = DEFAULT_TEMPLATES` as a default kwarg so `calendar.py:44` and the existing tests still work. Keep `uid=event_uid(programme)` (it hashes the raw title, lines 20-23):
```python
def to_event_fields(programme: Programme, channel: Channel | None) -> EventFields:
    location = channel.display_name if channel is not None else programme.channel_id
    return EventFields(
        summary=f"{location}: {programme.title}",
        location=location,
        description=programme.description,
        uid=event_uid(programme),
    )
```
`TemplateError(ValueError)`, `compile_template`, `render`, the cleanup regexes and `default_description` follow RESEARCH Pattern 8. Module-level compiled regexes and `_FORMATTER` match the module-level `_START` constant style in `window.py:14`. Put `TYPE_CHECKING` imports at the top, as in lines 7-8.

---

### `xmltv/window.py` (pure lib, query)

**Analog:** `MatchIndex.current_or_next` (lines 39-44). Model `upcoming(now, limit) -> tuple[int, list[Programme]]` on the same bisect start and `stop > now` scan:
```python
def current_or_next(self, now: datetime) -> Programme | None:
    for i in range(bisect_left(self._starts, now - self._max_duration), len(self._programmes)):
        if (programme := self._programmes[i]).stop > now:
            return programme
    return None
```
For the IN-14 OverflowError clamp: `now - self._max_duration` (lines 35 and 41) can overflow near `datetime.min`. Wrap it in a small `_lower_bound(t)` helper that catches `OverflowError` and returns `0`, and use it in all three methods.

---

### `xmltv/parser.py` (`_text`, lines 55-56)

```python
def _text(elem: ET.Element) -> str:
    return (elem.text or "").strip()
```
Change it to `unicodedata.normalize("NFC", (elem.text or "").strip())`. `_texts` and `_first` (59-65) inherit the change. Check whether channel IDs (line 69, `elem.get("id")`) should stay un-normalized. Recommendation: leave IDs as they are, because they are used as stored keys.

---

### `xmltv/preview.py` (new, optional, pure)

**Analog:** `xmltv/render.py` (pure, `TYPE_CHECKING` model imports, module-level constants). Contents:
- weekday table keyed by language
- Markdown escape (Pitfall 8)
- `format_line(programme, channel, title, tz, language)`
- `build_preview(data, epg, now, tz, limit)`, which calls `FilterSpec.from_mapping(data).apply(epg, tz=tz)` → `MatchIndex(...).upcoming(now, limit)`.

`tests/xmltv/test_purity.py` enforces no `homeassistant` imports automatically (it uses `rglob`).

---

### `const.py` (config)

**Analog:** lines 7 and 21-24, plus `__all__` (29-48). Re-export the library keys under `CONF_*` names and add them to `__all__`:
```python
from .xmltv.filter import KEY_CHANNEL_REGEX, KEY_CHANNELS, KEY_EXCLUDE, KEY_INCLUDE
...
CONF_CHANNELS = KEY_CHANNELS
CONF_INCLUDE = KEY_INCLUDE
```
Add the HA-only constants `CONF_ADVANCED = "advanced"` (not stored, D-03) and `PREVIEW_LIMIT = 10`. Put the template keys and defaults in `render.py` (as `KEY_TITLE_TEMPLATE` and so on) and re-export them here the same way.

---

### `config_flow.py` → `CalendarSubentryFlow` (controller, multi-step)

**Analog A, the existing calendar step** (lines 189-237). Copy the loaded-guard, the error/placeholder loop and the schema shape into `async_step_basic`:
```python
entry: XmltvConfigEntry = self._get_entry()
if entry.state is not ConfigEntryState.LOADED:
    return self.async_abort(reason="source_not_loaded")

errors: dict[str, str] = {}
placeholders: dict[str, str] = {}
if user_input is not None:
    ...
    for field in _PATTERN_FIELDS:
        if (bad := first_invalid_pattern(str(user_input.get(field, "")))) is not None:
            errors[field] = "invalid_regex"
            placeholders.setdefault("pattern", bad.pattern)
            placeholders.setdefault("error", bad.message)
```
Changes required:
- `step_id="user"` → `"basic"`.
- The `vol.Optional(field, default="")` on lines 219 and 228 must become `vol.Optional(field)` plus `add_suggested_values_to_schema(schema, self._pending)`, so reconfigure pre-fills and fields can be cleared (RESEARCH Pattern 6).
- `first_invalid_pattern` must receive the pending `case_sensitive` value.
- Template errors use separate placeholders `template_error`/`template_field` (Pitfall 12).

**Analog B, multi-step state on the instance** (`XmltvConfigFlow.__init__`, lines 84-88, and the hand-off at 112-115):
```python
def __init__(self) -> None:
    self._data: dict[str, Any] = {}
    self._options: dict[str, Any] = {}
    self._suggested_name = ""
...
    self._data = {...}
    return await self.async_step_name()
```
Use this for `self._pending` and `self._show_advanced`, and for `basic` → `return await self.async_step_advanced()` / `self.async_step_preview()`.

**Analog C, menu step** (lines 90-92). The preview uses the same API plus `description_placeholders`:
```python
return self.async_show_menu(step_id="user", menu_options=[SOURCE_TYPE_URL, SOURCE_TYPE_FILE])
```

**Analog D, executor offload** (line 133). Run the preview computation this way:
```python
real_path = await self.hass.async_add_executor_job(check_file, self.hass.config, path)
```

**Selector style** (lines 66-76, 220-226). Mirror these for the NumberSelector (duration, `unit_of_measurement="min"`, `mode=BOX`) and the SelectSelector (fields/weekdays with `translation_key=`, `multiple=True`).

**Save branching.** `async_create_entry` when `self.source == SOURCE_USER`, otherwise `async_update_and_abort(self._get_entry(), self._get_reconfigure_subentry(), title=, data=)`. Alias it with `async_step_user = async_step_reconfigure = async_step_basic`. Ruff: keep the `# noqa: ARG002` convention (line 90) on steps that ignore `user_input` (`save`, `back`).

---

### `calendar.py` (entity, event-driven)

**Analog:** `_async_refilter` with generation counter (lines 111-131):
```python
self._generation += 1
generation = self._generation
epg = self.coordinator.data
if epg is None:
    return
subentry = self._entry.subentries.get(self._subentry_id)
spec = FilterSpec.from_mapping(subentry.data if subentry is not None else self._subentry_data)
result = await self.hass.async_add_executor_job(spec.apply, epg)
if generation != self._generation:
    return
```
Changes:
- Lines 118-119 become `self._config.spec`; the spec is built once in `__init__`/`async_apply_subentry`, which gives one source of truth.
- Pass the tz: `async_add_executor_job(partial(spec.apply, epg, tz=dt_util.get_default_time_zone()))`. `async_add_executor_job` does not take kwargs, so use `functools.partial`.
- `__init__` (83-97) already stores `self._subentry_data = subentry.data`. Extend it to `(title, data)` for `differs_from`.
- `_to_event`/`build_events` (40-58) gain a `templates` parameter, which is threaded through `event` (141) and `async_get_events` (166-167).
- Keep the `except HomeAssistantError, OverflowError, ValueError:` style (Py3.14 unparenthesized, lines 56 and 142).

New `async_apply_subentry`:
- Device rename via `dr.async_get(self.hass)`.
- `if self.hass is None: return` guard (Pitfall 10), before `_async_refilter()`.
- Mirror the `async_create_task` usage on line 109 only if fire-and-forget is needed. Awaiting is preferred, because the listener is async.

---

### `__init__.py` (listener, event-driven)

**Analog:** `_async_entry_updated` (lines 32-46). Insert the "changed existing calendars" loop after the removal loop (line 39) and before the `add_entities is None` guard (line 40). Changed calendars must be applied even when the platform isn't set up yet:
```python
for subentry_id in set(runtime.calendars) - set(entry.subentries):
    runtime.calendars.pop(subentry_id)  # HA already removed the entity and its device
if runtime.add_entities is None:
    return
```
Update the comment on line 26 ("subentry add/remove and title changes") to cover data changes as well.

---

### `translations/en.json`

**Analog:** the existing `config_subentries.calendar` block.
- Rename `step.user` → `step.basic`.
- Add `advanced`, `preview` and `preview_empty` (each with `description` + `menu_options.save/back`).
- Add `initiate_flow.reconfigure`, abort `reconfigure_successful`, and new errors (`invalid_template`, `unknown_placeholder`, `time_incomplete`, `time_equal`, `duration_order`, `fields_required`).
- Add a top-level `"selector": {"match_fields": {"options": {...}}, "weekdays": {"options": {...}}}`.
- Literal `{channel}` text must go through a `{placeholders}` placeholder (ICU).
- The existing data_description texts say "title or sub-title (case-insensitive)". Update them to reference the field selection.

---

### `tests/conftest.py` (helper)

**Analog:** the `setup_xmltv` factory fixture (lines 53-79): a fixture returning an inner `async def _setup(...)`. Build `complete_calendar_flow` the same way, or as a plain module-level async function. It should:
1. `hass.config_entries.subentries.async_init((entry.entry_id, "calendar"), context={"source": SOURCE_USER})`
2. `async_configure(basic)`
3. if `advanced`: `async_configure(advanced)`
4. assert `MENU`
5. `async_configure({"next_step_id": "save"})`

Use the `berlin_tz` fixture (lines 46-49) for window tests.

### HA tests to migrate

**Analog:** `tests/test_subentry_flow.py` lines 85-140. These lines use `freezer.move_to(NOW)`, `setup_xmltv(FEED, calendars=())`, `_submit(...)`, `assert result["type"] is FlowResultType.CREATE_ENTRY`, then `_summaries(hass, "calendar.x")`.
- The `result["data"] == {...4 keys}` assertion (around lines 98-103) must become the full key set.
- Pitfall 2 lists the one-shot submits: `test_subentry_flow.py` 97, 135, 206, 220, 250, 313; `test_init.py` 69, 227; `test_tracer.py` 71.

### Pure tests

Analog: `tests/xmltv/test_filter.py`. It imports `FilterSpec, first_invalid_pattern` and model classes directly, and uses a parametrized `test_truth_table` (line 76). Add D-11 window tables, the ReDoS table and NFD cases as new parametrized tests in the same file.

---

## Shared Patterns

### Pure-library boundary
**Source:** `tests/xmltv/test_purity.py` (AST scan of `xmltv/**/*.py`).
**Apply to:** filter.py, render.py, window.py, parser.py, preview.py.
- No `homeassistant` imports.
- The tz is passed in (`dt_util.get_default_time_zone()` from the glue).
- The weekday tuple is duplicated, with an equality test against `homeassistant.const.WEEKDAYS` in an HA-side test.

### Executor offload
**Source:** `calendar.py:120`, `calendar.py:166`, `config_flow.py:133`.
**Apply to:** the refilter in the entity, the preview step and `async_apply_subentry`. Never scan `coordinator.data` on the loop.

### Loaded-source guard
**Source:** `config_flow.py:195-197`.
**Apply to:** the `basic`, `preview` and `save` steps.

### Tolerant read of stored data (D-06)
**Source:** `filter.py:60-65, 77-78` (`_str_set`, `_text`).
**Apply to:** every new subentry key, for both `FilterSpec.from_mapping` and the template config. Missing or wrong-typed values fall back to the default. Never raise.

### Error-key + placeholder convention
**Source:** `config_flow.py:205-209` with en.json `error.invalid_regex`.
**Apply to:** all new validation errors. Use per-field keys in `errors`, and fill placeholders with `setdefault`.

### Skip-bad-programme guard
**Source:** `calendar.py:56, 142`.
**Apply to:** template rendering in events. A broken template config falls back to the default (Pitfall 3).

## No Analog Found

| File | Role | Reason |
|---|---|---|
| nested-repeat ReDoS checker (inside filter.py) | utility | No `re._parser` usage in the repo. Use RESEARCH Pattern 9 verbatim |
| `CompiledTemplate` / `string.Formatter().parse` (inside render.py) | utility | No templating exists yet. Use RESEARCH Pattern 8 |
| Reconfigure / `async_update_and_abort` / device rename | flow / entity | First use in the repo. Use RESEARCH Pattern 6/7 and the reconfigure test example |

## Metadata

**Analog search scope:** `custom_components/xmltv_calendar/**`, `tests/**`
**Files scanned:** 14
**Pattern extraction date:** 2026-10-15
