---
phase: 03-resilient-sources
verified: 2026-10-16T11:49:08Z
status: gaps_found
score: 70/79 must-haves verified
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
covered_digest: "v3:sha256:abfaf90245c65c7d38b2d9f6cd67087df01ba1ea97e1ece1b908db7bf36f21d8"
behavior_unverified: 2
overrides_applied: 0
gaps:
  - truth: "A daily source refreshes at its slot (e.g. 18:15 Europe/Berlin), again at the next day's slot, and not before the slot; it contacts the feed host once per slot (03-01 truth 1 + 03-01 prohibition)"
    status: failed
    reason: "CR-01. HA arms the timer at int(loop.time()) + _microsecond + interval (homeassistant/helpers/update_coordinator.py:283), so it fires up to ~0.95 s before _next_refresh_at. _set_regular_target() then computes next_slot(utcnow()), which returns the same slot that is less than 1 s away; _schedule_refresh clamps it to MIN_DELAY and the source is requested a second time one second later. Reproduced by the verifier: a refresh at 16:14:59.4Z leaves next_refresh_at = 16:15:00Z, and the slot then causes a third request (call_count 1 -> 2 -> 3). On a fast failure the same effect produces backoff MIN_DELAY, a second failure within 1 s, and skips the 5-minute backoff step."
    artifacts:
      - path: "custom_components/xmltv_calendar/coordinator.py"
        issue: "_set_regular_target (line 141-142) and the failure path (line 170) derive the next target from the slightly early utcnow() instead of the served target"
      - path: "tests/test_schedule_refresh.py"
        issue: "Every step lands 1 s after the target, so the early-fire case is never exercised"
    missing:
      - "Derive the next regular target from max(utcnow(), served _next_refresh_at), in both the success path and the backoff computation"
      - "Regression test: step to slot - <1 s (or call async_refresh just before the slot) and assert exactly one request for that slot"
  - truth: "After a failed refresh the next attempt backs off (5 min, 15 min, 1 h, 3 h, 6 h ...), the failure is recorded in the source health, and a source failing for more than 24 h raises a Repairs issue (03-04 truths 3 and 8, roadmap SC 4, 03-01 prohibition)"
    status: failed
    reason: "CR-02. _async_update_data only handles UpdateFailed (coordinator.py:163-171). Any other exception (MemoryError while parsing a large feed, a latent bug; the parser documents that other exceptions propagate unchanged) reaches HA's generic handler, which re-arms the timer via _schedule_refresh; _next_refresh_at still holds the target just served, so update_interval = MIN_DELAY. Reproduced by the verifier: parse patched to raise RuntimeError on a scheduled refresh caused 6 downloads in ~10 s, consecutive_failures stayed 0, no failing_since, so no backoff and never a Repairs issue, plus a traceback every second."
    artifacts:
      - path: "custom_components/xmltv_calendar/coordinator.py"
        issue: "except UpdateFailed only; unexpected exceptions skip _async_record_failure and the backoff target"
    missing:
      - "Catch Exception (not CancelledError) around the fetch/parse, record the failure with reason unable_to_fetch, set the backoff target, and re-raise as UpdateFailed"
      - "Regression test: patch parse to raise a non-FeedError exception on a scheduled refresh and assert one request, consecutive_failures == 1 and next_refresh_at == now + 5 min"
  - truth: "Diagnostics (and the Repairs issue text) show the last successful refresh (03-07 truth 3, roadmap SC 5)"
    status: partial
    reason: "WR-02. A source created through the setup flow starts from the flow-seeded cache via _async_start_from_cache, which never calls _async_record_success, and _async_seed_cache writes only CacheMeta. health.last_success stays None until the first scheduled refresh (up to 168 h or a day later): diagnostics show last_success null for a working source, and a failure streak that starts at the first scheduled refresh produces a Repairs issue saying 'Last successful refresh: -'. This is the normal user path, not an edge case."
    artifacts:
      - path: "custom_components/xmltv_calendar/coordinator.py"
        issue: "_async_start_from_cache (229-252) returns cached data without recording meta.fetched_at as a success when health.last_success is None or older"
      - path: "custom_components/xmltv_calendar/config_flow.py"
        issue: "_async_seed_cache (344-361) seeds payload and metadata but no SourceHealth"
    missing:
      - "Record the seeded fetch as a success (seed SourceHealth(last_success=fetched_at), or adopt meta.fetched_at in _async_start_from_cache when it is newer than health.last_success)"
      - "Assert health.last_success / diagnostics last_success in test_url_source_end_to_end_with_progress_and_seeded_cache"
  - truth: "The suite no longer depends on the wall clock: test modules that use the 2026-10-13 fixtures run frozen (03-01 truth 11)"
    status: partial
    reason: "WR-03. tests/test_identity.py loads fixtures/basic.xml (2026-10-13 programmes) and has no freeze_time or freezer usage. On 2026-10-16 the parser drops every programme, setup fails with empty_feed and the entry sits in SETUP_RETRY; the tests still pass because they only assert on flow results, so they no longer exercise a loaded source."
    artifacts:
      - path: "tests/test_identity.py"
        issue: "No pytestmark freeze_time; no assertion on entry.state"
    missing:
      - "pytestmark = pytest.mark.freeze_time('2026-10-13T06:00:00+00:00') and an assertion that the created entry is LOADED"
behavior_unverified_items:
  - truth: "A manual update_entity that arrives while a scheduled refresh runs is serialized by the coordinator's debouncer lock, so health and cache are never written by two refreshes at once (03-04, verification: backstop)"
    test: "Start a scheduled refresh against a slow feed and fire homeassistant.update_entity on the calendar while the download is running"
    expected: "The two refreshes run one after the other; the Store holds one consistent CacheMeta/SourceHealth and consecutive_failures changes by at most 1 per refresh"
    why_human: "Backstop truth relying on HA's debouncer; no test in tests/ exercises concurrent refreshes, and presence/wiring cannot prove serialization"
  - truth: "An options save during a running parse cannot mix old and new timezone settings: the reload replaces the coordinator and the old result is discarded (03-05, verification: backstop)"
    test: "Change the timezone option in the options flow while a large-feed parse is running"
    expected: "After the reload the events reflect only the new timezone options; nothing from the old coordinator's parse is shown"
    why_human: "Backstop truth; no test exercises an options save during an in-flight parse"
---

# Phase 3: Resilient Sources Verification Report

**Phase Goal:** Sources keep every calendar populated at minimal network and CPU cost: cached across restarts, refreshed on the user's schedule and only when changed, tolerant of failures and timezone quirks, editable later, and visible to the user when something goes wrong.
**Mode:** mvp. The user story in the PLAN files is valid per `user-story.validate`.
**Verified:** 2026-10-16T11:49:08Z
**Status:** gaps_found
**Re-verification:** No, initial verification

## User Flow Coverage

User story: "As a Home Assistant user with XMLTV sources, I want to have each source cached across restarts, refreshed on my own schedule and only when the feed changed, tolerant of failures and timezone quirks, editable later, and visible when something goes wrong, so that every calendar stays populated at minimal network and CPU cost."

| Step | Expected | Evidence | Status |
|------|----------|----------|--------|
| Add a URL source | Progress dialog during download, schedule step, collapsed timezone section, exactly one HTTP request | `config_flow.py` async_show_progress plus seed; `test_url_source_end_to_end_with_progress_and_seeded_cache` (call_count 1, 4 events) | VERIFIED (automated); visual check in UAT |
| Restart / reload | Calendars filled from disk cache, no download while fresh | `coordinator._async_start_from_cache`; `test_restart_uses_fresh_cache`, `test_reload_uses_fresh_cache`, `test_stale_cache_offline_start_still_loads` | VERIFIED |
| Refreshed on the user's schedule | Interval or once daily at the slot, once per slot | `test_daily_slot_refreshes_at_local_time` passes, but HA's timer fires up to ~0.95 s early and a second request follows (CR-01, reproduced) | FAILED |
| Only when changed | 304 / identical body / unchanged file: no download and no parse | `test_unchanged_feed_answers_304_without_reparse`, `test_identical_body_is_not_reparsed`, `test_unchanged_file_is_not_reparsed` | VERIFIED |
| Tolerant of failures | Last good data kept; capped backoff; no hammering | Last good data verified (`test_failures_keep_last_good_data`). Backoff only for UpdateFailed: an unexpected exception re-downloads every ~1 s (CR-02, reproduced) | FAILED |
| Timezone quirks | Naive = local and/or offset correction shift the events | `test_naive_local_timestamps_end_to_end`, `test_offset_correction_shifts_events`, `test_timezone_option_change_reparses_cache_without_download` | VERIFIED |
| Editable later | Options flow: interval/daily plus timezone; reload once, no download | `XmltvOptionsFlow`; `test_options_flow_switch_to_daily`, `test_identical_options_do_not_reload` | VERIFIED |
| Visible when something goes wrong | Repairs issue after >24 h of failures; diagnostics with last success/failure | Verified for UpdateFailed failures. Never raised for unexpected exceptions (CR-02); last_success is null after flow setup (WR-02); a feed that stops updating is never reported (WR-01, advisory) | PARTIAL |
| Outcome | Every calendar stays populated at minimal network and CPU cost | Calendars stay populated. "Minimal network cost" is violated by CR-01 (two requests per daily slot) and CR-02 (1 request/s indefinitely) | FAILED |

## Goal Achievement

### Roadmap Success Criteria (contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | Progress during setup download; options flow switches interval/daily and edits timezone; source options reload the source, calendar edits do not | VERIFIED | `config_flow.py` (`async_show_progress`, `XmltvOptionsFlow(OptionsFlow)`), `__init__._async_entry_updated` diff on (data, options); tests `test_url_source_end_to_end_with_progress_and_seeded_cache`, `test_options_flow_switch_to_daily`, `test_identical_options_do_not_reload`, reconfigure tests pass |
| SC2 | Restart/reload uses fresh disk cache; unchanged feed not re-downloaded or re-parsed; update_entity refreshes immediately | VERIFIED | `cache.py` FeedCache, `coordinator._async_update_url` 304/identical-body branches; `test_restart_uses_fresh_cache`, `test_unchanged_feed_answers_304_without_reparse`, `test_update_entity_refreshes_now_with_validators` (validators sent, 0 parses) |
| SC3 | Naive timestamps as local time and/or offset correction shift events | VERIFIED | `timeparse.parse_xmltv_time(naive_tz)`, `parser.parse(shift=)`, `coordinator._parser()`; `test_timezone_options.py` (6 tests) |
| SC4 | Fetch/parse failure keeps last good data; persistently failing source raises a Repairs issue that clears on success | FAILED (partial) | Last good data and the issue lifecycle work for UpdateFailed (`test_failures_keep_last_good_data`, `test_persistent_failure_raises_and_clears_issue`). An unexpected exception is never recorded, so the issue never appears and the source is re-downloaded every ~1 s (CR-02, reproduced) |
| SC5 | Diagnostics with programme/channel/match counts and last success/failure, URL and credentials redacted | FAILED (partial) | Counts and redaction verified (`test_diagnostics_end_to_end`). last_success is null for every flow-created source until its first scheduled refresh (WR-02) |

### Plan Must-Have Truths

| Plan | Truths | Verified | Failed / unverified | Notes |
|------|--------|----------|---------------------|-------|
| 03-01 schedule engine | 11 | 9 | T1 FAILED (CR-01), T11 partial (WR-03) | Pure maths verified by `tests/xmltv/test_schedule.py` (slots, DST gap/fold, freshness, backoff table, 24 h test, options contract and idempotency). `_schedule_refresh` never yields a zero interval (`max(..., MIN_DELAY)`) |
| 03-02 disk cache | 11 | 11 | none | 17 tests in `test_cache.py`: restart/reload, source-id and size validation, atomic write, poisoned cache dropped, stale-while-revalidate, offline start, removal, 0o600, no URL in Store, validator cleaning |
| 03-03 conditional refresh | 8 | 8 | none | `test_refresh.py` (9) and `test_file_source.py` (6); calendar identity guard at `calendar.py:139` |
| 03-04 failure health / Repairs / backoff | 11 | 8 | T3 and T8 FAILED (CR-02); T11 backstop unverified | UpdateFailed path fully tested (`test_repairs.py`, `test_empty_feed.py`, `test_failure_backoff_steps`). Non-UpdateFailed exceptions bypass health, backoff and Repairs |
| 03-05 timezone options | 10 | 9 | T10 backstop unverified | Parser tables plus end-to-end tests; reload re-parses the cache without a download |
| 03-06 setup flow with progress | 8 | 8 | none | Progress, seeding (1 request total), schedule step, flat timezone storage, error mapping, abandoned download writes no cache, duplicate aborts before download |
| 03-07 diagnostics | 6 | 5 | T3 partial (WR-02) | Redaction, allow-list, no-refresh, not-loaded entry verified |
| 03-08 options flow | 9 | 9 | none | The UAT part of T9 is queued (see Human Verification) |

**Score:** 70/79 truths verified (5 roadmap SCs + 74 plan truths). Of the 9 not verified, 7 are failed or partial and 2 are backstop truths without behavioral evidence.

### Prohibitions

| Plan | Prohibition | Tier | Verdict |
|------|-------------|------|---------|
| 03-01 | MUST NOT contact the feed host more often than the user's schedule | judgment | VIOLATED, with deterministic evidence: CR-01 (2 requests per daily slot) and CR-02 (1 request/s on unexpected exceptions) |
| 03-02 | MUST NOT download at start-up/reload/options save while a valid cache is fresh | judgment | Holds (non-authoritative LLM verdict): `test_restart_uses_fresh_cache`, `test_reload_uses_fresh_cache`, options-flow tests assert call_count unchanged |
| 03-03 | MUST NOT re-download/re-parse unchanged feeds or drop validators on manual refresh | judgment | Holds (non-authoritative): 304 and identical-body tests count 0 parses, update_entity sends If-None-Match |
| 03-04 | MUST NOT blank or disable calendars while last good data exists | judgment | Holds (non-authoritative): `available` = `data is not None`, data reassigned only on success, HA's generic exception path also keeps data |
| 03-07 | MUST NOT put programme content or filter patterns into diagnostics | judgment | Holds (non-authoritative): allow-listed output, test asserts "Tagesschau" is absent |

### Required Artifacts

`verify.artifacts`: all plans pass (03-01 6/6, 03-02 6/6, 03-03 6/6, 03-04 6/6, 03-05 4/4, 03-06 6/6, 03-07 3/3, 03-08 4/4).

| Artifact | Status | Details |
|----------|--------|---------|
| `xmltv/schedule.py` | VERIFIED | Pure, stdlib only; SourceOptions, slots, freshness, backoff |
| `cache.py` | VERIFIED | FeedCache, CacheMeta and SourceHealth in one Store; atomic payload write |
| `coordinator.py` | VERIFIED (with defects CR-01/CR-02) | Wired to cache, schedule, source and issue registry |
| `config_flow.py` | VERIFIED | Progress, shared schema builders, seeding, `XmltvOptionsFlow(OptionsFlow)` |
| `diagnostics.py` | VERIFIED | `async_redact_data` with URL/path redactors and TO_REDACT |
| `translations/en.json`, `de.json` | VERIFIED | Key sets identical; six `source_failing_*` issues, progress and options sections |
| `__init__.py` | VERIFIED | `async_remove_entry` deletes cache and issue |
| `calendar.py` | VERIFIED | `available`, identity guard, `match_count` |

### Key Link Verification

`verify.key-links`: all links verified (22/22 across 8 plans). Spot-checked manually: `coordinator.py:170` backoff_delay plus next_regular, `coordinator.py:218` `ir.async_create_issue(translation_key=f"source_failing_{reason}")`, `__init__.py:64` `ir.async_delete_issue`, `diagnostics.py:103` `async_redact_data`, `config_flow.py:353` `FeedCache(...)` seeding.

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| Calendar entities | `coordinator.data` (EpgData) | download -> executor parse, or cached payload -> parse | yes | FLOWING |
| Repairs issue | `SourceHealth` | `_async_record_failure` / `_async_record_success` persisted in Store | yes for UpdateFailed; never for other exceptions | PARTIAL (CR-02) |
| Diagnostics | health, cache_meta, stats, match counts | live coordinator or Store for unloaded entries | yes; last_success missing after flow-seeded setup | PARTIAL (WR-02) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite (run once) | `uv run pytest tests/ -q -rA` | 798 passed, 1 skipped (real-feed check deferred), 49.9 s | PASS |
| Lint/format | `uv run ruff check . && uv run ruff format --check .` | All checks passed; 62 files already formatted | PASS |
| CR-01 repro (throwaway test, deleted afterwards) | refresh at 16:14:59.4Z for daily 18:15 Berlin, then step to 16:15:01Z | next_refresh_at stayed 16:15:00Z; call_count 1 -> 2 -> 3 | FAIL |
| CR-02 repro (throwaway test, deleted afterwards) | parse raises RuntimeError on a scheduled refresh, step 10 s | 6 downloads in ~10 s, consecutive_failures 0 | FAIL |
| HA timer arithmetic | read `homeassistant/helpers/update_coordinator.py:283` | `next_refresh = int(loop.time()) + self._microsecond + update_interval`: up to ~0.95 s early | confirms CR-01 premise |

### Probe Execution

No `scripts/*/tests/probe-*.sh` exist and no plan declares a probe. Step 7c: not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SRC-05 | 03-01, 03-06, 03-08 | Refresh once daily at a fixed time | BLOCKED (partial) | Configurable and scheduled, but a daily slot is requested twice (CR-01) |
| SRC-06 | 03-02 | Disk cache, no re-fetch while fresh | SATISFIED | `test_cache.py` |
| SRC-07 | 03-03 | Re-download only when changed | SATISFIED | `test_refresh.py`, `test_file_source.py` |
| SRC-08 | 03-04 | Failed fetch/parse keeps last good data | SATISFIED (data kept); the backoff side of tolerance fails, see SRC-11/CR-02 | `test_failures_keep_last_good_data`, `test_later_empty_feed_keeps_last_good_data` |
| SRC-10 | 03-05, 03-06, 03-08 | Naive = local and/or offset correction | SATISFIED | `test_timezone_options.py`, parser tables |
| SRC-11 | 03-04 | Repairs issue on persistent failure, clears on success | BLOCKED (partial) | Works for UpdateFailed; never raised for unexpected exceptions (CR-02) |
| SRC-12 | 03-07 | Diagnostics with counts, last success/failure, redaction | PARTIAL | last_success null after flow setup (WR-02) |
| CFG-02 | 03-08 | Options flow for refresh and timezone | SATISFIED | `test_options_flow.py` (8 tests) |
| CFG-03 | 03-06 | Progress indicator during setup download | SATISFIED (automated); visual check in UAT | `progress_action == "download"` |
| AUT-04 | 03-03 | Manual refresh via update_entity | SATISFIED | `test_update_entity_refreshes_now_with_validators`, `test_update_entity_on_any_calendar_refreshes_the_source` |

All 10 phase requirement IDs are claimed by at least one plan. REQUIREMENTS.md maps no other ID to Phase 3, so none are orphaned. REQUIREMENTS.md already marks all 10 `[x] Complete`; SRC-05, SRC-11 and SRC-12 are overstated until the gaps close.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `coordinator.py` | 141-142, 170 | Next target derived from early-firing `utcnow()` | Blocker (CR-01) | Double request per daily slot; backoff step skipped on fast failures |
| `coordinator.py` | 163-171 | `except UpdateFailed` only | Blocker (CR-02) | 1 request/s indefinitely, no health record, no Repairs |
| `coordinator.py` | 229-252 / `config_flow.py` 344-361 | Seeded cache start never records success | Warning (WR-02) | Diagnostics/Repairs show no last success for a working source |
| `coordinator.py` | 323-326, 337-346, 388-390 | "Unchanged" shortcuts skip the current-programme check | Warning (WR-01) | A provider that stops updating (304 forever, frozen file) is never reported; calendars silently run dry. The plans define 304 as success, so this is outside the must-haves, but it works against "visible when something goes wrong" |
| `tests/test_identity.py` | 52-121 | Unfrozen test with expired fixtures | Warning (WR-03) | Tests a SETUP_RETRY entry |
| Info | | IN-01..IN-05 from 03-REVIEW.md | Info | Not goal-blocking |

No TBD/FIXME/XXX/TODO markers in the 35 files changed since `bfcd455`.

### Human Verification Required

These items are queued for the end-of-phase UAT batch (03-08 `<human-check>`). They do not change the gaps_found status.

1. **ha-dev walkthrough (03-08 human-check, 12 steps).** Collapsed timezone section and progress dialog; one download per setup; no download on restart or options save; update_entity sends validators against the real feed; `curl -sI` shows whether ETag/Last-Modified exist; diagnostics redaction; German texts; no tracebacks or blocking-call warnings.
2. **Debouncer serialization (03-04, backstop).** Fire update_entity during a running scheduled refresh. Expected: the two refreshes run one after the other, with consistent health and cache.
3. **Options save during a running parse (03-05, backstop).** Expected: only the new timezone options show after the reload.

### Gaps Summary

The phase delivers most of its goal. Cache, conditional GET, timezone options, options flow, setup progress, last-good data and diagnostics all exist, are wired, and are covered by substantive tests (798 green). Two scheduling and failure-handling defects in `coordinator.py` contradict the core of the goal, "minimal network cost" and "tolerant of failures". The verifier reproduced both independently:

- **CR-01:** every daily source can hit the feed host twice per slot, because HA's timer fires slightly early and the next target is computed from that early `now`.
- **CR-02:** any non-`UpdateFailed` exception turns the coordinator into a once-per-second download loop. It records no failure, never backs off and never raises a Repairs issue.

Both have the same root cause: the refresh target is updated only on the anticipated paths. They can be fixed together in `_async_update_data` / `_set_regular_target` with two regression tests. WR-02 (record the flow-seeded fetch as a success) and WR-03 (freeze `test_identity.py`) are small. WR-01 is advisory but worth a decision, because a stalled provider is the most likely real-world "something goes wrong".

No gap is deferred: Phase 4 (Automation Extras & Release) does not cover scheduling or failure handling.

---

_Verified: 2026-10-16T11:49:08Z_
_Verifier: Claude (gsd-verifier)_
