# Feature Research

**Domain:** Home Assistant custom integration: XMLTV EPG feed turned into filtered `calendar.*` entities (a "watch for specific programmes" calendar)
**Researched:** 2026-10-12
**Confidence:** MEDIUM overall. HA calendar semantics and the XMLTV DTD come from primary sources (official HA docs and the raw `xmltv.dtd`). The competitor landscape comes from the READMEs of each competitor repo. UX judgments such as "users expect X" are inferred from those projects plus sparse forum threads, so they are LOW–MEDIUM.

---

## Landscape in One Paragraph

No existing HA integration exposes XMLTV as filtered calendar entities. Every current EPG integration models the guide as **per-channel sensors** (current / next / prime-time programme):

- `shadow578/homeassistant_xmltv-epg` and its fork `domodom30/ha-xmltv-epg`
- `janfajessen/What's On TV`
- `yohaybn/HomeAssistant-EPG`
- `iAlias/HomeAssistantTVGuideEPG`
- `cyclope205/programme-tnt-fr`
- `criticallimit/TV-Guide` (add-on)

The "notify me when show X airs" use case is handled in ad-hoc ways:

- keyword watches with their own notify plumbing (What's On TV, TV-Guide add-on)
- a favourite-title `binary_sensor` per title (iAlias)
- a regex search service that returns a response (yohaybn)

On the calendar side, `ics_calendar` (franc6) and core `caldav` (`custom_calendars` with a `search` regex) already show that filtered calendars are an established HA pattern. Neither reads EPG data.

**The calendar approach is the differentiator.** HA calendar triggers with `offset`, the calendar card and `calendar.get_events` give reminders, dashboards and "next airing" lookups at no extra cost, with no entity explosion and no recorder bloat.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Missing any of these makes the integration feel broken or amateurish next to the existing EPG integrations and `ics_calendar`.

#### A. Source handling

| ID | Feature | Why Expected | Complexity | Notes |
|----|---------|--------------|------------|-------|
| TS-S1 | HTTP(S) URL source | Every competitor supports it; most real feeds (iptv-org/epg, epgshare01, open-epg, TVHeadend `/xmltv`) are URLs | LOW | Use HA's shared aiohttp session. Set a sane timeout, since 50+ MB downloads take a while. |
| TS-S2 | Local file source | Needed for TVHeadend / WebGrab+Plus / `tv_grab_*` output dropped into `/config` or `/media` | LOW | Validate the path with `hass.config.is_allowed_path()`. Otherwise users hit "path not allowed" confusion. |
| TS-S3 | gzip support (`.xml.gz`) | Almost all large public feeds ship gzipped. domodom30 also does `.xz`/`.zip`. | LOW | **Detect by magic bytes (`1f 8b`), not by extension.** Some servers serve gzip under `.xml`, or set `Content-Encoding: gzip`, which aiohttp already decodes. |
| TS-S4 | Configurable refresh interval | All competitors expose it (1–24 h typical). EPG data changes at most a few times a day. | LOW | Default 6–12 h. Minimum about 1 h to protect free EPG hosts. With shared sources, see dependency note D3. |
| TS-S5 | Keep last good data on fetch/parse failure | A failed download must not empty the calendar and break automations | LOW | Use `DataUpdateCoordinator` semantics: keep the old data, mark the coordinator failed, log once. |
| TS-S6 | Non-blocking parse of large feeds | 50+ MB XML can take seconds. Blocking the loop triggers HA warnings and kills UX. | MEDIUM | Parse in the executor with a streaming parser (`iterparse` plus element clearing). domodom30 explicitly advertises "memory-efficient streaming parser", which marks it as an expectation. |
| TS-S7 | Diagnostics plus a "last update" indicator | domodom30 ships a diagnostics download (URL redacted) and a Last Update diagnostic sensor. Users need to know whether the feed is stale. | LOW | Diagnostics: source (redacted), programme and channel counts, last success/failure, match count. A diagnostic sensor is optional (see DF-A2). |

#### B. Filtering (the core value)

| ID | Feature | Why Expected | Complexity | Notes |
|----|---------|--------------|------------|-------|
| TS-F1 | Channel filter via picker populated from the feed | Every competitor offers "select channels from the dynamically fetched list" | MEDIUM | Needs the feed downloaded during config flow (see D1). Show `display-name (id)`. An empty selection means all channels. |
| TS-F2 | Include regex | Core of the project. ics_calendar, caldav `search` and yohaybn's search service all use regex. | LOW | One pattern per line, OR-combined. Compile once per filter set, not per programme. |
| TS-F3 | Exclude regex | Needed to remove noise ("Highlights", "Wiederholung", "Vorschau", news segments) under the 1 programme = 1 event rule | LOW | **Semantics: match = include AND NOT exclude.** Do not copy ics_calendar's "exclude first, include re-admits, exclude `/.*/` to whitelist" model, which confuses users. |
| TS-F4 | Case-insensitive matching by default | ics_calendar plain strings and yohaybn search are case-insensitive. XMLTV casing is inconsistent across providers. | LOW | Default `re.IGNORECASE`. Expose a case-sensitive toggle (cheap). |
| TS-F5 | Regex validation in the flow | An invalid regex saved into options means a silently empty calendar | LOW | `re.compile` in the flow step. Return a field error (`invalid_regex`) with the compiler message in `description_placeholders`. |
| TS-F6 | Choose which fields include/exclude apply to | The F1 case needs **title-only** include (descriptions of news shows mention "Formel 1"), while exclude often needs description ("Wiederholung vom ..."). | LOW | Two multi-selects, one for include fields and one for exclude fields. Options: title, sub-title, description, category. Defaults: include = title + sub-title; exclude = title + sub-title + description. |

#### C. Event formatting

| ID | Feature | Why Expected | Complexity | Notes |
|----|---------|--------------|------------|-------|
| TS-E1 | Event location = channel display name | PROJECT requirement. Surfaces in `trigger.calendar_event.location` and the calendar card. | LOW | Use the first `<display-name>` (the DTD says "earlier = more canonical"). Fall back to the channel id. |
| TS-E2 | Title template with placeholders, default including the channel | Channel must be visible at a glance. ics_calendar's `prefix` shows users want title shaping. | LOW | Python `str.format_map` with a safe dict. **Not Jinja** (see AF-6). Placeholders: `{channel}`, `{title}`, `{subtitle}`, `{episode}`, `{category}`, `{channel_id}`. Default `{channel}: {title}`. Validate unknown placeholders in the flow. |
| TS-E3 | Description carries programme details | PROJECT requirement. Notifications use `trigger.calendar_event.description`. | LOW | Fixed layout: sub-title, episode, categories, description, plus flags (new / premiere / repeat) when present. |
| TS-E4 | Correct start/end with timezones | Calendar triggers and the card depend on it | MEDIUM | XMLTV `YYYYMMDDhhmmss ±HHMM`; the DTD says **no offset = UTC** and **truncated timestamps are legal**. `stop` is **optional** (`#IMPLIED`). Infer it from the next programme on the same channel, else use a default duration. HA requires tz-aware datetimes with end > start. |
| TS-E5 | Stable event UID | Needed for the calendar card / WebSocket subscription diffing and deterministic tests | LOW | `uid = sha1(channel_id + start + title)`. |
| TS-E6 | Duplicate-entry collapse (identical channel+start+title) | iptv-org-style merged feeds sometimes repeat the exact same programme | LOW | This collapses exact duplicates (data errors), not simulcasts on different channels. It is consistent with the "no merging" decision. |

#### D. Config UX

| ID | Feature | Why Expected | Complexity | Notes |
|----|---------|--------------|------------|-------|
| TS-C1 | Full setup via Config Flow | All modern competitors and ics_calendar are UI-only. PROJECT constraint. | MEDIUM | Steps: source → (download with progress) → channels → filters + template. |
| TS-C2 | All settings editable via Options Flow | domodom30 groups options into sections (channels / update / programs). Users expect to tweak filters without deleting the entry. | MEDIUM | Reuse the same step schemas as the config flow. Reload the entry on options change. The source URL could move to a **reconfigure** flow (`async_step_reconfigure`) so options stay filter-focused. |
| TS-C3 | Progress indicator while the feed downloads during setup | domodom30: "a progress indicator is shown; this can take a while for large guides" | MEDIUM | `async_show_progress` / `async_show_progress_done`. Without it the flow appears hung or hits the frontend timeout on big feeds. |
| TS-C4 | Multiple independent entries | What's On TV, iAlias and ics_calendar all support multiple entries. PROJECT requirement. | LOW (UI) / MEDIUM (shared source, D3) | One entry = one calendar. |
| TS-C5 | English + German translations | User and target audience are German. domodom30 ships EN/FR, What's On TV ships many languages. | LOW | `strings.json` plus `translations/de.json`. Include selector option labels and error texts. |

#### E. Automation integration

| ID | Feature | Why Expected | Complexity | Notes |
|----|---------|--------------|------------|-------|
| TS-A1 | Works with calendar triggers (start/end, offset) | This is the entire point versus sensor-based competitors | LOW | Comes free from a correct `CalendarEntity`: an `event` property returning the current or next event, and an `async_get_events(start, end)` that returns sorted tz-aware events. |
| TS-A2 | Works with `calendar.get_events` and the calendar dashboard | Users build "next 5 F1 sessions" lists from `get_events` | LOW | Same implementation. Filter by overlap (`event.end > start and event.start < end`). |
| TS-A3 | Calendar entity state/attributes reflect the current or next match | Calendar `on` while a match is airing gives a free "is my show on now" binary signal (replaces iAlias's favourite binary sensors) | LOW | When several matches overlap (simulcast on two channels), HA shows only one in attributes. Document it and point users to triggers / `get_events`. |
| TS-A4 | Manual refresh | yohaybn ships `epg.update_channels`. Users want "pull now" after changing the source. | LOW | Support `homeassistant.update_entity` on the calendar to trigger a coordinator refresh. An extra `xmltv_calendar.refresh` action is optional. |

### Differentiators (Competitive Advantage)

These align with the Core Value: "configured filters reliably turn a large feed into exactly the programmes I care about".

| ID | Feature | Value Proposition | Complexity | Notes |
|----|---------|-------------------|------------|-------|
| DF-1 | **Filter preview / test step in Config and Options Flow** | No competitor has it. Regex filters are the hardest part of setup; showing "23 matches, next: Sky Sport F1 – Sun 14:00 – Formel 1: Großer Preis von …" before saving turns trial-and-error into one loop. **Strongest UX differentiator.** | MEDIUM | Extra step after filters. Run the matcher on the cached parsed feed (in the executor). Render count plus the first N (about 10) via `description_placeholders` as markdown. Offer "Back / Save". Requires D1 (parsed feed available in the flow). |
| DF-2 | Category filter (regex on `<category>` or multi-select from categories in the feed) | Precise targeting ("Sport", "Motorsport", "Film") without title regex gymnastics. cyclope205 offers a genre filter in its card, so users know the concept. | LOW (regex) / MEDIUM (picker) | XMLTV categories are free-text, language-specific and inconsistent across providers ("Sport" vs "Sports" vs "Motorsport"). **Recommendation: v1 = add `category` as a matchable field in TS-F6; v1.x = optional category picker built from distinct values in the feed.** |
| DF-3 | Time-window filter (time-of-day range, weekdays) | "Only evening films", "only weekend races". Cuts noise from overnight repeats without regex. | LOW | Matched against the local start time. Window can cross midnight (22:00–02:00). |
| DF-4 | Minimum / maximum duration filter | Removes 5-minute trailers, "News"-style teasers and "Vorschau" fillers that match a title regex. Directly useful for the F1 example. | LOW | Compute after stop inference (TS-E4). |
| DF-5 | "New / premiere / live only" flag filters | XMLTV has `<new/>`, `<premiere>`, `<previously-shown>`, `<last-chance>`. "Skip repeats" is a top wish for "watch X" use cases. | LOW | **Coverage varies widely by feed.** Many feeds omit these tags, so present them as "only if the feed provides them". Treat as a v1.x option. |
| DF-6 | Next-match sensor (timestamp `device_class`, attributes: title, channel, start, end) | The calendar entity's attributes already show the current/next event, but a timestamp sensor gives relative time in the UI ("in 2 days"), easy template use and history graphs | LOW | One sensor per entry, so no entity explosion. Optional extra: "matches in the next N days" count sensor. Keep attributes small (see AF-4). |
| DF-7 | HA event on newly appeared matches (`xmltv_calendar_new_match`) | What's On TV's main pitch is "notify when a matching programme **appears** in the guide", which is different from "notify when it starts". Lets users learn about an F1 broadcast days ahead. | MEDIUM | Diff the match-UID set between refreshes. **The seen-set must be persisted (HA `Store`)**, or every restart re-fires all matches. Suppress on the first refresh after setup. |
| DF-8 | Conditional GET (ETag / If-Modified-Since) | Avoids re-downloading and re-parsing 50 MB when the feed has not changed. Polite to free EPG hosts. | LOW | Skip the parse on 304. Pairs with the shared source layer. |
| DF-9 | Persist the last parsed/filtered result across restarts | The calendar is populated immediately after an HA restart, without waiting for or hammering the feed. Automations that fire shortly after a restart don't miss events. | MEDIUM | Store only the **filtered** events per entry (small), not the whole feed. |
| DF-10 | Description template (in addition to the title template) | Power users want e.g. only `{subtitle} – {episode}` in notifications | LOW | Same `format_map` engine as TS-E2. The default stays the fixed layout of TS-E3. |
| DF-11 | Episode normalisation (`xmltv_ns` "0.4." → `S01E05`) | A consistent `{episode}` placeholder across feeds. The DTD's `xmltv_ns` is zero-based and easy to get wrong. | LOW | Prefer `onscreen` when present. Fall back to converted `xmltv_ns`. |
| DF-12 | Preferred language for multi-lang `<title>`/`<desc>` | Feeds may carry `lang="de"` and `lang="en"` variants | LOW | Default: HA language, then the first element. v1.x. |
| DF-13 | Time offset correction (`offset_hours`) | ics_calendar ships it because broken feeds exist (local time labelled as UTC). Common with scraped EPGs. | LOW | Per source, not per entry. Hidden in an "advanced" section. |
| DF-14 | Retain past matched events for N days | The calendar card shows past matches ("did I miss it?") even after the feed drops them | MEDIUM | Builds on DF-9 storage. Keep N small (≤7 days). |
| DF-15 | Example blueprint "Notify before a matching programme starts" | Removes the "how do I wire this up" barrier. Replaces competitors' built-in notify plumbing with HA-native tooling. | LOW | Ship in repo/docs. Use calendar trigger, negative offset and `mode: queued`, because the HA docs warn `single` mode drops simultaneous starts. |
| DF-16 | Repairs issue on persistent source failure | Proactive feedback when the EPG host dies (bevy.be → open-epg migration in yohaybn shows sources do die) | LOW | `issue_registry` after N consecutive failures. Clear on success. |

### Anti-Features (Commonly Requested, Often Problematic)

| ID | Feature | Why Requested | Why Problematic | Alternative |
|----|---------|---------------|-----------------|-------------|
| AF-1 | Per-channel current/next/prime-time sensors | That's what every other EPG integration does | Entity explosion (shadow578/domodom30 READMEs tell users to disable entities). Duplicates existing integrations. Off-mission. | Point users to domodom30's xmltv_epg for guide-style sensors. The calendar plus DF-6 covers "what's next for my filter". |
| AF-2 | Built-in reminder/notification system (notify target, lead time, saved programmes) | What's On TV and the TV-Guide add-on have it | Re-implements HA automations. Needs persistence and per-device config. Brittle. | Calendar trigger with `offset` plus blueprint DF-15. DF-7 covers "new match appeared". |
| AF-3 | Bundled country/source catalogue (pick "Germany") | What's On TV lists 115 countries | Sources die or move (bevy.be → open-epg.com). Permanent maintenance burden. Licensing grey zone. | Document a few known-good source URLs (iptv-org/epg, epgshare01, TVHeadend `/xmltv/channels`) in the README. |
| AF-4 | Full schedule / match list as entity attributes | Easy templating (yohaybn "Track Full Schedule") | Recorder DB bloat; yohaybn documents "size limit issues in Home Assistant's database". HA's 16 KB attribute limit. | `calendar.get_events` returns the list on demand. Keep sensor attributes to the single next match. |
| AF-5 | Merging consecutive or simulcast entries | Cleaner calendar | Explicitly rejected in PROJECT.md. Hides which channel to watch. Fragile heuristics. | 1 programme = 1 event. Exact-duplicate collapse only (TS-E6). Use exclude regex for noise. |
| AF-6 | Jinja templates for title/description | "HA uses Jinja everywhere" | Rendering Jinja per event across thousands of programmes on every `get_events` call is slow. Templates need `hass` context, are harder to validate in the flow, and are overkill for string assembly. | `str.format_map` placeholders (TS-E2 / DF-10), validated at config time. |
| AF-7 | Plain-substring plus `/regex/flags` mixed syntax (ics_calendar style) | Friendlier for non-regex users | Two syntaxes in one field; the exclude-first-then-include semantics confuses users (ics_calendar needs a NOTE box explaining "exclude `/.*/` to whitelist"). | Regex only, case-insensitive by default, with preview (DF-1) as the safety net. Docs give copy-paste examples (`formel\s*1\|formula\s*1`). |
| AF-8 | Multiple calendars per entry (per channel / per filter group) | "One entry for all my shows" | Rejected in PROJECT.md. Complicates options flow and entity lifecycle. | Create multiple entries. The shared source layer (D3) makes that cheap. |
| AF-9 | Writable calendar (create/delete/hide events) | "Hide this one airing" | The EPG is read-only truth. Edits are lost on refresh. Needs a separate persistence model. | Exclude regex. A UID blocklist is a possible v2 if demand appears. |
| AF-10 | PVR / recorder control, TMDB artwork, custom Lovelace card | Competitors bundle cards and TMDB (cyclope205) | Out of scope (PROJECT.md). Calendar events can't carry images anyway. The core calendar card, atomic-calendar-revive and similar cards already exist. | Calendar triggers drive PVR scripts. Use existing calendar cards. |
| AF-11 | YAML configuration | Power users, version control | PROJECT constraint: UI-only | Config, Options and Reconfigure flows. Diagnostics export for debugging. |
| AF-12 | Fuzzy / "word" / "exact" match modes as separate UI concepts (What's On TV) | Simpler than regex | Three modes plus regex multiplies UI and test surface | Regex covers all three (`\bFriends\b`, `^Title$`). Put examples in the field description text. |

---

## Feature Dependencies

```
[TS-S1/S2/S3 Source fetch + gzip]
    └──requires──> [TS-S6 Streaming executor parse]
                       └──requires──> [TS-E4 Timestamp/tz + stop inference]
                                          └──required by──> [TS-A1 Calendar entity / triggers]
                                          └──required by──> [DF-4 Duration filter]

[D3 Shared source layer (per-URL coordinator, ref-counted)]
    └──required by──> [TS-C4 Multiple entries on same feed]
    └──enhanced by──> [DF-8 Conditional GET] ──> [DF-9 Persisted results]

[D1 Feed available during config flow (download + parse with progress, TS-C3)]
    └──required by──> [TS-F1 Channel picker]
    └──required by──> [DF-1 Filter preview]
    └──required by──> [DF-2 Category picker variant]

[TS-F2/F3/F4/F5/F6 Matcher (pure function: programme x filter-set -> bool)]
    └──required by──> [TS-A1 Calendar] [DF-1 Preview] [DF-6 Next-match sensor] [DF-7 New-match events]
    └──extended by──> [DF-2 Category] [DF-3 Time window] [DF-4 Duration] [DF-5 New/premiere flags]

[TS-E2 Title template engine] ──reused by──> [DF-10 Description template]
[DF-9 Persistence (HA Store)] ──required by──> [DF-7 New-match events (seen-set)] [DF-14 Past-event retention]
[TS-A1 Calendar entity] ──enables──> [DF-15 Blueprint]

[DF-7 New-match events] ──conflicts with──> [no persistence] (restart re-fires everything)
[AF-4 Attribute lists] ──conflicts with──> [Recorder health]
```

### Dependency Notes

- **D1, feed in the config flow:** the channel picker (TS-F1) and preview (DF-1) need a parsed feed *before* the entry exists. The flow should reuse the shared source layer's cache: if another entry already loaded that URL, skip the download. Otherwise download with `async_show_progress`. This is the single riskiest UX dependency for big feeds, so build it early.
- **D2, matcher as a pure function:** the calendar entity, preview, next-match sensor and new-match events all call the same `matches(programme, filter_set)`. Keep it HA-free so it is unit-testable against fixtures. It is the core of the Core Value.
- **D3, shared source vs. per-entry refresh interval:** PROJECT says "refresh interval configurable per source" while entries are per-filter. With two entries on one URL using different intervals, **use the minimum interval among the attached entries**, or store the interval at source level. Decide this in requirements, because it shapes the options flow.
- **Stop inference (TS-E4) before the duration filter (DF-4):** the duration is undefined without a `stop`.
- **Persistence before new-match events (DF-7):** shipping DF-7 without a persisted seen-set spams users after every restart.
- **Calendar state limitation (TS-A3):** HA shows only one event in calendar attributes. Overlapping matches (same race on two channels) are fully visible only via triggers and `get_events`. DF-6 does not fix this either, so document it.

---

## Filter Model Recommendation (opinionated)

One filter set per entry, evaluated per programme:

```
match =
    channel in selected_channels (empty = all)
AND (include_patterns empty OR any(include_regex matches any(include_fields)))
AND NOT any(exclude_regex matches any(exclude_fields))
AND [v1.x] category / time-window / duration / flags constraints
```

- Patterns: multiline text, one regex per line, OR-combined. The `IGNORECASE` toggle defaults to on.
- Fields: `title`, `sub-title`, `desc`, `category`, matched against the selected-language text (DF-12) or all variants.
- An empty include list matches everything on the selected channels, which is a valid "channel calendar" use case. **Warn in the preview when the match count is very large** (for example over 2,000), because the calendar card becomes unusable.

Motivating example (F1, German feed):
- Include fields: title. Include: `formel\s*1|formula\s*1|\bF1\b`
- Exclude fields: title + description. Exclude: `highlights|magazin|vorschau|news`
- Duration ≥ 30 min (DF-4)
- Channels: Sky Sport F1, ORF 1, RTL, ServusTV

---

## MVP Definition

### Launch With (v1)

- [ ] TS-S1..S7: URL/file, gzip by magic bytes, refresh interval, keep-last-good, streaming executor parse, diagnostics. *Without these the integration fails on real feeds.*
- [ ] D3 shared source layer. *PROJECT requirement; needed before multiple entries are realistic with 50 MB feeds.*
- [ ] TS-F1..F6 channel picker, include/exclude regex, case toggle, validation, field selection. *This is the Core Value.*
- [ ] TS-E1..E6 location = channel, title template, description details, tz-correct times with stop inference, stable UID, duplicate collapse.
- [ ] TS-C1..C5 Config + Options flow with download progress, multiple entries, EN/DE.
- [ ] TS-A1..A4 calendar triggers, `get_events`, correct `event` property, manual refresh.
- [ ] **DF-1 filter preview.** *A cheap differentiator once D1 exists, and it removes the main source of support pain (regex trial and error).*
- [ ] DF-2 (category as a matchable field only) and DF-4 duration filter. *Both nearly free once the matcher exists, and directly useful for the F1 example.*
- [ ] HACS packaging (hacs.json, hassfest, HACS validation CI). *PROJECT requirement.*

### Add After Validation (v1.x)

- [ ] DF-6 next-match timestamp sensor. Trigger: users want relative "in 2 days" display or template use.
- [ ] DF-8 conditional GET and DF-9 persisted filtered results. Trigger: restart gaps or slow feeds observed on `ha-host`.
- [ ] DF-3 time-window filter and DF-5 new/premiere flags. Trigger: real feeds show repeat or overnight noise that regex can't handle cleanly.
- [ ] DF-15 notify blueprint. Trigger: first external users.
- [ ] DF-16 Repairs issue on persistent failure.
- [ ] DF-10 description template, DF-11 episode normalisation, DF-12 language preference, DF-13 offset correction.

### Future Consideration (v2+)

- [ ] DF-7 new-match HA events. Defer because it needs persistence (DF-9) and diffing semantics (what counts as "new" when the feed shifts times).
- [ ] DF-14 past-match retention.
- [ ] DF-2 category picker from feed values.
- [ ] Ad-hoc search action with response (yohaybn-style `search_program`). Defer because `get_events` on a broad calendar covers most needs.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Source fetch (URL/file/gzip) + streaming parse | HIGH | MEDIUM | P1 |
| Shared source layer (D3) | HIGH (perf) | MEDIUM | P1 |
| Channel picker from feed | HIGH | MEDIUM | P1 |
| Include/exclude regex + fields + case + validation | HIGH | LOW | P1 |
| TZ-correct times + stop inference | HIGH | MEDIUM | P1 |
| Title template, location = channel, details in description | HIGH | LOW | P1 |
| Config + Options flow with progress | HIGH | MEDIUM | P1 |
| Calendar entity (triggers, get_events) | HIGH | LOW | P1 |
| Filter preview step (DF-1) | HIGH | MEDIUM | P1 |
| Duration filter, category as field | MEDIUM | LOW | P1 |
| EN/DE translations, diagnostics | MEDIUM | LOW | P1 |
| Next-match sensor | MEDIUM | LOW | P2 |
| Conditional GET + persisted results | MEDIUM | MEDIUM | P2 |
| Time window, new/premiere flags | MEDIUM | LOW | P2 |
| Blueprint, Repairs issue | MEDIUM | LOW | P2 |
| Description template, episode normalisation, language preference, offset | LOW–MEDIUM | LOW | P2 |
| New-match events | MEDIUM | MEDIUM | P3 |
| Past-match retention, category picker, search action | LOW | MEDIUM | P3 |

**Priority key:** P1 = must have for launch; P2 = should have, add when possible; P3 = nice to have, future consideration.

---

## Competitor Feature Analysis

| Feature | xmltv_epg (shadow578 / domodom30 fork) | What's On TV (janfajessen) | HomeAssistant-EPG (yohaybn) | TV Guide EPG (iAlias) | ics_calendar (franc6) / core caldav | **Our Approach** |
|---------|------|------|------|------|------|------|
| Entity model | Per-channel current/upcoming/prime-time sensors + image entities | Per-channel sensor with schedule (≤50) in attributes | Per-channel sensors; optional full schedule in attributes (DB bloat) | 2 sensors/channel + favourite binary sensors | One calendar per entry; caldav `custom_calendars` = filtered calendar | **One filtered calendar per entry** (+ optional next-match sensor) |
| Source | Any XMLTV URL, `.gz/.xz/.zip`, streaming parser | Country catalogue + custom URL (`.xml/.xml.gz`) | open-epg.com only | Fixed sources per country | ICS URL / `file://`, URL templates | XMLTV URL or local file, gzip by magic bytes |
| Refresh | Options: interval (hours) | 1–24 h | Daily + `update_channels` service | 30 min–4 h | `download_interval` (15-min multiples), one download at a time globally | Per source, shared download, keep-last-good, manual refresh |
| Channel selection | Picker from feed (setup + options) | Picker fetched live | Picker fetched live | Fixed per country | n/a | Picker from feed with progress step |
| Content filter | None | Keyword watch: contains / word / exact | Search service: case-insensitive regex, channel, date | Favourite titles, substring, comma-separated | include/exclude: substring or `/re/flags`, exclude-first semantics; caldav `search` regex on summary/desc/location | Include/exclude regex, per-filter field choice, case toggle, validated, **previewed** |
| Category / time / duration filters | No (prime-time time setting only) | No | Date filter (today/tomorrow) | No | `include_all_day`, `offset_hours` | Category as field (v1), duration (v1), time window + flags (v1.x) |
| Title formatting | n/a | n/a | n/a | n/a | `prefix` only | `format_map` template, default `{channel}: {title}` |
| Notifications | None | Built-in keyword-watch notify | Assist automation example | Binary sensor → user automation | Calendar triggers | Calendar triggers + blueprint; new-match events later |
| Config UX | Config + options flow (sectioned), progress indicator, EN/FR | Config flow 2 steps | Config flow | Config + options | UI config flow (YAML removed) | Config + options (+ reconfigure), progress, preview, EN/DE |
| Diagnostics | Diagnostics (URL redacted), Last Update sensor | n/a | Debug logging docs | Stale-data fallback | n/a | Diagnostics + Repairs issue |

---

## Sources

Confidence tags come from the GSD `classify-confidence` seam (websearch/webfetch = LOW unverified, MEDIUM when cross-checked). Items marked "primary" were read directly from the authoritative source.

- XMLTV DTD (primary, raw): https://raw.githubusercontent.com/XMLTV/xmltv/master/xmltv.dtd. Covers: `stop` is `#IMPLIED`; no tz means UTC; truncated timestamps; `clumpidx`; `episode-num` systems; `new`/`premiere`/`previously-shown`; multiple `display-name` with the earlier one more canonical. MEDIUM, cross-checked with https://wiki.xmltv.org/index.php/XMLTVFormat
- HA Calendar integration docs (primary): https://www.home-assistant.io/integrations/calendar/. Covers: triggers with offset; calendars read every 15 min; don't use `single` mode. MEDIUM.
- HA developer docs, CalendarEntity (primary): https://developers.home-assistant.io/docs/core/entity/calendar/. Covers: the `event` property; `async_get_events` overlap semantics; tz-aware; no I/O in properties. MEDIUM.
- HA `calendar.get_events`: https://www.home-assistant.io/actions/calendar.get_events/. MEDIUM.
- HA Remote Calendar (no filtering, 24 h refresh): https://www.home-assistant.io/integrations/remote_calendar/. MEDIUM.
- HA CalDAV `custom_calendars` regex `search`: https://www.home-assistant.io/integrations/caldav/. MEDIUM.
- franc6/ics_calendar README (filter semantics, prefix, offset_hours, UI config): https://github.com/franc6/ics_calendar. MEDIUM.
- shadow578/homeassistant_xmltv-epg: https://github.com/shadow578/homeassistant_xmltv-epg. MEDIUM.
- domodom30/ha-xmltv-epg (streaming parser, gz/xz/zip, progress indicator, diagnostics): https://github.com/domodom30/ha-xmltv-epg. MEDIUM.
- janfajessen What's On TV (keyword watches, match modes, multi-instance): https://github.com/janfajessen/What-s-On-TV---EPG-TV-Guide---Home-Assistant. MEDIUM.
- yohaybn/HomeAssistant-EPG (regex search service, full-schedule DB bloat warning): https://github.com/yohaybn/HomeAssistant-EPG. MEDIUM.
- iAlias/HomeAssistantTVGuideEPG (favourite binary sensors): https://github.com/iAlias/HomeAssistantTVGuideEPG. MEDIUM.
- criticallimit/TV-Guide add-on (saved programmes, reminders, next-reminder sensor): https://github.com/criticallimit/TV-Guide. MEDIUM.
- cyclope205/programme-tnt-fr (genre filter, favourites): https://github.com/cyclope205/programme-tnt-fr. MEDIUM.
- HA Community "EPG Support for TV" (REST-sensor workaround, 255-char state limit): https://community.home-assistant.io/t/epg-support-for-tv/237892. LOW.
- Channels community "Integrating Channels calendar into Home Assistant" (demand for EPG/recording calendars as triggers): https://community.getchannels.com/t/integrating-channels-calendar-into-home-assistant/40993. LOW.

### Gaps / verify in phase research

- How HA's `SelectSelector` (multiple, dropdown) behaves with 1,000–10,000 options from big iptv-org feeds: frontend performance and search-as-you-type. A regex-based channel filter may be needed as a fallback. LOW.
- Exact `async_show_progress` usage pattern in current HA core (task-based API changed in 2024.x). Verify against the current dev docs during the config-flow phase.
- Real-world coverage of `<new/>`, `<previously-shown>` and `<category>` in German feeds (epgshare01 DE, iptv-org DE, TVHeadend). This determines whether DF-5 is worth building. Check once a real source is chosen.

---
*Feature research for: Home Assistant XMLTV → filtered calendar integration*
*Researched: 2026-10-12*
