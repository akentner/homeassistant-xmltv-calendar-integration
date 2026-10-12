---
phase: 01-first-filtered-calendar
plan: 01
subsystem: infra
tags: [home-assistant, config-flow, config-subentry, data-update-coordinator, calendar, xmltv, iterparse, uv, ruff, pytest]

requires: []
provides:
  - "Loadable xmltv_calendar integration: URL source config flow (menu -> url -> name), calendar subentry flow, one calendar entity and device per subentry"
  - "XmltvCoordinator: one download plus executor parse per source, shared by all calendars"
  - "Pure xmltv/ library contracts: model, timeparse, normalize, parser, filter, render, window (signatures frozen for 01-02..01-08)"
  - "Single diffing update listener (_async_entry_updated) and XmltvRuntimeData/XmltvConfigEntry"
  - "Test harness: setup_xmltv factory, forbid_loop_io, berlin_tz, FEED_URL, hass-free tests/xmltv package"
  - "Pinned dev toolchain: pytest-homeassistant-custom-component 0.13.372 (HA 2026.10.1), ruff 0.17.0, uv.lock"
affects: [01-02, 01-03, 01-04, 01-05, 01-06, 01-07, 01-08, 01-09, 01-10]

actuals:
  tokens: 11183   # chars/4 over the 26 authored files (44,733 chars); the generated uv.lock (564,500 chars, ~141k) is excluded
  tasks: 3
  commits: 3
plan_head_before: 90eea707463f3cfd8138af8d59d7553d79fcde43
plan_head_after: 2f5a4511ea1bd445e340b5b52145baf87a661e84

tech-stack:
  added: [pytest-homeassistant-custom-component==0.13.372, ruff==0.17.0, homeassistant==2026.10.1 (dev, via phcc)]
  patterns:
    - "Source = config entry with coordinator in runtime_data; calendar = config subentry with its own device"
    - "Exactly one update listener that diffs (data, options) against a setup snapshot"
    - "CPU work (parse, filter) only via hass.async_add_executor_job; refilter guarded by a generation counter"
    - "Pure xmltv/ package without Home Assistant imports; missing stop passed to normalize as stop == start"
    - "Logs and exception messages name only the source host"

key-files:
  created:
    - pyproject.toml
    - uv.lock
    - .ruff.toml
    - custom_components/xmltv_calendar/manifest.json
    - custom_components/xmltv_calendar/__init__.py
    - custom_components/xmltv_calendar/const.py
    - custom_components/xmltv_calendar/data.py
    - custom_components/xmltv_calendar/source.py
    - custom_components/xmltv_calendar/coordinator.py
    - custom_components/xmltv_calendar/calendar.py
    - custom_components/xmltv_calendar/config_flow.py
    - custom_components/xmltv_calendar/translations/en.json
    - custom_components/xmltv_calendar/xmltv/__init__.py
    - custom_components/xmltv_calendar/xmltv/model.py
    - custom_components/xmltv_calendar/xmltv/timeparse.py
    - custom_components/xmltv_calendar/xmltv/normalize.py
    - custom_components/xmltv_calendar/xmltv/parser.py
    - custom_components/xmltv_calendar/xmltv/filter.py
    - custom_components/xmltv_calendar/xmltv/render.py
    - custom_components/xmltv_calendar/xmltv/window.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/xmltv/__init__.py
    - tests/xmltv/conftest.py
    - tests/fixtures/basic.xml
    - tests/test_tracer.py
  modified:
    - .gitignore

key-decisions:
  - "Task 1: approved (0.13.372 / 0.17.0): pytest-homeassistant-custom-component==0.13.372 and ruff==0.17.0, verified on PyPI by the orchestrator before dispatch"
  - "iot_class cloud_polling: most sources are internet feeds, same as core remote_calendar"
  - "Parser hands a missing or unparsable stop to normalize as stop == start; normalize treats any stop <= start as missing (keeps Programme.stop a non-optional datetime)"
  - "keep_after drop runs after normalization so inferred stops are respected"
  - "URL step rejects non-http(s) URLs with invalid_url; name and subentry steps reject blank names with name_required; subentry flow aborts with source_not_loaded when the entry is not LOADED"

patterns-established:
  - "Flow steps: menu -> source-type step -> shared async_step_name (plan 01-07 reuses it for files)"
  - "Subentry entities: platform stores async_add_entities in runtime_data.add_entities; listener adds later subentries with config_subentry_id"
  - "TC-rule imports go under TYPE_CHECKING (Python 3.14 deferred annotations make this safe, also in dataclasses)"

requirements-completed: [SRC-01, SRC-04, FLT-01, FLT-02, EVT-02, AUT-01, AUT-02, CFG-01]

coverage:
  - id: D1
    description: "URL source config flow: menu offers url, url step leads to a name step pre-filled with the host, entry created with data {source_type, url} and options {refresh_hours}, entry LOADED"
    requirement: "SRC-01"
    verification:
      - kind: integration
        ref: "tests/test_tracer.py#test_url_source_to_calendar_events"
        status: pass
    human_judgment: false
  - id: D2
    description: "Calendar subentry offers channel IDs from the loaded feed and is added without another HTTP request"
    requirement: "FLT-01"
    verification:
      - kind: integration
        ref: "tests/test_tracer.py#test_url_source_to_calendar_events"
        status: pass
    human_judgment: false
  - id: D3
    description: "calendar.formel_1 is on while a programme airs, location = channel display name"
    requirement: "AUT-02"
    verification:
      - kind: integration
        ref: "tests/test_tracer.py#test_url_source_to_calendar_events"
        status: pass
    human_judgment: false
  - id: D4
    description: "calendar.get_events returns only the selected channel's programmes with summary '<display-name>: <title>', location and tz-aware start/end"
    requirement: "EVT-02"
    verification:
      - kind: integration
        ref: "tests/test_tracer.py#test_url_source_to_calendar_events"
        status: pass
    human_judgment: false
  - id: D5
    description: "Pinned dev toolchain locked and installed; Ruff clean"
    verification:
      - kind: other
        ref: "uv sync --locked && uv run ruff check . && uv run ruff format --check ."
        status: pass
    human_judgment: false
  - id: D6
    description: "Translations render correctly in the real HA frontend (menu, url, name and Add calendar forms)"
    verification: []
    human_judgment: true
    rationale: "No frontend in the test harness; verified on the ha-dev container in plan 01-09"

duration: 6min
completed: 2026-10-13
status: complete
---

# Phase 1 Plan 01: Walking Skeleton Summary

**A URL source config flow plus one calendar subentry turns an XMLTV feed into a live `calendar.*` entity. The feed is downloaded once per source and parsed in the executor with stdlib `iterparse`. Proven end to end by a flow-only tracer test on HA 2026.10.1.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-12T22:32:06Z
- **Completed:** 2026-10-12T22:38:29Z
- **Tasks:** 3 (Task 1 resolved before dispatch)
- **Files modified:** 27 (26 authored + uv.lock)

## Accomplishments

- The source flow (menu, url, name pre-filled with the host) creates an entry. That entry sets up `XmltvCoordinator`, which fetches through HA's shared aiohttp session and parses in the executor.
- Calendar subentries reuse the loaded data for the channel picker and add their entity in place through the single diffing update listener. There is no re-download (verified by `aioclient_mock.call_count`).
- `XmltvCalendarEntity` gets one device per subentry. It refilters in the executor behind a generation counter, computes `event` live from `dt_util.now()`, and returns end-inclusive `get_events` results.
- The pure `xmltv/` library has every contract from the interfaces block, with no Home Assistant imports.
- The harness (`setup_xmltv`, `forbid_loop_io`, `berlin_tz`, hass-free `tests/xmltv/`) and the pinned toolchain are ready for wave 2.

## Task Commits

1. **Task 1: Package legitimacy gate (T-01-SC)**: resolved before dispatch, answer "approved"; no commit
2. **Task 2: Install approved pins and dev harness**: `c84ae04` (chore)
3. **Task 3: Tracer, URL source to calendar events**: `ddbd3e3` (test, RED), `2f5a451` (feat, GREEN)

## Files Created/Modified

- `pyproject.toml`, `uv.lock`, `.ruff.toml`, `.gitignore`: uv project, exact dev pins, Ruff config copied from the sibling, merged ignores
- `custom_components/xmltv_calendar/manifest.json`: domain `xmltv_calendar`, `cloud_polling`, `requirements: []`
- `__init__.py`: setup/unload plus `_async_entry_updated` (the diffing listener)
- `const.py`, `data.py`: config keys and constants, `XmltvRuntimeData` and `XmltvConfigEntry`
- `source.py`: `async_fetch_url`, `SourceError` and `SourceUnavailableError`. Logs name only the host.
- `coordinator.py`: `XmltvCoordinator` with translated `UpdateFailed` (`unable_to_fetch`, `invalid_feed`)
- `calendar.py`: platform setup per subentry and `XmltvCalendarEntity`
- `config_flow.py`: `XmltvConfigFlow` (user menu, url, name) and `CalendarSubentryFlow`
- `translations/en.json`: config, config_subentries.calendar, exceptions
- `xmltv/{model,timeparse,normalize,parser,filter,render,window}.py`: pure library
- `tests/conftest.py`, `tests/xmltv/conftest.py`, `tests/fixtures/basic.xml`, `tests/test_tracer.py`: harness and tracer

## TDD Gate Compliance

- **RED** `ddbd3e3`: `tests/test_tracer.py::test_url_source_to_calendar_events` failed at `assert result["type"] is FlowResultType.MENU` (got ABORT from the placeholder flow). JUnit report classified `RED_EVIDENCE_OK` (`target_test_failed`). Semantic assessment: the target test was collected, ran and failed on the planned flow-result assertion. This was not an import, collection or fixture fault.
- **GREEN** `2f5a451`: the same test passes, `uv run pytest -q` reports 1 passed.
- **REFACTOR**: none needed. Ruff's TC fixes were applied before the GREEN commit.

## Decisions Made

- **Task 1: approved (0.13.372 / 0.17.0).** The pins are pytest-homeassistant-custom-component==0.13.372 (Matthew Flamm, requires homeassistant==2026.10.1) and ruff==0.17.0 (Astral). The orchestrator checked both against live PyPI metadata before dispatch.
- **iot_class `cloud_polling`.** Most sources are internet feeds, the same as core `remote_calendar`.
- **Missing stop encoding.** The parser passes a missing or unparsable stop as `stop == start`, and `normalize_programmes` treats any `stop <= start` as missing. This keeps the frozen `Programme.stop: datetime` contract, and it matches the D-12/Pitfall 6 rule that `stop <= start` needs inference.
- **`keep_after` drop runs after normalization,** so inferred stops (and 01-02's next-start inference) are respected.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Placeholder config_flow.py in the RED commit**
- **Found during:** Task 3, Step A
- **Issue:** The RED scaffold the plan listed had no `config_flow.py`. Without it, `flow.async_init` raises `UnknownHandler`, and the plan requires RED to fail on a flow-result assertion, not on an error.
- **Fix:** Added a placeholder `XmltvConfigFlow` that aborts. RED then failed on `assert result["type"] is FlowResultType.MENU`. GREEN replaced the file.
- **Files modified:** custom_components/xmltv_calendar/config_flow.py
- **Committed in:** ddbd3e3 (RED), replaced in 2f5a451

**2. [Rule 2 - Missing critical] Input validation in the flows**
- **Found during:** Task 3, Step B
- **Issue:** The plan's flows accepted any URL and blank names, and the subentry flow read `runtime_data` without checking that the entry was loaded. That would crash with AttributeError for an entry in SETUP_RETRY.
- **Fix:** The URL step rejects non-http(s) URLs or URLs without a host (`invalid_url`). The name step and the subentry step reject blank names (`name_required`). The subentry flow aborts with `source_not_loaded` unless the entry is LOADED, per the RESEARCH skeleton. Matching en.json strings were added.
- **Files modified:** config_flow.py, translations/en.json
- **Committed in:** 2f5a451

**3. [Rule 2 - Missing critical] Pitfall 6 guard in calendar reads**
- **Found during:** Task 3, Step B
- **Issue:** A single invalid programme raising `HomeAssistantError` in `CalendarEvent` would fail the whole `get_events` call.
- **Fix:** Each event is constructed inside `try/except HomeAssistantError`, which skips the programme and logs at debug level.
- **Files modified:** calendar.py
- **Committed in:** 2f5a451

**4. [Rule 2 - Security] aiohttp error text kept out of logs and messages**
- **Found during:** Task 3, Step B (threat T-01-01)
- **Issue:** aiohttp exception strings can embed the full request URL, including its query string.
- **Fix:** `source.py` logs and raises with the host and the exception type name only, and raises `from None`.
- **Files modified:** source.py
- **Committed in:** 2f5a451

---

**Total deviations:** 4 auto-fixed (1 blocking, 3 missing critical/security)
**Impact on plan:** All four are small correctness or security additions inside planned files. No interface in the contracts block changed, and there is no scope creep.

## Issues Encountered

- Commits landed on `main`, which the GSD protected-branch check reports as protected. The orchestrator dispatched this executor sequentially on the main working tree (`branching_strategy: none`, no remote) and explicitly told it to make normal commits there. All earlier planning commits are on `main` as well.

## Known Stubs

These are intentional. Each is assigned to a later wave-2 plan, and none blocks this plan's goal.

| File | Line | Stub | Resolved by |
|------|------|------|-------------|
| custom_components/xmltv_calendar/xmltv/render.py | 24 | `uid=None` | 01-02 (stable uid). Recorded in .planning/WINDOWS.md |
| custom_components/xmltv_calendar/xmltv/timeparse.py | 7 | Only `YYYYMMDDhhmmss +HHMM` | 01-02 |
| custom_components/xmltv_calendar/xmltv/normalize.py | 26 | No next-start inference or dedup | 01-02 |
| custom_components/xmltv_calendar/xmltv/filter.py | 57 | Channels only (no regex, include or exclude) | 01-03 |
| custom_components/xmltv_calendar/xmltv/window.py | 1 | Linear scans, no cap | 01-04 |
| custom_components/xmltv_calendar/source.py | 29 | No size cap or gzip | 01-05 |

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- Wave 2 (01-02 to 01-05) can build on the contracts without touching each other's files.
- The `forbid_loop_io` fixture is available. A caplog assertion for T-01-01 lands in 01-05.

## Self-Check: PASSED

- All 26 key files exist on disk.
- Commits c84ae04, ddbd3e3 and 2f5a451 are ancestors of HEAD (3 commits since 90eea70).
- `uv run pytest -q` reports 1 passed. `ruff check` and `ruff format --check` are clean. `uv sync --locked` succeeds.

---
*Phase: 01-first-filtered-calendar*
*Completed: 2026-10-13*
