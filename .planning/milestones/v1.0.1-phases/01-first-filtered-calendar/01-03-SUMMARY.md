---
phase: 01-first-filtered-calendar
plan: 03
subsystem: xmltv-library
tags: [xmltv, filter, regex, re, tdd, pytest, calendar]

requires:
  - phase: 01-01
    provides: "FilterSpec/FilterResult/InvalidPattern contracts, calendar.py refilter wiring with the D-04 warning, setup_xmltv harness"
provides:
  - "FilterSpec with channel_patterns, include and exclude (tuples of compiled re.Pattern), built by from_mapping from channels, channel_regex, include and exclude"
  - "Match = channel (selected IDs OR channel regex, both empty = all) AND (include empty OR any include) AND NOT any exclude; title and each sub-title tested separately, IGNORECASE"
  - "first_invalid_pattern with MAX_PATTERN_LENGTH = 300 and MAX_PATTERN_LINES = 50 (FLT-07 library side, for the 01-08 calendar flow)"
  - "FilterResult.missing_channels = selected IDs absent from both epg.channels and programme channel IDs (D-04)"
affects: [01-04, 01-08, 01-09, 02]

actuals:
  tokens: 2994   # chars/4 over the 3 authored source/test files (11,976 chars); committed RED evidence (JUnit XML + JSON records) excluded
  tasks: 2
  commits: 4
plan_head_before: 233bb74a831173ef5f23d7ca141dc8d3b7d05494
plan_head_after: 61f84641c511ab5cd7c86aff4e9940dbeb2b74aa

tech-stack:
  added: []
  patterns:
    - "Every pattern field (channel_regex, include, exclude) goes through compile_patterns: strip, skip blank lines, re.IGNORECASE"
    - "Channel predicate evaluated once per channel ID per apply() and cached in a dict, so each programme is visited once"
    - "Pattern tests assert InvalidPattern.pattern only, never the message text"

key-files:
  created:
    - tests/test_filtering.py
    - tests/xmltv/test_filter.py
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-03-red.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-03-red.json
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-03-red-2.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-03-red-2-exclude.json
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-03-red-2-channel-regex.json
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-03-red-2-once.json
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-03-red-2-missing.json
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-03-red-2-caps.json
  modified:
    - custom_components/xmltv_calendar/xmltv/filter.py

key-decisions:
  - "01-03: channel_regex is parsed like include/exclude (multiline, blank lines skipped, IGNORECASE) and re.search-ed on the channel ID"
  - "01-03: missing_channels also subtracts channel IDs seen in programmes, so a channel with programmes but no <channel> element is not reported missing"
  - "01-03: first_invalid_pattern checks each non-blank line in order (line-count cap, then length cap, then re.compile); the 51st line is the one reported for too many patterns"

patterns-established:
  - "RED tests that need not-yet-existing module constants use local literals, so RED fails on an assertion instead of ImportError"

requirements-completed: [FLT-02, FLT-03, FLT-04, FLT-07]

coverage:
  - id: D1
    description: "A calendar subentry with include '^Tagesschau$' shows only 'Das Erste: Tagesschau' in calendar.get_events"
    requirement: "FLT-03"
    verification:
      - kind: integration
        ref: "tests/test_filtering.py#test_include_pattern_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "Include OR-combined over title and each sub-title separately (anchored patterns stay exact), case-insensitive, blank lines ignored, empty include = all"
    requirement: "FLT-03"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_truth_table"
        status: pass
    human_judgment: false
  - id: D3
    description: "Exclude removes a programme when any line matches the title or a sub-title; blank exclude lines exclude nothing"
    requirement: "FLT-04"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_exclude_removes_matches"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_truth_table"
        status: pass
    human_judgment: false
  - id: D4
    description: "Channel selection = selected IDs OR channel regex on the ID, both empty = all; a channel matched both ways yields each programme once"
    requirement: "FLT-02"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_channel_regex_selects_by_id"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_selected_and_regex_channel_counted_once"
        status: pass
    human_judgment: false
  - id: D5
    description: "first_invalid_pattern rejects compile errors, lines over 300 characters and more than 50 non-blank lines; returns None for valid input"
    requirement: "FLT-07"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_first_invalid_pattern_caps"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_first_invalid_pattern_reports_compile_error"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_first_invalid_pattern_accepts_valid_input"
        status: pass
    human_judgment: false
  - id: D6
    description: "Selected channels absent from the feed are reported, warned once per refresh, and the calendar keeps the remaining channels (D-04)"
    requirement: "FLT-02"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_missing_channels_reported"
        status: pass
      - kind: integration
        ref: "tests/test_filtering.py#test_missing_channel_warning_once_per_refresh"
        status: pass
    human_judgment: false
  - id: D7
    description: "No programme- or use-case-specific matching logic in the filter engine"
    verification:
      - kind: other
        ref: "! grep -Eiq 'formel|formula|tatort' custom_components/xmltv_calendar/xmltv/filter.py"
        status: pass
    human_judgment: true
    rationale: "The prohibition is a judgment check; the grep covers known keywords only, a reviewer confirms no other hard-coded channel lists or keywords exist"

duration: 4min
completed: 2026-10-13
status: complete
---

# Phase 1 Plan 03: Filter Engine Summary

**`FilterSpec` now applies the full D-02 to D-08 rule: channel (selected IDs OR channel-ID regex, both empty = all) AND (include empty OR any include line) AND NOT any exclude line. Each pattern is tested case-insensitively against the title and each sub-title on its own. `first_invalid_pattern` enforces 300-character and 50-line caps, and `missing_channels` only names IDs the feed truly lacks. Both RED/GREEN cycles were classified `RED_EVIDENCE_OK`.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-12T22:47:27Z
- **Completed:** 2026-10-12T22:51:09Z
- **Tasks:** 2
- **Files modified:** 3 source/test files, plus 7 RED evidence files

## Accomplishments

- An include pattern stored on a calendar subentry filters the calendar end to end (`calendar.news` shows only "Das Erste: Tagesschau"). `calendar.py` is unchanged; it reads the new keys through `FilterSpec.from_mapping`.
- Anchored patterns behave per D-07: `^Tatort$` matches the title "Tatort" (P3) but not "Tatort: Der Fall" (P4), and `^Der Fall$` matches P3 through its sub-title.
- Blank or whitespace-only lines never compile to a match-everything pattern, so an empty exclude cannot empty a calendar (T-01-07).
- `first_invalid_pattern` returns `InvalidPattern(pattern, message)` for compile errors, over-long lines and too many lines. The calendar flow (01-08) can use it for `invalid_regex` errors (FLT-07).
- The D-04 warning fires once per refresh and names only `gone.de`. The calendar still shows the zdf.de programmes.

## Task Commits

1. **Task 1 (tracer): an include pattern on a calendar shows only matching programmes**
   - `883ca64` test(01-03): RED
   - `85205ad` feat(01-03): GREEN
   - Tracer feedback gate: no `blocking-human` gate, auto mode off, `human_verify_mode=end-of-phase`, automated-only `<verify>`. The verify was re-run (1 passed) and expansion continued with no checkpoint.
2. **Task 2: exclude, channel regex, validation caps and missing-channel reporting**
   - `a2b420b` test(01-03): RED
   - `61f8464` feat(01-03): GREEN
   - REFACTOR: none needed.

## TDD Gate Compliance

| Cycle | RED | GREEN | REFACTOR |
|-------|-----|-------|----------|
| Task 1 | `883ca64` | `85205ad` | none |
| Task 2 | `a2b420b` | `61f8464` | none |

Each `test(01-03)` commit precedes its `feat(01-03)` commit in git log.

- **RED 1** (`tdd-evidence/01-03-red.xml`, record `01-03-red.json`):
  - Target: `tests/test_filtering.py::test_include_pattern_end_to_end`. It failed on the summary-list assertion and got all four `basic.xml` programmes.
  - Classifier verdict: `RED_EVIDENCE_OK` (`target_test_failed`), 1 test, 1 failing.
  - Semantic assessment: the target was collected and setup succeeded (`calendar.news` registered). It failed on the planned assertion because the 01-01 `FilterSpec` ignored the include key. There was no import, collection or fixture fault.
- **GREEN 1:** `FilterSpec.include` plus a per-field `re.search`. The full suite reported 37 passed.
- **RED 2** (`tdd-evidence/01-03-red-2.xml`, one record per target). 31 tests ran and 8 failed. Each target was classified `RED_EVIDENCE_OK` (`target_test_failed`):
  - `test_exclude_removes_matches`: got (P3, P4) instead of `()`. Exclude was ignored.
  - `test_channel_regex_selects_by_id`: got all 7 instead of (P5, P6). The channel regex was ignored.
  - `test_selected_and_regex_channel_counted_once`: got (P3, P4) instead of (P3, P4, P5, P6). The regex was not OR-combined.
  - `test_missing_channels_reported`: got `{'gone.de', 'one.de'}` instead of `{'gone.de'}`. Programme channel IDs were not subtracted.
  - `test_first_invalid_pattern_caps`: got `None` for a 301-character line.
  - The other 3 failures were truth-table rows for the same missing behaviour (two exclude rows, one channel-regex row).
  - Semantic assessment: all failures are planned assertions, with no load, fixture or collection faults. The D-04 end-to-end test, the include rows and the compile-error and valid-input guards already passed, as expected from the 01-01 wiring and the Task 1 GREEN.
- **GREEN 2:** exclude, the channel predicate, the caps and the `missing_channels` subtraction. Task verify reported 31 passed, and the full suite reported 66 passed.

## Files Created/Modified

- `custom_components/xmltv_calendar/xmltv/filter.py`: `MAX_PATTERN_LENGTH`, `MAX_PATTERN_LINES`, capped `first_invalid_pattern`, `FilterSpec` fields `channel_patterns`, `include` and `exclude`, plus `_channel_selected`, `_text_matches` and the single-pass `apply`
- `tests/xmltv/test_filter.py`: the 18-row parametrized truth table (P1 to P7 fixture), the 5 named RED targets, compile-error and valid-input guards
- `tests/test_filtering.py`: the end-to-end include tracer and the D-04 once-per-refresh warning test
- `.planning/phases/01-first-filtered-calendar/tdd-evidence/01-03-red*.{xml,json}`: JUnit reports and classifier records

## Decisions Made

- `channel_regex` is parsed like include and exclude: multiline, blank lines skipped, `IGNORECASE`, and `re.search` on the channel ID.
- `missing_channels` = selected IDs − `epg.channels` keys − channel IDs seen in programmes, per the plan's implementation note. A channel that has programmes but no `<channel>` element is therefore not reported missing.
- `first_invalid_pattern` walks the non-blank lines in order and checks the line-count cap, then the length cap, then `re.compile`. For too many lines it reports the 51st line, with the message "more than 50 patterns".
- The include, exclude and channel-regex value for a key is read only when it is a `str`. Any other stored type counts as empty.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Literal caps in the test module instead of importing the constants**
- **Found during:** Task 2 RED
- **Issue:** Importing `MAX_PATTERN_LENGTH` and `MAX_PATTERN_LINES` before they exist makes the whole module fail at collection (`ImportError`). That is INVALID_RED, not an assertion failure.
- **Fix:** `tests/xmltv/test_filter.py` defines `MAX_PATTERN_LENGTH = 300` and `MAX_PATTERN_LINES = 50` locally. The acceptance greps confirm the real constants in `filter.py`.
- **Files modified:** tests/xmltv/test_filter.py
- **Committed in:** a2b420b

**2. [Rule 1 - Test correctness] Two RED targets made discriminating**
- **Found during:** Task 2 RED design
- **Issue:** With the 01-01 behaviour, the plan's literal cases for two targets already pass, so they could not serve as RED:
  - `channels ["zdf.de"]` + `channel_regex "^z"` gives (P3, P4) because zdf.de is already selected.
  - For `["gone.de", "zdf.de"]`, `missing_channels` is already `{"gone.de"}`.
- **Fix:** `test_selected_and_regex_channel_counted_once` now uses `channel_regex "^(z|sky)"` and asserts (P3, P4, P5, P6), each exactly once. `test_missing_channels_reported` selects `one.de`, which has programmes but no `<channel>` element. The plan's literal cases remain as truth-table rows, so every behaviour-block case is still asserted.
- **Files modified:** tests/xmltv/test_filter.py
- **Committed in:** a2b420b

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 test correctness)
**Impact on plan:** Test-side only. Every case from the behaviour block is asserted, and no interface signature changed.

## Issues Encountered

- `test_missing_channel_warning_once_per_refresh` already passed at RED 2. The 01-01 `calendar.py` logs one warning per refilter, and the old `missing_channels` already contained `gone.de`. It was not a named RED target and now serves as a regression guard for D-04.
- Running pytest with `-p no:logging` breaks phcc's `caplog` override ("recursive dependency involving fixture 'caplog'"). All committed evidence comes from runs without that flag.
- Commits land on `main`, which the orchestrator expected for this sequential run (`branching_strategy: none`, no remote).

## Known Stubs

None. The 01-01 stub "filter.py: channels only (no regex, include or exclude)" is resolved by this plan.

## Threat Flags

None. No new network, file or auth surface.
- T-01-06 is mitigated: caps enforced in `first_invalid_pattern`, and matching still runs only in the executor via the 01-01 refilter.
- T-01-07 is mitigated: blank lines are skipped before compiling. The blank-exclude truth-table row covers it.
- T-01-SC: no packages were added, and `uv.lock` is unchanged.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- 01-08 can call `first_invalid_pattern(text)` per field and map a non-None result to `errors={field: "invalid_regex"}` with `description_placeholders={"pattern": result.pattern, "error": result.message}`.
- `compile_patterns` still raises `re.error` on invalid input. Stored subentry data must be validated by the flow (01-08) before it reaches `from_mapping`.
- Plan verification:
  - `uv run pytest -q -m "not benchmark"`: 66 passed.
  - `ruff check` and `ruff format --check`: clean.
  - TDD gates: `test(01-03)` precedes `feat(01-03)` in both cycles, and the evidence files exist.

## Self-Check: PASSED

- `filter.py`, `tests/xmltv/test_filter.py`, `tests/test_filtering.py` and the 7 evidence files exist on disk.
- Commits 883ca64, 85205ad, a2b420b and 61f8464 are ancestors of HEAD: 4 commits since 233bb74, and `check evaluation-scope --plan 01-03 --commits-only` resolves all four.
- Every acceptance criterion was re-run and passed:
  - `tests/test_filtering.py` exits 0. Task 2 verify: 31 passed.
  - `IGNORECASE` and both cap constants are present in `filter.py`, and no formel/formula/tatort keywords appear there.
  - `calendar.py` has no 01-03 commit.
  - The tests never assert message text.

---
*Phase: 01-first-filtered-calendar*
*Completed: 2026-10-13*
