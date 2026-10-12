# Project Research Summary

**Project:** XMLTV Calendar (Home Assistant integration)
**Domain:** Home Assistant custom integration (read-only polling, CalendarEntity, HACS)
**Researched:** 2026-10-12
**Confidence:** HIGH (Features: MEDIUM)

## Executive Summary

The integration is a read-only HA polling integration: one expensive shared resource (a 1–150 MB XMLTV feed) feeds several cheap, filtered `calendar.*` consumers. About seven EPG/XMLTV integrations exist (shadow578, domodom30 fork, What's On TV, yohaybn, iAlias, cyclope205, TV-Guide add-on) — all build per-channel current/next sensors; **none produces a filtered calendar**. The closest filter prior art is `ics_calendar` include/exclude and core `caldav` `custom_calendars` regex search.

Recommended approach: zero runtime dependencies (stdlib streaming `iterparse` + `gzip` in the executor), **one parent config entry per source with the coordinator in `runtime_data`, one config subentry per calendar** (user decision, see below), filter + title rendering as a pure, HA-free library, and a calendar entity that does only cheap bisect lookups over precomputed matches.

Main risks: silent timestamp errors (`strptime` mis-parses shortened XMLTV timestamps), one bad programme breaking `async_get_events`, event-loop blocking / memory blow-up on large feeds, and the update-listener / `OptionsFlowWithReload` conflict in the subentry model. All have concrete mitigations below.

## User Decision: Config Topology (final)

- **One config entry per XMLTV source** — holds `DataUpdateCoordinator(config_entry=entry)` in `entry.runtime_data`, refresh interval and source options, `unique_id` from normalized source to block duplicates.
- **One `ConfigSubentryFlow` subentry per calendar** — user + reconfigure steps; channel list read from the already loaded coordinator (abort `source_not_loaded` otherwise).
- **Rejected:** flat entries + `hass.data` ref-counted registry.

## Key Findings

### Recommended Stack

HA floor **2026.3.0** / Python **3.14.2** (first release requiring 3.14.2; supports local `brand/icon.png`; `hass.config.cache_path`). Develop/test against HA 2026.10.1 via `pytest-homeassistant-custom-component==0.13.372` (pins pytest 9.0.3, pytest-asyncio 1.4.0, syrupy, freezer, respx, pytest-socket — don't add separately). Ruff 0.17.0 (`select=ALL`, line 120, py314; copy `.ruff.toml` from mqtt-actions), uv 0.13.0.

**Core technologies:**
- `xml.etree.ElementTree.iterparse` + `root.clear()` in executor — 78 MB / 120k programmes in 1.2 s at 14 MB peak (full `ET.parse`: 396 MB); `"requirements": []`
- `gzip` detected by magic bytes `1f 8b`, decompressed-size cap — servers mislabel gzip; bomb protection
- HA shared aiohttp session + conditional GET (ETag/If-Modified-Since) + raw-file cache in `cache_path` — no re-download on restart/reload
- Custom slicing timestamp parser — `strptime` mis-parses shortened timestamps and is ~7x slower
- Restricted `str.format_map` for title templates (no `.`/`[` in fields, missing → empty) — Jinja `Template.render()` from executor hops to the loop; too slow for thousands of titles
- stdlib `re`, compiled once per filter set
- CI: hassfest, `hacs/action`, Ruff, pytest; release workflow checking tag == manifest version (copy from mqtt-actions)

**Avoid:** `python-xmltv` (2014), `py-xmltv` (2021), `pydantic-xml` (full tree, event-loop parsing in shadow578), Jinja for titles, pinning lxml (HA pins `lxml==6.1.2`).

### Expected Features

**Must have (table stakes):**
- URL + local file source (`is_allowed_path`; `/media`, `/config/www` allowed by default), gzip, configurable refresh, keep last good data, non-blocking streaming parse, diagnostics with redacted URL
- Channel picker populated from the feed (empty = all channels)
- Include regex AND NOT exclude regex; case-insensitive by default with toggle; regex validated in flow; per-filter field selection (title, sub-title, description, category)
- Location = channel display name; title template (default `{channel}: {title}`); description with sub-title/episode/category/desc; correct tz-aware start/end with stop inference; stable UID; exact-duplicate collapse
- Full config via flows, editable later, progress indicator during initial download, EN + DE translations
- Works with calendar triggers, `calendar.get_events`, calendar card; manual refresh via `homeassistant.update_entity`

**Should have (differentiators):**
- **DF-1 Filter preview step** (match count + next ~10 matches) — no competitor has it; strongest UX differentiator
- DF-4 Min/max duration filter (useful for F1: drops trailers/teasers)
- DF-2 Category as matchable field (v1), category picker later
- DF-6 Next-match timestamp sensor, DF-8 conditional GET, DF-13 offset correction / "no-offset timestamps are local time" option, DF-16 Repairs issue on persistent failure, DF-15 notification blueprint

**Defer (v2+):**
- DF-7 HA event on newly appearing matches (needs persisted seen-set), DF-14 retain past matches, DF-3 time-window filter, DF-5 new/premiere flags (feed coverage varies), DF-12 preferred language

**Anti-features:** per-channel sensors, built-in notification system, bundled source catalogue, full schedule in attributes (recorder bloat, 16 KB limit), merging entries, Jinja titles, mixed plain/`/regex/` syntax, writable calendar, PVR control, YAML config, fuzzy/word/exact match modes.

### Architecture Approach

A pure `xmltv/` library (no `homeassistant` imports) holds parser, models, filter engine and title rendering and runs in the executor. The source entry owns fetcher + coordinator; each refresh parses once (dropping out-of-window programmes), then evaluates every subentry's filter once in the executor, producing sorted, precomputed match lists. Calendar entities answer `async_get_events` via bisect overlap lookups and compute `event` fresh from the current time on every call. Exactly one diffing update listener on the source entry: full reload only when source data/options change; subentry add/edit/remove updates entities in place (no re-download / re-parse).

**Major components:**
1. `xmltv/parser.py` + `models.py` — streaming parse, timestamp parsing, stop inference, sanitizing
2. `xmltv/filter.py` + `render.py` — compiled filter sets, field selection, title/description rendering
3. `source.py` — HTTP/file fetch, gzip sniffing, size cap, conditional GET, `cache_path` cache
4. `coordinator.py` — `DataUpdateCoordinator(config_entry=entry)`, `EpgData` (`eq=False`), per-subentry match lists
5. `calendar.py` — one `CalendarEntity` per subentry, bisect queries, live `event`
6. `config_flow.py` — source ConfigFlow (with `async_show_progress`), plain `OptionsFlow`, `CalendarSubentryFlow` (user + reconfigure, preview)
7. `__init__.py` — setup/unload, diffing update listener

### Critical Pitfalls

1. **Timestamp parsing** — `strptime("202610122030 +0200", "%Y%m%d%H%M%S %z")` yields 20:03. Custom parser; missing offset = UTC per DTD, plus per-source "no offset = local time" option; tests with explicit timezone (test framework default is `US/Pacific`).
2. **One bad programme breaks the calendar** — `CalendarEvent` rejects naive datetimes and end < start; the trigger only catches `HomeAssistantError` and drops the 15-min window. Sanitize at parse time (infer missing stop, drop invalid), raise only `HomeAssistantError`.
3. **Calendar semantics** — return all events *overlapping* the range (else end triggers miss); compute `event` live (state gets stuck otherwise); trigger polls every 15 min and never looks back; document `mode: queued`; overlapping matches visible only via triggers/`get_events`.
4. **Subentry lifecycle (reinterpreted Pitfall 11)** — every subentry change fires parent update listeners; `OptionsFlowWithReload` + listener raises `ValueError` (error from 2026.12) → plain `OptionsFlow`, subentry reconfigure via `async_update_and_abort`, diffing listener. Also: max one device per subentry (2026.8), calendars can't move between sources, subentry may be added before platform loaded (`add_entities is None`).
5. **Memory / regex** — full-tree parse of 100 MB ≈ 800 MB; stream + clear ≈ 20 MB. Blank exclude pattern matches everything; ReDoS example 6.2 s on 27 chars; `ß`≠`ss` under IGNORECASE, decomposed umlauts need NFC normalization. Validate in flow, ignore empty patterns, normalize text.

Eliminated by the subentry decision: shared coordinator killed by wrong entry / `config_entry=None` / ref-counting (Pitfall 5) and refresh-interval conflicts between entries (Pitfall 6). Pitfalls 15/24 (cleanup) are handled by cache + conditional GET and HA's automatic subentry entity cleanup. Platform note: since 2026.9 voluptuous is replaced by probatio — keep the old import, don't list it as a requirement, don't assert on error message text.

## Implications for Roadmap

### Phase 1: Scaffold + Pure Domain Library
**Rationale:** highest correctness/performance risk, no HA needed, ideal for TDD.
**Delivers:** repo scaffold (manifest, hacs.json, brand icon, skeleton CI), parser, models, filter engine, title/description rendering, fixtures, 50 MB benchmark with tracemalloc budget.
**Addresses:** TS-S3, TS-S6, TS-F2–F6, TS-E1–E6, DF-4.
**Avoids:** Pitfalls 1, 2, 5.

### Phase 2: HA Runtime Core
**Rationale:** proves end-to-end value on `ha-host`.
**Delivers:** `source.py` (streaming, caps, conditional GET, `cache_path` cache), coordinator, calendar entity (bisect overlap, live `event`), minimal source config flow.
**Uses:** aiohttp session, `DataUpdateCoordinator(config_entry=entry)`, `runtime_data`.
**Implements:** components 3–5, 7.

### Phase 3: Full Configuration UX
**Rationale:** depends on Phase 2 coordinator data and subentry application.
**Delivers:** `CalendarSubentryFlow` (channel picker, regex/template validation, DF-1 preview), plain `OptionsFlow`, diffing update listener, progress step, EN/DE strings.
**Avoids:** Pitfall 4.

### Phase 4: Distribution + Hardening
**Rationale:** standard patterns, needs a working product.
**Delivers:** hassfest + HACS action, releases, diagnostics redaction, Repairs issue, migration scaffold, README (15-min trigger limit, `mode: queued`, source examples).

### Phase Ordering Rationale

- Pure library first: all later phases consume its models; testable without HA.
- Runtime before full UX: subentry flow reads channels from the loaded coordinator.
- Coarse granularity per config — 4 phases.

### Research Flags

Needs deeper research during planning:
- **Phase 3:** `async_show_progress` API, subentry helper APIs, scope of listener + reload-helper deprecation, `SelectSelector` with thousands of options (may need regex channel filter fallback).
- **Phase 2:** light check of `cache_path` and coordinator APIs.

Standard patterns (skip research): Phase 1, Phase 4.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | PyPI/GitHub APIs, HA `const.py` at tags, local benchmarks |
| Features | MEDIUM | Competitor READMEs, HA docs, XMLTV DTD; thin forum demand |
| Architecture | HIGH | Read in HA core source (2026.11.0.dev, release tags) |
| Pitfalls | HIGH | HA source + DTD + local experiments; HACS/brands MEDIUM |

**Overall confidence:** HIGH

### Gaps to Address

- Options-flow conflict between files (STACK/PITFALLS: `OptionsFlowWithReload`, ARCHITECTURE: plain `OptionsFlow`) — resolved in favour of plain `OptionsFlow` + listener; verify against 2026-05-07 dev blog in Phase 3.
- Parse time on target hardware unmeasured — Phase 1 benchmark; if < ~5 s, "reload on any change + disk cache" is an acceptable fallback to the diffing listener.
- No real XMLTV source yet — fixtures only; real feeds later.
- `SelectSelector` with large channel lists — Phase 3 research.
- `CalendarEvent` construction cost (~38 µs, voluptuous validation) — heavy work in executor, build lazily per requested slice, cap ~2,000.
- Keep 2026.3 floor; don't use `CalendarEvent.status`.
- `iot_class`: `cloud_polling` vs `local_polling` — decide in Phase 1.
- `.planning/research/.cache/` contains tool-cache JSON — gitignored.

## Sources

- HA core source: `config_entries.py`, `helpers/update_coordinator.py`, `helpers/entity_platform.py`, `components/calendar/__init__.py`, `trigger.py`, `components/openai_conversation/*`
- https://developers.home-assistant.io/docs/config_entries_config_flow_handler
- https://developers.home-assistant.io/blog/2025/02/16/config-subentries
- https://developers.home-assistant.io/blog/2026/07/21/device-registry-single-config-entry
- XMLTV DTD (`xmltv.dtd`), XMLTV wiki
- Competitors: shadow578/homeassistant_xmltv-epg, domodom30 fork, What's On TV, yohaybn, iAlias, cyclope205, ics_calendar
- Detailed sources in STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md

---
*Research completed: 2026-10-12*
*Ready for roadmap: yes*
