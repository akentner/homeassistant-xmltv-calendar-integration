# XMLTV Calendar (Home Assistant Integration)

## What This Is

A Home Assistant custom integration (distributed via HACS) that turns XMLTV EPG data into calendar entities. Each configured instance applies its own filters (channels, include/exclude regex on title and description) and exposes the matching broadcasts as a single `calendar.*` entity — e.g. "which channel shows Formula 1 next, and when". Built for the user's own HA setup but generic enough for any "watch for specific programmes" use case.

## Core Value

Configured filters reliably turn a (possibly large) XMLTV feed into a calendar showing exactly the programmes the user cares about, with channel and start time clearly visible.

## Requirements

### Validated

- ✓ Multiple XMLTV sources can be configured (one config entry per source) — Phase 1
- ✓ Each source can have multiple calendars (one config subentry per calendar), each with its own filters and one calendar entity — Phase 1
- ✓ XMLTV source can be an HTTP(S) URL or a local file; gzip-compressed (`.xml.gz`) sources are supported — Phase 1
- ✓ All calendars of a source share one download/parse (XMLTV files can be 50+ MB) — Phase 1
- ✓ Filter by channel (channel list selectable from channels found in the XMLTV data) — Phase 1
- ✓ Every matching XMLTV programme becomes one calendar event (no merging) — Phase 1
- ✓ Event location = channel name — Phase 1
- ✓ Calendar works with HA calendar triggers (automations) and the calendar dashboard/card — Phase 1
- ✓ Filter by include regex and exclude regex on title, sub-title, description and category (field-scoped, Unicode-safe, case toggle, ReDoS-guarded) plus duration, time-window and weekday filters — Phase 2
- ✓ Event title is configurable via sandboxed Jinja template (e.g. `{{ channel }}: {{ title }}`); default includes the channel — Phase 2, reworked in Phase 5
- ✓ Event description carries programme details (subtitle, description, category, episode where available), overridable via sandboxed Jinja description template — Phase 2, reworked in Phase 5
- ✓ Live filter preview in the flow (match count + next matches) before saving; calendars editable in place without re-downloading the source — Phase 2
- ✓ Refresh schedule configurable and editable per source: interval or daily at a fixed time — Phase 3
- ✓ Complete setup and later editing of all settings via Config Flow, Subentry Flow and Options Flow (no YAML), with a progress indicator during the setup download — Phase 3
- ✓ Sources are resilient: disk cache across restarts, conditional requests (ETag / If-Modified-Since), last good data kept on failure, backoff, Repairs issue after 24 h of failures, diagnostics, timezone options, manual refresh via `update_entity` — Phase 3
- ✓ Automation extras: next-match sensor, new-match event with payload, recent past matches, ready-made blueprint — Phase 4
- ✓ Distributed as HACS repository (hacs.json, tagged releases v1.0.0 and v1.0.1, CI with hassfest + HACS validation), bilingual README — Phase 1 and Phase 4, released v1.0.0

### Active

(None — define the next milestone's requirements with `/gsd-new-milestone`)

### Out of Scope

- Merging consecutive/simulcast entries into one event — user prefers 1 programme = 1 event; unwanted entries handled via exclude regex
- Use-case-specific logic (e.g. hardcoded Formula 1 handling) — integration must stay generic
- Recorder/PVR control (Enigma2, TVHeadend recording) — not requested; can be done via automations on calendar triggers
- YAML configuration — UI-only (Config + Options Flow) by user choice
- Multiple calendar entities per calendar subentry (e.g. per channel) — one calendar per filter set

## Context

- Part of the user's Home Assistant ecosystem monorepo (`~/Projects/`), alongside phone-logger, kroki integration etc. — independent Git repo.
- Target HA host: `ha-host`.
- Shipped v1.0.0 (2026-10-26) and v1.0.1 (2026-10-30): about 6.7k lines of integration code and 15.5k lines of tests, no runtime requirements (stdlib parsing, `jinja2` from HA core). Development and tests use fixture files; a real-feed acceptance test stays opt-in via `XMLTV_REAL_FEED`.
- Known and accepted: the Jinja regex-check bypass via `map`/`select`/`reject` naming the filter as text (T-05-03) and exponential growth through `set` and `~` (T-05-12), both admin-only and documented in the README Limits. Phase 5 review findings WR-01, WR-04 and IN-01..IN-04 are open (`05-REVIEW-DISPOSITION.md`).
- Real sources may be TVHeadend, iptv-org/epg, epg.best etc.
- XMLTV format: `<channel id>` with `<display-name>`, `<programme start stop channel>` with `<title>`, `<sub-title>`, `<desc>`, `<category>`, `<episode-num>`; timestamps like `20261012203000 +0200`.
- Motivating example: "Which TV channel broadcasts Formula 1 next, and when?" — visible in the calendar and usable as automation trigger.

## Constraints

- **Tech stack**: Python, Home Assistant custom component; `uv` for deps, Ruff (120-char lines) — matches monorepo conventions
- **Config**: Config Flow + Options Flow only — user preference, consistent with other HA components
- **Performance**: Large XMLTV files (tens of MB) must not block the HA event loop — parse in executor, share across instances
- **Distribution**: HACS-compatible repository structure and validation
- **Language**: Code, comments, commits in English

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Source = config entry, calendar = config subentry | HA-native sharing of one download/parse per source (coordinator in runtime_data), no custom ref-counting; chosen after research (2026-10-12) | ✓ Good — Phase 1 (UAT: independent per-source refresh, multiple calendars per source) |
| One calendar entity per subentry | Simple mental model: one filter set = one calendar | ✓ Good — Phase 1 (entity_id stable across delete/re-add) |
| 1 programme = 1 event, no merging | Predictable; exclude regex handles noise | ✓ Good — Phase 1 (exact duplicates collapsed, stable UIDs) |
| Templated event title, channel as location | Channel must be visible at a glance; flexible formatting | ✓ Good — Phase 2 shipped restricted placeholder templates, validated in the flow; Phase 5 supersedes them with sandboxed Jinja templates |
| Sandboxed Jinja2 templates for event titles and descriptions | Conditions, text filters and local time are needed (for example strip a redundant Formel 1 prefix, use the first description line); jinja2 ships with HA core, the sandbox is used directly (not the HA Template class), templates are precompiled and only the requested window is rendered, so the Phase 2 speed objection no longer applies; hard break for stored single-brace templates, no migration | Pending, Phase 5 |
| Preview renders feed text literally | Feed text is untrusted; HA renders the flow description as Markdown (marked GFM) | ✓ Good — Phase 2 (HTML/Markdown/autolink/tilde escaping, whitespace collapsed; verified live in ha-dev) |
| German UI translation (de.json) alongside en.json | User runs HA in German; parity tests keep keys/placeholders in sync | ✓ Good — quick 261015-su3 |
| UI-only configuration | User preference, editable via Options Flow | ✓ Good — Phase 3 (source options flow reloads once from cache; no YAML anywhere) |
| Stale-while-revalidate disk cache per URL source | Restarts and reloads must not re-download a large feed; calendars show cached data at once | ✓ Good — Phase 3 (UAT: one download per setup, none on restart or options save) |
| Unchanged data counts as success only while it still holds a current programme | A stalled provider answering 304 must become visible instead of silently emptying the calendar | ✓ Good — Phase 3 (WR-01 fix; 3 plan truths accepted by override in 03-VERIFICATION.md) |
| Every non-cancellation exception on a refresh is a recorded, backed-off failure | No exception may turn into a faster retry against the feed host | ✓ Good — Phase 3 (residuals WR-05 setup-retry cadence and IN-09 accepted; WR-06 logging deferred) |
| HACS distribution | Standard install/update path | ✓ Good — Phase 1 (HACS accepts custom repo, hassfest/HACS CI green) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-30 after v1.0.1 milestone*
