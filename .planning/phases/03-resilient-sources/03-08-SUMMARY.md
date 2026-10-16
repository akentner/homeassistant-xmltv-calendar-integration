---
phase: 03-resilient-sources
plan: 08
subsystem: config-flow
tags: [home-assistant, options-flow, config-entries, voluptuous, translations, tdd]

requires:
  - phase: 03-resilient-sources
    provides: "03-01 SourceOptions contract (from_mapping/as_options), 03-02/03-05 diffing listener reload from fresh cache, 03-06 shared setup builders (_settings_fields, _settings_from_input, _schedule_schema)"
provides:
  - "XmltvOptionsFlow (plain OptionsFlow): init (refresh mode + collapsed timezone section) -> schedule (one field) -> complete option contract"
  - "XmltvConfigFlow.async_get_options_flow"
  - "_options_to_store: full option contract that keeps a valid daily time while interval mode is active"
  - "options.step.init / options.step.schedule / options.error.invalid_time translations (en + de)"
  - "tests/test_options_flow.py (7 tests, 10 cases)"
affects: [phase-03-uat, phase-03-verification, phase-04]

actuals:
  tokens: 8896
  tasks: 2
  commits: 4
plan_head_before: d54b8b168e9eb178a563e007d928075790330602
plan_head_after: 57073ac6fae355032556cd4e9ac357bf57a9adee

tech-stack:
  added: []
  patterns:
    - "Options flow reuses the setup schema builders; the save writes entry.options only and the single diffing update listener reloads"
    - "Inactive schedule field survives a mode switch in storage (refresh_hours always, refresh_time kept when valid)"

key-files:
  created:
    - tests/test_options_flow.py
    - .planning/phases/03-resilient-sources/tdd-evidence/03-08-red.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-08-red.xml
    - .planning/phases/03-resilient-sources/tdd-evidence/03-08-red-2-switching.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-08-red-2.xml
  modified:
    - custom_components/xmltv_calendar/config_flow.py
    - custom_components/xmltv_calendar/translations/en.json
    - custom_components/xmltv_calendar/translations/de.json

key-decisions:
  - "An interval source keeps its last valid daily time in entry.options (_options_to_store), so a later switch back to daily pre-fills it; SourceOptions.from_mapping ignores the key outside daily mode, so schedule and diagnostics are unaffected"
  - "The options flow is a plain OptionsFlow with no own reload logic: async_create_entry(data=...) replaces entry.options and the existing diffing listener reloads once; identical values cause no reload"
  - "Options translations copy the setup texts for refresh_mode, the timezone section and the schedule step, plus a description that the save reloads from the cache and that URL/file cannot be changed here"

patterns-established:
  - "Options flow testing: hass.config_entries.options.async_init/async_configure plus a monkeypatched async_schedule_reload spy that still calls the original"

requirements-completed: [CFG-02, SRC-05, SRC-10]

coverage:
  - id: D1
    description: "Switching a source to daily 18:15 in its options stores the full contract, reloads once from the cache without a download and plans 18:15 local"
    requirement: CFG-02
    verification:
      - kind: integration
        ref: "tests/test_options_flow.py#test_options_flow_switch_to_daily"
        status: pass
    human_judgment: false
  - id: D2
    description: "Pre-Phase-3 entries pre-fill defaults (interval, stored hours, UTC, 0 min) and the first save writes the full contract with one cache reload"
    requirement: SRC-05
    verification:
      - kind: integration
        ref: "tests/test_options_flow.py#test_options_prefill_for_pre_phase3_entry"
        status: pass
    human_judgment: false
  - id: D3
    description: "Switching modes pre-fills the previously stored hours, and a later switch back to daily suggests the previously stored time"
    requirement: SRC-05
    verification:
      - kind: integration
        ref: "tests/test_options_flow.py#test_switching_back_prefills_previous_values"
        status: pass
    human_judgment: false
  - id: D4
    description: "Changing the timezone interpretation in the options flow shifts the events without a download"
    requirement: SRC-10
    verification:
      - kind: integration
        ref: "tests/test_options_flow.py#test_options_timezone_change_shifts_events_without_download"
        status: pass
    human_judgment: false
  - id: D5
    description: "The options flow has no URL/path field and never changes entry.data; identical values do not reload; hour and offset bounds are enforced"
    requirement: CFG-02
    verification:
      - kind: integration
        ref: "tests/test_options_flow.py#test_options_flow_has_no_url_or_path"
        status: pass
      - kind: integration
        ref: "tests/test_options_flow.py#test_identical_options_do_not_reload"
        status: pass
      - kind: integration
        ref: "tests/test_options_flow.py#test_options_bounds_are_enforced_for_hours"
        status: pass
      - kind: integration
        ref: "tests/test_options_flow.py#test_options_bounds_are_enforced_for_offset"
        status: pass
    human_judgment: false
  - id: D6
    description: "Options texts are served in English and German with key parity, and hassfest accepts the translations"
    requirement: CFG-02
    verification:
      - kind: integration
        ref: "tests/test_translations.py"
        status: pass
      - kind: other
        ref: "podman run --rm -v \"$PWD\":/github/workspace:ro,Z ghcr.io/home-assistant/hassfest"
        status: pass
    human_judgment: false
  - id: D7
    description: "Hands-on Phase 3 UAT walkthrough on ha-dev (12 steps: setup with progress and schedule, cache reuse across restart, options switch to daily, timezone edit, manual refresh with 304, real-feed ETag/Last-Modified check, diagnostics redaction, Repairs, German UI, logs)"
    verification: []
    human_judgment: true
    rationale: "Real frontend rendering, the user's real feed (validator support, RESEARCH A8) and live log inspection are not covered by phcc tests; queued for the end-of-phase UAT batch (human_verify_mode end-of-phase)"

duration: 7min
completed: 2026-10-16
status: complete
---

# Phase 3 Plan 08: Source Options Flow Summary

**Plain OptionsFlow (init -> schedule) built from the setup builders lets a source's refresh mode, interval or daily time and timezone settings be edited later. A save writes the complete option contract, keeps the inactive daily time, and reloads the source once from its cache through the existing diffing listener.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-10-16T11:18:25Z
- **Completed:** 2026-10-16T11:25:30Z
- **Tasks:** 2
- **Files modified:** 8 (4 source/test, 4 RED evidence)

## Accomplishments

- `XmltvOptionsFlow(OptionsFlow)` with `async_step_init` (refresh mode + collapsed timezone section, pre-filled through `SourceOptions.from_mapping(self.config_entry.options)`) and `async_step_schedule` (exactly one field, `invalid_time` guard). It is registered through `XmltvConfigFlow.async_get_options_flow`. There is no `OptionsFlowWithReload`, and `__init__` never touches `self.config_entry`.
- Saving replaces `entry.options` with the complete contract. `_async_entry_updated` sees the diff and schedules one reload, which re-parses the fresh disk cache (no download) and applies the new schedule and timezone options. Saving identical values on a full-contract entry neither updates the entry nor reloads it.
- `_options_to_store` keeps a valid daily time while interval mode is active, so daily -> interval -> daily pre-fills 18:15 again across saves.
- Options texts in en.json and de.json (`options.step.init` with `sections.timezone`, `options.step.schedule`, `options.error.invalid_time`), with the same key order. `test_translations.py` and hassfest are green.
- Phase gate: full suite 794 passed / 1 skipped (pre-existing real-feed skip), benchmarks 4 passed / 1 skipped, Ruff check + format clean, hassfest `Invalid integrations: 0` (exit 0). ha-dev was restarted with this code: port 18123 answers 200, and the log has no xmltv_calendar errors.

## Task Commits

1. **Task 1 (tracer): switch a source to "daily at 18:15" in its options**
   - RED `c1eed7d`: test(03-08): add failing test for switching a source to daily in its options
   - GREEN `31f1773`: feat(03-08): add source options flow for schedule and timezone settings
   - Tracer gate (interactive, end-of-phase, automated-only verify): verify re-run passed, so expansion went ahead
2. **Task 2: pre-fill, mode switching, timezone edits, no URL field, no needless reload; phase gate**
   - RED `35b0cfc`: test(03-08): add options flow pre-fill, switching, timezone and bounds tests
   - GREEN `57073ac`: feat(03-08): keep the inactive daily time when a source switches to interval

No REFACTOR commits (nothing to clean up).

## TDD Gate Compliance

| Cycle | RED | GREEN | Evidence |
|-------|-----|-------|----------|
| Task 1 | `c1eed7d` | `31f1773` | `03-08-red.json`: RED_EVIDENCE_OK (junit) |
| Task 2 | `35b0cfc` | `57073ac` | `03-08-red-2-switching.json`: RED_EVIDENCE_OK (junit) |

- **RED 1:** `test_options_flow_switch_to_daily` failed inside the test body with `UnknownHandler` from the ConfigFlow base `async_get_options_flow`. Setup had completed (one download, calendar.test registered). Semantic assessment: this is the planned reason (no options flow), not a fixture, import or collection fault.
- **RED 2:** In the Task 2 run, 9 of 10 cases already passed after Task 1 (shared builders, listener diff, selector bounds), so they are regression coverage. The target `test_switching_back_prefills_previous_values` failed on the planned assertion, `None == {'suggested_value': '18:15:00'}`, in the second options flow: the interval save had dropped the daily time. Semantic assessment: the target executed through both flows and failed for the intended reason.

## Files Created/Modified

- `custom_components/xmltv_calendar/config_flow.py`: `_options_to_store`, `XmltvOptionsFlow`, `XmltvConfigFlow.async_get_options_flow`, `OptionsFlow` import
- `custom_components/xmltv_calendar/translations/en.json`, `de.json`: `options` block after `config_subentries`
- `tests/test_options_flow.py`: options flow end-to-end, pre-fill, switching, timezone change, no URL/path, identical save, bounds
- `.planning/phases/03-resilient-sources/tdd-evidence/03-08-red*.{json,xml}`: RED evidence

## Decisions Made

- An interval source stores its last valid `refresh_time` next to the full contract (see Deviations). `from_mapping` ignores it outside daily mode, so scheduling, the listener snapshot semantics and diagnostics (which emit `as_options()`) are unchanged.
- The bounds test from the plan is split into two parametrized tests (`..._for_hours` with 0/169 in the schedule step, `..._for_offset` with -721/721 in the init section), because the two limits are rejected in different steps.
- `test_switching_back_prefills_previous_values` checks the switch back **across saves** (interval saved, then a new options flow), the case the must-have "pre-fills the previously stored hours or time" describes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The plan's literal save expression dropped the inactive daily time**
- **Found during:** Task 2 (RED for `test_switching_back_prefills_previous_values`)
- **Issue:** The plan says to store `SourceOptions.from_mapping(self._pending).as_options()` and also says the complete dict keeps the inactive field's previous value so that switching back pre-fills it (RESEARCH Pattern 8 says the same). `from_mapping` clears `refresh_time` outside daily mode, so an interval save erased the stored time and a later switch back to daily offered no suggestion.
- **Fix:** `_options_to_store(options)` returns `SourceOptions.from_mapping(options).as_options()` plus the normalized `refresh_time` when one is valid. The options flow starts its pending values from it and saves through it. `refresh_hours` was already always part of the contract.
- **Files modified:** custom_components/xmltv_calendar/config_flow.py
- **Verification:** test_options_flow.py 10/10 and the full suite are green, including the diagnostics and setup tests that compare the full contract.
- **Committed in:** 57073ac

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** This is required to meet the plan's own must-have (D-06 switching pre-fill). The stored option keys and the contract are unchanged, and no migration is needed.

## Issues Encountered

- Running pytest with `-p no:logging` (used for the RED 2 report, to keep the console readable) makes caplog-based tests error out. The RED 2 target does not use caplog. The phase-gate runs use the default plugins and are green.

## Known Stubs

None.

## User Setup Required

None. No external service configuration is required.

## UAT Walkthrough (pending human verification, end-of-phase batch)

ha-dev has already been restarted with this code (`podman restart ha-dev`; http://localhost:18123 answers 200). Enable debug logging for XMLTV Calendar on its integration page, then check each step and note the result:

1. Add integration XMLTV Calendar -> Feed URL. The form shows the URL, a refresh mode choice (interval / daily at a fixed time) and a collapsed "Timezone" section with the no-offset interpretation (UTC / Home Assistant time zone) and the offset correction in minutes.
2. Enter your real feed URL and keep the defaults. A progress indicator with the download text appears, then a step with only the refresh interval, then the name step. After saving, `podman logs ha-dev` shows exactly one download from the feed host for this setup.
3. Add a calendar to the new source. It shows events, and the log shows no second download.
4. `podman restart ha-dev`. Right after the start the calendars show events, and the log shows no download for this source at start (fresh cache).
5. Open Configure on the source, switch to "daily at a fixed time" and enter 18:15. After saving, the source reloads, the log shows no download, and the second options step only offered the time.
6. Open Configure again and set the no-offset interpretation to the Home Assistant time zone and/or an offset of -60. The calendar events shift accordingly, with no download in the log. Set the values back.
7. Developer tools -> Actions: run homeassistant.update_entity on the calendar. The log shows one request to the feed host. If the feed supports validators, a "not modified" (304) debug line follows and there is no parse.
8. On the dev box run `curl -sI <your feed URL>` and note whether ETag and/or Last-Modified are present (RESEARCH A8, STATE Phase 3 concern). If neither is present, step 7 shows a full download, and the unchanged feed is still not re-parsed (SHA-256 compare).
9. Download diagnostics for the source. The URL shows only scheme and host, the URL's token or credentials appear nowhere, and programme/channel counts, skipped_malformed, cache metadata and per-calendar match counts are present.
10. Settings -> Repairs shows no XMLTV issue for the healthy source. (Automated tests cover the 24 h persistent-failure issue; reproducing it by hand would take a day of failures.)
11. Switch the HA user language to German. The setup steps, the progress text, the schedule step, the timezone section and the options steps are all in German.
12. `podman logs ha-dev` shows no xmltv_calendar tracebacks and no "Detected blocking call" warning for xmltv_calendar during the walkthrough.

## Next Phase Readiness

- All 8 plans of Phase 3 have summaries. Next: the end-of-phase TDD review, the verifier, code review and the UAT walkthrough above (including the real-feed validator check).
- CFG-02, SRC-05 and SRC-10 are closed by this plan together with 03-01..03-06.

---
*Phase: 03-resilient-sources*
*Completed: 2026-10-16*

## Self-Check: PASSED
