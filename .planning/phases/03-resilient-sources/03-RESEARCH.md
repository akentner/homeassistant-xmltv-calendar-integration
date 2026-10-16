# Phase 3: Resilient Sources - Research

**Researched:** 2026-10-16
**Domain:** Home Assistant custom integration: DataUpdateCoordinator scheduling, on-disk feed cache with HTTP conditional requests, config/options flow (progress step, sections), Repairs, diagnostics, timezone handling in the pure XMLTV parser
**Confidence:** HIGH. Almost everything was read in the installed HA 2026.10.1 source or the project code this session, and key behaviours were probed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Refresh schedule & source options
- **D-01:** The schedule is a mode select: "interval" or "daily at". After the select, only the matching field is shown: refresh hours (existing `refresh_hours`, default 24, min 1, max 168 per Phase 1 D-13) or one `TimeSelector` time. Both fields are never active at the same time.
- **D-02:** "Daily at" takes exactly one time of day, evaluated in the HA configured timezone (e.g. 18:15 for a feed generated at 18:00). Multiple times are out of scope.
- **D-03:** A missed daily slot is caught up at start: if the most recent scheduled time is later than the cache's fetch time, the cache counts as stale and the source refreshes immediately.
- **D-04:** The source options flow edits **only** schedule (mode, hours, time) and timezone options (D-14..D-16). URL/path stay fixed (unique_id and duplicate check, SRC-13). The name is changed with HA's normal rename.
- **D-05:** Schedule and timezone options are also asked in the source setup flow, so the first parse already uses the right timezone settings. Setup and options share one schema builder.
- **D-06:** Entries stored before Phase 3 only have `refresh_hours`. A missing mode key means "interval"; missing timezone keys mean UTC and offset 0 (the Phase 1 D-14 behaviour). There is no entry migration and no version bump. — **Reversibility:** costly — the new option keys (mode, daily time, tz interpretation, offset minutes) become a stored contract. Renaming them later needs a config entry migration.
- **D-07:** A source options save reloads the entry. Use a plain `OptionsFlow`, never `OptionsFlowWithReload` (roadmap note). The Phase 2 diffing listener (`__init__.py:_async_entry_updated`) already reloads when data/options change. Calendar subentry edits still never reload (Phase 2 D-04).

#### Cache & startup
- **D-08:** For URL sources the disk cache holds the **raw feed bytes** as downloaded (gzip stays gzip) plus metadata: ETag, Last-Modified, fetch time. The location is `hass.config.cache_path` (roadmap note). At start or reload, a cache that is fresh for the schedule is parsed from disk in the executor, without network. The cache is removed when its entry is removed. — **Reversibility:** reversible — the cache is disposable. A format change can drop old files and re-download.
- **D-09:** The cache is fresh when its fetch time is within the configured interval, or (daily mode) later than the most recent scheduled time (D-03). When the cache is stale and the source cannot be reached at start, setup still **succeeds with the cached data**. The coordinator keeps retrying (D-10) and failure tracking runs (D-17). `ConfigEntryNotReady` is only raised when there is no cache at all and the first fetch fails (the current behaviour).
- **D-10:** After a failed refresh the source retries with a backoff (roughly 5 min → 15 min → 60 min → …). The backoff is capped at the regular schedule: the interval, or in daily mode at most until the next scheduled time. Exact steps are Claude's discretion.
- **D-11:** (local files) Local file sources get **no** disk cache. A refresh re-parses only when the file's mtime or size changed (the local equivalent of `304`). The allowed-path check still runs on every refresh. After a reload the file is parsed again, because nothing is cached in memory.
- **D-12:** `homeassistant.update_entity` on any calendar of a source triggers an immediate source refresh. It ignores cache freshness but still sends ETag / If-Modified-Since; a `304` means no re-download and no re-parse.
- **D-13:** The setup flow downloads the full feed once, with `async_show_progress` (CFG-03). That download **seeds the disk cache**, so the first coordinator refresh parses from the cache instead of downloading the feed a second time. Today the flow probes and then the coordinator downloads.

#### Timezone options (SRC-10)
- **D-14:** "Timestamps without offset" is a select with two values: **UTC** (default, XMLTV DTD, Phase 1 D-14) or **HA timezone** (`hass.config.time_zone`, DST-aware). Free IANA zones are out of scope.
- **D-15:** The offset correction is an integer in **minutes, −720..+720** (default 0). It shifts **all** start/stop timestamps after interpretation, whether they had an offset or not. Use case: feeds with a wrong offset.
- **D-16:** A timezone option change reloads the entry (D-07) and re-parses from the disk cache, with no download. Shifting data in memory is rejected. Because event UIDs use the UTC start (EVT-06), changed UIDs after a correction change are expected and acceptable.

#### Failure visibility
- **D-17:** A source counts as persistently failing when it has had **no successful refresh for more than 24 h**. The count of failed attempts does not matter. A `304` and a successful local-file mtime check both count as success. Then a Repairs issue is raised. It clears automatically after the next successful refresh.
- **D-18:** The Repairs issue is **info only** (not fixable). It names the source, the last success time and the failure reason (translated reason key, never the URL or credentials).
- **D-19:** During failures the calendars stay **available** and show the last good data (SRC-08), so calendar triggers keep working. There are no extra stale attributes on the calendar. The failure state is visible in Repairs and diagnostics.
- **D-20:** A feed that parses but yields **0 programmes** counts as a failure. The last good data is kept and failure tracking runs. A feed that merely has fewer programmes than before is accepted.
- **D-21:** Diagnostics per source (SRC-12) show:
  - source type and redacted URL/path (`async_redact_data`, no credentials or query secrets)
  - schedule and timezone options
  - last success and last failure, with time and reason
  - cache metadata (fetch time, ETag/Last-Modified present, size)
  - programme and channel counts, `skipped_malformed` (covers Phase 1 review WR-08)
  - per-calendar match counts

### Claude's Discretion
- Exact backoff steps (D-10) and how they combine with the daily-time scheduling, e.g. `async_track_point_in_time` vs a dynamic `update_interval`.
- Cache file layout: one file per entry, named by entry_id; metadata in a sidecar JSON or an HA `Store`. Also whether writes are atomic (write to a temp file, then rename).
- Progress-flow mechanics (`async_show_progress` task, `progress_action` texts) and how the setup download hands its bytes to the cache.
- Whether failure timestamps survive a restart (needed for the 24 h threshold across restarts), e.g. stored with the cache metadata.
- Logging levels for refresh failures, 304s and cache hits.

### Deferred Ideas (OUT OF SCOPE)
- Reconfigure flow for a source's URL/path (with duplicate check). Not part of CFG-02, possible backlog item.
- Multiple daily refresh times.
- Free IANA timezone choice for timestamps without offset.
- Stale/last-success attributes on calendar entities.
- Fixable Repairs flow leading to the source options.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SRC-05 | Refresh once daily at a fixed time | Pure `schedule.py` (`last_slot`/`next_slot` with zoneinfo), with a wall-clock target applied through a `_schedule_refresh` override (Pattern 2). DST behaviour probed. |
| SRC-06 | Disk cache, restart/reload uses it while fresh | `FeedCache` (payload in `cache_path`, metadata in `Store`). The first refresh parses a valid cache without network (Pattern 3). `hass_config_dir` override in tests (Wave 0). |
| SRC-07 | Re-download only when changed (ETag / If-Modified-Since) | `async_fetch_url(..., etag=, last_modified=)` returns `NotModified` on 304. Probed with `aioclient_mock` (Pattern 4). |
| SRC-08 | Failure keeps last good data, calendars keep working | Coordinator keeps `self.data` on `UpdateFailed` (verified). `available` override, identity guard on refilter (Pattern 5). |
| SRC-10 | Local-time interpretation and offset correction | `parse(..., naive_tz=, shift=)` threaded into `parse_xmltv_time`. The shift is applied in UTC (DST pitfall probed). |
| SRC-11 | Repairs issue on persistent failure, clears on success | `issue_registry.async_create_issue/async_delete_issue`, one translation key per reason, re-evaluated at setup (Pattern 6). |
| SRC-12 | Diagnostics with redaction and counts | `diagnostics.py` with `async_get_config_entry_diagnostics`. URL reduced to scheme+host. Counts from `ParseStats` and the per-entity `len(MatchIndex)` (Pattern 7). |
| CFG-02 | Options flow for refresh and timezone options | Plain `OptionsFlow`: `init` (mode + timezone section) → `schedule` → `async_create_entry(data=full options)`. The existing listener reloads (Pattern 8). |
| CFG-03 | Progress indicator during setup download | `async_show_progress(progress_action="download", progress_task=...)` with `eager_start=False`. On failure, `async_show_progress_done(next_step_id="url")` plus stored error (Pattern 9). |
| AUT-04 | Manual refresh via `homeassistant.update_entity` | Already wired: `CoordinatorEntity.async_update` → `coordinator.async_request_refresh()` (verified). Phase 3 must make a non-first refresh always hit the network (with validators), and add the test. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python 3.14, HA custom component, `uv` for deps, Ruff 0.17.0 with `select = ["ALL"]`, 120-char lines. Code, comments and commits in English.
- **Config Flow + Options Flow only** (no YAML). Plain `OptionsFlow` plus exactly one diffing update listener, never `OptionsFlowWithReload` (STATE.md [Init]).
- **Zero runtime requirements** (`"requirements": []`). Stdlib only for parsing, HA built-ins for everything else.
- Large feeds must not block the event loop: all file IO and parsing go in one executor job. `hass.config.is_allowed_path()` also runs in the executor.
- Never create an own `aiohttp.ClientSession`. Use `async_get_clientsession(hass)`.
- Don't use `OptionsFlowWithConfigEntry` or `hass.data[DOMAIN][entry_id]`. Use `entry.runtime_data`. Pass `config_entry=` to the coordinator.
- Established in Phases 1/2: URLs are never logged, only the host. Error texts are translation keys. `source.py` keeps builtin `open()` so the `forbid_loop_io` test guard works. A missing stored key means the default, with no migration. The pure `xmltv/` package has no HA imports (enforced by `tests/xmltv/test_purity.py`) and is built test-first.
- `tdd_mode: true`, `security_enforcement: true` (ASVS L1), `nyquist_validation: false` (so there is no Validation Architecture section).
- GSD workflow: changes go through `/gsd-execute-phase`. The user expects detailed, goal-backward verifiable plans and minimal, atomic implementations.
- Translations: de.json and en.json key/placeholder parity is enforced by `tests/test_translations.py`. hassfest skips de.json for custom integrations, so that test enforces its rules.

## Summary

Phase 3 is almost entirely **HA glue around existing building blocks**. No new libraries are needed. The installed HA 2026.10.1 source confirms what each mechanism needs.
- **Coordinator failures:** `DataUpdateCoordinator` already keeps `self.data` when `_async_update_data` raises `UpdateFailed`. It ignores `retry_after` during the first refresh. It reads `update_interval` again each time it schedules, from `_schedule_refresh`.
- **Manual refresh:** `homeassistant.update_entity` already reaches `coordinator.async_request_refresh()` through `CoordinatorEntity.async_update`.
- **Progress step:** `async_show_progress` needs a real `progress_task`, and a progress step may only transition to progress or progress-done.
- **Repairs:** issues are non-persistent by default. Their reason text must be a separate translation key per reason, because `HomeAssistantError` messages are always English.

The core design problem is **one decision function in the coordinator**:
- **Inputs:** cache validity, cache freshness, schedule mode, first-vs-later refresh, and HTTP outcome (200 / 304 / error / 0 programmes).
- **Outputs:** which data to return (new parse, the same object, or the parsed cache), what to persist (payload plus metadata, or metadata only), how failures are tracked (success/failure, Repairs), and when the next refresh runs (a wall-clock target).

Keep schedule maths (fresh / last slot / next slot / backoff) in a **pure, test-first module**. Keep the cache in a small `FeedCache` helper. The coordinator then only orchestrates.

**Primary recommendation:**
- **Scheduling:** keep one wall-clock `_next_refresh_at` target on the coordinator and convert it to `update_interval` in a `_schedule_refresh` override.
- **Cache:** raw bytes go in `cache_path(DOMAIN, f"{key}.feed")`, metadata plus health in an HA `Store`. The key is the entry's `unique_id`, so the flow can seed it.
- **Failure handling:** raise `UpdateFailed` for later failures, keeping HA's built-in logging, with `available` overridden. Return the parsed cache during the first refresh whenever a valid cache exists (stale-while-revalidate).
- **Repairs:** track "failing since" in the Store and re-evaluate the issue at every outcome and at setup.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Schedule maths (fresh, last/next daily slot, backoff) | Pure Python module (no HA) | Coordinator (applies it) | Deterministic and DST-sensitive, so it needs exhaustive unit tests without HA |
| Conditional download, 304 detection, validators | `source.py` (HA HTTP session) | — | Already owns bounded download and host-only logging |
| Raw-feed cache (payload + metadata), removal | `cache.py` helper (executor IO + `Store`) | Config flow (seeds it), `__init__` (removes it) | Shared by flow and coordinator, and blocking IO must stay off the loop |
| Refresh decision, data retention, health tracking | `coordinator.py` | `schedule.py`, `cache.py`, `source.py` | Single orchestration point. HA's coordinator semantics live here |
| Timezone interpretation + offset correction | Pure `xmltv/` parser (`timeparse.py`, `parser.py`) | Coordinator (passes tz/shift) | Purity rule: tz is passed in as a `tzinfo`, with no HA import |
| Repairs issue lifecycle | Coordinator (health) via `issue_registry` | `__init__.async_remove_entry` (cleanup) | Raised and cleared exactly where outcomes are known |
| Diagnostics | `diagnostics.py` | Coordinator (exposes state), calendar entity (match count) | HA discovers the platform by module name |
| Options / setup schema | `config_flow.py` (shared builders) | translations | D-05: one schema builder for setup and options |
| Availability during failure | `calendar.py` entity | — | D-19: entity-level `available` override |

## Standard Stack

### Core (all HA built-ins or stdlib; nothing to install)
| Library / API | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `homeassistant.helpers.update_coordinator.DataUpdateCoordinator` | HA 2026.10.1 | Refresh orchestration, data retention on failure, debounced manual refresh | Already in use. Failure semantics verified in source [VERIFIED: .venv/.../helpers/update_coordinator.py:434-613] |
| `homeassistant.helpers.storage.Store` | HA 2026.10.1 | Per-source metadata + health JSON (atomic, async, moves corrupt files aside) | HA's standard persistence. Mocked in memory by phcc's `hass_storage` fixture [VERIFIED: helpers/storage.py:225-240, 304-420] |
| `hass.config.cache_path(*path)` | HA ≥ 2026.3 | Raw payload location, excluded from backups | Returns `self.path(".cache", *path)`. Backups exclude `".cache/*"` [VERIFIED: core_config.py:637-645; components/backup/const.py:27] |
| `homeassistant.util.file.write_utf8_file(filename, data, private, mode)` | HA 2026.10.1 | Atomic temp-file plus `os.replace` write, also for bytes with `mode="wb"` | No fsync cost (unlike `write_utf8_file_atomic`). Raises `WriteError` [VERIFIED: util/file.py:46-80] |
| `homeassistant.helpers.issue_registry` (`async_create_issue`, `async_delete_issue`, `IssueSeverity`) | HA 2026.10.1 | Repairs issue | Deleting a missing issue is not an error [VERIFIED: helpers/issue_registry.py:339-353, 415-421] |
| `homeassistant.helpers.redact.async_redact_data` | HA 2026.10.1 | Diagnostics redaction. Accepts a mapping of key → callable | [VERIFIED: helpers/redact.py:30-80] |
| `FlowHandler.async_show_progress` / `async_show_progress_done` / `async_update_progress` | HA 2026.10.1 | Download progress in the setup flow | [VERIFIED: data_entry_flow.py:809-875] |
| `homeassistant.data_entry_flow.section` | HA 2026.10.1 | Collapsible "Timezone" group | [VERIFIED: data_entry_flow.py:939-953] |
| `homeassistant.config_entries.OptionsFlow` | HA 2026.10.1 | Source options. `self.config_entry` is a property (not usable in `__init__`) | [VERIFIED: config_entries.py:4135-4182] |
| stdlib `zoneinfo` / `datetime` | Python 3.14.7 | Daily slot maths and naive → local interpretation | DST behaviour probed this session |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `homeassistant.util.dt` (`utcnow`, `get_default_time_zone`, `as_local`) | HA built-in | Current time and HA tz to pass into pure code | Every schedule computation and every parse call |
| `pytest_homeassistant_custom_component.components.diagnostics.get_diagnostics_for_config_entry` | phcc 0.13.372 | End-to-end diagnostics test (needs `hass_client`) | One integration test. Unit-test the function directly otherwise [VERIFIED: phcc components/diagnostics/__init__.py:37-44] |
| `pytest_homeassistant_custom_component.common.async_fire_time_changed` | phcc 0.13.372 | Fires due loop `TimerHandle`s, so coordinator `loop.call_at` schedules fire under `freezer` | Schedule tests [VERIFIED: phcc common.py:539-563] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Wall-clock target + `_schedule_refresh` override | `async_track_point_in_utc_time` for the daily slot | Wall-clock exact, but bypasses the coordinator's debouncer lock, `pref_disable_polling` and cancel-on-unload. Needs its own unsubscribe and races with `update_entity`. Rejected. |
| Wall-clock target + override | Plain `update_interval` set at the end of each refresh plus `UpdateFailed(retry_after=…)` | Uses only public API. But `retry_after` is ignored in the first refresh, and the relative interval goes stale when the last listener is removed and later re-added (it re-arms with the old delay). Acceptable fallback if the override ever breaks. |
| Raise `UpdateFailed` on later failures (keep HA logging) | Never raise while data exists; track failures only internally | Keeps entities available without an override. But it breaks the existing `test_refresh_with_truncated_gzip_keeps_previous_data` contract (`last_update_success is False`, `last_exception.translation_key == "invalid_feed"`) and loses HA's once-per-streak ERROR/"recovered" logs. Rejected. |
| `Store` for metadata | Sidecar JSON next to the payload in `.cache` | Both are disposable. `Store` gives atomic JSON, corruption handling and phcc in-memory mocking (`hass_storage`). A sidecar is not backed up (nor is it needed). Either works. `Store` is recommended. |
| Cache keyed by `entry.unique_id` | Keyed by `entry_id` | `entry_id` does not exist while the flow runs, so the flow could not seed the cache (D-13). `unique_id` is already the SHA-256 of the source and safe for the filesystem. Fall back to `entry_id` when `unique_id` is `None` (tests' `MockConfigEntry`). |
| Per-reason issue translation keys | One key plus `{reason}` placeholder filled from `str(UpdateFailed)` | `HomeAssistantError.__str__` / `async_get_exception_message` always use **English** (`language = "en"`) [VERIFIED: exceptions.py `__str__` docstring; helpers/translation.py:442]. A German UI would then show an English reason. Rejected for D-18 ("translated reason key"). |

**Installation:** none. `manifest.json` `"requirements": []` stays unchanged.

## Package Legitimacy Audit

This phase installs **no external packages**: all APIs are HA built-ins or the Python stdlib, and `manifest.json` requirements stay `[]`. Dev dependencies (phcc 0.13.372, ruff 0.17.0) are unchanged from Phase 1.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| — | — | — | — | — | — | No packages added |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                ┌──────────── Setup flow (URL) ─────────────┐
 user ─► url step (url + mode + [timezone section])
            │ normalize, duplicate check (unique_id)
            ▼
        download step ── async_show_progress(task) ──► async_fetch_url(full, no validators)
            │ ok                              │ error / not a feed
            ▼                                 └─► progress_done → url step (stored error)
        schedule step (refresh_hours | refresh_time)
            ▼
        name step ──► FeedCache.write(unique_id, payload, etag, last_modified, fetched_at)  [executor + Store]
            ▼
        async_create_entry(data={source_type,url}, options={mode,hours|time,tz,offset})
                                                           │
 HA start / reload ─► async_setup_entry ─► coordinator.async_config_entry_first_refresh()
                                                           ▼
                         ┌──────── _async_update_data (decision) ─────────┐
   first refresh? ──yes─► cache valid (source_id + size)? ──yes─► parse cache (executor)
        │                     │ no                                 │ ok: return epg, target = fresh? stale-at : now
        │                     ▼                                    │ parse fails: drop cache ─┐
        no ──────────────► network: GET with If-None-Match / If-Modified-Since (only if cache valid)
                              │
           ┌──────────────────┼──────────────────────┬───────────────────────────┐
          304                200                 error (net/HTTP/size)       200 but parse error / 0 programmes
           │                  │                      │                           │
  data in memory?      parse bytes (executor)   first refresh & cache? ─yes─► return parsed cache
   yes: return same     >0 programmes:           no (later) ─► record failure, raise UpdateFailed
   no:  parse cache     write payload+meta,       no cache & first ─► UpdateFailed → ConfigEntryNotReady
   update fetched_at    return new epg
           │                  │                      │
           └──── health.success() ──► delete issue   └── health.failure(reason) ──► issue if failing > 24 h
                              │
                 target = next regular (interval / next daily slot) or backoff (capped)
                              ▼
            _schedule_refresh override: update_interval = max(target - utcnow, 1 s)
                              ▼
     listeners (calendar entities): refilter only if coordinator.data is a new object
                              ▲
 homeassistant.update_entity ─┘ (CoordinatorEntity.async_update → async_request_refresh → non-first path)
```

### Recommended Project Structure
```
custom_components/xmltv_calendar/
├── schedule.py        # NEW, pure stdlib: Schedule, last_slot, next_slot, is_fresh, next_regular, backoff_delay
├── cache.py           # NEW: FeedCache (payload path in cache_path, Store metadata, read/write/remove; executor IO)
├── diagnostics.py     # NEW: async_get_config_entry_diagnostics
├── coordinator.py     # decision function, health tracking, Repairs sync, _schedule_refresh override
├── source.py          # async_fetch_url(..., etag, last_modified) -> Fetched | NotModified; file stat helper
├── config_flow.py     # shared schema builders, download progress step, schedule step, XmltvOptionsFlow
├── __init__.py        # async_remove_entry (cache + Store + issue cleanup)
├── calendar.py        # available override, identity guard, match_count property
├── const.py           # new option keys + defaults
├── translations/{en,de}.json   # options, progress, issues, new exception key, selector option labels
└── xmltv/
    ├── timeparse.py   # parse_xmltv_time(value, naive_tz=UTC)
    └── parser.py      # parse(..., naive_tz=UTC, shift=timedelta(0))
tests/
├── conftest.py        # Wave 0: hass_config_dir -> hass_tmp_config_dir (autouse)
├── test_schedule.py   # pure, test-first (DST cases)
├── test_cache.py      # FeedCache + restart/reload behaviour
├── test_refresh.py    # 200/304/error/0-programme matrix, backoff, update_entity
├── test_repairs.py    # 24 h threshold, clear on success, re-evaluate at setup
├── test_diagnostics.py
├── test_options_flow.py
└── xmltv/test_timeparse.py, test_parser.py   # naive_tz + shift cases
```

### Pattern 1: Pure schedule module (test-first)
**What:** All time maths lives in pure functions taking `now` (aware UTC), the schedule and a `tzinfo`.
**When to use:** freshness at start (D-03, D-09), next regular refresh, backoff cap (D-10).
```python
# schedule.py: pure stdlib, no HA imports (same rule as xmltv/)
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta, tzinfo

BACKOFF = (timedelta(minutes=5), timedelta(minutes=15), timedelta(hours=1), timedelta(hours=3), timedelta(hours=6))

@dataclass(frozen=True, slots=True)
class Schedule:
    interval: timedelta | None  # interval mode
    daily_at: time | None       # daily mode, evaluated in tz
    tz: tzinfo

def last_slot(now: datetime, s: Schedule) -> datetime:
    """Most recent daily slot <= now (aware UTC)."""
    local = now.astimezone(s.tz)
    slot = datetime.combine(local.date(), s.daily_at, tzinfo=s.tz)
    if slot > now:
        slot = datetime.combine(local.date() - timedelta(days=1), s.daily_at, tzinfo=s.tz)
    return slot.astimezone(UTC)

def next_slot(now: datetime, s: Schedule) -> datetime:
    """First daily slot strictly after now (aware UTC)."""
    local = now.astimezone(s.tz)
    for days in (0, 1, 2):  # 2 covers a slot swallowed by a DST gap edge
        slot = datetime.combine(local.date() + timedelta(days=days), s.daily_at, tzinfo=s.tz).astimezone(UTC)
        if slot > now:
            return slot
    raise AssertionError("unreachable")

def is_fresh(fetched_at: datetime, now: datetime, s: Schedule) -> bool:
    if fetched_at > now:  # clock went backwards: never trust a future fetch time
        return False
    if s.daily_at is not None:
        return fetched_at >= last_slot(now, s)
    return now - fetched_at < s.interval

def backoff_delay(failures: int, now: datetime, regular_next: datetime) -> timedelta:
    """D-10: 5 m, 15 m, 1 h, 3 h, 6 h, 6 h, ... capped at the next regular refresh."""
    step = BACKOFF[min(failures - 1, len(BACKOFF) - 1)]
    return max(min(step, regular_next - now), timedelta(seconds=1))
```
Probed this session: `datetime(2026, 3, 29, 2, 30, tzinfo=ZoneInfo("Europe/Berlin"))` (a nonexistent wall time) maps to `01:30 UTC`, i.e. it fires at 03:30 CEST. Acceptable, but pin it in a test. The backoff steps are a discretion choice [ASSUMED].

### Pattern 2: Wall-clock target converted at scheduling time
**What:** The coordinator holds `self._next_refresh_at: datetime` (UTC) and sets it after every outcome. A `_schedule_refresh` override turns it into `update_interval` right before HA arms `loop.call_at`.
**Why:** HA's `_schedule_refresh` uses `self._update_interval_seconds` (relative) and is called after every refresh and **when the first listener is added** [VERIFIED: update_coordinator.py:182-188, 259-294, 600-601]. A relative delay computed long ago would re-arm wrong after "all calendars removed → one added". It also lets backoff and daily mode share one mechanism, without `retry_after` (which is ignored in the first refresh: `if err.retry_after is not None and not raise_on_entry_error` [VERIFIED: update_coordinator.py:518]).
```python
MIN_DELAY = timedelta(seconds=1)

@callback
@override
def _schedule_refresh(self) -> None:
    # update_interval must never be timedelta(0): the setter treats a falsy value as None (= no polling)
    self.update_interval = max(self._next_refresh_at - dt_util.utcnow(), MIN_DELAY)
    super()._schedule_refresh()
```
Verified: the setter is `self._update_interval_seconds = value.total_seconds() if value else None` [VERIFIED: update_coordinator.py:257], and `not timedelta(0)` is `True` (probed). `_schedule_refresh` is a single-underscore method (overridable). Add a test that would fail if HA stopped calling it: daily slot fires after removing and re-adding the only calendar. It still respects `pref_disable_polling` [VERIFIED: update_coordinator.py:265-266].

### Pattern 3: Stale-while-revalidate first refresh
**What:** In the **first** refresh (`self.data is None`), a *valid* cache is always parsed and returned:
- If it is fresh, `_next_refresh_at = fetched_at + interval` (or `next_slot`).
- If it is stale (including a missed daily slot, D-03), `_next_refresh_at = now`, so the network refresh runs about 1 s after setup in the background.

The network is only hit during setup when there is no valid cache. D-09's outcome ("stale + offline ⇒ setup succeeds with cached data") follows directly, setup is never blocked by a slow or blackholed host (`DOWNLOAD_TIMEOUT = aiohttp.ClientTimeout(total=300, sock_read=60)` [VERIFIED: source.py:30]), and an unchanged feed costs exactly one parse: the background conditional GET returns 304 and the in-memory data is kept.

"Valid cache" means all of the following:
- the payload file exists;
- its size equals the stored `size`;
- the stored `source_id` equals `source_unique_id(source_type, locator)` for the entry's current data.

The `source_id` check matters because `test_data_change_reloads_once` changes the URL in place [VERIFIED: tests/test_init.py:141-156].

If the cache parse fails, delete the cache and fall through to an unconditional GET.

**Variant:** network-first when stale. It blocks setup for up to the download timeout, so use it only if the user insists.

### Pattern 4: Conditional GET result type
```python
# source.py
@dataclass(frozen=True, slots=True)
class Fetched:
    payload: bytes
    etag: str | None
    last_modified: str | None

class NotModified: ...  # singleton sentinel or dataclass

async def async_fetch_url(hass, url, *, etag=None, last_modified=None) -> Fetched | NotModified:
    headers = {}
    if etag: headers[hdrs.IF_NONE_MATCH] = etag            # echo verbatim (keep W/ and quotes)
    if last_modified: headers[hdrs.IF_MODIFIED_SINCE] = last_modified  # echo verbatim, never reformat
    async with session.get(url, timeout=DOWNLOAD_TIMEOUT, headers=headers) as response:
        if response.status == HTTPStatus.NOT_MODIFIED: return NOT_MODIFIED
        ...existing bounded streaming...
        return Fetched(b"".join(chunks), _validator(response.headers.get(hdrs.ETAG)),
                       _validator(response.headers.get(hdrs.LAST_MODIFIED)))
```
Probed with phcc: `aioclient_mock.get(url, status=304, headers={"ETag": '"v1"'})` yields `resp.status == 304`, an empty body and `resp.headers.get("etag") == '"v1"'`, and `aioclient_mock.mock_calls[-1][3] == {'If-None-Match': '"v1"'}` records the sent headers [VERIFIED: probe run, phcc test_util/aiohttp.py:142-176]. `side_effect` receives `(method, url, data)` only, not the headers, so tests assert headers through `mock_calls[i][3]` and change responses with `clear_requests()` + re-register (which also clears `mock_calls`) [VERIFIED: phcc test_util/aiohttp.py:129-133].

Only send validators when the cache is valid; otherwise a 304 leaves nothing to parse.

### Pattern 5: Availability and refilter identity guard (D-19)
- `CoordinatorEntity.available` returns `self.coordinator.last_update_success` [VERIFIED: update_coordinator.py:726-728]. Override it in `XmltvCalendarEntity`: `return self.coordinator.data is not None`.
- On a success→failure transition the coordinator calls listeners even though `data` is unchanged [VERIFIED: update_coordinator.py:605-613]. `_handle_coordinator_update` currently always refilters [VERIFIED: calendar.py:131-133]. Guard it: if `self.coordinator.data is self._epg`, only `async_write_ha_state()` (or return).
- Set `always_update=False` on the coordinator. `EpgData` is `@dataclass(frozen=True, eq=False)` [VERIFIED: xmltv/model.py:50], so `previous_data != self.data` is an identity check: returning the same object on a 304 or an unchanged file triggers no listener calls, while a new parse does.

### Pattern 6: Health tracking and Repairs lifecycle (D-17, D-18)
**Persisted in the Store** (survives restart and `ConfigEntryNotReady` retries):
- `last_success` (ISO UTC);
- `failing_since` (ISO UTC of the first failure after the last success, else null);
- `last_failure` `{time, reason}`;
- `consecutive_failures` (int, drives the backoff index).

**On success** (200 parsed, 304, unchanged file): set `last_success = now`, `failing_since = None`, `consecutive_failures = 0`, then `ir.async_delete_issue(hass, DOMAIN, f"source_failing_{entry_id}")`.

**On failure:** record `last_failure`, set `failing_since` if it is null, and increment `consecutive_failures`. If `now - failing_since > 24 h`, call:
```python
ir.async_create_issue(
    hass, DOMAIN, f"source_failing_{entry.entry_id}",
    is_fixable=False, is_persistent=False, severity=ir.IssueSeverity.WARNING,
    translation_key=f"source_failing_{reason}",  # reason ∈ the coordinator's translation keys
    translation_placeholders={"source": entry.title, "last_success": last_success_local_or_dash},
)
```
- Re-creating an existing issue with another `translation_key` replaces it in place [VERIFIED: issue_registry.py `async_get_or_create` replace branch].
- **At setup:** evaluate the persisted health once, so a fresh-cache start does not hide a still-failing source. Non-persistent issues are not restored after restart [VERIFIED: issue_registry.py:83-90, 270].
- **In `async_remove_entry`:** delete the issue.
- **Reasons** (translation keys already used, quoted verbatim from coordinator.py:73-121): `translation_key="feed_too_large"`, `translation_key="unable_to_fetch"`, `translation_key="path_not_allowed"`, `translation_key="file_not_found"`, `translation_key="invalid_feed"`. D-20 adds a new one; the name `empty_feed` is a proposal [ASSUMED].
- Diagnostics automatically include the domain's issues in the payload [VERIFIED: components/diagnostics/__init__.py `payload["issues"]`].

### Pattern 7: Diagnostics
```python
# diagnostics.py
from homeassistant.helpers.redact import REDACTED, async_redact_data

def _redact_url(url: str) -> str:
    u = URL(url)
    return f"{u.scheme}://{u.host}/{REDACTED}"  # no userinfo, path, query

def _redact_path(path: str) -> str:
    return f"{REDACTED}/{PurePath(path).name}"

async def async_get_config_entry_diagnostics(hass, entry: XmltvConfigEntry) -> dict[str, Any]:
    c = entry.runtime_data.coordinator
    return {
        "source": async_redact_data(dict(entry.data), {CONF_URL: _redact_url, CONF_PATH: _redact_path}),
        "options": dict(entry.options),
        "health": c.health.as_dict(),            # last_success, last_failure{time, reason}, failing_since
        "cache": c.cache_info(),                 # fetched_at, has_etag, has_last_modified, size (never the values' secrets)
        "stats": dataclasses.asdict(c.data.stats) if c.data else None,  # programmes, channels, skipped_malformed, ...
        "calendars": {sid: {"title": e.name_for_diag, "matches": len(e.match_index)} for sid, e in entry.runtime_data.calendars.items()},
        "next_refresh": c.next_refresh_at.isoformat(),
    }
```
- `async_redact_data` accepts `Mapping[key, callable]` [VERIFIED: redact.py:59-63].
- `ParseStats` fields, quoted from xmltv/model.py:37-46: `programmes`, `channels`, `skipped_malformed`, `duplicates`, `inferred_stops`, `dropped_past`.
- `MatchIndex` defines `__len__` [VERIFIED: xmltv/window.py:28].
- Do not dump the raw ETag/Last-Modified values. Presence is enough (D-21).

### Pattern 8: Options flow with shared builders (D-01, D-04, D-05, D-07)
```python
def _source_settings_schema() -> vol.Schema:   # mode + timezone section; setup steps add url/path in front
    return vol.Schema({
        vol.Required(CONF_REFRESH_MODE, default=REFRESH_MODE_INTERVAL): SelectSelector(SelectSelectorConfig(
            options=[REFRESH_MODE_INTERVAL, REFRESH_MODE_DAILY], mode=SelectSelectorMode.LIST, translation_key="refresh_mode")),
        vol.Required("timezone"): section(vol.Schema({
            vol.Required(CONF_NAIVE_TZ, default=NAIVE_TZ_UTC): SelectSelector(SelectSelectorConfig(
                options=[NAIVE_TZ_UTC, NAIVE_TZ_LOCAL], translation_key="naive_tz")),
            vol.Required(CONF_OFFSET_MINUTES, default=0): NumberSelector(NumberSelectorConfig(
                min=-720, max=720, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="min")),
        }), {"collapsed": True}),
    })

def _schedule_schema(mode: str) -> vol.Schema:  # exactly one field (D-01)
    if mode == REFRESH_MODE_DAILY:
        return vol.Schema({vol.Required(CONF_REFRESH_TIME): TimeSelector()})
    return vol.Schema({vol.Required(CONF_REFRESH_HOURS, default=DEFAULT_REFRESH_HOURS): _refresh_selector()})

class XmltvOptionsFlow(OptionsFlow):            # plain OptionsFlow (D-07); never touch self.config_entry in __init__
    async def async_step_init(self, user_input=None): ...      # -> async_step_schedule
    async def async_step_schedule(self, user_input=None):
        ...
        return self.async_create_entry(data=self._options)     # replaces entry.options -> listener diff -> reload
```
- `async_create_entry(data=…)` in an options flow becomes `async_update_entry(entry, options=result["data"])` [VERIFIED: config_entries.py:4114-4115]. Always write the **complete** options dict, including the inactive schedule field's previous value so switching back pre-fills.
- Section values arrive nested (`user_input["timezone"][...]`). Flatten them before storing.
- The `TimeSelector` returns the raw validated string (`cv.time(data); return data`) [VERIFIED: helpers/selector.py:2310-2313]. Reuse `normalize_time` (`"HH:MM[:SS]"` → `"HH:MM"`) [VERIFIED: xmltv/settings.py:65-73] and suggest `f"{value}:00"` back, as Phase 2 does.
- Existing option key and defaults, verbatim from const.py:31-34: `CONF_REFRESH_HOURS = "refresh_hours"`, `DEFAULT_REFRESH_HOURS = 24`, `MIN_REFRESH_HOURS = 1`, `MAX_REFRESH_HOURS = 168`.
- New key names (`refresh_mode`, `refresh_time`, `naive_timezone`, `offset_minutes`) and the values (`interval`/`daily`, `utc`/`local`) are proposals. They become a stored contract under D-06, so lock them in the plan [ASSUMED].
- Register with `@staticmethod @callback def async_get_options_flow(config_entry) -> XmltvOptionsFlow: return XmltvOptionsFlow()` [VERIFIED: config_entries.py:3177-3187].

### Pattern 9: Download progress step (CFG-03, D-13)
```python
async def async_step_download(self, user_input=None) -> ConfigFlowResult:
    if self._download_task is None:
        # eager_start=False: the first call always shows progress (deterministic tests, as core shelly/hyperion do)
        self._download_task = self.hass.async_create_task(
            async_fetch_url(self.hass, self._data[CONF_URL]), eager_start=False)
    if not self._download_task.done():
        return self.async_show_progress(step_id="download", progress_action="download",
                                        progress_task=self._download_task)
    task, self._download_task = self._download_task, None
    try:
        fetched = task.result()
    except SourceTooLargeError: self._errors = {"base": "feed_too_large"}  # new flow error key [ASSUMED]
    except SourceError:         self._errors = {"base": "cannot_connect"}
    else:
        if looks_like_feed(fetched.payload[:PROBE_BYTES]):
            self._fetched = fetched
            return self.async_show_progress_done(next_step_id="schedule")
        self._errors = {"base": "invalid_feed"}
    return self.async_show_progress_done(next_step_id="url")   # url step shows self._errors + last input
```
- A progress step may only return SHOW_PROGRESS or SHOW_PROGRESS_DONE, otherwise it raises `ValueError("Show progress can only transition to …")` [VERIFIED: data_entry_flow.py:405-414]. That is why errors go back through `progress_done(next_step_id="url")`.
- `async_configure` loops while the result is SHOW_PROGRESS_DONE, so the follow-up form comes back in the same call [VERIFIED: data_entry_flow.py:338-342].
- The manager cancels the progress task when the flow is removed [VERIFIED: data_entry_flow.py:470].
- Use `hass.async_create_task` (tracked) rather than a background task, so `hass.async_block_till_done()` in tests waits for it.
- `async_update_progress(fraction)` can drive a progress bar when `Content-Length` is known. Optional polish [VERIFIED: data_entry_flow.py:849-854].
- The test sequence: `configure(url form)` → `SHOW_PROGRESS` with `progress_action == "download"` → `await hass.async_block_till_done()` → `configure(flow_id)` → `FORM` step `schedule`.
- **Seeding:** keep `self._fetched` on the flow and write the cache in the final `name` step, right before `async_create_entry`, using `FeedCache.async_write(key=self.unique_id, ...)`. This avoids orphan files when the user abandons the flow. If the write fails, log at debug and continue; the coordinator then downloads.
- Translation location: `config.progress.download`, the same shape as core ollama's `config_subentries.*.progress.download` [VERIFIED: components/ollama/strings.json].

### Pattern 10: Timezone threading in the pure parser (SRC-10, D-14..D-16)
```python
# timeparse.py
def parse_xmltv_time(value: str | None, naive_tz: tzinfo = UTC) -> datetime | None:
    ...
    else:
        tz = naive_tz  # D-14: UTC by default, or the HA zone (DST-aware via zoneinfo)

# parser.py: _programme(elem, naive_tz, shift)
start = parse_xmltv_time(elem.get("start"), naive_tz)
...
if shift:  # D-15: shift the instant, never the wall clock
    start = start.astimezone(UTC) + shift
    stop = stop.astimezone(UTC) + shift
```
- Coordinator passes `naive_tz=dt_util.get_default_time_zone() if local else UTC` and `shift=timedelta(minutes=offset)`.
- The current fallback, verbatim at timeparse.py:52: `tz = UTC  # D-14: no offset means UTC`.
- **Default arguments must keep today's behaviour bit-for-bit:** UTC, and no conversion when `shift == 0`. Existing tests then stay green.

### Anti-Patterns to Avoid
- **Aware wall-clock arithmetic with ZoneInfo:** `datetime(2026,10,25,2,30,tzinfo=Berlin) + timedelta(hours=1)` lands at `02:30 UTC` (+2 h absolute), while UTC arithmetic gives `01:30 UTC` (probed). Always shift in UTC.
- **`update_interval = timedelta(0)`:** silently disables polling (falsy → None).
- **Sending validators without a valid payload on disk:** a 304 then leaves nothing to parse, and after a reload `self.data` is `None`.
- **Caching before validating:** caching a payload that fails to parse or has 0 programmes, together with its ETag, makes every later request 304 and keeps the bad copy forever. Write the cache only after a successful parse with more than 0 programmes, or from the flow (and drop the cache on any later parse failure).
- **Refiltering on every listener call:** failure transitions call listeners with unchanged data (Pattern 5).
- **Using `OptionsFlowWithReload` or `async_update_reload_and_abort`:** conflicts with the single diffing listener (roadmap note; Phase 2 Pitfall 1).
- **Using `self.config_entry` in `OptionsFlow.__init__`:** raises (`hass is None`) [VERIFIED: config_entries.py:4174-4182].
- **Writing the URL into the Store, the issue placeholders, diagnostics or logs:** the cache key is the hashed `unique_id`, never the URL.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file replace | own temp-file/rename code | `homeassistant.util.file.write_utf8_file(path, payload, private=True, mode="wb")` | Handles the temp file in the same dir, `os.replace`, cleanup on error, and 0o600 when private |
| JSON metadata persistence | own JSON read/write | `Store(hass, 1, f"{DOMAIN}.{key}")` | Atomic, executor IO, corrupt-file quarantine, in-memory mock in tests |
| Debounced manual refresh | own lock/timer | `CoordinatorEntity.async_update` → `async_request_refresh` (cooldown 10 s, immediate) | Already wired [VERIFIED: update_coordinator.py:42-43, 731-740] |
| Data retention on failure | own "last good" copy | coordinator keeps `self.data` when `_async_update_data` raises | Assignment happens only on success [VERIFIED: update_coordinator.py:456] |
| Redaction | string slicing | `async_redact_data` with callables | Handles nested dicts and lists, skips None/empty |
| Progress UI | polling step or sleeps | `async_show_progress(progress_task=…)` | The manager re-invokes the step when the task finishes |
| DST-aware "next 18:15" | manual offset maths | `datetime.combine(date, time, tzinfo=ZoneInfo)` + `astimezone(UTC)` in pure code (or `dt_util.find_next_time_expression_time`) | zoneinfo resolves gaps and folds. HA's helper documents DST handling [VERIFIED: util/dt.py:450-463] |

**Key insight:** every mechanism this phase needs already exists in HA. The real risk is the **interaction matrix**: first vs later refresh, cache valid/fresh, 200/304/error/empty, interval vs daily. Pin it with a table-driven test suite rather than more abstractions.

## Common Pitfalls

### Pitfall 1: Test cache files leak into the shared phcc config dir
**What goes wrong:** `hass.config.cache_path("xmltv_calendar")` in tests resolves to `.venv/.../pytest_homeassistant_custom_component/testing_config/.cache/xmltv_calendar` (probed). Cache files survive between tests and runs. Flow tests key by `unique_id`, which is the same for the same URL across tests, so they cross-contaminate.
**How to avoid:** in Wave 0, add an override to `tests/conftest.py`: `@pytest.fixture(autouse=True) def hass_config_dir(hass_tmp_config_dir: str) -> str: return hass_tmp_config_dir` [VERIFIED: phcc plugins.py:662-690].
**Warning signs:** a test passes alone but fails in the suite, or `aioclient_mock.call_count` is 0 when 1 was expected.

### Pitfall 2: Existing tests encode Phase 1 behaviour that Phase 3 changes
These must be updated deliberately. Budget the work in the plans.
- `tests/test_init.py::test_options_change_reloads_once` asserts `aioclient_mock.call_count == calls + 1` and `update_interval == timedelta(hours=12)` after an options change [VERIFIED: tests/test_init.py:121-138]. With a fresh cache a reload downloads nothing, and `update_interval` becomes dynamic.
- `tests/test_calendar.py::test_calendar_with_no_matches[feed-without-programmes]` sets up `NO_PROGRAMMES_FEED` [VERIFIED: tests/test_calendar.py:30-35, 266-281]. Under D-20 the first refresh without a cache fails, so the entry is NOT LOADED (Open Question 2, RESOLVED: 03-04 Task 3 removes this parameter and covers the case in `tests/test_empty_feed.py`).
- `tests/test_config_flow.py`: the `url`/`file` step payloads `{"url"/"path", "refresh_hours": 24}` and the probe tests (`test_probe_reads_at_most_probe_bytes`) change with the new step chain (mode/timezone, then download progress, then schedule) [VERIFIED: tests/test_config_flow.py:153-185, 196-199].
- Keep green: `tests/test_ingestion.py::test_refresh_with_truncated_gzip_keeps_previous_data` expects `last_update_success is False` and `last_exception.translation_key == "invalid_feed"` [VERIFIED: tests/test_ingestion.py:57-77]. This is why later failures still raise `UpdateFailed`.

### Pitfall 3: 304 after a reload with no data in memory
**What goes wrong:** after an options reload the coordinator is new (`self.data is None`). A 304 must then parse the **disk cache**, not return `None`.
**How to avoid:** the decision function handles a 304 with `self.data is None` as "parse cache" (normally unreachable thanks to Pattern 3, but keep it for robustness).

### Pitfall 4: Cache bound to a different source
**What goes wrong:** keying by `unique_id`/`entry_id` alone reuses an old URL's cache after `entry.data` changes (tests do this today).
**How to avoid:** store `source_id = source_unique_id(source_type, locator)` in the metadata and reject a mismatch. `source_unique_id` returns `hashlib.sha256(f"{source_type}:{normalized}".encode()).hexdigest()` [VERIFIED: source.py:84-91].

### Pitfall 5: Metadata and payload out of sync after a crash
**What goes wrong:** the payload is written but the Store still holds the old ETag. The next conditional GET returns 304 and the server's new version is never fetched.
**How to avoid:** write the payload first and the metadata second (`await store.async_save`, not delayed). Store `size` (optionally `sha256`) and treat any mismatch as "no valid cache", which means an unconditional GET.

### Pitfall 6: Persistent-failure threshold vs long intervals (D-17 wording)
**What goes wrong:** read literally ("no success for > 24 h"), a daily or 48 h schedule raises the issue at the *first* failed attempt, because the last success is already ≥ 24 h old.
**How to avoid:** measure from `failing_since` (the first failure of the current streak). The user confirmed this interpretation in plan review (Open Question 1, RESOLVED).

### Pitfall 7: Coordinator scheduling needs listeners
**What goes wrong:** `_schedule_refresh` runs only when listeners exist [VERIFIED: update_coordinator.py:182-188, 600-601]. A source with zero calendars never refreshes, and Repairs is never evaluated. That is acceptable (nothing to show), but don't write a test expecting refreshes with zero calendars. Adding the first calendar arms the schedule through the `_schedule_refresh` override with a fresh delay.

### Pitfall 8: HA logs once per failure streak; don't double-log
Scheduled refreshes log `ERROR "Error fetching %s data: %s"` on the first failure, then `INFO "Fetching %s data recovered"` [VERIFIED: update_coordinator.py:525-529, 588-590]. The message is `str(UpdateFailed)`, i.e. the English translated text without the URL. Keep the integration's own failure logs at DEBUG (host-only), and 304s and cache hits at DEBUG too.

### Pitfall 9: ETag/Last-Modified are untrusted server input
Validate before storing and echoing them: length ≤ 1024 (cap is a proposal [ASSUMED]), printable ASCII, no CR/LF. Otherwise drop the value. They go back out as request headers and into the Store.

### Pitfall 10: File source "unchanged" only with data in memory (D-11)
Compare `(st_mtime_ns, st_size)` with the last parse *of this coordinator instance*. After a reload there is no data, so always parse. The `check_file` allowed-path check still runs first, on every refresh [VERIFIED: source.py:133-142, 158-172]. Return the same `EpgData` object when unchanged, and count it as success.

## Code Examples

### Coordinator decision skeleton (URL path)
```python
async def _async_update_data(self) -> EpgData:
    now = dt_util.utcnow()
    first = self.data is None
    meta = self._cache.meta if self._cache.valid_for(self._source_id) else None
    if first and meta is not None:
        if (epg := await self._async_parse_cache()) is not None:      # None -> cache dropped
            self._next_refresh_at = self._fresh_until(meta.fetched_at) if is_fresh(meta.fetched_at, now, self._schedule) else now
            self._health_evaluate_issue(now)                          # persisted state, Pattern 6
            return epg
        meta = None
    try:
        result = await async_fetch_url(self.hass, self._url,
                                       etag=meta and meta.etag, last_modified=meta and meta.last_modified)
        if isinstance(result, NotModified):
            epg = self.data if self.data is not None else await self._async_parse_cache_or_raise()
            await self._cache.async_touch(fetched_at=now)            # metadata only
        else:
            epg = await self._async_parse_bytes(result.payload)       # raises UpdateFailed(invalid_feed/...)
            if not epg.programmes:
                raise UpdateFailed(translation_domain=DOMAIN, translation_key="empty_feed")  # D-20, key [ASSUMED]
            await self._cache.async_write(result, fetched_at=now, source_id=self._source_id)
    except UpdateFailed as err:
        self._record_failure(now, err.translation_key)                # sets backoff target, maybe issue
        if first and (cached := await self._async_parse_cache()) is not None:
            return cached                                             # D-09: stale + offline -> still set up
        raise                                                         # first & no cache -> ConfigEntryNotReady
    self._record_success(now)                                         # clears issue, target = next regular
    return epg
```
(Map `SourceError` and `FeedError` to `UpdateFailed` with the existing translation keys before the `except`, as `_feed_errors` does today [VERIFIED: coordinator.py:111-121].)

### Remove-entry cleanup
```python
async def async_remove_entry(hass: HomeAssistant, entry: XmltvConfigEntry) -> None:
    """Delete the cached feed, its metadata and any Repairs issue (D-08)."""
    cache = FeedCache(hass, cache_key(entry))
    await cache.async_remove()                                        # executor unlink + Store.async_remove()
    ir.async_delete_issue(hass, DOMAIN, f"source_failing_{entry.entry_id}")
```
`async_remove_entry` is called by HA when an entry is deleted, if the module defines it [VERIFIED: config_entries.py:1186-1189].

### Translation skeleton (en.json additions)
```json
{
  "config": { "progress": { "download": "Downloading the feed. Large feeds can take a minute." } },
  "options": { "step": { "init": { "...": "..." }, "schedule": { "...": "..." } } },
  "issues": {
    "source_failing_unable_to_fetch": {
      "title": "XMLTV source {source} keeps failing",
      "description": "{source} could not be downloaded for more than 24 hours (last success: {last_success}). Calendars keep showing the last good data."
    }
  },
  "exceptions": { "empty_feed": { "message": "The XMLTV feed contains no current programmes." } },
  "selector": { "refresh_mode": { "options": { "interval": "Interval", "daily": "Daily at a fixed time" } } }
}
```
Options-step sections translate as `options.step.<step>.sections.<section>.{name,data,data_description}`, as in core cast [VERIFIED: components/cast/strings.json options.step.init.sections]. Mirror every key in de.json; `tests/test_translations.py` enforces parity.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `async_show_progress` without task | `progress_task=` required | warning since 2024.5, "will break" 2024.8 [VERIFIED: data_entry_flow.py:818-831] | Always pass the task |
| `OptionsFlowWithConfigEntry` | `OptionsFlow` + `self.config_entry` property | "being phased out" [VERIFIED: config_entries.py:4185-4200] | Plain `OptionsFlow` |
| Coordinator without `config_entry=` | explicit `config_entry=` | ContextVar fallback reported [VERIFIED: update_coordinator.py:102-115] | Already done in Phase 1 |
| `hass.config.path(".cache", …)` | `hass.config.cache_path(…)` | HA 2026.3 (Phase 1 research) | Floor is 2026.3, use `cache_path` |

**Deprecated/outdated:** `OptionsFlowWithReload` for this integration (project rule, conflicts with the diffing listener).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Backoff steps 5 m, 15 m, 1 h, 3 h, 6 h (then 6 h), each capped at the next regular refresh | Pattern 1 | Low. Discretion item; tune freely |
| A2 | New option key names/values `refresh_mode` (`interval`/`daily`), `refresh_time` (`HH:MM`), `naive_timezone` (`utc`/`local`), `offset_minutes` | Pattern 8 | **Costly** (D-06): stored contract; renaming later needs a migration. Lock in the plan |
| A3 | New reason/translation key `empty_feed` for D-20, and flow error key `feed_too_large` in the setup flow | Patterns 6, 9 | Low. Naming only, but it becomes part of the issue keys |
| A4 | Persistent failure is measured from `failing_since` (first failure of the streak), not from `last_success` | Pitfall 6 | Medium: changes when the Repairs issue appears for daily or ≥ 24 h schedules |
| A5 | Stale-while-revalidate at start (parse a stale cache, then refresh about 1 s later in the background) instead of network-first | Pattern 3 | Low to medium: stale data is visible for seconds after start, and a changed feed costs 2 parses at start |
| A6 | Cache key = `entry.unique_id` (fallback `entry_id`), cache written in the flow's final step | Pattern 9 | Low. Disposable cache |
| A7 | ETag/Last-Modified sanity cap of 1024 chars | Pitfall 9 | Low |
| A8 | Real feeds (the user's 18:00 feed) send ETag and/or Last-Modified | Summary | Medium: without validators, SRC-07 degrades to "re-download every time". An optional sha256 compare of the new payload against the cached one still avoids the re-parse. Needs a real-feed check (STATE.md Phase 3 concern) |
| A9 | A nonexistent local daily time (spring-forward gap) fires at the shifted instant (03:30 CEST for 02:30) | Pattern 1 | Low. Pinned by test |

**Planning status (2026-10-16):**
- A2 is locked in 03-01 Task 2 exactly as proposed: `refresh_mode` (`interval` | `daily`), `refresh_hours`, `refresh_time` (`HH:MM`), `naive_timezone` (`utc` | `local`), `offset_minutes`. The task carries a `costly` reversibility rating (D-06).
- A3 is fixed as `empty_feed` (03-04) and `feed_too_large` (03-06).
- A4 was confirmed by the user (Open Question 1).
- A8 remains a manual UAT check (03-08). 03-03 adds the SHA-256 skip, so either outcome is covered.

## Open Questions (RESOLVED)

All four questions are resolved. The resolutions below match what the Phase 3 plans implement. The stored option key names (A2) were never an open question; see the planning status under the Assumptions Log.

1. **D-17 threshold reference point.** RESOLVED (user decision, plan review 2026-10-16)
   - What we know: the literal wording is "no successful refresh for more than 24 h". With a daily or 48 h schedule, the last success is always ≥ 24 h old at the next regular attempt.
   - What's unclear: whether the issue may appear at the first failed daily attempt.
   - Recommendation: measure from `failing_since` (A4) and confirm with the user in plan review.
   - **Resolution:**
     - The 24 h count from `failing_since`, the first failure of the current streak, not from `last_success`. The issue appears only when a failure happens strictly more than 24 h after `failing_since`.
     - A daily source whose first failure comes 24 h after its last success raises no issue at that first failure.
     - A 304 or an unchanged local file counts as success and ends the streak.
     - 03-01 Task 2 implements `is_persistently_failing(failing_since, now)` with `PERSISTENT_FAILURE = timedelta(hours=24)`.
     - 03-04 persists `SourceHealth.failing_since`. Its tests `test_persistent_failure_raises_and_clears_issue` and `test_daily_first_failure_after_24h_raises_no_issue` pin the behaviour.
2. **D-20 at first setup without cache.** RESOLVED (user decision, plan review 2026-10-16)
   - What we know: 0 programmes = failure, and the last good data is kept.
   - What's unclear: with no last good data, should setup fail (`ConfigEntryNotReady`) or load an empty calendar?
   - Recommendation: treat it as failure (`ConfigEntryNotReady`, entry retries, health tracked, Repairs after 24 h), and change `test_calendar_with_no_matches[feed-without-programmes]` to a feed with one non-matching programme. Alternative: accept an empty first load. Decide in the plan.
   - **Resolution:**
     - The rule: first setup, no cache and a feed that yields 0 programmes raise `UpdateFailed(translation_key="empty_feed")`. Home Assistant turns this into `ConfigEntryNotReady`: the entry state is SETUP_RETRY, with `error_reason_translation_key` `empty_feed`.
     - Nothing is cached. The failure is recorded in `SourceHealth`, so setup retries count toward the 24 h issue.
     - The empty-first-load alternative is rejected.
     - 03-04 Task 3 implements this and adjusts the existing tests. It removes the `feed-without-programmes` parameter from `test_calendar_with_no_matches` instead of rewriting it; the `channel-not-in-feed` parameter keeps covering a loaded calendar without matches.
     - 03-04 Task 3 moves the empty-feed case to `tests/test_empty_feed.py::test_first_setup_with_empty_feed_retries` and `test_feed_with_only_past_programmes_retries`.
     - 03-04 Task 3 gives `tests/test_subentry_flow.py::test_channel_picker_lists_sorted_ids` one programme, so its source still loads.
     - 03-01 Task 3 pins the clock of the fixture-dated test modules, so they do not hit the new failure by accident.
3. **Do real feeds send validators?** (A8) RESOLVED (planner, both outcomes handled)
   - Recommendation: add a manual UAT step with `curl -sI <feed-url>` on the user's feed. Optionally implement the payload-hash skip so an unchanged 200 is not re-parsed.
   - **Resolution:** both parts of the recommendation are planned.
     - With validators: 03-03 Task 1 sends If-None-Match / If-Modified-Since and handles 304.
     - Without validators: 03-03 Task 2 implements the SHA-256 payload-hash skip. A 200 whose body hash equals `CacheMeta.sha256` is not re-parsed (`test_identical_body_is_not_reparsed`), so only the download remains.
     - The real-feed check is step 8 of the 03-08 Task 2 human-check (`curl -sI <feed URL>`). Step 7 watches `update_entity` on the same feed.
     - The answer only changes network cost, not the design, so A8 stays an assumption until UAT.
4. **File-source progress indicator.** RESOLVED (planner, recommendation adopted)
   - CFG-03 says "while a source is downloaded". Local files are not downloaded.
   - Recommendation: no progress step for files (parsing happens at setup, as today).
   - **Resolution:**
     - Local files get no progress step. 03-06 Task 2 sends the file step straight to the schedule step and seeds no cache (D-11).
     - The progress step (CFG-03, D-13) exists only in the URL chain (03-06 Task 1).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | runtime/tests | ✓ | 3.14.7 | — |
| uv | env/lock | ✓ | 0.12.7 (STACK mentions 0.13.0; lock works with 0.12.7) | — |
| Ruff | lint | ✓ | 0.17.0 | — |
| Home Assistant (via phcc) | tests | ✓ | 2026.10.1 (phcc 0.13.372) | — |
| Test suite baseline | regression | ✓ | 560 passed, 1 skipped (43.6 s) | — |
| Real XMLTV feed with ETag/Last-Modified | SRC-07 UAT | unknown | — | Fixtures + `aioclient_mock` cover the logic; real check in UAT |
| `ha-host` (HAOS) | deploy/UAT | not probed | — | ha-dev container as in Phase 1 |

**Missing dependencies with no fallback:** none.

## Testing Notes (tdd_mode)

Nyquist validation is disabled, so this is guidance only:
- **Pure, test-first (RED before GREEN):**
  - `schedule.py`, with cases: interval fresh/stale boundaries, daily before/after slot, missed slot, DST end 2026-10-25 and start 2026-03-29 in Europe/Berlin, future `fetched_at`, backoff cap.
  - `timeparse`/`parser`, with cases: naive → local incl. DST, shift ±720, shift across DST, defaults unchanged.
- **HA glue (phcc):**
  - Table-driven refresh matrix (first/later × cache none/fresh/stale/corrupt × 200/304/error/empty).
  - Restart simulation: unload + setup the same entry. `hass_storage` keeps the Store, and the tmp config dir keeps the payload.
  - Daily slot firing via `freezer.move_to` + `async_fire_time_changed(hass)` [VERIFIED: tests/test_calendar.py:158-160 pattern].
  - `update_entity` via `hass.services.async_call("homeassistant", "update_entity", {"entity_id": ...}, blocking=True)`, then assert one request with `If-None-Match` [VERIFIED: components/homeassistant/__init__.py:81, 267 → entity_component.async_update_entity].
  - Repairs via `ir.async_get(hass).async_get_issue(DOMAIN, issue_id)`.
  - Diagnostics via direct call, plus one `get_diagnostics_for_config_entry`.
- Keep the `forbid_loop_io` fixture on every new cache/flow test.
- Quick: `uv run pytest tests/test_schedule.py -x -q`. Full: `uv run pytest -q` (about 45 s today).

## Security Domain

### Applicable ASVS Categories (Level 1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (credentials, if any, live inside the user's URL; never logged, stored elsewhere or shown) |
| V3 Session Management | no | — |
| V4 Access Control | yes (file paths) | `check_file` allowed-path check on every refresh (existing). Cache paths are built only from the hex `unique_id`/`entry_id`, never from user input |
| V5 Input Validation | yes | Selector ranges (offset −720..720, hours 1..168), `normalize_time` for `refresh_time`, ETag/Last-Modified sanitisation (Pitfall 9). Stored options read defensively (missing/wrong type → default, D-06) |
| V6 Cryptography | no | SHA-256 only as an identifier (existing `source_unique_id`) |
| V7 Error handling & logging | yes | Host-only logs, translation-key errors, no URL in issues or diagnostics |
| V8 Data protection | yes | Cache file written `private=True` (0o600). `.cache` excluded from backups. Diagnostics redact URL to scheme+host and path to basename |
| V12 Files & resources | yes | Existing download cap 256 MiB and decompressed cap 1 GiB bound the cache size per source. The cache is deleted in `async_remove_entry` |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credential/token leak via URL in diagnostics, Repairs, Store or logs | Information disclosure | `_redact_url` (scheme+host), hashed cache key, placeholders limited to title and time |
| Header injection via a hostile server's ETag echoed back | Tampering | Validate printable ASCII, no CR/LF, length cap, before storing |
| Poisoned cache (bad payload stored with a validator → permanent 304) | Tampering / DoS | Cache only after a successful, non-empty parse; drop the cache on any parse failure of it |
| Disk exhaustion | DoS | One payload per source, ≤ `MAX_DOWNLOAD_BYTES`; atomic replace leaves no stray temp files (`write_utf8_file` cleans up) |
| Path traversal via cache filename | Tampering | Filename from `[0-9a-f]{64}` or a ULID only |
| Decompression bomb from the cache | DoS | The same `parse(max_bytes=MAX_DECOMPRESSED_BYTES)` path as downloads |

## Sources

### Primary (HIGH confidence, read this session)
- Installed HA 2026.10.1 (`.venv/lib/python3.14/site-packages/homeassistant/`): `helpers/update_coordinator.py` (UpdateFailed, `_schedule_refresh`, `_async_refresh`, CoordinatorEntity), `helpers/debounce.py`, `data_entry_flow.py` (progress API, transitions, `section`), `config_entries.py` (OptionsFlow, options save, `async_remove_entry`), `helpers/issue_registry.py`, `helpers/storage.py`, `helpers/redact.py`, `components/diagnostics/__init__.py`, `core_config.py` (`cache_path`), `components/backup/const.py`, `util/file.py`, `util/dt.py`, `helpers/start.py`, `exceptions.py`, `helpers/translation.py`, `helpers/selector.py` (TimeSelector), `helpers/entity_component.py`, `components/ollama/config_flow.py` + `strings.json`, `components/cast/strings.json`.
- phcc 0.13.372: `test_util/aiohttp.py`, `common.py` (`async_fire_time_changed`, `get_test_config_dir`), `plugins.py` (`hass_tmp_config_dir`, `hass_config_dir`, `hass_storage`), `components/diagnostics`.
- Project code: `custom_components/xmltv_calendar/*` and `tests/*` (all cited lines read this session).
- Probes: 304 + headers via `aioclient_mock`; test `cache_path` location; ZoneInfo DST arithmetic; `timedelta(0)` truthiness; full suite baseline.

### Secondary
- `.planning/research/ARCHITECTURE.md`, `PITFALLS.md`, `.claude/CLAUDE.md` stack notes (earlier project research; consistent with the findings above).

### Tertiary
- None. No web sources were needed: everything was answered from installed source.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. All APIs read in the installed HA version.
- Architecture: HIGH for the mechanisms. MEDIUM for discretion choices (A1, A5, A6), which are flagged.
- Pitfalls: HIGH. Each one is backed by a source line or a probe.

**Research date:** 2026-10-16
**Valid until:** about 2026-11-15, or the next phcc/HA bump (Renovate): re-check `_schedule_refresh` and the progress-flow internals.
