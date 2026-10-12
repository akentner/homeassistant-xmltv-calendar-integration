# Architecture Research

**Domain:** Home Assistant custom integration (HACS): XMLTV EPG feed turned into filtered `calendar.*` entities
**Researched:** 2026-10-12
**Confidence:** HIGH for HA API facts (checked against `home-assistant/core` source on the `dev` branch, 2026.11.0.dev, and release tags); MEDIUM for the recommended structure (design judgement based on core precedent)

---

## TL;DR: Recommended Shape

**One parent config entry per XMLTV source, plus one config subentry per calendar (filter set).**

- Parent entry: the source (URL or file path) and its refresh interval. It owns one `DataUpdateCoordinator` that downloads and parses the feed once, stored in `entry.runtime_data`.
- Subentries of type `calendar`: one per filter set, holding channels, include/exclude regex and the title template. Each subentry gets one `CalendarEntity`, added with `config_subentry_id=...`.
- The update listener applies a diff. A change to the source causes a full reload. Adding, removing or editing a calendar subentry updates entities in place, with no re-download or re-parse.
- A raw-file disk cache in `hass.config.cache_path(DOMAIN)` lets HA restarts and source reloads skip the network when the cached copy is still fresh.

This uses HA's own mechanism for "several configurations sharing one expensive resource". The February 2025 subentries blog post describes exactly that case (MQTT broker, cloud account), and `openai_conversation`, `google_generative_ai_conversation` and `anthropic` all use it as "parent = API client, subentries = agents". There is no global `hass.data` registry, no ref-counting and no cross-entry lifecycle coupling.

**Needs user sign-off:** PROJECT.md currently says "one calendar entity per config entry". Under this design that becomes "one calendar per *subentry*". The user experience is: add the integration once per source, then use "+ Add calendar" on the integration card. The flat-entries alternative (a ref-counted shared registry) is fully specified below in case the user prefers it.

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       HA UI / Calendar consumers                         │
│   Config Flow   Options Flow   Subentry Flow     Calendar card  Triggers │
│   (source)      (source)       (calendar add/    (range query)  (15-min  │
│                                 reconfigure)                    windows) │
└──────┬─────────────┬──────────────┬──────────────────┬───────────┬───────┘
       │             │              │                  │           │
       ▼             ▼              ▼                  ▼           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Parent ConfigEntry  (one per source; unique_id = normalized source)     │
│  entry.runtime_data = XmltvRuntimeData                                   │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ XmltvCoordinator (DataUpdateCoordinator[EpgData], config_entry=e)  │  │
│  │   _async_update_data:                                              │  │
│  │     SourceFetcher.fetch() ──► unchanged? return self.data          │  │
│  │                         └──► changed: executor(parse_xmltv(path))  │  │
│  └───────────────┬────────────────────────────────────────────────────┘  │
│                  │ listeners (one per calendar)                          │
│     ┌────────────┼──────────────────────┬────────────────────────┐       │
│     ▼            ▼                      ▼                        │       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │       │
│  │ XmltvCalendar   │  │ XmltvCalendar   │  │ XmltvCalendar   │ ◄─┘       │
│  │ (subentry A)    │  │ (subentry B)    │  │ (subentry C)    │           │
│  │ FilterSpec A    │  │ FilterSpec B    │  │ FilterSpec C    │           │
│  │ matches: sorted │  │ matches: sorted │  │ matches: sorted │           │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘           │
└──────────────────────────────────────────────────────────────────────────┘
       │ uses (pure, no HA imports)
       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Domain library (runs in the executor, unit-testable without HA)         │
│   xmltv/parser.py  (streaming iterparse, then EpgData)                   │
│   filter.py        (FilterSpec: compile, match, render title/desc)       │
└──────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  I/O: aiohttp shared session (HTTP/S)  ·  local file (allowlisted path)  │
│       disk cache: hass.config.cache_path(DOMAIN, "<entry_id>.xml[.gz]")  │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Owns | Talks to | Implementation |
|-----------|------|----------|----------------|
| `xmltv/parser.py` | Turning XMLTV bytes or files into immutable `EpgData` | nothing (pure) | `xml.etree.ElementTree.iterparse` (C-accelerated) over `gzip.open()` or `open()`, `elem.clear()` after each `<programme>`, timestamps parsed to aware UTC `datetime`, past programmes dropped. Has no HA imports. |
| `xmltv/model.py` | `Channel`, `Programme`, `EpgData` | nothing | `@dataclass(frozen=True, slots=True)`. `EpgData` uses `eq=False` (see anti-pattern 6). Programmes sorted by start, plus a `channels: dict[id, Channel]` map. |
| `filter.py` | `FilterSpec` (channel set, compiled include/exclude regex, fields to match, title template) and the resulting `Match` list | `EpgData` (read-only) | Pure. `FilterSpec.from_subentry_data()` compiles once. `apply(epg) -> list[CalendarEvent-ready tuples]`. Title rendered with `str.format_map` over whitelisted keys (not Jinja). |
| `source.py` (`SourceFetcher`) | Getting fresh bytes onto disk: URL or local path, conditional GET (ETag / Last-Modified), gzip detection by magic bytes, disk cache, path allowlist check | aiohttp session, filesystem (via executor) | Async. Returns a `FetchResult(path, changed: bool, fingerprint)`. Never parses. |
| `coordinator.py` (`XmltvCoordinator`) | Refresh schedule (= the source's refresh interval), the current `EpgData`, error state | `SourceFetcher`, parser (via executor), listeners | `DataUpdateCoordinator[EpgData]` with `config_entry=parent_entry`. Raises `UpdateFailed` on fetch or parse errors and keeps the last good data. |
| `calendar.py` (`XmltvCalendarEntity`) | One filter set's matches; `event` (current or next); `async_get_events` | coordinator (listener), `filter.py` (via executor) | `CoordinatorEntity[XmltvCoordinator]` + `CalendarEntity`. Recomputes matches on each coordinator update and stores them sorted by start. Reads use `bisect`. |
| `__init__.py` | Entry lifecycle: setup, unload, update listener (diff), remove (delete cache), migrate | everything above | `type XmltvConfigEntry = ConfigEntry[XmltvRuntimeData]` |
| `config_flow.py` | `ConfigFlow` (source), `OptionsFlow` (source options), `CalendarSubentryFlow` (user + reconfigure) | `SourceFetcher` + parser (validation), parent `runtime_data` (channel list) | Selectors: `SelectSelector(multiple=True)` for channels, `TextSelector` for regex and template. |
| `diagnostics.py` | Diagnostics download | runtime_data | Redact the source URL (EPG providers often put API keys in the query string). |

---

## Recommended Project Structure

```
custom_components/xmltv_calendar/
├── __init__.py            # setup/unload/update-listener/remove/migrate; runtime_data wiring
├── manifest.json          # config_flow: true, integration_type: "service", iot_class: "cloud_polling"
├── const.py               # DOMAIN, CONF_* keys, SUBENTRY_TYPE_CALENDAR, defaults
├── data.py                # XmltvRuntimeData dataclass + XmltvConfigEntry type alias
├── source.py              # SourceFetcher (HTTP/file, conditional GET, gzip sniff, disk cache)
├── coordinator.py         # XmltvCoordinator(DataUpdateCoordinator[EpgData])
├── filter.py              # FilterSpec, matching, title/description rendering (pure)
├── calendar.py            # XmltvCalendarEntity, platform async_setup_entry
├── config_flow.py         # ConfigFlow, OptionsFlow, CalendarSubentryFlow
├── diagnostics.py         # redacted diagnostics
├── strings.json           # config, options, config_subentries.calendar, exceptions
├── translations/{en,de}.json
└── xmltv/                 # pure domain library: NO homeassistant imports
    ├── __init__.py
    ├── model.py           # Channel, Programme, EpgData
    └── parser.py          # parse_xmltv(path, *, keep_from) -> EpgData
tests/
├── fixtures/              # small.xml, small.xml.gz, tz-edge.xml, malformed.xml, large-generated (script)
├── xmltv/test_parser.py   # plain pytest, no HA
├── test_filter.py         # plain pytest, no HA
├── test_source.py         # aioclient_mock / aresponses
├── test_init.py           # pytest-homeassistant-custom-component, MockConfigEntry(subentries_data=...)
├── test_calendar.py
└── test_config_flow.py
hacs.json                  # { "name": ..., "homeassistant": "2026.3.0" }
pyproject.toml             # uv, ruff (line-length 120), pytest
.github/workflows/         # hassfest, hacs/action, pytest
```

### Structure Rationale

- **`xmltv/` has no HA imports.** The parser is the riskiest and most performance-sensitive code. Keeping it pure allows fast TDD with fixtures (`tdd_mode: true` in config), benchmarking against a 50+ MB generated file without HA, and makes it obvious that it is safe to run in the executor (no event-loop calls).
- **`filter.py` is pure too.** The config flow can then use the same code for validation and a "N matches" preview, and the entity reuses it.
- **`source.py` is separate from `coordinator.py`.** The coordinator only orchestrates. Fetch semantics (304, gzip, file vs URL, cache) are tested in isolation with mocked HTTP.
- **`data.py` holds the runtime_data type.** This avoids circular imports between `__init__.py`, `calendar.py` and `config_flow.py`, the usual problem in HA integrations.
- **Domain name `xmltv_calendar`.** It avoids colliding with the existing HACS integration `xmltv_epg` (shadow578), which provides sensors per channel. Other names are fine as long as they don't collide.

---

## Architectural Patterns

### Pattern 1: Parent entry (source) with calendar subentries (RECOMMENDED)

**What:** The parent `ConfigEntry` represents the expensive shared resource. Its `ConfigSubentry` items are the cheap consumers. The coordinator is created with `config_entry=entry`, so HA ties its lifecycle to the parent: `async_on_unload(self.async_shutdown)` is registered automatically in `DataUpdateCoordinator.__init__`.

**When to use:** Many consumers share one resource and each consumer has independent settings. This is the stated purpose of subentries.

**Verified API facts:**
- `ConfigSubentryFlow` and `async_get_supported_subentry_types` exist from **HA 2025.3** (absent in 2025.2.0). Subentry `reconfigure` (`_get_reconfigure_subentry()`) is also in 2025.3.
- `async_add_entities(entities, config_subentry_id=subentry_id)` ties entities to a subentry. The platform validates that the subentry belongs to the entry.
- Adding, updating or removing a subentry goes through `ConfigEntries._async_update_entry`, which **fires the entry's update listeners**.
- Removing a subentry automatically calls `entity_registry.async_clear_config_subentry`, which removes its entities. The integration does not need to clean them up.
- Subentry unique IDs only have to be unique within their parent entry.
- From HA 2026.8 a device belongs to exactly one config entry and at most one subentry. If you create devices, create **one device per calendar subentry** (`DeviceEntryType.SERVICE`, identifiers `{(DOMAIN, subentry_id)}`). Do not share one device across subentries.

**Trade-offs:**
- Pro: Uses HA's native model. There is no global state, `async_config_entry_first_refresh` works (see Pattern 3), and the refresh interval sits naturally on the source as PROJECT.md wants.
- Pro: The calendar subentry flow can read the channel list from the already-loaded coordinator (`self._get_entry().runtime_data.coordinator.data.channels`). The 50 MB file is never fetched inside a flow.
- Pro: Deduplicating sources is just `await self.async_set_unique_id(normalize(source)); self._abort_if_unique_id_configured()`.
- Con: Users must add the source before they can add calendars (two steps). A calendar cannot move to a different source; delete and recreate it.
- Con: A naive "reload on any change" listener re-parses the whole feed on every filter edit. Pattern 2 avoids this.
- Con: If the parent failed to load (source unreachable), the subentry flow has no channel list. Abort with `source_not_loaded`, or fall back to free-text channel IDs.

**Example:**
```python
# data.py
@dataclass
class XmltvRuntimeData:
    coordinator: XmltvCoordinator
    source_snapshot: tuple[MappingProxyType, MappingProxyType]       # (data, options) at setup
    calendars: dict[str, XmltvCalendarEntity] = field(default_factory=dict)  # subentry_id -> entity
    add_entities: AddConfigEntryEntitiesCallback | None = None

type XmltvConfigEntry = ConfigEntry[XmltvRuntimeData]

# __init__.py
async def async_setup_entry(hass: HomeAssistant, entry: XmltvConfigEntry) -> bool:
    fetcher = SourceFetcher(hass, entry)
    coordinator = XmltvCoordinator(hass, entry, fetcher)        # config_entry=entry inside
    await coordinator.async_config_entry_first_refresh()       # raises ConfigEntryNotReady
    entry.runtime_data = XmltvRuntimeData(coordinator, (entry.data, entry.options))
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.CALENDAR])
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: XmltvConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, [Platform.CALENDAR])

async def async_remove_entry(hass: HomeAssistant, entry: XmltvConfigEntry) -> None:
    await hass.async_add_executor_job(remove_cache_files, hass, entry.entry_id)

# calendar.py
async def async_setup_entry(hass, entry: XmltvConfigEntry, async_add_entities) -> None:
    rt = entry.runtime_data
    rt.add_entities = async_add_entities
    for sub in entry.subentries.values():
        if sub.subentry_type == SUBENTRY_TYPE_CALENDAR:
            ent = XmltvCalendarEntity(rt.coordinator, entry, sub)
            rt.calendars[sub.subentry_id] = ent
            async_add_entities([ent], config_subentry_id=sub.subentry_id)
```

### Pattern 2: Diffing update listener (no reload for filter edits)

**What:** A single update listener on the parent entry:
1. If `entry.data` or `entry.options` differ from `source_snapshot`, the source changed. Call `hass.config_entries.async_schedule_reload(entry.entry_id)`; a full reload is correct here.
2. Otherwise only subentries changed:
   - **added** subentry IDs: create the entity and call `rt.add_entities([...], config_subentry_id=sid)`.
   - **removed** subentry IDs: HA already removed the entity. Drop it from `rt.calendars`.
   - **changed** subentries (data or title differ): call `entity.async_apply_subentry(sub)`, which recompiles the `FilterSpec`, re-filters in the executor and writes state.

**When to use:** Always in this design. Re-parsing 50+ MB is seconds of CPU and hundreds of MB of RAM; doing that for a regex tweak is unacceptable, particularly on an Odroid N2+.

**Critical constraint (verified in `config_entries.py`):** `OptionsFlowWithReload` (HA 2025.8+) raises `ValueError("Config entry update listeners should not be used with OptionsFlowWithReload")` if the entry has an update listener. Because this design needs a listener for subentry diffs, the source options flow **must be a plain `OptionsFlow`**. The listener detects the options change and schedules the reload itself.

**Trade-offs:** About 40 more lines than "reload on any change" (the pattern `openai_conversation` uses, which works because reloading is cheap there). Edge case: a subentry added while the entity platform isn't loaded yet (`rt.add_entities is None`). The platform setup loop picks it up, so just return.

**Fallback if this proves fiddly:** Use "reload on any change" together with the disk cache. A reload then costs a re-parse but no download. That is acceptable for v1 if the parse time of the target feed is under about 5 s on the target host. Measure before deciding.

### Pattern 3: Coordinator owned by the parent entry (`config_entry=entry`)

**What:** Pass the parent entry explicitly. This gives you:
- automatic `async_shutdown` on unload (registered in `DataUpdateCoordinator.__init__`)
- `async_config_entry_first_refresh()`, which converts failures into `ConfigEntryNotReady` so HA retries with backoff and avoids log spam

**Verified constraints (`helpers/update_coordinator.py`):**
- `async_config_entry_first_refresh` raises `ConfigEntryError` if `config_entry is None`, or if the entry is not in `SETUP_IN_PROGRESS`.
- Not passing `config_entry` at all (`UNDEFINED`) falls back to a ContextVar. Core reports this as an error; custom integrations are currently ignored. Pass it explicitly anyway.
- A coordinator with `config_entry=None` must call `async_register_shutdown()` itself and cannot use first-refresh. This matters for the alternative pattern below.

**Stale-while-revalidate on startup:** Inside `_async_update_data`, when `self.data is None` (first run) and a disk-cached file exists, parse the cached file first so entities become available quickly without network. If the cache is older than the refresh interval, follow up with `self.async_request_refresh()` / `entry.async_create_background_task(...)`. This also keeps setup from being blocked by a slow 50 MB download at HA boot.

### Pattern 4: Executor boundary = the domain library

**What:** Everything CPU-bound or doing blocking I/O runs via `hass.async_add_executor_job(...)`:

| Work | Where | Why |
|------|-------|-----|
| HTTP download | event loop (aiohttp, streamed in chunks) | aiohttp is async |
| Writing chunks to the cache file | executor (batch chunks, or write the whole temp file in one executor call) | blocking file I/O |
| `hass.config.is_allowed_path(path)` | executor | the docstring says it does blocking I/O |
| Local file `stat()` (mtime as change detection) | executor | blocking |
| `parse_xmltv(path)` incl. gzip decompression | executor | CPU-bound, the main cost |
| `FilterSpec.apply(epg)` per calendar | executor | regex over 10^4 to 10^5 programmes × (title + desc) |
| `async_get_events` range lookup | event loop | `bisect` over precomputed matches, microseconds |
| `event` property | event loop | small scan of precomputed matches |

**GIL caveat (MEDIUM confidence):** HA runs a GIL-enabled CPython (core requires Python ≥ 3.14.2). An executor thread running pure-Python per-element callbacks still competes with the event loop for the GIL. The loop stays responsive because of the 5 ms switch interval, but it gets slower. To keep the Python-level work small:
- use C-accelerated `iterparse`
- handle only `end` events for `programme` and `channel`
- call `elem.clear()`
- drop out-of-window programmes before building objects
- intern channel IDs

A `ProcessPoolExecutor` is not justified: pickling ~100k objects back across the process boundary costs about as much as parsing them.

### Pattern 5: Precompute on write, cheap on read

**What:** The calendar is read much more often than the data changes:
- calendar card range queries
- trigger polling every 15 minutes (`UPDATE_INTERVAL = timedelta(minutes=15)` in `calendar/trigger.py`)
- state writes at every event start and end

So all the work happens once per coordinator update, per calendar, in the executor:
- filter
- render the title template
- compose the description
- build `CalendarEvent` objects (their `__post_init__` runs schema validation, which is too expensive to repeat on every read)
- sort by start, and keep a parallel `starts: list[datetime]` for `bisect`

Reads become slicing.

**`event` property must stay dynamic.** `CalendarEntity._async_write_ha_state` schedules `async_track_point_in_time` alarms at the current event's start and end, then calls `async_write_ha_state()` again. The `event` property must therefore compute "first match with `end > now`" (earliest start among overlapping matches) **from `dt_util.now()` at call time**, not return a value cached during the last coordinator update. Otherwise the calendar gets stuck on a finished programme.

---

## Data Flow

### Refresh flow (write path, once per refresh interval)

```
coordinator timer (refresh interval from parent options)
    ↓
XmltvCoordinator._async_update_data()
    ↓
SourceFetcher.fetch()
    ├─ URL:  GET with If-None-Match / If-Modified-Since
    │        304 → FetchResult(changed=False) → return self.data   (no parse)
    │        200 → stream into cache tmp file (executor writes) → atomic rename
    └─ file: executor stat(); mtime/size unchanged → changed=False
    ↓ (changed)
await hass.async_add_executor_job(parse_xmltv, path, keep_from=now - 1 day)
    ↓  gzip sniffed by magic bytes 1f 8b (not extension or Content-Type)
EpgData (immutable, eq=False)  ──► coordinator.data
    ↓ async_update_listeners()
for each XmltvCalendarEntity (one per subentry):
    _handle_coordinator_update()
        → schedule executor: matches = filter_spec.apply(epg)   (references, never copies)
        → self._events, self._starts = matches
        → async_write_ha_state()   → CalendarEntity re-arms start/end alarms
```

### Read flow (event loop, frequent)

```
Calendar card / calendar.get_events action / calendar trigger (15-min windows)
    ↓
XmltvCalendarEntity.async_get_events(hass, start, end)
    ↓ bisect on self._starts (plus an overlap check on end > start)
list[CalendarEvent]  (prebuilt; location = channel display-name, summary = rendered template)
```

### Configuration flow (user-driven)

```
Add integration → ConfigFlow.async_step_user(source, refresh interval)
    → validate: URL scheme / allowed path (executor)
    → async_show_progress: fetch + parse once (task)  → error mapping → abort/retry
    → async_set_unique_id(normalized source) → _abort_if_unique_id_configured()
    → create entry (cache file already warm → setup does not re-download)
    → optional: next_flow → first CalendarSubentryFlow (per docs: from async_on_create_entry)

"+ Add calendar" → CalendarSubentryFlow.async_step_user
    → channels from self._get_entry().runtime_data.coordinator.data.channels (entry must be LOADED)
    → validate regex compiles, template keys whitelisted, optional "N matches" preview
    → async_create_entry(title=name, data={...})
    → HA fires update listener → Pattern 2 adds the entity (no reload)

Calendar "reconfigure" → CalendarSubentryFlow.async_step_reconfigure
    → async_update_and_abort(entry, subentry, data=...) → listener → entity.async_apply_subentry()

Source options (URL, interval) → plain OptionsFlow → options saved → listener sees a source change
    → async_schedule_reload(entry_id) → full re-setup (cache keyed by entry_id is invalidated if the URL changed)
```

### State Management

```
Persistent (core.config_entries):
  parent.data      = {source}                         (immutable identity)
  parent.options   = {refresh_interval, ...}          (editable)
  subentry.data    = {channels[], include, exclude, match_fields, title_template}
Persistent (disk cache, not in backups):
  .cache/xmltv_calendar/<entry_id>.xml[.gz] + <entry_id>.meta.json (etag, last_modified, fetched_at)
Runtime (entry.runtime_data, dies with unload):
  coordinator.data (EpgData), per-entity matches, add_entities callback, source_snapshot
```

---

## Alternative: Flat entries + shared source registry in `hass.data` (NOT recommended, specified for completeness)

Use this only if the user insists on "one config entry = one calendar".

```python
# __init__.py
SOURCES: HassKey[SourceRegistry] = HassKey(DOMAIN)

async def async_setup(hass, config) -> bool:
    hass.data[SOURCES] = SourceRegistry(hass)
    return True

class SourceRegistry:
    def __init__(self, hass):
        self._hass = hass
        self._lock = asyncio.Lock()
        self._sources: dict[str, _Shared] = {}   # key = normalized source

    async def acquire(self, key: str, entry_id: str, interval: timedelta) -> XmltvCoordinator:
        async with self._lock:                    # concurrent entry setups at boot
            shared = self._sources.get(key)
            if shared is None:
                coord = XmltvCoordinator(self._hass, None, ...)   # config_entry=None!
                await coord.async_register_shutdown()           # required without an entry
                shared = self._sources[key] = _Shared(coord)
            if shared.teardown: shared.teardown(); shared.teardown = None   # cancel delayed release
            shared.refs.add(entry_id)
            shared.intervals[entry_id] = interval
            shared.coord.update_interval = min(shared.intervals.values())
        if shared.coord.data is None:
            await shared.coord.async_refresh()   # first_refresh is NOT allowed (config_entry=None)
            if not shared.coord.last_update_success:
                await self.release(key, entry_id)
                raise ConfigEntryNotReady(...)
        return shared.coord

    async def release(self, key, entry_id):  # via entry.async_on_unload
        # remove ref; if refs empty: async_call_later(60s, shutdown+drop) for reload survival
        ...
```

Costs compared with the recommended design:

| Concern | Subentries (recommended) | Flat + registry |
|---------|--------------------------|-----------------|
| Global mutable state | none | `hass.data[HassKey]` plus a lock |
| Coordinator lifecycle | automatic via `config_entry=entry` | manual: `async_register_shutdown`, ref-count, delayed teardown |
| First refresh / not-ready semantics | `async_config_entry_first_refresh` | hand-rolled `async_refresh` + `last_update_success` check |
| Refresh interval "per source" | single value on the parent | conflicting values across entries; needs a rule (min) |
| Channel list in config flow | from the loaded coordinator | must fetch 50 MB inside the flow unless the source is already in the registry |
| Editing one calendar's filter | in-place update (Pattern 2) | reloads that entry only (cheap while other refs keep the source alive) |
| Last consumer reloads | n/a | needs a teardown grace period, or the source is re-fetched |
| Changing an entry's source | n/a (source is the parent) | release old key, acquire new key |
| Duplicate source detection | `unique_id` on the parent | implicit via registry key |
| UX | add source once, "+ Add calendar" | each calendar repeats the URL and interval |
| Matches PROJECT.md wording | needs a small decision update | as written |

Pitfall specific to this alternative: **do not** create the shared coordinator with `config_entry=<first entry>`. Its `async_shutdown` is then registered on that entry's unload, so unloading or reloading that one entry silently stops refreshes for all other entries sharing the source.

---

## Scaling Considerations

The relevant scale is feed size × number of calendars on one HA host, not users.

| Scale | Architecture adjustments |
|-------|--------------------------|
| 1 source, ≤ 5 MB, a few calendars | Anything works. Still parse in the executor (hassfest and HA's blocking-call detector would flag file I/O on the loop). |
| 1–3 sources, 20–150 MB uncompressed (iptv-org, epg.best full DE), 5–20 calendars | Streaming `iterparse`, a time window (drop programmes ending before now − 1 day), `slots=True` dataclasses, interned channel IDs, filter results as references, conditional GET. Expect 10^5 programmes and tens of MB of RAM per source. |
| Very large multi-country feeds (500 MB+) | Optional channel pre-filter at parse time: the union of all subentries' channel sets, re-parsed when a subentry adds a new channel. Defer; only build it if measured RAM is a problem. |

### Scaling Priorities

1. **First bottleneck: peak memory and CPU during parse.** A full DOM (`ET.parse`, pydantic-xml as used in `xmltv_epg`) of a 100 MB feed can spike to over 1 GB. Fix: streaming `iterparse` with `elem.clear()` and window pruning from the first version.
2. **Second bottleneck: per-calendar regex over `desc`.** 20 calendars × 10^5 programmes × multi-KB descriptions. Fix: check the channel filter first (a cheap set lookup), then include/exclude on title, then on description. Run in the executor and compile once per `FilterSpec`.
3. **Third: network politeness.** Providers rate-limit (epg.best, some iptv-org mirrors). Fix: conditional GET, the disk cache honoured across restarts, and a minimum refresh interval (for example ≥ 1 h) enforced in the flow.

---

## Anti-Patterns

### Anti-Pattern 1: One coordinator per calendar, each downloading the feed
**What people do:** Follow the "one entry, one coordinator" tutorial literally.
**Why it's wrong:** N downloads and N parses of 50 MB, which breaks the core requirement.
**Do this instead:** One coordinator per source (Pattern 1).

### Anti-Pattern 2: Parsing or decompressing on the event loop
**What people do:** `gzip.decompress(await resp.read())`, `ET.fromstring(...)`, or `open(path)` inside an `async def`.
**Why it's wrong:** Blocks HA for seconds. HA's blocking-I/O detector logs warnings for `open()` in the loop.
**Do this instead:** Run everything in `xmltv/` via `hass.async_add_executor_job` (Pattern 4).

### Anti-Pattern 3: Full DOM parse
**What people do:** `ET.parse()` or pydantic-xml on the whole document.
**Why it's wrong:** Memory is a multiple of the file size, risky on 4 GB HA boxes.
**Do this instead:** Streaming `iterparse` with `elem.clear()` and window pruning.

### Anti-Pattern 4: Reloading the whole source entry on every subentry change
**What people do:** Copy the `openai_conversation` listener (`async_reload` on any update).
**Why it's wrong:** Every filter edit triggers a full re-parse, and the calendar goes unavailable meanwhile.
**Do this instead:** Use the diffing listener (Pattern 2) and reload only when the source data or options changed.

### Anti-Pattern 5: Combining `OptionsFlowWithReload` with an update listener
**Why it's wrong:** HA raises `ValueError` at runtime (verified in `config_entries.py`).
**Do this instead:** Use a plain `OptionsFlow`; the listener schedules the reload.

### Anti-Pattern 6: `always_update=False` with value-equality on huge data
**What people do:** Set `always_update=False` to skip no-op updates while `EpgData` is a regular dataclass.
**Why it's wrong:** The coordinator compares `self.data != previous_data`, which means an O(n) deep comparison of ~10^5 programmes on the event loop.
**Do this instead:** On 304 or unchanged mtime, return **the same object** (`self.data`). Give `EpgData` `eq=False` so comparison is by identity, then `always_update=False` is cheap and correct.

### Anti-Pattern 7: Filtering or building events inside `async_get_events`
**Why it's wrong:** The method is called by the frontend, the calendar card and the trigger (every 15 minutes), and `CalendarEvent.__post_init__` runs schema validation.
**Do this instead:** Precompute on coordinator update (Pattern 5).

### Anti-Pattern 8: Caching the `event` property value
**Why it's wrong:** HA's calendar alarms rewrite state at event end. A cached `event` never advances.
**Do this instead:** Compute it from `dt_util.now()` against precomputed matches.

### Anti-Pattern 9: Legacy `hass.data[DOMAIN][entry_id]` for per-entry state
**Do this instead:** Use `entry.runtime_data` with the typed alias `ConfigEntry[XmltvRuntimeData]`. HA clears it on unload, and it is a quality-scale rule (`runtime-data`). In the alternative design, use `hass.data` only for a cross-entry registry, typed with `HassKey`.

### Anti-Pattern 10: Jinja templates for the event title
**Why it's wrong:** Rendering a Jinja `Template` per event is slow, needs `hass`, and invites user templates that do I/O.
**Do this instead:** `str.format_map` with a whitelisted dict (`channel`, `title`, `subtitle`, `episode`, `category`, `start`). Validate the keys in the flow and handle unknown keys with a safe default.

### Anti-Pattern 11: Detecting gzip by extension or `Content-Type`
**Why it's wrong:** Real providers send gzipped XML with wrong content types. `xmltv_epg` carries a workaround for elres.de. A server may also apply `Content-Encoding: gzip` on top of a `.gz` file.
**Do this instead:** Let aiohttp handle `Content-Encoding`, then sniff the first two bytes of the payload (`1f 8b`) before choosing `gzip.open` or `open`.

---

## Integration Points

### External Services

| Service | Integration pattern | Notes |
|---------|---------------------|-------|
| HTTP(S) XMLTV source (TVHeadend `/xmltv/channels`, iptv-org/epg, epg.best, etc.) | `async_get_clientsession(hass)`; streamed read; `ClientTimeout(total≈300s, sock_read≈60s)`; conditional GET | Redact the URL in logs and diagnostics. Map `ClientError`/`TimeoutError` to `UpdateFailed` and keep the last data. Local TVHeadend on the LAN should still be HTTP via the shared session (no SSL issues with `verify_ssl` default; expose a `verify_ssl` option only if needed). |
| Local file | Path in `/media/...` or `/config/www/...` | Allowed by default: `allowlist_external_dirs` defaults to `config/www` plus the media dirs (verified in `core_config.py`). Other paths need `allowlist_external_dirs` in `configuration.yaml`; this is HA core config, not integration YAML, so it doesn't violate "UI-only". `is_allowed_path` must run in the executor. Detect changes via mtime and size. |
| Disk cache | `hass.config.cache_path(DOMAIN, ...)` | `cache_path` exists from **HA 2026.3** (absent in 2026.2.0) and is excluded from backups. With a lower minimum HA version, use `hass.config.path(".cache", DOMAIN)`, which is the same location. Write via a temp file plus atomic rename. Delete in `async_remove_entry`. |

### Home Assistant Internals

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Coordinator → calendar entities | `CoordinatorEntity` listener callback | `_handle_coordinator_update` must not block; schedule the executor filter via `entry.async_create_background_task` or `hass.async_create_task`, and guard against overlapping runs (keep the latest). |
| Calendar entity → HA calendar component | `event` property, `async_get_events` | `CalendarEntity.state` and `state_attributes` are `@final`; implement only `event` and `async_get_events`. Datetimes must be tz-aware. `CoordinatorEntity` gives `should_poll=False`, so the calendar's own 60 s `SCAN_INTERVAL` polling is not used. |
| Config/subentry flow → runtime data | `self._get_entry().runtime_data` | Check `entry.state is ConfigEntryState.LOADED` first. |
| Update listener → entity platform | stored `add_entities` callback plus `calendars` dict in runtime_data | Dynamic entity add is an established core pattern. Subentry removal cleans the registry automatically. |
| Entity/device registry | unique_id = `subentry_id` (UUID); optional device per subentry | 2026.8 device rule: one entry and at most one subentry per device. |
| `xmltv/` ↔ HA code | plain function calls via executor | `xmltv/` must never import `homeassistant`. Enforce with a ruff `banned-api`/import rule or a test. |

---

## Suggested Build Order (dependency-driven)

Granularity in `config.json` is `coarse`, so this maps to 4 phases. Arrows show hard dependencies.

```
[1] Domain library (pure)  ──►  [2] HA runtime core  ──►  [3] Full UI flows  ──►  [4] HACS + polish
    parser, models, filter        fetcher, coordinator,      subentry flow,           CI, hassfest,
    + fixtures, benchmark         calendar entity,           reconfigure, options,    translations,
                                  minimal source flow        diff listener            diagnostics
```

1. **Domain library: parser + models + filter (no HA).**
   - Build `xmltv/parser.py` with streaming iterparse, timestamp/offset parsing, gzip sniffing and window pruning, then `filter.py` and title/description rendering.
   - TDD against fixtures, plus a generated 50–100 MB feed to benchmark time and peak RSS.
   - *Why first:* everything consumes `EpgData` and `FilterSpec`, the most risk sits in performance and timezone handling, and it needs no HA test harness.
2. **HA runtime core: `source.py`, `coordinator.py`, `__init__.py` lifecycle, `calendar.py`.**
   - Use runtime_data, `config_entry=entry`, first-refresh, the disk cache with stale-while-revalidate, and conditional GET.
   - Add a minimal `ConfigFlow` (source only). Calendars come from `MockConfigEntry(subentries_data=...)` in tests, or from a trivial subentry user step.
   - *Why second:* proves the end-to-end value (a calendar shows matches, triggers fire) on `ha-host` early.
3. **Full configuration UX.**
   - `CalendarSubentryFlow` (user + reconfigure) with the channel multi-select from loaded data, regex and template validation, and an optional match-count preview.
   - Source `OptionsFlow` (plain), and the diffing update listener (Pattern 2).
   - `ConfigFlow` with `async_show_progress` for the initial fetch.
   - *Why third:* depends on the coordinator data (channel list) and the entity's `async_apply_subentry` from phase 2.
4. **Distribution and hardening.**
   - `hacs.json`, GitHub Actions (hassfest, `hacs/action`, pytest), en/de translations including `config_subentries`, diagnostics with URL redaction.
   - `async_migrate_entry` scaffold (VERSION=1, MINOR_VERSION=1), README.
   - *Why last:* validation tooling is cheap to add once the structure is stable. Start a skeleton CI in phase 1 if you want hassfest feedback early.

**Decision gate before phase 2:** confirm with the user that the subentry model is acceptable. Phase 2's `__init__.py` and `calendar.py` look substantially different under the flat-entries alternative.

---

## Version Floor Implications

| API used | Minimum HA | Verified via |
|----------|-----------|--------------|
| Config subentries + subentry reconfigure | 2025.3 | `config_entries.py` at tags 2025.2.0 (absent) and 2025.3.0 (present) |
| `OptionsFlowWithReload` (not used in the recommended design, but relevant) | 2025.8 | tags 2025.7.0 (absent) and 2025.8.0 (present) |
| `hass.config.cache_path()` | 2026.3 | tags 2026.2.0 (absent) and 2026.3.0 (present) |
| Device-per-subentry rule | 2026.8 (enforced 2026.10) | developer blog 2026-07-21 / 2026-09-15 |

Recommendation: `hacs.json` `"homeassistant": "2026.3.0"`. The user runs current HA, and this allows `cache_path`.

---

## Sources

- HA core source, `dev` branch (2026.11.0.dev), read directly. Confidence HIGH, primary source:
  - `homeassistant/config_entries.py`: `ConfigSubentryFlow`, `async_add_subentry`/`async_remove_subentry` → `_async_update_entry` → update listeners; `OptionsFlowWithReload` and its `ValueError` with update listeners
  - `homeassistant/helpers/update_coordinator.py`: `config_entry` handling, `async_on_unload(async_shutdown)`, `async_register_shutdown`, `async_config_entry_first_refresh` constraints
  - `homeassistant/helpers/entity_platform.py`: `config_subentry_id` on `async_add_entities`
  - `homeassistant/helpers/entity_registry.py`: `async_clear_config_subentry`
  - `homeassistant/components/calendar/__init__.py`: `CalendarEvent` validation, `event`/`async_get_events`, alarm scheduling
  - `homeassistant/components/calendar/trigger.py`: `UPDATE_INTERVAL = 15 min`
  - `homeassistant/core_config.py`: `cache_path`, `is_allowed_path`, default `allowlist_external_dirs`
  - `homeassistant/components/openai_conversation/{__init__,conversation}.py`: precedent for subentries + runtime_data
- Release tags 2025.2.0/2025.3.0/2025.7.0/2025.8.0/2026.2.0/2026.3.0 for the version floors (HIGH)
- [Config flow handler docs: subentries](https://developers.home-assistant.io/docs/config_entries_config_flow_handler) (HIGH, official)
- [Options flow docs: OptionsFlowWithReload](https://developers.home-assistant.io/docs/core/integration/options_flow) (HIGH, official)
- [Dev blog: config subentries (2025-02-16)](https://developers.home-assistant.io/blog/2025/02/16/config-subentries) (HIGH, official)
- [Dev blog: devices restricted to a single config entry and at most one subentry (2026-07-21)](https://developers.home-assistant.io/blog/2026/07/21/device-registry-single-config-entry) (HIGH, official)
- [Dev blog: device entry config entries deprecation (2026-09-15)](https://developers.home-assistant.io/blog/2026/09/15/device-entry-config-entries-deprecation) (MEDIUM, seen in search results only)
- Prior art: [shadow578/homeassistant_xmltv-epg](https://github.com/shadow578/homeassistant_xmltv-epg) (`coordinator.py`, `api.py`, `manifest.json`): per-entry coordinator, gzip content-type workaround, pydantic-xml full parse (MEDIUM, used as a counter-example)
- GIL/executor interaction and memory estimates: general CPython knowledge, not benchmarked for this feed (MEDIUM; validate with the phase 1 benchmark)

---
*Architecture research for: HA custom integration, XMLTV EPG to filtered calendar entities*
*Researched: 2026-10-12*
