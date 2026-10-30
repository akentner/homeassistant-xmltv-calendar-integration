# Phase 2: Precise Filters & Preview - Context

**Gathered:** 2026-10-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the calendar subentry (FLT-05, FLT-06, FLT-08, FLT-09, FLT-10, FLT-11, EVT-03, EVT-04):
- Field-scoped include/exclude matching: title, sub-title, description and category, chosen separately for include and exclude.
- Case-sensitivity toggle. Unicode-normalization-safe matching.
- Duration filter (min/max) and time-of-day window plus weekday filter.
- Title and description templates.
- Preview step before saving.
- Subentry reconfigure. Updates apply in place: no re-download or re-parse, and the source's other calendars are not reloaded.

Out of scope here: category picker (FLT-12), new/premiere tags (FLT-13), language preference (FLT-14), episode normalization (EVT-09), timezone options and anything source-side (Phase 3).

</domain>

<decisions>
## Implementation Decisions

### Flow structure
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

### Field selection & case
- **D-05:** Field selection uses two multi-selects, "Include matches fields" and "Exclude matches fields". Options: title, sub-title, description, category. The default for both is title + sub-title, which is the Phase 1 behaviour.
- **D-06:** Subentries stored by Phase 1 (without the new keys) must behave exactly as before. Missing keys mean defaults. — **Reversibility:** costly — the new subentry data keys become a stored contract. Renaming them later needs a subentry data migration.
- **D-07:** Multi-valued fields are matched element by element: each category and each sub-title is tested on its own, and one hit is enough. This keeps anchors like `^Sport$` working.
- **D-08:** Matching is case-insensitive by default. The case-sensitive toggle sits in the advanced step and applies to include and exclude of that calendar. Text and patterns are Unicode-normalized (NFC per roadmap notes) before matching, so umlauts match regardless of composed or decomposed form.

### Time window, weekdays, duration
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

### Preview
- **D-15:** The preview is a separate flow step. It shows the match count and the next 10 matches. The actions are **Save** and **Back**. Back returns to the basic step with the entered values pre-filled, including the advanced values.
- **D-16:** The preview covers matches from now onwards (running programmes included), across the whole loaded feed (`coordinator.data`), sorted by start. This is the same match logic the calendar entity uses.
- **D-17:** Each preview line reads `<weekday> <dd.mm.> <HH:MM> · <channel display name> · <rendered event title>`, in local HA time. Because the title is rendered with the entered title template, the preview also checks the template.
- **D-18:** With 0 matches the preview shows a warning ("currently no matches in the feed"), but saving is still allowed.
- **D-19:** The preview runs for both new calendars and reconfigure.

### Templates
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope & requirements
- `.planning/ROADMAP.md` § "Phase 2: Precise Filters & Preview": goal, success criteria, notes on the diffing listener, `async_update_and_abort`, restricted `str.format_map`, NFC, ReDoS
- `.planning/REQUIREMENTS.md`: FLT-05, FLT-06, FLT-08..FLT-11, EVT-03, EVT-04
- `.planning/PROJECT.md` § Key Decisions: source = entry, calendar = subentry; templated title

### Prior decisions & research
- `.planning/phases/01-first-filtered-calendar/01-CONTEXT.md`: D-05..D-08 (pattern input, Phase 1 field/case defaults that Phase 2 must stay compatible with)
- `.planning/phases/01-first-filtered-calendar/01-REVIEW-DISPOSITION.md`: WR-07 / IN-14 items deferred to Phase 2
- `.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md`: subentry flow / listener and regex pitfalls
- `.claude/CLAUDE.md` (project): stack notes on `string.Formatter` restrictions, selectors, `section`, CalendarEvent cost

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `custom_components/xmltv_calendar/xmltv/filter.py`: `FilterSpec.from_mapping`, `compile_patterns`, `first_invalid_pattern`, `_fields`. Extend with field selection, case flag, duration and window. Keep it pure (no HA imports), so the window logic receives a tz.
- `custom_components/xmltv_calendar/xmltv/render.py`: `to_event_fields` currently hard-codes `"{location}: {title}"` and the raw description. Replace it with template rendering plus the default description builder.
- `custom_components/xmltv_calendar/xmltv/model.py`: `Programme` already carries `sub_titles`, `description`, `categories` and `episode`. No parser change is needed.
- `custom_components/xmltv_calendar/xmltv/window.py`: `MatchIndex`. The preview "next 10 from now" can reuse it.

### Established Patterns
- Pattern fields are stored as raw text, and blank lines are skipped at filter time (Phase 1, 01-08).
- `invalid_regex` errors carry `pattern`/`error` description placeholders (`config_flow.py` `CalendarSubentryFlow`).
- The pure `xmltv/` library is built test-first, while HA glue is tested with phcc fixtures.

### Integration Points
- `config_flow.py` `CalendarSubentryFlow`: add `async_step_advanced`, `async_step_preview` and `async_step_reconfigure`.
- `__init__.py` `_async_entry_updated`: today it only adds and removes subentries. It must also detect changed subentry data and update the existing entity in place.
- `calendar.py` `XmltvCalendarEntity`: needs a method to swap its filter spec/templates and recompute matches without a coordinator refresh.
- `strings.json` / `translations/en.json`: new step, field, error and preview texts.

</code_context>

<specifics>
## Specific Ideas

- Example preview line: `Sa 18.10. 14:55 · Sky Sport F1 · Sky Sport F1: Formel 1 – Qualifying`
- Example cleanup: `{title} – {subtitle}` with no sub-title gives `Tatort`
- Midnight example: weekday Fri + window 22:00–02:00 includes Sat 01:00 and excludes Fri 01:00

</specifics>

<deferred>
## Deferred Ideas

- Time placeholders (`{start}`, `{end}`, `{duration}`) in templates: considered but not chosen. Possible later addition.
- Real live preview while typing (WebSocket preview component): rejected because it is not practical for custom integrations.

</deferred>

---

*Phase: 02-precise-filters-preview*
*Context gathered: 2026-10-15*
