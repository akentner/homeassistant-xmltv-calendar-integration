---
phase: 03-resilient-sources
verified: 2026-10-16T18:20:00Z
status: human_needed
score: 93/95 must-haves verified
covered_files:
  - .planning/phases/03-resilient-sources/03-01-PLAN.md
  - .planning/phases/03-resilient-sources/03-01-SUMMARY.md
  - .planning/phases/03-resilient-sources/03-02-PLAN.md
  - .planning/phases/03-resilient-sources/03-02-SUMMARY.md
  - .planning/phases/03-resilient-sources/03-03-PLAN.md
  - .planning/phases/03-resilient-sources/03-03-SUMMARY.md
  - .planning/phases/03-resilient-sources/03-04-PLAN.md
  - .planning/phases/03-resilient-sources/03-04-SUMMARY.md
  - .planning/phases/03-resilient-sources/03-05-PLAN.md
  - .planning/phases/03-resilient-sources/03-05-SUMMARY.md
  - .planning/phases/03-resilient-sources/03-06-PLAN.md
  - .planning/phases/03-resilient-sources/03-06-SUMMARY.md
  - .planning/phases/03-resilient-sources/03-07-PLAN.md
  - .planning/phases/03-resilient-sources/03-07-SUMMARY.md
  - .planning/phases/03-resilient-sources/03-08-PLAN.md
  - .planning/phases/03-resilient-sources/03-08-SUMMARY.md
  - .planning/phases/03-resilient-sources/03-09-PLAN.md
  - .planning/phases/03-resilient-sources/03-09-SUMMARY.md
  - .planning/phases/03-resilient-sources/03-10-PLAN.md
  - .planning/phases/03-resilient-sources/03-10-SUMMARY.md
  - custom_components/xmltv_calendar/__init__.py
  - custom_components/xmltv_calendar/cache.py
  - custom_components/xmltv_calendar/calendar.py
  - custom_components/xmltv_calendar/config_flow.py
  - custom_components/xmltv_calendar/const.py
  - custom_components/xmltv_calendar/coordinator.py
  - custom_components/xmltv_calendar/diagnostics.py
  - custom_components/xmltv_calendar/source.py
  - custom_components/xmltv_calendar/translations/de.json
  - custom_components/xmltv_calendar/translations/en.json
  - custom_components/xmltv_calendar/xmltv/parser.py
  - custom_components/xmltv_calendar/xmltv/schedule.py
  - custom_components/xmltv_calendar/xmltv/timeparse.py
  - tests/conftest.py
  - tests/test_cache.py
  - tests/test_calendar.py
  - tests/test_config_flow.py
  - tests/test_diagnostics.py
  - tests/test_empty_feed.py
  - tests/test_file_source.py
  - tests/test_filtering.py
  - tests/test_identity.py
  - tests/test_init.py
  - tests/test_options_flow.py
  - tests/test_reconfigure.py
  - tests/test_refresh.py
  - tests/test_repairs.py
  - tests/test_schedule_refresh.py
  - tests/test_source.py
  - tests/test_subentry_flow.py
  - tests/test_timezone_options.py
  - tests/test_tracer.py
  - tests/xmltv/test_parser.py
  - tests/xmltv/test_schedule.py
  - tests/xmltv/test_timeparse.py
covered_digest: "v3:sha256:0652f1725300ce0250136a87a93c0c5532ad9d689ef95487d568fde4e22c4332"
behavior_unverified: 2
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 70/79
  gaps_closed:
    - "CR-01: a daily slot is requested once even when HA's timer fires up to ~0.95 s early; a fast failure at the slot backs off 5 min (03-01 truth 1, 03-01 prohibition)"
    - "CR-02: every non-cancellation Exception during cache start, download or parse is recorded as unable_to_fetch, backs off and reaches HA as UpdateFailed; the Repairs issue appears after 24 h (03-04 truths 3 and 8, roadmap SC 4)"
    - "WR-02: a flow-created source reports the setup download as last_success in coordinator health, diagnostics and Repairs text (03-07 truth 3, roadmap SC 5)"
    - "WR-03: tests/test_identity.py runs frozen at 2026-10-13 and asserts LOADED entries (03-01 truth 11)"
  gaps_remaining: []
  regressions: []
advisory:
  - finding: "WR-04: a CancelledError that HA swallows (the refresh task itself is not being cancelled) on a timer-fired refresh leaves _next_refresh_at at the served, now past, target; HA re-arms at MIN_DELAY and retries about once per second, unrecorded and invisible"
    category: other
    reason: "Reproduced by the verifier (6 attempts in 11 s, consecutive_failures 0, next_refresh_at stuck at 2026-10-14T06:00Z). Non-blocking: not reachable from feed content or modelled network failures (Python 3.14 asyncio.timeout and aiohttp ClientTimeout raise TimeoutError; real task cancellation is re-raised by HA and unload sets _shutdown_requested, so the stale timer is a no-op). Needs a runtime/library bug that leaks CancelledError. Cheap fix: set a provisional target (served or now + 5 min) at the start of _async_update_data. Recommended as a follow-up before release; resolves the literal wording of the 03-01/03-09 prohibition."
    evidence_status: "deterministic repro with injected CancelledError; no input-reachable trigger found"
  - finding: "WR-05: an unexpected exception while parsing the disk cache at setup keeps the cache, so setup retries re-parse the same cache and never download (stays in SETUP_RETRY until the cache is removed)"
    category: other
    reason: "Reproduced (8 cache parses, 0 downloads, SETUP_RETRY over 20 min). Non-blocking: this is exactly 03-09 truth 8 as planned; zero network cost; every attempt is recorded (consecutive_failures, content-free WARNING), and the unable_to_fetch Repairs issue appears after 24 h, so it is visible. The cache is only written after those same bytes parsed with programmes, so a crash on it needs an integration-upgrade bug (a deterministic bug would also crash on a fresh download; the proposed drop-and-download fix would then download on every setup retry, up to every 10 min) or a transient MemoryError (keeping the offline fallback is right). Cost: one cache parse per HA setup retry (5 s doubling, capped at 600 s). Residual: the setup-retry text says 'Unable to download' although nothing was downloaded, and a fixed upstream feed is never fetched. Follow-up, not a goal blocker."
    evidence_status: "deterministic repro with injected RuntimeError on the cache parse"
  - finding: "WR-01: the 304 / identical-body / unchanged-file shortcuts skip the empty-feed check, so a provider that stops updating is reported as success and calendars silently run dry"
    category: other
    reason: "Carried forward as advisory from the initial verification; outside every plan's must-haves (304 is success by D-17). Still disposition 'open' in 03-REVIEW-DISPOSITION.md: needs a fix plan or an explicit 'deferred' with reason."
    evidence_status: "none provided (design gap, no failing must-have)"
behavior_unverified_items:
  - truth: "A manual update_entity that arrives while a scheduled refresh runs is serialized by the coordinator's debouncer lock, so health, cache and the refresh target are never written by two refreshes at once (03-04 truth 11, restated as 03-09 truth 11; verification: backstop)"
    test: "Start a scheduled refresh against a slow feed and fire homeassistant.update_entity on the calendar while the download is running"
    expected: "The two refreshes run one after the other; the Store holds one consistent CacheMeta/SourceHealth and consecutive_failures changes by at most 1 per refresh"
    why_human: "Backstop truth relying on HA's _debounced_refresh.async_lock(); no test exercises concurrent refreshes"
  - truth: "An options save during a running parse cannot mix old and new timezone settings: the reload replaces the coordinator and the old result is discarded (03-05 truth 10; verification: backstop)"
    test: "Change the timezone option in the options flow while a large-feed parse is running"
    expected: "After the reload the events reflect only the new timezone options; nothing from the old coordinator's parse is shown"
    why_human: "Backstop truth; no test exercises an options save during an in-flight parse"
human_verification:
  - test: "ha-dev walkthrough (03-08 human-check): add a URL source (progress dialog, collapsed timezone section), restart HA, save options, run update_entity against the real feed, check curl -sI for ETag/Last-Modified, download diagnostics, check German texts"
    expected: "One download per setup; no download on restart or options save; update_entity sends validators; diagnostics redacted and show last_success right after setup; no tracebacks or blocking-call warnings"
    why_human: "Visual flow, real feed server behaviour and HA runtime logs cannot be checked from the test suite"
  - test: "Debouncer serialization (backstop, see behavior_unverified_items[0])"
    expected: "Two refreshes run one after the other with consistent health and cache"
    why_human: "Backstop truth without behavioural test"
  - test: "Options save during a running parse (backstop, see behavior_unverified_items[1])"
    expected: "Only the new timezone options show after the reload"
    why_human: "Backstop truth without behavioural test"
  - test: "Decide on the flagged prohibition 'MUST NOT contact the feed host more often than the user's schedule ... no exception, anticipated or not ... turns into a faster retry' (03-01, 03-09): accept WR-04 as a non-input-reachable residual (set disposition deferred with reason) or schedule the provisional-target fix; likewise set dispositions for WR-05 and WR-01"
    expected: "Each of WR-01, WR-04, WR-05 has disposition fixed or deferred-with-reason in 03-REVIEW-DISPOSITION.md before the phase is marked complete"
    why_human: "Judgment-tier prohibition: the verifier's verdict (holds for every input-reachable exception, violated only by an injected CancelledError) is non-authoritative"
---

# Phase 3: Resilient Sources Verification Report

**Phase Goal:** Sources keep every calendar populated at minimal network and CPU cost: cached across restarts, refreshed on the user's schedule and only when changed, tolerant of failures and timezone quirks, editable later, and visible to the user when something goes wrong.
**Mode:** mvp (user story in all PLAN files, unchanged from the initial verification)
**Verified:** 2026-10-16T18:20:00Z
**Status:** human_needed
**Re-verification:** Yes, after gap closure (03-09: CR-01/CR-02, 03-10: WR-02/WR-03; commits 6f5a1b3..acde918)

## User Flow Coverage

| Step | Expected | Evidence | Status |
|------|----------|----------|--------|
| Add a URL source | Progress dialog, schedule step, timezone section, one HTTP request, last success recorded | `test_url_source_end_to_end_with_progress_and_seeded_cache` now also asserts `health.last_success == NOW`, diagnostics `last_success`/`fetched_at == NOW`, `call_count == 1` | VERIFIED (visual part in UAT) |
| Restart / reload | Filled from disk cache, no download while fresh | `test_restart_uses_fresh_cache`, `test_reload_uses_fresh_cache`, `test_stale_cache_offline_start_still_loads` (regression: pass) | VERIFIED |
| Refreshed on the user's schedule | Once per daily slot / interval | `refresh_base` (`schedule.py:180-190`) used in `_set_regular_target` (`coordinator.py:142-146`) and `_async_handle_failure` (`:199-207`). Verifier repro with HA's real timer, stepping 16:14:58Z..16:15:03.5Z in 0.5 s steps: call_count 1 -> 2 and stays 2, next target 2026-10-14T16:15Z. Direct refresh at 16:14:59.05Z: no further request at 16:15:01/03/20 | VERIFIED (CR-01 closed) |
| Only when changed | 304 / identical body / unchanged file: no download body, no parse | `test_refresh.py`, `test_file_source.py` (regression: pass) | VERIFIED |
| Tolerant of failures | Last good data kept; capped backoff; recorded | `except Exception` clause (`coordinator.py:169-178`). Verifier repro: `parse` raising `MemoryError` on a timer-fired refresh, then 20 s of 2 s steps: 1 request, `consecutive_failures 1`, `unable_to_fetch`, next target +5 min. `aiohttp.ClientPayloadError`: 1 request, data object unchanged. Residuals WR-04/WR-05 (advisory, see below) | VERIFIED |
| Timezone quirks | Naive = local and/or offset correction | `test_timezone_options.py` (regression: pass) | VERIFIED |
| Editable later | Options flow, single reload, no download | `test_options_flow.py` (regression: pass) | VERIFIED |
| Visible when something goes wrong | Repairs after >24 h for every failure kind; diagnostics with last success | `test_unexpected_exception_raises_issue_after_24h`, `test_seeded_source_issue_names_setup_download` ("2026-10-13 08:00", not "-"), diagnostics step 7 | VERIFIED (WR-01 stalled-feed case remains advisory) |
| Outcome | Calendars stay populated at minimal network and CPU cost | CR-01 and CR-02 loops gone (reproduced closed). Only the injected-CancelledError path (WR-04) still loops | VERIFIED, with one flagged residual |

## Goal Achievement

### Roadmap Success Criteria (contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | Progress during setup download; options flow switches interval/daily and edits timezone; source options reload, calendar edits do not | VERIFIED | Regression: `test_config_flow.py`, `test_options_flow.py`, `test_reconfigure.py` pass |
| SC2 | Restart/reload uses fresh cache; unchanged feed not re-downloaded/re-parsed; update_entity refreshes immediately | VERIFIED | Regression: `test_cache.py`, `test_refresh.py` pass; `test_manual_refresh_*` guards pass |
| SC3 | Naive timestamps local and/or offset correction | VERIFIED | Regression: `test_timezone_options.py`, parser tables pass |
| SC4 | Failure keeps last good data; persistent failure raises a Repairs issue that clears on success | VERIFIED (was FAILED) | `test_unexpected_exception_backs_off_and_is_recorded` (data `is previous`, calendar not unavailable, one request in 10 s), `test_unexpected_exception_raises_issue_after_24h`, verifier MemoryError repro |
| SC5 | Diagnostics with counts, last success/failure, redaction | VERIFIED (was partial) | `config_flow.py:357-366` seeds `SourceHealth(last_success=fetched_at)` only when `async_write` returns True; step 7 asserts coordinator and diagnostics values |

### Previous Gaps (full 3-level re-check)

| Gap | Exists | Substantive | Wired / behaviour | Status |
|-----|--------|-------------|-------------------|--------|
| CR-01 early fire | `EARLY_FIRE_TOLERANCE`, `refresh_base` in `schedule.py` (pure, `test_purity.py` passes) | Returns target only when `now < target <= now + 2 s` | Both target computations call `refresh_base(now, self._next_refresh_at)`; tests `test_daily_slot_served_once_when_timer_fires_early`, `test_daily_fast_failure_before_slot_backs_off_five_minutes`, guards `test_manual_refresh_before_slot_keeps_the_slot`, `test_manual_refresh_restarts_the_interval` pass; real-timer repro closed | CLOSED |
| CR-02 unexpected exceptions | `_async_read_source`, `_async_handle_failure`, `except Exception as err` | Records, sets backoff, logs class name only, re-raises `UpdateFailed(unable_to_fetch) from err` | Cache start, download and parse are all inside the guarded `try`; 4 named tests pass; MemoryError repro closed | CLOSED |
| WR-02 last_success after flow | `SourceHealth` imported and saved in `_async_seed_cache` | Same `fetched_at` as CacheMeta; only after a successful write | Coordinator `_async_setup` loads the Store before the first refresh; seed awaited before `async_create_entry`; step 7 and issue test pass | CLOSED |
| WR-03 unfrozen identity tests | `pytestmark = pytest.mark.freeze_time(NOW)` | 3 `ConfigEntryState.LOADED` asserts, 1 single-download assert | All other fixture-loading modules checked: frozen per module or by `freezer` | CLOSED |

### Plan Must-Have Truths

| Plan | Truths | Verified | Not verified | Notes |
|------|--------|----------|--------------|-------|
| 03-01 schedule engine | 11 | 11 | none | T1 and T11 now verified (CR-01, WR-03 closed) |
| 03-02 disk cache | 11 | 11 | none | Regression pass. T5 "a cached payload that no longer parses is deleted and downloaded again" holds for `FeedError`/empty parses; an unexpected exception is deliberately kept (03-09 T8, WR-05) |
| 03-03 conditional refresh | 8 | 8 | none | Regression pass |
| 03-04 failure health / Repairs / backoff | 11 | 10 | T11 backstop | T3 and T8 now verified (CR-02 closed) |
| 03-05 timezone options | 10 | 9 | T10 backstop | Regression pass |
| 03-06 setup flow | 8 | 8 | none | Regression pass; still one download in total |
| 03-07 diagnostics | 6 | 6 | none | T3 now verified (WR-02 closed) |
| 03-08 options flow | 9 | 9 | none | UAT part of T9 queued |
| 03-09 gap closure CR-01/CR-02 | 10 (T11 = 03-04 T11, deduplicated) | 10 | none | T9 (CancelledError records nothing, keeps target) holds as written; its timer-fired consequence is WR-04 |
| 03-10 gap closure WR-02/WR-03 | 6 | 6 | none | Seed before `async_create_entry` verified in code order (`config_flow.py:334-335`) and by the test reading health right after the flow |

**Score:** 93/95 (5 roadmap SCs + 90 plan truths). The 2 not verified are backstop truths without behavioural evidence (PRESENT_BEHAVIOR_UNVERIFIED, routed to human).

### Prohibitions

| Plan | Prohibition | Tier | Verdict (non-authoritative) |
|------|-------------|------|-----------------------------|
| 03-01 / 03-09 | MUST NOT contact the feed host more often than the schedule; no exception and no early timer turns into a faster retry | judgment | Holds for the early-firing timer and every `Exception` (reproduced). Literal violation only via an injected, HA-swallowed `CancelledError` (WR-04). **unverified-prohibition: human review recommended** |
| 03-02 | No download at start/reload/options save while the cache is fresh | judgment | Holds |
| 03-03 | No re-download/re-parse of unchanged feeds; validators kept on manual refresh | judgment | Holds |
| 03-04 | Never blank or disable calendars while last good data exists | judgment | Holds; new test asserts `coordinator.data is previous` and the calendar stays available on unexpected exceptions |
| 03-07 | No programme content or filter patterns in diagnostics | judgment | Holds |
| 03-10 | Never report a last success that did not happen | judgment | Holds: health is seeded only inside `if await cache.async_write(...)` |

### WR-04 / WR-05 decision (requested by the orchestrator)

Both are **non-blocking warnings** (recorded under `advisory`), not gaps. They are not regressions; they are residuals of the CR-02 fix that the plan encoded on purpose (03-09 T8, T9).

- **WR-04 (swallowed CancelledError, 1 s retry):** reproduced, 6 attempts in 11 s with nothing recorded. It does not block because no input or modelled failure reaches it:
  - The refresh only awaits aiohttp with `ClientTimeout` (`source.py:220`), executor jobs and Store saves. On Python 3.14 a timeout is `TimeoutError`, which is an `Exception` and handled.
  - When the refresh task itself is cancelled, HA re-raises the error (`update_coordinator.py:575-580`).
  - After an unload, `_shutdown_requested` makes the re-armed timer a no-op (`:445`).
  - What remains is a library or runtime that leaks `CancelledError`. Feed content cannot trigger that, unlike CR-02, where a malformed feed could crash the parser or a large one raise `MemoryError`.
  - It still breaks the literal wording of the prohibition, so it is flagged for a human decision. The fix is small: set a provisional target at the start of `_async_update_data`. Doing it before release is recommended.
- **WR-05 (cache-parse crash keeps the cache, setup never downloads):** reproduced, 8 parses, 0 downloads, SETUP_RETRY. It does not block the goal:
  - Network cost is zero.
  - CPU cost is bounded by HA's setup-retry backoff (5 s doubling, capped at 600 s).
  - Every attempt is recorded and logs a WARNING, and the Repairs issue appears after 24 h, so "visible" holds.
  - The cache is written only after those bytes parsed successfully with programmes. A crash on them therefore means an integration bug, which a fresh download would hit too (and the suggested fix would turn into a download on every retry), or a transient `MemoryError`, where keeping the offline fallback is correct.
  - Two residuals: the misleading "Unable to download" setup text, and a fixed upstream feed is never fetched until the cache is removed. Both are follow-up material.

### Required Artifacts

`verify.artifacts`: every plan passes. 03-01 6/6, 03-02 6/6, 03-03 6/6, 03-04 6/6, 03-05 4/4, 03-06 6/6, 03-07 3/3, 03-08 4/4, 03-09 5/5, 03-10 3/3.

| Artifact | Status | Details |
|----------|--------|---------|
| `xmltv/schedule.py` | VERIFIED | `EARLY_FIRE_TOLERANCE`, `refresh_base`; still HA-free (purity test passes) |
| `coordinator.py` | VERIFIED | Single guarded read, shared failure handler, `refresh_base` on both target paths |
| `config_flow.py` | VERIFIED | Health seeded with the cache write |
| `tests/test_schedule_refresh.py`, `tests/test_repairs.py`, `tests/xmltv/test_schedule.py`, `tests/test_config_flow.py`, `tests/test_identity.py` | VERIFIED | New tests substantive; all pass |
| Remaining Phase 3 artifacts | VERIFIED (regression) | Unchanged since the initial verification; suite green |

### Key Link Verification

`verify.key-links`: every plan verifies, 26/26 across the 10 plans (03-09: 3/3, 03-10: 2/2). Spot-checked by hand:

- `refresh_base(now, self._next_refresh_at)` at `coordinator.py:145` and `:206`.
- `translation_key=_DEFAULT_REASON) from err` at `:178`.
- `_async_record_failure(` reached from `_async_handle_failure`, which leads to `_sync_issue`.
- `async_save_health(` at `config_flow.py:366`.
- `_health(coordinator.health)` in `diagnostics.py`.

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| Calendar entities | `coordinator.data` | Download, then executor parse, or the cached payload | yes | FLOWING |
| Repairs issue | `SourceHealth` | `_async_record_failure`, now for every `Exception` | yes | FLOWING |
| Diagnostics | health, cache_meta, stats | live coordinator, or the Store for unloaded entries; flow seed supplies last_success | yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite (run once) | `uv run pytest tests/ -q -rs` | 815 passed, 1 skipped (real-feed check deferred), 0 "Lingering", 49.9 s | PASS |
| Lint/format | `uv run ruff check . && uv run ruff format --check .` | clean; 62 files formatted | PASS |
| Gap-closure tests (named) | `pytest ... -k "fires_early or fast_failure_before_slot or manual_refresh or unexpected or cancelled or seeded or identity or refresh_base or early_fire"` | 29 passed | PASS |
| CR-01 real-timer repro (scratch copy) | Step 16:14:58Z to 16:15:03.5Z in 0.5 s steps, daily 18:15 Berlin | counts `[1,1,1,1,2,2,2,2,2,2,2,2]`, next 2026-10-14T16:15Z | PASS |
| CR-01 direct early refresh | `async_refresh` at 16:14:59.05Z, then step 16:15:01, 16:15:03, 16:20 | counts `[2,2,2,2]` | PASS |
| CR-02 repro (MemoryError in parse, timer path) | Step past target, then 10 steps of 2 s | 1 request, failures 1, next +5 min | PASS |
| WR-04 repro (CancelledError from fetch, timer path) | Step past target, then 6 steps of 2 s | 6 attempts, failures 0, next stuck at past target | FAIL (advisory) |
| WR-05 repro (RuntimeError on cache parse at setup) | 40 steps of 30 s | 8 parses, 0 downloads, SETUP_RETRY | as planned (advisory) |

The repros ran in a throwaway copy under the session scratchpad. The repository was not modified.

### Probe Execution

There are no `scripts/*/tests/probe-*.sh` files, and no plan declares a probe, so Step 7c does not apply.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SRC-05 | 03-01, 03-06, 03-08, 03-09 | Daily fixed-time refresh | SATISFIED | CR-01 closed (tests and real-timer repro) |
| SRC-06 | 03-02 | Disk cache, no re-fetch while fresh | SATISFIED | `test_cache.py` |
| SRC-07 | 03-03 | Conditional re-download | SATISFIED | `test_refresh.py`, `test_file_source.py` |
| SRC-08 | 03-04, 03-09 | Failed fetch/parse keeps last good data | SATISFIED | `test_failures_keep_last_good_data`, `test_unexpected_exception_backs_off_and_is_recorded` |
| SRC-10 | 03-05, 03-06, 03-08 | Naive = local and/or offset correction | SATISFIED | `test_timezone_options.py` |
| SRC-11 | 03-04, 03-09 | Repairs on persistent failure, clears on success | SATISFIED | `test_persistent_failure_raises_and_clears_issue`, `test_unexpected_exception_raises_issue_after_24h` |
| SRC-12 | 03-07, 03-10 | Diagnostics with counts, last success/failure, redaction | SATISFIED | `test_diagnostics_end_to_end`, step 7 of the URL flow test |
| CFG-02 | 03-08 | Options flow for refresh and timezone | SATISFIED | `test_options_flow.py` |
| CFG-03 | 03-06, 03-10 | Progress during setup download | SATISFIED (visual check in UAT) | `progress_action == "download"`, single download |
| AUT-04 | 03-03 | Manual refresh via update_entity | SATISFIED | `test_update_entity_refreshes_now_with_validators`, manual-refresh guards |

All 10 IDs are claimed by at least one plan, and REQUIREMENTS.md maps no other ID to Phase 3, so none are orphaned. The "Gaps Found" statuses in REQUIREMENTS.md (commit 21e69d6) were set on purpose and are not a gap. They can go back to Complete once the human items are resolved.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `coordinator.py` | 162-185 | No target set when a swallowed `CancelledError` exits the refresh (WR-04) | Warning (advisory) | 1 s retry loop on a library-leaked CancelledError only |
| `coordinator.py` | 193-196, 308-326 | Cache kept on an unexpected cache-parse exception (WR-05) | Warning (advisory) | Stuck in SETUP_RETRY without downloading; recorded and visible |
| `coordinator.py` | 355-379, 421-423 | Unchanged shortcuts skip the empty-feed check (WR-01) | Warning (advisory, carried forward) | A stalled provider is never reported |
| `config_flow.py` | 357 | `fetched_at` taken at the name step, not at download completion (IN-06) | Info | Seconds-to-minutes late last_success; a slot between download and name step counts as served |
| tests | | Duplicated `_raise_runtime_error`, tautological `test_early_fire_tolerance` (IN-07) | Info | Hygiene |

The files changed since `659c9e6` contain no TBD/FIXME/XXX/TODO/HACK markers. The `PLACEHOLDERS` hits in `config_flow.py` are identifiers, not markers. Under the re-verification evidence gate, nothing is promoted to blocker: CR-01/CR-02 are closed by tests and repros, and WR-04/WR-05 are justified above as non-blocking.

### Human Verification Required

1. **ha-dev walkthrough (03-08 human-check).** Covers the progress dialog and collapsed timezone section; one download per setup; no download on restart or options save; update_entity against the real feed sends validators; `curl -sI` for ETag/Last-Modified; diagnostics redacted, with last_success present right after setup; German texts; no tracebacks or blocking-call warnings.
2. **Debouncer serialization (backstop).** Fire update_entity during a running scheduled refresh. Expected: the refreshes run one after the other, with consistent health and cache.
3. **Options save during a running parse (backstop).** Expected: only the new timezone options are visible after the reload.
4. **Prohibition decision and dispositions.** Decide WR-04: fix it with the provisional target (recommended, small), or set `deferred` with the non-input-reachable rationale. Set dispositions for WR-05 and WR-01 in 03-REVIEW-DISPOSITION.md.

### Gaps Summary

All four previous gaps are closed, and the verifier confirmed each fix independently:

- **CR-01:** an early-firing HA timer now serves its slot once, and a fast failure backs off 5 min.
- **CR-02:** every `Exception` is recorded, backed off, surfaced as `UpdateFailed(unable_to_fetch)` and raised in Repairs after 24 h. The once-per-second download loop is gone.
- **WR-02:** a flow-created source reports its setup download as last_success.
- **WR-03:** the identity tests run frozen and assert LOADED.

There are no regressions: 815 tests pass, Ruff is clean, and all 10 plans pass the artifact and key-link checks.

The phase goal is achieved. The status is `human_needed` rather than `passed` for three reasons: two backstop truths have no behavioural test, the end-of-phase UAT walkthrough is still pending, and the judgment-tier prohibition is flagged. WR-04, WR-05 and WR-01 are non-blocking follow-ups that need a disposition. WR-04 is the one worth fixing before release.

---

_Verified: 2026-10-16T18:20:00Z_
_Verifier: Claude (gsd-verifier)_
