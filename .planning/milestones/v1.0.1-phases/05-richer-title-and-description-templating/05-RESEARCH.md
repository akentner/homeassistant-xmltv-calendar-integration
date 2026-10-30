# Phase 5: Richer title and description templating - Research

**Researched:** 2026-10-23
**Domain:** Sandboxed Jinja2 text templating inside a pure-Python (HA-free) render module of a Home Assistant custom integration
**Confidence:** HIGH (every engine claim below was executed against the repo's own `.venv`: jinja2 3.1.6, Python 3.14.8)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Titles and descriptions are rendered with `jinja2.sandbox.SandboxedEnvironment` used directly (jinja2 ships with HA core). Not the HA `Template` class and no HA state access, so rendering stays synchronous and never hops back to the event loop. Templates are compiled once per calendar and shared by the calendar entity and the flow preview, as `EventTemplates` is today. — **Reversibility:** costly — template storage format and README syntax change for users; switching engines again needs another migration.
- **D-02:** This reverses the REQUIREMENTS.md out-of-scope line "Jinja title templates — too slow for thousands of events". The earlier objection targeted HA's `Template.render()`; here only the requested calendar window is rendered with precompiled templates. Update REQUIREMENTS.md and the PROJECT.md key decision accordingly.
- **D-03:** Undefined values are lenient: a missing field renders as an empty string (keeps D-22). A template that still raises at runtime logs one WARNING per calendar and falls back to the programme title (title template) or the default description (description template), so one broken programme cannot fail `async_get_events` for the whole window.
- **D-04:** Sandbox safety is enforced by an AST whitelist at compile time (flow and load): expressions, `if`/`elif`/`else`, `set`, filters and tests are allowed; `for`, `macro`, `call`, `include`, `import`, `extends` and `block` are rejected with `unsupported_syntax`. No runtime timeout is needed because render cost stays linear and small.
- **D-05:** Variables are flat and typed. The existing names stay (`channel`, `channel_id`, `title`, `subtitle`, `episode`, `category`, and `description` for the description template) and are added to with list values (`categories`, `subtitles`) and `start` / `end` as tz-aware local datetimes. Lists are formatted with `join`.
- **D-06:** Besides the Jinja standard filters (`split`, `join`, `replace`, `trim`, `truncate`, `first`, `last`, `select`, `reject`, `map`, `default`, `upper`, `title`, `length`) and the `~` concat operator, the phase ships a small custom set: `regex_replace`, `regex_search`, `strip_prefix`, `strip_suffix`, `remove`, `lines`, `first_line`, and a local-time formatter for `start` / `end` (e.g. `{{ start | time('%H:%M') }}`). `lines` / `first_line` return an empty value on an empty description instead of raising. No HA state, `now()` or other environment access.
- **D-07:** Driving use cases (user's own words): a Formula 1 calendar should not repeat "Formel 1" in the title, and for some channels part of the title sits in the first line of the description. Both must be expressible with the filters above, plus `if` for conditional parts.
- **D-08:** Hard break, no migration and no dual syntax. Legacy single-brace templates such as `{channel}: {title}` are detected at load time (single-brace placeholders and no `{{ }}` / `{% %}`); such a template falls back to the new default with one WARNING. Jinja would otherwise render it literally. The flow rejects such input with the form error `legacy_placeholder` so it is never stored again.
- **D-09:** The new default title template is the Jinja equivalent of today's default: `{{ channel }}: {{ title }}` (D-20 behaviour unchanged). An empty description template still means the default description (D-23 / EVT-04).
- **D-10:** Flow errors are form error keys plus detail via `description_placeholders`, following the existing `TemplateError(reason, detail)` pattern: `invalid_template` (syntax error with line), `unsupported_syntax`, `unknown_filter`, `legacy_placeholder`, and a trial-render error (`template_runtime_error`) from rendering a sample programme during validation. All keys translated in `en.json` and `de.json`.
- **D-11:** The post-render cleanup stays: `clean_title` (single line, collapsed spaces, dangling edge separators stripped, D-22) and `clean_description` (collapsed spaces, at most one blank line). Jinja whitespace control (`{%-`, `-%}`) remains available on top of it. An empty rendered title still falls back to the programme title.
- **D-12:** Documentation: a README section with the variables, the filters and 3-4 worked recipes (strip a "Formel 1" prefix, use the first description line as sub-title, conditional sub-title). The existing flow preview renders the real templates against real programmes. Field help texts stay short and point at the README.

### Claude's Discretion

- Whether `titles` (all `<title>` elements, currently stored on `Programme.titles`) is exposed as a list variable. The user mentioned several titles on some channels but did not ask for it explicitly; expose it if it comes for free.
- Exact names/signatures of the custom filters (`regex_replace`, `time`, ...) as long as D-06 is met.
- Regex safety (catastrophic backtracking in user patterns inside the render path); research should check what the include/exclude filter code already does and reuse it.
- Exact wording of English and German error and help texts.
- Whether the storage/subentry `VERSION` is bumped (the config flow is at `VERSION = 1`) given that D-08 forbids migration.

### Deferred Ideas (OUT OF SCOPE)

- Additional XMLTV fields in the model (year, rating, language, duration) — not discussed; own phase if wanted.
- `for` loops, macros and includes — deliberately excluded by D-04; revisit only with a concrete use case.
- Dual syntax / automatic migration of legacy `{field}` templates — rejected by D-08.
</user_constraints>

<phase_requirements>
## Phase Requirements

ROADMAP lists `**Requirements**: TBD` for Phase 5 [VERIFIED: .planning/ROADMAP.md:209]. No IDs were provided. The phase reworks behaviour that two completed requirements describe, so the planner must either re-open or supersede them and keep the traceability table honest.

| ID | Description | Research Support |
|----|-------------|------------------|
| EVT-03 (reworked) | Today: "User can configure the event title via placeholder template (`{channel}`, ...); default `{channel}: {title}`; unknown placeholders rejected in flow" [VERIFIED: REQUIREMENTS.md:42] | Whole engine design below. Recommend rewording to Jinja syntax and keeping "unknown variables rejected in flow" (via `meta.find_undeclared_variables`, see Pattern 2). |
| EVT-04 (reworked) | Today: "Event description contains sub-title, episode, categories and description by default; user can override it with a description template" [VERIFIED: REQUIREMENTS.md:44] | Default description stays `default_description()`; override uses the same engine. |
| (new, suggested) EVT-10 | "User can shape event titles and descriptions with sandboxed Jinja templates (conditions, text filters, local time)" | Recommend adding it plus the traceability row, and moving the "Jinja title templates" row out of Out of Scope (D-02). |
</phase_requirements>

## Summary

The phase is a swap of the engine *inside* `xmltv/render.py`; the class boundary (`EventTemplates`, `to_event_fields`, `template_values`, `clean_*`, `default_description`, `event_uid`) stays. The engine is `ImmutableSandboxedEnvironment` (the same class HA core's own `TemplateEnvironment` subclasses [VERIFIED: homeassistant/helpers/template/__init__.py:822]) with a pruned filter/test/global set, a compile-time AST whitelist, and a pre-registered set of custom filters. Nothing to install: `Jinja2==3.1.6` is pinned by HA core [VERIFIED: homeassistant/package_constraints.txt:47] and is already in the venv; `manifest.json` keeps `"requirements": []`.

Four findings change the plan relative to CONTEXT.md and are not obvious from it. (1) **Jinja has no `split` filter**; D-06 lists it among the "standard filters", so it must be a custom filter (verified by listing `env.filters`). (2) **D-07 needs `description` in the title template**, but today `TITLE_FIELDS` excludes it, so the two variable sets must be merged. (3) **The sandbox does not bound resources**: `(99**99999999) | string | length` hung the *compile* (constant folding; exit 124 under `timeout 10`), `'a' * 100000000` and `'%99999999d' % 1` each produced 100 MB, and a chain of ~143 `| trim` filters took ~600 ms to compile, then 286 filters failed with a raw Python `SyntaxError` (not a Jinja error). The AST whitelist must therefore also reject `*`, `**`, `%`, cap template length and filter-chain depth, and the compile wrapper must catch `SyntaxError`/`RecursionError`. (4) **Almost every existing calendar stores the legacy default `{channel}: {title}` literally** (the Phase 2 flow writes `title_template or DEFAULT_TITLE_TEMPLATE`), so a naive D-08 would log a WARNING for each of them at every start and flip their "Advanced" checkbox on; the legacy *default* string must be normalized silently.

Performance is a non-issue, which settles the D-02 objection with numbers: 5000 title+description renders took 27 ms (5.5 µs per event) against about 38 µs for the `CalendarEvent` construction that follows it [VERIFIED: local benchmark; CLAUDE.md benchmark table]. Compiling a typical template takes about 0.6 ms.

**Primary recommendation:** put the engine in a new pure module `xmltv/template_engine.py` (env, whitelist, filters, `TemplateError`, `compile_template`), keep `render.py` as the facade, and implement the whitelist as an explicit allow-list of AST node classes (everything else is `unsupported_syntax`), exactly as prototyped below.

## Architectural Responsibility Map

This is a Home Assistant integration (no browser/SSR/CDN tiers); the tiers below are the integration's own layers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Template compile, whitelist, filters, render | Pure library (`xmltv/`, no HA imports) | — | `test_purity.py` forbids `homeassistant` imports under `xmltv/`; keeps the engine unit-testable [VERIFIED: tests/xmltv/test_purity.py:23-33] |
| Local-time conversion of `start`/`end` | HA layer (callers pass a `tzinfo`) | Pure library (applies it) | The local zone comes from `dt_util`; render.py cannot import it |
| Validation + error keys + trial render | Config flow (`config_flow.py`) | Pure library (raises `TemplateError`) | Flow maps `err.reason` to form errors, as today |
| Stored-template fallback (legacy / invalid) | Pure library (`EventTemplates.from_mapping`) | `settings.with_defaults` | Existing `_stored` pattern logs WARNING and uses the default |
| Per-event rendering | Calendar entity / matcher (`build_events`, `describe_match`) | Executor for large slices | Rendering is synchronous and cheap; `build_events` already runs in the executor above 200 programmes |
| Event/sensor `summary` | Matcher `describe_match` | — | Uses the same `EventTemplates`, no template-dependent persisted state (verified below) |

## Project Constraints (from CLAUDE.md)

From `./.claude/CLAUDE.md` [VERIFIED: file read this session]:

- Python 3.14, HA >= 2026.3.0; Ruff `select = ["ALL"]`, line length 120, pinned 0.17.0; code, comments, commits in English.
- **No runtime requirements** (`"requirements": []`). jinja2 comes with HA core, so it is imported without being declared; do not add it to the manifest (an exact pin would clash with HA core's pin).
- Config Flow / Options Flow / Subentry flow only; no YAML.
- Performance: large feeds must not block the event loop. Rendering is per requested window only.
- Tests run with `pytest-homeassistant-custom-component`; use the built-in fixtures.
- **Stale note to update:** the CLAUDE.md stack table says titles use "a restricted `str.format`-style formatter, **not** HA Jinja templates" and lists "Restricted `str.format` placeholders" in Alternatives. User decisions D-01/D-02 supersede this; add a doc task to rewrite that passage (the "string.Formatter subclass" supporting-library row and the Jinja alternative row).
- GSD workflow: all edits go through `/gsd-execute-phase`; `workflow.tdd_mode: true` and `workflow.nyquist_validation: false` in `.planning/config.json` [VERIFIED: config.json]. TDD fits: the engine is pure and fast to test.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `jinja2` (`jinja2.sandbox.ImmutableSandboxedEnvironment`, `jinja2.nodes`, `jinja2.meta`) | 3.1.6 (HA core pin; venv has 3.1.6) | Template parse, AST whitelist, compile, sandboxed render | HA core's own template env subclasses this exact class [VERIFIED: venv `jinja2.__version__` printed 3.1.6; package_constraints.txt:47; homeassistant/helpers/template/__init__.py:822] |
| `re` (stdlib) | Python 3.14.8 | Custom regex filters | Same engine as the include/exclude filters; reuse `has_nested_repeat`, `MAX_PATTERN_LENGTH`, `PATTERN_ERRORS` from `xmltv/filter.py` [VERIFIED: filter.py:48,55,169] |
| `functools.lru_cache` (stdlib) | — | Compiled-pattern cache for the regex filters | HA's own regex filters do the same via `_regex_cache` [VERIFIED: homeassistant/helpers/template/extensions/regex.py:64-107] |

### Supporting

Nothing to install. HA-side helpers already in use: `dt_util.get_default_time_zone()` (already used by the flow preview [VERIFIED: config_flow.py:685-689]) supplies the `tzinfo` that callers pass into the pure module.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ImmutableSandboxedEnvironment` | `SandboxedEnvironment` (D-01's literal wording) | Immutable is a subclass that additionally blocks mutating list/dict methods; HA uses it. Recommend Immutable; no template this phase allows method calls anyway, so behaviour is identical for users. (A5) |
| HA `Template` class | — | Locked out by D-01 (event-loop hop, state access). |
| Jinja `Environment.getattr`-based method calls (`title.startswith('x')`) | Filters only | Method calls (`nodes.Call`) are rejected here, see Pitfall 5. |

**Installation:** none.

**Version verification:** `jinja2` is not installed by this phase, it is HA-provided. `gsd-tools query package-legitimacy check --ecosystem pypi jinja2` returned verdict `SUS` with the only reason `unknown-downloads` (the registry API gave no weekly download count; repo `github.com/pallets/jinja`, published 2025-03-05, not deprecated, no postinstall). This is a data gap, not a risk signal: the package is pinned by HA core and already imported by HA itself. No `checkpoint:human-verify` install task is needed because nothing is installed; the planner may still add one if it wants the SUS flag acknowledged.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| jinja2 | PyPI | long-standing (3.1.6 published 2025-03-05) | not returned by seam | github.com/pallets/jinja | SUS (reason: `unknown-downloads` only) | Not installed by this phase (HA core dependency, pinned `Jinja2==3.1.6`). Approved as an import; no install step. |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** jinja2 (seam data gap only, see above). No install happens, so no `checkpoint:human-verify` is required.

## Architecture Patterns

### System Architecture Diagram

```
 stored subentry data (title_template, description_template)       flow form input
              |                                                          |
              v                                                          v
   settings.with_defaults  --(legacy default "{channel}: {title}"  -->  _advanced_values
        | normalizes silently to new default)                            |
        v                                                                v
 EventTemplates.from_mapping(data, name)                    _advanced_errors(values)
        |                                                                |
        |  compile_template(text)  <-------------------------------------+
        |     1. length cap  2. legacy single-brace check  3. env.parse
        |     4. AST allow-list walk (nodes, filters, tests, const regex, chain depth)
        |     5. meta.find_undeclared_variables - allowed names
        |     6. env.from_string(ast)  (catch TemplateError | SyntaxError | RecursionError)
        |        |
        |        +-- TemplateError(reason, detail) --> stored: WARNING + default | flow: form error key
        |                                                  |
        |                                  trial_render(sample_full, sample_sparse) --> template_runtime_error
        v
 EventTemplates (sources for ==, compiled templates compare=False)
        |
        +--> calendar.build_events / entity.event / matcher.describe_match / preview.build_preview
                   |
                   v
        to_event_fields(programme, channel, templates, tz=...)
                   |
        template_values(programme, channel, tz) -> flat typed dict
                   |
        Template.render(**values)  --exception--> one WARNING per calendar, fallback (title / default description)
                   |
        clean_title / clean_description  --> EventFields(summary, location, description, uid)
```

### Recommended Project Structure

```
custom_components/xmltv_calendar/xmltv/
├── template_engine.py   # NEW, pure: ENV, whitelist, custom filters, TemplateError, compile_template, error reasons
├── render.py            # facade: EventTemplates, template_values, clean_*, default_description, event_uid, to_event_fields
├── settings.py          # DEFAULT_TITLE_TEMPLATE -> "{{ channel }}: {{ title }}", LEGACY_DEFAULT_TITLE_TEMPLATE
└── preview.py           # builds EventTemplates quietly (no WARNING spam from the flow)
```

Re-export `TemplateError` and `compile_template` from `render.py` so `config_flow.py`'s import line changes minimally. `test_purity.py` walks `LIBRARY.rglob("*.py")`, so the new module is covered automatically [VERIFIED: test_purity.py:23].

### Pattern 1: The environment (verified by execution)

```python
# Source: prototype run in the research session (jinja2 3.1.6); pattern mirrors HA's ImmutableSandboxedEnvironment use
import jinja2
from jinja2.sandbox import ImmutableSandboxedEnvironment

def _make_env() -> ImmutableSandboxedEnvironment:
    # No autoescape= kwarg: ruff S701 fires on an explicit autoescape=False (verified with the repo's ruff 0.17.0);
    # the default is already False and the output is plain text.
    env = ImmutableSandboxedEnvironment(undefined=jinja2.ChainableUndefined, trim_blocks=True, lstrip_blocks=True)
    env.filters = {name: fn for name, fn in env.filters.items() if name in ALLOWED_FILTERS}  # drop center, format, indent, e, attr, ...
    env.filters.update(CUSTOM_FILTERS)           # split, regex_replace, ... (split does NOT exist in Jinja)
    env.tests = {name: fn for name, fn in env.tests.items() if name in ALLOWED_TESTS}
    env.globals = {}                             # drops range, dict, lipsum, cycler, joiner, namespace
    return env
```

- `ChainableUndefined` makes `{{ missing.attr }}` and `{{ categories[5] }}` render `''` instead of raising (D-03 leniency); verified: `{{ categories[0] | upper }}|{{ subtitle | first_line }}|{{ categories[5] }}` renders `SPORT||`.
- `trim_blocks`/`lstrip_blocks` (recommendation, A2): a multi-line description such as `{% if episode %}\nEpisode: {{ episode }}\n{% endif %}\n{{ description }}` then renders without stray blank lines; `clean_description` would otherwise leave one blank line in place of each block tag line. Document it in the README. Either setting works with D-11; this is a UX choice for the user to confirm.
- Create **one** module-level environment (compile is per template, the env is thread-safe: 4 threads x 2000 renders, 0 errors [VERIFIED: probe4]).

### Pattern 2: Compile = parse, allow-list walk, undeclared-variable check, build from the AST

```python
# Source: prototype run in the research session
from jinja2 import meta, nodes

ALLOWED_NODES = (
    nodes.Template, nodes.Output, nodes.TemplateData, nodes.If, nodes.Assign,
    nodes.Name, nodes.Const, nodes.Tuple, nodes.List, nodes.Dict, nodes.Pair,
    nodes.Getattr, nodes.Getitem, nodes.Slice, nodes.Filter, nodes.Test, nodes.Keyword,   # Keyword: filter kwargs
    nodes.CondExpr, nodes.Concat, nodes.Add, nodes.Sub, nodes.Div, nodes.FloorDiv,
    nodes.And, nodes.Or, nodes.Not, nodes.Neg, nodes.Pos, nodes.Compare, nodes.Operand,
)  # deliberately absent: Mul, Pow, Mod (resource DoS), Call, For, Macro, CallBlock, Include, Import, Extends, Block,
   #                      With, AssignBlock, FilterBlock, NSRef

def compile_template(text: str) -> jinja2.Template:
    if len(text) > MAX_TEMPLATE_LENGTH:                       # A1: recommended 2000 chars
        raise TemplateError(INVALID_TEMPLATE, f"longer than {MAX_TEMPLATE_LENGTH} characters")
    if _is_legacy(text):                                      # D-08, see Pattern 5
        raise TemplateError(LEGACY_PLACEHOLDER, first_legacy_placeholder(text))
    try:
        ast = ENV.parse(text)                                  # TemplateSyntaxError (.lineno, .message)
        _check_ast(ast)                                        # raises TemplateError; walks ast.find_all(nodes.Node)
        unknown = meta.find_undeclared_variables(ast) - VARIABLES
        if unknown:
            raise TemplateError(UNKNOWN_PLACEHOLDER, ", ".join(sorted(unknown)))
        return ENV.from_string(ast)                            # from_string accepts a nodes.Template
    except jinja2.TemplateSyntaxError as err:
        raise TemplateError(INVALID_TEMPLATE, f"line {err.lineno}: {err.message}") from None
    except (SyntaxError, RecursionError):                      # Python's own compile() limits, see Pitfall 3
        raise TemplateError(INVALID_TEMPLATE, "template is too complex") from None
```

`_check_ast` must, for each node: reject classes outside `ALLOWED_NODES` (`unsupported_syntax`, detail `f"{type(node).__name__} (line {node.lineno})"`); for `nodes.Filter` check `node.name in ALLOWED_FILTERS` (`unknown_filter`), reject `dyn_args`/`dyn_kwargs` (star-args); for `nodes.Test` check `node.name in ALLOWED_TESTS`; reject `nodes.Name` named `self`; for the two regex filters require the first argument to be a `nodes.Const` string, `len <= MAX_PATTERN_LENGTH`, compile it, run `has_nested_repeat`, and for `regex_replace` also run `compiled.sub(repl, "")` to validate the replacement. Also compute the filter-chain length (`Filter` whose `.node` is a `Filter`, repeatedly) and reject chains over a cap (A1: 16).

Verified behaviours of this exact whitelist (prototype output, abbreviated):

| Input | Result |
|-------|--------|
| `{{ channel }}: {{ title \| regex_replace('^Formel ?1:? ?', '') }}` | `Sky Sport F1: Großer Preis` |
| `{{ title \| strip_prefix('Formel 1: ') }} ({{ start \| time('%H:%M') }})` | `Großer Preis (20:15)` |
| `{{ description \| first_line }} - {{ title \| split(':') \| last \| trim }}` | `Quali - Großer Preis` |
| `{% set sub = description \| first_line %}{% if sub %}{{ sub }}{% endif %}` | `Quali` |
| `{{ nope }}` / `{{ title \| nope }}` / `{{ title is nope }}` | `unknown_variable` (use `unknown_placeholder`) / `unknown_filter` / `unknown_filter` |
| `{% for ... %}`, `{% macro %}`, `{% import %}`, `{% include %}`, `{% extends %}`, `{% block %}`, `{% call %}`, `{% with %}`, `{% set x %}..{% endset %}`, `{% filter %}` | `unsupported_syntax` |
| `{{ title * 3 }}`, `{{ (99**99999999) \| string \| length }}`, `{{ title.upper() }}`, `{{ range(3) }}` | `unsupported_syntax` (Mul, Pow, Call, Call) |
| `{{ title \| center(10) }}`, `format`, `attr`, `e` | `unknown_filter` (not in the pruned set) |
| `{{ title.__class__.__mro__ }}` | renders `''` (sandbox blocks unsafe attributes) |
| `{{ title \| regex_replace('a','b', ignorecase=true) }}` | **rejected as `Keyword` unless `nodes.Keyword` is in the allow-list** (Pitfall 2) |

### Pattern 3: `EventTemplates` keeps its boundary, changes its insides

```python
@dataclass(frozen=True, slots=True)
class EventTemplates:
    title_source: str                                   # compared
    description_source: str | None                      # compared; None = default description
    _title: jinja2.Template = field(compare=False, repr=False)
    _description: jinja2.Template | None = field(default=None, compare=False, repr=False)
    _state: _WarnState = field(default_factory=_WarnState, compare=False, repr=False)  # mutable "warned" flag, name
```

- **Equality must be on the source strings.** `matcher.async_apply_subentry` does `write_state = templates != self._templates` [VERIFIED: matcher.py:416-418]. Compiled `jinja2.Template` objects compare by identity, so every `from_mapping` would count as "changed" and fire an extra `signal_matches` on every filter-only edit.
- `from_mapping(data, name=None)`: the new optional `name` is the calendar title for the single WARNING (D-03); `preview.build_preview` passes none and stays silent. Callers today: `matcher.py:130`, `matcher.py:416`, `preview.py:81` [VERIFIED: grep].
- `render_title` / `render_description` catch `Exception` (template user code can raise anything: `ZeroDivisionError`, `TypeError`, `re.error` all observed), log one WARNING per calendar with the exception **type name only** (feed text must not leak into logs, matching the Phase 3 content-free warning convention; details at DEBUG), and return the fallback (`programme.title` / `default_description(programme)`). `# noqa: BLE001` with a comment, as Phase 3 did for `_async_update_data`.
- Keep a separate strict path (`_render_strict`) that raises, used only by the flow's trial render.

### Pattern 4: Variables (flat, typed) and the local-time parameter

`Programme` fields available [VERIFIED: model.py:23-35]:

```python
    channel_id: str
    start: datetime  # tz-aware
    stop: datetime  # tz-aware, never earlier than start
    titles: tuple[str, ...]  # all title elements, document order; titles[0] is the display title
    sub_titles: tuple[str, ...]
    description: str | None
    categories: tuple[str, ...]
    episode: str | None  # raw first episode-num text
```

Recommended `template_values(programme, channel, tz=None)` result. Existing keys keep their current meaning [VERIFIED: render.py:111-121]; additions come from D-05:

| Variable | Type | Value |
|----------|------|-------|
| `channel` | str | `channel.display_name`, else `programme.channel_id` |
| `channel_id` | str | `programme.channel_id` |
| `title` | str | `programme.title` |
| `titles` | list[str] | `list(programme.titles)` (free; the discretion item, recommend exposing) |
| `subtitle` | str | first of `sub_titles`, else `""` |
| `subtitles` | list[str] | `list(programme.sub_titles)` |
| `episode` | str | `programme.episode or ""` |
| `category` | str | `", ".join(programme.categories)` |
| `categories` | list[str] | `list(programme.categories)` |
| `description` | str | `programme.description or ""` (**available in both templates**, D-07) |
| `start`, `end` | datetime | `programme.start` / `programme.stop`, `astimezone(tz)` when `tz` is given (the model calls the end `stop`; the variable is `end`, D-05) |

- **Merge `TITLE_FIELDS` and `DESCRIPTION_FIELDS` into one `VARIABLES` set.** Today `TITLE_FIELDS = frozenset({"channel", "title", "subtitle", "episode", "category", "channel_id"})  # D-21` and `DESCRIPTION_FIELDS = TITLE_FIELDS | {"description"}` [VERIFIED: render.py:20-21]. D-07 requires `{{ description | first_line }}` in the *title* template. The flow placeholders `title_fields` / `description_fields` in `_ADVANCED_PLACEHOLDERS` [VERIFIED: config_flow.py:441-447] and the translations collapse into one `variables` placeholder.
- **Local time:** `render.py` cannot import HA. Add an optional keyword `tz: tzinfo | None = None` to `to_event_fields` and `template_values`; without it `start`/`end` stay as parsed (aware, feed offset), so every existing call `to_event_fields(p, None)` keeps working. Callers pass the HA zone: `calendar._to_event` (and `build_events`, which runs in the executor, so resolve `dt_util.get_default_time_zone()` once on the loop and pass it down rather than relying on thread context), `matcher.describe_match`, and `preview.build_preview` (already has `tz`). The signature stays compatible, as CONTEXT.md requires.
- `strftime` names (`%a`, `%B`) follow the process locale, which is global and not thread-safe; `preview.py` uses fixed tables for that reason [VERIFIED: preview.py:18-22 comment "Fixed tables instead of the process locale, which is global and not thread-safe (A3)"]. Document the `time` filter with numeric directives (`%H:%M`, `%d.%m.`) and note weekday/month names are English (A3). German weekday names would be a separate small feature, not in D-06.

### Pattern 5: Legacy detection (D-08) and the silent legacy default

- Detect with a regex over the seven legacy names only: `\{(channel_id|channel|title|subtitle|episode|category|description)\}` combined with "contains neither `{{` nor `{%`". Restricting to the known names avoids false positives on literal text such as `{live}`, and old stored templates could only ever contain those names (old validation rejected everything else). Whether to also flag mixed templates is a judgement call; D-08 says "no `{{ }}` / `{% %}`", so follow it literally.
- **Normalize the exact legacy default silently.** The Phase 2 flow stores `title_template or DEFAULT_TITLE_TEMPLATE` [VERIFIED: config_flow.py:513 `CONF_TITLE_TEMPLATE: title_template or DEFAULT_TITLE_TEMPLATE,`], so existing calendars carry `{channel}: {title}` [VERIFIED: settings.py:49 `DEFAULT_TITLE_TEMPLATE = "{channel}: {title}"  # D-20`]. In `with_defaults`, map that exact string to the new default. Effects avoided: a WARNING per calendar per load, and `has_advanced()` (compares every stored value with `ADVANCED_DEFAULTS` [VERIFIED: settings.py:157-160]) returning True so the Advanced box opens pre-checked.
- Customized legacy templates (the only real "hard break" casualties): `EventTemplates.from_mapping` warns once and falls back to the default; the advanced form shows the stored text and rejects an unchanged resubmit with `legacy_placeholder` until the user rewrites it.
- Known edge: an old template that used `{{`/`}}` as escaped literal braces now reads as a Jinja expression. Very unlikely; mention in the README upgrade note.

### Pattern 6: Custom filters (HA-compatible signatures)

HA's own filters are `regex_replace(value, find, replace, ignorecase=False)` and `regex_search(value, find, ignorecase=False) -> bool` [VERIFIED: extensions/regex.py:71-92]; the CONTEXT example `{{ title | regex_replace('^Formel ?1:? ?', '') }}` matches that shape. Recommended contract (all accept `Undefined`/`None` and treat it as `""`; D-06 "empty value, not raise"):

| Filter | Signature | Returns |
|--------|-----------|---------|
| `split` | `split(value, sep=None, maxsplit=-1)` | list[str] (custom: **not a Jinja builtin**) |
| `regex_replace` | `(value, find, replace="", ignorecase=False)` | str; `find` must be a string literal (validated at compile) |
| `regex_search` | `(value, find, ignorecase=False)` | bool (use inside `if`) |
| `strip_prefix` / `strip_suffix` | `(value, text)` | `str.removeprefix` / `removesuffix` |
| `remove` | `(value, *parts)` | str with each part removed |
| `lines` | `(value)` | stripped non-blank lines, `[]` when empty |
| `first_line` | `(value)` | first non-blank line, `""` when none |
| `time` | `(value, fmt="%H:%M")` | `value.strftime(fmt)` when `isinstance(value, datetime)`, else `""` |

Allowed standard filters (prune everything else): `abs capitalize count d default first int join last length list lower map max min reject replace reverse round select sort string title trim truncate unique upper wordcount`. Allowed tests: `defined undefined none string number integer eq equalto ne ge gt le lt in sameas lower upper odd even`. This covers every filter D-06 names except `split` (custom). `time` is not a Jinja builtin either [VERIFIED: filter listing in probe1].

### Anti-Patterns to Avoid

- **Whitelisting node classes by guesswork.** A first-draft allow-list without `nodes.Keyword` rejected `regex_replace(..., ignorecase=true)`; always test kwargs, `elif`, tuple `set`, slices, negative indices.
- **Relying on Jinja's own errors for unknown filters.** Do your own name check on `nodes.Filter`/`nodes.Test`; Jinja can defer "No filter named" to render time in some contexts.
- **Letting regex filters compile patterns at render time without validation.** Validate const patterns at compile, cache with `lru_cache`.
- **Using `ImmutableSandboxedEnvironment(autoescape=False)`.** Ruff S701 flags it; omit the kwarg.
- **Passing `Undefined` into `strftime`.** With `ChainableUndefined`, `hasattr(value, "strftime")` is True and the call then raises `UndefinedError`; use `isinstance(value, datetime)`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Template parsing / control flow | A custom mini-language or regex substitution | `jinja2` `ImmutableSandboxedEnvironment` | Locked by D-01 |
| Detecting unknown variables | Regex over the template text | `jinja2.meta.find_undeclared_variables(ast)` | Understands `set`-assigned names and scoping; verified: `{% set sub = ... %}{% if sub %}` passes, `{{ nope }}` is flagged |
| Syntax error line numbers | Own line counting | `TemplateSyntaxError.lineno` / `.message` | Already provided |
| Regex nesting check | New ReDoS heuristic | `xmltv.filter.has_nested_repeat`, `MAX_PATTERN_LENGTH`, `PATTERN_ERRORS` | The include/exclude path already uses them; same documented residual risk (overlapping alternation such as `(a\|aa)+` is not detected) |
| Compiled-pattern cache | Dict with manual eviction | `functools.lru_cache` | Thread-safe, as HA's regex filters |
| Whitespace/edge cleanup | New cleanup | existing `clean_title` / `clean_description` | D-11 keeps them |

**Key insight:** the sandbox is an *attribute-access* sandbox, not a *resource* sandbox (the Jinja docs say so: "It is possible to construct a relatively small template that renders to a very large amount of output" and recommend running with CPU/memory limits [CITED: jinja.palletsprojects.com/en/stable/sandbox/]). The AST allow-list is what bounds cost; that is why D-04's "no runtime timeout needed" holds only if `*`, `**`, `%` and long filter chains are excluded.

## Runtime State Inventory

Not a rename/refactor of identifiers, but the phase changes the *syntax of stored values*, so the stored-data question is answered explicitly:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Subentry data keys `title_template` / `description_template` hold legacy `{field}` text in existing calendars (most hold the literal default `{channel}: {title}`). Key names stay [VERIFIED: settings.py:31-32]. Match store and seen-sets are keyed by `event_uid` (hash of the raw title), never by rendered text [VERIFIED: matches.py:57-73 `uid = event_uid(programme)`; `grep -n "summary\|templates\|render\."` found no rendered-text state in `match_store.py`] | Code edit only (read-time fallback); **no data migration** (D-08). No `VERSION` bump (see Open Question 3). |
| Live service config | None — verified: HA state is not read; the blueprint (`blueprints/automation/xmltv_calendar/notify_before_programme.yaml`) uses HA `value_template`s on event data, not this templating | None |
| OS-registered state | None — no OS registrations involve template text | None |
| Secrets / env vars | None | None |
| Build artifacts | None — `custom_components/` is not built; `.venv` already has jinja2 3.1.6 | None |

A template edit that changes the title must not re-announce matches. Verified: `new_matches` uses `event_uid(programme)` [VERIFIED: matches.py:68]; `event_uid` hashes `programme.title` (raw) [VERIFIED: render.py:164-168]; `describe_match` only *reads* the rendered `summary` for the sensor/event payload [VERIFIED: matcher.py:368-387]. A regression test should pin: edit title template, assert no `xmltv_calendar_new_match` events and identical UIDs.

## Common Pitfalls

### Pitfall 1: `split` is not a Jinja filter
**What goes wrong:** D-06 lists `split` among the standard filters; `{{ title | split(':') }}` fails with "No filter named 'split'".
**Why it happens:** Jinja 3.1.6 has no such builtin [VERIFIED: `'split' in env.filters` is False; full builtin list printed].
**How to avoid:** Ship `split` as a custom filter (Pattern 6).
**Warning signs:** a unit test for the D-07 recipe `title | split(':') | last` failing at compile.

### Pitfall 2: AST allow-list that forgets structural nodes
**What goes wrong:** `ignorecase=true` kwargs, `elif`, tuple targets, slices rejected as `unsupported_syntax`.
**Why it happens:** filter keyword arguments are `nodes.Keyword`; `Operand`/`Compare` and `Slice` are separate classes.
**How to avoid:** Use the allow-list in Pattern 2 and test every construct in the README recipes plus kwargs.
**Warning signs:** `unsupported_syntax: Keyword`.

### Pitfall 3: Compile cost and non-Jinja compile errors (event-loop stalls, raw SyntaxError)
**What goes wrong:** Compile happens on the event loop (matcher init, `async_apply_subentry`, flow submit). Measured filter-chain compile time: 20 filters 3.5 ms, 40 filters 17.9 ms, 80 filters 121.7 ms, 120 filters 398 ms, ~143 filters ~600 ms; at ~286 filters Python raised `SyntaxError`; 253 nested `{% if %}` raised `IndentationError`; ~2500 nested parens raised `RecursionError` [VERIFIED: probe6/probe7]. `jinja2.TemplateSyntaxError` is not a `SyntaxError` subclass, so `except jinja2.TemplateError` does not catch these.
**How to avoid:** length cap (A1: 2000 chars, description may need more, say 5000), filter-chain cap (A1: 16), and `except (SyntaxError, RecursionError)` around parse/walk/compile. Both walking (`ast.find_all`) and `from_string` can raise `RecursionError`.
**Warning signs:** flow submit hanging; an unhandled `IndentationError` in the flow.

### Pitfall 4: Constant folding hangs the compile (not just the render)
**What goes wrong:** `{{ (99**99999999) | string | length }}` never finished compiling (timeout, exit 124). Jinja folds constant expressions at compile time; `intercepted_binops` defaults to an empty frozenset [VERIFIED: sandbox.py:225], so the sandbox does not interfere. `{{ 'a' * 100000000 }}` and `{{ '%99999999d' % 1 }}` produced 100 MB strings in ~0.35 s.
**How to avoid:** the AST walk runs *before* `from_string`, so rejecting `Mul`, `Pow`, `Mod` removes the hazard entirely (also `range` is gone with `env.globals = {}`; `center`/`indent`/`wordwrap`/`format` are gone with the pruned filters). Do not use `intercepted_binops` instead: Jinja warns intercepted calls are slower, and the whitelist is simpler.
**Warning signs:** a flow submit that freezes HA.

### Pitfall 5: Method calls and "call" in D-04
**What goes wrong:** D-04 says `call` is rejected; the AST has both `CallBlock` (`{% call %}`) and `Call` (any `x(...)`, including `title.upper()` and `namespace(...)`).
**Why it matters:** `str.format` is the next DoS (`'{:>99999999}'.format('x')`), and method calls bypass the filter allow-list. Recommended: reject all `nodes.Call` (unsupported_syntax) since every needed operation is a filter. Users who expect `title.startswith('F')` get a clear error; the README recipes use `regex_search`/`strip_prefix`. Flag for user confirmation (A6).

### Pitfall 6: `EventTemplates` equality with compiled templates
**What goes wrong:** every `from_mapping` yields an "unequal" object, so filter-only edits trigger `write_state`/`signal_matches` (matcher.py:416-418).
**How to avoid:** compare source strings, `compare=False` on compiled fields (Pattern 3).

### Pitfall 7: Existing calendars all carry the legacy default
See Pattern 5. Without the silent normalization every pre-Phase-5 calendar logs a WARNING per start and opens "Advanced" in the reconfigure flow.

### Pitfall 8: `{{ ... }}` in translation strings
**What goes wrong:** in HA translation strings `{...}` is an ICU placeholder; a literal `{{ title }}` in `en.json`/`de.json` breaks placeholder parity tests and hassfest.
**How to avoid:** the existing trick: pass the literal text as a `description_placeholders` *value* (as `_TITLE_FIELD_NAMES` is today [VERIFIED: config_flow.py:441-447, comment "a literal {channel} in a translation is an ICU placeholder"]) and reference `{variables}` in the string. Keep help texts short and point at the README (D-12).

### Pitfall 9: test_translations imports the old reason constants
`tests/test_translations.py` adds `render.INVALID_TEMPLATE, render.UNKNOWN_PLACEHOLDER, "invalid_regex"` to the required `error` keys by hand [VERIFIED: test_translations.py, `_flow_requirements` end]. Export a `TEMPLATE_ERROR_REASONS` tuple from the engine and have the test iterate it (same pattern Phase 4 used for `FAILURE_REASONS`), so a new reason cannot be forgotten in `en.json`/`de.json`. `_error_literals` only sees literal `errors[x] = "key"`, and the flow assigns `err.reason` dynamically, so this constant is the only guard.

### Pitfall 10: Runtime errors only appear at render
`{{ 1/0 }}` (`ZeroDivisionError`), `{{ title | truncate('a') }}` (`TypeError`), `{{ start | time(5) }}` (`TypeError`), and `regex_replace('a', '\\g<9>')` (`re.PatternError`, which is `re.error` [VERIFIED: `re.PatternError is re.error` -> True]) pass compile. Const-regex validation catches the pattern/replacement cases at compile (the bad replacement raised even with no match, so `compiled.sub(repl, "")` is a valid compile-time probe [VERIFIED: probe4]); the rest rely on the trial render (flow) and the render-time fallback (runtime). Trial-render two synthetic programmes: a fully populated one and a sparse one (no sub-title/description/categories/episode, empty lists), because optional-field handling is where lenient templates break.

### Pitfall 11: Ruff `ALL`
Expect `C901`/`PLR0912` on a monolithic `_check_ast`; split per node family. Broad `except Exception` needs `# noqa: BLE001`. Avoid an explicit `autoescape=False` (S701). Multi-exception clauses use the PEP 758 unparenthesized form because ruff 0.17 rewrites the parenthesized one [VERIFIED: STATE.md decision 01-11].

## Code Examples

### Rendering with fallback and strict trial path

```python
# Source: design derived from the existing EventTemplates (render.py) plus prototype-verified engine calls
def _render(self, template: jinja2.Template, values: Mapping[str, object]) -> str:
    return template.render(**values)           # may raise anything a user template can provoke

def render_title(self, programme: Programme, values: Mapping[str, object]) -> str:
    try:
        text = self._render(self._title, values)
    except Exception as err:  # noqa: BLE001 - user template code can raise anything; one broken programme must not fail the window
        self._warn_once("title", err)           # one WARNING per calendar, exception type only
        return programme.title
    return clean_title(text) or programme.title  # empty render falls back, D-11

def render_description(self, programme: Programme, values: Mapping[str, object]) -> str | None:
    if self._description is None:
        return default_description(programme)
    try:
        text = self._render(self._description, values)
    except Exception as err:  # noqa: BLE001
        self._warn_once("description", err)
        return default_description(programme)
    return clean_description(text)
```

### Flow wiring (replaces the template block in `_advanced_errors`)

```python
# Existing shape [VERIFIED: config_flow.py:543-551]:  errors[field] = err.reason; placeholders.setdefault("template_error", err.detail)
# New: same shape, one call per non-blank template, then the trial render of what compiled
for field, text in templates:                       # title always, description only when text.strip()
    try:
        compile_template(text)
    except TemplateError as err:
        errors[field] = err.reason
        placeholders.setdefault("template_error", err.detail)
if not errors_for_templates:
    try:
        trial_render(values[CONF_TITLE_TEMPLATE], values[CONF_DESCRIPTION_TEMPLATE])
    except TemplateError as err:                    # reason == "template_runtime_error"
        ...
```

### Spot checks that become tests (all verified in the prototype)

```python
assert render("{{ channel }}: {{ title | regex_replace('^Formel ?1:? ?', '') }}") == "Sky Sport F1: Großer Preis"
assert render("{% if subtitle %}{{ subtitle }}{% else %}{{ categories | join(', ') }}{% endif %}") == "Sport, Motorsport"
assert render("{{ categories[0] | upper }}|{{ subtitle | first_line }}|{{ categories[5] }}") == "SPORT||"
assert compile_error("{{ title * 3 }}").reason == "unsupported_syntax"
assert compile_error("{{ title | nope }}").reason == "unknown_filter"
assert compile_error("{{ nope }}").reason == "unknown_placeholder"
assert compile_error("{channel}: {title}").reason == "legacy_placeholder"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `string.Formatter.parse` + `format_map`-style join (`compile_template`/`render_template`) | Jinja2 sandbox, precompiled, AST-whitelisted | This phase (D-01/D-02) | Conditions, text filters, local time; hard break for custom templates |
| Separate `TITLE_FIELDS` / `DESCRIPTION_FIELDS` | One variable set | This phase (D-07) | Description is usable in titles; one `variables` flow placeholder |
| REQUIREMENTS.md "Jinja title templates" out of scope | In scope | D-02 | Update REQUIREMENTS.md, PROJECT.md key decision, `.claude/CLAUDE.md` stack notes |

**Deprecated/outdated after this phase:** `compile_template(text, allowed)`, `render_template`, `CompiledTemplate` tuple type, `TITLE_FIELDS`/`DESCRIPTION_FIELDS`, `_FORMATTER`, `UNKNOWN_PLACEHOLDER` meaning (keep the *key*, change the text, see Open Question 1).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Caps: template length 2000 chars (title) / 5000 (description), filter chain <= 16, are sensible limits | Pitfall 3, Pattern 2 | Too low frustrates a power user; too high re-opens the compile-time stall. Measured only that chains of 20 take 3.5 ms and 80 take 122 ms; the exact caps are a judgement |
| A2 | Enable `trim_blocks` and `lstrip_blocks` | Pattern 1 | Users used to HA's Jinja defaults (both False) may be surprised that a newline after `{% ... %}` vanishes; either choice works with D-11 cleanup. Needs user/planner confirmation |
| A3 | The HA process runs with the C locale so `%a`/`%B` yield English names | Pattern 4 | German weekday names might appear on some hosts, or not at all; avoid documenting name directives |
| A4 | Reuse the existing error key `unknown_placeholder` (reworded) for undeclared variables, rejecting unknown names in the flow | Pattern 2, Phase Requirements | D-10's key list does not name it; EVT-03 currently promises "unknown placeholders rejected in flow", so dropping it would silently remove a requirement. User should confirm |
| A5 | `ImmutableSandboxedEnvironment` instead of D-01's `SandboxedEnvironment` | Standard Stack | Behaviourally identical for this feature set; subclass; low risk |
| A6 | Reject every `nodes.Call` (method calls like `title.startswith()`), reading D-04's "call" broadly | Pitfall 5 | If the user expected method calls, they get `unsupported_syntax`; filters cover the use cases |
| A7 | Reject `*`, `**`, `%` operators (extends D-04's explicit reject list) | Pitfall 4 | Measured hazard; users lose `'-' * 10` style decoration only |
| A8 | `regex_search` returns a bool (HA-compatible) rather than the matched text | Pattern 6 | Extracting a capture group needs `regex_replace('^.*?(\\d+).*$', '\\1')`; a `regex_find` filter is outside D-06's closed list |
| A9 | `lines` drops blank lines and strips each line; `first_line` = first non-blank line | Pattern 6 | If the user wants raw `splitlines()` semantics, an empty first line would differ |

## Open Questions

1. **Unknown variables: reject in the flow?**
   - What we know: EVT-03 says unknown placeholders are rejected; `meta.find_undeclared_variables` makes it cheap and accurate; D-03 makes undefined *runtime* values lenient, which is a different matter (a typo such as `{{ titel }}` would otherwise render empty forever).
   - What's unclear: D-10 lists five error keys and omits this one.
   - Recommendation: keep `unknown_placeholder` (reword to "unknown variable"), tagged A4; confirm with the user in plan review.

2. **Requirement IDs.** ROADMAP says TBD. Recommend EVT-03/EVT-04 reworded plus a new EVT-10, and moving the out-of-scope row. The planner should decide and update the traceability table.

3. **`VERSION` bump?** The only `VERSION` is the config flow's `VERSION = 1` [VERIFIED: config_flow.py:192]; there is no `async_migrate_entry` in the integration. Recommend **no bump**: stored keys and shapes are unchanged, D-08 forbids migration, and a bump would require writing a migration and would make a downgrade fail.

4. **README scope for `time`.** Is German weekday naming wanted? Out of D-06; deferred unless the user asks.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (repo `.venv`) | everything | ✓ | 3.14.8 | — |
| jinja2 (HA-provided) | engine | ✓ | 3.1.6 | — |
| homeassistant (phcc) | tests, flow | ✓ | 2026.10.1 | — |
| pytest (phcc) | tests | ✓ | `.venv/bin/pytest` present; baseline `tests/xmltv/test_render.py tests/test_templates.py tests/xmltv/test_purity.py` -> 51 passed in 0.45 s | — |
| ruff | lint | ✓ | 0.17.0 (pinned in pyproject) | — |
| gsd-tools package-legitimacy | audit | ✓ | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Validation Architecture

Skipped: `workflow.nyquist_validation` is `false` in `.planning/config.json` [VERIFIED: config.json]. For planning orientation only, the test files that exercise the old syntax and need rewriting (counts of lines matching old placeholders/template keys, from `grep -c`): `tests/xmltv/test_render.py` (37), `tests/test_advanced_flow.py` (26), `tests/xmltv/test_settings.py` (17), `tests/test_templates.py` (6), `tests/test_matcher_races.py` (6), `tests/test_reconfigure.py` (4), `tests/xmltv/test_parser.py` (3), `tests/xmltv/test_preview.py` (3), plus single hits in `test_filtering`, `test_matcher_runtime`, `test_new_match_event`, `test_retention`, `test_sensor`, `test_subentry_flow`; and `tests/test_translations.py` (constants import, Pitfall 9). Quick command: `.venv/bin/python -m pytest tests/xmltv -q` (about 0.5 s for the render/purity subset).

## Security Domain

`security_enforcement` is enabled (absent or true), ASVS level 1 [VERIFIED: config.json `security_asvs_level: 1`, `security_block_on: high`].

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (config flows are already admin-only in HA) |
| V3 Session Management | no | — |
| V4 Access Control | no | Only HA admins can add/edit subentries; unchanged |
| V5 Input Validation | **yes** | Compile-time AST allow-list, length and chain caps, const-regex validation, `find_undeclared_variables`, trial render; stored values re-validated at load |
| V6 Cryptography | no | — |

### Known Threat Patterns for sandboxed Jinja templating

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Server-side template injection / sandbox escape | Elevation of privilege | `ImmutableSandboxedEnvironment`, no globals, no `Call`, no `attr` filter, pruned filters; unsafe attributes render empty (`{{ title.__class__.__mro__ }}` -> `''`); reject `self` |
| Resource exhaustion at compile or render (`**`, `*`, `%`, huge `center`, `range`, long chains) | Denial of service | Operators and filters excluded by the allow-list (see Pitfall 4); template length and chain caps; `SyntaxError`/`RecursionError` caught |
| Catastrophic regex backtracking in `regex_replace`/`regex_search` | Denial of service | Const-pattern only, 300-char cap, `has_nested_repeat` rejection, shared `lru_cache`; residual risk for overlapping alternation is the same as the include/exclude filters (documented there) |
| Feed text treated as a template | Tampering | Never: feed values are *context data*, not template source; Jinja does not re-render values |
| Information disclosure through logs | Information disclosure | One WARNING per calendar with the exception type only; details at DEBUG; no feed text, no URL |
| Access to HA state/secrets from templates | Information disclosure | No HA environment: render context is only the programme variables; `env.globals = {}` |
| Hand-edited storage bypassing the flow | Tampering | Same `compile_template` at load; failure -> WARNING + default |

## Sources

### Primary (HIGH confidence)
- Local execution against the repo `.venv` (jinja2 3.1.6, Python 3.14.8): filter/test/global listings, `split` absence, sandbox DoS probes, AST whitelist prototype, runtime failure modes, thread safety, timings, compile-scaling probes, ruff S701 check.
- `homeassistant/helpers/template/__init__.py:822` (HA's `TemplateEnvironment(ImmutableSandboxedEnvironment)`), `extensions/regex.py:64-107` (regex filter signatures), `package_constraints.txt:47` (`Jinja2==3.1.6`) in the venv.
- `jinja2/sandbox.py:225` (`intercepted_binops` default empty; `call_binop`), `jinja2/meta.py:34` (`find_undeclared_variables`).
- Repo files read this session: `xmltv/render.py`, `xmltv/model.py`, `xmltv/settings.py`, `xmltv/filter.py`, `xmltv/preview.py`, `config_flow.py` (lines 420-720), `matcher.py` (100-180, 340-475), `calendar.py`, `matches.py` (57-82), `tests/xmltv/test_purity.py`, `tests/test_translations.py` (236-372), `README.md` (120-215), `en.json`/`de.json` (template keys), `.planning/*` and `.claude/CLAUDE.md`.

### Secondary (MEDIUM confidence)
- https://jinja.palletsprojects.com/en/stable/sandbox/ — sandbox does not bound output size ("relatively small template that renders to a very large amount of output"), binary operators are interceptable (`//, %, +, *, -, /, **`), recommends resource limits.

### Tertiary (LOW confidence)
- None used. The caps in A1 and the locale claim in A3 are assumptions, listed above.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependency; jinja2 version and HA's own use verified in the venv.
- Architecture: HIGH — integration points (callers, equality, stored defaults, UID independence) verified by reading the code.
- Pitfalls: HIGH — each pitfall was reproduced by running it, with timings; cap values (A1) are the only judgement.

**Research date:** 2026-10-23
**Valid until:** 2026-11-22 (jinja2 pinned by HA 2026.10.1; recheck if the phcc/HA pin moves)
