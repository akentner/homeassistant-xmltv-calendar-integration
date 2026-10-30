---
phase: 04-automation-extras-release
plan: 04
subsystem: events
tags: [home-assistant, event-bus, storage, seen-set, xmltv_calendar_new_match]

requires:
  - phase: 04-automation-extras-release
    provides: "04-01: describe_match (incl. uid), signal_matches, per-platform add_entities, PLATFORMS = [CALENDAR, SENSOR]"
  - phase: 03-reliability
    provides: "cache_key, FeedCache Store patterns, source options reload, empty_feed rejection"
provides:
  - "Event xmltv_calendar_new_match with keys entity_id, calendar, title, summary, channel, channel_id, start, end, uid"
  - "xmltv/matches.py (pure): CalendarMatches, new_matches, split_announcements, prune_seen, records_to_dict, records_from_dict"
  - "match_store.py: MatchStore per source (Store xmltv_calendar.matches.<cache key>) with get/put/forget/retain_only/async_flush/async_remove"
  - "calendar.py: REFILTER_INITIAL/DATA/CONFIG, _async_refilter(reason), _baseline_ready, _fire_new_match_events"
  - "XmltvRuntimeData.match_store"
affects: [04-06 past matches / retention (extends the same store and record), release docs (event payload)]

actuals:
  tokens: 8201
  tasks: 3
  commits: 6
plan_head_before: c971808823dac3d304593f5f80749d6814418d17
plan_head_after: 19dc08b767065cceac6950fbe4185d9931ac2064

tech-stack:
  added: []
  patterns:
    - "Refilter reason (initial/data/config) plus a per-entity baseline flag decides whether new matches are announced"
    - "Per-source Store with copy-on-write records, delayed off-loop saves (serialize_in_event_loop=False) and an explicit flush on unload"
    - "Entities bump their refilter generation on removal so in-flight runs never write after unload"

key-files:
  created:
    - custom_components/xmltv_calendar/xmltv/matches.py
    - custom_components/xmltv_calendar/match_store.py
    - tests/test_new_match_event.py
    - tests/xmltv/test_matches.py
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-04-red*.json / *.xml
  modified:
    - custom_components/xmltv_calendar/calendar.py
    - custom_components/xmltv_calendar/__init__.py
    - custom_components/xmltv_calendar/data.py
    - custom_components/xmltv_calendar/const.py

key-decisions:
  - "New-match events fire only for refilter reason data after the entity's first completed refilter; initial (add, restart, reload, source option change) and config (filter or template edit) refilters update the seen-set silently (D-10, D-11), without a fingerprint"
  - "Burst cap MAX_NEW_MATCH_EVENTS = 50 per calendar and refresh, earliest start first, one WARNING with the suppressed count (D-12)"
  - "Seen entries are pruned at stop < now - KEEP_PAST (one day) on every refilter; 04-06 replaces KEEP_PAST with the calendar's retention days (D-13)"
  - "records_to_dict returns the full stored form {calendars: {...}}, so records_from_dict(records_to_dict(x)) == x holds on the stored shape"
  - "Calendars discard refilters still in flight when the entity is removed, so a late run cannot re-arm the old Store's delayed save after the unload flush (Pitfall 3)"

patterns-established:
  - "Match store lifecycle: load before forwarding platforms, retain_only(calendar subentry IDs) at setup, forget on subentry removal, async_flush on unload, async_remove with the entry"

requirements-completed: [EVT-08]

coverage:
  - id: D1
    description: "A refresh that brings a new matching programme starting after now fires exactly one xmltv_calendar_new_match event with the nine D-07 keys (start/end as local ISO 8601 strings); nothing fires at setup"
    requirement: EVT-08
    verification:
      - kind: integration
        ref: "tests/test_new_match_event.py#test_new_programme_fires_one_event"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_matches.py#test_new_matches_only_future_unseen"
        status: pass
      - kind: integration
        ref: "tests/test_new_match_event.py#test_started_match_is_not_announced"
        status: pass
    human_judgment: false
  - id: D2
    description: "At most 50 events per calendar and refresh in start order; the rest join the seen-set with one WARNING"
    requirement: EVT-08
    verification:
      - kind: integration
        ref: "tests/test_new_match_event.py#test_burst_is_capped"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_matches.py#test_split_announcements"
        status: pass
    human_judgment: false
  - id: D3
    description: "Silent baselines: new calendar, restart/reload, double reload, filter edit and timezone offset change announce nothing; only later feed data announces unseen UIDs"
    requirement: EVT-08
    verification:
      - kind: integration
        ref: "tests/test_new_match_event.py#test_restart_does_not_announce_again"
        status: pass
      - kind: integration
        ref: "tests/test_new_match_event.py#test_double_reload_keeps_seen_set"
        status: pass
      - kind: integration
        ref: "tests/test_new_match_event.py#test_new_calendar_is_silent"
        status: pass
      - kind: integration
        ref: "tests/test_new_match_event.py#test_filter_edit_is_silent"
        status: pass
      - kind: integration
        ref: "tests/test_new_match_event.py#test_timezone_change_is_silent"
        status: pass
    human_judgment: false
  - id: D4
    description: "Seen-set persisted per calendar in xmltv_calendar.matches.<cache key>, pruned after the window, tolerant of malformed data, cleaned up on calendar and source removal"
    requirement: EVT-08
    verification:
      - kind: integration
        ref: "tests/test_new_match_event.py#test_seen_set_is_persisted"
        status: pass
      - kind: integration
        ref: "tests/test_new_match_event.py#test_seen_is_pruned_after_the_window"
        status: pass
      - kind: integration
        ref: "tests/test_new_match_event.py#test_removed_calendar_and_source_clean_up"
        status: pass
      - kind: integration
        ref: "tests/test_new_match_event.py#test_setup_drops_records_of_unknown_calendars"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_matches.py#test_prune_seen"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_matches.py#test_records_from_dict_is_tolerant"
        status: pass
    human_judgment: false
  - id: D5
    description: "On a real HA instance the event appears in Developer tools > Events with title, channel and local start, and does not repeat after an HA restart"
    requirement: EVT-08
    verification: []
    human_judgment: true
    rationale: "Plan human-check for Task 3 (ha-dev): the real event bus, Developer tools listener and a real HA restart are not exercised by the phcc tests"

duration: 10min
completed: 2026-10-21
status: complete
---

# Phase 4 Plan 04: New-Match Event Summary

**A new matching programme in a refreshed feed now fires one `xmltv_calendar_new_match` event, with the calendar, programme and local start/end in the payload. The per-calendar seen-set behind it is persisted in a per-source Store and pruned after one day. Events are capped at 50 per refresh. Restarts, reloads, new calendars, filter edits and timezone changes stay silent.**

## Performance

- **Duration:** about 10 min
- **Started:** 2026-10-21T09:24:56Z
- **Completed:** 2026-10-21T09:34:30Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 8 code/test files, plus the RED evidence

## Accomplishments

- `xmltv/matches.py` (new, pure). Contents:
  - `CalendarMatches(seen)`, a frozen slotted dataclass.
  - `new_matches`: returns unseen matches with `start > now`, ordered by start, channel ID and title. Every given match joins the seen-set.
  - `split_announcements` and `prune_seen`.
  - Tolerant `records_to_dict` / `records_from_dict`: a non-dict, non-str key, non-int or bool stop drops that item.
- `match_store.py` (new). `MatchStore` wraps `Store(..., f"xmltv_calendar.matches.{key}", private=True, serialize_in_event_loop=False)`.
  - Records are replaced copy-on-write, never mutated.
  - `put` / `forget` / `retain_only` schedule a 10 s delayed save.
  - `async_flush` writes at once. `async_remove` deletes the file.
- `calendar.py`:
  - `_async_refilter(reason)` updates and prunes the seen-set on every completed run.
  - It fires events only for `REFILTER_DATA` after `_baseline_ready`.
  - `_fire_new_match_events` uses the nine D-07 keys from `describe_match`, caps the count, and logs the WARNING.
  - `async_will_remove_from_hass` discards in-flight runs.
- `__init__.py`:
  - Setup loads the store before the platforms and calls `retain_only` with the calendar subentry IDs.
  - The update listener forgets removed calendars.
  - Unload flushes after the platforms are unloaded.
  - `async_remove_entry` deletes the store next to the feed cache.
- `const.py`: `EVENT_NEW_MATCH = f"{DOMAIN}_new_match"` and `MAX_NEW_MATCH_EVENTS = 50`. `data.py`: `XmltvRuntimeData.match_store`.

## Task Commits

1. **Task 1 (tracer): new programme fires one event.** RED `8136ca6`, GREEN `6a276bc`
2. **Task 2: future only, ordering, burst cap, pruning, tolerant reading.** RED `9ff424c`, GREEN `a5316fa`
3. **Task 3: silent baselines and store lifecycle.** RED `d75c96e`, GREEN `19dc08b`

No refactor commits were needed.

## TDD Gate Compliance

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 1 (tracer) | `8136ca6` test(04-04) | `6a276bc` feat(04-04) | none |
| 2 | `9ff424c` test(04-04) | `a5316fa` feat(04-04) | none |
| 3 | `d75c96e` test(04-04) | `19dc08b` feat(04-04) | none |

Every RED record classifies as `RED_EVIDENCE_OK (target_test_failed)` and carries a `semanticAssessment`:

- `04-04-red.json`, target `test_new_programme_fires_one_event`. After setup (`events == []` passed) and a refresh with the race, the event list was empty. The integration set up normally.
- `04-04-red-2-split.json`, target `test_split_announcements`. The call returned all 60 with 0 suppressed, not (50 earliest, 10).
- `04-04-red-2-prune.json`, target `test_prune_seen`. `old` (cutoff - 1 s) was kept.
- `04-04-red-2-burst.json`, target `test_burst_is_capped`. 60 events fired in start order, and the first extra was `Show 50`.
- `04-04-red-3-test_removed_calendar_and_source_clean_up.json`. The removed calendar B's record was still stored.
- `04-04-red-3-test_setup_drops_records_of_unknown_calendars.json`. The orphan record `gone` survived setup.

`test_seen_is_pruned_after_the_window` also failed in the `04-04-red-2.xml` run (the seen-set still held the 13 October UIDs). It is covered by the same report.

Regression guards, listed as the plan requires:
- Green after Task 1: `test_started_match_is_not_announced`, `test_new_matches_only_future_unseen`, `test_new_matches_keeps_unrelated_seen_entries`, `test_records_from_dict_is_tolerant[*]` (9 cases), `test_records_round_trip`. Task 1 already had the future-only rule, the seen-set, and the tolerant reader.
- Green after Task 1, for D-10/D-11: `test_restart_does_not_announce_again`, `test_double_reload_keeps_seen_set`, `test_new_calendar_is_silent`, `test_filter_edit_is_silent`, `test_timezone_change_is_silent`. The refilter reasons, the baseline flag and the unload flush from Task 1 already covered them, as RESEARCH Pattern 1 predicted.

## Decisions Made

- `records_to_dict` returns the full stored form `{"calendars": {...}}`, and `_data_to_save` returns it unchanged. The plan text wraps the result in `{"calendars": ...}` once more, but its tolerance test passes the full stored form to `records_from_dict` and demands a round trip. The stored shape is exactly as planned.
- `new_matches` reads membership from the growing mapping. A UID that appears twice in one feed is announced at most once.
- The WARNING is logged before the capped events fire. Its text matches the plan exactly.

## Deviations from Plan

### Auto-fixed Issues

**1. [TDD evidence - Fail-fast rule 2] RED stubs for `split_announcements` and `prune_seen`**
- **Found during:** Task 2 (RED)
- **Issue:** I imported inside the test bodies as planned. Even so, the first run failed `test_split_announcements` and `test_prune_seen` with `ImportError`. That is an import fault, not an assertion failure on the planned behaviour, so it cannot authorize GREEN.
- **Fix:** The RED commit adds no-op stubs that keep the current behaviour: no cap (`(list(new), 0)`) and no pruning (`dict(seen)`). Both targets then failed on their planned assertions, and those runs are the recorded evidence. GREEN replaced the stubs. The discarded ImportError run is documented in the records' `semanticAssessment`.
- **Files modified:** custom_components/xmltv_calendar/xmltv/matches.py
- **Commit:** `9ff424c` (stubs), `a5316fa` (real implementation)

**2. [Rule 1 - Bug] In-flight refilter could write to the old store after the unload flush**
- **Found during:** Task 3 (GREEN)
- **Issue:** `ConfigEntry.async_unload` waits for entry tasks only after `async_unload_entry` returns. A data refilter still in the executor could therefore `put` into the old `MatchStore` after the flush and re-arm its delayed save. That save would fire about 10 s later and overwrite the new store's data, which is the Pitfall 3 path through a different door. Such a run could also bring back the record of a calendar removed while it was running.
- **Fix:** `XmltvCalendarEntity.async_will_remove_from_hass` bumps `_generation`, so a run that finishes after removal is discarded by the existing generation check.
- **Files modified:** custom_components/xmltv_calendar/calendar.py
- **Verification:** The full suite passes. The race itself is timing-dependent and not covered by a deterministic test.
- **Commit:** `19dc08b`

**3. [Scope] Extra test `test_setup_drops_records_of_unknown_calendars`**
- `retain_only` at setup is a planned deliverable with no planned test, so I added one. It was a RED target in Task 3.

**4. [Process] Commits on `main`**
- `git.allow_default_branch_commits: true` applies. The orchestrator dispatched this executor sequentially on the main working tree, as for 04-01..04-03.

**Total deviations:** 2 auto-fixed (1 TDD-evidence fix, 1 bug), 1 added test, 1 process note. **Impact:** none on scope. The planned interfaces and stored shape are unchanged.

## Issues Encountered

None.

## Known Stubs

None. The Task 2 RED stubs were replaced in `a5316fa`.

## Threat Flags

None. There is no new surface beyond the plan's threat model.
- T-04-09: the cap is mitigated (`test_burst_is_capped`).
- T-04-10: pruning plus forget/retain_only/remove are mitigated (`test_seen_is_pruned_after_the_window`, `test_removed_calendar_and_source_clean_up`, `test_setup_drops_records_of_unknown_calendars`).
- T-04-11: the tolerant reader is mitigated (`test_records_from_dict_is_tolerant`).
- T-04-12: the payload is limited to the nine keys and holds no URL (`test_new_programme_fires_one_event`).
- T-04-SC: no packages were added.

## Verification

- `uv run pytest -q -m "not benchmark"`: 891 passed, 1 skipped, 4 deselected.
- `uv run ruff check . && uv run ruff format --check .`: all checks passed, 70 files already formatted.
- Task verify commands passed. Task 1: 41 passed. Task 2: 21 passed.
- Acceptance greps all passed:
  - `EVENT_NEW_MATCH` in const.py
  - `serialize_in_event_loop=False` in match_store.py
  - `async_flush` in `__init__.py`
  - `def split_announcements` in matches.py
  - `MAX_NEW_MATCH_EVENTS` in calendar.py
  - `def retain_only` in match_store.py
  - `MatchStore(hass, cache_key(entry)).async_remove()` in `__init__.py`
- Tracer feedback gate (interactive, `human_verify_mode: end-of-phase`, automated-only verify): Task 1 verify passed again before expansion.
- Human check (deferred to end of phase, D5): on ha-dev, listen to `xmltv_calendar_new_match` in Developer tools > Events and add a matching programme to the test feed. Then run `homeassistant.update_entity` and expect one event. A restart should show no repeat.

## Next Phase Readiness

Ready for 04-05/04-06. 04-06 extends `CalendarMatches` and `records_to_dict`/`records_from_dict` with retained programmes. It also replaces `KEEP_PAST` in the `prune_seen` call (calendar.py `_async_refilter`) with the calendar's retention days.

## Self-Check: PASSED
