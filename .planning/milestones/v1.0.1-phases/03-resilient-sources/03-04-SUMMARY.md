---
phase: 03-resilient-sources
plan: 04
subsystem: coordinator
tags: [repairs, issue_registry, backoff, health, empty-feed, translations]

requires:
  - phase: 03-01
    provides: schedule.backoff_delay, is_persistently_failing, next_regular, coordinator _next_refresh_at
  - phase: 03-02
    provides: FeedCache (Store + payload), cache-first start, async_remove_entry cache cleanup
  - phase: 03-03
    provides: NotModified/identical-body/unchanged-file success paths returning the identical EpgData
provides:
  - SourceHealth (last_success, failing_since, last_failure_at, last_failure_reason, consecutive_failures) persisted next to CacheMeta in the same Store
  - Coordinator success/failure recording, Repairs issue source_failing_<entry_id> after > 24 h of failures, cleared on next success
  - Capped failure backoff target (5 min, 15 min, 1 h, 3 h, 6 h ..., capped by the next regular refresh)
  - Issue re-raised at setup from the cache; setup retries count toward the 24 h
  - empty_feed failure for feeds without current programmes (D-20)
  - coordinator.health property and issue_id() helper for diagnostics (03-07)
affects: [03-05, 03-06, 03-07, 03-08, diagnostics]

actuals:
  tokens: 12797      # chars/4 over the code + test diff (51188 chars); with the committed RED evidence ~35172 (140686 chars)
  tasks: 3
  commits: 6
plan_head_before: b585a2aab9835faeb59bcfd32da0e662c9c99cf8
plan_head_after: 3e1858c5137632c1c34293c680d06a79795560ea

tech-stack:
  added: []
  patterns:
    - "Every coordinator outcome is recorded: success -> _async_record_success (clears issue), UpdateFailed -> _async_record_failure (may raise issue) and is re-raised unchanged"
    - "SourceHealth is a frozen slotted dataclass replaced on each outcome; tolerant from_dict gives the healthy default for malformed Store data"
    - "Repairs issue reason restricted to FAILURE_REASONS; unknown reasons map to unable_to_fetch"

key-files:
  created:
    - tests/test_repairs.py
    - tests/test_empty_feed.py
    - .planning/phases/03-resilient-sources/tdd-evidence/03-04-red.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-04-red-2-backoff.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-04-red-2-restart.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-04-red-2-remove.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-04-red-3.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-04-red-3-later.json
  modified:
    - custom_components/xmltv_calendar/cache.py
    - custom_components/xmltv_calendar/coordinator.py
    - custom_components/xmltv_calendar/__init__.py
    - custom_components/xmltv_calendar/translations/en.json
    - custom_components/xmltv_calendar/translations/de.json
    - tests/test_schedule_refresh.py
    - tests/test_calendar.py
    - tests/test_subentry_flow.py
    - tests/test_cache.py

key-decisions:
  - "03-04: SourceHealth lives in the cache Store as {meta, health}, for file sources too; success keeps last_failure_at/reason for diagnostics and resets failing_since and consecutive_failures"
  - "03-04: Repairs issue source_failing_<entry_id>, is_fixable False, is_persistent False, severity WARNING, translation_key source_failing_<reason>, placeholders source (entry title) and last_success (local 'YYYY-MM-DD HH:MM' or '-')"
  - "03-04: failure reasons limited to FAILURE_REASONS (unable_to_fetch, invalid_feed, feed_too_large, path_not_allowed, file_not_found, empty_feed); stored reasons must match [a-z_]{1,64}, unknown ones become unable_to_fetch"
  - "03-04: failure target = now + backoff_delay(consecutive_failures, now, next_regular(now, schedule)); success target = next_regular"
  - "03-04: a stale-cache start still refreshes about 1 s after the first listener even while failing; the failure count continues from the Store"
  - "03-04: empty_feed is raised after parse and before any cache write or file signature update, for URL and file sources"

patterns-established:
  - "Health-recording wrapper: _async_update_data catches UpdateFailed only to record it, then re-raises unchanged (HA logs once per streak)"
  - "Repairs placeholders carry only the entry title and a formatted time; reasons are fixed translation keys"

requirements-completed: [SRC-08, SRC-11]

coverage:
  - id: D1
    description: "A source failing more than 24 h after the first failure of its streak raises one not-fixable warning Repairs issue with source, last success and reason; the next success clears it"
    requirement: SRC-11
    verification:
      - kind: integration
        ref: "tests/test_repairs.py#test_persistent_failure_raises_and_clears_issue"
        status: pass
      - kind: integration
        ref: "tests/test_repairs.py#test_issue_follows_the_latest_reason"
        status: pass
      - kind: integration
        ref: "tests/test_repairs.py#test_daily_first_failure_after_24h_raises_no_issue"
        status: pass
      - kind: integration
        ref: "tests/test_repairs.py#test_not_modified_and_unchanged_file_count_as_success"
        status: pass
    human_judgment: false
  - id: D2
    description: "Issue texts and placeholders never contain the URL or credentials (en and de rendered)"
    requirement: SRC-11
    verification:
      - kind: integration
        ref: "tests/test_repairs.py#test_issue_text_has_no_url"
        status: pass
      - kind: unit
        ref: "tests/test_translations.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Failure state survives restarts and setup retries; the issue is re-raised at setup before any request; removing the entry deletes the issue"
    requirement: SRC-11
    verification:
      - kind: integration
        ref: "tests/test_repairs.py#test_failing_since_survives_restart"
        status: pass
      - kind: integration
        ref: "tests/test_repairs.py#test_setup_retries_count_toward_the_issue"
        status: pass
      - kind: integration
        ref: "tests/test_repairs.py#test_remove_entry_deletes_issue"
        status: pass
    human_judgment: false
  - id: D4
    description: "Capped backoff after failures: 5 min, 15 min, 1 h, 3 h, 6 h, 6 h, never past the interval or next daily slot; success returns to the regular schedule"
    verification:
      - kind: integration
        ref: "tests/test_schedule_refresh.py#test_failure_backoff_steps"
        status: pass
      - kind: integration
        ref: "tests/test_schedule_refresh.py#test_backoff_capped_by_interval"
        status: pass
      - kind: integration
        ref: "tests/test_schedule_refresh.py#test_backoff_capped_by_next_daily_slot"
        status: pass
    human_judgment: false
  - id: D5
    description: "During failures calendars stay available with the identical last good data, keep get_events and turn on at a cached programme's start"
    requirement: SRC-08
    verification:
      - kind: integration
        ref: "tests/test_repairs.py#test_failures_keep_last_good_data"
        status: pass
      - kind: integration
        ref: "tests/test_ingestion.py#test_refresh_with_truncated_gzip_keeps_previous_data"
        status: pass
    human_judgment: false
  - id: D6
    description: "A feed without current programmes is a failure (empty_feed): first setup retries, later refreshes keep data and cache; fewer programmes are accepted"
    requirement: SRC-08
    verification:
      - kind: integration
        ref: "tests/test_empty_feed.py#test_first_setup_with_empty_feed_retries"
        status: pass
      - kind: integration
        ref: "tests/test_empty_feed.py#test_feed_with_only_past_programmes_retries"
        status: pass
      - kind: integration
        ref: "tests/test_empty_feed.py#test_later_empty_feed_keeps_last_good_data"
        status: pass
      - kind: integration
        ref: "tests/test_empty_feed.py#test_fewer_programmes_are_accepted"
        status: pass
    human_judgment: false
  - id: D7
    description: "German issue wording reads naturally in the Repairs UI"
    verification: []
    human_judgment: true
    rationale: "Translation quality and how the issue looks in the Repairs dashboard are not asserted by tests (parity, placeholders and literals are)"

duration: 9min
completed: 2026-10-16
status: complete
---

# Phase 3 Plan 04: Failure Health, Repairs and Backoff Summary

**Persisted SourceHealth drives a per-source Repairs issue after more than 24 h of failures (per-reason en/de texts, no URL), a 5 min to 6 h capped retry backoff, and an empty_feed failure that never wipes the last good data**

## Performance

- **Duration:** 9 min
- **Started:** 2026-10-16T10:39:49Z
- **Completed:** 2026-10-16T10:48:33Z
- **Tasks:** 3
- **Files modified:** 11 source/test files, plus 9 RED evidence files

## Accomplishments

- Every refresh outcome is recorded in `SourceHealth`, which is persisted next to the cache metadata (`{"meta": ..., "health": ...}`).
  - A success (also a 304, an identical body or an unchanged file) ends the streak and deletes the issue.
  - A failure extends the streak. Once a failure comes more than 24 h after `failing_since`, it raises `source_failing_<entry_id>`.
- The issue is not fixable, has severity warning and uses translation key `source_failing_<reason>`.
  - Placeholders: `source` (entry title) and `last_success` (local time, `-` if the source never succeeded).
  - Six reasons are translated in en and de.
- Failed refreshes retry after 5 min, 15 min, 1 h, 3 h, 6 h, 6 h ..., never later than the next regular refresh. A success returns to the regular schedule.
- The failure state survives restarts and setup retries:
  - A cache start re-raises the issue before any request.
  - A failed first setup without cache is recorded.
  - Removing the entry deletes the issue.
- A feed that parses to 0 current programmes fails with `empty_feed`:
  - The data and cache stay.
  - A first setup without cache ends in SETUP_RETRY.
  - A smaller non-empty feed is accepted.

## Task Commits

1. **Task 1: Tracer: Repairs issue after more than 24 h, cleared on success**
   - RED `a9c7261` (test)
   - GREEN `064d8c7` (feat)
   - Tracer gate: verify re-run passed (19 passed), expanded.
2. **Task 2: Capped backoff, failure state across restarts, calendars keep working**
   - RED `0472a92` (test)
   - GREEN `822809f` (feat)
3. **Task 3: Empty feed is a failure**
   - RED `b0d5b55` (test)
   - GREEN `3e1858c` (feat)

No REFACTOR commits were needed.

## TDD Gate Compliance

| Gate | Task 1 | Task 2 | Task 3 |
|------|--------|--------|--------|
| RED commit before GREEN | `a9c7261` before `064d8c7` | `0472a92` before `822809f` | `b0d5b55` before `3e1858c` |
| RED classifier | `03-04-red.json`: RED_EVIDENCE_OK (target_test_failed) | `03-04-red-2-backoff.json`, `-restart.json`, `-remove.json`: all RED_EVIDENCE_OK | `03-04-red-3.json`, `03-04-red-3-later.json`: both RED_EVIDENCE_OK |

**RED semantic assessments:**

- **`test_persistent_failure_raises_and_clears_issue`:** The test failed on the planned assertion that the issue exists at NOW + 25 h + 1 s (`assert None is not None`, line 67). The two earlier "no issue" assertions passed. The cause was the missing health tracking.
- **`test_failure_backoff_steps`:** The test failed on the first backoff assertion: `next_refresh_at` was the regular 24 h target instead of +5 min.
- **`test_failing_since_survives_restart`:** The entry was LOADED from the stale cache with 0 requests. The test then failed on the planned assertion that the issue exists right after setup.
- **`test_remove_entry_deletes_issue`:** The issue was still present after `async_remove`.
- **`test_first_setup_with_empty_feed_retries`:** The entry state was LOADED instead of SETUP_RETRY.
- **`test_later_empty_feed_keeps_last_good_data`:** `last_update_success` was still True after the empty refresh.

**Tests already green at RED time (regression guards):**

- `test_backoff_capped_by_interval`: with a 2 h interval the regular target already equals the cap.
- `test_setup_retries_count_toward_the_issue`, `test_daily_first_failure_after_24h_raises_no_issue` and `test_not_modified_and_unchanged_file_count_as_success[url-304|file-unchanged]`: Task 1's recording already covered these.
- `test_fewer_programmes_are_accepted`.

**RED for the planned reason, but without a separate record:**

- `test_issue_follows_the_latest_reason` and `test_issue_text_has_no_url`: no issue existed yet.
- `test_backoff_capped_by_next_daily_slot`: no backoff yet.
- `test_failures_keep_last_good_data`: it also asserts that backoff retries ran. Its data-kept assertions were already satisfied.
- `test_feed_with_only_past_programmes_retries`: the entry was LOADED.

## Files Created/Modified

- `custom_components/xmltv_calendar/cache.py`: `SourceHealth` with `as_dict`/tolerant `from_dict`, `FeedCache.health`, `async_save_health`. Every Store save writes meta and health.
- `custom_components/xmltv_calendar/coordinator.py`: `FAILURE_REASONS`, `issue_id()`, `health` property, `_async_record_success`/`_async_record_failure`/`_sync_issue`, backoff failure target, issue sync on cache start, `_require_programmes` (empty_feed).
- `custom_components/xmltv_calendar/__init__.py`: `async_remove_entry` deletes the Repairs issue.
- `custom_components/xmltv_calendar/translations/en.json`, `de.json`: `issues.source_failing_<reason>` ×6 (title, description), `exceptions.empty_feed`.
- `tests/test_repairs.py` (new): 10 Repairs/health tests.
- `tests/test_empty_feed.py` (new): 4 D-20 tests.
- `tests/test_schedule_refresh.py`: 3 backoff tests.
- `tests/test_calendar.py`: `feed-without-programmes` case and `NO_PROGRAMMES_FEED` removed.
- `tests/test_subentry_flow.py`: the channel-picker feed gains one zdf.de programme.
- `tests/test_cache.py`: `test_empty_parse_is_not_cached` adapted (see Deviations).

## Decisions Made

- Health is stored for file sources too, under the same Store key as URL caches. File sources still have no payload or meta.
- A success keeps `last_failure_at` and `last_failure_reason`, for diagnostics (03-07, D-21).
- Stored reasons are validated against `[a-z_]{1,64}`, and the issue only uses `FAILURE_REASONS`. A hand-edited Store cannot inject text or name a missing translation key (T-03-14).
- `SourceHealth` is frozen: `coordinator.health` is a safe read-only snapshot.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `tests/test_cache.py::test_empty_parse_is_not_cached` assumed no Store for an empty parse**
- **Found during:** Task 1 (GREEN full-suite run)
- **Issue:** The test asserted that the Store key does not exist after an empty parse. The health is now saved on every outcome, so the Store exists, but it holds no payload metadata.
- **Fix:** The test now asserts that the Store is absent or holds `meta: None`, and still checks that there is no payload file. After Task 3 the same setup ends in SETUP_RETRY and the assertions still hold.
- **Files modified:** tests/test_cache.py
- **Verification:** The full suite passes.
- **Committed in:** `064d8c7`

---

**Total deviations:** 1 auto-fixed (1 blocking test assumption)
**Impact on plan:** This is a necessary adaptation to the Store shape the plan itself specifies. There is no scope creep.

## Issues Encountered

- `gsd_run query git.base-branch --is-protected main` reports `true`. The orchestrator explicitly directed commits on `main` (branching_strategy none, sequential executor, same as 03-01..03-03), so the commits were made there.

## Verification

- `uv run pytest -q -m "not benchmark"`: 706 passed, 1 skipped.
- `uv run pytest -q -m benchmark`: 4 passed, 1 skipped.
- `uv run ruff check . && uv run ruff format --check .`: clean.
- Acceptance greps:
  - `source_failing_` count is 6 in en.json and 6 in de.json.
  - `is_fixable=False`, `class SourceHealth`, `backoff_delay(`, `async_delete_issue` and `translation_key="empty_feed"` are present.
  - `feed-without-programmes` count in tests/test_calendar.py is 0.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- 03-07 diagnostics can read `coordinator.health` (last success, failure streak, last failure with reason) and `issue_id()`.
- A source with no calendars is never refreshed (RESEARCH Pitfall 7), so its issue changes only at setup. This is accepted.

---
*Phase: 03-resilient-sources*
*Completed: 2026-10-16*

## Self-Check: PASSED
