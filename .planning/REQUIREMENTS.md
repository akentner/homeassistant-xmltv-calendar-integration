# Requirements: XMLTV Calendar

**Defined:** 2026-10-12
**Core Value:** Configured filters reliably turn a (possibly large) XMLTV feed into a calendar showing exactly the programmes the user cares about, with channel and start time clearly visible.

## v1 Requirements

### Source

- [x] **SRC-01**: User can add an XMLTV source by HTTP(S) URL as its own config entry
- [x] **SRC-02**: User can add an XMLTV source by local file path (validated against HA allowed paths)
- [x] **SRC-03**: Gzip-compressed sources are read transparently (detected by content, not file extension)
- [x] **SRC-04**: User can set a refresh interval per source
- [ ] **SRC-05**: User can alternatively schedule a source to refresh once daily at a fixed time (e.g. 18:15 for a feed generated at 18:00)
- [x] **SRC-06**: Downloaded source data is cached on disk; an HA restart or entry reload uses the cache and does not re-fetch while the cache is still fresh for the configured schedule
- [ ] **SRC-07**: Remote sources are re-downloaded only when changed (ETag / If-Modified-Since)
- [ ] **SRC-08**: A failed fetch or parse keeps the last good data; calendars keep working
- [x] **SRC-09**: Large feeds (50+ MB) are parsed without blocking the HA event loop and with bounded memory
- [ ] **SRC-10**: User can configure per source that timestamps without offset are local time, and/or apply a time offset correction
- [ ] **SRC-11**: User sees a Repairs issue when a source fails persistently; it clears on success
- [ ] **SRC-12**: User can download diagnostics for a source (URL/credentials redacted; programme/channel/match counts, last success/failure)
- [x] **SRC-13**: Duplicate sources (same normalized URL/path) are rejected during setup

### Filter

- [x] **FLT-01**: User can add multiple calendars to a source (one subentry each), each with its own filters
- [x] **FLT-02**: User can select channels from a list built from the source's channels (empty = all channels)
- [x] **FLT-03**: User can define include regex patterns (OR-combined); a programme matches only if an include pattern matches
- [x] **FLT-04**: User can define exclude regex patterns; matching programmes are removed (match = channel AND include AND NOT exclude)
- [x] **FLT-05**: User can choose which fields include and exclude patterns apply to (title, sub-title, description, category), separately
- [x] **FLT-06**: Matching is case-insensitive by default with a case-sensitive toggle; umlauts match regardless of Unicode normalization
- [x] **FLT-07**: Invalid regex patterns are rejected in the flow with the error shown; empty patterns are ignored
- [x] **FLT-08**: User can filter by minimum and maximum programme duration
- [x] **FLT-09**: User can filter by time window (time-of-day range, may cross midnight) and weekdays
- [x] **FLT-10**: User sees a filter preview in the flow (match count + next ~10 matches with channel and time) before saving
- [x] **FLT-11**: User can edit all filters of an existing calendar (reconfigure) without re-downloading or re-parsing the source

### Events

- [x] **EVT-01**: Each matching programme becomes exactly one calendar event (no merging); exact duplicates (same channel+start+title) are collapsed
- [x] **EVT-02**: Event location is the channel display name
- [x] **EVT-03**: User can configure the event title via placeholder template (`{channel}`, `{title}`, `{subtitle}`, `{episode}`, `{category}`, `{channel_id}`); default `{channel}: {title}`; unknown placeholders rejected in flow
- [x] **EVT-04**: Event description contains sub-title, episode, categories and description by default; user can override it with a description template
- [x] **EVT-05**: Event start/end are correct and timezone-aware for all XMLTV timestamp variants; missing stop times are inferred
- [x] **EVT-06**: Events have stable UIDs across refreshes
- [ ] **EVT-07**: Matches from the past N days (configurable, ≤7) remain visible in the calendar even after the feed drops them
- [ ] **EVT-08**: An HA event is fired when a new matching programme appears in the feed (not on first refresh, not again after restart)

### Automation

- [x] **AUT-01**: Calendar works with calendar triggers (start/end, offsets) and `calendar.get_events`
- [x] **AUT-02**: Calendar state is `on` while a matching programme airs; attributes show the current/next match
- [ ] **AUT-03**: Each calendar has a next-match timestamp sensor (attributes: title, channel, start, end)
- [ ] **AUT-04**: User can trigger a manual refresh (`homeassistant.update_entity`)
- [ ] **AUT-05**: Repo ships a blueprint "notify before a matching programme starts" (`mode: queued`)

### Configuration UX

- [x] **CFG-01**: All setup is possible via UI (config flow for source, subentry flow for calendars); no YAML
- [ ] **CFG-02**: User can edit source settings (refresh, timezone options) via options flow
- [ ] **CFG-03**: User sees a progress indicator while a source is downloaded during setup
- [ ] **CFG-04**: UI is available in English and German

### Distribution

- [x] **DST-01**: Integration installs via HACS (custom repository) with valid `hacs.json` / `manifest.json` and brand icon
- [x] **DST-02**: CI runs hassfest, HACS validation, Ruff and pytest on every push
- [ ] **DST-03**: Tagged releases are published with version matching `manifest.json`
- [ ] **DST-04**: README documents setup, filter examples (regex), automation examples and calendar limitations (15-min trigger window, overlapping events)

## v2 Requirements

### Filter

- **FLT-12**: User can pick categories from a list built from the feed
- **FLT-13**: User can restrict to new/premiere/live programmes (if feed provides tags)
- **FLT-14**: User can choose preferred language for multi-language titles/descriptions

### Events

- **EVT-09**: Episode numbers normalized (`xmltv_ns` → `S01E05`)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Per-channel current/next sensors | Entity explosion; existing EPG integrations cover it |
| Built-in notification system | HA automations + blueprint (AUT-05) cover it |
| Bundled country/source catalogue | Sources die/move; maintenance burden |
| Full schedule as entity attributes | Recorder bloat, 16 KB limit; use `get_events` |
| Merging consecutive/simulcast programmes | User decision: 1 programme = 1 event, exclude regex for noise |
| Jinja title templates | Too slow for thousands of events; `str.format_map` instead |
| Plain-text / mixed match syntax | Regex only + preview |
| Writable calendar | EPG is read-only truth |
| PVR/recorder control, artwork, custom card | Not requested; calendar triggers drive PVR scripts |
| YAML configuration | User decision: UI only |
| Multiple calendar entities per calendar subentry | One filter set = one calendar |
| Use-case-specific logic (e.g. hardcoded F1) | Integration stays generic |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SRC-01 | Phase 1 | Complete |
| SRC-02 | Phase 1 | Complete |
| SRC-03 | Phase 1 | Complete |
| SRC-04 | Phase 1 | Complete |
| SRC-05 | Phase 3 | Pending |
| SRC-06 | Phase 3 | Complete |
| SRC-07 | Phase 3 | Pending |
| SRC-08 | Phase 3 | Pending |
| SRC-09 | Phase 1 | Complete |
| SRC-10 | Phase 3 | Pending |
| SRC-11 | Phase 3 | Pending |
| SRC-12 | Phase 3 | Pending |
| SRC-13 | Phase 1 | Complete |
| FLT-01 | Phase 1 | Complete |
| FLT-02 | Phase 1 | Complete |
| FLT-03 | Phase 1 | Complete |
| FLT-04 | Phase 1 | Complete |
| FLT-05 | Phase 2 | Complete |
| FLT-06 | Phase 2 | Complete |
| FLT-07 | Phase 1 | Complete |
| FLT-08 | Phase 2 | Complete |
| FLT-09 | Phase 2 | Complete |
| FLT-10 | Phase 2 | Complete |
| FLT-11 | Phase 2 | Complete |
| EVT-01 | Phase 1 | Complete |
| EVT-02 | Phase 1 | Complete |
| EVT-03 | Phase 2 | Complete |
| EVT-04 | Phase 2 | Complete |
| EVT-05 | Phase 1 | Complete |
| EVT-06 | Phase 1 | Complete |
| EVT-07 | Phase 4 | Pending |
| EVT-08 | Phase 4 | Pending |
| AUT-01 | Phase 1 | Complete |
| AUT-02 | Phase 1 | Complete |
| AUT-03 | Phase 4 | Pending |
| AUT-04 | Phase 3 | Pending |
| AUT-05 | Phase 4 | Pending |
| CFG-01 | Phase 1 | Complete |
| CFG-02 | Phase 3 | Pending |
| CFG-03 | Phase 3 | Pending |
| CFG-04 | Phase 4 | Pending |
| DST-01 | Phase 1 | Complete |
| DST-02 | Phase 1 | Complete |
| DST-03 | Phase 4 | Pending |
| DST-04 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 45 total
- Mapped to phases: 45
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-12*
*Last updated: 2026-10-12 after roadmap creation (traceability mapped)*
