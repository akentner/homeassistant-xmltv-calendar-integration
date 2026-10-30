---
phase: 03-resilient-sources
plan: 05
subsystem: parser
tags: [xmltv, timezone, zoneinfo, dst, coordinator, tdd]

requires:
  - phase: 03-resilient-sources
    provides: "03-01 SourceOptions.naive_timezone/offset_minutes and coordinator.source_options; 03-02/03-03 one _parser() partial for downloads, cached payloads and files, and a reload that re-parses a fresh disk cache"
provides:
  - "parse_xmltv_time(value, naive_tz=UTC) returning fixed-offset datetimes only"
  - "parse(..., naive_tz=UTC, shift=timedelta(0)) shifting start and stop before normalize"
  - "coordinator _parser() passing the source's naive_timezone and offset_minutes"
  - "tests/test_timezone_options.py end-to-end suite"
affects: [03-06 options flow, 03-07 diagnostics, 04]

actuals:
  tokens: 7800
  tasks: 3
  commits: 4
plan_head_before: 83a315e1fd195687e922fbe8382654e0a37d5c50
plan_head_after: bdb7c0bf22ff7b128128b8a86d4717678a97c2d2

tech-stack:
  added: []
  patterns:
    - "Zone-aware parse results are re-attached to a cached fixed-offset timezone (_pin_offset), so no ZoneInfo leaves the pure parser"
    - "Timezone correction applied once per parse inside the parser partial; data in memory is never shifted"

key-files:
  created:
    - tests/test_timezone_options.py
    - .planning/phases/03-resilient-sources/tdd-evidence/03-05-red.json
    - .planning/phases/03-resilient-sources/tdd-evidence/03-05-red.xml
  modified:
    - custom_components/xmltv_calendar/xmltv/timeparse.py
    - custom_components/xmltv_calendar/xmltv/parser.py
    - custom_components/xmltv_calendar/coordinator.py
    - tests/xmltv/test_timeparse.py
    - tests/xmltv/test_parser.py

key-decisions:
  - "Offset-less timestamps in a DST-aware naive_tz resolve with fold=0 (offset before the transition) and are re-attached to a cached fixed offset; non-whole-minute offsets get an uncached timezone"
  - "shift is added to start and stop (stop defaults to start first) only when non-zero, before normalize, so inferred stops follow shifted starts; the defaults keep the old code path bit-for-bit"
  - "Tasks 2 and 3 are regression suites (all rows green on the Task 1 implementation); mutation checks confirmed the tables catch a leaked ZoneInfo and a shift applied after stop inference"

patterns-established:
  - "Pure parser options as keyword arguments bound once in coordinator._parser(); every read path (download, cache, file) shares that partial"

requirements-completed: [SRC-10]

coverage:
  - id: D1
    description: "Offset-less timestamps read as HA local time (DST-aware) when naive_timezone is local; UTC by default"
    requirement: SRC-10
    verification:
      - kind: integration
        ref: "tests/test_timezone_options.py#test_naive_local_timestamps_end_to_end"
        status: pass
      - kind: integration
        ref: "tests/test_timezone_options.py#test_naive_timestamps_stay_utc_by_default"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_timeparse.py#test_naive_local_timestamps"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_timeparse.py#test_explicit_zones_ignore_naive_timezone"
        status: pass
    human_judgment: false
  - id: D2
    description: "DST gap/fold resolve deterministically and parsed datetimes carry fixed offsets, so durations across DST are exact"
    requirement: SRC-10
    verification:
      - kind: unit
        ref: "tests/xmltv/test_parser.py#test_naive_local_duration_across_dst_end_2026_10_25"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_parser.py#test_naive_local_inferred_stop_across_dst_start_2026_03_29"
        status: pass
    human_judgment: false
  - id: D3
    description: "offset_minutes shifts every start and stop by absolute minutes, before stop inference, idempotently"
    requirement: SRC-10
    verification:
      - kind: unit
        ref: "tests/xmltv/test_parser.py#test_shift_applies_before_stop_inference"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_parser.py#test_parse_is_idempotent_with_options"
        status: pass
      - kind: integration
        ref: "tests/test_timezone_options.py#test_offset_correction_shifts_events"
        status: pass
    human_judgment: false
  - id: D4
    description: "Defaults leave parser output unchanged for every existing table row and fixture"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_timeparse.py#test_default_arguments_unchanged"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_parser.py#test_default_arguments_unchanged"
        status: pass
    human_judgment: false
  - id: D5
    description: "A timezone option change reloads and re-parses the disk cache without a download; UIDs stable across reloads; file sources honour the options (D-16)"
    requirement: SRC-10
    verification:
      - kind: integration
        ref: "tests/test_timezone_options.py#test_timezone_option_change_reparses_cache_without_download"
        status: pass
      - kind: integration
        ref: "tests/test_timezone_options.py#test_correction_change_changes_uids"
        status: pass
      - kind: integration
        ref: "tests/test_timezone_options.py#test_file_source_uses_timezone_options"
        status: pass
    human_judgment: false

duration: 7min
completed: 2026-10-16
status: complete
---

# Phase 3 Plan 5: Per-Source Timezone Options Summary

**Offset-less XMLTV timestamps can be read as HA local time (DST-aware, re-pinned to fixed offsets), and a per-source minute correction shifts every programme by absolute time. The correction is applied once at parse time for downloads, the disk cache and local files.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-10-16T10:51:08Z
- **Completed:** 2026-10-16T10:58:03Z
- **Tasks:** 3
- **Files modified:** 6 source/test files (+2 RED evidence files)

## Accomplishments
- `parse_xmltv_time(value, naive_tz=UTC)`: offset-less timestamps are read in `naive_tz` with fold=0 (gap 02:30 on 2026-03-29 -> 01:30Z, fold 02:30 on 2026-10-25 -> 00:30Z), then re-attached to the cached fixed offset. No ZoneInfo leaves the parser. Explicit numeric offsets and alpha zones are never reinterpreted.
- `parse(..., naive_tz=UTC, shift=timedelta(0))`: the shift moves start and stop (a missing stop defaults to start first) before normalize, so inferred stops come from shifted starts. Shifts of +-720 min parse cleanly.
- `coordinator._parser()` passes `dt_util.get_default_time_zone()` when `naive_timezone == "local"` (otherwise UTC) and `timedelta(minutes=offset_minutes)`. All three read paths use it.
- End to end: a local 20:00 programme shows at 20:00+02:00. An option change reloads and re-parses the cache with no request. UIDs change with the correction and stay equal across reloads. File sources honour the options.

## Task Commits

1. **Task 1 (tracer): local-time end-to-end**
   - RED `168f9ba` (test): failing end-to-end test plus RED evidence
   - GREEN `0ac92f9` (feat): naive_tz/shift in timeparse, parser and coordinator
2. **Task 2: pure DST/offset/shift tables**: `73c9ae4` (test). This is a regression suite with no feat commit.
3. **Task 3: option change, UID and file-source end-to-end tests**: `bdb7c0b` (test). This is a regression suite with no feat commit.

**Plan metadata:** see the docs(03-05) commit

## TDD Gate Compliance

| Task | RED | GREEN | Notes |
|------|-----|-------|-------|
| 1 | `168f9ba` test(03-05). `03-05-red.json` classifies RED_EVIDENCE_OK (target_test_failed) | `0ac92f9` feat(03-05) | Target `test_naive_local_timestamps_end_to_end` failed on the planned start/end assertion: 22:00+02:00 instead of 20:00+02:00, because offset-less times were still read as UTC. The sibling default-UTC test passed in the same run, so there was no fixture or collection fault. |
| 2 | none: regression suite | none | Every new row passed against the Task 1 implementation, which already ships the complete feature implementation from the plan's `<feature>` block. Mutation checks (reverted afterwards) confirmed the tables are meaningful. Returning the ZoneInfo result unpinned failed 11 rows (all `test_naive_local_timestamps` DST/gap/fold rows, `test_naive_local_results_share_cached_offsets`, and both parser DST-duration tests). Inferring the stop from the unshifted start failed `test_shift_applies_before_stop_inference`. |
| 3 | none: regression suite | none | All 6 end-to-end cases passed on the Task 1 wiring plus the 03-02/03-03 reload/cache path. No RED record was written, as the plan allows. |

Regression guards from Task 2: all `test_default_arguments_unchanged` rows, `test_naive_local_timestamps[*]`, `test_explicit_zones_ignore_naive_timezone[*]`, `test_shift_*`, `test_parse_is_idempotent_with_options`.

## Files Created/Modified
- `custom_components/xmltv_calendar/xmltv/timeparse.py`: `naive_tz` parameter plus the `_fixed` and `_pin_offset` helpers
- `custom_components/xmltv_calendar/xmltv/parser.py`: `naive_tz` and `shift` threaded through `parse`, `_collect` and `_programme`
- `custom_components/xmltv_calendar/coordinator.py`: `_parser()` binds the source's timezone options
- `tests/test_timezone_options.py`: end-to-end suite (local time, default UTC, offset correction, reload without download, UIDs, file source)
- `tests/xmltv/test_timeparse.py`: table moved to `VALID`, plus default-unchanged, Berlin local/DST, explicit-zone and invalid rows
- `tests/xmltv/test_parser.py`: fixture default-unchanged, shift, inference, DST duration, extremes and idempotency tests. Test doubles now accept the new arguments.

## Decisions Made
- A DST-aware `naive_tz` resolves with fold=0. Results are always re-pinned to a cached `datetime.timezone`; a non-whole-minute offset gets an uncached `timezone`.
- The shift uses plain `+` on fixed-offset datetimes instead of Pattern 10's `astimezone(UTC) + shift`. The arithmetic is equally absolute, and the parsed offset representation is kept.
- `parse` carries `# noqa: PLR0913`. All its options are keyword-only and bound once by the coordinator partial.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Parser test doubles had the old one-argument signatures**
- **Found during:** Task 1 (GREEN)
- **Issue:** `test_conversion_error_skips_only_that_programme` monkeypatched `parse_xmltv_time` with `flaky(value)`, and `test_programming_error_is_not_reported_as_feed_error` patched `_programme` with `broken(elem)`. Both raised TypeError now that the parser passes `naive_tz` and `shift`.
- **Fix:** both doubles accept and forward the extra positional arguments (`*args`).
- **Files modified:** tests/xmltv/test_parser.py
- **Verification:** the Task 1 verify passed (76 tests)
- **Committed in:** 0ac92f9

**2. [Rule 3 - Blocking] Ruff PLR0911 on parse_xmltv_time**
- **Found during:** Task 1 (GREEN)
- **Issue:** inlining the offset re-pinning added return statements past the limit.
- **Fix:** extracted `_pin_offset(value)`.
- **Files modified:** custom_components/xmltv_calendar/xmltv/timeparse.py
- **Committed in:** 0ac92f9

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** test-double signature and lint-shape fixes only. No scope change.

## Issues Encountered
None.

## Verification
- `uv run pytest -q -m "not benchmark"`: 765 passed, 1 skipped
- `uv run pytest -q -m benchmark`: 4 passed, 1 skipped (default path adds no per-programme cost)
- `uv run ruff check . && uv run ruff format --check .`: clean
- Tracer gate (interactive, end-of-phase, automated-only verify): re-ran and passed before expansion

## User Setup Required
None. No external service configuration required.

## Next Phase Readiness
- 03-06 can write `naive_timezone` / `offset_minutes` into `entry.options`. The coordinator already reads them, and a change reloads and re-parses the cache without a download.
- 03-07 diagnostics can read `coordinator.source_options` unchanged.

---
*Phase: 03-resilient-sources*
*Completed: 2026-10-16*

## Self-Check: PASSED
