# Phase 2: Precise Filters & Preview - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log preserves the alternatives considered.

**Date:** 2026-10-15
**Phase:** 02-precise-filters-preview
**Areas discussed:** Form layout, Preview behaviour, Time/duration semantics, Fields & templates

---

## Form layout

| Option | Description | Selected |
|--------|-------------|----------|
| One form + sections | Basic fields on top, collapsed sections for fields/case, time/duration, templates | |
| Multiple steps | One step each for name+channels, text filters, time, templates, preview | |
| Basic + optional advanced step | Basic step with an "Advanced" checkbox that leads to an advanced step | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| 2 multi-selects | Separate field selection for include and exclude, default title+sub-title | ✓ |
| Shared selection | One selection for both, which does not satisfy FLT-05 | |

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-on when used | Checkbox pre-checked when advanced values differ from defaults; unchecking keeps values | ✓ |
| Always off, values kept | | |
| Uncheck = reset | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Case toggle in advanced step | | ✓ |
| Case toggle in basic step | | |

---

## Preview behaviour

| Option | Description | Selected |
|--------|-------------|----------|
| Own step | Preview step with Save / Back | ✓ |
| Inline in same form | "Preview only" checkbox that re-renders the form | |
| True live preview | WebSocket preview component; high risk for custom integrations | |

| Option | Description | Selected |
|--------|-------------|----------|
| From now, whole feed | | ✓ |
| Everything in feed incl. past | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Date time · channel · rendered title | | ✓ |
| Date time · channel · raw title | | |

| Option | Description | Selected |
|--------|-------------|----------|
| 0 matches: warning, saving allowed | | ✓ |
| 0 matches: block saving | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Preview also on reconfigure | | ✓ |
| Only on create | | |

---

## Time/duration semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Start time within window | | ✓ |
| Overlaps window | | |
| Fully inside window | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Weekday = day the window starts | | ✓ |
| Weekday = calendar day of start | | |

| Option | Description | Selected |
|--------|-------------|----------|
| HA timezone | | ✓ |
| Feed offset | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Minutes, inclusive, two number fields | | ✓ |
| DurationSelector | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Empty = no restriction (from/to together, from==to invalid) | | ✓ |
| Window only with both times | Same as above | |

---

## Fields & templates

| Option | Description | Selected |
|--------|-------------|----------|
| Lines, only present parts, English labels | | ✓ |
| No labels, comma header | | |
| German labels | | |

| Option | Description | Selected |
|--------|-------------|----------|
| EVT-03 list + {description} | | ✓ |
| Plus {start}/{end}/{duration} | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Empty + clean up dangling separators | | ✓ |
| Empty only | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Templates in advanced step | | ✓ |
| Title template in basic step | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Each category matched separately | | ✓ |
| Joined string | | |

---

## Claude's Discretion

- NFC/casefold strategy, ReDoS hardening, time/weekday selector widgets, separator set, preview rendering and Back/Save mechanics, executor use for preview.

## Deferred Ideas

- Time placeholders in templates.
- True live preview while typing.
