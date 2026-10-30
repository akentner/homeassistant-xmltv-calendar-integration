---
phase: 01-first-filtered-calendar
plan: 11
subsystem: parser
tags: [xmltv, timestamps, robustness, calendar, gap-closure, cr-01, wr-06, tdd]
requires:
  - phase: 01-02
    provides: "parse_xmltv_time, streaming parser with skipped_malformed counting, normalize_programmes (D-12 stop inference)"
  - phase: 01-04
    provides: "build_events / XmltvCalendarEntity.event with the HomeAssistantError skip (T-01-09)"
  - phase: 01-05
    provides: "FeedError / FeedTooLargeError, _STREAM_ERRORS translation, content-free error messages (T-01-12)"
provides:
  - "parse_xmltv_time never raises: offset minutes >= 60, offsets beyond 18 h and written years outside 1900..2200 return None"
  - "Per-programme ValueError/OverflowError guard in parser._collect (skip + skipped_malformed)"
  - "parser._read_events: FeedError translation limited to iterparse reads (WR-06); programming errors propagate"
  - "build_events and XmltvCalendarEntity.event skip matches that cannot become a CalendarEvent (HomeAssistantError, OverflowError, ValueError)"
  - "CR-01 regression tests at every layer (timeparse table, parser table, end-to-end tracer, calendar)"
affects: [phase-01-verify, phase-01-uat]
actuals:
  tokens: 45459   # chars/4 over the full realized diff (181,836 chars); code + tests alone are 21,354 chars (~5,339), the rest is JUnit/JSON RED evidence
  tasks: 3
  commits: 6
plan_head_before: 700e1417697c11666642dd3d0fec886e5d9153aa
plan_head_after: 05fe9fe301ff13db011253b0920cee2f7262dfe2
tech-stack:
  added: []
  patterns:
    - "Validate ranges before constructing datetime/timezone so parsing helpers return None instead of raising"
    - "Translate stream errors only around the iterator's next() call (generator wrapper), never around per-element code"
    - "Ruff 0.17 with target py314 formats multi-exception clauses without parentheses (PEP 758) unless they bind `as err`"
key-files:
  created:
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-11-red.{xml,json}
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-11-red-2.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-11-red-2-{guard,propagate}.json
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-11-red-3.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-11-red-3-{build-events,event}.json
  modified:
    - custom_components/xmltv_calendar/xmltv/timeparse.py
    - custom_components/xmltv_calendar/xmltv/parser.py
    - custom_components/xmltv_calendar/calendar.py
    - tests/test_timing.py
    - tests/xmltv/test_timeparse.py
    - tests/xmltv/test_parser.py
    - tests/test_calendar.py
key-decisions:
  - "01-11: parse_xmltv_time accepts offsets up to +-18:00 and written years 1900..2200 (inclusive); everything else returns None, which closes the OverflowError sites in normalize.py without touching it"
  - "01-11 (WR-06, planner decision): _STREAM_ERRORS keeps LookupError and ValueError because Expat raises them at read time (unknown encoding, multi-byte declaration, decode errors); WR-06 is closed by narrowing the scope to iterparse next() in _read_events, not by narrowing the tuple"
  - "01-11: multi-exception clauses use the PEP 758 unparenthesized form (`except ValueError, OverflowError:`) because ruff format 0.17 with target py314 rewrites the parenthesized form; plan grep criteria were checked against this form"
patterns-established:
  - "One malformed <programme> is always skipped and counted; FeedError is reserved for read/decode failures of the document"
requirements-completed: [EVT-05, AUT-01, AUT-02]
coverage:
  - id: D1
    description: "A feed with +2500/+0099 offsets, year 0001 and year 9999 (with and without stop) programmes and an unparsable stop loads as LOADED and get_events returns exactly the two valid programmes (ROADMAP SC3)"
    requirement: "EVT-05"
    verification:
      - kind: integration
        ref: "tests/test_timing.py#test_malformed_timestamps_never_break_the_calendar"
        status: pass
    human_judgment: false
  - id: D2
    description: "parse_xmltv_time returns None for out-of-range offsets/minutes/years and still parses +-18:00 and the 1900/2200 edges"
    requirement: "EVT-05"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_timeparse.py#test_valid_timestamps, #test_invalid_timestamps_return_none"
        status: pass
    human_judgment: false
  - id: D3
    description: "Each CR-01 timestamp variant skips only its programme (skipped_malformed == 1); an unparsable stop is inferred per D-12; a ValueError/OverflowError during conversion skips one programme; a KeyError propagates; Shift_JIS still raises a content-free FeedError"
    requirement: "EVT-05"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_parser.py#test_malformed_timestamp_skips_only_that_programme (6 cases)"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_parser.py#test_unparsable_stop_offset_infers_stop"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_parser.py#test_conversion_error_skips_only_that_programme (2 cases), #test_programming_error_is_not_reported_as_feed_error, #test_multibyte_encoding_declaration_raises_feed_error"
        status: pass
    human_judgment: false
  - id: D4
    description: "build_events skips an unbuildable match (year 9999 under Europe/Berlin, or ValueError) and the entity state returns None instead of raising"
    requirement: "AUT-01, AUT-02"
    verification:
      - kind: unit
        ref: "tests/test_calendar.py#test_build_events_skips_out_of_range_programme, #test_build_events_skips_value_error"
        status: pass
      - kind: integration
        ref: "tests/test_calendar.py#test_event_property_skips_out_of_range_match"
        status: pass
    human_judgment: false
  - id: D5
    description: "Parser hot-loop change keeps SRC-09 limits: 60 MB parse under 30 s and max loop gap under 250 ms"
    verification:
      - kind: other
        ref: "uv run pytest -q -m benchmark (feed.xml parse_seconds=2.78, max_loop_gap_ms=172.5; feed.xml.gz 2.92 s, 139.0 ms)"
        status: pass
    human_judgment: false
duration: 6min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 11: Malformed-Programme Containment (CR-01, WR-06) Summary

**`parse_xmltv_time` now range-checks offsets (minutes < 60, magnitude <= 18 h) and years (1900..2200) and never raises. The parser skips any programme whose conversion fails and only reports genuine read/decode failures as `FeedError`. The calendar skips matches that cannot become a `CalendarEvent`. One broken `<programme>` can no longer reject a feed, crash `parse()` or crash event building.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-14T14:14:59Z
- **Completed:** 2026-10-14T14:20:30Z
- **Tasks:** 3
- **Files modified:** 7 code/test files plus 9 RED-evidence artifacts

## Accomplishments

- **timeparse.py:** `_MAX_OFFSET_MINUTES = 18 * 60`, `_MIN_YEAR = 1900`, `_MAX_YEAR = 2200`. The year check runs on the written year for every variant (numeric offset, alpha zone, no offset per D-14). Offsets with minutes >= 60 or beyond 18 h return None before `_tz` is called. The datetime construction now catches `ValueError` and `OverflowError`.
- **parser.py:**
  - New generator `_read_events(reader)` wraps only `next()` on the iterparse iterator. `ET.ParseError` becomes `FeedError("invalid XML at line L, column C")` and `_STREAM_ERRORS` become `FeedError("unreadable feed: <Type> after N bytes")`, both `from None` with the same messages as before (T-01-12).
  - `_collect` consumes `_read_events` and guards `_programme(elem)` with `except ValueError, OverflowError:`, counting the programme in `skipped_malformed` (CR-01).
  - `parse()` keeps only the `StopIteration` -> "empty document" handler. A `KeyError` or any other programming error now keeps its traceback (WR-06).
- **calendar.py:** `build_events` and `XmltvCalendarEntity.event` catch `HomeAssistantError, OverflowError, ValueError`. A year-9999 match under Europe/Berlin is skipped with a debug log, and `event` returns None.
- **normalize.py is unchanged on purpose.** Its OverflowError sites can no longer be reached, because every Programme instant now comes from a 1900..2200 year. The year-0001/9999 cases of the parser table prove this end to end.

## Task Commits

1. **Task 1: Tracer, a feed with malformed timestamps still loads** (type tracer)
   - `0237355` test(01-11): RED, tracer plus timeparse and parser tables, evidence `01-11-red.{xml,json}`
   - `23ea4d7` feat(01-11): GREEN, range validation in `parse_xmltv_time` (only non-test file changed: timeparse.py)
   - Tracer feedback gate: interactive, `end-of-phase`, automated-only verify. Re-ran `uv run pytest tests/test_timing.py tests/xmltv/test_timeparse.py tests/xmltv/test_parser.py -q` (67 passed), then expanded.
2. **Task 2: Parser per-programme guard and read-only stream-error translation**
   - `9f41a3a` test(01-11): RED, guard/propagation/Shift_JIS tests, evidence `01-11-red-2*.{xml,json}`
   - `6a4c1f3` feat(01-11): GREEN, `_read_events`, per-programme guard, reduced `parse()` handlers
3. **Task 3: Calendar skips unbuildable matches**
   - `60d90af` test(01-11): RED, build_events and event-property tests, evidence `01-11-red-3*.{xml,json}`
   - `05fe9fe` fix(01-11): GREEN, widened except clauses in calendar.py

## TDD Gate Compliance

| Cycle | RED | GREEN | REFACTOR |
|-------|-----|-------|----------|
| Task 1 (tracer) | `0237355` | `23ea4d7` | none needed |
| Task 2 | `9f41a3a` | `6a4c1f3` | none needed |
| Task 3 | `60d90af` | `05fe9fe` (`fix(01-11)`) | none needed |

Each RED commit precedes its GREEN commit. Task 3's GREEN uses the `fix(01-11)` type because it repairs a crash in existing behaviour. The orchestrator objective allows `feat` or `fix`. The phase-level `feat(01-11)` gate check is met by `23ea4d7` and `6a4c1f3`.

**RED 1:** `test_malformed_timestamps_never_break_the_calendar` (`01-11-red.json`, report `01-11-red.xml`, 18 failed / 49 passed, exit 1). Classifier verdict: RED_EVIDENCE_OK (target_test_failed).
- Semantic assessment: the target ran and failed on the planned LOADED assertion. The entry was in SETUP_RETRY because `parse()` turned the `+2500` start offset into `FeedError 'unreadable feed: ValueError'` and rejected the whole feed. The supporting failures match the plan: the parser table fails with FeedError (+/-2500) and OverflowError (years 0001/9999) and keeps "Bad" for `+0099`; the stop-offset test fails with FeedError; the timeparse table returns datetimes (or raises ValueError) for every new invalid value. No import, collection or fixture fault.

**RED 2:** one report (`01-11-red-2.xml`, 3 failed / 29 passed, exit 1), two targets, both RED_EVIDENCE_OK (target_test_failed):
- `test_conversion_error_skips_only_that_programme[ValueError]` (`01-11-red-2-guard.json`). Semantic assessment: with `parse_xmltv_time` patched to raise for the Bad start, the ValueError case raised `FeedError 'unreadable feed: ValueError'` (the feed was rejected instead of one programme being skipped), and the OverflowError case escaped `parse()` uncaught. Both show the missing per-programme guard.
- `test_programming_error_is_not_reported_as_feed_error` (`01-11-red-2-propagate.json`). Semantic assessment: a KeyError from the patched `_programme` was caught by `_STREAM_ERRORS` (KeyError is a LookupError) and reported as `FeedError 'unreadable feed: KeyError'`, masking a programming error as a feed problem (WR-06).
- The Shift_JIS regression guard passed before and after, as planned.

**RED 3:** one report (`01-11-red-3.xml`, 3 failed / 6 passed, exit 1), two targets, both RED_EVIDENCE_OK (target_test_failed):
- `test_build_events_skips_out_of_range_programme` (`01-11-red-3-build-events.json`). Semantic assessment: under Europe/Berlin, `OverflowError: date value out of range` from `dt_util.as_local` (homeassistant/util/dt.py:182) inside `_to_event` escaped `build_events`, which only caught HomeAssistantError. The companion `test_build_events_skips_value_error` failed with the injected ValueError for the same reason.
- `test_event_property_skips_out_of_range_match` (`01-11-red-3-event.json`). Semantic assessment: setup loaded the entry, the index was replaced with a single year-9999 match, and reading `entity.event` raised OverflowError from `dt_util.as_local` instead of returning None.

**GREEN:** every target passes. Final runs:
- `uv run pytest -q -m "not benchmark"`: 238 passed, 1 skipped (pre-existing real-feed skip, D-15/01-09), 4 deselected
- `uv run pytest -q -m benchmark`: 4 passed, 1 skipped. feed.xml parse_seconds=2.78, max_loop_gap_ms=172.5; feed.xml.gz 2.92 s, 139.0 ms (SRC-09 limits: 30 s, 250 ms)
- `uv run ruff check . && uv run ruff format --check .`: clean

**REFACTOR:** none needed in any cycle.

## Files Created/Modified

- `custom_components/xmltv_calendar/xmltv/timeparse.py`: range constants, year/offset/minute validation, widened except, docstring lists every None case.
- `custom_components/xmltv_calendar/xmltv/parser.py`: `_read_events`, per-programme guard in `_collect`, reduced `parse()` handlers, rewritten `_STREAM_ERRORS` comment, updated `parse()` docstring. `Iterator` is imported under `TYPE_CHECKING`.
- `custom_components/xmltv_calendar/calendar.py`: both except clauses widened, comment above the `build_events` loop updated.
- `tests/test_timing.py`: `MALFORMED_FEED`, shared `_events` helper, `test_malformed_timestamps_never_break_the_calendar`.
- `tests/xmltv/test_timeparse.py`: `_utc` takes seconds; 4 valid and 10 invalid CR-01 cases.
- `tests/xmltv/test_parser.py`: `_good_plus` helper, the 6-case malformed-timestamp table, stop inference, conversion-error guard (2 cases), KeyError propagation, Shift_JIS guard.
- `tests/test_calendar.py`: out-of-range and ValueError `build_events` tests and the event-property test.

## Decisions Made

- The year window is 1900..2200 inclusive, applied to the written year. This keeps `start + default_duration` (D-12), `astimezone(UTC)` in normalize and `dt_util.as_local` in the calendar inside datetime's range.
- WR-06 planner decision: the `_STREAM_ERRORS` tuple still holds `LookupError` and `ValueError`, because Expat raises them while reading (unknown declared encoding, multi-byte encoding declaration, decode errors). WR-06 is closed by narrowing where the tuple applies (only iterparse `next()` in `_read_events`), not by shrinking the tuple.
- The minute and magnitude checks share one `if` to stay within Ruff's PLR0911 return limit. `>= 60` carries a `noqa: PLR2004`, since 60 minutes per hour is not a tunable constant.

## Fixed Review Findings

- **CR-01 (critical):** fixed. All three reproduction paths from 01-VERIFICATION.md are covered by passing tests: offset +2500 -> FeedError (tracer and parser table), year 0001/9999 -> OverflowError in parse (parser table), year 9999 in build_events (Task 3).
- **WR-06 (warning):** fixed. Only iterparse read/decode failures become `FeedError`. A KeyError from per-element code propagates (`test_programming_error_is_not_reported_as_feed_error`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Exception-tuple syntax forced by the formatter**
- **Found during:** Task 1 GREEN
- **Issue:** The plan's acceptance greps expect `except (ValueError, OverflowError):` and `except (HomeAssistantError, OverflowError, ValueError):`. Ruff 0.17 with `target-version = "py314"` rewrites unparenthesized-capable clauses to the PEP 758 form, so the parenthesized text fails `ruff format --check`, a hard gate. The parentheses stay only when the clause binds `as err` (as in `source.py`).
- **Fix:** Used the formatter's form: `except ValueError, OverflowError:` (timeparse.py, parser.py) and `except HomeAssistantError, OverflowError, ValueError:` (2x in calendar.py). The behaviour is identical. Equivalent greps: timeparse 1 hit, parser 1 hit, calendar 2 hits.
- **Commits:** 23ea4d7, 6a4c1f3, 05fe9fe

**2. [Rule 3 - Blocking] PLR0911 (too many returns) in parse_xmltv_time**
- **Found during:** Task 1 GREEN
- **Issue:** Separate returns for the minute check and the magnitude check gave 7 returns, over Ruff's limit of 6.
- **Fix:** Combined them into one condition: `if int(off_m) >= 60 or offset > _MAX_OFFSET_MINUTES`.
- **Commit:** 23ea4d7

**3. [Minor] Task 3 GREEN commit type**
- The plan text says `feat(01-11)`. `fix(01-11)` was used because the change repairs a crash, and the orchestrator objective explicitly allows it.

**Total deviations:** 3, all syntactic or naming. The behaviour matches the plan exactly.

## Issues Encountered

- The Bash tool runs zsh, so `${PIPESTATUS[0]}` was empty in the first Task 1 RED run. The RED run was repeated with `RC=$?` to record the real exit code (1). The committed report and record come from that repeated run.

## Known Stubs

None.

## User Setup Required

None.

## Next Phase Readiness

- 01-VERIFICATION.md `gaps[0]` (ROADMAP SC3, "a single malformed programme never breaks the calendar") is closed by tests at every layer. Phase 1 is ready for re-verification.

## Self-Check: PASSED

- All 7 code/test files and 9 RED-evidence files exist.
- Commits 0237355, 23ea4d7, 9f41a3a, 6a4c1f3, 60d90af and 05fe9fe are ancestors of HEAD.
