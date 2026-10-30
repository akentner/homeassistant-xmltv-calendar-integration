---
phase: 02-precise-filters-preview
plan: 01
subsystem: calendar
tags: [home-assistant, config-subentry, update-listener, device-registry, bisect]

requires:
  - phase: 01-first-filtered-calendar
    provides: single diffing update listener, XmltvCalendarEntity with generation counter, MatchIndex
provides:
  - In-place apply of edited calendar subentries (title and data) through the single update listener
  - XmltvCalendarEntity._spec, differs_from(), async_apply_subentry(), module helper _build_spec()
  - Device rename on calendar title change without refilter
  - MatchIndex._lower() OverflowError clamp (IN-14)
affects: [02-02, 02-03, 02-05, reconfigure flow, templates]

actuals:
  tokens: 4450
  tasks: 2
  commits: 4
plan_head_before: 5a8952e872f63e13ceb2a8cb6786ed4830c8f353
plan_head_after: a71965629e9fbeeb4bfadeb532a5350354db6a4d

tech-stack:
  added: []
  patterns:
    - "Entity owns its FilterSpec (single source of truth); listener diffs (title, data) per entity and calls async_apply_subentry"
    - "Diff base stored before any await, so concurrent listener tasks see an edit as applied"

key-files:
  created:
    - tests/test_reconfigure.py
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-01-red.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-01-red-2-rename.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-01-red-2-corrupt.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-01-red-2-overflow.json
  modified:
    - custom_components/xmltv_calendar/calendar.py
    - custom_components/xmltv_calendar/__init__.py
    - custom_components/xmltv_calendar/xmltv/window.py
    - tests/xmltv/test_window.py

key-decisions:
  - "02-01: device lookup for the rename uses async_get_device_by_identifier((DOMAIN, subentry_id), entry_id); async_get_device is deprecated and raises in HA 2026.10"
  - "02-01: the listener iterates over a copy of runtime.calendars and uses entry.subentries.get, because HA runs each update listener call as its own task"
  - "02-01: a stored pattern that does not compile at entity creation gives an empty index (Phase 1 visible result); on an edit it keeps the previous spec and matches, and the bad data still becomes the diff base"

patterns-established:
  - "In-place calendar edit: listener -> entity.differs_from(subentry) -> await entity.async_apply_subentry(subentry)"
  - "Title-only edit: rename device via device registry, no refilter; friendly_name follows the device name"

requirements-completed: [FLT-11]

coverage:
  - id: D1
    description: "Editing a calendar subentry's data updates that calendar in place: no download, no parse, no reload, sibling entity and events untouched"
    requirement: FLT-11
    verification:
      - kind: integration
        ref: "tests/test_reconfigure.py#test_data_change_applies_in_place"
        status: pass
    human_judgment: false
  - id: D2
    description: "Title-only edit renames the device and friendly_name, keeps entity_id, skips the refilter"
    requirement: FLT-11
    verification:
      - kind: integration
        ref: "tests/test_reconfigure.py#test_title_change_renames_device"
        status: pass
    human_judgment: false
  - id: D3
    description: "No-op update, two calendars edited together, last of two edits wins, apply before the entity is added"
    requirement: FLT-11
    verification:
      - kind: integration
        ref: "tests/test_reconfigure.py#test_unchanged_update_is_a_no_op"
        status: pass
      - kind: integration
        ref: "tests/test_reconfigure.py#test_two_calendars_changed_together"
        status: pass
      - kind: integration
        ref: "tests/test_reconfigure.py#test_last_of_two_updates_wins"
        status: pass
      - kind: integration
        ref: "tests/test_reconfigure.py#test_apply_before_added_stores_settings"
        status: pass
    human_judgment: false
  - id: D4
    description: "Uncompilable stored pattern keeps the calendar's previous matches, logs one WARNING naming it, other calendars still update (T-02-01)"
    requirement: FLT-11
    verification:
      - kind: integration
        ref: "tests/test_reconfigure.py#test_corrupt_pattern_keeps_previous_matches"
        status: pass
    human_judgment: false
  - id: D5
    description: "MatchIndex.overlapping and current_or_next do not raise OverflowError near datetime.min (IN-14)"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_window.py#test_queries_near_datetime_min_do_not_overflow"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-10-15
status: complete
---

# Phase 2 Plan 01: In-place Calendar Reconfigure Summary

**Calendar subentry edits now apply in place through the single diffing listener. The entity rebuilds its own FilterSpec and re-filters `coordinator.data` with no download, parse or reload. Title edits rename the device. Corrupt stored patterns keep the previous matches. MatchIndex lookups clamp near `datetime.min` (IN-14).**

## Performance

- **Duration:** about 4 min
- **Started:** 2026-10-15T10:25:42Z
- **Completed:** 2026-10-15T10:29:56Z
- **Tasks:** 2 (tracer + TDD expansion)
- **Files modified:** 5 source/test files plus 6 TDD evidence files

## Accomplishments
- `_async_entry_updated` applies changed calendar subentries in place. It runs after the removal loop and before the add-entities guard, and only for calendars whose `(title, data)` differs (FLT-11, D-04).
- `XmltvCalendarEntity` builds its `FilterSpec` once (`_build_spec`) and no longer re-reads `entry.subentries` in `_async_refilter`.
- A title-only edit renames the device. `friendly_name` follows the device name, `entity_id` stays the same, and the match index object stays untouched.
- A corrupt stored pattern is contained to its own calendar: it keeps its previous matches and logs one WARNING. Siblings changed in the same listener call still update (T-02-01).
- IN-14 is closed: `MatchIndex._lower()` returns 0 when `t - max_duration` overflows.

## Task Commits

1. **Task 1 (tracer): in-place data change**
   - RED `d3fb1be` (test)
   - GREEN `5e821b5` (feat)
   - Tracer gate re-run green, so the plan continued to Task 2.
2. **Task 2: rename, no-op, ordering, not-yet-added, corrupt data, IN-14**
   - RED `1541985` (test)
   - GREEN `a719656` (feat)

No REFACTOR commit was needed.

## TDD Gate Compliance

| Gate | Commit | Evidence |
|------|--------|----------|
| RED (Task 1) | `d3fb1be` | `02-01-red.json`: RED_EVIDENCE_OK. `test_data_change_applies_in_place` failed on the calendar.a summaries assertion (it returned `['Das Erste: Tagesschau']`, because the Phase 1 listener ignored data edits). |
| GREEN (Task 1) | `5e821b5` | Task 1 verify passed: 12 tests. |
| RED (Task 2) | `1541985` | Three records, all RED_EVIDENCE_OK. **rename:** device.name was `'A'`, not `'Renamed'`. **corrupt:** calendar.a returned `[]`, because of the empty index. **overflow:** OverflowError at `window.py:35`. |
| GREEN (Task 2) | `a719656` | Task 2 verify passed: 36 tests. |

Regression guards (green right after Task 1, kept as guards as the plan specifies):
- `test_unchanged_update_is_a_no_op`
- `test_two_calendars_changed_together`
- `test_last_of_two_updates_wins`
- `test_apply_before_added_stores_settings`

## Files Created/Modified
- `custom_components/xmltv_calendar/calendar.py`: `_build_spec`, `_spec`, `_subentry_title`, `differs_from`, `async_apply_subentry` (device rename, corrupt-pattern containment, Pitfall 10 guard).
- `custom_components/xmltv_calendar/__init__.py`: in-place apply loop in `_async_entry_updated`, and an updated listener comment.
- `custom_components/xmltv_calendar/xmltv/window.py`: `MatchIndex._lower()` OverflowError clamp, used by `overlapping` and `current_or_next`.
- `tests/test_reconfigure.py` (new): 7 in-place update tests.
- `tests/xmltv/test_window.py`: `test_queries_near_datetime_min_do_not_overflow`.

## Decisions Made
- **Device lookup:** uses `async_get_device_by_identifier((DOMAIN, subentry_id), entry_id)` instead of the plan's `async_get_device(identifiers=...)`. In HA 2026.10, `async_get_device` raises a deprecation RuntimeError for custom integrations.
- **Listener iteration:** the listener walks a copy of `runtime.calendars` and reads subentries with `entry.subentries.get`. HA runs each update listener call as its own task (`_async_save_and_notify` uses `async_create_task`), so calls can interleave.
- **When the diff base is stored:** `async_apply_subentry` stores the new diff base before any await. A concurrent listener call then sees the edit as already applied, and the generation counter discards stale refilters.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Deprecated device-registry lookup in the plan's action**
- **Found during:** Task 2 RED. The first run of the rename test failed with a RuntimeError ("async_get_device ... is deprecated") instead of on its assertion.
- **Issue:** The plan prescribed `dr.async_get(hass).async_get_device(identifiers={(DOMAIN, id)})`. That call raises in HA 2026.10.
- **Fix:**
  - The test and the implementation both use `async_get_device_by_identifier((DOMAIN, subentry_id), entry.entry_id)`.
  - RED was re-run, and this run's record is the one committed.
  - The rename record's `semanticAssessment` documents the first wrong-reason run.
- **Files modified:** `tests/test_reconfigure.py`, `custom_components/xmltv_calendar/calendar.py`
- **Committed in:** `1541985`, `a719656`

**2. [Rule 2 - Missing Critical] Listener robust against concurrent calls**
- **Found during:** Task 1 GREEN.
- **Issue:** Iterating `runtime.calendars` directly while awaiting `async_apply_subentry` can raise "dictionary changed size during iteration". That happens when a concurrent listener task adds a calendar.
- **Fix:** iterate over `list(runtime.calendars.items())` and use `entry.subentries.get(...)`, skipping subentries that have vanished.
- **Committed in:** `5e821b5`

**Process note:**
- The commits landed on `main`. `git.base-branch --is-protected main` returns true, but `branching_strategy` is `none`.
- The orchestrator dispatched this plan sequentially on the main working tree. All Phase 1 commits also live on `main`.
- The protected-branch step for `none` only warns, so no branch was created and no config was changed.

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical).
**Impact on plan:** Both were needed for correctness on HA 2026.10. There was no scope creep.

## Issues Encountered
- The plan estimated 60,000 tokens. The realized code/test diff is about 4,450 tokens (chars/4). The estimate's scale was evidently much broader than this diff.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness
- 02-05 (the reconfigure flow) can rely on `async_update_and_abort` plus this listener path. No reload is needed.
- 02-02 and 02-03 can extend `FilterSpec` and templates. `_build_spec` is the single construction point, so templates can be folded in there.

## Self-Check: PASSED
- All key files exist on disk.
- Commits `d3fb1be`, `5e821b5`, `1541985` and `a719656` are ancestors of HEAD.
- `uv run pytest -q -m "not benchmark"`: 246 passed, 1 skipped.
- `uv run ruff check . && uv run ruff format --check .`: clean.

---
*Phase: 02-precise-filters-preview*
*Completed: 2026-10-15*
