# XMLTV Calendar (Home Assistant Integration)

## What This Is

A Home Assistant custom integration (distributed via HACS) that turns XMLTV EPG data into calendar entities. Each configured instance applies its own filters (channels, include/exclude regex on title and description) and exposes the matching broadcasts as a single `calendar.*` entity — e.g. "which channel shows Formula 1 next, and when". Built for the user's own HA setup but generic enough for any "watch for specific programmes" use case.

## Core Value

Configured filters reliably turn a (possibly large) XMLTV feed into a calendar showing exactly the programmes the user cares about, with channel and start time clearly visible.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Multiple independent instances (config entries) can be set up, each producing one calendar entity
- [ ] XMLTV source can be an HTTP(S) URL or a local file; gzip-compressed (`.xml.gz`) sources are supported
- [ ] Instances sharing the same source share one download/parse (shared data layer, XMLTV files can be 50+ MB)
- [ ] Refresh interval is configurable per source
- [ ] Filter by channel (channel list selectable from channels found in the XMLTV data)
- [ ] Filter by include regex and exclude regex on title and description (flexible enough to precisely identify specific shows)
- [ ] Every matching XMLTV programme becomes one calendar event (no merging)
- [ ] Event location = channel name
- [ ] Event title is configurable via template (e.g. `{channel}: {title}`); default includes the channel
- [ ] Event description carries programme details (subtitle, description, category, episode where available)
- [ ] Complete setup and later editing of all settings via Config Flow + Options Flow (no YAML)
- [ ] Calendar works with HA calendar triggers (automations) and the calendar dashboard/card
- [ ] Distributed as HACS repository (hacs.json, releases, CI with hassfest + HACS validation)

### Out of Scope

- Merging consecutive/simulcast entries into one event — user prefers 1 programme = 1 event; unwanted entries handled via exclude regex
- Use-case-specific logic (e.g. hardcoded Formula 1 handling) — integration must stay generic
- Recorder/PVR control (Enigma2, TVHeadend recording) — not requested; can be done via automations on calendar triggers
- YAML configuration — UI-only (Config + Options Flow) by user choice
- Multiple calendar entities per instance (e.g. per channel) — one calendar per config entry

## Context

- Part of the user's Home Assistant ecosystem monorepo (`~/Projects/`), alongside phone-logger, kroki integration etc. — independent Git repo.
- Target HA host: `ha-host`.
- No concrete XMLTV source yet — development and tests use fixture files. Real sources later may be TVHeadend, iptv-org/epg, epg.best etc.
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
| One calendar entity per config entry | Simple mental model: one filter set = one calendar | — Pending |
| Shared download/parse per source | Avoid repeated download/parse of large XMLTV files | — Pending |
| 1 programme = 1 event, no merging | Predictable; exclude regex handles noise | — Pending |
| Templated event title, channel as location | Channel must be visible at a glance; flexible formatting | — Pending |
| UI-only configuration | User preference, editable via Options Flow | — Pending |
| HACS distribution | Standard install/update path | — Pending |

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
*Last updated: 2026-10-12 after initialization*
