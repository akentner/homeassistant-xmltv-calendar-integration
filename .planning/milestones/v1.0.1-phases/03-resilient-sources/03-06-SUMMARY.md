---
phase: 03-resilient-sources
plan: 06
subsystem: config-flow
tags: [home-assistant, config-flow, async_show_progress, data_entry_flow.section, feed-cache, translations]

requires:
  - phase: 03-resilient-sources
    provides: "03-01 SourceOptions contract (refresh_mode/refresh_hours/refresh_time/naive_timezone/offset_minutes); 03-02 FeedCache + cache-first start; 03-03 async_fetch_url -> Fetched | NotModified; 03-05 coordinator reads naive_timezone/offset_minutes"
provides:
  - "Source setup chain url -> download (progress) -> schedule -> name and file -> schedule -> name"
  - "Shared builders _settings_fields / _settings_from_input / _schedule_schema (reused by the 03-08 options flow)"
  - "Setup download seeds the disk cache in the name step (one HTTP request per added URL source)"
  - "Download errors (cannot_connect, invalid_feed, feed_too_large) return to the url form with the input kept"
  - "tests/conftest.py add_url_source / add_file_source flow helpers"
  - "source.async_probe_url removed"
affects: [03-07, 03-08, options-flow, diagnostics]

actuals:
  tokens: 15600
  tasks: 3
  commits: 6
plan_head_before: 46c704d7b6edf32fbe760f9fcfcfdd4281e90d8a
plan_head_after: c1f3e9447b24d61eaf97ac3d29f928e059ccc8ae

tech-stack:
  added: []
  patterns:
    - "Progress step: task created once with hass.async_create_task(..., eager_start=False); errors leave through async_show_progress_done(next_step_id='url') plus a stored error dict"
    - "Collapsed data_entry_flow.section for timezone settings; section values flattened before storing (section key never stored)"
    - "Cache seeded only in the final flow step, so an abandoned flow leaves no file"

key-files:
  created: []
  modified:
    - custom_components/xmltv_calendar/config_flow.py
    - custom_components/xmltv_calendar/source.py
    - custom_components/xmltv_calendar/translations/en.json
    - custom_components/xmltv_calendar/translations/de.json
    - tests/conftest.py
    - tests/test_config_flow.py
    - tests/test_tracer.py
    - tests/test_identity.py

key-decisions:
  - "03-06: SECTION_TIMEZONE = 'timezone' is a form-only key; naive_timezone and offset_minutes are stored flat, options always go through SourceOptions.from_mapping(...).as_options()"
  - "03-06: the schedule step takes the mode from the pending settings, not from SourceOptions (daily without a time reads as interval there)"
  - "03-06: a NotModified answer to the validator-less setup download counts as cannot_connect"
  - "03-06: the setup download is written to FeedCache(hass, unique_id) only in the name step, right before async_create_entry"

patterns-established:
  - "Flow tests drive source setup through tests/conftest.py add_url_source / add_file_source; both return the name-step result or any earlier form/abort"

requirements-completed: [CFG-03, SRC-05, SRC-10]

coverage:
  - id: D1
    description: "Adding a URL source shows a download progress step, then the schedule and name steps; the entry stores the full option contract and starts from the seeded cache with one HTTP request in total"
    requirement: CFG-03
    verification:
      - kind: integration
        ref: "tests/test_config_flow.py#test_url_source_end_to_end_with_progress_and_seeded_cache"
        status: pass
      - kind: integration
        ref: "tests/test_tracer.py#test_url_source_to_calendar_events"
        status: pass
    human_judgment: false
  - id: D2
    description: "Schedule step shows exactly one field: refresh hours (1..168, default 24) for interval or a time for daily; daily stores refresh_time as HH:MM"
    requirement: SRC-05
    verification:
      - kind: integration
        ref: "tests/test_config_flow.py#test_daily_mode_asks_only_for_a_time"
        status: pass
      - kind: integration
        ref: "tests/test_config_flow.py#test_refresh_out_of_bounds_is_rejected"
        status: pass
      - kind: integration
        ref: "tests/test_config_flow.py#test_refresh_default_is_24_hours"
        status: pass
    human_judgment: false
  - id: D3
    description: "url and file steps share refresh_mode and a collapsed timezone section (naive_timezone, offset_minutes -720..720) built by one builder; values stored flat"
    requirement: SRC-10
    verification:
      - kind: integration
        ref: "tests/test_config_flow.py#test_url_and_file_steps_share_settings_fields"
        status: pass
      - kind: integration
        ref: "tests/test_config_flow.py#test_timezone_section_is_stored_flat"
        status: pass
      - kind: integration
        ref: "tests/test_config_flow.py#test_offset_out_of_bounds_is_rejected"
        status: pass
      - kind: integration
        ref: "tests/test_config_flow.py#test_file_source_end_to_end"
        status: pass
    human_judgment: false
  - id: D4
    description: "Download failures return to the url form with the entered values and cannot_connect / invalid_feed / feed_too_large; logs name the host only; a retry downloads again"
    verification:
      - kind: integration
        ref: "tests/test_config_flow.py#test_unreachable_url_cannot_connect"
        status: pass
      - kind: integration
        ref: "tests/test_config_flow.py#test_http_error_cannot_connect"
        status: pass
      - kind: integration
        ref: "tests/test_config_flow.py#test_non_feed_body_is_invalid_feed"
        status: pass
      - kind: integration
        ref: "tests/test_config_flow.py#test_too_large_download_shows_feed_too_large"
        status: pass
      - kind: integration
        ref: "tests/test_config_flow.py#test_flow_download_logs_host_only"
        status: pass
      - kind: integration
        ref: "tests/test_config_flow.py#test_retry_after_download_error_downloads_again"
        status: pass
    human_judgment: false
  - id: D5
    description: "Closing the dialog during the download cancels it and writes no entry and no cache file; duplicates abort before any download"
    verification:
      - kind: integration
        ref: "tests/test_config_flow.py#test_abandoned_download_writes_no_cache"
        status: pass
      - kind: integration
        ref: "tests/test_config_flow.py#test_duplicate_source_aborts_before_download"
        status: pass
      - kind: integration
        ref: "tests/test_identity.py#test_url_variant_identity_invariant"
        status: pass
    human_judgment: false
  - id: D6
    description: "Progress text, schedule step, timezone section and selector labels read well in the HA UI (en + de), and the indeterminate progress indicator is acceptable for a 50 MB feed"
    verification:
      - kind: other
        ref: "tests/test_translations.py (key/placeholder/literal parity) + hassfest container (0 invalid integrations)"
        status: pass
    human_judgment: true
    rationale: "Wording and the look of the collapsed section and progress dialog in the frontend are not asserted by any test"

duration: 9min
completed: 2026-10-16
status: complete
---

# Phase 03 Plan 06: Source Setup Flow with Download Progress Summary

**URL sources are now added through url -> download progress -> schedule -> name. The full, bounded download runs as a tracked task behind `async_show_progress`, and the name step writes it to the disk cache, so a new source costs one HTTP request. File sources share the refresh-mode and timezone fields and skip the download step.**

## Performance

- **Duration:** about 9 min
- **Started:** 2026-10-16T11:00:29Z
- **Completed:** 2026-10-16T11:09:39Z
- **Tasks:** 3 (tracer + 2 TDD)
- **Files modified:** 8 source/test files, plus 8 RED evidence files

## Accomplishments

- `config_flow.py` has shared builders, so the url, file and (from 03-08) options steps build the same fields (D-05):
  - `SECTION_TIMEZONE`, `_offset_selector()` and `_choice_selector()`
  - `_settings_fields(defaults)`: refresh mode plus the collapsed `timezone` section
  - `_settings_from_input()` flattens the section values
  - `_schedule_schema(options, mode)` returns exactly one field (D-01, D-02)
- URL chain:
  - `async_step_url` validates the URL and rejects duplicates (SRC-13) before anything is downloaded.
  - `async_step_download` runs `async_fetch_url` with `eager_start=False` behind `progress_action="download"` (CFG-03).
  - `async_step_schedule` stores `SourceOptions.from_mapping(...).as_options()`. An invalid time gives `invalid_time`.
  - `async_step_name` seeds `FeedCache(hass, unique_id)` before `async_create_entry` (D-13).
- Every download failure leaves the progress step through `progress_done(next_step_id="url")`. The url form then shows `cannot_connect`, `invalid_feed` or `feed_too_large` once, with the entered values as suggestions. The task reference is cleared, so a retry downloads again.
- The file chain is `file -> schedule -> name`. It has no progress step and seeds no cache (D-11, RESEARCH Open Question 4).
- `source.async_probe_url` was removed. The flow sniffs the first `PROBE_BYTES` of the full download with `looks_like_feed`.
- Translations, en and de with the same key order:
  - `config.progress.download` and `config.step.schedule`
  - `sections.timezone` and `refresh_mode` on the url and file steps
  - errors `feed_too_large` and `invalid_time`
  - selectors `refresh_mode` and `naive_timezone`
- hassfest validates all of them (0 invalid integrations).
- Tests:
  - `add_url_source` and `add_file_source` helpers.
  - 14 new or rewritten flow tests.
  - `test_tracer.py` and `test_identity.py` moved to the helpers and keep all their assertions.
  - The suite is at 776 passed, 1 skipped.

## Task Commits

1. **Task 1 (tracer): progress, schedule and timezone options, seeded cache**
   - RED `820cf9b` test(03-06)
   - GREEN `860e916` feat(03-06)
   - Tracer gate: the verify was re-run end to end and passed, then expansion continued.
2. **Task 2: file sources share settings and schedule steps**
   - RED `e4f5365` test(03-06)
   - GREEN `867fce7` feat(03-06)
3. **Task 3: download errors, abandoned download, caller migration**
   - RED `0eadeab` test(03-06)
   - GREEN `c1f3e94` feat(03-06)

**Plan metadata:** recorded in the docs(03-06) commit.

## TDD Gate Compliance

| Task | RED | GREEN | RED evidence |
|------|-----|-------|--------------|
| 1 | `820cf9b` | `860e916` | `03-06-red.json`: RED_EVIDENCE_OK (target_test_failed). The target failed on its form assertion `refresh_mode not in form`. That is one assertion before the planned result-type check, and the cause is the same missing chain. |
| 2 | `e4f5365` | `867fce7` | `03-06-red-2.json`: RED_EVIDENCE_OK. `test_file_source_end_to_end` fails with InvalidData at `refresh_mode`, because the old file schema rejects the new fields. `03-06-red-2-shared.json`: RED_EVIDENCE_OK, a clean assertion failure, `refresh_mode not in form` for the `[file]` variant. |
| 3 | `0eadeab` | `c1f3e94` | `03-06-red-3.json`: RED_EVIDENCE_OK via a TAP rerun (see deviations). The target `test_unreachable_url_cannot_connect[client-error]` was still on SHOW_PROGRESS where FORM was expected. The abandoned-download and duplicate tests already passed on the Task 1 wiring, so no `-abort` record was written, as the plan allows. |

No REFACTOR commits were needed.

## Files Created/Modified

- `custom_components/xmltv_calendar/config_flow.py`: shared settings and schedule builders; download, schedule and seeding steps; error round-trip.
- `custom_components/xmltv_calendar/source.py`: `async_probe_url` removed; `PROBE_BYTES` comment updated.
- `custom_components/xmltv_calendar/translations/en.json`, `de.json`: the new step, section, progress, error and selector texts.
- `tests/conftest.py`: `add_url_source`, `add_file_source` and `SECTION_TIMEZONE`.
- `tests/test_config_flow.py`: progress, seeding, schedule, shared-fields, flat-storage, bounds, error, abort, duplicate and log tests. `test_probe_reads_at_most_probe_bytes` was deleted.
- `tests/test_tracer.py`, `tests/test_identity.py`: moved to the helpers.
- `.planning/phases/03-resilient-sources/tdd-evidence/03-06-red{,-2,-2-shared,-3}.json`, `03-06-red{,-2,-3}.xml`, `03-06-red-3.tap`.

## Decisions Made

- The timezone section key is form-only. Options are always stored flat through `SourceOptions.from_mapping(...).as_options()`, which follows the 03-01 contract.
- The schedule step reads the mode from the pending settings. `SourceOptions.from_mapping` turns a daily mode without a time into interval, so it cannot tell the step which field to show.
- A `NotModified` answer to the validator-less setup download is shown as `cannot_connect`. It cannot happen with a correct server.
- A cache write that fails during seeding is logged by `FeedCache` at DEBUG. The entry is still created, and the coordinator then downloads.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The Task 3 RED record uses a TAP rerun**
- **Found during:** Task 3 RED.
- **Issue:** The JUnit report `03-06-red-3.xml` was classified `INVALID_RED (invalid_record: Incomplete JUnit test suite)`. The download task's uncaught SourceError is re-raised at teardown by the phcc `hass` fixture. pytest then writes two `<testcase>` elements for that test and lowers `tests=`. This is the same situation as 02-09.
- **Fix:** Reran with the stdlib TAP reporter plugin from 02-09; its source is kept in the record. The JUnit report is kept beside it.
- **Files modified:** `tdd-evidence/03-06-red-3.{tap,json}`
- **Commit:** `0eadeab`

**2. [Plan inconsistency] Task 2 verify was run without the old URL tests**
- **Found during:** Task 2 GREEN.
- **Issue:** The Task 2 verify needs all of `tests/test_config_flow.py` to pass. The plan, however, moves the old url-flow tests to Task 3 (Task 1 action step 4; Context Budget: "The full suite is green only at the end of this plan"). Those tests had been broken by design since Task 1.
- **Fix:** Ran the Task 2 verify with the 12 old url-flow tests deselected: 26 passed. After Task 3 the full suite is green: 776 passed, 1 skipped.
- **Commit:** n/a.

**3. [Rule 1 - Bug] The RED commit `820cf9b` contained two ruff findings in the tests**
- **Issue:**
  - An unused `noqa: PLR0913` (tests already ignore PLR0913).
  - ASYNC240 on `Path(...).is_file()` inside an async test.
- The lint check and the commit ran in one chain, and the `;` let the commit run after the lint failed.
- **Fix:** Added a sync `_cache_file()` helper and dropped the noqa, in the Task 1 GREEN commit `860e916`. Ruff is clean from that commit on.

**4. [Rule 2 - Missing test] Added `test_retry_after_download_error_downloads_again`**
- The plan requires that the finished task reference is cleared so a retry downloads again, but no test pinned it. This test does: an HTTP 500, then a resubmit, then a fresh download and the schedule step.
- **Commit:** `0eadeab` / `c1f3e94`

**5. [Test shape] The tracer test checks the menu in a separate flow**
- `test_tracer.py` keeps its menu assertion in a flow it then aborts. The source is added through `add_url_source`. All other assertions are unchanged, and the options assertion now expects the complete contract.

---

**Total deviations:** 5 (1 blocking evidence format, 1 plan inconsistency, 1 lint slip fixed in the next commit, 1 added test, 1 test shape).
**Impact on plan:** None on behaviour. Evidence and tests are stronger than the plan required.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- 03-07 (diagnostics) can rely on flow-created entries always having the complete option set.
- 03-08 (options flow) can reuse `_settings_fields(SourceOptions.from_mapping(entry.options))` and `_schedule_schema(...)` as they are. The translations follow the same section shape under `options.step.*`.
- UAT (03-08 human-check) should look at:
  - the progress dialog and the collapsed Timezone section in the real frontend
  - the time a large real feed takes during setup

## Self-Check: PASSED

- Files: all 8 modified files and 8 evidence files exist.
- Commits: `820cf9b`, `860e916`, `e4f5365`, `867fce7`, `0eadeab` and `c1f3e94` are all ancestors of HEAD.
- Checks: `uv run pytest -q -m "not benchmark"` gives 776 passed, 1 skipped. `ruff check` and `ruff format --check` are clean. hassfest reports 0 invalid integrations.

---
*Phase: 03-resilient-sources*
*Completed: 2026-10-16*
