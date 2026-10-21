---
phase: 04-automation-extras-release
plan: 06
subsystem: retention
tags: [home-assistant, calendar, storage, retention, past-matches, diagnostics]

requires:
  - phase: 04-automation-extras-release
    provides: "04-04: CalendarMatches, records_to_dict/records_from_dict, MatchStore, _async_refilter(reason), seen pruning; 04-05: diagnostics last_attempt"
  - phase: 03-resilient-sources
    provides: "coordinator._parser keep_after (one-day cut-off), source options naive_timezone/offset_minutes, unchanged-data identity, empty_feed rejection"
provides:
  - "xmltv/settings.py: KEY_RETENTION_DAYS = \"retention_days\", DEFAULT_RETENTION_DAYS = 1, MAX_RETENTION_DAYS = 7, _retention_days, last key of ADVANCED_DEFAULTS and with_defaults"
  - "xmltv/matches.py: RetainedMatch(programme, channel_name), CalendarMatches.retained, capture_ended, prune_retained (MAX_RETAINED = 5000, latest by start), merge_matches, strict retained (de)serialization"
  - "match_store.py: async_load(fingerprint); stored shape {calendars: {sid: {seen, retained}}, source: {naive_timezone, offset_minutes}}"
  - "calendar.py: _retention_days, _feed_matches, _channels, _retained_shown, retained_count, _capture_now, stop listener, removal capture, D-17 re-check on config refilters"
  - "diagnostics.py: calendar rows {title, matches, retained}"
affects: [04-07 retention field in the calendar form (key retention_days, 0..7), 04-08 README retention docs, UAT on ha-dev]

actuals:
  tokens: 10786
  tasks: 3
  commits: 6
plan_head_before: 1ebdc21755451bfe14512fb3347901ea062b58fc
plan_head_after: 7221d1fba548a472fd0dbc7c75b6c7c2310ea2b1

tech-stack:
  added: []
  patterns:
    - "Two match sources merged at index-build time: feed matches (truth about the future) plus ended-only retained programmes, feed wins on a UID collision"
    - "Capture points: every refilter (previous and new matches), entity removal, EVENT_HOMEASSISTANT_STOP (async_listen, unsubscribed on removal)"
    - "Source fingerprint in the match store invalidates derived data parsed under other timezone options"

key-files:
  created:
    - tests/test_retention.py
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-06-red*.json / *.xml
  modified:
    - custom_components/xmltv_calendar/xmltv/settings.py
    - custom_components/xmltv_calendar/xmltv/matches.py
    - custom_components/xmltv_calendar/match_store.py
    - custom_components/xmltv_calendar/calendar.py
    - custom_components/xmltv_calendar/__init__.py
    - custom_components/xmltv_calendar/diagnostics.py
    - tests/xmltv/test_settings.py
    - tests/xmltv/test_matches.py
    - tests/test_diagnostics.py
    - tests/test_reconfigure.py
    - tests/test_advanced_flow.py

key-decisions:
  - "Stored calendar key retention_days (int 0..7, default 1) is the last key of ADVANCED_DEFAULTS and with_defaults; bool, non-numeric and non-finite read as 1, values clamp to 0..7, fractions round down. Calendars saved through the flow now store it (15 keys)"
  - "Retention cutoff = now - retention_days for both retained programmes and the seen-set (replaces KEEP_PAST in calendar.py, D-13); retention 0 captures nothing"
  - "Retained store shape: per calendar a list of {channel_id, channel_name, start, stop (ISO 8601 UTC), titles, sub_titles, description, categories, episode}; the strict reader drops naive or unparsable times, stop before start, empty or non-string titles, empty channel IDs and wrong types"
  - "match_count stays the feed match count; retained_count counts retained programmes shown in addition to the feed and still inside the window"
  - "A filter edit (REFILTER_CONFIG) re-checks the retained programmes and the previous run's matches against the new filter in the same executor job as the feed; data and initial refilters skip the re-check"
  - "Match store fingerprint = {naive_timezone, offset_minutes}; a stored fingerprint that differs drops every calendar's retained programmes at load, seen-sets stay; a store without fingerprint (04-04/04-05) keeps its data"
  - "get_events hides retained programmes whose window has ended even when no refilter runs (304, identical body); removal capture is skipped for a calendar whose subentry is gone, so forget() is never undone"

patterns-established:
  - "Executor helper _apply_filter(spec, epg, recheck, tz) returns (feed result, allowed re-check set) so one job covers feed and retained filtering"

requirements-completed: [EVT-07]

coverage:
  - id: D1
    description: "A matching programme the feed dropped after it ended stays in the calendar for the retention days (default 1), also across a reload, and disappears after the window; future or airing matches the feed drops disappear at once"
    requirement: EVT-07
    verification:
      - kind: integration
        ref: "tests/test_retention.py#test_dropped_match_stays_for_retention_days"
        status: pass
      - kind: integration
        ref: "tests/test_retention.py#test_future_match_removed_from_feed_disappears"
        status: pass
      - kind: integration
        ref: "tests/test_retention.py#test_expired_retained_hidden_without_refilter"
        status: pass
      - kind: integration
        ref: "tests/test_retention.py#test_retention_zero_keeps_nothing"
        status: pass
    human_judgment: false
  - id: D2
    description: "Retention longer than the parser's one-day cut-off works: ended matches are captured from the previous run, on entity removal (reload) and on HA stop"
    requirement: EVT-07
    verification:
      - kind: integration
        ref: "tests/test_retention.py#test_three_day_retention_survives_parser_cutoff"
        status: pass
      - kind: integration
        ref: "tests/test_retention.py#test_capture_on_reload"
        status: pass
      - kind: integration
        ref: "tests/test_retention.py#test_capture_on_stop"
        status: pass
    human_judgment: false
  - id: D3
    description: "Edits follow the user's vision: filter edits drop no-longer-matching retained programmes (no resurrection on widening), template edits change retained text, retention edits apply in place without reload or request, timezone option changes drop retained programmes and keep seen-sets"
    requirement: EVT-07
    verification:
      - kind: integration
        ref: "tests/test_retention.py#test_filter_edit_rechecks_retained"
        status: pass
      - kind: integration
        ref: "tests/test_retention.py#test_template_edit_changes_retained_text"
        status: pass
      - kind: integration
        ref: "tests/test_retention.py#test_retention_edit_applies_in_place"
        status: pass
      - kind: integration
        ref: "tests/test_retention.py#test_timezone_change_drops_retained"
        status: pass
    human_judgment: false
  - id: D4
    description: "Pure rules: retention_days tolerant read and clamping, capture (stop <= now, no duplicates, channel-name fallbacks), prune boundary, merge preferring the feed, cap of 5,000 latest, strict tolerant stored reads; no UID shown twice"
    requirement: EVT-07
    verification:
      - kind: unit
        ref: "tests/xmltv/test_settings.py#test_with_defaults_tolerant_read"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_matches.py#test_capture_ended"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_matches.py#test_prune_retained_boundary"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_matches.py#test_merge_matches_prefers_feed"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_matches.py#test_retained_cap"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_matches.py#test_retained_roundtrip_and_tolerance"
        status: pass
      - kind: integration
        ref: "tests/test_retention.py#test_no_uid_is_shown_twice"
        status: pass
    human_judgment: false
  - id: D5
    description: "Diagnostics list per calendar matches (feed) and retained (store only, shown in addition) separately"
    requirement: EVT-07
    verification:
      - kind: integration
        ref: "tests/test_diagnostics.py#test_retained_matches_are_listed_apart"
        status: pass
      - kind: integration
        ref: "tests/test_diagnostics.py#test_diagnostics_end_to_end"
        status: pass
    human_judgment: false
  - id: D6
    description: "On ha-dev a match that ended earlier today stays in the calendar view after the test feed drops it and after an HA restart, and shows under retained in downloaded diagnostics"
    requirement: EVT-07
    verification: []
    human_judgment: true
    rationale: "Task 3 <human-check>: the real frontend calendar view, a real HA restart (stop event, final write, .storage on disk) and the diagnostics download are not exercised end to end by the phcc tests"

duration: 14min
completed: 2026-10-21
status: complete
---

# Phase 4 Plan 06: Recent Past Matches (Retention) Summary

**Matches that have ended now stay in the calendar for the calendar's `retention_days` (0..7, default 1) after the feed drops them. They are stored as raw programme data in the per-source match store and captured on every refilter, on entity removal and on HA stop, so retention of more than one day survives the parser's one-day cut-off and restarts. They merge with the feed by UID (the feed wins), get re-checked when the filter is edited, are dropped when the source's timezone options change, and show up separately as `retained` in diagnostics.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-10-21T09:55:43Z
- **Completed:** 2026-10-21T10:09:32Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 6 integration files and 6 test files, plus 10 RED evidence files

## Accomplishments

- **Settings contract:** `retention_days` is the last stored calendar key, with a tolerant reader. `has_advanced` sees a non-default retention, so 04-07's form will pre-check "Advanced".
- **Pure retention rules** (`xmltv/matches.py`):
  - `RetainedMatch(programme, channel_name)`.
  - `capture_ended`: captures programmes with stop <= now and no duplicate UID. The channel name is the display name, else the stored name, else the channel ID.
  - `prune_retained`: keeps stop >= cutoff, sorted by start, and caps at the 5,000 latest.
  - `merge_matches`: the feed wins on a UID collision (D-18).
  - Strict JSON (de)serialization.
- **Calendar:**
  - Each refilter captures ended matches from the previous and the new run, prunes them to the window, persists them with the seen-set (same cutoff) and indexes feed + retained.
  - Rendering uses a channel map that includes the stored names of channels that left the feed.
  - `async_will_remove_from_hass` and an `EVENT_HOMEASSISTANT_STOP` listener capture once more without refiltering.
  - A filter edit re-checks retained programmes in the same executor job (D-17). A retention edit applies in place.
  - `get_events` hides retained programmes whose window has ended, even when unchanged feeds skip the refilter.
- **Match store:** setup passes `{naive_timezone, offset_minutes}` as the source fingerprint. A mismatch drops the retained programmes and keeps the seen-sets. Every save writes `source`.
- **Diagnostics:** rows are `{title, matches, retained}`.

## Task Commits

1. **Task 1 (tracer): a dropped match stays for one day, also across a reload.** RED `e2b0917`, GREEN `74c8f69`
2. **Task 2: pure retention rules.** RED `b165e0b`, GREEN `afcaf3d`
3. **Task 3: capture on removal and stop, timezone fingerprint, edits, diagnostics.** RED `07f75fa`, GREEN `7221d1f`

Tracer feedback gate after Task 1 (interactive, `end-of-phase`, automated-only verify): the Task 1 verify command was re-run (162 passed) before Task 2 started.

## RED Evidence

Every record classifies as `RED_EVIDENCE_OK (target_test_failed)` and carries a `semanticAssessment`:

- `04-06-red.json`, target `test_dropped_match_stays_for_retention_days`. After the race-less refresh the calendar showed only Tagesschau; nothing retained ended matches.
- `04-06-red-2-cap.json`, target `test_retained_cap`. `prune_retained` returned all 5,003 items unsorted. `MAX_RETAINED` was a no-op stub in the RED commit, so the test failed on behaviour rather than on an ImportError (04-04 lesson).
- `04-06-red-2-tolerance.json`, target `test_retained_roundtrip_and_tolerance[naive_start]`. The lenient Task 1 reader accepted the naive start. Eleven sibling cases failed the same assertion. `empty_titles` failed with IndexError, which shows the crash the strict reader prevents.
- `04-06-red-3-test_capture_on_reload.json`: the reloaded calendar was empty.
- `04-06-red-3-test_capture_on_stop.json`: the final write saved a record without retained programmes.
- `04-06-red-3-test_filter_edit_rechecks_retained.json`: the race survived narrowing to zdf.de.
- `04-06-red-3-test_retention_edit_applies_in_place.json`: retention 0 left the race shown.
- `04-06-red-3-test_timezone_change_drops_retained.json`: the race was still shown after the offset change.
- `04-06-red-3-test_retained_matches_are_listed_apart.json`: the row had no `retained` key.

`test_expired_retained_hidden_without_refilter` also failed in the `04-06-red-3.xml` run; that report covers it.

These tests were already green in RED and serve as regression guards:

- `test_future_match_removed_from_feed_disappears` (Task 1)
- In Task 2: the capture, prune-boundary and merge tests; all `retention_days` settings and `has_advanced` cases (Task 1 already implemented `_retention_days` in full); and the `unparsable_start`, `int_start`, `none_titles`, `none_sub_titles` and `none_stop` tolerance cases
- In Task 3: `test_three_day_retention_survives_parser_cutoff` (Task 1 already captures from the previous run), `test_retention_zero_keeps_nothing`, `test_template_edit_changes_retained_text` and `test_no_uid_is_shown_twice` (the D-18 invariant)

## TDD Gate Compliance

Each task has a `test(04-06)` commit before its `feat(04-06)` commit. No REFACTOR commits were needed.

## Files Created/Modified

- `custom_components/xmltv_calendar/xmltv/settings.py`: retention key, constants, reader, defaults order
- `custom_components/xmltv_calendar/xmltv/matches.py`: retained model, capture/prune/merge, cap, strict reader
- `custom_components/xmltv_calendar/match_store.py`: `async_load(fingerprint)`, `source` in the saved data
- `custom_components/xmltv_calendar/calendar.py`: retention in the refilter, `_apply_filter`, capture on removal and stop, retained expiry in `get_events`, retention edits
- `custom_components/xmltv_calendar/__init__.py`: fingerprint from `coordinator.source_options`
- `custom_components/xmltv_calendar/diagnostics.py`: `retained` per calendar row
- `tests/test_retention.py` (new, 13 tests); additions to `tests/xmltv/test_matches.py`, `tests/xmltv/test_settings.py` and `tests/test_diagnostics.py`; expectation updates in `tests/test_reconfigure.py` and `tests/test_advanced_flow.py`

## Decisions Made

- **Re-check scope.** Only `REFILTER_CONFIG` re-checks against the filter. The previous run's matches are re-checked together with the stored retained programmes, so an ended match from the old filter cannot slip in through the capture after a narrowing edit.
- **Removal capture guard.** The removal capture does nothing when the calendar's subentry is gone. Otherwise HA could remove the entity after the listener's `forget()` and bring the record back.
- **`retained_count`.** It counts only retained programmes still inside the window, matching what `get_events` shows between refilters.
- **Stored shape.** `records_to_dict` always writes `"retained": []`, so the stored shape is uniform. `"source"` is added by `MatchStore._data_to_save`, which keeps `matches.py` free of store concerns.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test expectations for the stored calendar key set**
- **Found during:** Task 1 (GREEN, verify and full suite)
- **Issue:** `tests/test_reconfigure.py::test_phase1_calendar_edit_keeps_events` asserted exactly 14 stored keys. `tests/test_advanced_flow.py::test_advanced_options_end_to_end` asserted the created data without `retention_days`. Calendars saved through the flow store `with_defaults(...)`, which now includes the new key.
- **Fix:** Expect 15 keys and `"retention_days": 1`. The literal is used because 04-07 adds the `CONF_` constant and the form field.
- **Files modified:** tests/test_reconfigure.py, tests/test_advanced_flow.py
- **Commit:** `74c8f69`

**2. [Rule 3 - Blocking] No-op `MAX_RETAINED` stub in the Task 2 RED commit**
- **Found during:** Task 2 RED
- **Issue:** `test_retained_cap` imports `MAX_RETAINED`. Without the constant the RED run would fail with ImportError, which is INVALID_RED.
- **Fix:** The RED commit added the constant without applying it. GREEN applied it in `prune_retained`.
- **Commit:** `b165e0b` (stub), `afcaf3d` (real)

**3. [Rule 1 - Test fix] UID invariant test reads the entity's events**
- **Found during:** Task 3 RED
- **Issue:** The `calendar.get_events` service response has no `uid` field.
- **Fix:** `test_no_uid_is_shown_twice` calls `entity.async_get_events` and compares against `_feed_matches` / `_retained_shown`.
- **Commit:** `07f75fa`

**4. [Process] Commits on `main`**
- `git.allow_default_branch_commits: true` applies, and the orchestrator dispatched this executor sequentially on the main working tree.

**Total deviations:** 3 auto-fixed (2 bugs/test fixes, 1 blocking), 1 process note. **Impact:** none on scope. The planned interfaces and stored shape are as specified.

## Issues Encountered

None.

## Known Stubs

None. The Task 2 RED stub was replaced in `afcaf3d`.

## Threat Flags

None. There is no new surface beyond the plan's threat model:
- T-04-17 is mitigated by the window, `MAX_RETAINED = 5000`, `forget`/`retain_only`, and off-loop serialization (`test_retained_cap`).
- T-04-18 is mitigated by the strict reader and the clamped `retention_days` (`test_retained_roundtrip_and_tolerance`, `test_with_defaults_tolerant_read`).
- T-04-19: the Store is still `private=True`. The new `source` field holds two option values and no URL.
- T-04-SC: no packages were added.

## Verification

- `uv run pytest -q -m "not benchmark"`: 966 passed, 1 skipped, 4 deselected
- `uv run pytest -q -m benchmark`: 4 passed, 1 skipped
- `uv run ruff check . && uv run ruff format --check .`: clean, 72 files formatted
- Task verify commands: Task 1 162 passed; Task 2 (`tests/xmltv/ -m "not benchmark"`) 568 passed, 1 skipped; Task 3 is the full suite above
- All acceptance greps pass:
  - `KEY_RETENTION_DAYS = "retention_days"`
  - `def merge_matches`
  - `MAX_RETAINED = 5000`
  - `EVENT_HOMEASSISTANT_STOP` in calendar.py
  - `"retained"` in diagnostics.py
  - `merge_matches(` in calendar.py
  - `fingerprint` in `__init__.py`
- Human check (deferred to end of phase, D6), on ha-dev:
  1. Drop an ended match from the local test feed and run `homeassistant.update_entity`.
  2. The calendar view still shows the match.
  3. Restart HA; the match is still there.
  4. Diagnostics show it under `retained`.

## User Setup Required

None.

## Next Phase Readiness

- 04-07 can add the retention field to the calendar form's advanced step. Use key `retention_days` with `NumberSelector` 0..7 in box mode. A cleared field means the default 1. `_advanced_suggestions` already picks the key up through `ADVANCED_DEFAULTS`. Remove the `"retention_days": 1` literal in `tests/test_advanced_flow.py` once `CONF_RETENTION_DAYS` exists.
- 04-08 README: document retention (0..7 days, default 1; ended-only; feed wins; filter edits drop, template edits re-render; timezone option changes drop retained programmes). Also document the accepted gap: matches that end while HA is down and are more than a day old at restart cannot be captured (RESEARCH Open Question 3).

---
*Phase: 04-automation-extras-release*
*Completed: 2026-10-21*

## Self-Check: PASSED
