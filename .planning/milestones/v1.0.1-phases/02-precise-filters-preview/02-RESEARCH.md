# Phase 2: Precise Filters & Preview - Research

**Researched:** 2026-10-15
**Domain:** HA config subentry flows (multi-step, menu, reconfigure), in-place entity updates via the update listener, pure-Python filtering (regex/Unicode/time windows), restricted string templating
**Confidence:** HIGH. All HA APIs were read from the installed HA 2026.10.1 source; the library approach rests on local experiments with Python 3.14.7.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Flow structure
- **D-01:** The calendar subentry flow (add **and** reconfigure) has these steps:
  1. **Basic step:** name, channels, channel regex, include, exclude. Same fields as Phase 1, plus a checkbox "Advanced options".
  2. **Advanced step:** shown only when the checkbox is set.
  3. **Preview step:** always shown. Saving happens only from the preview step.
- **D-02:** The advanced step contains:
  - include fields and exclude fields
  - case-sensitive toggle
  - time window (from/to) and weekdays
  - min/max duration
  - title template and description template
- **D-03:** On reconfigure, the "Advanced options" checkbox is pre-checked when the calendar has any advanced value that differs from the defaults. Unchecking it **keeps** the stored advanced values. It only skips the step, it never resets them.
- **D-04:** Reconfigure ends via `async_update_and_abort`. The existing single diffing update listener (`__init__.py:_async_entry_updated`) must handle changed subentry data by updating the existing entity in place (rebuild its `FilterSpec`/templates, recompute matches from `coordinator.data`). It must not reload the entry. A source data/options change still reloads.

#### Field selection & case
- **D-05:** Field selection uses two multi-selects, "Include matches fields" and "Exclude matches fields". Options: title, sub-title, description, category. The default for both is title + sub-title, which is the Phase 1 behaviour.
- **D-06:** Subentries stored by Phase 1 (without the new keys) must behave exactly as before. Missing keys mean defaults. — **Reversibility:** costly — the new subentry data keys become a stored contract. Renaming them later needs a subentry data migration.
- **D-07:** Multi-valued fields are matched element by element: each category and each sub-title is tested on its own, and one hit is enough. This keeps anchors like `^Sport$` working.
- **D-08:** Matching is case-insensitive by default. The case-sensitive toggle sits in the advanced step and applies to include and exclude of that calendar. Text and patterns are Unicode-normalized (NFC per roadmap notes) before matching, so umlauts match regardless of composed or decomposed form.

#### Time window, weekdays, duration
- **D-09:** A programme passes the time window when its **start time** falls within the window. Overlap and full containment are not used.
- **D-10:** The window and weekdays are evaluated in the **HA configured timezone** (start converted with `dt_util.as_local` or the equivalent).
- **D-11:** For windows that cross midnight (e.g. 22:00–02:00), the weekday is **the day the window starts**. With weekday Fri and window 22:00–02:00, a programme starting Sat 01:00 matches (it counts as "Friday night"). A Fri 01:00 start does not match.
- **D-12:** Window and weekday input rules:
  - Empty weekdays mean all days.
  - Empty from/to means no time restriction.
  - from and to must be given together.
  - from == to is rejected in the flow.
- **D-13:** Duration is set with two optional number fields in **minutes** (min and max). Empty means unbounded. The bounds are inclusive (`min ≤ duration ≤ max`), and the flow validates min ≤ max. Duration = stop − start, including inferred stops. The max-duration filter also covers the accepted Phase 1 review item WR-07, where an absurd in-window stop showed up.
- **D-14:** A programme must satisfy every configured constraint (channel AND include AND NOT exclude AND duration AND window/weekday).

#### Preview
- **D-15:** The preview is a separate flow step. It shows the match count and the next 10 matches. The actions are **Save** and **Back**. Back returns to the basic step with the entered values pre-filled, including the advanced values.
- **D-16:** The preview covers matches from now onwards (running programmes included), across the whole loaded feed (`coordinator.data`), sorted by start. This is the same match logic the calendar entity uses.
- **D-17:** Each preview line reads `<weekday> <dd.mm.> <HH:MM> · <channel display name> · <rendered event title>`, in local HA time. Because the title is rendered with the entered title template, the preview also checks the template.
- **D-18:** With 0 matches the preview shows a warning ("currently no matches in the feed"), but saving is still allowed.
- **D-19:** The preview runs for both new calendars and reconfigure.

#### Templates
- **D-20:** Both templates are set in the advanced step. The default title template is `{channel}: {title}`. An empty description template means the default description.
- **D-21:** Placeholders for both templates are `{channel}`, `{title}`, `{subtitle}`, `{episode}`, `{category}` and `{channel_id}`. `{description}` is available in the description template only. Unknown placeholders are rejected in the flow, and so are field names containing `.` or `[`.
  - Multiple categories are joined as `"A, B"`.
  - `{subtitle}` is the first sub-title.
  - `{episode}` stays the raw first episode-num, because normalization is EVT-09 (v2).
  - `{channel}` is the display name, falling back to the ID.
- **D-22:** Missing values render as `""`. After rendering, separators left dangling at the start or end (e.g. ` – `, ` - `, `: `, `, `) are stripped and repeated whitespace is collapsed, so `{title} – {subtitle}` without a sub-title gives `Tatort`.
- **D-23:** The default description (no template) is made of lines, and lines without data are dropped together with their label:
  ```
  <sub-title>
  Episode: <episode>
  Categories: <A, B>

  <description>
  ```
  The labels are fixed in English, because event text is not translated.

### Claude's Discretion
- Exact NFC vs NFC+casefold strategy, as long as D-08 holds and patterns stay valid regex.
- ReDoS hardening beyond the existing caps (`MAX_PATTERN_LENGTH`, `MAX_PATTERN_LINES`).
- Selector widget for the time window (TimeSelector) and weekdays (multi-select with translated labels).
- Exact separator set for D-22 cleanup.
- How the preview step renders the list (description placeholders with a markdown list, etc.) and the button mechanics for Back/Save (e.g. menu step or a form with a boolean).
- Whether the preview computation runs in the executor (it should if it scans the full feed).

### Deferred Ideas (OUT OF SCOPE)
- Time placeholders (`{start}`, `{end}`, `{duration}`) in templates: considered but not chosen. Possible later addition.
- Real live preview while typing (WebSocket preview component): rejected because it is not practical for custom integrations.

Also out of scope (from the CONTEXT domain section): category picker (FLT-12), new/premiere tags (FLT-13), language preference (FLT-14), episode normalization (EVT-09), timezone options and anything source-side (Phase 3).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FLT-05 | Choose which fields include/exclude apply to (title, sub-title, description, category), separately | Pattern 2 (`FilterSpec` field sets, element-wise matching); flow field `SelectSelector(multiple, translation_key)`; Pitfall 7 (description scan cost) |
| FLT-06 | Case-insensitive by default with a case toggle; umlauts match regardless of normalization | Pattern 3 (NFC at parse time + NFC'd patterns, `re.IGNORECASE`, no casefold); Pitfall 4 (casefold breaks `\S`/`\D`) |
| FLT-08 | Min/max programme duration | Pattern 2 (`stop - start` on fixed-offset datetimes, inclusive bounds); Pitfall 6 (same-tzinfo subtraction) |
| FLT-09 | Time window (may cross midnight) and weekdays | Pattern 4 (`TimeWindow.anchor_date`, half-open window, weekday = anchor day); Open Question 1 (end inclusivity) |
| FLT-10 | Preview in the flow: match count + next ~10 matches with channel and time | Pattern 5 (menu step `preview` / `preview_empty`, markdown list in `description_placeholders`, executor computation via `MatchIndex.upcoming`) |
| FLT-11 | Edit all filters of an existing calendar without re-download or re-parse | Pattern 6 (`async_step_reconfigure` alias, `async_update_and_abort`), Pattern 7 (listener diff → `entity.async_apply_subentry`), Pitfall 1 (`async_update_reload_and_abort` raises with listeners) |
| EVT-03 | Title template with placeholders; default `{channel}: {title}`; unknown placeholders rejected | Pattern 8 (`string.Formatter().parse` → compiled parts, render by join); Pitfall 3 (format-spec memory DoS, attribute traversal) |
| EVT-04 | Default description with sub-title/episode/categories/description; optional description template | Pattern 8 (`default_description`, D-23); Pitfall 9 (whitespace collapse must not eat newlines) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Directives from `./.claude/CLAUDE.md`, `~/Projects/CLAUDE.md` and `~/CLAUDE.md` that the planner must honour:

- **No runtime requirements.** `manifest.json` `"requirements": []`. Stdlib only (`re`, `unicodedata`, `string`, `zoneinfo`/`datetime`). Do **not** add the `regex` package for timeouts.
- **Config Flow + Options/Subentry flows only.** No YAML.
- **No Jinja templates.** Titles use a restricted `str.format`-style formatter that rejects field names containing `.` or `[`, with missing fields rendered as `""`.
- **Never use `OptionsFlowWithReload`.** Use exactly one diffing update listener (STATE.md decision; Phase 3 also uses a plain `OptionsFlow`).
- **No blocking work on the event loop.** Matching runs over the full feed (120k programmes), so it must run in the executor.
- **Python 3.14, Ruff 0.17.0** with `select = ["ALL"]`, line length 120, `target-version = "py314"`. Pinned dev deps: `pytest-homeassistant-custom-component==0.13.372` (HA 2026.10.1).
- **Pure `xmltv/` library:** no `homeassistant` imports. `tests/xmltv/test_purity.py` enforces this, and the library is built test-first (`tdd_mode: true` in config).
- **English** for code, comments and commits. Event text labels are English (D-23).
- **Keep `import voluptuous as vol`** in flows. Under HA 2026.10 it is aliased to probatio (see State of the Art). Don't assert on validation message text.
- **Work goes through the GSD workflow**. Make minimal, atomic commits.

## Summary

Every HA mechanism this phase needs exists in HA 2026.10.1 and was read from the installed source:
- **Subentry reconfigure.** `async_step_reconfigure`, `_get_reconfigure_subentry()`, `async_update_and_abort()`. The frontend shows "Reconfigure" iff the flow class has `async_step_reconfigure`.
- **Menu steps.** `async_show_menu(description_placeholders=...)`. The frontend renders the description as Markdown with line breaks.
- **Update listener.** `async_update_subentry` fires the entry's update listeners only when something actually changed.
- **Friendly-name sync.** Entities re-render their friendly name when the device registry entry's `name` changes.

The core HA pattern for add and reconfigure is one shared step function: `async_step_user = async_step_reconfigure = <step>`, with `self.source` telling the two apart. That pattern is used by ollama, google_weather and google_generative_ai_conversation.

The pure-library work splits into three areas, each small and test-first:
1. **`filter.py`** gains:
   - field sets (title/subtitle/description/category)
   - a case flag
   - NFC-normalized patterns
   - a nested-quantifier ReDoS guard
   - duration bounds
   - a `TimeWindow` plus weekdays, evaluated with an explicitly passed `tzinfo`
2. **`render.py`** gains a compiled template (parsed once by `string.Formatter().parse`, rendered by joining literals and values, never `str.format`), the D-22 cleanup and the D-23 default description.
3. **`window.py`** gains `upcoming(now, limit)` for the preview, plus the IN-14 `OverflowError` clamp that STATE.md assigns to this phase.

Feed text should be NFC-normalized once, in the parser's `_text()`. Measured cost: about 0.015 s per 120k titles and about 0.13 s per 120k descriptions of 600 characters. Doing it in the parser means every calendar, the renderer and the preview all see canonical text.

The HA glue is the riskiest part:
- **Calendar entity.** It must hold a swappable config (filter spec plus templates) and expose `async_apply_subentry(subentry)`.
- **Update listener.** It diffs `(title, data)` per existing calendar and calls that method, so other calendars and the coordinator stay untouched.
- **Subentry flow.** It becomes a small state machine: `basic` → (`advanced`) → `preview` menu → `save` | `back`. A pending-data dict lives on the flow instance.
- **Existing tests.** Seven tests in three files submit the calendar form once and expect `CREATE_ENTRY`. They must move to a helper that drives the flow through preview and save.

**Primary recommendation:**
- Build the pure library changes first, test-first (filter, render/template, window).
- Then refactor the entity and listener for in-place updates.
- Then the multi-step subentry flow, using a shared `basic` step, a `menu` preview step (`save`/`back`) and `async_update_and_abort` for reconfigure.
- Never call `async_update_reload_and_abort`: it raises `ValueError` when an update listener exists.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Field-scoped / case / NFC regex matching | Pure library `xmltv/filter.py` (runs in executor) | — | No HA imports (purity test). CPU-bound over 120k programmes |
| Feed-text NFC normalization | Pure library `xmltv/parser.py` `_text()` | — | Once per refresh instead of once per calendar per refresh |
| Duration / time-window / weekday predicate | Pure library `xmltv/filter.py` | HA glue passes `dt_util.get_default_time_zone()` | Library stays tz-agnostic (D-10 needs the HA tz) |
| Template compile / validate / render / cleanup, default description | Pure library `xmltv/render.py` | Flow maps `TemplateError` → form error | Same code validates in the flow and renders events (no drift) |
| Preview selection (count + next N from now) | Pure library `xmltv/window.py` `MatchIndex.upcoming` | Flow formats lines in local time and runs everything in the executor | Same match path as the entity (D-16) |
| Preview UI (Save / Back) | HA config flow `CalendarSubentryFlow` menu step | `translations/en.json` | Menu steps render a Markdown description with placeholders |
| Reconfigure persistence | HA config flow (`async_update_and_abort`) | — | Writes the subentry; HA fires the update listener |
| In-place calendar update | `__init__.py` listener → `calendar.py` entity | Device registry (title → device name) | D-04: no entry reload, no re-download, other calendars untouched |

## Standard Stack

### Core (all built-in, nothing to install)
| Library / API | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `ConfigSubentryFlow` + `async_step_reconfigure` / `_get_reconfigure_subentry()` / `async_update_and_abort()` | HA 2026.10.1 | Add and edit a calendar | [VERIFIED: .venv/.../homeassistant/config_entries.py:3948-3982, 4049-4062] Core pattern |
| `FlowHandler.async_show_menu(step_id=, menu_options=, description_placeholders=)` | HA 2026.10.1 | Preview step with Save/Back | [VERIFIED: data_entry_flow.py:878-902] The frontend renders the menu description through `<ha-markdown allow-svg breaks>` [CITED: github.com/home-assistant/frontend/blob/dev/src/dialogs/config-flow/show-dialog-sub-config-flow.ts] |
| `selector.TimeSelector()` | HA 2026.10.1 | Window from/to | [VERIFIED: helpers/selector.py:2299-2313] Validates with `cv.time` and returns the **raw string** (`"22:00:00"` from the UI). The backend config has no `no_second` key |
| `selector.SelectSelector(SelectSelectorConfig(options=[...], multiple=True, translation_key=...))` | HA 2026.10.1 | Weekdays, include/exclude fields | [VERIFIED: helpers/selector.py:1921-1929] `translation_key: str` exists. Labels come from top-level `"selector": {"<key>": {"options": {...}}}` in `translations/en.json` (same structure as core `amberelectric`, `alexa_devices`) |
| `selector.NumberSelector(NumberSelectorConfig(min=, step=1, mode=BOX, unit_of_measurement="min"))` | HA 2026.10.1 | Min/max duration | [VERIFIED: helpers/selector.py:1495-1505] Returns **float**, so store `int(...)` |
| `selector.BooleanSelector()` | HA 2026.10.1 | "Advanced options", case-sensitive | Standard |
| `selector.TextSelector(TextSelectorConfig(multiline=True))` | HA 2026.10.1 | Description template | Already used for pattern fields |
| `unicodedata.normalize("NFC", …)` | stdlib 3.14 | D-08 | Measured: 120k titles 0.016 s, 120k × 600-char descriptions 0.125 s [VERIFIED: local benchmark] |
| `re` (+ `re._parser` for the ReDoS shape check) | stdlib 3.14 | Matching, nested-quantifier detection | No dependency. `re._parser` is private (see Pitfall 5) |
| `string.Formatter().parse()` | stdlib 3.14 | Template tokenizing/validation | Gives `(literal, field_name, format_spec, conversion)` per piece. Raises `ValueError` for `{title`, `x}` [VERIFIED: local experiment] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Menu step for preview | Form with a `save: bool` checkbox | A form needs a submit **and** a checkbox. It's clumsier, and Back would be a checkbox too. The menu gives two clear buttons, and core uses subentry menus (bayesian, mqtt, ntfy, waqi translations) |
| Flat advanced form | `data_entry_flow.section(...)` groups | Sections nest `user_input` (`{"time": {...}}`), which complicates storage mapping and tests. The step is already "advanced", so flat is enough |
| NFC at parse time | NFC per field inside `FilterSpec.apply` | Per-calendar cost on every refresh (≈0.13 s per calendar when descriptions are matched). Advantage: no parser change and no UID change for NFD feeds |
| Compiled template (join) | `str.format_map` on the stored string | `format_map` executes format specs (`{title:>999999999}` allocates ~1 GB) and attribute access if validation is ever bypassed (e.g. a hand-edited `.storage`). Join over pre-validated parts can't do either |
| Nested-quantifier rejection | `regex` package with `timeout=` | Adds a runtime dependency (forbidden). Not in HA constraints [CITED: .planning/research/PITFALLS.md Pitfall 10] |

**Installation:** none (no new packages).

## Package Legitimacy Audit

This phase installs no external packages. All functionality is stdlib or built into HA 2026.10.1.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| — | — | — | — | — | — | No new packages |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                ┌─────────────── Subentry flow (UI, admin) ──────────────────────────┐
 "Add calendar" │ async_step_user ─┐                                                 │
 "Reconfigure"  │ async_step_reconfigure ─┤→ basic ──(advanced checked?)──yes→ advanced│
                │                        │      │no                          │       │
                │                        │      ▼                            ▼       │
                │                        │   preview (menu) ◄────────────────┘       │
                │                        │   [executor: FilterSpec.apply(epg,tz) →    │
                │                        │    MatchIndex.upcoming(now,10) → lines]    │
                │                        │      │ save                 │ back        │
                │                        │      ▼                      └──→ basic    │
                │                        │  source==user? create_entry : update_and_abort
                └────────────────────────┴──────────┬──────────────────────────────────┘
                                                    │ ConfigEntries.async_add/update_subentry
                                                    ▼ (fires update listeners only on change)
                 __init__._async_entry_updated (single listener)
                   ├─ entry.data/options changed? → async_schedule_reload (unchanged behaviour)
                   ├─ removed subentries → drop from runtime.calendars
                   ├─ changed (title,data) of existing calendar → entity.async_apply_subentry(subentry)
                   │        ├─ rebuild CalendarConfig (FilterSpec + templates)
                   │        ├─ title changed → device_registry.async_update_device(name=title)
                   │        └─ _async_refilter() [executor: spec.apply(coordinator.data, tz)]
                   └─ new subentries → create entity + add_entities(config_subentry_id=…)
                                                    │
 coordinator.data (EpgData, parsed once per refresh, NFC text) ─────┘ (never re-fetched here)
                                                    ▼
 XmltvCalendarEntity: MatchIndex → event / async_get_events → build_events(…, templates)
```

### Recommended Project Structure (changes only)
```
custom_components/xmltv_calendar/
├── xmltv/filter.py     # + field sets, case flag, NFC patterns, ReDoS shape check, duration, TimeWindow, weekdays
├── xmltv/render.py     # + CompiledTemplate, compile/validate/render, cleanup, default_description, EventTemplates
├── xmltv/window.py     # + MatchIndex.upcoming(now, limit), IN-14 OverflowError clamp
├── xmltv/parser.py     # _text(): NFC-normalize extracted text
├── xmltv/preview.py    # (optional) pure preview-line formatting: weekday names table + line format
├── calendar.py         # entity holds CalendarConfig; async_apply_subentry(); build_events(..., templates)
├── __init__.py         # listener: diff (title, data) of existing calendars → in-place apply
├── config_flow.py      # basic / advanced / preview(menu) / save / back; reconfigure alias
├── const.py            # new CONF_* keys + defaults
└── translations/en.json# steps basic/advanced/preview/preview_empty, initiate_flow.reconfigure, selector.*, errors
```

### Pattern 1: Stored subentry data contract (D-06: costly to change)

Phase 1 keys: [VERIFIED: custom_components/xmltv_calendar/xmltv/filter.py:11-18]
```python
KEY_CHANNELS = "channels"
KEY_CHANNEL_REGEX = "channel_regex"
KEY_INCLUDE = "include"
KEY_EXCLUDE = "exclude"
...
MAX_PATTERN_LENGTH = 300
MAX_PATTERN_LINES = 50
```

**Proposed new keys** [ASSUMED: names are a proposal. Confirm before the first plan locks them, because they become a stored contract]:

| Key | Type stored | Default (also used when the key is missing) |
|-----|-------------|-------------------------|
| `include_fields` | `list[str]` ⊆ `["title","subtitle","description","category"]` | `["title","subtitle"]` |
| `exclude_fields` | same | `["title","subtitle"]` |
| `case_sensitive` | `bool` | `False` |
| `time_from` / `time_to` | `"HH:MM"` string or `None` | `None` |
| `weekdays` | `list[str]` ⊆ `["mon","tue","wed","thu","fri","sat","sun"]` | `[]` (= all) |
| `min_duration` / `max_duration` | `int` minutes or `None` | `None` |
| `title_template` | `str` | `"{channel}: {title}"` |
| `description_template` | `str` | `""` (= default description) |

Rules:
- Weekday values match HA's own constant: [VERIFIED: .venv/.../homeassistant/const.py:1018] `WEEKDAYS: Final[list[str]] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]`.
  - The library can't import it, so it defines an identical tuple. A test asserts the two are equal.
  - Index = `datetime.weekday()`.
- Field option value `"subtitle"` matches the `{subtitle}` placeholder name, so there is one vocabulary.
- Always **write all keys** on create/reconfigure. Also **read tolerantly**:
  - missing or `None` → default
  - wrong type → default
  - an unknown field name is dropped
  - an empty field list → default (defensive; the flow prevents it)
- Normalize `time_from`/`time_to` to `"HH:MM"` before storing. The TimeSelector delivers `"HH:MM:SS"`.
- Do **not** store the "Advanced options" checkbox. Derive it as `has_advanced(data)`, true when any advanced key differs from its default (D-03).

### Pattern 2: `FilterSpec` extension (pure, frozen)

```python
# Sketch. Names marked [ASSUMED] are proposals; the Phase 1 names are quoted above.
FIELD_TITLE, FIELD_SUBTITLE, FIELD_DESCRIPTION, FIELD_CATEGORY = "title", "subtitle", "description", "category"
DEFAULT_FIELDS = frozenset({FIELD_TITLE, FIELD_SUBTITLE})

def _field_values(programme: Programme, fields: frozenset[str]) -> Iterator[str]:
    # D-07: each sub-title and each category is tested on its own
    if FIELD_TITLE in fields:
        yield programme.title          # titles[0], unchanged Phase 1 behaviour
    if FIELD_SUBTITLE in fields:
        yield from programme.sub_titles
    if FIELD_CATEGORY in fields:
        yield from programme.categories
    if FIELD_DESCRIPTION in fields and programme.description:
        yield programme.description    # last: the most expensive to scan (Pitfall 7)

@dataclass(frozen=True)
class FilterSpec:
    channels: frozenset[str]
    channel_patterns: tuple[re.Pattern[str], ...] = ()
    include: tuple[re.Pattern[str], ...] = ()
    exclude: tuple[re.Pattern[str], ...] = ()
    include_fields: frozenset[str] = DEFAULT_FIELDS
    exclude_fields: frozenset[str] = DEFAULT_FIELDS
    min_duration: timedelta | None = None
    max_duration: timedelta | None = None
    window: TimeWindow | None = None
    weekdays: frozenset[int] = frozenset()        # 0=Mon … 6=Sun; empty = all

    def apply(self, epg: EpgData, *, tz: tzinfo = UTC) -> FilterResult:
        # order cheapest first: channel (cached) → duration → window/weekday → include → exclude
        ...
```
- `compile_patterns(text, *, case_sensitive=False)` NFC-normalizes each line, then compiles with `0` or `re.IGNORECASE`.
- `first_invalid_pattern` does the same plus the nested-quantifier check (Pattern 9).
- Keeping the defaults on the dataclass keeps every existing `tests/xmltv/test_filter.py` case valid (`.apply(EPG)` with the UTC default).
- The entity and the preview **must** pass `tz=dt_util.get_default_time_zone()`.

### Pattern 3: Unicode strategy (D-08, Claude's discretion → NFC + `re.IGNORECASE`, no casefold)

Verified locally on Python 3.14.7:
- An NFD feed string does **not** match the pattern `köln` until it is NFC-normalized.
- After NFC it matches.
- `re.IGNORECASE` matches `ä`/`Ä` and `ß`/`ẞ`, but not `ß`/`SS`.
- `r"\S+\D".casefold()` gives `\s+\d`, so casefolding a pattern changes its meaning.
- A decomposed character class `[äöü]` fails until NFC'd.

Recommendation:
- NFC the **pattern line** before compiling. This is safe: escapes like `ä` are ASCII text and unaffected.
- NFC **feed text** once in `parser._text()`. This covers titles, sub-titles, description, categories, episode and display names.
- Never casefold.
- `ß` ≠ `ss` stays a documented limitation. Users can write `stra(ß|ss)e`.

### Pattern 4: Time window and weekdays (D-09…D-12)

```python
@dataclass(frozen=True, slots=True)
class TimeWindow:
    start: int  # minutes after local midnight
    end: int    # != start (flow rejects equality)

    def anchor_date(self, local: datetime) -> date | None:
        """Return the date the matching window started on, or None if `local` is outside the window."""
        minute = local.hour * 60 + local.minute
        if self.start < self.end:                      # same-day window
            return local.date() if self.start <= minute < self.end else None
        if minute >= self.start:                       # evening part of a midnight-crossing window
            return local.date()
        if minute < self.end:                          # after-midnight part → counts for the previous day (D-11)
            return local.date() - timedelta(days=1)
        return None

# in apply():
local = programme.start.astimezone(tz)
day = self.window.anchor_date(local) if self.window else local.date()
if day is None or (self.weekdays and day.weekday() not in self.weekdays):
    reject
```
- With weekdays and no window, the weekday is the local start date's weekday.
- The window is **half-open `[from, to)`**, the same as HA's own time condition: `if not after <= now_time < before` / crossing: `if before <= now_time < after: return False` [VERIFIED: .venv/.../homeassistant/helpers/condition.py:2112-2119]. See Open Question 1.
- Only convert to local time when a window or weekdays are configured. Measured: 0.15 s per 120k `astimezone` calls.

D-11 test table (Europe/Berlin):

| Start | Window | Weekdays | Expected |
|-------|--------|----------|----------|
| Sat 01:00 | 22:00–02:00 | Fri | match |
| Fri 01:00 | 22:00–02:00 | Fri | no match |
| Fri 22:00 | 22:00–02:00 | Fri | match |
| Sat 02:00 | 22:00–02:00 | Fri | no match (end exclusive) |

Add the DST nights 2026-10-25 and 2027-03-28 as well.

### Pattern 5: Preview as a menu step (FLT-10, D-15…D-19)

```python
async def async_step_preview(self, user_input=None) -> SubentryFlowResult:
    entry = self._get_entry()
    if entry.state is not ConfigEntryState.LOADED:
        return self.async_abort(reason="source_not_loaded")
    epg = entry.runtime_data.coordinator.data
    tz = dt_util.get_default_time_zone()
    now = dt_util.utcnow()
    count, lines = await self.hass.async_add_executor_job(
        build_preview, self._pending, epg, now, tz, PREVIEW_LIMIT  # pure; same CalendarConfig.from_mapping as the entity
    )
    return self.async_show_menu(
        step_id="preview" if count else "preview_empty",   # D-18 warning text lives in translations, so it's translatable
        menu_options=["save", "back"],
        description_placeholders={"count": str(count), "matches": "\n".join(f"- {line}" for line in lines)},
    )

async def async_step_save(self, user_input=None): ...   # create_entry (source user) / async_update_and_abort (reconfigure)
async def async_step_back(self, user_input=None):
    return await self.async_step_basic()                   # user_input None → form pre-filled from self._pending
```
- Menu option ids are step ids: `save` → `async_step_save`, `back` → `async_step_back`. In tests, call `async_configure(flow_id, {"next_step_id": "save"})`.
- Labels come from `config_subentries.calendar.step.<step_id>.menu_options.<option>`. The description comes from `…step.<step_id>.description`, with placeholders applied by `hass.localize` [CITED: frontend show-dialog-sub-config-flow.ts `renderMenuDescription`]. So **both** `preview` and `preview_empty` need `description` and `menu_options` translations.
- Preview line, D-17: `f"{weekday} {local:%d.%m.} {local:%H:%M} · {channel_name} · {title}"`.
  - `title` comes from the entered title template.
  - `local = start.astimezone(tz)`.
  - Weekday names come from a small table keyed by `hass.config.language` (`de` → `Mo Di Mi Do Fr Sa So`, else `Mon Tue …`). Never `locale.setlocale` (process-global, not thread-safe). [ASSUMED: language source. The frontend language is per user, so `hass.config.language` is the closest server-side proxy]
  - **Escape Markdown** in channel name and title: `\ * _ [ ] < > # | `` ` ``. The description is rendered as Markdown (Pitfall 8).
- Count = number of matches with `stop > now`. Selection = the first 10 of them by start (running programmes included, D-16).
  - `MatchIndex.upcoming(now, limit) -> tuple[int, list[Programme]]` reuses the bisect start: `bisect_left(starts, now - max_duration)`, then a scan with `stop > now`.

### Pattern 6: Shared basic step for add and reconfigure (core idiom)

Core pattern [VERIFIED: .venv/.../homeassistant/components/ollama/config_flow.py:254-257, 401-402]:
```python
@property
def _is_new(self) -> bool:
    return self.source == "user"
...
async_step_user = async_step_set_options
async_step_reconfigure = async_step_set_options
```
Applied here:
```python
class CalendarSubentryFlow(ConfigSubentryFlow):
    def __init__(self) -> None:
        self._pending: dict[str, Any] | None = None   # basic + advanced values, survives Back
        self._show_advanced = False

    def _load_pending(self) -> dict[str, Any]:
        if self._pending is None:
            stored = {} if self.source == SOURCE_USER else dict(self._get_reconfigure_subentry().data)
            self._pending = with_defaults(stored)            # D-06: missing keys → defaults
            if self.source != SOURCE_USER:
                self._pending[CONF_NAME] = self._get_reconfigure_subentry().title
            self._show_advanced = has_advanced(self._pending)   # D-03 pre-check
        return self._pending

    async def async_step_basic(self, user_input=None): ...   # step_id="basic"
    async_step_user = async_step_basic
    async_step_reconfigure = async_step_basic
```
- `ConfigSubentryFlow.async_create_entry` **raises** `ValueError` when `self.source != SOURCE_USER` [VERIFIED: config_entries.py:3904-3905]. So `async_step_save` must branch:
  ```python
  if self.source == SOURCE_USER:
      return self.async_create_entry(title=name, data=data)
  return self.async_update_and_abort(self._get_entry(), self._get_reconfigure_subentry(), title=name, data=data)
  ```
- The frontend offers "Reconfigure" only because of `hasattr(subentry_flow_handler, "async_step_reconfigure")` [VERIFIED: config_entries.py:653-655]. Add `"initiate_flow": {"user": "Add calendar", "reconfigure": "Edit calendar"}` (the same keys ollama ships).
- **Optional fields** (time, duration, description template) must use `vol.Optional(key)` plus suggested values (`add_suggested_values_to_schema`), **never `default=`**. Otherwise a cleared field comes back filled. A missing key in `user_input` means "cleared". In the advanced step, build the advanced values **fresh from `user_input`**; never `dict.update` them over the old values.
- Unchecked "Advanced options" skips the step and keeps `self._pending`'s advanced values (D-03).
- Keep the basic form's `source_not_loaded` abort (existing translation). Apply it in `basic`, `preview` and `save`.

### Pattern 7: In-place calendar update in the single listener (FLT-11, D-04)

Facts:
- `async_update_subentry` replaces `subentry.data`/`title` on the **same `ConfigSubentry` object**, using `object.__setattr__` with a new `MappingProxyType`.
- It fires update listeners only when something changed, and returns `False` otherwise [VERIFIED: config_entries.py:2840-2885, 2799-2810].
- An entity that kept a reference to the old `data` mapping can diff against it.

```python
async def _async_entry_updated(hass, entry):
    runtime = entry.runtime_data
    if (dict(entry.data), dict(entry.options)) != runtime.source_snapshot:
        hass.config_entries.async_schedule_reload(entry.entry_id)
        return
    for subentry_id in set(runtime.calendars) - set(entry.subentries):
        runtime.calendars.pop(subentry_id)
    for subentry_id, entity in runtime.calendars.items():          # NEW: changed calendars, in place
        subentry = entry.subentries[subentry_id]
        if entity.differs_from(subentry):                          # (title, data) vs. what the entity was built from
            await entity.async_apply_subentry(subentry)
    if runtime.add_entities is None:
        return
    ...  # existing "add new subentries" loop unchanged
```

`XmltvCalendarEntity.async_apply_subentry(subentry)`:
1. Store `subentry.data`/`title`, and rebuild `self._config = CalendarConfig.from_mapping(subentry.data)` (filter spec plus compiled templates).
2. If the title changed:
   ```python
   dev = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, subentry_id)})
   dr.async_get(hass).async_update_device(dev.id, name=subentry.title)
   ```
   - The entity re-renders its friendly name by itself, because `Entity._async_device_registry_updated` reacts to `"name"` changes [VERIFIED: helpers/entity.py:1691-1705].
   - `entity_id` does not change (normal HA behaviour).
3. If `self.hass is None` (entity created but not yet added), stop here. `async_added_to_hass` refilters with the new config.
4. Otherwise `await self._async_refilter()`. The existing generation counter discards an in-flight older run.

`_async_refilter` must read `self._config` instead of re-reading `entry.subentries` (today it does `FilterSpec.from_mapping(subentry.data …)` per refresh, calendar.py:118-119), so there is one source of truth. `event` and `async_get_events` pass `self._config.templates` to rendering.

### Pattern 8: Templates (EVT-03, EVT-04)

```python
TITLE_FIELDS = frozenset({"channel", "title", "subtitle", "episode", "category", "channel_id"})
DESCRIPTION_FIELDS = TITLE_FIELDS | {"description"}
_FORMATTER = string.Formatter()

class TemplateError(ValueError):
    """`reason` is a flow error key: invalid_template | unknown_placeholder; `detail` goes into a placeholder."""

def compile_template(text: str, allowed: frozenset[str]) -> tuple[tuple[str, str | None], ...]:
    try:
        pieces = list(_FORMATTER.parse(text))           # parse() is lazy: errors surface while iterating
    except ValueError as err:
        raise TemplateError("invalid_template", str(err)) from None
    compiled = []
    for literal, field, spec, conversion in pieces:
        if field is not None and (field not in allowed or spec or conversion):
            raise TemplateError("unknown_placeholder", "{" + field + "}")   # covers ".", "[", "{}", "{0}", "{x:>9}", "{x!r}"
        compiled.append((literal, field))
    return tuple(compiled)

def render(compiled, values: Mapping[str, str]) -> str:
    return "".join(literal + (values.get(field) or "" if field else "") for literal, field in compiled)
```

Verified `Formatter.parse` outputs (Python 3.14.7):

| Template | Parse result |
|----------|--------------|
| `'{title.__class__}'` | field `'title.__class__'` |
| `'{title[0]}'` | field `'title[0]'` |
| `'{}'` | field `''` |
| `'{title:>99999999}'` | spec `'>99999999'` |
| `'{title!r}'` | conversion `'r'` |
| `'{title:{channel}}'` | spec `'{channel}'` |
| `'{{literal}}'` | literals `'{'` + `'literal}'` |

All of the field/spec/conversion cases are rejected by the rule above.

Values:
- `channel` = display name, else ID
- `subtitle` = `sub_titles[0]`
- `category` = `", ".join(categories)`
- `episode` = raw
- `description` = `programme.description` (description template only)

Cleanup (D-22, discretion on the set):
```python
_SEP = r"[\s\-–—:,;|·/]"
_EDGES = re.compile(rf"^{_SEP}+|{_SEP}+$")
_SPACES = re.compile(r"[ \t]{2,}")
title = _EDGES.sub("", _SPACES.sub(" ", rendered.replace("\n", " ")))
```
- If the cleaned title is empty, fall back to `programme.title`. `CalendarEvent.summary` is required (`probatio.Required(EVENT_SUMMARY): cv.string`) [VERIFIED: components/calendar/__init__.py:117-131].
- For the **description template**, collapse only `[ \t]{2,}` and `\n{3,}` → `\n\n`, then strip edge separators of the whole text. Never per line, which would eat `- ` bullets.

Default description (D-23):
```python
lines = [subtitle, f"Episode: {episode}" if episode else "", f"Categories: {cats}" if cats else ""]
head = "\n".join(line for line in lines if line)
return "\n\n".join(part for part in (head, description or "") if part) or None
```

The UID must keep using `programme.title`, not the rendered title. Phase 1 has `crc32(programme.title)` in `event_uid` [VERIFIED: xmltv/render.py:20-23], so template edits never change UIDs.

Keep a default parameter so existing call sites and tests still work: `to_event_fields(programme, channel, templates=DEFAULT_TEMPLATES)`. The default title template reproduces Phase 1's `summary=f"{location}: {programme.title}"` [VERIFIED: xmltv/render.py:30].

**The description changes for every calendar.** Phase 1 used the raw `description=programme.description` (render.py:32). The D-23 default now prepends sub-title, episode and categories. This is intended (EVT-04).

**Translation strings and literal braces.** HA translations are ICU messages, so a literal `{channel}` in a `data_description` is treated as a placeholder. The frontend passes `step.description_placeholders` to field labels, helpers and errors [CITED: frontend show-dialog-sub-config-flow.ts]. So write `"Placeholders: {placeholders}"` and pass `description_placeholders={"placeholders": "{channel}, {title}, {subtitle}, {episode}, {category}, {channel_id}"}`.

### Pattern 9: ReDoS shape check (Claude's discretion; Phase 1 review WR-01 is still open)

Walk the parsed pattern and reject an unbounded repeat nested inside another unbounded repeat. Atomic groups and possessive quantifiers are exempt.

```python
import re._parser as _sre   # private stdlib module (Pitfall 5)
from re import _constants as _c
_REPEATS = {_c.MAX_REPEAT, _c.MIN_REPEAT}

def _nested_repeat(items, inside: bool = False) -> bool:
    for op, av in items:
        if op in _REPEATS:
            _lo, hi, sub = av
            unbounded = hi is _c.MAXREPEAT or hi > 1
            if (unbounded and inside) or _nested_repeat(sub, inside or unbounded):
                return True
        elif op is _c.SUBPATTERN and _nested_repeat(av[-1], inside):
            return True
        elif op is _c.BRANCH and any(_nested_repeat(b, inside) for b in av[1]):
            return True
        elif op in (_c.ASSERT, _c.ASSERT_NOT) and _nested_repeat(av[1], inside):
            return True
    return False   # ATOMIC_GROUP / POSSESSIVE_REPEAT: no backtracking into them
```

Verified results:

| Pattern | Result |
|---------|--------|
| `^(\w+\s?)+$` | rejected |
| `(a*)*` | rejected |
| `(\d+\s*)+x` | rejected |
| `(formel\|formula)\s*1` | allowed |
| `^Tatort$` | allowed |
| `(?:a+)++` | allowed |
| `(?>a+)+` | allowed |
| `(ab){2,5}` | allowed |
| `[a-z]+\d*` | allowed |
| `(a\|aa)+` | **not** caught (overlapping alternation; documented residual risk) |

`^(\w+\s?)+$` against 22 `a`s plus `!` took 0.30 s, roughly ×4 per 2 extra characters.

Wire it into `first_invalid_pattern` with message `"nested repetition can be very slow"`, so the existing `invalid_regex` error key and placeholders are reused. Stored Phase 1 patterns are not re-validated at load time. They keep working.

### Anti-Patterns to Avoid
- **`async_update_reload_and_abort` in the reconfigure step.** It raises `ValueError("Cannot update and reload entry with update listeners")` [VERIFIED: config_entries.py:4016-4018], and a reload would defeat D-04 anyway.
- **Re-reading `entry.subentries` inside the entity on every refresh while also holding a config.** That gives two sources of truth. Hold one `CalendarConfig`.
- **Running `FilterSpec.apply` or the preview on the event loop.** A full scan is 0.15 s (title only) to 1.3 s (description) on the dev box.
- **`default=` on optional selectors.** Users can't clear the field.
- **`str.format`/`format_map` on user templates at render time.** See Pitfall 3.
- **Casefolding patterns.**

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Template tokenizer | Own `{…}` regex parser | `string.Formatter().parse` | Handles `{{`/`}}` escapes, nested specs and errors exactly like `str.format` |
| Time-string parsing | Own `HH:MM` regex | `TimeSelector` + `dt_util.parse_time` in glue (or `datetime.time.fromisoformat` in the library) | `parse_time` accepts `HH:MM` and `HH:MM:SS` [VERIFIED: util/dt.py:296-311] |
| tz conversion / DST | Offset arithmetic | `datetime.astimezone(zoneinfo)` with the tz from `dt_util.get_default_time_zone()` | DST nights |
| Regex AST | String heuristics over pattern text | `re._parser.parse` tree walk | Escapes and classes (`[(+]`) defeat text heuristics |
| Subentry persistence | Writing `entry.subentries` via `async_update_entry` | `async_update_and_abort` / `async_update_subentry` | Fires listeners only on change, validates unique_id |
| Device rename | Removing and recreating entity/device | `device_registry.async_update_device(name=…)` | Keeps entity_id, history and triggers |

**Key insight:** every risky piece (templating, regex, tz) has a stdlib or HA primitive. Custom code should only combine them.

## Common Pitfalls

### Pitfall 1: Reconfigure that reloads the entry
**What goes wrong:** `async_update_reload_and_abort` raises when an update listener is registered. A plain reload re-downloads the feed and rebuilds every calendar.
**How to avoid:** Use `async_update_and_abort` and let the listener apply the change in place.
**Warning signs:** `aioclient_mock.call_count` rises in the reconfigure test; `entry.runtime_data` is a new object.

### Pitfall 2: Seven existing tests assume a one-step calendar flow
**What goes wrong:** These tests submit the form once and expect `CREATE_ENTRY`:
- `tests/test_subentry_flow.py` (lines 97, 135, 206, 220, 250, 313)
- `tests/test_init.py` (lines 69 and 227)
- `tests/test_tracer.py` (line 71)

With a mandatory preview they get a MENU result. `test_include_calendar_via_form_end_to_end` also asserts `result["data"] == {...}` with only the four Phase 1 keys.
**How to avoid:**
- Add a shared helper, e.g. `tests/conftest.py::complete_calendar_flow(hass, entry, basic, advanced=None) -> result`, that drives basic → (advanced) → preview → `{"next_step_id": "save"}`.
- Migrate these tests in the same plan that changes the flow.
- Update the data assertion to the full key set.

### Pitfall 3: Format-string abuse in templates
**What goes wrong:**
- `"{title.__class__.__init__.__globals__}"` style traversal.
- `"{title:>999999999}"` allocates about 1 GB per event.
- `"{title:{channel}}"` nests fields.

**How to avoid:**
- Reject any field not in the allowed set, any non-empty `format_spec` and any `conversion`.
- Render only from the compiled parts.
- When `CalendarConfig.from_mapping` meets a stored template that fails to compile (e.g. a hand-edited `.storage`), fall back to the default template and log a warning. Never raise during refilter.

### Pitfall 4: Casefold / NFD
**What goes wrong:**
- `pattern.casefold()` turns `\S` into `\s`.
- An NFD feed never matches NFC user input.

**How to avoid:** Follow Pattern 3. Tests should use an NFD fixture feed (`unicodedata.normalize("NFD", "Köln")` written into the XML) end to end, plus a decomposed-pattern case.

### Pitfall 5: `re._parser` is private
**What goes wrong:** A future Python could rename it, or change the tree shape or constants.
**How to avoid:**
- Wrap the shape check in `try/except (ImportError, AttributeError)`. If it fails, skip the check (fail-open: it is a best-effort guard; the length/line caps still apply).
- Pin the behaviour with tests that assert `^(\w+\s?)+$` is rejected and `(formel|formula)\s*1` accepted, so a Python bump that silently disables the check shows up in CI.
- Ruff `SLF001` may flag `re._parser` attribute access. Use `import re._parser as sre_parse` (module import), or a targeted `noqa`.

### Pitfall 6: Duration across DST with a shared tzinfo
**What goes wrong:** Subtracting two aware datetimes that share the **same** `tzinfo` object ignores utcoffset, so you get wall-clock time. Applied to `as_local(...)` zoneinfo datetimes, that gives wrong durations on DST nights.
**How to avoid:** Compute `programme.stop - programme.start` on the parser's datetimes. Those use cached fixed-offset `datetime.timezone` objects [VERIFIED: xmltv/timeparse.py:14,23-26 `_TZ_CACHE: dict[int, timezone] = {0: UTC}`], which are safe. Never compute durations on local-converted values.

### Pitfall 7: Matching descriptions is slow
**What goes wrong:** One include alternation over 120k × 540-char descriptions took **1.33 s** on the dev box. Title and sub-title together took 0.15 s. `ha-host` is slower, and every calendar that matches descriptions pays this on every refresh and on every preview.
**How to avoid:**
- Test cheap constraints first: channel → duration → window → title/sub-title/category → description last.
- Short-circuit with `any()`.
- Run in the executor (already the case).
- Mention the cost in the field helper text.
- Optional: cap the text matched per description (e.g. the first 2,000 characters). That changes semantics, so it needs a user decision. Not recommended by default.

### Pitfall 8: Markdown/HTML from feed text in the preview
**What goes wrong:** Feed titles are untrusted. The menu description is rendered with `<ha-markdown allow-svg breaks>`, so `*`, `_`, `[x](javascript:…)` and `<img …>` in titles distort the preview or try injection.
**How to avoid:** Escape Markdown metacharacters and `<`, `>`, `&` in channel and title before joining. [ASSUMED: HA's ha-markdown also sanitizes HTML; escaping makes the preview safe either way]

### Pitfall 9: Whitespace collapse eating description newlines
**What goes wrong:** Applying the title cleanup (`\s+` → `" "`) to descriptions destroys the D-23 line layout.
**How to avoid:** Use separate cleanups for title and description (Pattern 8).

### Pitfall 10: Entity not yet added when the listener runs
**What goes wrong:** A subentry added and then edited quickly, or edited before the platform has finished setting up, leaves the entity with `hass is None`. Calling `async_write_ha_state` raises.
**How to avoid:** `async_apply_subentry` only stores the config when `self.hass is None`. `async_added_to_hass` already refilters.

### Pitfall 11: The TimeSelector returns `"HH:MM:SS"`; `NumberSelector` returns float
**How to avoid:**
- Normalize times to `"HH:MM"` for storage and minute comparison. `from == to` must be compared after normalization.
- Store `int(minutes)`.
- Tests should submit both `"22:00"` and `"22:00:00"`.

### Pitfall 12: Error placeholders collide across fields
**What goes wrong:** Phase 1 WR-03: several invalid fields share the `pattern`/`error` placeholders, so the message shows the first one. Template errors need their own placeholders.
**How to avoid:** Use `template_error`/`template_field`. Keep `pattern`/`error` for regex errors.

### Pitfall 13: HA timezone in tests
phcc defaults to US/Pacific. Window and weekday tests must use the existing `berlin_tz` fixture (`tests/conftest.py`) and `freezer`. Parametrize one end-to-end test over two zones [CITED: .planning/research/PITFALLS.md Pitfall 20].

## Code Examples

### Reconfigure test (phcc helper)
```python
# Source: pytest_homeassistant_custom_component/common.py:1212-1230 (MockConfigEntry.start_subentry_reconfigure_flow)
result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
assert result["step_id"] == "basic"
result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"name": "A", "include": "tatort", "advanced": False})
assert result["type"] is FlowResultType.MENU and result["step_id"] in {"preview", "preview_empty"}
result = await hass.config_entries.subentries.async_configure(result["flow_id"], {"next_step_id": "save"})
assert result["type"] is FlowResultType.ABORT and result["reason"] == "reconfigure_successful"
await hass.async_block_till_done()
assert entry.runtime_data is runtime                     # no reload
assert aioclient_mock.call_count == calls                # no re-download
assert entry.runtime_data.coordinator.data is epg_before # no re-parse
assert entry.runtime_data.calendars[other_id] is other_entity  # sibling untouched
```

### Translations skeleton (en.json additions)
```json
"config_subentries": { "calendar": {
  "initiate_flow": { "user": "Add calendar", "reconfigure": "Edit calendar" },
  "step": {
    "basic":    { "title": "Calendar", "data": { "advanced": "Advanced options", "...": "..." } },
    "advanced": { "title": "Advanced options", "data_description": { "title_template": "Placeholders: {placeholders}" } },
    "preview":       { "title": "Preview", "description": "{count} matches from now on. Next:\n\n{matches}",
                       "menu_options": { "save": "Save", "back": "Back" } },
    "preview_empty": { "title": "Preview", "description": "Currently no matches in the feed. You can still save the calendar.",
                       "menu_options": { "save": "Save", "back": "Back" } }
  },
  "error": { "invalid_template": "...{template_error}", "unknown_placeholder": "...{template_error}",
             "time_window_incomplete": "...", "time_window_empty": "...", "duration_range": "...", "fields_required": "..." }
}},
"selector": {
  "weekday": { "options": { "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday" } },
  "match_field": { "options": { "title": "Title", "subtitle": "Sub-title", "description": "Description", "category": "Category" } }
}
```
The existing keys are kept as they are: [VERIFIED: translations/en.json] error `"invalid_regex"` and `"name_required"`, abort `"source_not_loaded"`. `reconfigure_successful` needs no entry, because `async_update_and_abort` uses the `homeassistant` translation domain by default [VERIFIED: config_entries.py:3977-3981].

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| voluptuous | probatio, with `voluptuous` aliased via `install_as_voluptuous()` in `homeassistant/__init__.py` | HA 2026.9/2026.10 [VERIFIED: homeassistant/__init__.py:3-11] | Keep `import voluptuous as vol`. Selector and validator errors are `probatio.Invalid` |
| `OptionsFlowWithConfigEntry` / reload-on-edit | Subentry reconfigure + `async_update_and_abort` + diffing listener | Subentry reconfigure since HA 2025.3/2025.4 | This phase |
| `async_show_form(preview=…)` frontend preview components | Core-only (needs a frontend component) | — | Not usable for custom integrations (deferred idea) |

**Deprecated/outdated:** `async_update_reload_and_abort` is incompatible with update listeners (raises).

## Carry-over items assigned to this phase (STATE.md)
- **WR-07** (absurd stop) → covered by the max-duration filter for calendars that set it (D-13, user-accepted).
- **IN-14** (`OverflowError` near `datetime.min` in `MatchIndex.overlapping` / `current_or_next`) → STATE.md says "clamp in window.py". It is cheap to fix while `window.py` gets `upcoming()`: wrap `start - self._max_duration` in `try/except OverflowError` → `lo = 0`. Recommend including it.
- **WR-01** (ReDoS) → Pattern 9 (Claude's discretion).

## Suggested Plan Decomposition (for the planner; coarse granularity)

| Plan | Scope | Depends on | Notes |
|------|-------|-----------|-------|
| A (TDD, pure) | `filter.py`: field sets, case flag, NFC patterns, ReDoS shape check, duration, `TimeWindow`/weekdays, `tz` param; `parser._text` NFC; `with_defaults`/`has_advanced` helpers | — | Parallel with B |
| B (TDD, pure) | `render.py`: compile/validate/render, cleanup, default description, `EventTemplates`; `window.py`: `upcoming()`, IN-14 clamp; preview-line formatter | — | Parallel with A |
| C (HA glue) | `CalendarConfig` in entity, `async_apply_subentry`, device rename, listener diff, `build_events(..., templates)` | A, B | Tests: in-place update, no reload/refetch/reparse, sibling untouched |
| D (HA glue) | Subentry flow basic/advanced/preview/save/back + reconfigure alias + en.json + migration of 7 existing tests | A, B (C for end-to-end reconfigure tests) | hassfest must stay green (translation keys) |
| E | UAT on ha-dev / ha-host (preview look, reconfigure, NFD feed) | C, D | `human_verify_mode: end-of-phase` |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | New stored keys: `include_fields`, `exclude_fields`, `case_sensitive`, `time_from`, `time_to`, `weekdays`, `min_duration`, `max_duration`, `title_template`, `description_template`, with values `"title"/"subtitle"/"description"/"category"` and `"mon"…"sun"` | Pattern 1 | Renaming later needs a subentry data migration (D-06 "costly") |
| A2 | The time window is half-open `[from, to)`, like HA's time condition | Pattern 4 | A programme starting exactly at `to` is excluded. The user may expect it included |
| A3 | Preview weekday names come from `hass.config.language` (`de` / else English) | Pattern 5 | The preview language differs from a user's frontend language |
| A4 | Feed text is NFC-normalized in the parser, which changes UIDs once for feeds delivered in NFD | Pattern 3 | One-time UID change for NFD feeds (no persisted UID consumers exist yet; EVT-08 is Phase 4) |
| A5 | ha-markdown sanitizes HTML; escaping is added anyway | Pitfall 8 | Low; escaping covers it |
| A6 | An empty include/exclude field selection is rejected (`fields_required`) instead of meaning "default" | Code Examples (errors) | UX choice. Alternative: silently treat it as the default |
| A7 | The cleanup separator set is `\s - – — : , ; \| · /` at the start/end of the rendered title | Pattern 8 | A real title starting or ending with one of these loses that character |

## Open Questions (RESOLVED)

1. **Is the window end inclusive?**
   - What we know: D-09 uses the start time, D-11 the anchor weekday. HA's time condition is `[after, before)`.
   - What's unclear: whether a programme starting exactly at `to` (e.g. 02:00 for 22:00–02:00) should match.
   - Recommendation: half-open (A2). State it in the field helper text ("start between from and before to"). Confirm with the user during plan review.
   - **RESOLVED (user, A2):** half-open `[from, to)`. A start exactly at `from` matches, a start exactly at `to` does not. Implemented in 02-04 (`TimeWindow`, edge table "Sat 02:00 no"); the helper text in 02-07 reads "start time between from and before to".
2. **Where does NFC normalization happen: parser or filter?**
   - Recommendation: in the parser (A4). Fallback: normalize per field inside `FilterSpec.apply` if the user wants to keep the parser untouched.
   - **RESOLVED (user, A4):** in the parser, applied to `_text()` output only (titles, sub-titles, description, categories, episode, display names). Channel IDs are never normalized. Pattern lines are NFC-normalized in `compile_patterns`/`first_invalid_pattern`. Implemented in 02-02.
3. **Should the preview count only from now, or report the total too?**
   - D-16 says "from now". Recommendation: count from now only.
   - **RESOLVED (per recommendation, D-16):** the preview reports one count, the matches from now on: every match whose stop is after now, so a running programme counts and `stop == now` does not. No feed-wide total is shown. Implemented in 02-03 (`build_preview`, `PreviewResult.count`).

**Assumptions A1–A7, as resolved for planning:**
- A1 (stored key names): kept as listed, but gated by the blocking `checkpoint:decision` in 02-02 before any key is written (D-06 "costly").
- A2: user resolution, see question 1.
- A3 (preview weekday names): from `hass.config.language` (`de`, otherwise English), per recommendation. Implemented in 02-03.
- A4: user resolution, see question 2.
- A5 (Markdown/HTML in the preview): escaped anyway, per recommendation. Implemented in 02-03 (`escape_markdown`).
- A6 (empty include/exclude field selection): user resolution: rejected in the flow with `fields_required`, never treated as "default". Implemented in 02-07.
- A7 (cleanup separator set): whitespace plus `- – — : , ; | · /` at the start and end of the rendered text, per recommendation (D-22 discretion). Implemented in 02-06.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | all | ✓ | 3.14.7 (.venv) | — |
| Home Assistant (dev, via phcc) | glue + tests | ✓ | 2026.10.1 | — |
| uv | test/lint runs | ✓ | (project tool) | — |
| pytest suite baseline | regression | ✓ | 238 passed, 1 skipped, 4 deselected in 4.79 s (`uv run pytest tests/ -q -m "not benchmark"`) | — |

No new external dependencies.

## Security Domain

`security_enforcement: true`, ASVS level 1.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | HA handles it (flows are admin-only) |
| V3 Session Management | no | HA |
| V4 Access Control | no | HA restricts config/subentry flows to admins |
| V5 Input Validation | **yes** | Regex compile + caps + nested-quantifier rejection; template allow-list (no spec/conversion/attribute/index); `cv.time` via TimeSelector; `min ≤ max`, `from ≠ to`, both-or-neither; field/weekday values limited to `SelectSelector` options and re-filtered when read |
| V6 Cryptography | no | — |
| V12/V14 (data from untrusted feed) | yes | NFC is harmless. Escape Markdown/HTML in the preview. Templates never evaluate feed text as format strings: values are substituted, never parsed |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Catastrophic regex backtracking (admin pattern × untrusted long text) | DoS | Executor only. Caps (300 chars / 50 lines). Nested-quantifier rejection. Residual: overlapping alternation |
| Format-string attribute traversal / width bomb in templates | Information disclosure / DoS | Allow-listed field names, empty spec/conversion, render by join |
| Markdown/HTML injection via feed titles in the preview | Tampering (UI) | Escape metacharacters before building `{matches}` |
| Corrupt stored subentry data (hand-edited `.storage`) | DoS (calendar dead) | Tolerant `from_mapping`: default on bad template/type. Invalid regex keeps Phase 1 behaviour; consider catching `re.error` → empty calendar + warning |

## Sources

### Primary (HIGH confidence)
- Installed HA 2026.10.1 (`.venv/lib/python3.14/site-packages/homeassistant/`):
  - `config_entries.py`: 641-662 (supports_reconfigure), 2799-2810, 2840-2885 (update_subentry → listeners), 3894-4062 (ConfigSubentryFlow: create_entry source check, update_and_abort, update_reload_and_abort ValueError, `_get_reconfigure_subentry`)
  - `data_entry_flow.py`: 668-703 (suggested values incl. sections), 706-726 (show_form), 878-902 (show_menu), 939-957 (section)
  - `helpers/selector.py`: 1495-1505, 1921-1929, 2294-2313
  - `helpers/entity.py`: 1691-1720
  - `helpers/condition.py`: 2112-2128
  - `util/dt.py`: 77-79, 175-181, 296-311
  - `const.py`: 1018
  - `components/calendar/__init__.py`: 117-131, 179-236
  - `components/ollama/config_flow.py`: 243-340, 401-402
  - `homeassistant/__init__.py`: 3-24
- phcc `common.py`: 1212-1230 (`start_subentry_reconfigure_flow`).
- Project source read this session: `__init__.py`, `const.py`, `data.py`, `calendar.py`, `config_flow.py`, `coordinator.py`, `xmltv/filter.py`, `model.py`, `render.py`, `window.py`, `normalize.py`, `parser.py` (helpers), `timeparse.py` (tz cache), `translations/en.json`, tests (`conftest.py`, `test_init.py`, `test_subentry_flow.py`, `test_filter.py`, `test_render.py`, `test_purity.py`).
- Local experiments (Python 3.14.7, scratchpad): NFC/NFD and IGNORECASE behaviour, casefold breaking escapes, normalization cost, `re._parser` nested-repeat detection, catastrophic timing, `Formatter.parse` outputs, filter/description/astimezone scan cost.

### Secondary (MEDIUM confidence)
- home-assistant/frontend `dev`:
  - `src/dialogs/config-flow/show-dialog-sub-config-flow.ts`: menu/form description rendered via `ha-markdown allow-svg breaks`; placeholders passed to field labels, helpers and errors
  - `step-flow-menu.ts`
  - `ha-selector-time.ts`: the time input is always `clearable`; `no_second` is frontend-only
- `.planning/research/PITFALLS.md` (Pitfalls 10, 18, 20, 23), `01-REVIEW.md` (WR-01, WR-07, IN-14).

### Tertiary (LOW confidence)
- ha-markdown HTML sanitization (A5).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. Every API was read in the installed HA source; no new packages.
- Architecture: HIGH. It follows the core subentry idiom and the existing listener/entity design.
- Pitfalls: HIGH for the HA/stdlib behaviour (verified by experiment or source). MEDIUM for the frontend rendering details (fetched from GitHub `dev`, which may differ slightly from the frontend bundled with 2026.10.1).

**Research date:** 2026-10-15
**Valid until:** 2026-11-15 (HA monthly releases; re-check if phcc/HA is bumped by Renovate)
