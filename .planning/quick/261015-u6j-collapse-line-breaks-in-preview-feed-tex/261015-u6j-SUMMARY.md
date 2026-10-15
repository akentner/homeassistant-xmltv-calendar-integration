---
phase: quick-261015-u6j
plan: 01
status: complete
subsystem: preview
tags: [preview, markdown-escaping, config-subentry-flow, tdd, WR-05]

requires:
  - phase: 02-precise-filters-preview
    provides: escape_markdown / format_line / build_preview (preview.py) and the subentry preview step that joins lines as a Markdown list (config_flow.py)
provides:
  - escape_markdown collapses every whitespace run (str-pattern \s+) to one ASCII space and strips the edges before HTML/Markdown/autolink escaping (WR-05)
  - Flow end-to-end test that feed line breaks in a channel name and a title keep one preview list line per match
  - Unit contract for whitespace collapsing, format_line single-line output and byte identity of plain single-line text
affects: [02-REVIEW WR-05 disposition (next code-review run), FLT-10 preview]

actuals:
  tokens: 1455  # chars/4 over code+test diff (5818 chars); 18535 incl. the committed RED junit/json evidence (74141 chars)
  tasks: 1
  commits: 2
plan_head_before: 43224567dcce0bba51c0e13b7bdc9bf75e168132
plan_head_after: 9b87e7f5c0150d61edb3d366e63183f8a7d34da0

tech-stack:
  added: []
  patterns:
    - "Preview feed text is normalised to a single line inside escape_markdown, before any escaping"

key-files:
  created:
    - .planning/quick/261015-u6j-collapse-line-breaks-in-preview-feed-tex/tdd-evidence/u6j-red.json
    - .planning/quick/261015-u6j-collapse-line-breaks-in-preview-feed-tex/tdd-evidence/u6j-red.xml
  modified:
    - custom_components/xmltv_calendar/xmltv/preview.py
    - tests/test_subentry_flow.py
    - tests/xmltv/test_preview.py

key-decisions:
  - "escape_markdown collapses every str-pattern \\s+ run, so NBSP (\\xa0), \\u202f, \\u3000 and \\x1c-\\x1f also become one ASCII space (intended: the preview renders as HTML where these look the same; pinned by the nbsp unit case)"
  - "Collapse runs as the first statement of escape_markdown; the HTML, Markdown and autolink escape passes and their order are unchanged"

requirements-completed: [FLT-10]

coverage:
  - id: D1
    description: "A channel display-name with a newline and a title with &#13; produce one preview list line per match in the subentry flow"
    requirement: "FLT-10"
    verification:
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_preview_keeps_one_line_per_match_despite_feed_line_breaks"
        status: pass
    human_judgment: false
  - id: D2
    description: "escape_markdown collapses all whitespace classes, keeps format_line single-line and leaves plain single-line text byte-identical"
    requirement: "FLT-10"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_preview.py#test_whitespace_runs_collapse_to_one_space"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_preview.py#test_feed_line_breaks_stay_on_one_preview_line"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_preview.py#test_single_line_text_is_byte_identical"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-10-15
---

# Quick 261015-u6j: Collapse line breaks in preview feed text (WR-05) Summary

**escape_markdown now collapses every `\s+` run to one space and strips the edges before escaping, so a newline in a feed channel name or a `&#13;` in a title can no longer split the subentry preview list into extra lists, an ordered list or an `<hr>`.**

## Performance

- **Duration:** ~5 min
- **Completed:** 2026-10-15T19:55Z
- **Tasks:** 1/1 (tracer, tdd)
- **Files modified:** 3 (1 production, 2 test) + 2 evidence files

## Accomplishments

- `custom_components/xmltv_calendar/xmltv/preview.py`: new `_WHITESPACE_RUNS = re.compile(r"\s+")`; `text = _WHITESPACE_RUNS.sub(" ", text).strip()` is the first statement of `escape_markdown`; docstring and comment block updated (WR-05).
- `tests/test_subentry_flow.py`: `test_preview_keeps_one_line_per_match_despite_feed_line_breaks` drives the real flow (aioclient_mock feed, coordinator parse, preview step) and asserts the exact `matches` placeholder plus `len(matches.splitlines()) == 2`.
- `tests/xmltv/test_preview.py`: new section "One line per match: whitespace collapsing (WR-05)" with 12 collapse ids, one format_line single-line test and 4 byte-identity guard ids (17 tests).

## Before / after (flow placeholder, 2 matches)

| | `matches` line 1 | splitlines() |
|---|---|---|
| Before | `- Tue 13.10. 14:00 · Sky\n1. Liga · Sky 1. Liga: Sport\r1. Bundesliga` | 4 |
| After | `- Tue 13.10. 14:00 · Sky 1. Liga · Sky 1. Liga: Sport 1. Bundesliga` | 2 |

Line 2 is `- Tue 13.10. 20:00 · Das Erste · Das Erste: Sportschau` in both cases.

## Task Commits

1. **RED:** `1132145` test(quick-261015-u6j): add failing tests for line breaks in preview feed text
2. **GREEN:** `9b87e7f` feat(quick-261015-u6j): collapse whitespace runs in preview feed text to one line

No REFACTOR commit (ruff format clean).

## TDD Gate Compliance

- RED record: `.planning/quick/261015-u6j-collapse-line-breaks-in-preview-feed-tex/tdd-evidence/u6j-red.json` (junit `u6j-red.xml`)
- Target: `tests/test_subentry_flow.py::test_preview_keeps_one_line_per_match_despite_feed_line_breaks`
- RED run: exit 1, 85 tests, 14 failed, 71 passed.
- `gsd_run check tdd-red-evidence --raw`: **RED_EVIDENCE_OK (target_test_failed)**
- semanticAssessment: the target ran and failed on its planned matches-equality assertion (`tests/test_subentry_flow.py:455`). escape_markdown leaves the `\n` in the channel display-name `Sky\n1. Liga` and the `\r` from `&#13;` in the title `Sport\r1. Bundesliga`, so the joined Markdown list has 4 lines for 2 matches. All 12 whitespace-collapse ids and the format_line single-line test fail for the same cause. The 4 byte-identity guard ids and all 67 pre-existing tests pass. No collection, import or fixture fault.
- Commit order: test (`1132145`) before feat (`9b87e7f`).
- GREEN: both files 85 passed; full suite 553 passed, 1 skipped, 4 deselected (baseline 535 + 18 new); `ruff check .` and `ruff format --check .` clean.

## Acceptance checks

- `-k test_preview_keeps_one_line_per_match_despite_feed_line_breaks`: 1 passed
- `-k "whitespace_runs_collapse or line_breaks_stay or byte_identical"`: 17 passed
- `git diff --numstat 4322456 -- tests/...`: 32/0 and 62/0 (no deletions, existing tests unedited)
- `git diff --name-only 4322456 -- custom_components`: only `xmltv/preview.py`
- `grep -c '_WHITESPACE_RUNS.sub(" ", text).strip()' preview.py`: 1

## Decisions Made

- `\s` under a str pattern also matches NBSP (`\xa0`), `\u202f`, `\u3000` and `\x1c`-`\x1f`. Collapsing these to one ASCII space is intended: the preview renders as HTML, where they look the same. The `nbsp` unit case pins this.

## Deviations from Plan

None in production code or test behaviour. One tooling note: the Edit tool wrote U+2028/U+2029 as literal characters instead of the `\u2028`/`\u2029` escape sequences (ruff RUF001 flagged them). They were replaced with the escape sequences before the RED run that produced the evidence, so the committed tests contain only escapes.

## Not addressed (out of scope)

- WR-05's disposition in `02-REVIEW.md` / `02-REVIEW-DISPOSITION.md` is left for the next code-review run.
- The review's separate suggestion that `clean_title` (render.py:88) should also replace `\r` for calendar event summaries was not addressed. It affects a different surface (calendar summaries, not the preview).

## Self-Check: PASSED

- FOUND: custom_components/xmltv_calendar/xmltv/preview.py, tests/test_subentry_flow.py, tests/xmltv/test_preview.py, tdd-evidence/u6j-red.json, tdd-evidence/u6j-red.xml
- FOUND commits: 1132145, 9b87e7f (ancestors of HEAD)
