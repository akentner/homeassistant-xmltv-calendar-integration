---
phase: 02-precise-filters-preview
plan: 02
subsystem: filtering
tags: [regex, unicode, nfc, settings-contract, tdd]

requires:
  - phase: 01
    provides: "FilterSpec, compile_patterns, first_invalid_pattern, streaming parser with _text()"
provides:
  - "xmltv/settings.py: the stored calendar subentry contract (14 flat keys, vocabularies, ADVANCED_DEFAULTS, with_defaults, has_advanced, normalize_time)"
  - "NFC-normalized feed text in the parser and NFC-normalized pattern lines"
  - "FilterSpec.include_fields / exclude_fields (title, subtitle, description, category), element-wise matching"
  - "case_sensitive toggle for include/exclude; compile_patterns/first_invalid_pattern take keyword-only case_sensitive"
affects: [02-03 preview, 02-04 window/duration, 02-05, 02-06 templates, 02-07 flow, 02-08]

actuals:
  tokens: 44113    # chars/4 over the full realized diff (7760 for code + tests alone; the rest is JUnit/RED evidence)
  tasks: 3
  commits: 4
plan_head_before: dbaa561cfa3a039dd1ff3623fe98b61c14c85d06
plan_head_after: 886fe6c5cec0724238090c709765f080cb396407

tech-stack:
  added: []
  patterns:
    - "One pure contract module (settings.py) owns every stored key; readers go through with_defaults()"
    - "Feed text NFC at parse time, pattern lines NFC at compile time; never case-fold"

key-files:
  created:
    - custom_components/xmltv_calendar/xmltv/settings.py
    - tests/xmltv/test_settings.py
  modified:
    - custom_components/xmltv_calendar/xmltv/parser.py
    - custom_components/xmltv_calendar/xmltv/filter.py
    - tests/xmltv/test_parser.py
    - tests/xmltv/test_filter.py
    - tests/test_filtering.py

key-decisions:
  - "02-02 Task 2: flat. Stored keys sit beside the Phase 1 keys: include_fields, exclude_fields, case_sensitive, time_from, time_to, weekdays, min_duration, max_duration, title_template, description_template; field values title/subtitle/description/category; weekdays mon..sun (== homeassistant.const.WEEKDAYS); times HH:MM, durations int minutes, templates plain strings; the Advanced checkbox is never stored (has_advanced derives it)"
  - "02-02: normalize_time checks HH:MM[:SS] by ASCII pattern instead of time.fromisoformat, which on Python 3.14 accepts 24:00 (as 00:00), bare hours and UTC offsets"
  - "02-02: with_defaults returns exactly the 14 contract keys (unknown keys dropped); whitespace-only templates read as their defaults; NaN/inf durations read as None"

patterns-established:
  - "Tests build subentry data with settings.KEY_* constants, never literal key strings"
  - "Field values are yielded title, sub-titles, categories, description last, matched with any()"

requirements-completed: [FLT-05, FLT-06]

coverage:
  - id: D1
    description: "Umlaut patterns match whether the feed or the pattern uses composed or decomposed Unicode, end to end through calendar.get_events"
    requirement: FLT-06
    verification:
      - kind: integration
        ref: "tests/test_filtering.py#test_umlaut_pattern_matches_decomposed_feed"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_parser.py#test_text_is_nfc_and_ids_are_untouched"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_unicode_matching"
        status: pass
    human_judgment: false
  - id: D2
    description: "Include and exclude each apply to user-chosen fields (title, sub-title, description, category), each sub-title and category tested on its own"
    requirement: FLT-05
    verification:
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_field_and_case_table"
        status: pass
      - kind: integration
        ref: "tests/test_filtering.py#test_category_field_selection_end_to_end"
        status: pass
      - kind: integration
        ref: "tests/test_filtering.py#test_two_calendars_different_fields_same_refresh"
        status: pass
    human_judgment: false
  - id: D3
    description: "case_sensitive toggle for include/exclude; channel regex stays case-insensitive"
    requirement: FLT-06
    verification:
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_field_and_case_table[case-sensitive-*, channel-regex-stays-insensitive]"
        status: pass
    human_judgment: false
  - id: D4
    description: "Stored settings contract with tolerant, idempotent defaults; Phase 1 calendars behave unchanged"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_settings.py"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_filter.py#test_truth_table"
        status: pass
      - kind: unit
        ref: "tests/test_filtering.py#test_weekday_vocabulary_matches_home_assistant"
        status: pass
    human_judgment: false

duration: 7min
completed: 2026-10-15
status: complete
---

# Phase 2 Plan 02: Precise Text Matching Summary

**Include and exclude now match only the fields each calendar chooses (title, sub-title, description, category). Each sub-title and each category is tested on its own. There is a case-sensitive toggle, and feed text and patterns are NFC-normalized, so umlauts match whether they are composed or decomposed. All of this sits on a new pure contract module, `xmltv/settings.py`, which defines every stored Phase 2 calendar setting and reads it tolerantly.**

## Performance

- **Duration:** about 7 min
- **Started:** 2026-10-15T10:43:57Z
- **Completed:** 2026-10-15T10:50:36Z
- **Tasks:** 3 (Task 2 was a decision, resolved before dispatch)
- **Files modified:** 8 code/test files, plus 6 TDD evidence files

## Accomplishments
- `parser._text` returns NFC text. This covers titles, sub-titles, description, categories, episode and display names. Channel IDs stay byte-identical.
- `compile_patterns` and `first_invalid_pattern` NFC-normalize each line. They take a keyword-only `case_sensitive`, and nothing is ever case-folded.
- `FilterSpec` has two new fields, `include_fields` and `exclude_fields`. Both default to title plus sub-title, so Phase 1 data behaves as before. `_field_values` yields the title, then the sub-titles, then the categories, and the description last, and matching short-circuits with `any()`.
- `settings.py` is a pure module. It owns all 14 keys, the field and weekday vocabularies, `ADVANCED_DEFAULTS`, `with_defaults()`, `has_advanced()` and `normalize_time()`. `FilterSpec.from_mapping` reads everything through `with_defaults`.

## TDD Gate Compliance

| Cycle | RED | GREEN | REFACTOR |
|-------|-----|-------|----------|
| Task 1 (NFC tracer) | `2a509da` test(02-02) | `d2af162` feat(02-02) | none needed |
| Task 3 (fields, case, contract) | `a767209` test(02-02) | `886fe6c` feat(02-02) | none needed |

- **RED 1:** The target was `test_umlaut_pattern_matches_decomposed_feed[nfd-feed]` (02-02-red.json) and its sibling `[nfd-pattern]` (02-02-red-nfd-pattern.json). The classifier returned RED_EVIDENCE_OK (target_test_failed) for both.
  - Semantic check: both cases ran and failed on the planned `len(summaries) == 1` assertion (0 == 1). Neither the parser nor `compile_patterns` normalized, so NFC and NFD text never met.
  - The JUnit target is the parametrized name: the classifier rejects the bare function name as `no_target_test_failure`.
- **RED 2:** The targets were `test_category_field_selection_end_to_end` (02-02-red-2-fields.json) and `test_field_and_case_table[case-sensitive-lowercase-misses]` (02-02-red-2-case.json). Both returned RED_EVIDENCE_OK.
  - Semantic check: the end-to-end target showed `[]` instead of Sportschau and Tagesschau, and the case target matched Tagesschau despite `case_sensitive`. In both runs `FilterSpec` ignored the new keys. No import, collection or fixture fault.
  - `test_settings.py` failed at import of `with_defaults`. The plan expects this, and it is not counted as RED evidence.
- **GREEN:** All target tests and the full suite pass.

## Task Commits

1. **Task 1: Tracer, an umlaut pattern matches decomposed Unicode end to end:** `2a509da` (test), `d2af162` (feat). Tracer gate in end-of-phase mode: the automated verify was re-run after the commit (68 passed) before expanding.
2. **Task 2: Decide the stored key names:** decided as "flat" before dispatch. No commit; recorded in Decisions and in STATE.md.
3. **Task 3: Settings contract, field selection, case toggle:** `a767209` (test), `886fe6c` (feat)

## Files Created/Modified
- `custom_components/xmltv_calendar/xmltv/settings.py`: the stored subentry contract (keys, vocabularies, defaults, tolerant reader).
- `custom_components/xmltv_calendar/xmltv/filter.py`:
  - imports the keys from settings.py; `const.py` still imports `KEY_*` from here
  - field-scoped and case-aware matching, NFC pattern lines
  - removed `_fields`, `_str_set` and `_text`, which `with_defaults` and `_field_values` replace
- `custom_components/xmltv_calendar/xmltv/parser.py`: `_text` returns NFC text.
- `tests/xmltv/test_settings.py` (new):
  - defaults, 38 tolerant-read cases, garbage input
  - idempotency, fresh lists, `has_advanced`, `normalize_time`
- `tests/xmltv/test_filter.py`:
  - Q1–Q4 field and case table
  - specs do not leak into each other, `apply` is deterministic
  - Unicode equality (ß is not ss, NFD character class, `\S`/`\d` keep their meaning)
- `tests/xmltv/test_parser.py`: NFC text, and IDs left untouched.
- `tests/test_filtering.py`:
  - the NFD end-to-end case (two variants)
  - category field selection end to end
  - two calendars with different fields across one refresh
  - weekdays equal `homeassistant.const.WEEKDAYS`

## Decisions Made
- **Task 2 (user, before dispatch): "flat".** Final stored contract (D-06):
  - Phase 1 keys, unchanged: `channels`, `channel_regex`, `include`, `exclude`.
  - Phase 2 keys, at the same top level:

    | Key | Stored as | Default |
    |-----|-----------|---------|
    | `include_fields` | list ⊆ `title`, `subtitle`, `description`, `category` | `["title","subtitle"]` |
    | `exclude_fields` | same | `["title","subtitle"]` |
    | `case_sensitive` | bool | `False` |
    | `time_from` / `time_to` | `"HH:MM"` or None | None |
    | `weekdays` | list ⊆ `mon`..`sun` | `[]` (all days) |
    | `min_duration` / `max_duration` | int minutes ≥ 0, or None | None |
    | `title_template` | str | `"{channel}: {title}"` |
    | `description_template` | str | `""` |

  - The "Advanced options" checkbox is never stored; `has_advanced()` derives it.
- **`normalize_time` uses an ASCII pattern, not `time.fromisoformat`.** On Python 3.14, `fromisoformat` accepts "24:00" (as 00:00), bare hours and UTC offsets. `re.ASCII` keeps non-ASCII digits out.
- **`with_defaults` returns exactly the 14 keys.** It also:
  - drops unknown keys
  - reads whitespace-only templates as their defaults
  - reads NaN and inf durations as None
  - turns set-typed channels into a sorted list, so the stored shape is deterministic

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `time.fromisoformat` accepts "24:00", bare hours and offsets**
- **Found during:** Task 3 GREEN (`test_normalize_time[24:00-None]` failed).
- **Issue:** The plan said to accept times via `datetime.time.fromisoformat`. On Python 3.14 that turns "24:00" into "00:00" and also accepts "22" and "22:00+01:00".
- **Fix:** `normalize_time` now uses a full-match ASCII pattern `([01]\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?`.
- **Files modified:** custom_components/xmltv_calendar/xmltv/settings.py
- **Verification:** all `test_normalize_time` and time tolerant-read cases pass.
- **Committed in:** 886fe6c

**2. [Rule 3 - Blocking] RED targets need the parametrized JUnit name**
- **Found during:** Task 1 RED.
- **Issue:** The classifier rejects the bare `test_umlaut_pattern_matches_decomposed_feed` name, because JUnit reports the parametrized names.
- **Fix:** 02-02-red.json targets `[nfd-feed]`, and a companion record 02-02-red-nfd-pattern.json covers `[nfd-pattern]`. Both are RED_EVIDENCE_OK.
- **Committed in:** 2a509da

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** No scope change. The stored contract is exactly the planned "flat" one.

## Issues Encountered
None.

## User Setup Required
None. No external service configuration required.

## Next Phase Readiness
- 02-03, 02-04, 02-06 and 02-07 can read every setting through `settings.with_defaults()` and use `ADVANCED_DEFAULTS` and `has_advanced()`.
- Note for 02-04: `with_defaults` keeps any non-negative int duration, including very large ones. `timedelta(minutes=...)` overflows above about 1.4e15 minutes. Clamp the value there, or cap it in the flow.
- Benchmarks after the NFC change: 60 MB parse took 2.84 s, with a max event-loop gap of 56.7 ms (limit 250 ms). The memory benchmark passed.

## Verification
- `uv run pytest -q -m "not benchmark"`: 340 passed, 1 skipped
- `uv run pytest -q -m benchmark`: 4 passed, 1 skipped
- `uv run ruff check . && uv run ruff format --check .`: clean
- `uv run pytest tests/xmltv/test_purity.py -q`: 2 passed. settings.py imports only `math`, `re`, `types`, `typing`.

## Self-Check: PASSED
- Found: settings.py, test_settings.py, 02-02-red.json, 02-02-red-2-fields.json, 02-02-red-2-case.json
- Found commits: 2a509da, d2af162, a767209, 886fe6c (`evaluation-scope --plan 02-02` resolved 4 commits)
- Acceptance greps: `normalize("NFC"` in parser.py and filter.py; `casefold` count 0; `^KEY_CHANNELS = ` in filter.py count 0; `with_defaults(` in filter.py; `def with_defaults` and `def has_advanced` in settings.py

---
*Phase: 02-precise-filters-preview*
*Completed: 2026-10-15*
