# Roadmap: XMLTV Calendar

## Overview

Four vertical slices, each usable on `ha-host` when it completes. Phase 1 is the walking skeleton. It builds a pure, HA-free XMLTV library test-first (streaming parser, timestamp handling, filter engine, rendering), wires it through fetcher, coordinator, calendar entity and minimal config + subentry flows, and runs CI from the first push. The result is one source with one or more filtered calendars working end to end. Phase 2 sharpens the filters (field selection, case/Unicode handling, duration, time window) and adds title/description templates, a live preview and instant reconfigure through the diffing update listener. Phase 3 makes sources cheap and resilient: disk cache, conditional GET, daily schedule, timezone options, options flow, setup progress, last-good data, Repairs and diagnostics. Phase 4 adds automation extras (next-match sensor, new-match event, past retention, blueprint) and ships a documented, bilingual, tagged HACS release.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: First Filtered Calendar** - One source with channel + regex filtered calendars showing correct events in HA; pure library, scaffold and CI first (completed 2026-10-15)
- [x] **Phase 2: Precise Filters & Preview** - Field-scoped Unicode-safe regex, duration and time-window filters, title/description templates, live preview, instant reconfigure (completed 2026-10-15)
- [ ] **Phase 3: Resilient Sources** - Disk cache, conditional GET, daily schedule, timezone options, options flow, setup progress, last-good data, Repairs, diagnostics
- [ ] **Phase 4: Automation Extras & Release** - Next-match sensor, new-match event, past-match retention, blueprint, German translation, README, tagged HACS releases

## Phase Details

### Phase 1: First Filtered Calendar

**Goal:** As a Home Assistant user, I want to add an XMLTV source (URL or local file) in the HA UI and attach calendars filtered by channel and include/exclude regex, so that I see exactly the matching programmes as correctly timed calendar events that drive calendar triggers.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: SRC-01, SRC-02, SRC-03, SRC-04, SRC-09, SRC-13, FLT-01, FLT-02, FLT-03, FLT-04, FLT-07, EVT-01, EVT-02, EVT-05, EVT-06, AUT-01, AUT-02, CFG-01, DST-01, DST-02
**Success Criteria** (what must be TRUE):
  1. On `ha-host` the user adds a source entirely through the UI: an HTTP(S) URL or a file under an allowed path (e.g. `/media`), plain or gzip-compressed regardless of file extension, with a refresh interval. The user then adds one or more calendars (subentries) to it, each with its own filters. Adding the same source (normalized URL/path) a second time is rejected.
  2. A calendar filtered by channels picked from the feed's channel list (empty = all) plus include/exclude regex shows exactly the programmes matching channel AND include AND NOT exclude. Each programme becomes one event, exact duplicates are collapsed, location is the channel display name and the default title is `{channel}: {title}`. An invalid regex is rejected in the flow with the error shown, and empty patterns are ignored.
  3. Event start/end are timezone-aware and correct for every XMLTV timestamp variant (full, shortened, with and without offset). Missing stop times are inferred, event UIDs stay the same across refreshes, and a single malformed programme never breaks the calendar.
  4. A calendar trigger automation (start and end, with offset) fires for a matching programme. `calendar.get_events` returns all events overlapping the queried range. The calendar is `on` while a match airs, and its attributes show the current/next match.
  5. A 50+ MB fixture feed refreshes without blocking the HA event loop and stays within a bounded memory budget (benchmark). Every push runs hassfest, HACS validation, Ruff and pytest green, and HACS accepts the repo as a custom repository (valid `hacs.json`, `manifest.json`, brand icon).

**Plans**: 11/11 plans complete

Plans:
**Wave 1**
- [x] 01-01-PLAN.md — Walking skeleton: package gate, pinned dev tooling, then tracer URL source → one calendar → events (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-02-PLAN.md — TDD: timestamp variants, stop inference, dedup, stable UIDs (wave 2)
- [x] 01-03-PLAN.md — TDD: filter engine (channel ∪ channel regex, include/exclude, validation API) (wave 2)
- [x] 01-04-PLAN.md — TDD: calendar window reads (bisect index, end-inclusive, capped), triggers and live state (wave 2)
- [x] 01-05-PLAN.md — TDD: robust ingestion (gzip by content, size caps, typed failures, host-only logs) (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 01-06-PLAN.md — HACS metadata, brand, CI/Validate workflows, 60 MB benchmark (wave 3)
- [x] 01-07-PLAN.md — Local-file sources, flow validation, duplicate protection (unique_id decision gate) (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 01-08-PLAN.md — Full "Add calendar" form with pattern validation; multiple calendars per source (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 01-09-PLAN.md — ha-dev deployment, real German feed excerpt (decision gate), UAT walkthrough (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*
- [x] 01-10-PLAN.md — Publish to GitHub (user push), CI/Validate green, HACS custom-repo check (wave 6)

**Gap closure** *(after verification: gaps_found)*
- [x] 01-11-PLAN.md — TDD gap closure CR-01/WR-06: malformed programme timestamps never break the calendar (timeparse range checks, per-programme parser guard, calendar except widening)

**UI hint**: yes
**Notes**: Build the pure `xmltv/` library (parser, models, filter, render; no `homeassistant` imports) test-first, before the HA layer. The subentry flow reads channels from the loaded coordinator (abort `source_not_loaded` otherwise) and must handle subentries added before the platform has loaded. Register exactly one update listener on the source entry; reload-on-change is acceptable here, and Phase 2 makes it diffing. Set `unique_id` from the normalized source now so it never needs a migration. Decide `iot_class`. Research flags: `cache_path`/coordinator APIs (light check), `SelectSelector` with thousands of channels (may need a fallback).

### Phase 2: Precise Filters & Preview

**Goal:** User can pinpoint specific shows with field-scoped, Unicode-safe regex plus duration and time-window filters, shape event title and description via templates, check the result in a live preview before saving, and retune any calendar instantly without touching the source.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: FLT-05, FLT-06, FLT-08, FLT-09, FLT-10, FLT-11, EVT-03, EVT-04
**Success Criteria** (what must be TRUE):
  1. User chooses separately which fields (title, sub-title, description, category) the include and the exclude patterns apply to. Matching is case-insensitive by default with a case-sensitive toggle, and a pattern containing umlauts matches whether the feed uses composed or decomposed Unicode.
  2. User can restrict a calendar by minimum/maximum programme duration, by a time-of-day window (including windows that cross midnight, e.g. 22:00-02:00) and by weekdays. Only programmes meeting every configured constraint appear.
  3. Before saving, the calendar flow shows the match count and the next ~10 matches, with channel and start time, for the entered filters.
  4. User sets the event title via a placeholder template (`{channel}`, `{title}`, `{subtitle}`, `{episode}`, `{category}`, `{channel_id}`) and can optionally set a description template. Unknown placeholders are rejected in the flow. Without a description template, events show sub-title, episode, categories and description.
  5. User reconfigures all filters and templates of an existing calendar and sees the updated events without a re-download or re-parse, and without reloading the source's other calendars.

**Plans**: 10/10 plans complete

Plans:
**Wave 1**
- [x] 02-01-PLAN.md — In-place calendar updates via the diffing listener (no refetch/reparse/reload), device rename, IN-14 clamp (wave 1)
- [x] 02-02-PLAN.md — TDD: NFC-safe, field-scoped, case-aware matching; stored-settings contract (key-name decision gate) (wave 1)
- [x] 02-03-PLAN.md — Preview step (count + next 10 matches), basic -> preview -> save/back flow, test migration (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 02-04-PLAN.md — TDD: duration, midnight-crossing time window, weekdays in HA time zone; nested-repetition guard (wave 2)
- [x] 02-05-PLAN.md — Edit a calendar from the UI (reconfigure + async_update_and_abort), full-key saves (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 02-06-PLAN.md — TDD: title/description templates, default description, preview titles via templates (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 02-07-PLAN.md — Advanced options step (fields, case, window, weekdays, durations, templates) with validation and translations (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 02-08-PLAN.md — Edit-flow D-03 checkbox pre-check, Back with advanced values, form pattern safety, placeholder audit, UAT walkthrough (wave 5)

**Gap closure** *(after verification: gaps_found)*
- [x] 02-09-PLAN.md — TDD gap closure CR-01: every re.compile failure (re.error, OverflowError, RecursionError) is contained in the calendar entity and the calendar form (02-01 truth 6, FLT-07)

**Gap closure** *(after UAT: G-02-2)*
- [x] 02-10-PLAN.md — TDD gap closure G-02-2 + IN-04: escape_markdown neutralises GFM autolinks (scheme://, www., e-mail) and escapes '~', so feed text renders literally in the preview (FLT-10, T-02-05)

**UI hint**: yes
**Notes**: Introduce the single diffing update listener: subentry add/edit/remove updates entities in place, and only changes to source data/options trigger a reload. Subentry reconfigure ends via `async_update_and_abort`. Rendering uses a restricted `str.format_map` (no Jinja, no `.`/`[` in fields, missing values become empty). Normalize text (NFC) before matching, and validate patterns with ReDoS in mind. Research flags: subentry reconfigure/helper APIs, preview rendering inside a flow step.

### Phase 3: Resilient Sources

**Goal:** Sources keep every calendar populated at minimal network and CPU cost: cached across restarts, refreshed on the user's schedule and only when changed, tolerant of failures and timezone quirks, editable later, and visible to the user when something goes wrong.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: SRC-05, SRC-06, SRC-07, SRC-08, SRC-10, SRC-11, SRC-12, CFG-02, CFG-03, AUT-04
**Success Criteria** (what must be TRUE):
  1. During source setup the user sees a progress indicator while the feed downloads. Later the user can switch between a refresh interval and a once-daily fixed time (e.g. 18:15) and edit timezone options in the source's options flow. Saving source options reloads that source, while calendar edits still do not.
  2. After an HA restart or entry reload, calendars are filled from the on-disk cache without a download while the cache is still fresh for the configured schedule. An unchanged remote feed (ETag / If-Modified-Since) is neither re-downloaded nor re-parsed. `homeassistant.update_entity` triggers an immediate refresh.
  3. User can declare per source that timestamps without offset are local time and/or apply an offset correction, and event times shift accordingly.
  4. When a fetch or parse fails, calendars keep showing the last good data. A source that keeps failing raises a Repairs issue, which clears automatically after the next successful refresh.
  5. User downloads diagnostics for a source showing programme/channel/match counts and last success/failure, with URL and credentials redacted.

**Plans**: 10/10 plans executed

Plans:
**Wave 1**
- [x] 03-01-PLAN.md — TDD: refresh schedule engine (interval / daily-at, DST, freshness and backoff maths), stored source-options contract, clock-independent tests (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 03-02-PLAN.md — Disk cache: restarts and reloads reuse the feed; a stale cache is shown and refreshed in the background (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 03-03-PLAN.md — Conditional GET (ETag / If-Modified-Since), manual refresh via update_entity, unchanged local files not re-parsed (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 03-04-PLAN.md — Failures keep last good data, capped backoff, Repairs issue after 24 h of failures, empty feed counts as failure (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 03-05-PLAN.md — TDD: timezone options (offset-less timestamps as local time, offset correction), option changes re-parse the cache (wave 5)
- [x] 03-06-PLAN.md — Setup flow: schedule and timezone fields, download progress step, cache seeding (wave 5)
- [x] 03-07-PLAN.md — Diagnostics with redacted URL/path, health, cache metadata and counts (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*
- [x] 03-08-PLAN.md — Options flow for schedule and timezone settings, phase gate and UAT walkthrough (wave 6)

**Gap closure** *(after verification: gaps_found)*
- [x] 03-09-PLAN.md — TDD gap closure CR-01/CR-02: one request per daily slot when HA's timer fires early (refresh_base), every unexpected exception recorded, backed off and reported as UpdateFailed (SRC-05, SRC-08, SRC-11) (wave 1)
- [x] 03-10-PLAN.md — TDD gap closure WR-02/WR-03: setup download recorded as last success for diagnostics and Repairs; test_identity.py frozen and asserting LOADED entries (SRC-12, CFG-03) (wave 1)

**Notes**: Use a plain `OptionsFlow` only, never `OptionsFlowWithReload` (it conflicts with the update listener and raises an error from 2026.12). Source option changes go through the Phase 2 diffing listener. Store the raw-file cache in `hass.config.cache_path`. Research flags: `async_show_progress`, Repairs issue lifecycle.

### Phase 4: Automation Extras & Release

**Goal:** User can automate around matches beyond plain calendar triggers (next-match sensor, new-match event, recent past matches, ready-made blueprint) and install a documented, bilingual, tagged release via HACS.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: AUT-03, AUT-05, EVT-07, EVT-08, CFG-04, DST-03, DST-04
**Success Criteria** (what must be TRUE):
  1. Each calendar has a next-match timestamp sensor with title, channel, start and end attributes, updated as matches pass or the feed changes.
  2. An HA event fires when a new matching programme appears in the feed, but not on the first refresh and not again after a restart. Matches from the past N days (configurable, up to 7) stay visible in the calendar after the feed drops them, also across restarts.
  3. User imports the shipped blueprint "notify before a matching programme starts" (`mode: queued`) and gets one notification per match, including overlapping matches.
  4. Every config, subentry and options flow step, error and abort reason is shown in German when HA runs in German, and in English otherwise.
  5. Pushing a version tag publishes a GitHub release whose version matches `manifest.json`, and HACS offers it for install/update. The README documents setup, regex filter examples, automation examples and calendar limitations (15-min trigger window, overlapping events).

**Plans**: TBD
**Notes**: EVT-07 and EVT-08 share one persisted match store (HA `Store`) holding the seen-set and retained past matches. Copy the release workflow (tag == manifest version) from mqtt-actions.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. First Filtered Calendar | 11/11 | Complete    | 2026-10-15 |
| 2. Precise Filters & Preview | 10/10 | Complete    | 2026-10-15 |
| 3. Resilient Sources | 10/10 | In Progress | - |
| 4. Automation Extras & Release | 0/TBD | Not started | - |
