# Walking Skeleton — XMLTV Calendar (Home Assistant Integration)

**Phase:** 1
**Generated:** 2026-10-13

## Capability Proven End-to-End

In Home Assistant, a user adds an XMLTV URL source and one calendar entirely through the UI flows and sees the feed's programmes as correctly timed calendar events. `calendar.get_events` returns them, and the entity is `on` while one airs. Proven by `tests/test_tracer.py` (plan 01-01) and, in the real frontend, on the local `ha-dev` container (plan 01-09).

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Framework | Home Assistant custom integration, domain `xmltv_calendar` (D-01), HA ≥ 2026.3 (`hacs.json`), developed and tested on HA 2026.10.1, Python 3.14 | HACS distribution for the user's HA; the domain is a one-way door, decided by the user |
| Topology | One config entry per **source** (URL or file) holding one `DataUpdateCoordinator` in `entry.runtime_data`; one config **subentry** per **calendar**, one `CalendarEntity` and one device per subentry (D-10, D-11) | HA-native sharing of one download and parse across calendars without custom ref-counting (PROJECT key decision) |
| Data layer | No database. Persistent state is HA's config-entry storage only: entry.data `{source_type, url or path}`, entry.options `{refresh_hours}`, subentry data `{channels, channel_regex, include, exclude}`, and `unique_id` = source identity (scheme decided in 01-07 Task 2). Feed data lives in memory as immutable `EpgData` (`eq=False`); disk cache is Phase 3 | Zero runtime dependencies; the feed is the source of truth |
| Parsing | Pure `custom_components/xmltv_calendar/xmltv/` library (no HA imports, enforced by an AST test): stdlib `ElementTree.iterparse` + `root.clear()`, gzip by magic bytes, size caps, `time.sleep(0.001)` every 250 programmes, always run in the executor | 60 MB feeds without blocking the loop; testable without HA |
| Filtering | `FilterSpec.from_mapping(subentry.data).apply(epg)` in the executor per calendar on every coordinator update. Channel predicate = IDs OR channel regex; include OR-combined, exclude wins; per field (title, sub-title), case-insensitive | Core value: exactly the user's programmes; reused for flow validation |
| Calendar reads | `MatchIndex` (bisect, max-duration lookback), end-inclusive overlap, live `event` from `dt_util.now()`, at most 5,000 events per query, executor-built above 200 | Trigger correctness at 15-minute boundaries; bounded cost |
| Configuration UX | Config flow: menu `url` / `file` → shared `name` step (D-09); subentry flow "Add calendar". Exactly one diffing update listener (reload only on data/options change). No YAML, no options flow in Phase 1 | CFG-01; no re-download on calendar add or rename |
| Auth | None of its own. Flows are admin-only HA flows; URL tokens stay in entry.data, never in logs, and are hashed out of `unique_id` if 01-07 chooses sha256; local files restricted by `hass.config.is_allowed_path` | Matches the HA trust model (core `remote_calendar`) |
| Tooling | uv (`package = false`), Ruff 0.17 (`select = ["ALL"]`, 120 columns), pytest + pytest-homeassistant-custom-component (pins approved in 01-01 Task 1), TDD for pure logic | Monorepo conventions; sibling-proven config |
| Deployment target | Dev: Podman `ha-dev` (`~/Projects/dev/compose.yml`) with a read-only component mount and `/media/xmltv` feeds (D-16). Distribution: public GitHub repo as a HACS custom repository; CI = Ruff + pytest + benchmark, Validate = hassfest + HACS (SHA-pinned) | Fast local loop; production install via HACS later |
| Directory layout | `custom_components/xmltv_calendar/{__init__, const, data, source, coordinator, calendar, config_flow}.py`, `translations/en.json`, `brand/`, `xmltv/{model, timeparse, normalize, parser, filter, render, window}.py`; tests in `tests/` (HA layer) and `tests/xmltv/` (pure, hass-free); `scripts/` for generator and trimmer | Pure core plus a thin HA shell; one module per responsibility |

## Stack Touched in Phase 1

- [ ] Project scaffold: uv project, Ruff, pytest harness with `setup_xmltv` / `forbid_loop_io` / `berlin_tz` fixtures (01-01)
- [ ] Routing: HA config flow (menu → url/file → name) and calendar subentry flow are the "routes" (01-01, 01-07, 01-08)
- [ ] Data: a real write (config entry and subentry stored through the flows) and a real read (coordinator downloads and parses the feed; calendar reads matches) (01-01)
- [ ] UI: a real interaction (the "Add calendar" form with channel picker and patterns) wired to the calendar entity shown in the HA Calendar panel (01-01, 01-08, 01-09)
- [ ] Deployment: running on the `ha-dev` dev environment (01-09); published as a HACS custom repository with green CI (01-10)

## Out of Scope (Deferred to Later Slices)

- Field-scoped matching (description, category), case toggle, Unicode normalization, duration/time-window filters, live preview, title/description templates, calendar reconfigure (Phase 2)
- Disk cache, conditional GET, daily schedule, timezone options, options flow, setup progress step, last-good data while failing, Repairs, diagnostics (Phase 3)
- Next-match sensor, new-match event, past-match retention, blueprint, German translation, README guide, tagged releases (Phase 4)
- Channel ID → friendly name mapping and "display-name (id)" picker labels (deferred idea, backlog)
- Deployment to `ha-host` (not part of the Phase 1 dev loop, D-16)

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without changing its decisions (topology, pure library, single diffing listener, stored schema keys):

- Phase 2: Precise filters and preview: field-scoped Unicode-safe regex, duration and time-window filters, templates, live preview, instant reconfigure through the diffing listener
- Phase 3: Resilient sources: cache, conditional GET, daily schedule, timezone options, options flow, Repairs, diagnostics
- Phase 4: Automation extras and release: next-match sensor, new-match event, retention, blueprint, DE translation, README, tagged HACS releases
