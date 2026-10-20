---
phase: 03-resilient-sources
verified: 2026-10-20T23:12:14Z
status: human_needed
score: 90/95 must-haves verified
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
covered_digest: "v3:sha256:fd1fb0032497082dbaecee9f48ffc3024d237583121d2bc7a9ab1305892e7eb3"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 93/95
  gaps_closed:
    - "WR-04 (advisory): an HA-swallowed CancelledError on a timer-fired refresh no longer retries every second; a provisional target max(served, now + 5 min) is set before any await (coordinator.py:163-166), test_timer_cancelled_refresh_does_not_retry_every_second passes"
    - "WR-05 (advisory): an unexpected cache-parse exception drops the cache and downloads (coordinator.py:323-334); verifier repro: the cache is parsed, dropped and replaced by the changed download in one setup"
    - "WR-01 (advisory): 304, identical-body and unchanged-file shortcuts reject data with no programme ending after now - KEEP_PAST as empty_feed, before async_touch (coordinator.py:367, :388, :434, :446-447)"
    - "Backstop truths 03-04 T11 (debouncer serialization) and 03-05 T10 (options save during a parse) are no longer behavior-unverified: human UAT pass recorded in 03-UAT.md tests 2 and 3"
  gaps_remaining: []
  regressions: []
advisory:
  - finding: "WR-06: the WR-05 catch-all in _async_parse_cached logs a cache-parse crash only at DEBUG, without the exception class or exc_info, and logs the drop twice; when the following download parses, nothing is recorded in health and nothing reaches the default log"
    category: other
    reason: "Confirmed by verifier repro (state LOADED, consecutive_failures 0, no WARNING line). Non-blocking: the calendars stay populated, so the source has not failed from the user's point of view, and when the download crashes too the existing WARNING plus health recording apply. It weakens CR-02's goal of making latent parser bugs visible. Fix proposed in 03-REVIEW.md (WARNING with class name, DEBUG with exc_info, one drop line). Disposition still 'open'."
    evidence_status: "code inspection coordinator.py:328-333 plus scratchpad repro; no failing must-have"
  - finding: "IN-09: an HA-swallowed CancelledError that keeps recurring retries every 5 min forever (fixed BACKOFF_STEPS[0], no escalation, no record, not capped by the regular slot)"
    category: other
    reason: "Residual of the WR-04 fix, the same non-input-reachable trigger the previous verification accepted (a library or runtime leaking CancelledError while the refresh task is not cancelled). About 288 requests a day in the worst case, against roughly 86,400 before the fix. Part of the prohibition judgment in human_verification[1]."
    evidence_status: "code inspection coordinator.py:163-166; encoded by tests/test_schedule_refresh.py:399-408"
human_verification:
  - test: "Accept or reject the 5 plan truths whose literal wording the user-approved 19e262d fixes (WR-01, WR-04, WR-05) superseded: 03-03 T1, 03-03 T7, 03-04 T5 (a 304 / unchanged file counts as success, now only while the data in memory still holds a programme ending after now - 1 day), 03-09 T8 (cache-parse crash 'without any download', now drops the cache and downloads), 03-09 T9 (CancelledError 'changes no refresh target', now sets a provisional target of at least now + 5 min). Paste the override block from the report into this frontmatter, or reject one and re-plan it as a gap"
    expected: "Each of the 5 truths is carried as PASSED (override) with accepted_by/accepted_at, or explicitly rejected; a re-run of verification then reaches passed (or gaps_found for rejected ones)"
    why_human: "The verifier may not accept a deviation from a planned must-have on the user's behalf. 03-UAT.md records the user's choice to fix WR-01/04/05, but no override entry exists"
  - test: "Confirm the non-authoritative judgment-tier prohibition verdicts after 19e262d, especially 03-01/03-09 'MUST NOT contact the feed host more often than the schedule ... no exception turns into a faster retry'. Two residuals: (a) WR-05 path, a deterministic parser crash on both cached and downloaded bytes now downloads once per HA setup retry (verifier repro: 8 downloads in 20 min, 5 s doubling up to 600 s, then 1 per 10 min; 0 downloads before the fix; the same cadence as the long-accepted 'no cache + failed first download' path, 03-02 T7), (b) IN-09, 5-min fixed retry on a recurring HA-swallowed CancelledError. Also set the disposition of WR-06 (fixed or deferred with reason) in 03-REVIEW-DISPOSITION.md"
    expected: "Each residual accepted with a reason (deferred), or scheduled as a follow-up; WR-06 has disposition fixed or deferred-with-reason before the phase is marked complete"
    why_human: "Judgment-tier prohibition: the verifier's verdict (holds for every input-reachable path; the residuals need an integration bug or a library that leaks CancelledError) is non-authoritative and must not be absorbed into a passed verdict"
---

# Phase 3: Resilient Sources Verification Report

**Phase Goal:** Sources keep every calendar populated at minimal network and CPU cost: cached across restarts, refreshed on the user's schedule and only when changed, tolerant of failures and timezone quirks, editable later, and visible to the user when something goes wrong.
**Mode:** mvp (user story in all PLAN files; the outcome clause "every calendar stays populated at minimal network and CPU cost" is the success condition)
**Verified:** 2026-10-20T23:12:14Z
**Status:** human_needed
**Re-verification:** Yes. The previous report (2026-10-16T18:20Z, human_needed, 93/95) went stale when commit 19e262d changed `coordinator.py` and four test modules. The rerun fully re-verifies what 19e262d touched and regression-checks everything else.

## User Flow Coverage

| Step | Expected | Evidence | Status |
|------|----------|----------|--------|
| Add a URL source | Progress dialog, schedule step, timezone section, one HTTP request, last success recorded | `test_url_source_end_to_end_with_progress_and_seeded_cache` passes (`call_count == 1`, `health.last_success == NOW`). `config_flow.py` is unchanged since the last verification | VERIFIED |
| Restart / reload | Filled from disk cache, no download while fresh | `test_restart_uses_fresh_cache`, `test_reload_uses_fresh_cache` and `test_stale_cache_offline_start_still_loads` pass. The cache-start path (`_async_start_from_cache`) is unchanged | VERIFIED |
| Refreshed on the user's schedule | One request per daily slot or interval | `_set_regular_target(served)` and `_async_handle_failure(..., served)` use `refresh_base(now, served)`, and `served = self._next_refresh_at` is captured at `coordinator.py:163`, so this is equivalent to the 03-09 code. `test_daily_slot_served_once_when_timer_fires_early`, `test_daily_fast_failure_before_slot_backs_off_five_minutes`, both manual-refresh guards and `test_timer_cancelled_refresh_does_not_retry_every_second` pass | VERIFIED |
| Only when changed | 304 / identical body / unchanged file: no body, no parse | All `test_refresh.py` and `test_file_source.py` cases pass. A new condition applies: the kept data must still hold a programme ending after now - 1 day (WR-01) | VERIFIED (see human item 1 for the changed success semantics) |
| Tolerant of failures | Last good data kept; capped backoff; recorded | `test_failures_keep_last_good_data`, `test_unexpected_exception_backs_off_and_is_recorded` and `test_expired_unchanged_*` pass (`coordinator.data is previous`). WR-05: a poisoned cache now falls through to a download, confirmed by verifier repro | VERIFIED |
| Timezone quirks | Naive = local and/or offset correction | `test_timezone_options.py` and the parser tables pass. Unchanged | VERIFIED |
| Editable later | Options flow, single reload, no download | `test_options_flow.py` passes. Unchanged | VERIFIED |
| Visible when something goes wrong | Repairs after more than 24 h; diagnostics with last success | `test_persistent_failure_raises_and_clears_issue`, `test_unexpected_exception_raises_issue_after_24h`, `test_seeded_source_issue_names_setup_download` and `test_diagnostics_*` pass. A stalled provider (WR-01) is now reported as `empty_feed`, about 1 day after its last programme ends (IN-08). A cache-only parser crash that the download repairs is invisible (WR-06, advisory) | VERIFIED |
| Outcome | Calendars stay populated at minimal network and CPU cost | All four loop or blind-spot residuals from the previous report are closed or reduced. Two residuals remain for the prohibition judgment (human item 2) | VERIFIED, pending human items |

## Goal Achievement

### Roadmap Success Criteria (contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | Progress during the setup download. The options flow switches between interval and daily and edits timezone options. Source option saves reload; calendar edits do not | VERIFIED | `test_config_flow.py`, `test_options_flow.py` and `test_reconfigure.py` pass. Untouched by 19e262d |
| SC2 | Restart/reload uses a fresh cache. An unchanged feed is not re-downloaded or re-parsed. update_entity refreshes immediately | VERIFIED | `test_cache.py`, `test_refresh.py` (304, identical body, update_entity ×2) and `test_file_source.py` pass. The expired-data variants still skip the body and the parse (`parses.calls == 0`, `call_count == 1`) |
| SC3 | Naive timestamps read as local time and/or an offset correction | VERIFIED | `test_timezone_options.py` and the parser tables pass |
| SC4 | A failure keeps the last good data. A persistent failure raises a Repairs issue that clears on success | VERIFIED | Failure tests pass. The WR-01 fix keeps `data is previous` and `cache_meta == meta` |
| SC5 | Diagnostics with counts, last success/failure, redaction | VERIFIED | `test_diagnostics.py` and step 7 of the URL flow test pass |

### Re-verified areas changed by 19e262d (full three-level check)

| Change | Exists | Substantive | Wired / behaviour | Status |
|--------|--------|-------------|-------------------|--------|
| WR-04 provisional target | `served` and `max(served, utcnow() + BACKOFF_STEPS[0])` (`coordinator.py:163-166`) | Set before the first await. Success, failure and cache start each overwrite it | `test_timer_cancelled_refresh_does_not_retry_every_second`: 1 attempt over 10 s, retry at +5 min. The early-fire, fast-failure and manual guards pass, so CR-01 is intact | CLOSED |
| WR-05 poisoned cache | `except MemoryError: raise` / `except Exception` (`:325-330`) | Drops via the unchanged `async_drop` path; `MemoryError` keeps the payload | Verifier repro: parse order `['cache', 'download']`, LOADED, cache replaced with the changed body, 1 request. `test_unexpected_cache_parse_failure_downloads_and_is_recorded` and `test_cache_memory_error_preserves_offline_fallback` pass | CLOSED (WR-06 advisory) |
| WR-01 expiry check | `_require_programmes` with `stop >= utcnow() - KEEP_PAST` (`:446-447`) | Called on the 304 (`:367`), identical-body (`:388`) and unchanged-file (`:434`) paths, each before `async_touch` | `test_expired_unchanged_feed_fails_without_reparse[304, body]` and `test_expired_unchanged_file_fails_without_reparse` pass: `empty_feed`, data and meta kept, no parse | CLOSED (IN-08 info) |

### Plan Must-Have Truths

| Plan | Truths | Verified | Not verified | Notes |
|------|--------|----------|--------------|-------|
| 03-01 schedule engine | 11 | 11 | none | T1 still holds through `refresh_base(now, served)`. The prohibition is in human item 2 |
| 03-02 disk cache | 11 | 11 | none | T5 now holds without the earlier caveat: an unexpected exception also drops and re-downloads (repro). `MemoryError` keeps the cache (IN-10), which is not "no longer parses" |
| 03-03 conditional refresh | 8 | 6 | T1, T7 (UNCERTAIN) | Both still hold for current data (tests pass). For data with no programme ending after now - 1 day, a 304 or an unchanged file now counts as failure `empty_feed` (WR-01 fix), against the literal "counts as a successful refresh". Override requested |
| 03-04 failure health / Repairs / backoff | 11 | 10 | T5 (UNCERTAIN) | Same WR-01 reason: "a 304 answer and an unchanged local file count as success". T11 (backstop) is now VERIFIED by human UAT (03-UAT.md test 2) |
| 03-05 timezone options | 10 | 10 | none | T10 (backstop) is now VERIFIED by human UAT (03-UAT.md test 3) |
| 03-06 setup flow | 8 | 8 | none | Unchanged |
| 03-07 diagnostics | 6 | 6 | none | Unchanged |
| 03-08 options flow | 9 | 9 | none | UAT walkthrough recorded as passed (03-UAT.md test 1) |
| 03-09 gap closure CR-01/CR-02 | 10 (T11 = 03-04 T11) | 8 | T8, T9 (UNCERTAIN) | T8 says "recorded as a failure **without any download**". It now downloads once per attempt (`test_unexpected_cache_parse_failure_downloads_and_is_recorded` asserts `call_count == 1`); SETUP_RETRY, `unable_to_fetch` and `consecutive_failures 1` still hold. T9 says CancelledError "changes no refresh target". It now sets a provisional target of at least now + 5 min; `test_cancelled_refresh_records_no_failure` passes only because its target lies 23 h ahead. Override requested |
| 03-10 gap closure WR-02/WR-03 | 6 | 6 | none | Unchanged |

**Score:** 90/95 (5 roadmap SCs + 90 plan truths). Behavior-unverified: 0.

The 5 unverified truths are UNCERTAIN, not FAILED, for three reasons:

- In each case the observable deviation is a deliberate change. The previous verification recommended it as a fix for a flagged defect: WR-01 was a design gap, WR-04 a literal prohibition violation, WR-05 a residual.
- 03-UAT.md records that the user chose these fixes.
- The phase goal is better served by the new behaviour.

What is missing is only the override that lets the verifier carry them as PASSED. If the user rejects any of them, that truth becomes FAILED and a gap.

#### Suggested overrides (paste into this frontmatter if accepted)

```yaml
overrides:
  - must_have: "A later refresh of a URL source with a valid cache sends the stored ETag as If-None-Match and the stored Last-Modified as If-Modified-Since, verbatim; a 304 answer causes no download of the body, no parse and no calendar refilter, keeps coordinator.data as the identical object, counts as a successful refresh and updates the cache fetched_at (SRC-07)"
    reason: "WR-01 fix (19e262d): a 304 counts as success only while the data in memory still holds a programme ending after now - KEEP_PAST; otherwise it is an empty_feed failure without parse and without touching the cache, so a stalled provider becomes visible"
    accepted_by: "{name}"
    accepted_at: "{ISO timestamp}"
  - must_have: "A local file source is re-parsed only when the file's mtime or size changed; an unchanged file counts as a successful refresh, keeps the identical data object, and the allowed-path check still runs on every refresh; local files get no payload cache, and after a reload the file is parsed again (D-11)"
    reason: "WR-01 fix (19e262d): an unchanged file counts as success only while its data still holds a current programme; expired data fails with empty_feed and keeps the data object"
    accepted_by: "{name}"
    accepted_at: "{ISO timestamp}"
  - must_have: "The next successful refresh deletes the issue and resets the failure streak; a 304 answer and an unchanged local file count as success (D-17)"
    reason: "WR-01 fix (19e262d): a 304 or an unchanged file with expired data in memory is an empty_feed failure, not a success"
    accepted_by: "{name}"
    accepted_at: "{ISO timestamp}"
  - must_have: "A cached payload whose parse raises an unexpected exception at setup is recorded as a failure without any download: the entry is SETUP_RETRY with error_reason_translation_key unable_to_fetch and the stored health shows consecutive_failures 1, so setup retries count toward the 24 h issue (CR-02, D-09, D-17)"
    reason: "WR-05 fix (19e262d): the poisoned cache is dropped and the source downloaded (aligns with 03-02 truth 5); a persistent crash is still SETUP_RETRY, unable_to_fetch, consecutive_failures 1 per attempt; MemoryError keeps the cache without download"
    accepted_by: "{name}"
    accepted_at: "{ISO timestamp}"
  - must_have: "A refresh that ends in asyncio.CancelledError (entry unload, shutdown) records no failure and changes no refresh target: the failure handler catches Exception only, so cancellation passes through to Home Assistant unrecorded (edge SRC-08 interruption)"
    reason: "WR-04 fix (19e262d): cancellation stays unrecorded, but a provisional target max(served, now + 5 min) is set before the read, so an HA-swallowed cancellation can no longer re-arm a served target every second"
    accepted_by: "{name}"
    accepted_at: "{ISO timestamp}"
```

### Prohibitions (judgment tier, non-authoritative verdicts)

| Plan | Prohibition | Verdict |
|------|-------------|---------|
| 03-01 / 03-09 | MUST NOT contact the feed host more often than the schedule; no exception and no early timer turns into a faster retry | Holds for the early-firing timer, every `Exception` on a scheduled refresh, and an HA-swallowed CancelledError (the 1 s loop is gone). Two residuals: (a) a deterministic crash on cached and downloaded bytes downloads once per HA setup retry, up to 1 per 10 min (repro); (b) a recurring swallowed CancelledError retries every 5 min (IN-09). **unverified-prohibition: human review recommended** (human item 2) |
| 03-02 | No download at start, reload or options save while the cache is fresh | Holds. A cache that crashes the parser is unusable, not valid, so 03-02 T5 applies |
| 03-03 | No re-download or re-parse of unchanged feeds; validators kept on manual refresh | Holds. The expired-data variants also skip the body and the parse |
| 03-04 | Never blank or disable calendars while last good data exists | Holds. WR-01 failures keep `coordinator.data is previous`, and `available` is `data is not None` |
| 03-07 | No programme content or filter patterns in diagnostics | Holds (unchanged) |
| 03-10 | Never report a last success that did not happen | Holds (unchanged) |

### Required Artifacts

`verify.artifacts` passes for every plan: 03-01 6/6, 03-02 6/6, 03-03 6/6, 03-04 6/6, 03-05 4/4, 03-06 6/6, 03-07 3/3, 03-08 4/4, 03-09 5/5, 03-10 3/3.

| Artifact | Status | Details |
|----------|--------|---------|
| `coordinator.py` | VERIFIED | Provisional target, served-target base, poisoned-cache fall-through, expiry check on the unchanged shortcuts |
| `tests/test_schedule_refresh.py`, `tests/test_repairs.py`, `tests/test_refresh.py`, `tests/test_file_source.py` | VERIFIED | 6 new or renamed tests, all collected and passing |
| Remaining Phase 3 artifacts | VERIFIED (regression) | Unchanged since the previous verification; the suite is green |

### Key Link Verification

`verify.key-links`: 25/26. The failing link is 03-09 link 1, whose pattern `refresh_base\(now, self\._next_refresh_at\)` is stale. The link is still wired by manual check:

- `served = self._next_refresh_at` is captured at `coordinator.py:163`.
- `refresh_base(now, served)` is used at `:146` (`_set_regular_target`) and at `:211` (`_async_handle_failure`).
- Both results feed `next_regular(base, self._schedule())`.

The rename was needed: the WR-04 provisional target overwrites `_next_refresh_at` before the read, so the original value has to be passed explicitly. Status: WIRED (pattern needs updating in a later doc touch; not a gap).

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| Calendar entities | `coordinator.data` | Download then executor parse, or the cached payload | yes | FLOWING |
| Repairs issue | `SourceHealth` | `_async_record_failure`, now also for expired unchanged data (`empty_feed`) | yes | FLOWING |
| Diagnostics | health, cache_meta, stats | Live coordinator, or the Store for unloaded entries | yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite (run once) | `uv run pytest tests/ -q -rs -p no:cacheprovider` | 821 passed, 1 skipped (real-feed gate), 0 "Lingering", 50.9 s | PASS |
| Lint and format | `uv run ruff check . && uv run ruff format --check .` | Clean; 62 files formatted | PASS |
| Fix tests exist | `pytest --collect-only` grep | `test_expired_unchanged_feed_fails_without_reparse[×2]`, `test_expired_unchanged_file_fails_without_reparse`, `test_timer_cancelled_refresh_does_not_retry_every_second`, `test_cache_parser_crash_recovers_from_changed_download`, `test_cache_memory_error_preserves_offline_fallback`, `test_unexpected_cache_parse_failure_downloads_and_is_recorded` collected (passed in the full run) | PASS |
| WR-05 cache path really runs (IN-11 gap) | Scratchpad test: parse spy, poisoned cached bytes, changed download | Parse order `['cache', 'download']`, LOADED, 1 request, cache now holds the changed body, `consecutive_failures 0`, no WARNING | PASS (confirms WR-06) |
| WR-05 cost for a deterministic crash | Scratchpad test: parse always raises; 40 × 30 s steps | Request counts `[1,2,3,4,4,5,5,5,6,…,7,…,8]`: 8 downloads in 20 min, SETUP_RETRY, one content-free WARNING per attempt | As traced (human item 2) |

The repros ran from the session scratchpad. The repository was not modified: `git status` shows only the pre-existing `.planning/config.json` and `.planning/intel/`.

### Probe Execution

There are no `scripts/*/tests/probe-*.sh` files, and no plan declares a probe. Step 7c does not apply.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SRC-05 | 03-01, 03-06, 03-08, 03-09 | Daily fixed-time refresh | SATISFIED | Early-fire and manual guards pass after 19e262d |
| SRC-06 | 03-02 | Disk cache, no re-fetch while fresh | SATISFIED | `test_cache.py` |
| SRC-07 | 03-03 | Conditional re-download | SATISFIED | `test_refresh.py`, `test_file_source.py`. The success semantics for expired data are in human item 1 |
| SRC-08 | 03-04, 03-09 | Failed fetch/parse keeps last good data | SATISFIED | Failure tests; WR-01 and WR-05 tests keep the data |
| SRC-10 | 03-05, 03-06, 03-08 | Naive = local and/or offset correction | SATISFIED | `test_timezone_options.py` |
| SRC-11 | 03-04, 03-09 | Repairs on persistent failure, clears on success | SATISFIED | Repairs tests. A stalled feed is now also reported |
| SRC-12 | 03-07, 03-10 | Diagnostics with counts, last success/failure, redaction | SATISFIED | `test_diagnostics.py`, step 7 of the flow test |
| CFG-02 | 03-08 | Options flow for refresh and timezone | SATISFIED | `test_options_flow.py` |
| CFG-03 | 03-06, 03-10 | Progress during the setup download | SATISFIED | `progress_action == "download"`, single download; UAT passed |
| AUT-04 | 03-03 | Manual refresh via update_entity | SATISFIED | `test_update_entity_*`, manual-refresh guards |

All 10 IDs are claimed by at least one plan, and REQUIREMENTS.md maps no other ID to Phase 3, so none are orphaned. REQUIREMENTS.md still shows "Gaps Found" for these IDs (commit 21e69d6). They can go to Complete once the two human items are resolved.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `coordinator.py` | 328-333 | Catch-all logs at DEBUG only, with no class name or `exc_info`; duplicate drop line (WR-06) | Warning (advisory) | A latent parser bug triggered only by cached bytes vanishes without a trace; disposition open |
| `coordinator.py` | 163-166 | Fixed 5-min provisional retry on recurring swallowed cancellations (IN-09) | Info (advisory) | No escalation, no record |
| `coordinator.py` | 370-374 | 304 without data reads the cache without `valid_meta` (IN-04, carried) | Info | Needs a 304 to an unconditional request. With WR-05 a poisoned cache there now causes a second, unconditional request in the same refresh |
| `coordinator.py` | 446-447 | Expiry cut-off is `KEEP_PAST` (1 day), so a stalled feed is reported about a day late (IN-08) | Info | Docstring at `:441` still says "when it holds programmes" |
| tests | `test_repairs.py:400-430`, `test_schedule_refresh.py:399-400` | WR-05 tests don't prove the cache path ran (IN-11); exact frozen-clock equality (IN-12); duplicated raisers (IN-07) | Info | The verifier repro covers IN-11 |

The 5 files changed by 19e262d contain no TBD/FIXME/XXX/TODO/HACK markers. Re-verification evidence gate: WR-06 sits in a file modified since the prior `verified:` timestamp, but it is a Warning, not a Blocker, so nothing is promoted to a gap.

### Human Verification Required

1. **Override decision for 5 superseded truths.** The truths are 03-03 T1, 03-03 T7, 03-04 T5, 03-09 T8 and 03-09 T9. Their literal wording was overtaken by the WR-01, WR-04 and WR-05 fixes the user chose in 03-UAT.md. To accept, paste the suggested override block above into this frontmatter, with your name and a timestamp. To reject a truth, re-plan it as a gap.
2. **Prohibition verdict and WR-06 disposition.**
   - Confirm or defer the two residuals of the "no faster retry" prohibition:
     - A deterministic parser crash now downloads once per HA setup retry, up to 1 per 10 min.
     - A recurring swallowed CancelledError retries every 5 min.
   - Set WR-06 to fixed or deferred (with a reason) in 03-REVIEW-DISPOSITION.md.

The four UAT items in 03-UAT.md (walkthrough, debouncer serialization, options save during a parse, WR dispositions) were recorded before 19e262d. The fix commit does not touch the setup flow, the reload, HA's debouncer lock or the normal-path refresh logic, and those paths are covered by passing tests, so the UAT results carry forward.

### Gaps Summary

There are no gaps. Commit 19e262d did what 03-FIX-VERIFICATION.md claims, and the verifier confirmed each fix independently:

- **WR-04:** the 1 s retry loop on a swallowed cancellation is gone.
- **WR-05:** a poisoned cache is dropped and re-downloaded (scratchpad repro); `MemoryError` keeps the offline fallback.
- **WR-01:** a stalled feed is now reported as `empty_feed` without a re-parse.

There are no regressions: 821 tests pass, Ruff is clean, and all 10 plans pass the artifact check. The one failing key-link pattern is a stale rename, still wired.

The phase goal is achieved. The status is `human_needed`, not `passed`, for two reasons:

- Five planned truths now read differently from the code, by the user's own choice. Only the user can accept that with an override.
- The judgment-tier network-cost prohibition has two residual paths that need a recorded decision. WR-06 also needs a disposition.

---

_Verified: 2026-10-20T23:12:14Z_
_Verifier: Claude (gsd-verifier)_
