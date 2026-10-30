---
phase: 03-resilient-sources
plan: 03
subsystem: ingestion
tags: [conditional-get, etag, if-modified-since, http-304, sha256, data-update-coordinator, always-update, file-stat]

requires:
  - phase: 03-resilient-sources
    provides: "03-02 disk cache (FeedCache, CacheMeta with sha256/etag/last_modified, valid_meta, _async_parse_cached) and the stale-while-revalidate start"
provides:
  - "Conditional GET: async_fetch_url(hass, url, *, etag, last_modified) -> Fetched | NotModified"
  - "Later-refresh decision: validators only with a valid cache, 304 keeps the identical data object, identical SHA-256 body skips the parse, 304 without data parses the cache or refetches unconditionally"
  - "FeedCache.async_touch(fetched_at, *, etag, last_modified) and payload_sha256()"
  - "always_update=False plus a calendar identity guard: refilter only for a new EpgData object"
  - "File sources: FileRead(signature, epg) and read_and_parse_file(config, path, *, parser, known) skipping unchanged (st_mtime_ns, st_size)"
affects: [03-04 health tracking (a 304 / unchanged file counts as success), 03-05, 03-06, 03-08 UAT (curl -sI validators, update_entity)]

actuals:
  tokens: 9560       # chars/4 over the realized code + test diff (38240 chars); the committed RED evidence adds ~13.5k more (23104 incl. evidence)
  tasks: 3
  commits: 6
plan_head_before: 31f4a125c3091f7e35c936ab1515537983e3e85d
plan_head_after: e30e936ea74943b8d07ba3604cc9085f0f0e94a5

tech-stack:
  added: []
  patterns:
    - "Conditional request result type: Fetched | NotModified; NotModified carries the cleaned validators of the 304"
    - "Unchanged sources return the identical EpgData object; always_update=False turns that into no listener calls"
    - "Calendar refilters only when coordinator.data is not self._epg; other listener calls only write state"
    - "File change detection by (st_mtime_ns, st_size) after the allowlist check, in the same executor job"

key-files:
  created:
    - tests/test_refresh.py
    - tests/test_file_source.py
    - .planning/phases/03-resilient-sources/tdd-evidence/03-03-red.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-03-red-2-identical.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-03-red-2-304cache.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-03-red-2-304nodata.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-03-red-2-refilter.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-03-red-3.json
  modified:
    - custom_components/xmltv_calendar/source.py
    - custom_components/xmltv_calendar/cache.py
    - custom_components/xmltv_calendar/coordinator.py
    - custom_components/xmltv_calendar/calendar.py
    - tests/test_filtering.py

key-decisions:
  - "NotModified is a frozen dataclass (etag, last_modified); NOT_MODIFIED is the validator-less instance, so a 304 with a new ETag/Last-Modified can replace the stored one"
  - "async_touch keeps a stored validator when the response does not send one; it only updates metadata, never the payload"
  - "Identical-body skip runs only with data in memory and a valid meta, after a cheap size check; SHA-256 is computed in the executor"
  - "304 with no data and no usable cache repeats the request without validators in the same refresh; a 304 to that unconditional request fails with unable_to_fetch"
  - "File sources compare (st_mtime_ns, st_size) against the signature of this coordinator instance only; nothing is persisted, so a reload parses again (D-11)"

patterns-established:
  - "ParseCounter test helper: monkeypatch the coordinator-module parse (looked up at call time by _parser) with a counting wrapper"
  - "Sequenced aioclient_mock responses via an async side_effect returning AiohttpClientMockResponse"

requirements-completed: [SRC-07, AUT-04]

coverage:
  - id: D1
    description: "A later refresh sends the stored ETag/Last-Modified verbatim; a 304 causes no body, no parse, keeps the identical data object, succeeds and moves cache fetched_at"
    requirement: SRC-07
    verification:
      - kind: integration
        ref: "tests/test_refresh.py#test_unchanged_feed_answers_304_without_reparse"
        status: pass
      - kind: integration
        ref: "tests/test_refresh.py#test_304_with_new_validator_replaces_stored"
        status: pass
    human_judgment: false
  - id: D2
    description: "A changed feed (200) replaces data, cached payload and validators; the next request sends the new validator"
    requirement: SRC-07
    verification:
      - kind: integration
        ref: "tests/test_refresh.py#test_changed_feed_replaces_data_and_cache"
        status: pass
    human_judgment: false
  - id: D3
    description: "A 200 whose body equals the cached payload (same SHA-256) is not re-parsed"
    requirement: SRC-07
    verification:
      - kind: integration
        ref: "tests/test_refresh.py#test_identical_body_is_not_reparsed"
        status: pass
    human_judgment: false
  - id: D4
    description: "homeassistant.update_entity on any calendar triggers one immediate conditional refresh of the source, ignoring cache freshness"
    requirement: AUT-04
    verification:
      - kind: integration
        ref: "tests/test_refresh.py#test_update_entity_refreshes_now_with_validators"
        status: pass
      - kind: integration
        ref: "tests/test_refresh.py#test_update_entity_on_any_calendar_refreshes_the_source"
        status: pass
    human_judgment: false
  - id: D5
    description: "A 304 without data in memory parses the cache; with an unusable cache the same refresh repeats the request without validators (Pitfall 3, T-03-09)"
    verification:
      - kind: integration
        ref: "tests/test_refresh.py#test_304_without_data_parses_cache"
        status: pass
      - kind: integration
        ref: "tests/test_refresh.py#test_304_without_usable_cache_refetches_unconditionally"
        status: pass
    human_judgment: false
  - id: D6
    description: "Calendars refilter only for new data; a 304 or a failed refresh only rewrites state and keeps events"
    verification:
      - kind: integration
        ref: "tests/test_refresh.py#test_unchanged_data_does_not_refilter"
        status: pass
    human_judgment: false
  - id: D7
    description: "Local files re-parse only on mtime/size change, allowlist checked on every refresh, no payload cache, reload parses again (D-11, T-03-10)"
    verification:
      - kind: integration
        ref: "tests/test_file_source.py#test_unchanged_file_is_not_reparsed"
        status: pass
      - kind: integration
        ref: "tests/test_file_source.py#test_changed_mtime_reparses"
        status: pass
      - kind: integration
        ref: "tests/test_file_source.py#test_changed_size_reparses"
        status: pass
      - kind: integration
        ref: "tests/test_file_source.py#test_allowed_path_checked_on_every_refresh"
        status: pass
      - kind: integration
        ref: "tests/test_file_source.py#test_reload_parses_file_again"
        status: pass
      - kind: integration
        ref: "tests/test_file_source.py#test_file_source_writes_no_payload_cache"
        status: pass
    human_judgment: false
  - id: D8
    description: "Real feeds send ETag/Last-Modified (RESEARCH A8) and update_entity behaves on the live host"
    verification: []
    human_judgment: true
    rationale: "Depends on the user's real feed servers and live HA host; planned as the 03-08 UAT steps (curl -sI <feed URL>, update_entity on a real calendar)"

duration: 9min
completed: 2026-10-16
status: complete
---

# Phase 03 Plan 03: Conditional Refresh Summary

**Conditional GET with If-None-Match/If-Modified-Since and 304 handling, a SHA-256 skip for identical bodies, an mtime/size skip for local files, and calendars that refilter only when the coordinator returns a new EpgData object (always_update=False plus an identity guard)**

## Performance

- **Duration:** 9 min
- **Started:** 2026-10-16T10:27:27Z
- **Completed:** 2026-10-16T10:36:23Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 7 source/test files, plus 9 RED evidence files

## Accomplishments

- A URL source with a valid cache sends its stored validators verbatim. A 304 costs one small request: no body, no parse, no refilter, and the data object stays the same. The cache `fetched_at` moves, and any new validator in the 304 replaces the stored one.
- Servers without validators no longer cost a parse when nothing changed: a 200 with the cached SHA-256 is treated like a 304.
- `homeassistant.update_entity` on any calendar refreshes the source at once, with validators (inherited `CoordinatorEntity.async_update`, D-12).
- A 304 that arrives while no data is in memory parses the cached payload. If that payload is unusable, the same refresh repeats the request without validators, so a 304 never leaves the source empty (T-03-09).
- Local files are only stat'ed when unchanged. The allowlist check still runs first on every refresh (T-03-10).
- `always_update=False` and the calendar identity guard mean unchanged data and success/failure transitions only rewrite state, with no filter pass.

## Task Commits

1. **Task 1 (tracer): an unchanged remote feed answers 304 and is neither re-downloaded nor re-parsed**
   - RED `d6cd051` (test)
   - GREEN `a6a31af` (feat)
   - Tracer gate: interactive, `end-of-phase`, automated-only verify. The re-run passed, so execution continued.
2. **Task 2: manual refresh, changed and identical bodies, the 304-without-data path, no refilter on unchanged data**
   - RED `dfd1328` (test)
   - GREEN `b367836` (feat)
3. **Task 3: local file sources re-parse only when the file changed**
   - RED `052d7b9` (test)
   - GREEN `e30e936` (feat)

No REFACTOR commits were needed.

## TDD Gate Compliance

| Gate | Task 1 | Task 2 | Task 3 |
|------|--------|--------|--------|
| RED commit before GREEN | `d6cd051` before `a6a31af` | `dfd1328` before `b367836` | `052d7b9` before `e30e936` |
| RED classifier | `03-03-red.json`: RED_EVIDENCE_OK (target_test_failed) | `03-03-red-2-identical.json`, `-304cache.json`, `-304nodata.json`, `-refilter.json`: all RED_EVIDENCE_OK | `03-03-red-3.json`: RED_EVIDENCE_OK |

**RED semantic assessments:**

- **Task 1** `test_unchanged_feed_answers_304_without_reparse`: setup and `call_count == 1` passed. The test failed on the planned assertion `If-None-Match == '"v1"'`, because no conditional headers were sent (request headers `{}`).
- **Task 2:**
  - `test_identical_body_is_not_reparsed` failed on `parses.calls == 0` (it was 1).
  - `test_304_without_data_parses_cache` failed on `parses.calls == 1` (it was 0), because the Task 1 code failed the refresh. The request and its If-None-Match had already been asserted.
  - `test_304_without_usable_cache_refetches_unconditionally` failed on `call_count == 2` (it was 1).
  - `test_unchanged_data_does_not_refilter` failed on `applies == 0` (it was 1, after a successful 304).
  - JUnit errors=0 in every run.
- **Task 3** `test_unchanged_file_is_not_reparsed` failed on `parses.calls == 0` (it was 1). The RED counter wrapped `parse` in both the source and coordinator modules, so the failure was not an artefact of where `parse` is looked up.

**Regression tests that were already green at RED (kept on purpose):**

- **AUT-04:** `test_update_entity_refreshes_now_with_validators` and `test_update_entity_on_any_calendar_refreshes_the_source`. As the plan expected, after Task 1 a non-first refresh always hits the network with validators.
- **SRC-07:** `test_changed_feed_replaces_data_and_cache` and `test_304_with_new_validator_replaces_stored`.
- **Task 3:** `test_changed_mtime_reparses`, `test_changed_size_reparses`, `test_allowed_path_checked_on_every_refresh`, `test_reload_parses_file_again` and `test_file_source_writes_no_payload_cache`. These were green before GREEN because every refresh parsed and no file cache existed.

## Files Created/Modified

- `custom_components/xmltv_calendar/source.py`: `NotModified` and `NOT_MODIFIED`; the conditional `async_fetch_url`; `FileRead`; `read_and_parse_file(config, path, *, parser, known)` with the stat skip.
- `custom_components/xmltv_calendar/cache.py`: `async_touch` and `payload_sha256`.
- `custom_components/xmltv_calendar/coordinator.py`:
  - `always_update=False`
  - `_async_fetch`, plus the later-refresh decision in `_async_update_url`
  - `_file_signature`, and the unchanged-file path in `_async_update_file`
- `custom_components/xmltv_calendar/calendar.py`: the identity guard in `_handle_coordinator_update`.
- `tests/test_refresh.py`: 9 tests (304, validator replacement, update_entity ×2, changed feed, identical body, 304 without data ×2, no refilter).
- `tests/test_file_source.py`: 6 file-source tests.
- `tests/test_filtering.py`: `test_missing_channel_warning_once_per_refresh` now serves a changed body.
- `.planning/phases/03-resilient-sources/tdd-evidence/03-03-*`: RED JUnit reports and records.

## Decisions Made

- `NotModified` carries the 304's cleaned validators. `NOT_MODIFIED` is the shared validator-less instance. The coordinator checks `isinstance(..., NotModified)`.
- `async_touch` keeps the stored validator when the response omits one. A failed Store save is logged at DEBUG and does not fail the refresh.
- The identical-body check runs only with data in memory and a valid meta. It compares the size first, so the SHA-256 (computed in the executor) only runs when it can match.
- If a 304 answers the unconditional retry, the refresh fails with `unable_to_fetch`.
- The file signature belongs to the coordinator instance only and is never persisted (D-11, Pitfall 10).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `NotModified` carries validators instead of being a bare singleton**
- **Found during:** Task 1 (GREEN)
- **Issue:** The plan said "return NOT_MODIFIED on 304" and also "touch using validators from the response when present". The must-have also requires that "a 304 that carries a new ETag or Last-Modified replaces the stored validator". A singleton cannot carry the 304's headers.
- **Fix:** `NotModified` is a frozen slotted dataclass `(etag, last_modified)`. `NOT_MODIFIED = NotModified()` is returned for a 304 without validators; a 304 with validators gets its own instance.
- **Files modified:** `custom_components/xmltv_calendar/source.py`
- **Verification:** `test_304_with_new_validator_replaces_stored` passes.
- **Committed in:** `a6a31af`

**2. [Rule 3 - Blocking] The Pitfall 3 tests bypass the cache-first start**
- **Found during:** Task 2 (RED)
- **Issue:** With `coordinator.data = None`, `_async_update_data` takes 03-02's stale-while-revalidate start, which serves any valid cache without a request. As planned, the "304 while no data in memory" tests could never reach the server.
- **Fix:** The helper `_without_start_from_cache` sets `data = None` and monkeypatches `_async_start_from_cache` to return None. The refresh then goes to the network with the stored validators, and the coordinator's 304-without-data branch is exercised through `async_refresh()`.
- **Files modified:** `tests/test_refresh.py`
- **Verification:** both tests RED before Task 2 GREEN, green after.
- **Committed in:** `dfd1328`

**3. [Rule 1 - Bug] An existing test encoded the old re-parse-every-200 behaviour**
- **Found during:** Task 2 (GREEN, full suite)
- **Issue:** `tests/test_filtering.py::test_missing_channel_warning_once_per_refresh` refreshed with the same body and expected a second refilter warning. Identical bodies are now skipped, by design (SRC-07/A8).
- **Fix:** The second refresh serves the feed plus an XML comment, so it is new data. The test's intent (one warning per refilter of new data) is unchanged.
- **Files modified:** `tests/test_filtering.py`
- **Verification:** full suite green.
- **Committed in:** `b367836`

**4. [Rule 1 - Bug] RED tests left refilter tasks pending (lingering-timer teardown error)**
- **Found during:** Task 2 (first RED run)
- **Issue:** `test_304_with_new_validator_replaces_stored` errored at teardown with a lingering calendar timer: a refilter task scheduled by the refresh outlived the test. The RED classifier rejects call-failure plus teardown-error reports (02-09).
- **Fix:** `await hass.async_block_till_done()` after every refresh in `tests/test_refresh.py`. RED was re-run, so the committed report comes from the final test code.
- **Files modified:** `tests/test_refresh.py`
- **Committed in:** `dfd1328`

**5. [Rule 3 - Blocking] The Task 3 test counter was adjusted in GREEN**
- **Found during:** Task 3 (GREEN)
- **Issue:** In RED, the counter wrapped `parse` in both `source` and `coordinator` (the old file path used `source.parse`). In GREEN, `source.py` no longer imports `parse`, because the parser is injected. `monkeypatch.setattr` on a missing attribute fails.
- **Fix:** The counter now wraps only `coordinator.parse`, which `_parser()` passes to `read_and_parse_file`.
- **Files modified:** `tests/test_file_source.py`
- **Committed in:** `e30e936`

**Additions (not deviations from behaviour):**
- An extra test, `test_304_with_new_validator_replaces_stored`, covers the must-have truth that had no planned test.
- An extra RED record, `03-03-red-2-304cache.json`, was added alongside the three required Task 2 records.
- `os.stat` became `Path(real_path).stat()` (Ruff PTH116). It still reads `st_mtime_ns`.

---

**Total deviations:** 5 auto-fixed (3 Rule 1, 2 Rule 3)
**Impact on plan:** Behaviour matches every must-have truth. No scope creep: the deviations are test plumbing, plus one result type widened so the plan's own validator requirement is satisfiable.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None. No external service configuration required.

## Next Phase Readiness

- 03-04 (health tracking, D-17) can treat a returned identical object (304, identical body, unchanged file) as a success. `last_update_success` is True in each case.
- One residual edge case: a 304 to an unconditional retry fails with `unable_to_fetch`. That is a misbehaving server; 03-04's failure accounting covers it.
- A8 stays a manual UAT check in 03-08: whether the real feeds send validators (`curl -sI <feed URL>`). Either way is handled.

## Self-Check: PASSED

- Files found: `source.py`, `cache.py`, `coordinator.py`, `calendar.py`, `tests/test_refresh.py`, `tests/test_file_source.py`, and 6 RED records (`03-03-red.json`, `-red-2-identical`, `-red-2-304cache`, `-red-2-304nodata`, `-red-2-refilter`, `-red-3`) plus 3 JUnit reports.
- Commits found on HEAD: `d6cd051`, `a6a31af`, `dfd1328`, `b367836`, `052d7b9`, `e30e936`. 6 commits since `plan_head_before`.
- TDD gate: 3 `test(03-03)` and 3 `feat(03-03)` commits, each RED before its GREEN.
- Verification:
  - `uv run pytest -q -m "not benchmark"`: 690 passed, 1 skipped.
  - `uv run pytest -q -m benchmark`: 4 passed, 1 skipped.
  - `uv run ruff check . && uv run ruff format --check .`: clean.
- Acceptance greps: IF_NONE_MATCH, IF_MODIFIED_SINCE, `async def async_touch`, `always_update=False`, `self.coordinator.data is self._epg`, `class FileRead`, `st_mtime_ns`, `known=`. All present.

---
*Phase: 03-resilient-sources*
*Completed: 2026-10-16*
