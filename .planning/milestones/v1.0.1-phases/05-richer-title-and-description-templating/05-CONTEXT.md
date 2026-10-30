# Phase 5: Richer title and description templating - Context

**Gathered:** 2026-10-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the restricted `str.format`-style placeholder templating of calendar event titles and descriptions (Phase 2, D-20..D-23) with a sandboxed Jinja2 template engine that supports text manipulation and control flow. Scope covers: the render engine, the template variables and helper filters, the flow validation and preview, the handling of stored legacy templates, and the README. It does not add new XMLTV data to the parser or model beyond what is listed below.

</domain>

<decisions>
## Implementation Decisions

### Template mechanism
- **D-01:** Titles and descriptions are rendered with `jinja2.sandbox.SandboxedEnvironment` used directly (jinja2 ships with HA core). Not the HA `Template` class and no HA state access, so rendering stays synchronous and never hops back to the event loop. Templates are compiled once per calendar and shared by the calendar entity and the flow preview, as `EventTemplates` is today. — **Reversibility:** costly — template storage format and README syntax change for users; switching engines again needs another migration.
- **D-02:** This reverses the REQUIREMENTS.md out-of-scope line "Jinja title templates — too slow for thousands of events". The earlier objection targeted HA's `Template.render()`; here only the requested calendar window is rendered with precompiled templates. Update REQUIREMENTS.md and the PROJECT.md key decision accordingly.
- **D-03:** Undefined values are lenient: a missing field renders as an empty string (keeps D-22). A template that still raises at runtime logs one WARNING per calendar and falls back to the programme title (title template) or the default description (description template), so one broken programme cannot fail `async_get_events` for the whole window.
- **D-04:** Sandbox safety is enforced by an AST whitelist at compile time (flow and load): expressions, `if`/`elif`/`else`, `set`, filters and tests are allowed; `for`, `macro`, `call`, `include`, `import`, `extends` and `block` are rejected with `unsupported_syntax`. No runtime timeout is needed because render cost stays linear and small.

### Template variables and text functions
- **D-05:** Variables are flat and typed. The existing names stay (`channel`, `channel_id`, `title`, `subtitle`, `episode`, `category`, and `description` for the description template) and are added to with list values (`categories`, `subtitles`) and `start` / `end` as tz-aware local datetimes. Lists are formatted with `join`.
- **D-06:** Besides the Jinja standard filters (`split`, `join`, `replace`, `trim`, `truncate`, `first`, `last`, `select`, `reject`, `map`, `default`, `upper`, `title`, `length`) and the `~` concat operator, the phase ships a small custom set: `regex_replace`, `regex_search`, `strip_prefix`, `strip_suffix`, `remove`, `lines`, `first_line`, and a local-time formatter for `start` / `end` (e.g. `{{ start | time('%H:%M') }}`). `lines` / `first_line` return an empty value on an empty description instead of raising. No HA state, `now()` or other environment access.
- **D-07:** Driving use cases (user's own words): a Formula 1 calendar should not repeat "Formel 1" in the title, and for some channels part of the title sits in the first line of the description. Both must be expressible with the filters above, plus `if` for conditional parts.

### Migration and compatibility
- **D-08:** Hard break, no migration and no dual syntax. Legacy single-brace templates such as `{channel}: {title}` are detected at load time (single-brace placeholders and no `{{ }}` / `{% %}`); such a template falls back to the new default with one WARNING. Jinja would otherwise render it literally. The flow rejects such input with the form error `legacy_placeholder` so it is never stored again.
- **D-09:** The new default title template is the Jinja equivalent of today's default: `{{ channel }}: {{ title }}` (D-20 behaviour unchanged). An empty description template still means the default description (D-23 / EVT-04).

### Flow, errors and post-processing
- **D-10:** Flow errors are form error keys plus detail via `description_placeholders`, following the existing `TemplateError(reason, detail)` pattern: `invalid_template` (syntax error with line), `unsupported_syntax`, `unknown_filter`, `legacy_placeholder`, and a trial-render error (`template_runtime_error`) from rendering a sample programme during validation. All keys translated in `en.json` and `de.json`.
- **D-11:** The post-render cleanup stays: `clean_title` (single line, collapsed spaces, dangling edge separators stripped, D-22) and `clean_description` (collapsed spaces, at most one blank line). Jinja whitespace control (`{%-`, `-%}`) remains available on top of it. An empty rendered title still falls back to the programme title.
- **D-12:** Documentation: a README section with the variables, the filters and 3-4 worked recipes (strip a "Formel 1" prefix, use the first description line as sub-title, conditional sub-title). The existing flow preview renders the real templates against real programmes. Field help texts stay short and point at the README.

### Claude's Discretion
- Whether `titles` (all `<title>` elements, currently stored on `Programme.titles`) is exposed as a list variable. The user mentioned several titles on some channels but did not ask for it explicitly; expose it if it comes for free.
- Exact names/signatures of the custom filters (`regex_replace`, `time`, ...) as long as D-06 is met.
- Regex safety (catastrophic backtracking in user patterns inside the render path); research should check what the include/exclude filter code already does and reuse it.
- Exact wording of English and German error and help texts.
- Whether the storage/subentry `VERSION` is bumped (the config flow is at `VERSION = 1`) given that D-08 forbids migration.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing templating (to be replaced)
- `custom_components/xmltv_calendar/xmltv/render.py` — `compile_template`, `render_template`, `clean_title`, `clean_description`, `default_description`, `template_values`, `EventTemplates`, `to_event_fields`
- `custom_components/xmltv_calendar/xmltv/settings.py` — `KEY_TITLE_TEMPLATE`, `KEY_DESCRIPTION_TEMPLATE`, `DEFAULT_TITLE_TEMPLATE`, `with_defaults`
- `custom_components/xmltv_calendar/xmltv/model.py` — `Programme`, `Channel` fields available to templates
- `custom_components/xmltv_calendar/config_flow.py` — advanced step, template validation, preview
- `custom_components/xmltv_calendar/translations/en.json`, `de.json` — flow error keys and field texts
- `custom_components/xmltv_calendar/calendar.py`, `matcher.py` — callers of `to_event_fields`

### Prior decisions to carry forward or reverse
- `.planning/phases/02-precise-filters-preview/02-CONTEXT.md` — D-20..D-23 (default template, placeholders, cleanup, default description)
- `.planning/REQUIREMENTS.md` — EVT-03, EVT-04, and the out-of-scope line "Jinja title templates" (reversed by D-02)
- `.planning/PROJECT.md` — key decision "Templated event title, channel as location"
- `.claude/CLAUDE.md` — stack notes on the restricted `str.format` formatter and why HA Jinja was avoided

### Documentation
- `README.md` — title/description template sections, event payload and automation examples that mention `{...}` placeholders

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EventTemplates` (render.py): compiled templates shared by calendar entity and flow preview; keep the class boundary, swap the engine inside.
- `TemplateError(reason, detail)` plus the flow error-key mapping: reuse for the new error keys.
- `clean_title` / `clean_description`: keep as the post-processing stage (D-11).
- `template_values()`: becomes the variable builder for the Jinja context.
- Existing flow preview: renders real programmes through the same templates.

### Established Patterns
- Pure-string render module under `xmltv/`, no HA imports; keep it HA-free so it stays unit-testable.
- Templates compiled once and "stored invalid → WARNING + default" (`_stored`); keep that failure mode for legacy and uncompilable stored templates.
- UIDs hash the raw programme title, so template edits do not change event UIDs (`event_uid`); must stay true.
- Match fingerprints and retained matches depend on rendered output? Research must check `match_store.py` / `matcher.py` for template-dependent state (a template edit changing the title must not re-announce matches).

### Integration Points
- `to_event_fields` is called from `calendar.py` and `matcher.py`; the new engine must keep that signature.
- Subentry storage keys `title_template` / `description_template` stay; only their syntax changes.
- Tests: `tests/test_advanced_flow.py`, `tests/test_reconfigure.py`, `tests/test_translations.py`, `tests/test_matcher_runtime.py` and the render unit tests exercise the old syntax and need rewriting.

</code_context>

<specifics>
## Specific Ideas

- Formula 1 calendar: remove the redundant "Formel 1" from the title (e.g. `{{ title | regex_replace('^Formel ?1:? ?', '') }}` or `strip_prefix`).
- Some channels put part of the title in the first line of the description; the title template must be able to use `{{ description | first_line }}`.
- `if` for optional parts, e.g. only show the sub-title when present.

</specifics>

<deferred>
## Deferred Ideas

- Additional XMLTV fields in the model (year, rating, language, duration) — not discussed; own phase if wanted.
- `for` loops, macros and includes — deliberately excluded by D-04; revisit only with a concrete use case.
- Dual syntax / automatic migration of legacy `{field}` templates — rejected by D-08.

</deferred>

---

*Phase: 5-Richer title and description templating*
*Context gathered: 2026-10-23*
