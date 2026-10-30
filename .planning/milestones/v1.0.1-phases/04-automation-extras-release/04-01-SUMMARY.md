---
phase: 04-automation-extras-release
plan: 01
subsystem: entities
tags: [home-assistant, sensor, timestamp, dispatcher, async_track_point_in_utc_time, translations]

requires:
  - phase: 01-first-filtered-calendar
    provides: XmltvCalendarEntity, MatchIndex, subentry topology, update listener
  - phase: 02-precise-filters-preview
    provides: render.template_values / EventTemplates, in-place subentry edits, T-02-01 invalid-pattern handling
provides:
  - Sensor platform with NextMatchSensor (one per calendar subentry, on the calendar's device)
  - MatchIndex.next_after(now)
  - calendar.device_info(subentry_id, title), calendar.signal_matches(subentry_id)
  - XmltvCalendarEntity.next_match(now) and describe_match(programme) (keys incl. uid, reused by 04-04)
  - XmltvRuntimeData.add_entities as dict[Platform, callback], XmltvRuntimeData.sensors
  - sensor.async_add_subentry_sensors(runtime, entry, subentry) (04-05 adds LastFetchSensor here)
  - entity.sensor.next_match name and state attribute names (en + de)
affects: [04-04 new-match event, 04-05 last-fetch sensor, 04-06 blueprint, release docs]

actuals:
  tokens: 6722
  tasks: 3
  commits: 6
plan_head_before: 2c4ea4636812aec33b290276f35c462cb61c3ec0
plan_head_after: 66c996f2669f59987a7230ad24ac502ff663f7b5

tech-stack:
  added: []
  patterns:
    - "Calendar -> sensor change notification through a per-subentry dispatcher signal (signal_matches)"
    - "Sensor re-arms async_track_point_in_utc_time at the next match start on every recompute"
    - "Per-platform add_entities callbacks so the update listener can add entities of every platform later"

key-files:
  created:
    - custom_components/xmltv_calendar/sensor.py
    - tests/test_sensor.py
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-01-red*.json / *.xml
  modified:
    - custom_components/xmltv_calendar/calendar.py
    - custom_components/xmltv_calendar/__init__.py
    - custom_components/xmltv_calendar/data.py
    - custom_components/xmltv_calendar/xmltv/window.py
    - custom_components/xmltv_calendar/translations/en.json
    - custom_components/xmltv_calendar/translations/de.json
    - tests/test_init.py
    - tests/xmltv/test_window.py

key-decisions:
  - "Next-match sensor value and attributes come from one next_after lookup; no match (or no calendar yet) means state unknown and no attributes, unavailable only without source data (D-01, D-02)"
  - "The start timer callback recomputes with max(utcnow, fired point), so a timer firing slightly early still moves on to the following match"
  - "Template-only edits signal the sensor only on the branch that does not refilter (uncompilable stored pattern); valid edits already refilter and signal"

patterns-established:
  - "Sensor platform per subentry: async_add_subentry_sensors records the subentry in runtime.sensors and adds through runtime.add_entities[Platform.SENSOR]"

requirements-completed: [AUT-03, CFG-04]

coverage:
  - id: D1
    description: "Each calendar has a Next programme timestamp sensor on its device showing the start of the next match that has not started (unique ID <subentry>_next_match, enabled by default)"
    requirement: AUT-03
    verification:
      - kind: integration
        ref: "tests/test_sensor.py#test_next_match_sensor_shows_next_start"
        status: pass
      - kind: integration
        ref: "tests/test_sensor.py#test_sensor_shares_the_calendar_device"
        status: pass
      - kind: integration
        ref: "tests/test_sensor.py#test_airing_match_is_not_next"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_window.py#test_next_after"
        status: pass
    human_judgment: false
  - id: D2
    description: "Attributes title, summary, channel, channel_id, start, end, subtitle, episode, description; description/subtitle/episode excluded from the recorder; unknown without a future match; ties resolved in feed order"
    requirement: AUT-03
    verification:
      - kind: integration
        ref: "tests/test_sensor.py#test_next_match_attributes"
        status: pass
      - kind: integration
        ref: "tests/test_sensor.py#test_match_texts_are_not_recorded"
        status: pass
      - kind: integration
        ref: "tests/test_sensor.py#test_no_future_match_is_unknown_but_available"
        status: pass
      - kind: integration
        ref: "tests/test_sensor.py#test_same_start_picks_feed_order"
        status: pass
      - kind: integration
        ref: "tests/test_sensor.py#test_invalid_stored_pattern_gives_unknown"
        status: pass
      - kind: integration
        ref: "tests/test_sensor.py#test_sensor_unavailable_without_data"
        status: pass
    human_judgment: false
  - id: D3
    description: "Sensor follows time (moves on at match start), new feed data, filter and template edits, calendars added later and removed calendars, without reload or download"
    requirement: AUT-03
    verification:
      - kind: integration
        ref: "tests/test_sensor.py#test_sensor_moves_on_at_match_start"
        status: pass
      - kind: integration
        ref: "tests/test_sensor.py#test_sensor_follows_new_feed_data"
        status: pass
      - kind: integration
        ref: "tests/test_sensor.py#test_sensor_follows_filter_and_template_edits"
        status: pass
      - kind: integration
        ref: "tests/test_sensor.py#test_template_edit_with_invalid_pattern_reaches_sensor"
        status: pass
      - kind: integration
        ref: "tests/test_sensor.py#test_calendar_added_later_gets_a_sensor"
        status: pass
      - kind: integration
        ref: "tests/test_init.py#test_remove_calendar_removes_entity_and_device"
        status: pass
    human_judgment: false
  - id: D4
    description: "Sensor name Next programme / Nächste Sendung and attribute names in English and German; German installs get sensor.<calendar>_nachste_sendung"
    requirement: CFG-04
    verification:
      - kind: integration
        ref: "tests/test_sensor.py#test_german_entity_ids"
        status: pass
      - kind: unit
        ref: "tests/test_translations.py"
        status: pass
    human_judgment: true
    rationale: "Plan human-check: on ha-dev, the device page shows the sensor and its attribute names, and the German UI shows Nächste Sendung; attribute-name rendering in the frontend is not asserted by any test"

duration: 8min
completed: 2026-10-21
status: complete
---

# Phase 4 Plan 01: Next-Match Sensor Summary

**Per-calendar "Next programme" timestamp sensor fed by a dispatcher signal from the calendar and a timer at the next match start, with D-03 attributes (texts kept out of the recorder) and English/German names.**

## Performance

- **Duration:** about 8 min
- **Started:** 2026-10-21T08:25:15Z
- **Completed:** 2026-10-21T08:33Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 10 code/test files (plus RED evidence)

## Accomplishments

- `sensor.py` (new): `NextMatchSensor` (`CoordinatorEntity` + `SensorEntity`, `SensorDeviceClass.TIMESTAMP`, translation key `next_match`, unique ID `<subentry_id>_next_match`, `_unrecorded_attributes = {"description", "subtitle", "episode"}`), `async_add_subentry_sensors`, `PARALLEL_UPDATES = 0`.
- `MatchIndex.next_after(now)`: `bisect_right` on the starts, so a match starting at `now` is no longer next, and equal starts keep the stable input order.
- `calendar.py`: `device_info()` helper (the only `DeviceInfo(` construction now), `signal_matches()`, `next_match()`, `describe_match()` (also returns `uid` for 04-04). The calendar sends the signal after every refilter and after a template-only state write.
- `__init__.py`: `PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]`. The update listener checks each platform's callback separately, adds calendars and sensors for new subentries, and drops removed subentries from `runtime.sensors`.
- Translations: `entity.sensor.next_match` name plus nine state attribute names in `en.json` and `de.json`, in the same key order.

## Task Commits

1. **Task 1: Tracer, next-match sensor end to end.** RED `53a9ac7`, GREEN `8695275`
2. **Task 2: Attributes, recorder exclusion, empty and tie cases, localized IDs.** RED `9c72e5c`, GREEN `24cce9d`
3. **Task 3: Sensor follows time, feed, edits, added/removed calendars.** RED `b32399c`, GREEN `66c996f`

No refactor commits were needed.

## TDD Gate Compliance

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 1 (tracer) | `53a9ac7` test(04-01) | `8695275` feat(04-01) | none |
| 2 | `9c72e5c` test(04-01) | `24cce9d` feat(04-01) | none |
| 3 | `b32399c` test(04-01) | `66c996f` feat(04-01) | none |

RED evidence (every record classifies as `RED_EVIDENCE_OK (target_test_failed)` and carries a `semanticAssessment`):

- `04-01-red.json`, target `test_next_match_sensor_shows_next_start`: `assert state is not None` failed because there was no sensor platform yet. The integration set up cleanly, with no collection errors.
- `04-01-red-2-attributes.json`, target `test_next_match_attributes`: every D-03 key read `missing`. The sensor existed with the correct state.
- `04-01-red-2-recorder.json`, target `test_match_texts_are_not_recorded`: `unrecorded_attributes` held only the sensor component's `options`.
- `04-01-red-3-timer.json`, target `test_sensor_moves_on_at_match_start`: after stepping to 10:00Z the state still showed the race start, because no timer existed.
- `04-01-red-3-added.json`, target `test_calendar_added_later_gets_a_sensor`: the flow created the calendar, but the listener added no sensor.
- `04-01-red-3-template.json`, target `test_template_edit_with_invalid_pattern_reaches_sensor`: the summary kept the old template. See deviation 2.

Regression guards that were already green after Task 1 (listed as the plan requires): `test_next_after[*]` (7 cases), `test_airing_match_is_not_next`, `test_no_future_match_is_unknown_but_available`, `test_german_entity_ids[de|en]`. After Task 2 the same applies to `test_sensor_follows_new_feed_data`, `test_sensor_follows_filter_and_template_edits`, `test_invalid_stored_pattern_gives_unknown`, `test_sensor_unavailable_without_data`, and the sensor assertions in `test_remove_calendar_removes_entity_and_device`. In each case the Task 1 dispatcher signal or HA's subentry removal already delivered the behaviour.

## Decisions Made

- Value and attributes are computed together in `_recompute()`. A missing calendar (sensor platform set up first, Pitfall 1) or a missing match gives `None` for both.
- `_handle_start(point)` recomputes with `max(utcnow, point)`. A timer that fires a few microseconds early cannot re-select the match that is just starting.
- The timer is cancelled through `async_on_remove` and before every recompute, so there is never more than one timer per sensor.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_preexisting_subentries_get_one_entity_each` counted all entities**
- **Found during:** Task 1 (GREEN verify)
- **Issue:** The test expected 3 registry entries for 3 subentries. With the sensor platform there are 6 (RESEARCH Pitfall 2 anticipates updating such counts).
- **Fix:** The test now counts calendars and sensors separately and checks that sensor unique IDs are `<subentry>_next_match` with the matching `config_subentry_id`.
- **Files modified:** tests/test_init.py
- **Commit:** `8695275`

**2. [Fail-fast rule 1 - Unexpected GREEN] The planned template-edit RED target was already green**
- **Found during:** Task 3 (RED)
- **Issue:** The plan assumed template-only edits send no signal. In fact `async_apply_subentry` rebuilds the filter on every data change and refilters whenever the pattern compiles, and the refilter already sends `signal_matches`. So `test_sensor_follows_filter_and_template_edits` passed before any Task 3 code existed, and its first RED record was `INVALID_RED no_target_test_failure`.
- **Fix:** I added `test_template_edit_with_invalid_pattern_reaches_sensor`. It reaches the only non-refiltering branch, an edit whose stored pattern does not compile together with a new title template. That branch failed RED as expected and was fixed by the planned `async_dispatcher_send` in the `elif write_state` branch. `test_sensor_follows_filter_and_template_edits` stays as a regression guard. `04-01-red-3-template.json` now holds the valid record from the rerun, and its `semanticAssessment` documents the first attempt.
- **Files modified:** tests/test_sensor.py
- **Commit:** `b32399c`

**3. [Process] Commits on `main`**
- `git.base-branch --is-protected main` reports `true`. The orchestrator dispatched this executor sequentially on the main working tree (`branching_strategy: none`) with normal commits. Plans 01-01 to 03-10 did the same.

**Total deviations:** 2 auto-handled (1 test-count bug, 1 unexpected-green RED retarget) plus 1 process note. **Impact:** none on scope. The planned code changes were made as specified.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. No new surface beyond the plan's threat model. T-04-01 is mitigated through `_unrecorded_attributes` and verified by `test_match_texts_are_not_recorded`. T-04-03 is mitigated because a missing calendar reads as no next match, and the sensor recomputes when the signal arrives.

## Verification

- `uv run pytest -q -m "not benchmark"`: 843 passed, 1 skipped, 4 deselected.
- `uv run ruff check . && uv run ruff format --check .`: all checks passed, 65 files already formatted.
- `podman run --rm -v "$PWD":/github/workspace:ro,Z ghcr.io/home-assistant/hassfest`: Integrations 1, Invalid integrations 0.
- Acceptance greps: `"next_match"` appears once in en.json and once in de.json. `Platform.SENSOR` is present. `def next_after` is present. `DeviceInfo(` appears once in calendar.py. `_unrecorded_attributes` is present. `Nächste Sendung` appears once. `async_track_point_in_utc_time` is present. `def async_add_subentry_sensors` is present. `add_entities is None` appears 0 times.
- Tracer feedback gate (interactive, `human_verify_mode: end-of-phase`, automated-only verify): Task 1 verify passed again before expansion.
- Human check (deferred to end of phase): on ha-dev, the device page shows "Next programme" with title, channel, start and end attributes, and the German UI shows "Nächste Sendung".

## Next Phase Readiness

Ready for 04-02. `describe_match` (including `uid`) and `async_add_subentry_sensors` are in place for 04-04 (new-match event) and 04-05 (last-fetch sensor).

## Self-Check: PASSED
