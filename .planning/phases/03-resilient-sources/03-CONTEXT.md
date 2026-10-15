# Phase 3: Resilient Sources - Context

**Gathered:** 2026-10-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Sources keep every calendar populated at minimal network and CPU cost:
- raw feed cached on disk across restarts and reloads
- conditional GET (ETag / If-Modified-Since); unchanged feeds are not re-downloaded or re-parsed
- schedule: refresh interval or once daily at a fixed time
- per-source timezone options (no-offset interpretation, offset correction)
- source options flow (schedule + timezone)
- progress indicator while the feed downloads during setup
- last-good data on failure, Repairs issue for persistent failures, diagnostics per source
- manual refresh via `homeassistant.update_entity`

Requirements: SRC-05, SRC-06, SRC-07, SRC-08, SRC-10, SRC-11, SRC-12, CFG-02, CFG-03, AUT-04.
Not in this phase: next-match sensor, new-match event, past retention, blueprint, README, releases (Phase 4); source URL/path reconfigure (deferred).

</domain>

<decisions>
## Implementation Decisions

### Refresh schedule & source options
- **D-01:** The schedule is a mode select: "interval" or "daily at". After the select, only the matching field is shown: refresh hours (existing `refresh_hours`, default 24, min 1, max 168 per Phase 1 D-13) or one `TimeSelector` time. Both fields are never active at the same time.
- **D-02:** "Daily at" takes exactly one time of day, evaluated in the HA configured timezone (e.g. 18:15 for a feed generated at 18:00). Multiple times are out of scope.
- **D-03:** A missed daily slot is caught up at start: if the most recent scheduled time is later than the cache's fetch time, the cache counts as stale and the source refreshes immediately.
- **D-04:** The source options flow edits **only** schedule (mode, hours, time) and timezone options (D-11..D-13). URL/path stay fixed (unique_id and duplicate check, SRC-13). The name is changed with HA's normal rename.
- **D-05:** Schedule and timezone options are also asked in the source setup flow, so the first parse already uses the right timezone settings. Setup and options share one schema builder.
- **D-06:** Entries stored before Phase 3 only have `refresh_hours`. A missing mode key means "interval"; missing timezone keys mean UTC and offset 0 (the Phase 1 D-14 behaviour). There is no entry migration and no version bump. — **Reversibility:** costly — the new option keys (mode, daily time, tz interpretation, offset minutes) become a stored contract. Renaming them later needs a config entry migration.
- **D-07:** A source options save reloads the entry. Use a plain `OptionsFlow`, never `OptionsFlowWithReload` (roadmap note). The Phase 2 diffing listener (`__init__.py:_async_entry_updated`) already reloads when data/options change. Calendar subentry edits still never reload (Phase 2 D-04).

### Cache & startup
- **D-08:** For URL sources the disk cache holds the **raw feed bytes** as downloaded (gzip stays gzip) plus metadata: ETag, Last-Modified, fetch time. The location is `hass.config.cache_path` (roadmap note). At start or reload, a cache that is fresh for the schedule is parsed from disk in the executor, without network. The cache is removed when its entry is removed. — **Reversibility:** reversible — the cache is disposable. A format change can drop old files and re-download.
- **D-09:** The cache is fresh when its fetch time is within the configured interval, or (daily mode) later than the most recent scheduled time (D-03). When the cache is stale and the source cannot be reached at start, setup still **succeeds with the cached data**. The coordinator keeps retrying (D-10) and failure tracking runs (D-14). `ConfigEntryNotReady` is only raised when there is no cache at all and the first fetch fails (the current behaviour).
- **D-10:** After a failed refresh the source retries with a backoff (roughly 5 min → 15 min → 60 min → …). The backoff is capped at the regular schedule: the interval, or in daily mode at most until the next scheduled time. Exact steps are Claude's discretion.
- **D-11 (local files):** Local file sources get **no** disk cache. A refresh re-parses only when the file's mtime or size changed (the local equivalent of `304`). The allowed-path check still runs on every refresh. After a reload the file is parsed again, because nothing is cached in memory.
- **D-12:** `homeassistant.update_entity` on any calendar of a source triggers an immediate source refresh. It ignores cache freshness but still sends ETag / If-Modified-Since; a `304` means no re-download and no re-parse.
- **D-13:** The setup flow downloads the full feed once, with `async_show_progress` (CFG-03). That download **seeds the disk cache**, so the first coordinator refresh parses from the cache instead of downloading the feed a second time. Today the flow probes and then the coordinator downloads.

### Timezone options (SRC-10)
- **D-14:** "Timestamps without offset" is a select with two values: **UTC** (default, XMLTV DTD, Phase 1 D-14) or **HA timezone** (`hass.config.time_zone`, DST-aware). Free IANA zones are out of scope.
- **D-15:** The offset correction is an integer in **minutes, −720..+720** (default 0). It shifts **all** start/stop timestamps after interpretation, whether they had an offset or not. Use case: feeds with a wrong offset.
- **D-16:** A timezone option change reloads the entry (D-07) and re-parses from the disk cache, with no download. Shifting data in memory is rejected. Because event UIDs use the UTC start (EVT-06), changed UIDs after a correction change are expected and acceptable.

### Failure visibility
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope & requirements
- `.planning/ROADMAP.md` § "Phase 3: Resilient Sources": goal, success criteria 1–5, notes (plain `OptionsFlow` only, diffing listener, `hass.config.cache_path`, research flags `async_show_progress` and the Repairs issue lifecycle)
- `.planning/REQUIREMENTS.md`: SRC-05..SRC-08, SRC-10..SRC-12, CFG-02, CFG-03, AUT-04
- `.planning/PROJECT.md` § Key Decisions: source = config entry, calendar = subentry, coordinator in `runtime_data`

### Prior decisions & research
- `.planning/phases/01-first-filtered-calendar/01-CONTEXT.md`: D-13 (refresh default/min), D-14 (no offset = UTC)
- `.planning/phases/02-precise-filters-preview/02-CONTEXT.md`: D-04 (subentry edits in place, source changes reload)
- `.planning/phases/01-first-filtered-calendar/01-REVIEW-DISPOSITION.md`: WR-08 (`skipped_malformed` not surfaced), mapped to SRC-12
- `.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md`, `.planning/research/STACK.md`: coordinator, caching and conditional-request notes, `is_allowed_path` in the executor
- `.claude/CLAUDE.md` (project): stack notes. HTTP conditional requests, `os.stat().st_mtime` skip, `Store` for the last parse, `UpdateFailed(retry_after=…)`, diagnostics with `async_redact_data`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `custom_components/xmltv_calendar/source.py`:
  - `async_fetch_url` (bounded streaming download): extend with conditional headers and `304` handling, and return the response's ETag/Last-Modified.
  - `async_probe_url`: today's setup probe. The progress-based full download (D-13) replaces or extends it.
  - `read_and_parse_file`: the local-file path, which gets the mtime/size skip (D-11).
- `custom_components/xmltv_calendar/coordinator.py` `XmltvCoordinator`:
  - `_async_update_url`/`_async_update_file` are where cache, conditional GET, the 0-programme check (D-20) and failure tracking plug in.
  - `update_interval` comes from `CONF_REFRESH_HOURS` today.
  - `_feed_errors` maps errors to translation keys, which can be reused as Repairs/diagnostics reason keys.
- `custom_components/xmltv_calendar/xmltv/timeparse.py:52`: the D-14 UTC fallback. The no-offset interpretation (D-14 new) and the correction (D-15) need a tz/offset parameter threaded through `parse()`. Keep it pure (no HA imports).
- `custom_components/xmltv_calendar/xmltv/model.py:44`: `EpgData` stats `skipped_malformed`, for diagnostics.
- `custom_components/xmltv_calendar/config_flow.py`:
  - `_refresh_selector`, `async_step_url`/`async_step_file`/`async_step_name`: the setup flow. The schedule and timezone fields are added here and shared with the new options flow.

### Established Patterns
- All blocking IO and parsing run in a single executor job (`source.py` keeps builtin `open` so the tests' `forbid_loop_io` guard works).
- URLs are never logged, only the host. Error texts are translation keys.
- `__init__.py:_async_entry_updated` diffs `(entry.data, entry.options)` against `runtime.source_snapshot`, and any change reloads. Options-flow saves get the reload from this for free.
- The pure `xmltv/` library is built test-first, while HA glue is tested with phcc fixtures (`aioclient_mock`, `freezer`).
- Missing stored keys mean defaults, with no migration (Phase 2 D-06). Phase 3 follows the same rule (D-06).

### Integration Points
- `__init__.py:async_setup_entry`: load the cache before `async_config_entry_first_refresh`, and handle "stale cache + offline = still set up" (D-09).
- New modules: `diagnostics.py`, a cache helper, and Repairs issue creation/deletion (`homeassistant.helpers.issue_registry`).
- `XmltvConfigFlow.async_get_options_flow` and a new `OptionsFlow` class.
- `strings.json`, `translations/en.json`, `translations/de.json`: options steps, schedule/timezone fields, progress action, issue texts. The de/en key-parity test exists from quick 261015-su3.
- `calendar.py`: `async_update` / `update_entity` routes to `coordinator.async_request_refresh()` (D-12).

</code_context>

<specifics>
## Specific Ideas

- The user's main feed is generated daily at 18:00, so "daily at 18:15" is the motivating schedule (SRC-05).
- Real feeds are still needed to check ETag/Last-Modified behaviour (STATE.md Phase 3 concern). Fixtures plus `aioclient_mock` cover the logic.

</specifics>

<deferred>
## Deferred Ideas

- Reconfigure flow for a source's URL/path (with duplicate check). Not part of CFG-02, possible backlog item.
- Multiple daily refresh times.
- Free IANA timezone choice for timestamps without offset.
- Stale/last-success attributes on calendar entities.
- Fixable Repairs flow leading to the source options.

</deferred>

---

*Phase: 03-resilient-sources*
*Context gathered: 2026-10-16*
