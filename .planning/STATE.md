---
gsd_state_version: "1.0"
milestone: v0.1.0
current_phase: 04
current_phase_name: Automation Extras & Release
status: executing
stopped_at: Completed 04-06-PLAN.md
last_updated: "2026-10-21T10:11:07.854Z"
last_activity: 2026-10-21
last_activity_desc: Phase 04 execution started
state_head: 5bda8ed9d68c4683980febb6f0b6129af9ab08ac
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 39
  completed_plans: 37
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-21)

**Core value:** Configured filters reliably turn a (possibly large) XMLTV feed into a calendar showing exactly the programmes the user cares about, with channel and start time clearly visible.
**Current focus:** Phase 04 — Automation Extras & Release

## Current Position

Phase: 04 (Automation Extras & Release) — EXECUTING
Plan: 7 of 8
Status: Ready to execute
Last activity: 2026-10-21 — Phase 04 execution started

Progress: [████████░░] 75%

## Performance Metrics

**Velocity:**
- Total plans completed: 31
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 11 | - | - |
| 02 | 10 | - | - |
| 03 | 10 | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 6 min | 3 tasks | 27 files |
| Phase 01 P02 | 4 min | 2 tasks | 7 files |
| Phase 01 P03 | 4 min | 2 tasks | 3 files |
| Phase 01 P04 | 6 min | 2 tasks | 9 files |
| Phase 01 P05 | 6 min | 3 tasks | 9 files |
| Phase 01 P06 | 10 min | 3 tasks | 13 files |
| Phase 01 P07 | 6 min | 3 tasks | 6 files |
| Phase 01 P08 | 4 min | 3 tasks | 4 files |
| Phase 01 P09 | 5 min | 3 tasks | 1 files |
| Phase 01 P10 | 5 min | 3 tasks | 0 files |
| Phase 01 P11 | 6min | 3 tasks | 7 files |
| Phase 02 P01 | 4 min | 2 tasks | 5 files |
| Phase 02 P02 | 7 min | 3 tasks | 8 files |
| Phase 02 P03 | 7 min | 3 tasks | 14 files |
| Phase 02 P04 | 6 min | 3 tasks | 6 files |
| Phase 02 P05 | 4 min | 2 tasks | 8 files |
| Phase 02 P06 | 6 min | 3 tasks | 8 files |
| Phase 02 P07 | 6 min | 2 tasks | 5 files |
| Phase 02 P08 | 5 min | 2 tasks | 4 files |
| Phase 02 P09 | 7 min | 2 tasks | 6 files |
| Phase 02 P10 | 4 min | 2 tasks | 3 files |
| Phase 03 P01 | 13 min | 3 tasks | 11 files |
| Phase 03 P02 | 8 min | 3 tasks | 7 files |
| Phase 03 P03 | 9 min | 3 tasks | 7 files |
| Phase 03 P04 | 9 min | 3 tasks | 11 files |
| Phase 03 P05 | 7 min | 3 tasks | 6 files |
| Phase 03 P06 | 9 min | 3 tasks | 8 files |
| Phase 03 P07 | 4 min | 2 tasks | 8 files |
| Phase 03 P08 | 7 min | 2 tasks | 8 files |
| Phase 03 P09 | 7 min | 3 tasks | 5 files |
| Phase 03 P10 | 3 min | 2 tasks | 3 files |
| Phase 04 P01 | 8 min | 3 tasks | 10 files |
| Phase 04 P02 | 41 min | 2 tasks | 5 files |
| Phase 04 P03 | 2 min | 2 tasks | 4 files |
| Phase 04 P04 | 10min | 3 tasks | 8 files |
| Phase 04 P05 | 15 min | 3 tasks | 13 files |
| Phase 04 P06 | 14 min | 3 tasks | 12 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: Source = config entry (coordinator in `runtime_data`), calendar = config subentry
- [Init]: Vertical MVP roadmap (4 coarse phases); the pure `xmltv/` library is still built first, inside Phase 1
- [Init]: Plain `OptionsFlow` + exactly one diffing update listener; never `OptionsFlowWithReload`
- [Init]: Zero runtime deps (stdlib `iterparse` + `gzip` in executor); titles via restricted `str.format_map`, no Jinja
- [Phase 01]: 01-01 Task 1 approved: dev pins pytest-homeassistant-custom-component 0.13.372 (HA 2026.10.1) and ruff 0.17.0
- [Phase 01]: iot_class cloud_polling (most sources are internet feeds, like core remote_calendar)
- [Phase 01]: Parser passes a missing stop as stop == start; normalize infers any stop <= start; keep_after drop runs after normalize
- [Phase 01]: 01-02: dedup before grouping, keyed on (channel_id, UTC start, title), first occurrence wins
- [Phase 01]: 01-02: EventFields.uid narrowed to str; UID = <channel_id>-<UTC start>-<crc32(title):08x> (A7)
- [Phase 01]: 01-03: channel_regex parsed like include/exclude (multiline, IGNORECASE) and re.search-ed on the channel ID
- [Phase 01]: 01-03: missing_channels subtracts channel IDs seen in programmes, so programme-only channels are not reported missing
- [Phase 01]: 01-03: first_invalid_pattern checks line-count cap, then length cap, then re.compile per non-blank line
- [Phase 01]: 01-04: get_events over the cap returns the earliest-starting 5,000 matches of the range (start-sorted slice) with a debug log
- [Phase 01]: 01-04: MatchIndex sorts its own input (stable) instead of trusting caller order
- [Phase 01]: 01-04: boundary end-trigger test asserts event end 11:30 and firing by 11:31 (freezer runs the already-due alarm on the next tick)
- [Phase 01]: 01-05: LookupError and ValueError are also translated into content-free FeedError (unknown encoding declarations leak feed text via LookupError)
- [Phase 01]: 01-05: programme-only channels are synthesized as Channel(id, id) from all parsed programmes, before the keep_after drop
- [Phase 01]: 01-05: successful downloads log byte count and host only; size failures use translation key feed_too_large
- [Phase 01]: 01-06: SRC-09 max event-loop gap is 86-164 ms on the dev box (limit 250 ms), driven by gen2 GC pauses and the C-level sorts in normalize_programmes; yield_every only covers iterparse. Parser unchanged; heapq.merge is the candidate fix if CI or ha-host runs get close to the limit
- [Phase 01]: 01-06: brand icons asserted at exactly 256x256 / 512x512; workflow supply-chain checks parametrize over every file in .github/workflows
- [Phase 01]: 01-06: hassfest container clean locally (0 invalid integrations); generator gzip output is byte-reproducible (mtime 0) and target_bytes counts uncompressed XML
- [Phase 01]: 01-07 Task 2: sha256. Config entry unique_id = SHA-256 hex of <source_type>:<normalized locator> (url: / file: prefix); changing it needs async_migrate_entry + VERSION bump
- [Phase 01]: 01-07: entry.data stores the normalized URL (fragment dropped, query kept) or the resolved real path; the duplicate check runs before the flow probe
- [Phase 01]: 01-07: file read OSError shows file_not_found in the flow and unable_to_fetch at setup; file helpers keep builtin open() so forbid_loop_io sees loop calls
- [Phase 01]: 01-08: pattern fields stored as raw text; FilterSpec strips and skips blank lines at filter time
- [Phase 01]: 01-08: several invalid pattern fields each get invalid_regex; placeholders show the first bad line (channel_regex, include, exclude order)
- [Phase 01]: 01-08: the 01-01 diffing listener already met FLT-01; tests/test_init.py is its regression suite, __init__.py unchanged
- [Phase 01]: 01-09 Task 2: none. No real German feed excerpt committed in Phase 1; D-15 real-feed excerpt and scripts/trim_feed.py deferred
- [Phase 01]: 01-09: ha-dev published on host port 18123 via a transient compose override (ha-a holds 8123); compose.yml keeps 8123:8123
- [Phase 01]: 01-09: test_real_feed.py holds the full checks behind a module skip; XMLTV_REAL_FEED runs them on any local feed
- [Phase 01]: 01-10 Task 2: before the first push, at the user's request, host names were rewritten across the full local history of main (git filter-repo --replace-text: dev laptop -> dev-host, HA host -> ha-host, 78 hits). All SHAs changed (HEAD dcebd6f -> ffd5363); SHAs cited in 01-01..01-09 SUMMARYs are pre-rewrite (find commits by subject); local backup/pre-anonymize keeps the old history, unpushed. New text uses ha-host / dev-host only
- [Phase 01]: 01-10 Task 3: the initial push of main emitted no push event, so CI and Validate for ffd5363 were started via workflow_dispatch (both success: runs 38553243429, 38553246496); the next push is the first push-triggered run
- [Phase 01]: 01-10: Renovate is active on the public repo (PR #1 home-assistant/actions digest, PR #2 setup-uv v10.3.0, both green); merging is left to the user
- [Phase 01]: 01-11: parse_xmltv_time accepts offsets up to +-18:00 and written years 1900..2200; everything else returns None (CR-01)
- [Phase 01]: 01-11 (WR-06): _STREAM_ERRORS keeps LookupError/ValueError (Expat raises them at read time); scope narrowed to iterparse next() in _read_events
- [Phase 01]: 01-11: multi-exception clauses use PEP 758 unparenthesized form because ruff format 0.17 (py314) rewrites the parenthesized form
- [Phase 02]: 02-01: device rename uses async_get_device_by_identifier((DOMAIN, subentry_id), entry_id); async_get_device raises in HA 2026.10
- [Phase 02]: 02-01: listener applies edited calendars in place over a copy of runtime.calendars (update listener calls run as concurrent tasks); the entity stores its (title, data) diff base before any await
- [Phase 02]: 02-01: uncompilable stored pattern gives an empty index at entity creation; on an edit the previous spec and matches are kept and the bad data still becomes the diff base, so it is logged once
- [Phase 02]: 02-02 Task 2: flat. Stored calendar keys sit beside the Phase 1 keys: include_fields, exclude_fields, case_sensitive, time_from, time_to, weekdays, min_duration, max_duration, title_template, description_template; field values title/subtitle/description/category; weekdays mon..sun (== homeassistant.const.WEEKDAYS); times "HH:MM", durations int minutes, templates plain strings; Advanced checkbox never stored (has_advanced derives it)
- [Phase 02]: 02-02: normalize_time checks HH:MM[:SS] by ASCII pattern, not time.fromisoformat (Python 3.14 accepts 24:00 as 00:00, bare hours and offsets)
- [Phase 02]: 02-02: with_defaults returns exactly the 14 contract keys (unknown keys dropped); whitespace-only templates read as defaults; NaN/inf durations read as None; large int durations are kept (clamp in 02-04)
- [Phase 02]: 02-03: preview_empty is a separate menu step id (translatable warning); its handler aliases async_step_preview because HA requires a handler for every shown step id
- [Phase 02]: 02-03: the calendar subentry still stores only the four Phase 1 keys; later plans extend _pending/_filter_data
- [Phase 02]: 02-03: preview weekday names keyed by the primary subtag of hass.config.language (de -> Mo..So, else Mon..Sun), no locale
- [Phase 02]: 02-03: escape_markdown turns & < > into entities, then backslash-escapes backslash, backtick, * _ [ ] # and pipe; parentheses stay
- [Phase 02]: 02-04: stored durations above timedelta.max minutes are clamped (huge min hides everything, huge max is unbounded); FilterSpec.from_mapping never raises OverflowError
- [Phase 02]: 02-04: nested-repetition check treats max > 1 as unbounded (so (a{2,3})* is rejected), also walks GROUPREF_EXISTS, and is fail-open (incl. RecursionError) when re._parser changes
- [Phase 02]: 02-04: weekdays without a window use the local start date; with a window the weekday is the day the window opened (D-11); apply(epg) without tz evaluates in UTC
- [Phase 02]: 02-05: Calendar edits save via async_update_and_abort only; the update listener applies them in place (no reload, no re-download)
- [Phase 02]: 02-05: The basic form submit merges into pending values instead of replacing them, so stored keys outside the form survive an edit
- [Phase 02]: 02-05: Channel selector options are sorted(feed IDs | stored IDs) so calendars with channels missing from the feed can be saved unchanged
- [Phase 02]: 02-06: Description edge cleanup keeps a leading dash/middle-dot bullet; strips whitespace and : , ; | / at the start and all separators at the end
- [Phase 02]: 02-06: Template-only calendar edits rebuild EventTemplates and write state without a refilter
- [Phase 02]: 02-06: TemplateError reasons exported as INVALID_TEMPLATE and UNKNOWN_PLACEHOLDER constants for the flow (02-07)
- [Phase 02]: 02-07: the title template is stored stripped; blank title stores DEFAULT_TITLE_TEMPLATE, blank description stores '' (default description)
- [Phase 02]: 02-07: a missing include_fields/exclude_fields key counts as an empty selection and is rejected with fields_required
- [Phase 02]: 02-07: time_incomplete goes on the missing side; time_equal on To, duration_order on Maximum; after an error the advanced form suggests exactly the submitted input
- [Phase 02]: 02-07: _load_pending sets self._show_advanced = False; 02-08 replaces that single assignment with has_advanced (D-03)
- [Phase 02]: 02-08: _show_advanced = has_advanced(self._pending) inside the run-once _load_pending, so Back and re-submits keep the user's own checkbox choice (D-03)
- [Phase 02]: 02-08: Task 2 is a regression suite (all cases green before changes); basic-step include/exclude validation now uses the calendar's case flag as a refactor (re.compile acceptance does not depend on IGNORECASE)
- [Phase 02]: 02-09: PATTERN_ERRORS = (re.error, OverflowError, RecursionError) is the single definition of an uncompilable pattern; _build_spec and first_invalid_pattern both catch it (CR-01)
- [Phase 02]: 02-09: pytest JUnit double-fail reports (call failure + teardown error) are rejected by the RED classifier; such RED records use a TAP rerun from a stdlib pytest reporter plugin
- [Phase 02]: 02-10: Preview escapes GFM autolink triggers (':' of '://', '.' after 'www' case-insensitive, '@') with a backslash after the character loop, plus '~' (G-02-2, IN-04)
- [Phase 03]: 03-01: stored source-option keys fixed: refresh_mode (interval|daily), refresh_hours, refresh_time (HH:MM), naive_timezone (utc|local), offset_minutes (-720..720); renaming needs async_migrate_entry + VERSION bump
- [Phase 03]: 03-01: coordinator keeps _next_refresh_at (aware UTC), recomputed via next_regular after every refresh (try/finally); _schedule_refresh override arms max(target - utcnow, 1 s)
- [Phase 03]: 03-01: backoff 5m/15m/1h/3h/6h then 6h, capped at the next regular refresh, floor 1 s; persistent failure = failing_since > 24 h before now; DST gap slot fires shifted, fold slot at first occurrence
- [Phase 03]: 03-01: tests/test_subentry_flow.py::test_channel_picker_lists_sorted_ids uses a channels-only feed; 03-04 (D-20 empty feed = failure) must adapt it
- [Phase 03]: Disk cache per URL source: raw payload in .cache/xmltv_calendar/<key>.feed (0o600) plus URL-free CacheMeta in Store xmltv_calendar.<key>; key = unique_id or entry_id, SHA-256 when not [0-9A-Za-z]{1,64}
- [Phase 03]: Cache valid only when stored source_id matches the current source and the payload has the stored size; payload written before metadata; unusable caches dropped
- [Phase 03]: Stale-while-revalidate start: any valid cache is shown at once; stale sets the refresh target to now (~1 s background refresh); setup only touches the network without a usable cache
- [Phase 03]: Calendars available while coordinator.data is not None (D-19)
- [Phase 03]: 03-03: NotModified carries the cleaned validators of a 304 (NOT_MODIFIED = validator-less instance); async_touch keeps a stored validator the response omits
- [Phase 03]: 03-03: unchanged sources (304, identical SHA-256 body, unchanged file) return the identical EpgData object; always_update=False plus calendar identity guard means no refilter
- [Phase 03]: 03-03: 304 without data parses the cache, else repeats the request without validators in the same refresh; a 304 to that retry fails unable_to_fetch
- [Phase 03]: 03-03: file sources skip the parse when (st_mtime_ns, st_size) matches the signature of this coordinator instance; allowlist check first, nothing persisted
- [Phase 03]: 03-04: SourceHealth (last_success, failing_since, last_failure_at/reason, consecutive_failures) is stored with CacheMeta in the cache Store as {meta, health}, for file sources too; success resets the streak but keeps the last failure for diagnostics
- [Phase 03]: 03-04: Repairs issue source_failing_<entry_id> (not fixable, WARNING, non-persistent) uses translation_key source_failing_<reason> with placeholders source and last_success (local YYYY-MM-DD HH:MM or -); reasons limited to FAILURE_REASONS, unknown -> unable_to_fetch
- [Phase 03]: 03-04: failure target = now + backoff_delay(consecutive_failures, now, next_regular); cache start re-raises the issue; failed first setup records health so retries count toward 24 h; async_remove_entry deletes the issue
- [Phase 03]: 03-04: a parsed feed with 0 current programmes raises UpdateFailed(empty_feed) before any cache write or file-signature update (D-20); first setup without cache -> SETUP_RETRY
- [Phase 03]: 03-05: offset-less timestamps in a DST-aware naive_tz resolve with fold=0 and are re-pinned to a cached fixed-offset timezone; no ZoneInfo leaves the pure parser
- [Phase 03]: 03-05: offset_minutes is added to start and stop before normalize (inferred stops follow shifted starts), once per parse via coordinator._parser(); downloads, cache and files share it, data in memory is never shifted
- [Phase 03]: 03-06: SECTION_TIMEZONE 'timezone' is form-only; naive_timezone/offset_minutes stored flat via SourceOptions.from_mapping(...).as_options()
- [Phase 03]: 03-06: setup download runs behind async_show_progress (eager_start=False) and is written to FeedCache(unique_id) only in the name step; errors return via progress_done(next_step_id='url') with input kept
- [Phase 03]: 03-06: schedule step reads the mode from the pending settings (from_mapping turns daily-without-time into interval); NotModified at setup = cannot_connect
- [Phase 03]: 03-06: async_probe_url removed; flow sniffs PROBE_BYTES of the full bounded download; tests use conftest add_url_source/add_file_source
- [Phase 03]: 03-07: diagnostics keys fixed: loaded, source (URL scheme+host / file name), options, health {last_success, failing_since, last_failure {time, reason}, consecutive_failures}, cache {fetched_at, size, has_etag, has_last_modified}, stats (ParseStats), calendars [{title, matches}] sorted by title, next_refresh
- [Phase 03]: 03-07: not-loaded entries read options from entry.options and health/cache presence from the Store (FeedCache(cache_key(entry))); diagnostics never refresh or download
- [Phase 03]: 03-08: An interval source keeps its last valid daily refresh_time in entry.options (_options_to_store), so switching back to daily pre-fills it; from_mapping ignores the key outside daily mode
- [Phase 03]: 03-08: Source options flow is a plain OptionsFlow reusing the setup builders; async_create_entry replaces entry.options and the single diffing listener reloads once from cache; identical values never reload
- [Phase 03]: 03-09: refresh_base(now, target) treats a target at most EARLY_FIRE_TOLERANCE (2 s) ahead as served; success and failure targets derive from it, so an early-firing HA timer neither re-requests a daily slot nor retries after MIN_DELAY, while manual refreshes keep their targets (D-12)
- [Phase 03]: 03-09: every non-cancellation Exception in _async_update_data (cache start, download, parse) is recorded as unable_to_fetch, backed off and re-raised as UpdateFailed(unable_to_fetch); one content-free WARNING per attempt, traceback at DEBUG; CancelledError passes through unrecorded
- [Phase 03]: 03-10: the setup flow seeds SourceHealth(last_success=fetched_at) with the cache metadata's fetched_at, only when FeedCache.async_write returned True; a failed write seeds nothing (WR-02)
- [Phase 03]: 03-10: tests/test_identity.py runs frozen at 2026-10-13T06:00:00+00:00 and asserts flow-created entries LOADED, so expired fixtures fail loudly (WR-03)
- [Phase 03]: UAT 2026-10-21: overrides accepted for 03-03 T1/T7, 03-04 T5, 03-09 T8/T9 (superseded by the WR-01/04/05 fixes in 19e262d); WR-06 and IN-09 deferred with reason in 03-REVIEW-DISPOSITION.md
- [Phase 04]: 04-01: next-match sensor value and attributes come from one MatchIndex.next_after lookup; no match or no calendar yet = unknown without attributes, unavailable only without source data
- [Phase 04]: 04-01: XmltvRuntimeData.add_entities is dict[Platform, callback] plus runtime.sensors; the update listener adds each platform's entities for new subentries (sensor.async_add_subentry_sensors)
- [Phase 04]: 04-01: calendar sends signal_matches(subentry_id) after every refilter and template-only write; sensor re-arms async_track_point_in_utc_time at the next start
- [Phase 04]: Blueprint notify_entity is optional; default action is if-guarded on notify_entity | count > 0 so users replacing the actions need no notify entity
- [Phase 04]: Blueprint description variable uses | default('') because CalendarEvent.as_dict() omits a missing description
- [Phase 04]: 04-03: release.yml is a verbatim copy of the sibling workflow with only the manifest path changed (D-29); tests execute its check-version and release scripts (bash, jq, stub gh) and shellcheck every workflow run step
- [Phase 04]: 04-04: New-match events fire only for refilter reason data after the entity's first completed refilter; initial (add, restart, reload, source option change) and config (filter/template edit) refilters update the persisted seen-set silently (D-10, D-11), no fingerprint
- [Phase 04]: 04-04: Burst cap 50 events per calendar and refresh (earliest first, one WARNING); seen entries pruned at stop < now - KEEP_PAST until 04-06 introduces per-calendar retention
- [Phase 04]: 04-04: Match store xmltv_calendar.matches.<cache key> is flushed on unload and calendars discard in-flight refilters on removal, so a late run never re-arms the old Store's delayed save (Pitfall 3)
- [Phase 04]: 04-05: Last-fetch sensor vocabularies fixed: trigger startup/scheduled/retry/revalidate/manual, outcome downloaded/not_modified/unchanged/read/cache_start/failed, cache fresh_hit/stale_hit/written/touched/write_failed/dropped/none; attributes = RefreshAttempt.as_dict order without time, then last_success, next_refresh, consecutive_failures, matches; diagnostics last_attempt uses the same as_dict
- [Phase 04]: 04-05: Run trigger = startup while coordinator.data is None, else the _target_kind of the target HA's timer serves (captured in a _handle_refresh_interval override), else manual; read before the cancellation fallback marks the target retry
- [Phase 04]: 04-05: Store shape {meta, health, attempt}; success/failure save the run with the health in one save, a cache start via async_save_attempt; RefreshAttempt.from_dict validates every field (vocabularies, reason pattern, status 100..599, counts >= 0, finite duration) and reads anything else as no run
- [Phase 04]: 04-06: Stored calendar key retention_days (int 0..7, default 1; bool/non-numeric/non-finite read as 1, clamp, fractions round down) is the last key of ADVANCED_DEFAULTS and with_defaults; retention cutoff now - retention_days prunes retained programmes and the seen-set (replaces KEEP_PAST in calendar.py)
- [Phase 04]: 04-06: Retained past matches are stored as raw programme data plus channel name in the match store ({calendars: {sid: {seen, retained}}, source: {naive_timezone, offset_minutes}}), captured on every refilter (previous and new matches), on entity removal and on HA stop; feed wins on UID collision; filter edits re-check retained programmes; a changed timezone fingerprint drops retained programmes and keeps seen-sets; MAX_RETAINED 5000 latest per calendar
- [Phase 04]: 04-06: Diagnostics calendar rows are {title, matches (feed), retained (shown in addition, inside the window)}; get_events hides retained programmes whose window ended even without a refilter

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1] UAT test 3 (calendar trigger with −5 min offset in a live automation) deferred; automated trigger tests cover it — see 01-UAT.md Deferred Follow-Ups
- [Phase 2] Review warnings accepted as non-blocking in Phase 1 UAT: WR-07 (absurd in-window stop → duration cap / FLT-08), IN-14 (get_events OverflowError near year 0001 → clamp in window.py); WR-08 (skipped_malformed not logged) → Phase 3 SRC-12
- [Phase 3] Only fixtures and the generated 60 MB feed are tracked; Phase 3 caching and conditional requests were exercised in the ha-dev walkthrough (03-UAT test 1), not yet against a long-running real feed on ha-host
- [Phase 3] Deferred review findings: WR-06 (cache-parse crash logged only at DEBUG), IN-09 (recurring swallowed CancelledError retries every 5 min); see 03-REVIEW-DISPOSITION.md
- [Phase 3] Parse time on `ha-host` hardware is unmeasured (dev-box ha-dev: 60 MB in 2.8 s, UI stayed responsive in Phase 1 UAT)
- Research suggested deferring FLT-09, EVT-07 and EVT-08 to v2, but REQUIREMENTS.md keeps them in v1 (mapped to Phases 2 and 4)
- Event-loop gap under the 60 MB benchmark is 86-164 ms on the dev box (limit 250 ms): CI benchmark job may be flaky on slower runners; 01-09 ran on the dev-laptop ha-dev only (60 MB parse 2.8 s in-container), ha-host still unmeasured (RESEARCH A2)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261015-su3 | Add German translation de.json mirroring en.json with key/placeholder parity test | 2026-10-15 | 4345d53 | [261015-su3-add-german-translation-de-json-mirroring](./quick/261015-su3-add-german-translation-de-json-mirroring/) |
| 261015-u6j | Collapse line breaks in preview feed text (WR-05) | 2026-10-15 | 9b87e7f | [261015-u6j-collapse-line-breaks-in-preview-feed-tex](./quick/261015-u6j-collapse-line-breaks-in-preview-feed-tex/) |
| 261016-1ox | Fix review findings WR-01 and WR-02, defer WR-03 and WR-04 | 2026-10-16 | 03c2f9b | [261016-1ox-fix-review-findings-wr-01-and-wr-02-defe](./quick/261016-1ox-fix-review-findings-wr-01-and-wr-02-defe/) |
| 4 | Rename repository references to homeassistant-xmltv-calendar-integration (fast; 5 files, exceeds fast's 3-edit guideline, mechanical rename) | 2026-10-16 | 93ad979 | — |

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| fixture | D-15 real German feed excerpt (`tests/fixtures/real_de_excerpt.xml`) plus `scripts/trim_feed.py`; `tests/xmltv/test_real_feed.py` skips until it exists | deferred (user decision "none", 01-09 Task 2: licensing risk in a public repo) | 2026-10-14 (01-09) | v1 |

## Session Continuity

Last session: 2026-10-21T10:11:07.587Z
Stopped at: Completed 04-06-PLAN.md
Resume file: None
