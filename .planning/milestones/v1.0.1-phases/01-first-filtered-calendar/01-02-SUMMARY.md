---
phase: 01-first-filtered-calendar
plan: 02
subsystem: xmltv-library
tags: [xmltv, timestamps, timezone, dedup, uid, tdd, pytest]

requires:
  - phase: 01-01
    provides: "Frozen xmltv/ contracts (Programme, ParseStats, parse_xmltv_time, normalize_programmes, to_event_fields), setup_xmltv harness"
provides:
  - "parse_xmltv_time for every XMLTV variant: 12/14 digits, +HHMM, +HH:MM, no space, alpha zones Z/UTC/GMT/BST/CET/CEST/EET/EEST, no offset = UTC (D-14)"
  - "normalize_programmes: exact-duplicate removal (EVT-01), per-channel next-start stop inference (D-12), deterministic (start, channel_id, title) order"
  - "event_uid '<channel_id>-<UTC start %Y%m%dT%H%M%SZ>-<crc32(title):08x>'; EventFields.uid is always a string (EVT-06)"
affects: [01-03, 01-04, 01-05, 01-06, 01-08]

actuals:
  tokens: 4141   # chars/4 over the 7 authored source/test files (16,565 chars); committed RED evidence (~80 KB JSON/XML) excluded
  tasks: 2
  commits: 4
plan_head_before: fcbb81d09032c25be3329468520d935122064399
plan_head_after: 069247d2361296d983565b48cb80b1895f8db368

tech-stack:
  added: []
  patterns:
    - "Stop inference walks each channel group backwards, tracking the start of the next strictly later block"
    - "Dedup key uses start.astimezone(UTC), so equal instants with different offsets collapse"
    - "RED evidence: pytest --junitxml report plus one classifier record per RED target under tdd-evidence/"

key-files:
  created:
    - tests/test_timing.py
    - tests/xmltv/test_timeparse.py
    - tests/xmltv/test_normalize.py
    - tests/xmltv/test_render.py
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-02-red.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-02-red.json
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-02-red-2.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-02-red-2-dedup.json
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-02-red-2-order.json
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-02-red-2-uid.json
  modified:
    - custom_components/xmltv_calendar/xmltv/timeparse.py
    - custom_components/xmltv_calendar/xmltv/normalize.py
    - custom_components/xmltv_calendar/xmltv/render.py
    - .planning/WINDOWS.md

key-decisions:
  - "Dedup runs before grouping, in input order, keyed on (channel_id, UTC start, title); first occurrence wins"
  - "EventFields.uid narrowed from str | None to str now that every programme has a UID"
  - "Inferred programmes are returned in start order so the final stable sort keeps input order for ties"

patterns-established:
  - "RED targets that would otherwise fail on ImportError (event_uid) are asserted through the existing public contract (to_event_fields) so RED fails on an assertion"

requirements-completed: [EVT-01, EVT-05, EVT-06]

coverage:
  - id: D1
    description: "Every XMLTV timestamp variant parses to the right instant; unknown zones, garbage and impossible dates return None"
    requirement: "EVT-05"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_timeparse.py#test_valid_timestamps"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_timeparse.py#test_invalid_timestamps_return_none"
        status: pass
    human_judgment: false
  - id: D2
    description: "A 12-digit '+02:00' programme without stop shows up in calendar.get_events at 10:00Z-12:00Z, ending at the next programme's start; the last one lasts 60 minutes"
    requirement: "EVT-05"
    verification:
      - kind: integration
        ref: "tests/test_timing.py#test_short_timestamp_and_missing_stop_end_to_end"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_normalize.py#test_missing_stops_inferred_from_next_start"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_normalize.py#test_stop_not_after_start_is_inferred"
        status: pass
    human_judgment: false
  - id: D3
    description: "Exact duplicates collapse (first wins); equal-start different titles, same title on two channels and back-to-back programmes are all kept; output order is shuffle-invariant"
    requirement: "EVT-01"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_normalize.py#test_exact_duplicates_collapse_first_wins"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_normalize.py#test_shuffled_input_gives_identical_output"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_normalize.py#test_equal_start_different_titles_both_kept"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_normalize.py#test_back_to_back_not_merged"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every event has the A7 UID, identical across two parses and after reversing the file order; different titles give different UIDs"
    requirement: "EVT-06"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_render.py#test_uid_format_and_stability"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_render.py#test_uid_differs_for_different_titles"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-10-13
status: complete
---

# Phase 1 Plan 02: Programme Identity and Timing Summary

**Every XMLTV timestamp variant now lands at the correct UTC instant. That covers 12-digit, `+HH:MM`, no-space, alpha zones, and no offset (treated as UTC). Missing or broken stops are inferred from the next later start on the same channel. Exact duplicates collapse. Each event carries a stable `<channel>-<UTC start>-<crc32>` UID. All four RED targets failed on their planned assertions before GREEN.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-12T22:40:51Z
- **Completed:** 2026-10-12T22:45:08Z
- **Tasks:** 2
- **Files modified:** 7 source/test files, plus 6 RED evidence files and `.planning/WINDOWS.md`

## Accomplishments

- `parse_xmltv_time` is the RESEARCH reference implementation (anchored regex, cached fixed-offset tzinfo, alpha map). It has no `strptime`, and every `ValueError` becomes `None` (T-01-04).
- `normalize_programmes` removes exact duplicates first, then sorts each channel group by (start, title) and infers stops. Each stop is the next strictly later start, else start + 60 min. This guarantees `stop >= start` for `CalendarEvent` (T-01-05).
- `event_uid` produces `daserste.de-20261013T100000Z-1bd7e913`-style UIDs. `to_event_fields` always fills `uid`, and the 01-01 calendar wiring passes it into `CalendarEvent(uid=...)` unchanged.
- The broken-windows entry #1 (`uid=None` stub in render.py) is marked fixed. `.planning/WINDOWS.md` now has open_count 0.

## Task Commits

1. **Task 1 (tracer): 12-digit '+02:00' programme without stop, correctly timed end to end**
   - `3f68e14` test(01-02): RED
   - `928c122` feat(01-02): GREEN
   - Tracer feedback gate: no `blocking-human` gate, auto mode off, `human_verify_mode=end-of-phase`, and `<verify>` is automated-only. The verify was re-run (24 passed) and expansion continued with no checkpoint.
2. **Task 2: Dedup, deterministic order and stable UIDs**
   - `d7bc06e` test(01-02): RED
   - `069247d` feat(01-02): GREEN
   - REFACTOR: none needed.

## TDD Gate Compliance

| Cycle | RED | GREEN | REFACTOR |
|-------|-----|-------|----------|
| Task 1 | `3f68e14` | `928c122` | none |
| Task 2 | `d7bc06e` | `069247d` | none |

The `test(01-02)` commits precede their `feat(01-02)` commits in git log.

- **RED 1** (`tdd-evidence/01-02-red.xml`, record `01-02-red.json`):
  - Target: `tests/test_timing.py::test_short_timestamp_and_missing_stop_end_to_end`. It failed on `assert events == [...]` and got `[]`.
  - Classifier verdict: `RED_EVIDENCE_OK` (`target_test_failed`), with 24 tests, 13 failing.
  - Semantic assessment: the target was collected and its setup succeeded. It failed on the planned `get_events` assertion because the 01-01 parser dropped both 12-digit `+02:00` starts. The other 12 failures were the planned timestamp table cases. There was no import, collection or fixture fault.
- **GREEN 1:** the reference `parse_xmltv_time`, plus per-channel next-start stop inference. 24 passed.
- **RED 2** (`tdd-evidence/01-02-red-2.xml`, one record per target). There were 11 tests, 4 failing, and each target was classified `RED_EVIDENCE_OK` (`target_test_failed`):
  - `test_exact_duplicates_collapse_first_wins` failed on `assert result == (first,)`. The same-instant duplicate with a CEST offset was kept.
  - `test_shuffled_input_gives_identical_output` failed on the canonical list assertion (seed 0). The exact duplicate `(x, C, 12:00Z)` appeared twice.
  - `test_uid_format_and_stability` failed on the UID assertion because `uid` was `None`.
  - The 4th failure, `test_uid_differs_for_different_titles`, failed on `assert uid_a is not None`. That is the same planned UID behavior.
  - Semantic assessment: all failures are planned assertions. There were no load, fixture or collection faults. The regression guards (equal start, back-to-back) already passed, as the plan expected.
- **GREEN 2:** dedup keyed on `(channel_id, UTC start, title)` plus `event_uid`. `tests/xmltv` reports 34 passed, and `test_tracer.py` still passes.

## Files Created/Modified

- `custom_components/xmltv_calendar/xmltv/timeparse.py`: full-variant parser (`_TS_RE`, `_ALPHA`, `_TZ_CACHE`, `_tz`)
- `custom_components/xmltv_calendar/xmltv/normalize.py`: dedup, `_infer_stops`, deterministic ordering
- `custom_components/xmltv_calendar/xmltv/render.py`: `event_uid`, `uid` set in `to_event_fields`, `EventFields.uid: str`
- `tests/test_timing.py`: end-to-end timing tracer through `calendar.get_events`
- `tests/xmltv/test_timeparse.py`: 17 valid plus 6 invalid parametrized cases, including both 2026 DST nights
- `tests/xmltv/test_normalize.py`: 8 normalization cases
- `tests/xmltv/test_render.py`: UID format and stability, plus a guard that summary and location are unchanged
- `.planning/phases/01-first-filtered-calendar/tdd-evidence/`: JUnit reports and classifier records

## Decisions Made

- Dedup runs before grouping, in input order, so "first occurrence in document order" holds literally. The key converts start to UTC, which makes `12:00+02:00` and `10:00Z` duplicates.
- `EventFields.uid` is narrowed to `str`. No caller depended on `None`, and the plan lists "`EventFields.uid` is now always a string" as a changed field.
- `_infer_stops` returns the group in start order, so the final stable sort keeps input order for programmes with identical sort keys.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The UID RED test asserts through `to_event_fields`, not `event_uid`**
- **Found during:** Task 2 RED
- **Issue:** Importing `event_uid` before it exists would make the whole test module fail at collection (`ImportError`). That is an INVALID_RED `fixture_or_load_failure`, not an assertion failure.
- **Fix:** The RED tests read `to_event_fields(...)["uid"]`, the existing contract, so RED fails on the UID assertion. `event_uid` exists after GREEN and is checked by the acceptance grep. It is exercised through `to_event_fields`.
- **Files modified:** tests/xmltv/test_render.py
- **Committed in:** d7bc06e

**2. [Rule 3 - Blocking] Ruff S311/ISC004 in the new tests; RED evidence regenerated**
- **Found during:** Task 2 RED
- **Issue:** `random.Random(seed).shuffle` triggered S311, and an implicitly concatenated string in a tuple triggered ISC004.
- **Fix:** Added a justified `# noqa: S311` (deterministic test shuffle) and parenthesized the string. The RED run was repeated so the committed JUnit report and records match the committed test files.
- **Files modified:** tests/xmltv/test_normalize.py, tests/xmltv/test_render.py
- **Committed in:** d7bc06e

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Test-side only. No contract in the interfaces block changed.

## Issues Encountered

- Commits land on `main`, which the orchestrator expected for this sequential run (`branching_strategy: none`, no remote).

## Known Stubs

None in the files this plan touched. The remaining 01-01 stubs (filter.py regex, window.py, source.py caps) belong to 01-03 to 01-05.

## Threat Flags

None. No new network, file or auth surface. T-01-04 (anchored, bounded regex, `ValueError` mapped to `None`) and T-01-05 (stop never earlier than start) are mitigated as planned. T-01-SC: no packages were added and `uv.lock` is unchanged.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- 01-03 to 01-05 can rely on correctly timed, deduplicated and sorted `EpgData.programmes`, with stable UIDs.
- Plan verification: `uv run pytest -q -m "not benchmark"` reports 36 passed. `ruff check` and `ruff format --check` are clean. Both RED to GREEN cycles appear in git log, and the evidence files exist under `tdd-evidence/`.

## Self-Check: PASSED

- All 7 source and test files exist on disk.
- Commits 3f68e14, 928c122, d7bc06e and 069247d are ancestors of HEAD (4 commits since fcbb81d). `check evaluation-scope --plan 01-02 --commits-only` resolves all four.
- Every acceptance criterion was re-run and passed: the target test files pass, RED_EVIDENCE_OK holds for all 4 targets, `def parse_xmltv_time` is present with no `strptime(` in timeparse.py, `def event_uid` and `crc32` are present in render.py, and `tests/xmltv` (34) and `tests/test_tracer.py` (1) pass.

---
*Phase: 01-first-filtered-calendar*
*Completed: 2026-10-13*
