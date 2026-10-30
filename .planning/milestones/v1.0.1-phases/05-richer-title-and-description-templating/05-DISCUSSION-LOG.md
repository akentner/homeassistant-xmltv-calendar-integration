# Phase 5: Richer title and description templating - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-23
**Phase:** 5-Richer title and description templating
**Areas discussed:** Template mechanism, Text functions (follow-up), Compatibility & UX

---

## Template mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Jinja2 sandboxed | `SandboxedEnvironment` directly, precompiled, no HA state; reverses the "Jinja too slow" requirement | ✓ |
| Extended format syntax | Own parser: defaults, simple condition, format specs | |
| Own mini language | Fixed function set (if, truncate, replace, date) | |

**User's choice:** Jinja2 sandboxed

### Legacy templates

| Option | Description | Selected |
|--------|-------------|----------|
| One-time migration | Subentry migration converts `{x}` to `{{ x }}` | |
| Both syntaxes in parallel | Old templates without `{{ }}` keep str.format behaviour | |
| Hard break | No migration; old templates fall back | ✓ |

**User's choice:** Hard break

### Legacy detection

| Option | Description | Selected |
|--------|-------------|----------|
| Detect + default | Detect legacy placeholders on load, WARNING + default; flow rejects with `legacy_placeholder` | ✓ |
| Reject in flow only | Stored values would render literally | |
| Catch nothing | Literal output after update | |

**User's choice:** Detect + default

### Missing values and runtime errors

| Option | Description | Selected |
|--------|-------------|----------|
| Lenient + fallback | Empty strings; runtime error → one WARNING and fallback title/description | ✓ |
| Strict | Missing field raises | |
| Lenient without fallback | Errors propagate | |

**User's choice:** Lenient + fallback

### Sandbox protection

| Option | Description | Selected |
|--------|-------------|----------|
| AST whitelist | Reject for/macro/call/include/import/extends at compile time | ✓ |
| Allow all + output limit | No protection against long loops | |
| Allow all, render in executor | Complicates `async_get_events` and preview | |

**User's choice:** AST whitelist

### Variables

| Option | Description | Selected |
|--------|-------------|----------|
| Flat, typed | Existing names plus list values and start/end datetimes | ✓ |
| One `programme` object | All names change | |
| Flat strings only | As today | |

**User's choice:** Flat, typed

### Helpers

| Option | Description | Selected |
|--------|-------------|----------|
| Small custom set | Standard filters plus time formatter and regex_replace | ✓ |
| Standard filters only | | |
| Rebuild HA template functions | | |

**User's choice:** Small custom set

---

## Text functions (free-text follow-up)

**User's input:** "Wichtig sind Funktionen für die Text-Manipulation: split, filter, concat, etc. UseCase: Ich habe mehrere Title erkannt bei bestimmten Sendern, die bearbeitet werden müssen. z.B. wenn ich mir einen Kalender mit Formel 1 Sendungen baue, dann brauche ich nicht nochmal Formel 1 im Titel. Oder: Ein Teil des Titels ist in der ersten Zeile der Description. Eventuell Kontrollstrukturen wie "if"."

| Option | Description | Selected |
|--------|-------------|----------|
| regex_replace / regex_search | Regex-based text editing | ✓ |
| strip_prefix / strip_suffix / remove | Simple literal editing | ✓ |
| lines / first_line | Robust on empty description | ✓ |
| All titles available | `titles` list variable | |

**User's choice:** regex_replace / regex_search, strip_prefix / strip_suffix / remove, lines / first_line
**Notes:** `titles` not selected; left to Claude's discretion.

---

## Compatibility & UX

| Option | Description | Selected |
|--------|-------------|----------|
| Key + detail | Error keys plus Jinja message with line via description_placeholders; trial render | ✓ |
| One generic key | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Keep cleanup | clean_title / clean_description stay after rendering | ✓ |
| Remove | | |
| Title only: lines and spaces | | |

| Option | Description | Selected |
|--------|-------------|----------|
| README + preview | README recipes, preview renders real templates | ✓ |
| README only | | |
| Detailed in-flow help texts | | |

---

## Claude's Discretion

- Exposure of `titles`, exact filter names, regex safety in the render path, error/help wording, storage version bump.

## Deferred Ideas

- More XMLTV fields in the model; `for`/macro/include; migration or dual syntax.
