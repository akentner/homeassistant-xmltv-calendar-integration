# Phase 1: First Filtered Calendar - Context

**Gathered:** 2026-10-12
**Status:** Ready for planning

<domain>
## Phase Boundary

User can add an XMLTV source (HTTP(S) URL or local file, plain or gzip) via the HA UI as a config entry, attach one or more calendars as config subentries filtered by channel and include/exclude regex, and see exactly the matching programmes as correctly timed calendar events that drive calendar triggers. Includes the pure `xmltv/` library (built test-first), coordinator, calendar entity, source config flow, calendar subentry flow, HACS scaffold and CI.

Requirements: SRC-01, SRC-02, SRC-03, SRC-04, SRC-09, SRC-13, FLT-01, FLT-02, FLT-03, FLT-04, FLT-07, EVT-01, EVT-02, EVT-05, EVT-06, AUT-01, AUT-02, CFG-01, DST-01, DST-02.

Not in this phase: per-filter field selection, case toggle, Unicode normalization, duration/time-window filters, preview, templates (Phase 2); disk cache, conditional GET, daily schedule, timezone options, options flow, progress step, Repairs, diagnostics (Phase 3); sensor, new-match event, retention, blueprint, DE translation, releases (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### Project identity
- **D-01:** Integration domain is `xmltv_calendar` (`custom_components/xmltv_calendar/`). — **Reversibility:** one-way — domain is part of config entries, entity registry and HACS install path; renaming requires user re-setup.

### Channel selection
- **D-02:** Calendar subentry offers a searchable multi-select of channels built from the loaded source's feed, PLUS an optional channel regex field (matched against channel ID) as fallback for very large feeds. Selected channels and channel regex are OR-combined; both empty = all channels.
- **D-03:** Picker shows the channel **ID** only in Phase 1 (no display-name label, no custom mapping). Event location still uses the channel display name from the feed (EVT-02), falling back to the ID.
- **D-04:** If a selected channel ID no longer exists in the feed, ignore it silently and log a warning (once per refresh); the calendar continues with the remaining channels.

### Regex input
- **D-05:** Include and exclude are multiline text fields, one pattern per line, OR-combined within each field; blank lines ignored. Match = channel AND (include empty OR any include matches) AND NOT any exclude matches.
- **D-06:** Empty include = all programmes of the selected channels match (allows "channel calendars").
- **D-07:** In Phase 1, include and exclude both apply to **title + sub-title**. (Per-filter field selection incl. description/category comes in Phase 2 — FLT-05; Phase 1 data model should already carry sub-title, description, category so Phase 2 only adds selection.)
- **D-08:** Matching in Phase 1 is case-insensitive (`re.IGNORECASE`); case toggle and Unicode normalization are Phase 2 (FLT-06).

### Naming & devices
- **D-09:** Source config flow has a required **Name** field (default suggestion derived from URL host or file name); it becomes the config entry title.
- **D-10:** Calendar subentry has a name field; entity_id derives from the calendar name only (e.g. "Formel 1" → `calendar.formel_1`), not prefixed with the source name.
- **D-11:** One HA device per calendar subentry (complies with the 2026.8 "max one device per subentry" rule); Phase 4's next-match sensor will attach to the same device.

### Time defaults
- **D-12:** Missing `stop`: end = start of the next programme on the same channel; for the last programme of a channel, default duration 60 minutes.
- **D-13:** Refresh interval default **24 h**, minimum **1 h** (user's main source regenerates once daily at 18:00; daily fixed-time schedule is Phase 3 / SRC-05).
- **D-14:** Timestamps without offset are treated as UTC (XMLTV DTD) in Phase 1; the "no offset = local time" option is Phase 3 (SRC-10).

### Test data & dev environment
- **D-15:** Fixtures: small hand-written synthetic XMLTV files covering all edge cases (full/shortened timestamps, with/without offset, missing stop, duplicates, umlauts, malformed programmes, gzip with `.xml` extension) + a generator script for a 50+ MB benchmark feed (not committed) + one **real German feed excerpt** (e.g. from iptv-org/epg) checked in, trimmed to a reasonable size.
- **D-16:** Manual testing happens on the **local Podman HA instance** (`~/Projects/dev/compose.yml`, container `ha-dev`, `TZ=Europe/Berlin`, image `stable`): add a read-only volume mount `../homeassistant-xmltv-integration/custom_components/xmltv_calendar:/config/custom_components/xmltv_calendar:ro` (same pattern as kroki/chargefinder) and mount a fixtures directory under `/media` for local-file source tests. Deployment to `ha-host` is not part of the Phase 1 dev loop.

### Claude's Discretion
- Regex help in the form: short examples in field descriptions (e.g. `formel\s*1|formula\s*1`, `^Tatort$`); detailed examples later in README (Phase 4).
- `iot_class` choice (`cloud_polling` vs `local_polling`).
- Exact handling of very large channel lists in the selector (research flag) — channel regex fallback (D-02) is the agreed safety net.
- Repo scaffold details (pyproject/uv, ruff config, CI workflows) — follow sibling integrations.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope & decisions
- `.planning/PROJECT.md` — vision, constraints, key decisions (source entry + calendar subentry topology)
- `.planning/REQUIREMENTS.md` — requirement IDs and wording for this phase
- `.planning/ROADMAP.md` §Phase 1 — goal, success criteria, notes (unique_id from normalized source, single update listener, `source_not_loaded` abort, subentry before platform loaded)

### Research
- `.planning/research/SUMMARY.md` — consolidated findings, topology decision, pitfalls reinterpreted for subentries
- `.planning/research/STACK.md` — HA 2026.3 floor, Python 3.14, phcc 0.13.372, Ruff 0.17.0, iterparse benchmark, no runtime deps
- `.planning/research/ARCHITECTURE.md` — component boundaries, pure `xmltv/` library, coordinator in `runtime_data`, bisect lookups, live `event`
- `.planning/research/PITFALLS.md` — timestamp parsing, CalendarEvent validation, calendar overlap semantics, memory/regex pitfalls
- `.planning/research/FEATURES.md` — TS-* table stakes referenced by this phase

### Sibling reference implementations (outside this repo)
- `~/Projects/homeassistant-kroki-integration/custom_components/kroki/config_flow.py` — existing `ConfigSubentryFlow` usage
- `~/Projects/homeassistant-mqtt-actions-integration/custom_components/mqtt_actions/config_flow.py` — existing `ConfigSubentryFlow` usage; repo has pyproject/uv/renovate + CI to copy (`.ruff.toml`, release workflow per STACK.md)
- `~/Projects/homeassistant-gatus-integration/custom_components/gatus/coordinator.py` — `DataUpdateCoordinator` pattern, uv + tests layout
- `~/Projects/dev/compose.yml` — local Podman HA dev instance to extend (D-16)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No code in this repo yet (greenfield).
- Sibling integrations provide copyable scaffolding: `hacs.json`, `pyproject.toml` + `uv.lock`, `ruff.toml`, `renovate.json`, `tests/` layout (gatus, mqtt-actions, traefik).

### Established Patterns
- `ConfigSubentryFlow` already used in kroki and mqtt_actions — follow their structure for the calendar subentry flow.
- `DataUpdateCoordinator` in gatus/traefik/chargefinder.
- Monorepo conventions: uv, Ruff 120-char lines, English code/comments.

### Integration Points
- `~/Projects/dev/compose.yml` volume mount for local testing.
- HACS custom repository (GitHub) — CI with hassfest + HACS action.

</code_context>

<specifics>
## Specific Ideas

- Motivating use case: "which channel shows Formula 1 next, and when" — but the integration must stay generic (no F1-specific logic).
- User's main real source regenerates once daily at 18:00 → default refresh 24 h.

</specifics>

<deferred>
## Deferred Ideas

- Per-source channel ID → friendly name mapping (usable in picker label, `{channel}` placeholder, location) — future phase / backlog.
- Picker label "display-name (id)" — revisit together with the mapping.

</deferred>

---

*Phase: 01-first-filtered-calendar*
*Context gathered: 2026-10-12*
