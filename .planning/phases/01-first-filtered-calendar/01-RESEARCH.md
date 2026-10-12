# Phase 1: First Filtered Calendar - Research

**Researched:** 2026-10-12
**Domain:** Home Assistant custom integration (Python 3.14, HA 2026.10): config entry + config subentries, DataUpdateCoordinator, CalendarEntity, streaming XMLTV parsing, HACS/CI scaffold
**Confidence:** HIGH. Most HA API claims were checked by running a throwaway prototype against `pytest-homeassistant-custom-component==0.13.372`, which pins `homeassistant==2026.10.1`.

> Scope note: project-level research in `.planning/research/` (STACK, ARCHITECTURE, PITFALLS, FEATURES, SUMMARY) is the baseline. This file does not repeat it. It adds Phase 1-specific findings, corrects two baseline claims (overlap semantics and blocking-call detection in tests), and gives prescriptive guidance for the planner.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### Deferred Ideas (OUT OF SCOPE)
- Per-source channel ID → friendly name mapping (usable in picker label, `{channel}` placeholder, location) — future phase / backlog.
- Picker label "display-name (id)" — revisit together with the mapping.

Also out of scope for Phase 1 (CONTEXT `<domain>`): per-filter field selection, case toggle, Unicode normalization, duration/time-window filters, preview, templates (Phase 2); disk cache, conditional GET, daily schedule, timezone options, options flow, progress step, Repairs, diagnostics (Phase 3); sensor, new-match event, retention, blueprint, DE translation, releases (Phase 4).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SRC-01 | Add source by HTTP(S) URL as its own config entry | Pattern 1 (source flow), Code Example "Source config flow"; URL normalization via `yarl.URL` (verified) |
| SRC-02 | Add source by local file path (validated against HA allowed paths) | `hass.config.is_allowed_path` must run in the executor; on HA Container `/media` is allowed by default (core_config.py:437-444) |
| SRC-03 | Gzip detected by content, not extension | Sniff the magic bytes `1f 8b`; works with `aioclient_mock` (prototype served gzip as `application/octet-stream`) |
| SRC-04 | Refresh interval per source | `NumberSelector` hours (default 24, min 1, D-13). Store it in `entry.options` from day one (`ConfigFlow.async_create_entry(options=...)` verified) |
| SRC-09 | 50+ MB without blocking the loop, bounded memory | Benchmark: 60 MB / 80k programmes parsed in 1.4 s, tracemalloc peak 74 MB. Loop gaps up to ~100 ms for **plain** XML, fixed by a periodic `time.sleep(0.001)` yield (max gap ~10 ms) |
| SRC-13 | Duplicate sources rejected | `async_set_unique_id(normalized)` + `_abort_if_unique_id_configured()`. Prototype: an upper-cased duplicate URL aborts `already_configured` |
| FLT-01 | Multiple calendars per source (subentries) | `ConfigSubentryFlow` + `async_get_supported_subentry_types`. Entities are added in place via the update listener (no re-download, verified) |
| FLT-02 | Channel list from the feed (empty = all) | `SelectSelector(multiple=True, mode=DROPDOWN, sort=True)`. The frontend renders a fuzzy-searchable, virtualized picker. Channel-regex fallback per D-02 |
| FLT-03 | Include regex, OR-combined | One compiled pattern per non-blank line, `re.search` with `re.IGNORECASE`, evaluated **per field** (title, sub-title) |
| FLT-04 | Exclude regex; channel AND include AND NOT exclude | Pure `FilterSpec.matches()` in `xmltv/filter.py` |
| FLT-07 | Invalid regex rejected in the flow; empty ignored | Compile each line in the flow; `errors={"include": "invalid_regex"}` plus a description placeholder with the bad line and the `re.error.msg` |
| EVT-01 | One event per programme; exact duplicates collapsed | Dedup key `(channel_id, start_utc, title)` at parse time |
| EVT-02 | Location = channel display name | First `<display-name>`, falling back to the channel id (D-03) |
| EVT-05 | Tz-aware start/end for all variants; stop inferred | Reference `parse_xmltv_time()` (17-case table test passes); stop inference per D-12 |
| EVT-06 | Stable UIDs across refreshes | UID derived from `channel_id` + UTC start + short title hash (deterministic) |
| AUT-01 | Calendar triggers + `calendar.get_events` | Prototype: the trigger fires with an offset, `get_events` returns overlapping events. **Overlap must be end-inclusive** (`end >= start_date`), otherwise end triggers are missed at 15-min window boundaries |
| AUT-02 | `on` while a match airs; attributes show current/next | `event` computed live from `dt_util.now()`. Prototype state went on at 12:00 and off at 14:00 without a refresh |
| CFG-01 | All setup via UI | Config flow (source) + subentry flow (calendar); no YAML, no `async_setup` |
| DST-01 | HACS install: valid hacs.json/manifest.json/brand icon | Copy the mqtt-actions layout (its Validate workflow is green with a local `brand/icon.png`). **The GitHub repo does not exist yet** (human action) |
| DST-02 | CI: hassfest, HACS, Ruff, pytest on every push | Copy mqtt-actions `ci.yml`/`validate.yml` (SHA-pinned). Add a separate benchmark job |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

From `/home/akentner/CLAUDE.md`, `/home/akentner/Projects/CLAUDE.md`, `.claude/CLAUDE.md`:

- Code, comments and commits in **English**. Chat with the user in German.
- Python projects use **uv** for dependency management and **Ruff** for linting (120-char lines). Use `uv run --with <pkg>` and never `pip install` globally.
- HA components use **Config Flow (UI setup)**; for this project it is **Config Flow + Options/Subentry flows only, no YAML**.
- Large XMLTV files must not block the HA event loop. Parse in the executor and share one parse across calendars.
- Distribution: HACS-compatible repository structure and validation.
- **Pushes are done by the user, not the assistant.** Creating the GitHub repo and pushing are human actions.
- Use GSD workflow entry points for file changes. Respect `.planning/` state.
- Plans must be detailed and verifiable backwards from the goal; implementations minimal and atomic.
- Secrets via Bitwarden only; no plaintext credentials in files.
- Shell scripts must pass `shellcheck` (monorepo rule; relevant only if a fixture-generator shell wrapper is added. Prefer Python).
- `.claude/CLAUDE.md` stack TL;DR: HA ≥ 2026.3.0 / Python 3.14, phcc `0.13.372`, `"requirements": []`, stdlib `iterparse` + `gzip` in the executor, Ruff 0.17.0 with `select = ["ALL"]`, `extend-exclude = [".planning", ".claude"]`, CI = hassfest + `hacs/action` + Ruff + pytest. Use `aioclient_mock`, not `aioresponses`.

## Summary

Phase 1 is a walking skeleton. The project-level research already settled the topology (source config entry + calendar subentries), the stack (zero runtime dependencies, stdlib `iterparse`) and the major pitfalls. This research de-risked the remaining unknowns by building a throwaway prototype integration and running it under the exact target harness (phcc 0.13.372 → HA 2026.10.1). Confirmed:
- subentry creation from loaded coordinator data
- in-place entity addition without a re-download
- `calendar.formel_1` entity IDs from a per-subentry device
- automatic entity removal on subentry delete
- calendar triggers with offsets firing
- `calendar.get_events` overlap
- live `on`/`off` state transitions

Three findings change what the planner must do, compared with the baseline research:
1. **Overlap must be end-inclusive.** `async_get_events` must return events with `start < end_date and end >= start_date`, as the core `demo` calendar does. With the strict `end > start_date` from PITFALLS.md, an `event: end` trigger is **silently skipped** whenever the programme end coincides with a 15-minute trigger-window boundary. The prototype reproduced this deterministically under `freezer`.
2. **HA's blocking-call detector is off under pytest** (`skip_for_tests=True` for `open`). "No blocking I/O on the loop" needs its own test guard (verified fixture below) plus a loop-latency benchmark.
3. **Test-harness import trap.** The phcc `hass` fixture puts its own `testing_config/custom_components` package first. Our `custom_components.xmltv_calendar` is then "not found" unless `tests/conftest.py` imports it at module level, as mqtt-actions does.

Performance is comfortably inside budget on the dev box: 60 MB / 80k programmes in about 1.4 s, with a tracemalloc peak of about 74 MB while retaining title, sub-title, description and categories (D-07). One catch: **plain (uncompressed) feeds starve the event loop for up to ~100 ms** while the parser thread holds the GIL. Gzip feeds don't, because zlib releases the GIL. A cooperative `time.sleep(0.001)` every 250 programmes caps loop gaps at about 10 ms, at a cost of about 0.6 s of wall time.

**Primary recommendation:** Build in this order:
1. Scaffold + CI + structure tests (Wave 0).
2. The pure `xmltv/` library, test-first: time → parser → filter → render. Include the 60 MB benchmark (time, tracemalloc, loop gap).
3. Source fetch + coordinator + calendar entity, with end-inclusive bisect overlap and a live `event`.
4. Flows.
5. Human checkpoints: GitHub repo/push/HACS and a manual UAT on `ha-dev`.

Use a **minimal diffing update listener already in Phase 1**: add/remove entities in place and reload only if `entry.data`/`entry.options` change. A reload-on-change listener would re-download 50 MB on every "add calendar" and on every **entry rename**, because title changes also fire the listener. Phase 1 has no disk cache.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| XMLTV parsing, timestamp parsing, stop inference, dedup | Pure library (`xmltv/`, executor thread) | — | CPU-bound, must not touch the loop, TDD without HA |
| Filter evaluation (channel / include / exclude) | Pure library (`xmltv/filter.py`, executor) | Calendar entity (schedules it) | Regex over 10^4–10^5 programmes is CPU work. Also reused for flow validation |
| HTTP download, local file read, gzip sniff, size caps | Integration I/O layer (`source.py`; aiohttp on the loop, file read in the executor) | — | aiohttp is async; file I/O and `is_allowed_path` are blocking |
| Refresh schedule, shared parsed data | `DataUpdateCoordinator` on the source config entry (`runtime_data`) | — | One download/parse per source, shared by all calendar subentries |
| Calendar state / `event` / `async_get_events` | `CalendarEntity` (event loop, bisect over precomputed matches) | Executor for large `CalendarEvent` batches | Reads are frequent (15-min trigger polls, dashboards); precompute on write |
| Source setup / calendar setup UI | Config flow (source), `ConfigSubentryFlow` (calendar) | Pure library (regex validation) | UI-only configuration (CFG-01) |
| Dedup of sources | Config entry `unique_id` (normalized source) | — | HA-native duplicate abort |
| Distribution / validation | GitHub Actions (hassfest, hacs/action, Ruff, pytest) | Repo structure tests (pytest) | DST-01/02 must be checkable offline as well |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Home Assistant (dev/test) | 2026.10.1 (PyPI, 2026-10-10) | Runtime under test | Pinned by phcc 0.13.372 [VERIFIED: PyPI JSON + `requires_dist` of phcc 0.13.372] |
| `hacs.json` floor | `"homeassistant": "2026.3.0"` | Minimum supported HA | First release requiring Python 3.14.2 and supporting local `brand/` [CITED: .planning/research/STACK.md]. Not tested below 2026.10.1 (see Assumptions A3) |
| Python | `requires-python = ">=3.14.2"` | Language | Matches HA's `REQUIRED_PYTHON_VER = (3, 14, 2)` [VERIFIED: HA const.py in the installed 2026.9.4 tree, sibling pyproject] |
| stdlib `xml.etree.ElementTree.iterparse`, `gzip`, `re`, `bisect`, `zlib.crc32` | Python 3.14 | Parse / filter / lookup | Zero runtime requirements (`"requirements": []`) [CITED: STACK.md; benchmarked this session] |
| `homeassistant.helpers.aiohttp_client.async_get_clientsession` | HA built-in (aiohttp 3.14.4 in HA 2026.10.1) | HTTP fetch | Shared session; `aioclient_mock` patches it in tests [VERIFIED: prototype] |

### Supporting (dev only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-homeassistant-custom-component` | `==0.13.372` (2026-10-11) | Test harness (`hass`, `aioclient_mock`, `freezer`, `MockConfigEntry`, `async_fire_time_changed`, `async_mock_service`) | All HA-layer tests. Exact pin; Renovate needs dashboard approval [VERIFIED: PyPI] |
| `ruff` | `==0.17.0` (2026-10-09) | Lint + format | `select = ["ALL"]`; config copied from mqtt-actions works with 0.17.0 unchanged [VERIFIED: ran ruff 0.17.0 with that `.ruff.toml`] |
| uv | 0.12.7 locally, 0.13.0 latest | Env + lockfile | `uv sync --locked` in CI via `astral-sh/setup-uv` [VERIFIED: `uv --version`, PyPI] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Minimal diffing listener (add/remove in place) | Reload-on-change listener (ROADMAP says "acceptable") | Reload re-downloads the whole feed (no disk cache until Phase 3) on every calendar add **and on entry rename**, and calendars go unavailable meanwhile. The diff version is about 25 lines and was verified in the prototype. Recommend diffing. |
| Lazy `CalendarEvent` construction per requested slice | Prebuilding `CalendarEvent` objects per match (ARCHITECTURE Pattern 5) | At about 34 µs each [VERIFIED: bench on 2026.10.1], prebuilding is fine for focused calendars but costs memory and CPU for "all channels" calendars. Recommend compact tuples plus lazy build, using the executor when a slice exceeds ~200 events, capped at 5,000 |
| One field "source" (URL or path) | `async_show_menu` → `url` / `file` steps | Menu = clearer UX and type-specific selectors (`TextSelectorType.URL`); single field = less code. Recommend the menu (UI hint: yes) |
| Plain normalized source as `unique_id` | SHA-256 of normalized source | EPG URLs often carry API keys in the query. A hash keeps the key out of `unique_id` and out of later diagnostics. Recommend the hash (`"url:"`/`"file:"` prefix before hashing) |

**Installation:**
```bash
uv sync                      # dev group only; no runtime deps
uv run pytest -q -m "not benchmark"
uv run ruff check . && uv run ruff format --check .
```

**Version verification:** `curl https://pypi.org/pypi/<pkg>/json`, run 2026-10-12: phcc 0.13.372 (2026-10-11T11:10Z), homeassistant 2026.10.1 (2026-10-10), ruff 0.17.0 (2026-10-09), uv 0.13.0 (2026-10-09). phcc 0.13.372 `requires_dist` includes `homeassistant==2026.10.1`, `pytest==9.0.3`, `pytest-asyncio==1.4.0`, `pytest-freezer==0.4.9`, `pytest-socket==0.8.1`, `pytest-timeout==2.4.0`, `pytest-xdist==3.8.0`.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| pytest-homeassistant-custom-component | PyPI | project since 2020-08 (579 releases); latest release 1 day old | unknown (seam) | github.com/MatthewFlamm/pytest-homeassistant-custom-component | [SUS] (`too-new`, `unknown-downloads`) | Flagged. Reason is the **release** age, not the project. Already used by all sibling repos. Planner adds `checkpoint:human-verify` before `uv sync`, or pins the sibling-vetted `0.13.367` |
| ruff | PyPI | project since 2022-08 (427 releases); latest release 3 days old | unknown (seam) | github.com/astral-sh/ruff | [SUS] (`too-new`, `unknown-downloads`) | Flagged. Same reason. Sibling uses `0.16.10`; STACK prescribes `0.17.0`. Human-verify before install |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** `pytest-homeassistant-custom-component==0.13.372`, `ruff==0.17.0`. Both are flagged only because their latest release is days old. No runtime packages are installed (`"requirements": []`). No npm packages, so the postinstall check is n/a.

## Architecture Patterns

### System Architecture Diagram

```
 User (HA UI)                                     HA core consumers
   │ Add integration                                │ calendar card / calendar.get_events /
   ▼                                                │ calendar trigger (polls every 15 min, forward-only)
 ConfigFlow (menu: url | file, name, refresh_h)     │
   │ validate: scheme / is_allowed_path (executor)  │
   │ probe: first bytes → gzip magic or '<'         │
   │ unique_id = sha256(normalized source)          │
   ▼                                                ▼
 ConfigEntry (source) ──setup──► XmltvCoordinator(config_entry=entry, interval=refresh_h)
   │  runtime_data                     │ _async_update_data
   │                                   ├─ URL: aiohttp GET (shared session, timeout, size cap) ─► bytes
   │                                   ├─ file: executor open()                                 ─► fileobj
   │                                   ▼
   │                         executor: xmltv.parser.parse(fileobj)  (gzip sniff, iterparse, root.clear,
   │                                   │                            ts parse, sanitize, dedup, stop infer)
   │                                   ▼
   │                         EpgData(channels, programmes sorted)  (eq=False, immutable)
   │                                   │ async_update_listeners
   │         ┌─────────────────────────┼──────────────────────────┐
   │         ▼                         ▼                          ▼
   │   XmltvCalendar(sub A)     XmltvCalendar(sub B)  ...  (one device per subentry)
   │     executor: FilterSpec.apply(epg) → Matches(starts[], items[], max_dur)
   │     event (live, bisect from now)   async_get_events (bisect, END-INCLUSIVE overlap)
   │
   ├─ "+ Add calendar" ► CalendarSubentryFlow (entry must be LOADED, else abort source_not_loaded)
   │        channels from runtime_data.coordinator.data.channels; regex lines compiled/validated
   │        async_create_entry ──► update listener (diff) ──► add_entities([...], config_subentry_id=…)
   └─ subentry removed ──► HA removes entity + device automatically; listener drops bookkeeping
```

### Recommended Project Structure

```
custom_components/xmltv_calendar/
├── __init__.py          # async_setup_entry / async_unload_entry / diffing update listener (no async_setup)
├── manifest.json        # domain, name, then alphabetical; requirements []; version
├── const.py             # DOMAIN, CONF_*, SUBENTRY_TYPE_CALENDAR = "calendar", defaults (24 h, min 1 h, 60 min)
├── data.py              # XmltvRuntimeData + type XmltvConfigEntry = ConfigEntry[XmltvRuntimeData]
├── source.py            # fetch_url()/open_file(): caps, timeouts, allowed-path check, normalize_source()
├── coordinator.py       # XmltvCoordinator(DataUpdateCoordinator[EpgData])
├── calendar.py          # XmltvCalendarEntity (CoordinatorEntity + CalendarEntity), platform setup
├── config_flow.py       # XmltvConfigFlow (menu → url/file) + CalendarSubentryFlow
├── translations/en.json # config + config_subentries.calendar (+ exceptions)
├── brand/icon.png       # 256x256 (+ icon@2x.png 512x512)
└── xmltv/               # PURE: no homeassistant imports (enforced by an AST test)
    ├── __init__.py
    ├── timeparse.py     # parse_xmltv_time()
    ├── model.py         # Channel, Programme (slots, frozen), EpgData (eq=False)
    ├── parser.py        # parse(fileobj, *, now, keep_after) -> EpgData; ParseStats counters
    ├── filter.py        # FilterSpec.from_config(...), compile_patterns(text) -> (patterns, error), matches()
    └── render.py        # event_title() ("{channel}: {title}"), event_description(), event_uid()
tests/
├── conftest.py          # MUST import custom_components.xmltv_calendar at module top; autouse enable_custom_integrations; TZ fixture
├── fixtures/            # synthetic *.xml, gzip-with-.xml-extension, malformed, real DE excerpt
├── xmltv/               # pure tests (no hass fixture): test_timeparse, test_parser, test_filter, test_render, test_purity
├── test_benchmark.py    # @pytest.mark.benchmark: generated 60 MB feed; time / tracemalloc / loop gap
├── test_source.py       # aioclient_mock; gzip sniff; caps; allowed paths
├── test_init.py         # setup/unload; listener add/remove; rename does not refetch
├── test_calendar.py     # overlap boundaries, live event, freezer state transitions, trigger start/end+offset
├── test_config_flow.py  # url/file steps, errors, duplicate abort, subentry flow, source_not_loaded
└── test_repo_structure.py  # manifest/hacs.json/brand/workflow pin checks (copy from mqtt-actions)
scripts/generate_benchmark_feed.py   # deterministic generator (not committed output)
.github/workflows/{ci.yml,validate.yml}   # release.yml is Phase 4
hacs.json, pyproject.toml, uv.lock, .ruff.toml, renovate.json, .gitignore, LICENSE, README.md (minimal)
```

### Pattern 1: Minimal diffing update listener (Phase 1 version)

**What:** Exactly one update listener on the source entry. If `entry.data`/`entry.options` differ from the snapshot taken at setup, schedule a reload. Otherwise reconcile subentries in place: add entities for new subentry IDs through the stored `add_entities` callback, and drop bookkeeping for removed IDs (HA already removed the entity and device). Title-only changes do nothing.
**When to use:** Always. HA fires update listeners on subentry add/remove **and on entry title changes** [VERIFIED: config_entries.py `_async_update_entry` sets `changed = True` for `title`; prototype: rename fired the listener, and the snapshot comparison kept HTTP calls at 1].
**Constraint:** With a listener registered, `ConfigSubentryFlow.async_update_reload_and_abort` raises `ValueError("Cannot update and reload entry with update listeners")` [VERIFIED: config_entries.py:4016-4018]. Any later reconfigure step must use `async_update_and_abort`. Phase 1 needs no reconfigure step (FLT-11 is Phase 2).

```python
# Source: prototype verified against HA 2026.10.1 (scratchpad), pattern from ARCHITECTURE.md Pattern 2
async def _async_entry_updated(hass: HomeAssistant, entry: XmltvConfigEntry) -> None:
    rt = entry.runtime_data
    if (dict(entry.data), dict(entry.options)) != rt.source_snapshot:
        hass.config_entries.async_schedule_reload(entry.entry_id)
        return
    for subentry_id in set(rt.calendars) - set(entry.subentries):
        rt.calendars.pop(subentry_id)            # entity + device already removed by HA
    if rt.add_entities is None:                  # platform not set up yet: its setup loop picks them up
        return
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type == SUBENTRY_TYPE_CALENDAR and subentry_id not in rt.calendars:
            entity = XmltvCalendarEntity(rt.coordinator, entry, subentry)
            rt.calendars[subentry_id] = entity
            rt.add_entities([entity], config_subentry_id=subentry_id)
```

### Pattern 2: Entity naming and device per subentry (D-10, D-11)

**What:** `_attr_has_entity_name = True`, `_attr_name = None`, `_attr_unique_id = subentry.subentry_id`, and `DeviceInfo(identifiers={(DOMAIN, subentry.subentry_id)}, name=subentry.title, entry_type=DeviceEntryType.SERVICE)`.
**Result (verified):** A subentry titled "Formel 1" yields `calendar.formel_1` with friendly name "Formel 1". The device carries `config_entry_id` + `config_subentry_id`. Removing the subentry removes the entity and the state [VERIFIED: prototype].
**Test gotcha:** `DeviceEntry.config_entries_subentries` is deprecated and **raises `RuntimeError` in tests** on 2026.10. Assert on `device.config_subentry_id` instead [VERIFIED: prototype traceback].

### Pattern 3: Calendar reads: end-inclusive overlap and live `event`

**What:** Matches are stored as compact tuples sorted by start, with a parallel `starts` list and `max_duration`.
- `async_get_events(start, end)` returns matches with `m.start < end and m.end >= start`, found with `bisect_left(starts, start - max_duration)` … `bisect_left(starts, end)`.
- `event` returns the earliest-start match with `m.end > dt_util.now()`.

**Why end-inclusive:** The trigger fetches `[span.start, span.end + 1s)` and keeps an end trigger only if `span.start <= trigger_time < span.end` (`Timespan.__contains__`, trigger.py:107-109). When a programme ends exactly at `span.start`, a strict `end > start_date` drops it from the fetch, and the previous window had already excluded it (`trigger_time < span.end` was false). The end trigger is lost. Reproduced: strict → no end call at aligned attach time; inclusive → end trigger fired. Both fired with a 7.3 s attach offset [VERIFIED: prototype under freezer]. The core `demo` calendar uses the same inclusive check (`if self._event.end_datetime_local < start_date: return []`) [VERIFIED: components/demo/calendar.py].
**Side effect:** A programme ending exactly at 00:00 is also returned for the following day's range. That is harmless for triggers, and the frontend shows it as ending at 00:00.

### Pattern 4: Coordinator update → per-calendar filtering in the executor

Follow core `remote_calendar`. `_handle_coordinator_update` schedules `config_entry.async_create_task(hass, self._async_refilter())`, which runs `FilterSpec.apply(epg)` via `hass.async_add_executor_job` and then `async_write_ha_state()`. `async_added_to_hass` does the same once [VERIFIED: components/remote_calendar/calendar.py:120-140]. Guard overlapping runs: keep only the latest by comparing a generation counter.

### Pattern 5: Source fetch for Phase 1 (no cache yet)

- **URL:** `async_get_clientsession(hass)`, `aiohttp.ClientTimeout(total=300, sock_read=60)`. Read with `stream = resp.content` (bind once; the mock's `content` property builds a new stream on each access) and `async for chunk in stream.iter_chunked(1 << 16)`, appending to a list with a **download cap** (e.g. 256 MB). Then `b"".join` → `io.BytesIO` → executor parse. Phase 3 replaces BytesIO with a cache file and the parser API (binary file object) stays the same.
- **File:** a single executor job does `is_allowed_path` + `open(path, "rb")` + parse.
- **Gzip:** peek the first 2 bytes. On `1f 8b`, wrap with `gzip.GzipFile(fileobj=…)` inside a counting reader that raises past a **decompressed cap** (e.g. 1 GiB).
- **Config-flow validation:** check the scheme (`http`/`https` only) or the path (absolute, allowed, is a file). For URLs, do a lightweight probe: GET, read up to 64 KiB, require the gzip magic or a leading `<` after BOM/whitespace, then close. Do **not** fully download/parse in the flow in Phase 1. Setup does that, and the progress step is Phase 3.

### Anti-Patterns to Avoid

- **Strict overlap `end > start_date`:** loses end triggers at window boundaries (Pattern 3).
- **Reload-on-change listener without a cache:** re-downloads on calendar add and on rename.
- **Matching against `title + "\n" + subtitle`:** breaks anchored patterns such as `^Tatort$` (the CONTEXT example). Run each pattern against each field separately.
- **`strptime("%Y%m%d%H%M%S %z")`:** `"202610122030 +0200"` parses as `20:03` [VERIFIED: probe this session].
- **Relying on HA's "Detected blocking call" warning in tests:** disabled under pytest (see Pitfall 2).
- **Using `DeviceEntry.config_entries_subentries` in tests:** raises on 2026.10.
- **Defining `async_setup`:** triggers the hassfest `CONFIG_SCHEMA` requirement. Not needed [CITED: PITFALLS.md #21].

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Periodic refresh, retries, listener fan-out | Own timers/tasks | `DataUpdateCoordinator(config_entry=entry, update_interval=…)` + `async_config_entry_first_refresh()` | `ConfigEntryNotReady` backoff, shutdown on unload, `UpdateFailed` semantics |
| HTTP session / SSL | `aiohttp.ClientSession()` | `async_get_clientsession(hass)` | Lifecycle, pooling, test patching via `aioclient_mock` |
| Path allowlist / traversal | Own prefix checks | `hass.config.is_allowed_path()` (executor) | Resolves symlinks, honours `allowlist_external_dirs` and media dirs |
| URL normalization | String lowercasing | `yarl.URL(url).with_fragment(None)` | Lowercases scheme/host, drops default port, removes dot segments [VERIFIED: probe] |
| Duplicate-entry check | Scanning entries | `async_set_unique_id` + `_abort_if_unique_id_configured` | Standard abort `already_configured` (translation provided by HA) [VERIFIED: prototype] |
| Entity removal on subentry delete | Manual registry cleanup | HA `async_remove_subentry` (clears entity + device registry) | Verified automatic |
| Calendar alarms / state | Own `async_track_point_in_time` | `CalendarEntity` base (`@final state`, alarm scheduling in `_async_write_ha_state`) | Only implement `event` + `async_get_events` |
| Streaming XML | DOM / pydantic-xml / lxml | `ET.iterparse` + `root.clear()` | 14–74 MB vs ~400 MB peak |
| Timestamp parsing | `strptime` | Reference `parse_xmltv_time()` (below) | Shortened forms, `+HH:MM`, alpha zones |

**Key insight:** Nearly all lifecycle complexity (shared resource, entity add/remove, device per subentry, retries) is already in HA's config-entry/subentry/coordinator machinery. The integration-specific risk is concentrated in the pure library (time, sanitizing, filtering) and in two calendar read semantics: end-inclusive overlap and a live `event`.

## Common Pitfalls

### Pitfall 1: Test harness can't find the custom integration
**What goes wrong:** `IntegrationNotFound: Integration 'xmltv_calendar' not found` in every HA test.
**Why it happens:** The phcc `hass` fixture points the config dir at `pytest_homeassistant_custom_component/testing_config`, whose `custom_components` is a regular package. If our namespace `custom_components` hasn't been imported yet, `import custom_components` resolves to theirs.
**How to avoid:** Add `import custom_components.xmltv_calendar  # noqa: F401` at the top of `tests/conftest.py`, plus the autouse `enable_custom_integrations` fixture. Keep **no** `custom_components/__init__.py`, matching the siblings [VERIFIED: prototype failed without the import and passed with it; mqtt-actions conftest.py:12-15 imports `custom_components.mqtt_actions` at module level].
**Warning signs:** All HA-layer tests fail at setup; the pure tests pass.

### Pitfall 2: "No blocking I/O" is unverifiable through HA's detector in tests
**What goes wrong:** An `open()` on the loop passes CI and only shows up as a warning on the real HA.
**Why it happens:** `block_async_io` skips `open` and friends in tests: `_IN_TESTS = "unittest" in sys.modules` (block_async_io.py:21) and `skip_for_tests=True` for `builtins.open` (block_async_io.py:136-143) [VERIFIED: Read + prototype (`block_async_io.enable()` + loop `open()` → no warning)].
**How to avoid:**
- Add an opt-in fixture `forbid_loop_io` (Code Examples) that wraps `builtins.open` and raises when it is called on the loop thread from `custom_components/xmltv_calendar` [VERIFIED: prototype]. Use it in source/coordinator/flow tests.
- Add the benchmark's loop-gap assertion.
- Add a code-review grep for `open(`, `gzip.`, `Path(`, `os.path` inside `async def`.

### Pitfall 3: End triggers lost at 15-minute window boundaries
See Pattern 3. **Test:** under `freezer`, attach the automation at an aligned time (e.g. `10:00:00`) with a programme ending at `14:00:00`. Step 1 minute at a time with `async_fire_time_changed` and assert the end trigger fired [VERIFIED: prototype].

### Pitfall 4: Plain-XML parse starves the event loop
**What goes wrong:** With an uncompressed 60 MB feed, event-loop heartbeat gaps reach 45–114 ms (p99) during the 1.4 s parse. With gzip the max is about 6 ms [VERIFIED: bench, 3 runs each, i5-10400H, Python 3.14.7].
**Why it happens:** The parser thread holds the GIL. It is not GC (gen2 pauses were 0; disabling GC didn't help) and not fixed by `time.sleep(0)` (tested).
**How to avoid:** Call `time.sleep(0.001)` every 250 programmes inside the parse loop. Max gap drops to ~10 ms; parse time goes 1.4 → 2.0 s [VERIFIED: bench]. Make the interval a parser kwarg so tests can set it to 0.
**Warning signs:** Benchmark loop-gap assertion; asyncio slow-callback logs.

### Pitfall 5: `CalendarEvent` construction cost on the loop
**What goes wrong:** A month view of an "all channels" calendar (tens of thousands of matches) blocks the loop for seconds.
**Why:** About **33.6 µs per `CalendarEvent`** on 2026.10.1 (probatio validation in `__post_init__`) [VERIFIED: bench, 10k constructions].
**How to avoid:** Build `CalendarEvent`s only for the requested slice. If the slice has more than about 200 items, build them in `hass.async_add_executor_job` (the core `remote_calendar` builds them in the executor). Cap at 5,000 with a debug log. Never prebuild for all matches.

### Pitfall 6: One bad programme raises in `async_get_events`
**What goes wrong:** `CalendarEvent` raises `HomeAssistantError` for `end < start` or naive datetimes [VERIFIED: probe: "Expected minimum event duration of 0:00:00", "Expected all values to have a timezone"]. `MIN_EVENT_DURATION = datetime.timedelta(seconds=0)` (calendar/helper.py:26), so zero-length events are valid.
**How to avoid:** Sanitize at parse time:
- drop programmes without a valid `start`/`channel`/`title` (count them in `ParseStats`)
- infer `stop` per D-12 when it is missing or `stop <= start` (next programme on the channel with a start greater than the current start; else +60 min)
- all datetimes tz-aware

Wrap event construction in `try/except HomeAssistantError: skip + debug log`. `async_get_events` must raise nothing but `HomeAssistantError`, and must return `[]` when there is no data yet.

### Pitfall 7: Regex input traps (Phase 1 subset)
- An empty line or empty field must not become `re.compile("")`, which matches everything. That would empty the calendar via exclude. Strip, then skip blank lines (D-05).
- Validate every line in the flow. Return `errors={"<field>": "invalid_regex"}` with `description_placeholders={"pattern": line, "error": err.msg}`. Don't assert on error **text** in tests (probatio/re wording).
- Cap the line length (e.g. 300 chars) and the number of lines (e.g. 50) as a cheap ReDoS dampener. Matching runs in the executor, so a pathological pattern stalls a worker thread, not the loop.
- Evaluate per field (title, each sub-title) with `re.search`, not `re.match`.

### Pitfall 8: Timezone-dependent tests
The phcc `hass` fixture sets `await hass.config.async_set_time_zone("US/Pacific")` (common.py:285) [VERIFIED: Read]. Tests that assert local times call `await hass.config.async_set_time_zone("Europe/Berlin")` explicitly. Pure-library tests compare in UTC. Include DST nights (2026-03-29, 2026-10-25) with explicit offsets.

### Pitfall 9: Lingering timers from automation tests
The calendar trigger keeps a 900 s interval timer. `verify_cleanup` fails the test ("Lingering timer … CalendarEventListener._handle_refresh") unless the automations are turned off at the end (`automation.turn_off` with `entity_id: all`) [VERIFIED: prototype].

### Pitfall 10: Ruff `S314` on `iterparse`
`select = ["ALL"]` flags `ET.iterparse` with S314 ("use defusedxml") [VERIFIED: ruff 0.17.0 probe]. Use a line-level `# noqa: S314` with a justification comment. ElementTree never resolves external entities, and the HA container ships Expat 2.8.1 with amplification protection [VERIFIED: `podman exec ha-a` on image `home-assistant:2026.9`: `3.14.6 expat_2.8.1`]. Don't add defusedxml (STACK.md).

### Pitfall 11: HACS/hassfest prerequisites that aren't files
- The **GitHub repository does not exist yet** (`gh repo view akentner/homeassistant-xmltv-integration` → not found) [VERIFIED].
- HACS validation needs a public repo with a description, topics and issues enabled. mqtt-actions has `custom-component, hacs, home-assistant, integration, …`.
- The user does the pushes (CLAUDE.md).

This is a `checkpoint:human-action` task. DST-02 ("every push runs CI") can only be observed after it.

### Pitfall 12: Translations for subentries
For custom integrations hassfest validates `translations/en.json` (and `strings.json` if present). Each `config_subentries.<type>` requires `entry_type`, `initiate_flow.user` and `step`. `data_description` keys must exist in the step's `data`. Placeholders must be identifiers and not inside single quotes [CITED: github.com/home-assistant/core/blob/2026.10.1/script/hassfest/translations.py]. Every `errors`/`abort` key used in code needs an entry (`invalid_regex`, `source_not_loaded`, `cannot_connect`, `invalid_url`, `path_not_allowed`, `file_not_found`, `invalid_feed`). `already_configured` comes from HA common strings, but an explicit entry is safe.

## Code Examples

### XMLTV timestamp parser (EVT-05; table-tested this session)
```python
# Source: written and run this session (17 cases pass; incl. 12-digit, +HH:MM, no space, BST, DST nights, garbage)
import re
from datetime import UTC, datetime, timedelta, timezone

_TS_RE = re.compile(
    r"^\s*(\d{4})(\d{2})(\d{2})(?:(\d{2})(\d{2})(\d{2})?)?\s*"
    r"(?:([+-])(\d{2}):?(\d{2})|(Z|UTC|GMT|[A-Z]{3,4}))?\s*$"
)
_ALPHA = {"Z": 0, "UTC": 0, "GMT": 0, "BST": 60, "CET": 60, "CEST": 120, "EET": 120, "EEST": 180}
_TZ_CACHE: dict[int, timezone] = {0: UTC}

def _tz(minutes: int) -> timezone:
    if (tz := _TZ_CACHE.get(minutes)) is None:
        tz = _TZ_CACHE[minutes] = timezone(timedelta(minutes=minutes))
    return tz

def parse_xmltv_time(value: str | None) -> datetime | None:
    """Return an aware datetime, or None if the value is not a valid XMLTV timestamp."""
    if not value or (m := _TS_RE.match(value)) is None:
        return None
    y, mo, d, h, mi, s, sign, oh, om, alpha = m.groups()
    if sign:
        minutes = int(oh) * 60 + int(om)
        tz = _tz(-minutes if sign == "-" else minutes)
    elif alpha:
        if alpha not in _ALPHA:
            return None
        tz = _tz(_ALPHA[alpha])
    else:
        tz = UTC  # D-14: no offset means UTC
    try:
        return datetime(int(y), int(mo), int(d), int(h or 0), int(mi or 0), int(s or 0), tzinfo=tz)
    except ValueError:
        return None
```

### Streaming parse loop skeleton (SRC-03, SRC-09)
```python
# Source: benchmarked this session (60 MB / 80,254 programmes: 1.4 s; tracemalloc peak ~74 MB)
def parse(fileobj: BinaryIO, *, yield_every: int = 250) -> EpgData:
    head = fileobj.read(2); fileobj.seek(0)          # BytesIO or real file: both seekable
    stream = gzip.GzipFile(fileobj=fileobj) if head == b"\x1f\x8b" else fileobj   # wrap in a size-capping reader
    events = ET.iterparse(stream, events=("start", "end"))  # noqa: S314 - ET never resolves external entities
    _, root = next(events)
    for event, elem in events:
        if event != "end":
            continue
        if elem.tag == "programme":
            ...  # extract compact fields; skip+count malformed; intern channel id
            root.clear()
            if yield_every and count % yield_every == 0:
                time.sleep(0.001)   # let the event-loop thread take the GIL (plain-XML loop gaps ~100 ms -> ~10 ms)
        elif elem.tag == "channel":
            ...  # first <display-name>, fallback id
            root.clear()
    # then: per channel sort, dedup (channel, start, title), infer stop (D-12), global sort by start
```

### Calendar subentry flow (FLT-01/02/03/04/07)
```python
# Source: prototype verified on HA 2026.10.1; API per config_entries.py ConfigSubentryFlow
class CalendarSubentryFlow(ConfigSubentryFlow):
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        entry = self._get_entry()
        if entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="source_not_loaded")      # verified with entry in SETUP_RETRY
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        if user_input is not None:
            for field in (CONF_CHANNEL_REGEX, CONF_INCLUDE, CONF_EXCLUDE):
                if (bad := first_invalid_pattern(user_input.get(field, ""))) is not None:
                    errors[field] = "invalid_regex"
                    placeholders.update(pattern=bad.pattern, error=bad.message)
            if not errors:
                return self.async_create_entry(title=user_input[CONF_NAME], data={...})
        channel_ids = sorted(entry.runtime_data.coordinator.data.channels)
        schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Optional(CONF_CHANNELS, default=[]): SelectSelector(SelectSelectorConfig(
                options=channel_ids, multiple=True, mode=SelectSelectorMode.DROPDOWN, sort=True)),
            vol.Optional(CONF_CHANNEL_REGEX, default=""): TextSelector(TextSelectorConfig(multiline=True)),
            vol.Optional(CONF_INCLUDE, default=""): TextSelector(TextSelectorConfig(multiline=True)),
            vol.Optional(CONF_EXCLUDE, default=""): TextSelector(TextSelectorConfig(multiline=True)),
        })
        return self.async_show_form(step_id="user", data_schema=self.add_suggested_values_to_schema(schema, user_input),
                                    errors=errors, description_placeholders=placeholders)
```
`SelectSelectorConfig` keys (selector.py:1921-1929): `options: Required[Sequence[SelectOptionDict] | Sequence[str]]`, `multiple: bool`, `custom_value: bool`, `mode: SelectSelectorMode`, `translation_key: str`, `sort: bool`. `TextSelectorConfig` keys (selector.py:2204-2212): `multiline: bool`, `prefix: str`, `suffix: str`, `type: TextSelectorType`, `autocomplete: str`, `multiple: bool` [VERIFIED: Read].
Use `import voluptuous as vol`. HA ≥2026.9 aliases it to probatio (`homeassistant/__init__.py` calls `install_as_voluptuous()`), and on the 2026.3 floor it is real voluptuous [VERIFIED: grep homeassistant/__init__.py:5-11]. Don't list it in `requirements`.

### Test harness essentials
```python
# tests/conftest.py  (Source: prototype + mqtt-actions conftest.py:12-15)
import builtins, sys, threading
import pytest
import custom_components.xmltv_calendar  # noqa: F401  # must precede the hass fixture (Pitfall 1)

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow loading custom_components in every test."""

@pytest.fixture
def forbid_loop_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail when integration code calls open() on the event-loop thread (HA's detector is off in tests)."""
    loop_thread = threading.get_ident()
    real_open = builtins.open
    def guarded(*args, **kwargs):
        if threading.get_ident() == loop_thread and "custom_components/xmltv_calendar" in sys._getframe(1).f_code.co_filename:
            raise AssertionError("blocking open() on the event loop")
        return real_open(*args, **kwargs)
    monkeypatch.setattr(builtins, "open", guarded)
```

```python
# Calendar trigger test pattern (Source: prototype; start+offset fired at 11:55, state on 12:00 / off 14:00)
calls = async_mock_service(hass, "test", "automation")
assert await async_setup_component(hass, "automation", {"automation": [
    {"triggers": [{"trigger": "calendar", "event": "start", "offset": "-0:05:00", "entity_id": "calendar.formel_1"}],
     "actions": [{"action": "test.automation", "data": {"summary": "{{ trigger.calendar_event.summary }}"}}]},
    {"triggers": [{"trigger": "calendar", "event": "end", "entity_id": "calendar.formel_1"}],
     "actions": [{"action": "test.automation", "data": {"location": "{{ trigger.calendar_event.location }}"}}]},
]})
for _ in range(4 * 60 + 10):              # step 1 minute at a time; coarse jumps skip trigger windows
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
await hass.services.async_call("automation", "turn_off", {"entity_id": "all"}, blocking=True)  # Pitfall 9
```
Calendar trigger registry (trigger.py:499-503): `"_": SingleEntityEventTrigger`, `"event_started": EventStartedTrigger`, `"event_ended": EventEndedTrigger` [VERIFIED: Read]. Use the legacy `trigger: calendar` form (`"_"`) in tests; it's the documented, stable form.

```python
# get_events (Source: prototype)
res = await hass.services.async_call("calendar", "get_events",
    {"entity_id": "calendar.formel_1", "start_date_time": "2026-10-13T13:00:00+00:00", "duration": {"hours": 1}},
    blocking=True, return_response=True)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `DeviceEntry.config_entries_subentries` | `DeviceEntry.config_entry_id` + `config_subentry_id` | deprecated in 2026.x (breaks 2027.10) | Raises in tests today [VERIFIED: prototype] |
| `import voluptuous` = real voluptuous | Aliased to probatio by `homeassistant/__init__.py` | 2026.9 | Keep `import voluptuous as vol` for the 2026.3 floor |
| Calendar trigger `platform: calendar` only | Plus targeted `calendar.event_started` / `event_ended` triggers | 2026.x (TRIGGERS map) | Both call `async_get_events`; same overlap requirement |
| `async_update_reload_and_abort` with a listener | Raises `ValueError` | current | Use `async_update_and_abort` when a listener exists |
| `next_flow` to a subentry flow from `async_create_entry` | Only `FlowType.CONFIG_FLOW`; subentry chaining needs `async_on_create_entry` | current | Don't chain "add first calendar" in Phase 1 (optional UX, not required) |

**Deprecated/outdated:** `OptionsFlowWithReload` together with listeners (not used in Phase 1). Strict overlap guidance in PITFALLS.md #7 is **superseded** by Pattern 3.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A real German XMLTV excerpt can be obtained and committed without licensing issues (iptv-org no longer hosts prebuilt guides; epgshare01 is a third-party mirror) | D-15 / Open Questions | Excerpt must be replaced by a self-generated or user-supplied one. Needs a human checkpoint |
| A2 | `ha-host` (x86 OptiPlex) parses a 60 MB feed in the same order of magnitude as the dev box (1.4–2 s) | SRC-09 | If much slower, the loop-yield interval and refresh UX need retuning. Benchmark numbers are from an i5-10400H only |
| A3 | All APIs used work on the `hacs.json` floor 2026.3.0 (subentries 2025.3, `config_subentry_id` 2025.3, calendar triggers) | Standard Stack | Tests only run on 2026.10.1; a 2026.3 user could hit an API gap. Mitigation: raise the floor to the tested version, or accept |
| A4 | Frontend multi-select dropdown with thousands of channel IDs is usable (fuzzy search + virtualization) | FLT-02 | Verified on the frontend `dev` branch source only, not on the 2026.10 release build; manual check on `ha-dev` with the large feed |
| A5 | `cloud_polling` is the right `iot_class` (core `remote_calendar` precedent; most feeds are internet URLs) | manifest | Cosmetic only; `local_polling` would fit file sources better |
| A6 | Caps (download 256 MB, decompressed 1 GiB, regex line 300 chars / 50 lines, event slice 5,000) are sensible defaults | Patterns / Security | Too low rejects legit huge feeds; tune after real feeds |
| A7 | UID format `"{channel_id}-{start_utc:%Y%m%dT%H%M%SZ}-{crc32(title):08x}"` is stable enough | EVT-06 | A title correction in the feed changes the UID (acceptable: it is a different event) |

## Open Questions

1. **Real German feed excerpt (D-15)**
   - What we know: iptv-org/epg no longer publishes prebuilt guides; community mirrors (epgshare01) exist with unclear licensing.
   - What's unclear: which source the user wants, and whether redistributing an excerpt in a public repo is acceptable.
   - Recommendation: a human checkpoint task. The user supplies a feed (e.g. their own 18:00 source), the executor trims it to ~5 channels × 1–2 days, and the user approves before commit. Until then the synthetic fixtures carry all tests.
2. **GitHub repository creation (DST-01/02)**
   - What we know: the repo doesn't exist; pushes are user-only.
   - Recommendation: a `checkpoint:human-action` task covering create public repo `akentner/homeassistant-xmltv-integration`, description, topics (`hacs`, `home-assistant`, `custom-component`, `integration`, `xmltv`, `epg`, `calendar`), enable issues, push, confirm CI green, add as a HACS custom repository on `ha-dev`.
3. **Floor vs tested version**
   - Recommendation: keep `2026.3.0` per STACK (user decision), but note A3. Alternatively, set the floor to `2026.10.0` to match what is tested. Ask only if the planner sees a cheap way to test 2026.3; otherwise keep.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | all | ✓ | 3.14.7 | — |
| uv | env/lock | ✓ | 0.12.7 (latest 0.13.0) | works; CI uses setup-uv |
| phcc + HA 2026.10.1 | tests | ✓ (installs from PyPI; verified in scratch venv) | 0.13.372 | — |
| podman | manual UAT (`ha-dev`, D-16) | ✓ | 6.1.3 | — (`ha-dev` container currently not running; `ha-a`/`ha-b` 2026.9 belong to mqtt-actions) |
| `~/Projects/dev/compose.yml` | D-16 | ✓ | image `stable` | Needs two new volume lines (component mount + `/media` fixtures mount) |
| gh CLI | repo creation (human) | ✓ | 2.102.0 | — |
| rsvg-convert / magick / inkscape | brand icon PNG 256/512 | ✓ | — | — |
| GitHub repo | DST-01/02 | ✗ | — | **Blocking for CI observation**: human creates it |
| Real DE feed | D-15 | ✗ | — | Synthetic fixtures until user supplies one |

**Missing dependencies with no fallback:** GitHub repository (human action required before DST-01/02 can be verified).
**Missing dependencies with fallback:** real DE feed excerpt (synthetic fixtures meanwhile).

## Validation Architecture

> `workflow.nyquist_validation` is `false` in `.planning/config.json`, but the orchestrator explicitly requested this section (TDD mode `tdd_mode: true`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.4.0 via `pytest-homeassistant-custom-component==0.13.372` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`: `asyncio_mode = "auto"`, `testpaths = ["tests"]`, `addopts = "--strict-markers"`, `markers = ["benchmark: generates a 60 MB feed; slow"]` (none yet; Wave 0) |
| Quick run command | `uv run pytest -q -x -m "not benchmark" tests/xmltv` (pure library, < 2 s) |
| HA-layer run | `uv run pytest -q -m "not benchmark"` |
| Full suite command | `uv run pytest -q && uv run ruff check . && uv run ruff format --check .` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SRC-01 | URL step creates entry; invalid scheme → `invalid_url`; unreachable → `cannot_connect` | HA flow | `uv run pytest tests/test_config_flow.py -k url -x` | ❌ Wave 0 |
| SRC-02 | File step: allowed path ok; disallowed → `path_not_allowed`; missing → `file_not_found` (set `hass.config.allowlist_external_dirs = {str(tmp_path)}`) | HA flow | `uv run pytest tests/test_config_flow.py -k file -x` | ❌ |
| SRC-03 | gzip bytes behind `.xml` URL/file parse; plain behind `.gz` name parses | unit + HA | `uv run pytest tests/xmltv/test_parser.py tests/test_source.py -k gzip -x` | ❌ |
| SRC-04 | Coordinator `update_interval == timedelta(hours=refresh)`; default 24, min 1 enforced by selector/schema | HA | `uv run pytest tests/test_init.py -k interval -x` | ❌ |
| SRC-09 | 60 MB generated feed: parse < 30 s (CI), tracemalloc peak < 150 MB, loop heartbeat max gap < 250 ms (CI-generous; dev ~10 ms) | benchmark | `uv run pytest -m benchmark -q` | ❌ |
| SRC-13 | Same normalized URL/path twice → abort `already_configured` (case/default-port/fragment variants) | HA flow + unit (`normalize_source`) | `uv run pytest tests/test_config_flow.py -k duplicate -x` | ❌ |
| FLT-01 | Two subentries → two entities, one HTTP call total; adding a third doesn't refetch; removing deletes entity | HA | `uv run pytest tests/test_init.py -k subentry -x` | ❌ |
| FLT-02 | Selector options = feed channel IDs; empty selection = all; unknown selected ID ignored + warning once | HA flow + unit | `uv run pytest tests/test_config_flow.py tests/xmltv/test_filter.py -k channel -x` | ❌ |
| FLT-03/04 | Truth table channel × include × exclude, per-field matching, `^Tatort$` on title, IGNORECASE, umlauts | unit | `uv run pytest tests/xmltv/test_filter.py -x` | ❌ |
| FLT-07 | Invalid line → form error on that field; blank lines ignored; empty exclude excludes nothing | unit + HA flow | `uv run pytest tests/xmltv/test_filter.py tests/test_config_flow.py -k regex -x` | ❌ |
| EVT-01 | Exact duplicates collapsed; non-identical overlaps kept | unit | `uv run pytest tests/xmltv/test_parser.py -k dedup -x` | ❌ |
| EVT-02 | location = first display-name; fallback channel id | unit | `uv run pytest tests/xmltv/test_render.py -x` | ❌ |
| EVT-05 | Timestamp table (17+ cases); stop inference; `stop <= start`; malformed programme skipped without failing parse | unit | `uv run pytest tests/xmltv/test_timeparse.py tests/xmltv/test_parser.py -x` | ❌ |
| EVT-06 | UID identical across two parses of the same feed and after reordering the file | unit | `uv run pytest tests/xmltv/test_render.py -k uid -x` | ❌ |
| AUT-01 | Trigger start with offset and end (aligned window boundary) fire; `get_events` overlap boundaries (end == start_date included, start == end_date excluded) | HA (freezer) | `uv run pytest tests/test_calendar.py -k "trigger or overlap" -x` | ❌ |
| AUT-02 | State on/off at programme start/end without refresh; attributes message/location/start/end | HA (freezer) | `uv run pytest tests/test_calendar.py -k state -x` | ❌ |
| CFG-01 | Full setup through flows only; no `async_setup`/YAML schema | HA flow | covered by the flow tests above | ❌ |
| DST-01 | manifest keys/order/version, hacs.json keys + floor, brand icon PNG ≥256, single folder in `custom_components` | structure | `uv run pytest tests/test_repo_structure.py -x` | ❌ |
| DST-02 | Workflows exist, SHA-pinned actions, single pinned runner, jobs for ruff/pytest/hassfest/hacs | structure (+ manual: green run on GitHub) | `uv run pytest tests/test_repo_structure.py -k workflow -x` | ❌ |
| (purity) | `xmltv/` has no `homeassistant` imports | structure (AST) | `uv run pytest tests/xmltv/test_purity.py -x` | ❌ |
| (loop I/O) | source/coordinator/flow never `open()` on the loop | HA with `forbid_loop_io` | part of `test_source.py` / `test_config_flow.py` | ❌ |

**Manual-only (end-of-phase UAT, `human_verify_mode: end-of-phase`):**
- add a source via URL and via `/media` file on `ha-dev`
- channel picker usability with the large feed
- a real automation firing
- HACS "custom repository" install from GitHub

Justification: these need the real frontend, the real container and a GitHub remote.

### Sampling Rate
- **Per task commit:** `uv run pytest -q -x -m "not benchmark"` (+ `ruff check` on touched files)
- **Per wave merge:** `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`
- **Phase gate:** full suite incl. `-m benchmark` green locally; CI green on GitHub (after the human push), then `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `pyproject.toml`, `uv.lock`, `.ruff.toml` (copy mqtt-actions + `benchmark` marker), `.gitignore` (merge mqtt-actions entries with the existing `.planning/research/.cache/`)
- [ ] `tests/conftest.py`: module-level integration import, autouse `enable_custom_integrations`, `forbid_loop_io`, Berlin-TZ helper fixture
- [ ] `tests/fixtures/*.xml` synthetic edge cases + gzip-with-`.xml` fixture (generate in a test helper or commit small binary)
- [ ] `scripts/generate_benchmark_feed.py` + session fixture writing to `tmp_path_factory`
- [ ] `tests/test_repo_structure.py` (adapt mqtt-actions: domain `xmltv_calendar`, floor `2026.3.0`, workflows `ci.yml`/`validate.yml`)
- [ ] Framework install: `uv sync` (after the human-verify checkpoint for the SUS-flagged dev packages)

## Security Domain

`security_enforcement: true`, ASVS level 1, block on high.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No credentials in Phase 1 (URL tokens only via query string) |
| V3 Session Management | no | — |
| V4 Access Control | yes (file access) | `hass.config.is_allowed_path()` in the executor (resolves symlinks); default allowlist = `config/www` + media dirs (`/media` on Container) |
| V5 Input Validation | yes | URL scheme allowlist (`http`/`https`), `yarl` normalization; regex compile per line with length/count caps; `NumberSelector` bounds (1..168 h); XML sanitizing per programme |
| V6 Cryptography | minimal | SHA-256 (`hashlib`) for the `unique_id` hash only; never hand-roll |
| V7 Error Handling & Logging | yes | Log host only, never the full URL (query may hold API keys); log parse error positions, never content excerpts |
| V12 Files & Resources | yes | Download cap + decompressed cap (gzip bomb); `ClientTimeout`; Expat entity-expansion protection (2.8.1 in the HA container) |
| V14 Configuration | yes | `"requirements": []`; SHA-pinned GitHub Actions; `permissions: {}` at workflow level; `persist-credentials: false` |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Arbitrary file read via the "local file" path (`/config/secrets.yaml`) | Information disclosure | `is_allowed_path` in the flow **and** at setup; error key only, no content echo |
| Gzip / XML decompression bomb | Denial of service | Counting reader with a decompressed cap → `UpdateFailed`; Expat amplification protection |
| Huge or slow download | DoS | `ClientTimeout(total, sock_read)`, byte cap while streaming |
| ReDoS via user regex | DoS (executor thread) | Matching only in the executor; pattern length/count caps; flow validation |
| API key in URL leaks via logs / unique_id | Information disclosure | Hash in `unique_id`; log `yarl.URL(url).host` only (diagnostics redaction is Phase 3) |
| SSRF to internal hosts via URL | Tampering / info disclosure | Accepted: admin-only config flow, same trust as other HA URL integrations (e.g. `remote_calendar`); only http/https schemes |
| Supply chain in CI | Tampering | SHA-pinned actions (copy mqtt-actions), Renovate digest updates, structure test enforcing pins |

## Sources

### Primary (HIGH confidence)
- Installed HA **2026.10.1** source (scratch venv via phcc 0.13.372): `config_entries.py` (FlowType 337-343, ConfigSubentryData 355-365, ConfigSubentryFlow 3882-4060, `_async_update_entry` 2706-2811, update-and-reload ValueError 4016-4018, `async_create_entry(options, subentries, next_flow)` 3568-3598), `components/calendar/{__init__,helper,trigger}.py`, `helpers/selector.py`, `helpers/entity_platform.py` (`config_subentry_id`), `helpers/update_coordinator.py`, `core_config.py` (437-444, `is_allowed_path`, `cache_path`), `block_async_io.py` (21, 136-143), `components/remote_calendar/*`, `components/demo/calendar.py`, `homeassistant/__init__.py` (probatio alias)
- phcc 0.13.372 `common.py:285`, `plugins.py` (fixtures, `disable_block_async_io`), `test_util/aiohttp.py`
- Prototype integration + tests run this session (subentry flow, dynamic add, naming/device, removal, rename, not-loaded abort, triggers, get_events, overlap boundary, loop-IO guard, import trap)
- Benchmarks run this session (parse time / tracemalloc / loop gaps / GIL yield / GC check / CalendarEvent cost)
- PyPI JSON API (versions, `requires_dist`), `gh repo view`, `gh run list` (mqtt-actions Validate green 2026-10-12), `podman exec ha-a` (Python 3.14.6, Expat 2.8.1)
- Sibling repo files: mqtt-actions `pyproject.toml`, `.ruff.toml`, `hacs.json`, `renovate.json`, workflows, `manifest.json`, `tests/conftest.py`, `tests/test_repo_structure.py`; kroki `config_flow.py` subentry flow; `~/Projects/dev/compose.yml`

### Secondary (MEDIUM confidence)
- github.com/home-assistant/core/blob/2026.10.1/script/hassfest/translations.py (config_subentries required keys), via WebFetch
- github.com/home-assistant/frontend (dev): `ha-selector-select.ts`, `ha-generic-picker.ts`, `ha-picker-combo-box.ts` (multi-select → generic picker, Fuse search, virtualized list > 12 items), via WebFetch
- Project research `.planning/research/*.md` (baseline)

### Tertiary (LOW confidence)
- WebSearch: iptv-org no longer hosts prebuilt guides; epgshare01 third-party mirror (community posts) — [Arch Wiki: Iptv.org EPG Grabber](https://wiki.archlinux.org/title/Iptv.org_EPG_Grabber), [Channels community: IPTV.org / EPG Setup](https://community.getchannels.com/t/iptv-org-epg-setup/38044), [Emby: Other Sources of EPG Guide Data](https://emby.media/support/articles/Live-TV-EPG-Other.html)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (PyPI-verified versions; config copied from a sibling with green CI)
- Architecture: HIGH (prototype executed on the target HA version)
- Pitfalls: HIGH for 1–3, 5, 6, 8–10 (reproduced); MEDIUM for 4 (single machine) and 12 (WebFetch of hassfest)

**Research date:** 2026-10-12
**Valid until:** 2026-11-12 (HA monthly release cadence; re-check if phcc is bumped past 2026.10.x)
