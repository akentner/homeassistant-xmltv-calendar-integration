# Pitfalls Research

**Domain:** Home Assistant custom integration (HACS) that turns XMLTV EPG feeds into filtered `calendar.*` entities
**Researched:** 2026-10-12
**Confidence:** HIGH for HA calendar/trigger/coordinator/options-flow behaviour (read directly from HA core `dev` source, 2026.11.0.dev0) and for XMLTV parsing behaviour (checked against the official DTD and by running experiments locally on Python 3.14.7 / expat 2.9.0). MEDIUM for HACS/brands details (official docs, but some community reports disagree). LOW for provider rate-limit specifics.

> Confidence note: the `classify-confidence` seam rates `webfetch`/`websearch` providers as LOW. Claims below marked **[verified: source]** were checked against the primary source code fetched from GitHub. Claims marked **[verified: experiment]** were reproduced locally. Those carry HIGH confidence even though the seam rates the fetch channel LOW. Claims without a tag are MEDIUM or LOW and are labelled that way.

Phase names used below are suggestions; the roadmapper will assign numbers:
- **P-Scaffold**: repo skeleton, manifest, hacs.json, CI (hassfest + HACS action + pytest)
- **P-Parser**: pure-Python XMLTV parser with no HA imports, plus fixtures
- **P-Source**: download, gzip, cache, shared per-source coordinator, refcounting
- **P-Filter**: channel and regex matching engine
- **P-Calendar**: `CalendarEntity`, `event`, `async_get_events`, trigger compatibility
- **P-Flows**: Config Flow and Options Flow
- **P-Release**: HACS publishing, docs, brand assets

---

## Critical Pitfalls

### Pitfall 1: Mis-parsing XMLTV timestamps (offsets, missing offsets, short forms, alpha zones)

**What goes wrong:**
Events show up 1–2 hours off, or end up on the wrong day. The worst case is silent: `datetime.strptime("202610122030 +0200", "%Y%m%d%H%M%S %z")` succeeds and returns **20:03:00**, not 20:30. strptime fills `%M`/`%S` greedily from too few digits. **[verified: experiment]**

**Why it happens:**
- The XMLTV DTD allows `YYYYMMDDhhmmss` **or any initial substring** (e.g. `YYYYMMDDhhmm`, even `YYYYMM`), and an **optional** timezone. The timezone can be numeric (`+0300`) or **alphabetic** (`BST`, the DTD's own example). If the timezone is missing, **UTC is assumed**. **[verified: source — xmltv.dtd]**
- Real grabbers break the spec: many emit local time without an offset (which is wrong per spec). Some omit the space before the offset, emit `+02:00`, or emit 12-digit timestamps.
- Developers copy the single format string `"%Y%m%d%H%M%S %z"` from a blog post and test only against their own feed.

**How to avoid:**
- Write a dedicated, tolerant parser in P-Parser. Slice fixed positions: date and time digits first, then optional seconds, then an optional offset in the forms `±HHMM`, `±HH:MM`, `Z`, or a small alpha map (`UTC`, `GMT`, `BST`, `CET`, `CEST`). Reject anything else explicitly. Do not use strptime. It is also about 3x slower than slicing: 1.8 s vs 0.6 s for 200k timestamps **[verified: experiment]**.
- Always return **tz-aware** datetimes. For a missing offset, follow the spec (UTC) by default. Add a per-source option "timestamps without offset are local time", which uses HA's configured zone and `fold=0`. A source setting is the right place because the quirk belongs to the feed, not to the filter.
- Never compare naive and aware datetimes. A single naive value raises `TypeError` in `async_get_events`, and `CalendarEvent` rejects naive datetimes (`has_timezone` validator) **[verified: source — calendar/helper.py]**.

**Warning signs:**
- Events at times like `xx:03` or `xx:01` (the strptime mis-split).
- All events shifted by exactly the UTC offset.
- Events around the last Sunday of March or October shifted by 1 hour.

**Phase to address:** P-Parser. Table-driven unit tests should cover: 14-digit with `+0200`, 14-digit without space, `+02:00`, 12-digit, no offset, `BST`, DST-transition nights (Europe/Berlin 2026-03-29 and 2026-10-25), and garbage input.

---

### Pitfall 2: Bad programme data crashes the whole calendar (missing/negative stop, zero duration)

**What goes wrong:**
`CalendarEvent.__post_init__` runs schema validation and **raises `HomeAssistantError` if `end < start`** (minimum duration 0) or if a datetime is naive **[verified: source — calendar/__init__.py, helper.py]**. If you build `CalendarEvent`s inside `async_get_events`, one malformed programme makes the whole call fail. The dashboard then shows "Error reading events". The calendar trigger only catches `HomeAssistantError` and **skips that 15-minute window**, so automations silently miss events.

**Why it happens:**
- `stop` is `#IMPLIED` (optional) in the DTD **[verified: source — xmltv.dtd]**. Many feeds omit it, especially on the last programme per channel.
- Grabbers produce cross-midnight bugs (stop on the wrong day, so stop < start), duplicates, and overlapping entries.

**How to avoid:**
- Sanitize at parse time (P-Parser), never at query time:
  - Missing `stop`: use the next programme's `start` on the same channel (sort per channel by start first). If it is the last programme, use a configurable default (e.g. 60 min) or drop it.
  - `stop <= start`: same inference as missing, or drop it and log at debug level with a counter.
  - Exact duplicates (same channel, start, and title): keep one.
- Make the in-memory model a plain tuple or dataclass that cannot be invalid. Only convert to `CalendarEvent` at the edge, inside a `try` that skips and logs bad items rather than raising.

**Warning signs:** "Failed to validate CalendarEvent" in logs; the calendar card intermittently empty; automations that "sometimes" don't fire.

**Phase to address:** P-Parser (inference and sanitizing), P-Calendar (defensive conversion).

---

### Pitfall 3: Parsing a 50+ MB feed with a full DOM (memory explosion)

**What goes wrong:**
`ET.parse()` / `ET.fromstring()` on a ~100 MB synthetic XMLTV file (240k programmes) peaked at **~800 MB** of Python heap. `ET.iterparse` with `elem.clear()` peaked at **~20 MB** at the same speed (~6 s on a desktop CPU) **[verified: experiment]**. On the target (`ha-host`) and especially on an Odroid N2+ (4 GB RAM shared with HA, recorder, and add-ons), a full DOM can trigger the OOM killer or heavy swapping during every refresh.

**Why it happens:**
- Tutorials use `ET.parse(...).getroot().findall("programme")`.
- `await resp.read()` followed by `gzip.decompress()` keeps compressed bytes, decompressed bytes, and the tree in memory at the same time.

**How to avoid:**
- Stream the HTTP body to a temp file in chunks (`resp.content.iter_chunked`). Write the file in the executor, or write each chunk via `hass.async_add_executor_job`, or use a single executor job that does the download with streaming writes.
- Parse with `gzip.open(path)` and `xml.etree.ElementTree.iterparse(f, events=("start", "end"))`. Take the root from the first `start` event. On each `</programme>` end, extract fields into a compact tuple, then call `elem.clear()`. Periodically call `root.clear()` so cleared children don't pile up in the root list.
- Keep only what you need after parsing:
  - Drop programmes that ended before `now - 1 day`.
  - Keep programmes only for channels referenced by at least one subscribed entry, or all channels if some entry has no channel filter.
  - Keep a small separate channel index (id to display-name) for the config flow.
- Intern channel ids (`sys.intern`), since they repeat hundreds of thousands of times.

```python
# Streaming pattern (runs in executor)
it = ET.iterparse(fh, events=("start", "end"))
_, root = next(it)                      # first 'start' = <tv>
for event, elem in it:
    if event == "end" and elem.tag == "programme":
        handle(elem)
        elem.clear()
        root.clear()                    # drop references to processed siblings
    elif event == "end" and elem.tag == "channel":
        handle_channel(elem)
        root.clear()
```

**Warning signs:** RSS of the HA process jumps by hundreds of MB at each refresh; the `System Monitor` memory sensor shows a sawtooth; HA restarts on low-RAM boxes.

**Phase to address:** P-Parser (streaming API), P-Source (stream-to-disk download). Add a test that parses a generated 50 MB fixture under `tracemalloc` with a peak budget (e.g. < 100 MB).

---

### Pitfall 4: Blocking the HA event loop (I/O, parsing, regex matching)

**What goes wrong:**
HA logs "Detected blocking call to open … inside the event loop by custom integration 'xmltv_calendar'", and the UI freezes for seconds during refresh. HA explicitly lists `open`, `glob`/`listdir`/`scandir`/`stat`, `Path.read_text`/`read_bytes`/`write_*`, `urllib`, `time.sleep`, `import_module`, and SSL cert loading as blocking. HA **only detects `open`**, so the related reads and writes go unnoticed even though they block too **[verified: source — developers.home-assistant.io/docs/asyncio_blocking_operations]**.

**Why it happens:**
- `os.path.exists(local_path)` or `open()` in `async_setup_entry` or the config flow validator.
- `gzip.decompress`, `ET.iterparse`, and regex matching over 240k programmes are CPU-bound. They are invisible to HA's detector but still freeze the loop.
- Creating a private `aiohttp.ClientSession` or an `ssl.create_default_context()` in the loop (blocking SSL cert loading).
- Running filter matching inside `async_get_events`, which runs on the loop for every dashboard view and every trigger poll.

**How to avoid:**
- Rule: **everything that touches the file system, decompresses, parses, or matches runs in `hass.async_add_executor_job`**. This includes the config flow's "validate source" and "list channels" steps.
- Use `async_get_clientsession(hass)` for HTTP. Never create your own session or SSL context.
- Compute each entry's matched-programme list **once per data refresh, in the executor**. Store it sorted by start. `async_get_events` then does only a `bisect` plus slicing (O(log n + k)) on the loop.
- Use HA's configured zone (`dt_util.get_default_time_zone()`), already loaded. If you need any other zone, use `await dt_util.async_get_time_zone(...)`, because the first `ZoneInfo` load reads files.
- Moderate caveat: CPU-bound pure-Python work in an executor thread still competes for the GIL, and expat does not release it. Expect HA to feel slightly sluggish for the parse duration (seconds on x86, possibly 20–30 s on ARM SBCs). That is acceptable for a refresh every few hours. If it isn't, shrink the work by filtering early. Do not add a subprocess.

**Warning signs:** "Detected blocking call" warnings; `homeassistant.util.async_` "took X seconds" warnings; frontend websocket disconnects during refresh. During development, run HA with `debugpy`/`asyncio` debug mode (`python -X dev`), which logs slow callbacks over 100 ms.

**Phase to address:** P-Source and P-Filter. Code review in every phase should grep for `open(`, `Path(`, `os.path`, `gzip.`, and `re.` inside `async def`.

---

### Pitfall 5: Shared source coordinator gets shut down by the wrong config entry

**What goes wrong:**
Entries A and B share one source. A's options are edited, so A reloads, and **B's calendar stops updating forever**, or B's setup raises.

**Why it happens:** **[verified: source — helpers/update_coordinator.py]**
- If a custom integration does not pass `config_entry` to `DataUpdateCoordinator`, it binds implicitly to `config_entries.current_entry` (a ContextVar). That is the entry being set up when the coordinator is created. HA does not warn custom integrations about this (`custom_integration_behavior=IGNORE`).
- A bound coordinator registers `config_entry.async_on_unload(self.async_shutdown)`. When **entry A** unloads, the **shared** coordinator shuts down, and entry B's listener never gets updates again.
- `async_config_entry_first_refresh()` **raises `ConfigEntryError` if `config_entry is None`**, so you cannot simply pass `None` and keep the usual setup idiom.
- A coordinator without an entry only schedules refreshes **once it has a listener** (`schedule_refresh = not self._listeners`). `pref_disable_polling` on an entry has no effect on it.

**How to avoid:**
- Keep a module-level registry, `hass.data[DOMAIN]["sources"][source_key] -> SharedSource(coordinator, refcount)`, where `source_key` is the normalized URL or absolute path.
- Construct the coordinator with **`config_entry=None` explicitly**. In `async_setup_entry`, acquire the source (refcount +1), `await coordinator.async_refresh()` if there is no data yet, and if `not coordinator.last_update_success`, release it and raise `ConfigEntryNotReady`.
- Release in `async_unload_entry`, not via `async_on_unload` callbacks registered before setup can fail. On refcount 0, call `await coordinator.async_shutdown()` and delete the registry key. Also register cleanup on `EVENT_HOMEASSISTANT_STOP` (`coordinator.async_register_shutdown()`).
- Guard concurrent first-acquire with an `asyncio.Lock` per source key. Two entries setting up in parallel at HA start must not create two coordinators or download twice.
- Per-entry data such as matched programmes belongs in `entry.runtime_data`. Only raw shared data lives in the registry.

**Warning signs:** a calendar's `last_updated` frozen after another entry was edited; two downloads of the same URL in the log at startup; "Lingering timer" failures in tests.

**Phase to address:** P-Source. Tests: set up A and B on the same source; reload A; assert B still receives a refresh. Unload both and assert the registry is empty and no timers linger.

---

### Pitfall 6: Refresh interval and source settings conflict across entries

**What goes wrong:**
Entries A (interval 6 h) and B (interval 1 h) share a source. Which interval wins? If A's options change the URL, A must move to a different shared source. A naive implementation mutates the shared coordinator in place and changes B's source.

**Why it happens:** PROJECT.md says "refresh interval is configurable **per source**", but entries are per filter set. The data model does not have a first-class "source" object.

**How to avoid (decide in P-Source, before writing flows):**
- Option A (simplest, recommended for v1): the effective interval is the **minimum** over all subscribed entries. Recompute on every acquire and release. Document this in the options UI description.
- Option B: make the source its own entry type, or a config subentry (HA supports config subentries). This is cleaner but needs more flow work.
- Changing URL, path, or offset-handling in options means release the old source key and acquire the new one. With `OptionsFlowWithReload` this happens naturally through unload and setup.

**Warning signs:** an "interval" option that appears to do nothing; different entries showing different data for the same URL.

**Phase to address:** P-Source (data model decision); P-Flows (UI).

---

### Pitfall 7: `async_get_events` range semantics wrong (start-only filtering)

**What goes wrong:**
- Programmes that started before the requested range but are still running don't appear in the dashboard's "today" view.
- **`event: end` calendar triggers never fire** for programmes that started before the trigger's 15-minute scan window.

**Why it happens:** **[verified: source — calendar/trigger.py]**
- The trigger fetches events for `[span.start, span.end + 1s)` and then filters by trigger time. For `event: end` it needs every event **overlapping** the window, not only events starting in it.
- The dashboard and websocket view pass **local-tz-aware** `start`/`end` (`dt_util.as_local`).

**How to avoid:**
- Return events where `prog.start < end_date and prog.stop > start_date` (overlap, half-open).
- With the list sorted by start, `bisect` to the first event with `start >= end_date` and scan backwards for events with `stop > start_date`. Alternatively keep a running "max duration" so you can bound the backward scan to `start_date - max_duration`.
- Unit-test boundaries: an event exactly ending at `start_date` (excluded), exactly starting at `end_date` (excluded), and spanning the whole range (included).

**Warning signs:** a running programme visible in state attributes but missing from the calendar card's day view; `event: end` automations never firing.

**Phase to address:** P-Calendar.

---

### Pitfall 8: `event` property cached at refresh time, so state never turns on/off correctly

**What goes wrong:**
The calendar's state stays `off` during a running programme, or `message` keeps showing a finished show until the next feed refresh hours later.

**Why it happens:** **[verified: source — calendar/__init__.py]**
- `state` is `on` iff `event.start <= now < event.end`. The base class schedules alarms at the current `event`'s start and end, then calls `async_write_ha_state()`, which **re-reads `self.event`**.
- If `event` returns a value computed once in the coordinator callback, the alarm fires but sees the same stale event. Its end is in the past, so no new alarm is scheduled, and the entity is stuck until the next refresh.
- If `event` returns only *upcoming* programmes (`start > now`), the state can never be `on`.

**How to avoid:**
- Compute `event` **live**: return the earliest-starting programme with `stop > dt_util.now()` from the entry's sorted matched list. That is a bisect on stop, or a linear scan from a cached index; it must be cheap because it runs on every state write.
- Overlapping matches (simulcasts, e.g. F1 on Sky and ORF at once) are normal here. Choose a deterministic tie-break (earliest start, then channel name). `state_attributes` can only show one event; the full list lives in `async_get_events`.
- After each coordinator update, call `async_write_ha_state()`. This re-arms alarms **and** pushes updates to dashboard websocket subscribers, which are debounced 1 s and re-call `async_get_events`.

**Warning signs:** state `off` while a matching programme is running; `start_time` attribute in the past while state is `off`.

**Phase to address:** P-Calendar. Use `freezer` (freezegun) tests to advance time across start and end and assert state transitions without a coordinator refresh.

---

### Pitfall 9: Calendar triggers miss events after EPG changes or entity reloads

**What goes wrong:**
- The feed refresh adds or moves a programme into the next few minutes, and the automation doesn't fire.
- The automation fires at the old time after the broadcaster shifted the schedule.
- An options-flow reload happening during a trigger poll makes that 15-minute window disappear.

**Why it happens:** **[verified: source — calendar/trigger.py]**
- The trigger polls every **15 minutes** with a forward-only cursor (`Timespan.next_upcoming`). Events are queued per window and **never re-fetched** for a window already scanned.
- During refresh, the cursor advances *before* the fetch. If `get_entity` fails (entity removed during reload) or `async_get_events` raises `HomeAssistantError`, the error is logged and the window is **lost**. Any **other** exception type propagates out of the refresh handler.

**How to avoid:**
- Accept and document the limitation: changes inside the next 15 minutes won't affect already-queued triggers. Recommend `offset: "-0:15:00"`-style triggers in the README for "notify me before".
- `async_get_events` must **never raise anything except `HomeAssistantError`**, and should return `[]` when data isn't loaded yet. Wrap the body defensively.
- Keep reloads fast: on options change, reuse the already-parsed shared source and don't re-download. This keeps the window in which the entity is missing small.

**Warning signs:** "Calendar trigger failed to fetch events" in logs; user reports of a missed trigger right after editing options.

**Phase to address:** P-Calendar (exception discipline), P-Release (README limitations section).

---

### Pitfall 10: Regex filters: empty patterns, invalid patterns, catastrophic backtracking, case and umlauts

**What goes wrong:**
- **An empty exclude pattern excludes everything.** `re.search("", s)` is always truthy **[verified: experiment]**. Storing `""` from an empty text field and compiling it blindly empties every calendar.
- An invalid pattern saved via the options flow raises `re.error` at setup, so the entry fails to load and the user has no UI hint.
- **Catastrophic backtracking:** `(a+)+$` against 26 `a`s plus `!` took **6.2 s** **[verified: experiment]**. Against 240k programme descriptions, a bad user pattern hangs the executor thread indefinitely. Python's `re` has **no timeout**.
- Case/Unicode:
  - `re.IGNORECASE` handles `Ü`/`ü` fine, but `"strasse"` does **not** match `"Straße"`. `casefold()` would match.
  - A feed in **NFD** (`u` + combining diaeresis) does **not** match a user's NFC `"Grüße"` until both sides are NFC-normalized **[verified: experiment]**.
  - Users expect "contains" semantics, so `re.match` (anchored) silently breaks their filters.

**Why it happens:** Regex is user input treated as trusted code; the HA text selector returns `""` rather than `None`; German content is rich in umlauts and ß.

**How to avoid:**
- Normalize config: empty or whitespace-only means "no filter" (`None`), and treat it separately for include vs exclude. Semantics: include passes if **any** include pattern matches **title or description** (or no include is set); exclude drops if any exclude pattern matches.
- Validate in **both** config flow and options flow: `try: re.compile(p) except re.error as e:` and return `errors={"include_title": "invalid_regex"}`, with a placeholder showing `e.msg` and the position. Also validate again at setup and create a **repair issue** instead of crashing.
- Compile once per refresh with `re.IGNORECASE`. NFC-normalize (`unicodedata.normalize("NFC", ...)`) both the pattern text and the programme text at parse time.
- Use `re.search` (contains).
- Backtracking mitigation, pick one:
  - (a) cap pattern length (e.g. 500 chars) and text length matched (truncate descriptions to ~2 KB for matching), and run matching in the executor so at worst a background thread stalls, never the loop;
  - (b) add the `regex` PyPI package, which supports `timeout=`. It is **not** in HA core's `package_constraints.txt` **[verified: source]**, so it adds a dependency and a wheel per architecture.
  Recommend (a) for v1. Offer a "preview matches" step in the flow so users see results (and slowness) immediately.
- Optional nicety: a "case sensitive" toggle that defaults to off.

**Warning signs:** a calendar empty after editing exclude; entry stuck in "Failed to set up"; refresh duration (debug log) growing from seconds to minutes after a regex change.

**Phase to address:** P-Filter (semantics, normalization, limits), P-Flows (validation, error strings, preview).

---

### Pitfall 11: Options flow reload done twice, or not at all

**What goes wrong:**
Options are changed but the calendar still uses old filters. Or the entry reloads twice, racing the shared-source refcount. From **2026.12 this is a hard error**.

**Why it happens:** **[verified: source — config_entries.py; developers blog 2026-05-07]**
- A plain `OptionsFlow` only stores `entry.options`; nothing reloads without an update listener.
- `OptionsFlowWithReload` reloads automatically, but **raises `ValueError` if the entry also has update listeners**. Using an update listener together with reloading methods in flows was deprecated in 2026.6 and **errors from 2026.12**.
- Setting `self.config_entry = config_entry` in `OptionsFlow.__init__` is a deprecated pattern (removed in 2025.12, per community reports). HA now provides `self.config_entry`.

**How to avoid:**
- Use **`OptionsFlowWithReload`** and **no** `entry.add_update_listener`. Don't pass the entry into the options flow constructor.
- Keep `entry.data` for immutable identity (source type and location, if those can't change). Put everything editable in `entry.options`. At setup, read a merged view `{**entry.data, **entry.options}`, but write edits only to options.
- Set `hacs.json` `"homeassistant"` minimum to a version that has every API you use (`OptionsFlowWithReload`, local `brand/` folder from 2026.3, probatio from 2026.9 if you import it directly).

**Warning signs:** `ValueError: Config entry update listeners should not be used with OptionsFlowWithReload`; deprecation warnings from `homeassistant.helpers.frame`; filters unchanged after saving options.

**Phase to address:** P-Flows.

---

### Pitfall 12: Channel IDs drift and configured channels silently stop matching

**What goes wrong:**
After months of working, the calendar is empty. The provider renamed channel ids (iptv-org style ids like `DasErste.de` vs `DasErste.de@SD`), or the user switched to another provider with the same channel names.

**Why it happens:**
- `programme@channel` references `channel@id`, which is opaque and provider-specific. Display names are not unique, and there can be **several** per channel in preference order, with `lang` attributes **[verified: source — xmltv.dtd]**.
- Programmes may also reference ids with no `<channel>` element.

**How to avoid:**
- Store channel **ids** in options. Display the **first** `display-name` (DTD: "most canonical first"), preferring one whose `lang` matches HA's language, with the id in brackets for disambiguation.
- Fall back to the id as the display name when no `<channel>` element exists.
- After each refresh, if any configured channel id is absent from the feed, raise a **repair issue** (`ir.async_create_issue`) naming the missing ids. Clear it when they reappear.
- Expose diagnostics (`diagnostics.py`): feed size, channel count, programme count, matched count, missing channel ids, last parse duration.

**Warning signs:** matched count dropping to 0 while the programme count stays stable.

**Phase to address:** P-Filter (detection), P-Flows (selector labels), P-Release (diagnostics).

---

## Moderate Pitfalls

### Pitfall 13: Malformed XML, wrong encodings, truncated downloads wipe the calendar

**What goes wrong:** `ParseError: not well-formed (invalid token)` from a bare `&` (`Tom & Jerry`), `undefined entity` from HTML entities (`&nbsp;`), Latin-1 bytes in a file declared UTF-8, or `no element found` from a truncated download. All four are **[verified: experiment]**. If the refresh replaces data with "nothing", every calendar empties until the next good refresh.
Expat handles the `windows-1252`, `iso-8859-1`, and `iso-8859-15` declarations correctly **[verified: experiment]**, so declared encodings are not the problem; **lying** declarations are.

**Prevention:**
- **Keep last-good data.** On any download or parse failure, raise `UpdateFailed` so the coordinator keeps the previous `data`. Mark the entity available or unavailable based on data **age** (e.g. unavailable only if the newest programme has already ended), not on last refresh success.
- Write the download to `*.tmp` and atomically rename it to the cache file only after a successful parse.
- Report the parse error position (`err.position`) in the log and diagnostics.
- Do not add `lxml` just for `recover=True`. It is not a core dependency, and pinned versions conflict easily. If recovery is really needed, do a targeted pre-pass in the executor that replaces bare `&` not followed by an entity pattern. Treat it as an optional "lenient" mode.

### Pitfall 14: gzip detection by file extension

**What goes wrong:**
- A `.xml.gz` URL arrives already decompressed (`Content-Encoding: gzip` is decoded transparently by aiohttp), so `gzip.open` fails with "Not a gzipped file".
- A `.xml` URL arrives gzipped.
- Some providers serve `.xz` instead.

**Prevention:** sniff magic bytes. `1f 8b` means gzip, `fd 37 7a 58 5a 00` means xz (stdlib `lzma`, cheap to support), anything else is plain XML. Ignore the extension. Cap the **decompressed** size (e.g. 1 GB) by reading through a counting wrapper, to defuse gzip bombs.

### Pitfall 15: Re-downloading big feeds too often (provider bans, startup storms)

**What goes wrong:** every HA restart and every entry reload triggers a 50 MB download, and some EPG providers cap downloads per day. One tvheadend report cites epgdata.com limiting to about 5 downloads a day (LOW confidence; old source).

**Prevention:**
- Cache the raw file at `hass.config.path(".cache", DOMAIN, <sha1(url)>.xml[.gz])`. HA core backups exclude `.cache/*` **[verified: source — backup/const.py]**, so a 50 MB file doesn't bloat every backup. Whether Supervisor-level backups use the same exclusion list is MEDIUM confidence.
- On startup, parse the cached file if it is younger than the interval, and only download when stale.
- Send `If-None-Match`/`If-Modified-Since` and handle `304`.
- Enforce a minimum refresh interval in the flow (e.g. ≥ 1 h). Use a sensible default (e.g. 12 h).
- A reload triggered by an options change must reuse the in-memory parsed source (Pitfall 5 registry) and must not re-download.

### Pitfall 16: Building `CalendarEvent` objects eagerly or for huge ranges

**What goes wrong:** each `CalendarEvent` runs probatio schema validation in `__post_init__` **[verified: source]**. Pre-building events for every matched programme, or an entry with only a broad channel filter returning thousands of events for a month view, costs noticeable CPU **on the event loop**. The view re-runs on every state write for every open dashboard (websocket subscriptions).
Per-instance cost was not measured (MEDIUM); the mechanism itself is verified.

**Prevention:**
- Store compact tuples. Create `CalendarEvent` only inside `async_get_events`, for the requested slice.
- Consider a hard cap on returned events per call (e.g. 2,000), with a debug log when it triggers.
- Warn in the flow, or require a confirmation checkbox, when a filter set matches more than N programmes per day ("this calendar would contain 3,400 events/day").

### Pitfall 17: Huge channel lists in the config flow

**What goes wrong:** an iptv-org guide can contain thousands of channels. A `SelectSelector` with thousands of options is slow and hard to use. Downloading and parsing 50 MB inside a config-flow step without feedback looks like a hang.

**Prevention:**
- Split the flow:
  1. Step 1 picks the source, with lightweight validation: HEAD/GET first bytes, or the local path exists and is allowed.
  2. Use a **progress step** (`async_show_progress` plus a background task) for the first download and parse, reusing the shared-source registry so setup doesn't parse again.
  3. Show a channel multi-select (`SelectSelector(multiple=True, mode=DROPDOWN, sort=True)`) built from the parsed channel index.
- Offer an optional "channel name filter" text field to narrow very large lists.

### Pitfall 18: Episode numbering off-by-one and multi-language elements

**What goes wrong:**
- `xmltv_ns` is **zero-based** (`1.4.` means S02E05) and may contain `X/Y` totals and spaces **[verified: source — xmltv.dtd]**. Showing it raw or without +1 gives wrong episode info.
- `title`, `sub-title`, `desc`, and `category` can repeat with different `lang` values. Taking the first `findtext("title")` may pick the wrong language. Regex filters that only check the first title miss matches.

**Prevention:**
- Parse `xmltv_ns` properly (+1, ignore totals). Prefer `onscreen` when present for display.
- Pick the display language by HA language, falling back to the first element.
- For **matching**, test against all title and desc variants (join them with `\n`).

### Pitfall 19: Local file source as an arbitrary-file-read primitive

**What goes wrong:** a "local file" path field accepts `/config/secrets.yaml` or `/etc/...`. The integration reads it and parse errors echo content snippets into logs or diagnostics.

**Prevention:** require `hass.config.is_allowed_path(path)` (respects `allowlist_external_dirs`; `www` and media dirs are allowed by default) **[verified: source — core_config.py]**. Resolve symlinks before checking. Never log content excerpts, only line and column positions. Redact URLs containing tokens (query strings) in diagnostics (`async_redact_data`).

### Pitfall 20: Timezone-dependent tests that pass locally and fail in CI

**What goes wrong:** the `hass` fixture of `pytest-homeassistant-custom-component` sets the HA timezone to **`US/Pacific`** **[verified: source — phcc common.py]**. Tests written assuming Europe/Berlin, or comparing naive local strings, fail. Or they pass for the wrong reason.

**Prevention:**
- Explicitly `await hass.config.async_set_time_zone("Europe/Berlin")` in tests that care. Parametrize key tests over two zones.
- Use `freezer` to pin "now".
- Include DST-transition fixtures.

---

## Minor Pitfalls

### Pitfall 21: hassfest failures that block CI
- Manifest keys must be sorted: `domain`, `name`, then alphabetical. `version` is required for custom integrations **[verified: source — script/hassfest/manifest.py]**.
- If you define `async_setup`, hassfest's `config_schema` plugin requires `CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)`. Simplest fix: don't define `async_setup` unless you need it.
- `config_flow: true`, `integration_type: "service"`, and `iot_class: "cloud_polling"` (or `local_polling` for file sources) must be present and valid.
- Every config flow `errors`/`abort` key must exist in `translations/en.json`. Use `strings.json` plus a copy, or maintain `translations/en.json` directly; custom integrations aren't compiled by core's translation tooling. Add `de.json`, since the user's HA is German.

### Pitfall 22: HACS action failures
- The checks are `archived`, `brands`, `description`, `hacsjson`, `images`, `information`, `issues`, and `topics`. All are ignorable via `ignore: "…"` (space-separated) **[verified: source — hacs.xyz/docs/publish/action]**.
- The repo needs a GitHub description, topics, and issues enabled. These are repo settings, not files, which is easy to forget.
- Brand assets: since HA **2026.3**, custom integrations can ship `custom_components/<domain>/brand/icon.png` (+ `dark_`/`@2x` variants), and local images take precedence **[verified: source — developers blog 2026-02-24]**. HACS docs say you "must provide brand assets" with at least `icon.png`. One community report says the HACS UI may still not show local logos (LOW).
- Only one directory under `custom_components/` is allowed.
- Releases are optional but preferred; tag them consistently with `manifest.json` `version`.

### Pitfall 23: voluptuous → probatio transition
Since HA **2026.9**, `import voluptuous as vol` resolves to probatio via a `sys.modules` alias, and voluptuous itself is no longer installed **[verified: source — developers blog 2026-09-30; package_constraints.txt]**. Effects:
- Keep `import voluptuous as vol` in flows. It works and remains compatible with older HA.
- **Do not** add `voluptuous` to `manifest.json` `requirements`.
- **Don't assert on validation error message text** in tests; the wording differs.

### Pitfall 24: Lingering timers and threads fail tests
The pytest plugin's `verify_cleanup` fixture fails tests on lingering tasks and timers **[verified: source — phcc plugins.py]**. A shared coordinator with `config_entry=None` is not cleaned up by entry unload automatically. Tests must unload all entries, or the integration must shut down on refcount 0 (Pitfall 5). Use the `enable_custom_integrations` fixture (autouse in `conftest.py`), or the integration is "not found". Sockets are blocked (`pytest_socket`), so use `aioclient_mock` for HTTP.

### Pitfall 25: Recorder bloat from long descriptions in state attributes
The calendar's `description` state attribute holds the full programme description, and it changes at every programme boundary, so each change is recorded. Keep descriptions sensible: strip, collapse whitespace, cap at ~1–2 KB. The recorder skips storing attributes larger than 16 KB, with a warning (MEDIUM confidence on the exact threshold).

### Pitfall 26: Simulcast triggers flood automations
One programme per event means three simultaneous broadcasts produce three trigger runs at the same instant. With the default `mode: single`, two are dropped with "Already running" warnings. Document `mode: queued`/`parallel`, or use a condition on `trigger.calendar_event.location`.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `ET.parse()` full DOM | 10 fewer lines | ~8× file size in RAM; OOM on SBCs | Never for the real path; fine in test helpers on tiny fixtures |
| `strptime("%Y%m%d%H%M%S %z")` | One-liner | Silent mis-parse of 12-digit stamps; breaks without offset; 3× slower | Never |
| Matching filters inside `async_get_events` | No precompute/state | Loop blocking on every dashboard open and trigger poll | Never |
| Coordinator per entry instead of shared | No refcount logic | N× downloads and parses of 50 MB; provider bans | Only in a throwaway spike |
| Implicit coordinator `config_entry` | Fewer args | Shared coordinator killed by first entry's unload | Never for shared sources |
| Raw XML kept in memory as `bytes` | Easy re-parse | +50–500 MB resident | Never; cache on disk under `.cache/` |
| No repair issue for missing channels/invalid regex | Less code | Silent empty calendars, support burden | MVP only if diagnostics expose the counts |
| `regex` PyPI package for timeouts | True ReDoS protection | Extra dependency and wheel availability per arch | Only if users actually hit pathological patterns |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| aiohttp (HA session) | `aiohttp.ClientSession()` per refresh; `await resp.read()` of 50 MB | `async_get_clientsession(hass)`; explicit `ClientTimeout(total=…)`; stream chunks to a temp file |
| HTTP `Content-Encoding: gzip` | Double-decompressing a `.gz` URL that aiohttp already decoded | Sniff magic bytes after download |
| HA calendar trigger | Assuming real-time reaction to EPG changes | 15-min forward-only polling; document it; never raise non-`HomeAssistantError` |
| HA calendar websocket subscriptions | Forgetting `async_write_ha_state()` after a data refresh | Write state after every coordinator update; it re-arms alarms and pushes to dashboards |
| Config entries / options | Update listener + `OptionsFlowWithReload` | `OptionsFlowWithReload` only (an error from 2026.12) |
| DataUpdateCoordinator (shared) | `async_config_entry_first_refresh()` with `config_entry=None` | `async_refresh()` and check `last_update_success`, then raise `ConfigEntryNotReady` manually |
| Repairs | Raising during setup for config problems | `ir.async_create_issue(...)` with a translation key; keep the entry loaded |
| TVHeadend / iptv-org / grabbers | Trusting spec compliance (UTC default, stop present, UTF-8 truth) | Per-source "no-offset means local" option, stop inference, last-good fallback |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full DOM parse | RAM spike ~8× file size | iterparse + clear | ≥ ~20 MB feeds on 2–4 GB devices |
| strptime per timestamp | Parse ~2 s slower per 200k stamps | Slice-based parser | ≥ 100k programmes, ARM devices |
| Regex over all programmes × all entries | Refresh scales with entries × patterns × text size | Precompile; match once per refresh in executor; normalize text once; truncate desc for matching | ≥ 5 entries with long descriptions |
| Linear scan in `event` / `async_get_events` | Dashboard lag; loop warnings | Sorted list + bisect | ≥ 10k matched programmes per entry |
| Keeping full multi-day history | Memory grows each refresh | Drop programmes ended > 1 day ago; keep only subscribed channels | Long uptime + frequent refresh |
| Eager `CalendarEvent` construction | CPU on loop at each write and view | Construct only for the requested slice; cap count | Broad filters (channel-only, no regex) |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Unrestricted local file path | Reads arbitrary host files; content leaks via logs/diagnostics | `hass.config.is_allowed_path()`, resolve symlinks, log positions not content |
| No decompressed-size limit | Gzip bomb exhausts memory or disk | Counting reader with a hard cap; abort with `UpdateFailed` |
| No download size/time limit | Hung refresh; disk fill | `ClientTimeout`, max-bytes cap while streaming |
| Unbounded user regex | ReDoS stalls executor thread indefinitely | Length caps; matching in executor; optional `regex` timeout |
| URLs with tokens in diagnostics/logs | Credential leak in shared diagnostics | `async_redact_data` on URL query; log host only |
| XML entity expansion | Billion-laughs memory blowup | Stdlib expat ≥ 2.4.1 has amplification protection (runtime has 2.9.0 **[verified: experiment]**); ElementTree doesn't fetch external entities. No defusedxml needed, but don't switch to a resolving parser |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No match preview in flow | Trial-and-error regex editing via repeated reloads | "Preview" step that shows the next 10 matches (title, channel, time) |
| Channel picker showing ids only | Can't find "Das Erste" among `ch123.de` ids | Label `Display Name (id)`, sorted, prefer HA language |
| Silent empty calendar | User thinks the integration is broken | Repair issues for missing channels and invalid regex; diagnostics with counts |
| Title template errors (`{chanel}` typo) | KeyError at runtime, empty calendar | Validate the template in the flow with a dummy programme; allowed placeholders listed in the field description |
| Timezone offset surprise | "All F1 sessions are 2 h off" | Per-source "timestamps without offset are local" option, explained in the help text |
| Too-short refresh interval | Provider ban | Minimum 1 h, default 12 h, and a note in the field description |

## "Looks Done But Isn't" Checklist

- [ ] **Timestamp parser:** handles 12-digit, no-offset, `+HH:MM`, alpha zones, DST nights. Verify with table tests in two HA timezones.
- [ ] **Stop inference:** last programme per channel and `stop <= start` are handled. Verify no `HomeAssistantError` from `CalendarEvent` with a malicious fixture.
- [ ] **Memory:** a 50 MB fixture parses under the tracemalloc budget. Verify in a CI test marked slow.
- [ ] **No loop blocking:** no `open`/`gzip`/`re` in `async def`. Verify with a grep in CI plus HA "Detected blocking call" absence in a manual run on `ha-host`.
- [ ] **State transitions:** state flips on/off at programme boundaries without a feed refresh. Verify with freezer tests.
- [ ] **Overlap semantics:** a running programme appears in today's range, and `event: end` triggers fire. Verify with boundary unit tests and one automation in the real HA.
- [ ] **Shared source lifecycle:** reloading or removing entry A doesn't affect B; the last unload frees everything. Verify with multi-entry tests and no lingering timers.
- [ ] **Options reload:** changed filters apply after save, without a re-download. Verify the log shows a reload and no HTTP request.
- [ ] **Empty regex fields:** an empty exclude doesn't empty the calendar. Verify with a unit test.
- [ ] **Invalid regex:** the form shows an inline error; setup with a corrupted stored regex creates a repair issue and doesn't crash.
- [ ] **Last-good data:** a truncated download keeps the old events. Verify with a test that refreshes using a broken payload.
- [ ] **HACS/hassfest:** both actions are green; repo description, topics, and issues are set; `brand/icon.png` is present; `hacs.json` min HA version is correct.
- [ ] **Translations:** every error and abort key exists in `en.json` (and `de.json`).
- [ ] **Diagnostics:** URL tokens are redacted.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Full-DOM parser shipped | MEDIUM | Swap to iterparse behind the same `parse_xmltv(path) -> ParsedFeed` interface; easy if P-Parser had no HA imports |
| Per-entry coordinators shipped | HIGH | Introduce a registry + refcount; migrate setup/unload; needs multi-entry tests written retroactively |
| Wrong timestamp semantics shipped | LOW–MEDIUM | Fix the parser; add a per-source offset option with a config entry migration (`async_migrate_entry`, bump `VERSION`/`MINOR_VERSION`) |
| Update listener + `OptionsFlowWithReload` | LOW | Remove the listener; test the reload path |
| Empty exclude bug in the wild | LOW | Normalize `""` to `None` at load time; bump minor version with a migration that cleans stored options |
| Channel id drift | LOW | Repair issue linking to the options flow; optional "match by display name" fallback |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1 Timestamp parsing | P-Parser | Table-driven tests incl. DST + 12-digit + no offset, in 2 TZs |
| 2 Missing/invalid stop | P-Parser, P-Calendar | Fixture with bad stops → no exception; inferred durations asserted |
| 3 Memory (DOM) | P-Parser, P-Source | tracemalloc budget test on 50 MB generated fixture |
| 4 Event loop blocking | P-Source, P-Filter | CI grep + manual HA run without "blocking call" logs |
| 5 Shared coordinator lifecycle | P-Source | Multi-entry reload/unload tests; no lingering timers |
| 6 Interval/source conflicts | P-Source (design), P-Flows | Documented rule; test min-interval recomputation |
| 7 Range semantics | P-Calendar | Boundary tests; `event: end` trigger integration test |
| 8 Live `event` property | P-Calendar | Freezer test crossing start/end without refresh |
| 9 Trigger window loss | P-Calendar, P-Release | `async_get_events` raises only `HomeAssistantError`; README limitation |
| 10 Regex safety/semantics | P-Filter, P-Flows | Unit tests: empty, invalid, ß/NFD, contains-semantics; flow error test |
| 11 Options reload | P-Flows | Options flow test asserts reload + new filters, no listener |
| 12 Channel id drift | P-Filter, P-Release | Repair issue test when channel disappears |
| 13 Malformed XML / last-good | P-Parser, P-Source | Broken-payload refresh test keeps data |
| 14 gzip/xz sniffing | P-Source | Tests: `.gz` served decoded, plain served as `.gz`, xz |
| 15 Over-downloading | P-Source | Restart test uses cache; 304 handling test |
| 16 Eager CalendarEvent | P-Calendar | Benchmark/assert count cap; no construction outside `async_get_events` |
| 17 Huge channel lists / slow flow | P-Flows | Progress step test; manual check with large fixture |
| 18 Episode/lang handling | P-Parser | xmltv_ns +1 tests; multi-lang fixture |
| 19 Local file read | P-Flows, P-Source | Disallowed path → form error test |
| 20 TZ in tests | P-Scaffold | conftest sets TZ explicitly; parametrized TZ tests |
| 21–22 hassfest/HACS | P-Scaffold, P-Release | Both GitHub Actions green from first commit |
| 23 probatio | P-Scaffold | No `voluptuous` in requirements; no error-text asserts |
| 24 Lingering timers | P-Source | Test suite green with `verify_cleanup` |
| 25 Recorder bloat | P-Calendar | Description truncation unit test |
| 26 Simulcast trigger floods | P-Release | README automation example uses `mode: queued` |

## Sources

- HA core `dev` source (2026.11.0.dev0), read directly:
  - `homeassistant/components/calendar/__init__.py`: `CalendarEvent` validation, `state`/`event`, alarms, websocket subscriptions
  - `homeassistant/components/calendar/helper.py`: `has_timezone`, `MIN_EVENT_DURATION = 0`
  - `homeassistant/components/calendar/trigger.py`: `UPDATE_INTERVAL = 15 min`, forward-only `Timespan`, `HomeAssistantError`-only catch
  - `homeassistant/helpers/update_coordinator.py`: implicit `config_entry` ContextVar binding, `async_on_unload(async_shutdown)`, `async_config_entry_first_refresh` requirements
  - `homeassistant/config_entries.py`: `OptionsFlowWithReload` vs update listeners `ValueError`
  - `homeassistant/components/backup/const.py`: `.cache/*` excluded from backups
  - `homeassistant/core_config.py`: `is_allowed_path`, `allowlist_external_dirs`
  - `homeassistant/package_constraints.txt`, `pyproject.toml`: Python ≥ 3.14.2, probatio 0.13.0, no `regex`/`lxml` pin
  - `script/hassfest/__main__.py`, `manifest.py`: plugins, key sorting, `version` required
- XMLTV DTD: https://github.com/XMLTV/xmltv/blob/master/xmltv.dtd (date format, optional `stop`, display-name order, `xmltv_ns` zero-based)
- HA developer docs: https://developers.home-assistant.io/docs/asyncio_blocking_operations/
- HA developer docs: https://developers.home-assistant.io/docs/core/integration/options_flow
- HA developer blog: https://developers.home-assistant.io/blog/2026/05/07/config-entry-listener-together-with-reloading-methods
- HA developer blog: https://developers.home-assistant.io/blog/2026/09/30/probatio-validation-engine
- HA developer blog: https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api and https://developers.home-assistant.io/docs/core/integration/brand_images
- HACS: https://hacs.xyz/docs/publish/action/ and https://hacs.xyz/docs/publish/integration/
- pytest-homeassistant-custom-component 0.13.372 (`common.py`: `US/Pacific`; `plugins.py`: `verify_cleanup`, `pytest_socket`)
- Provider download caps (LOW, old): https://old.tvheadend.org/issues/5364
- Local experiments (Python 3.14.7, expat 2.9.0):
  - strptime mis-parse and speed
  - DOM vs iterparse memory on a 100 MB synthetic feed
  - ParseError cases
  - cp1252 declaration handling
  - regex backtracking time, ß and NFD matching, empty-pattern behaviour

---
*Pitfalls research for: Home Assistant XMLTV calendar custom integration*
*Researched: 2026-10-12*
