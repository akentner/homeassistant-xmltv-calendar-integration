---
phase: 02-precise-filters-preview
plan: 10
subsystem: preview
tags: [markdown, escaping, gfm, marked, autolink, config-flow, tdd, gap-closure]

requires:
  - phase: 02-precise-filters-preview
    provides: "escape_markdown / format_line / build_preview (02-05) and the preview menu step of the calendar subentry flow"
provides:
  - "escape_markdown neutralises GFM autolinks (scheme '://', 'www.', '@') and GFM strikethrough ('~')"
  - "_AUTOLINK_TRIGGERS module constant (compiled, re.IGNORECASE) applied after the character loop"
  - "End-to-end preview test with a URL in a feed title"
affects: [02-verification, 02-uat, preview, threat-T-02-05]

actuals:
  tokens: 27800   # chars/4 over the realized diff (111216 chars incl. JUnit/RED evidence); code+tests alone ~1660
  tasks: 2
  commits: 4      # MEASURED: git rev-list --count plan_head_before..HEAD
plan_head_before: 3b32cc477af0b96ad590f567ef70608f8ee6c92e
plan_head_after: debb599cf4f25ba3e9f2e20e6c07daef6990f2b8

tech-stack:
  added: []
  patterns:
    - "Escape GFM autolink triggers by backslash-prefixing the single punctuation each form needs, after the character loop so the backslash is never doubled"

key-files:
  created:
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-10-red.xml
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-10-red-escape.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-10-red-flow.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-10-red-2.xml
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-10-red-2-autolink.json
    - .planning/phases/02-precise-filters-preview/tdd-evidence/02-10-red-2-tilde.json
  modified:
    - custom_components/xmltv_calendar/xmltv/preview.py
    - tests/xmltv/test_preview.py
    - tests/test_subentry_flow.py

key-decisions:
  - "Autolink neutralisation via a CommonMark backslash escape before the trigger punctuation (':' of '://', '.' after 'www', '@'), not zero-width characters: renders and copies as the original text"
  - "The 'www' branch matches case-insensitively (re.IGNORECASE): older marked versions also link 'WWW.', and the escape renders identically either way"

patterns-established:
  - "escape_markdown order: HTML entities -> character loop (backslash first) -> _AUTOLINK_TRIGGERS"

requirements-completed: [FLT-10]

coverage:
  - id: D1
    description: "URL scheme separator ('://', any letter case, http/https/ftp) in feed text is backslash-escaped so the preview never autolinks it; the UAT reproduction '[link](http://x.y)' reaches the preview placeholder as '\\[link\\](http\\://x.y)'"
    requirement: FLT-10
    verification:
      - kind: unit
        ref: "tests/xmltv/test_preview.py#test_url_scheme_separator_is_escaped"
        status: pass
      - kind: integration
        ref: "tests/test_subentry_flow.py#test_preview_shows_feed_urls_as_plain_text"
        status: pass
    human_judgment: false
  - id: D2
    description: "'www.' hosts (any case, prefixed, after a scheme) and e-mail addresses (incl. mailto:) are escaped; '~' is escaped (IN-04)"
    requirement: FLT-10
    verification:
      - kind: unit
        ref: "tests/xmltv/test_preview.py#test_www_and_email_are_not_autolinked"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_preview.py#test_tilde_is_escaped"
        status: pass
    human_judgment: false
  - id: D3
    description: "UAT test 2 re-check on ha-dev: the HA frontend renders URL, www. and e-mail titles as plain non-clickable text and '~~strike~~' literally, with no stray backslash"
    requirement: FLT-10
    verification: []
    human_judgment: true
    rationale: "Only the HA frontend's own Markdown renderer (marked GFM in the markdown worker) decides whether text becomes a link; pytest checks the escaped strings, not the rendered DOM"

duration: 4min
completed: 2026-10-15
status: complete
---

# Phase 02 Plan 10: Preview Autolink and Strikethrough Escaping Summary

**escape_markdown now backslash-escapes the ':' of '://', the '.' after 'www' (case-insensitive), every '@' and every '~', so feed URLs, hosts, e-mail addresses and strikethrough render as literal, non-clickable text in the config-flow preview (G-02-2, IN-04)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-15T19:23:17Z
- **Completed:** 2026-10-15T19:26:49Z
- **Tasks:** 2
- **Files modified:** 3 source/test files (+6 TDD evidence files)

## Accomplishments

- G-02-2 closed in code. A bare or Markdown-wrapped URL in a feed title (`[link](http://x.y)`, `HTTP://X.Y`, `ftp://…`) no longer becomes a GFM autolink in the preview. `www.` hosts and e-mail addresses (including `mailto:`) are neutralised as well.
- IN-04 fixed. `~` is in `_MARKDOWN_CHARS`, so `~~Abgesagt~~` and `~x~` are not struck through.
- Each escape is a CommonMark escape of ASCII punctuation, so the rendered preview shows the feed text character for character. Strings without triggers are byte-identical to before (`Formel 1: Rennen`, `javascript:x`, `C:\path`).
- Verifier spot-check prints `\[link\](http\://x.y) www\.a.de u\@b.de \~\~x\~\~`, exactly as planned.

## Task Commits

1. **Task 1 (tracer): URL scheme separator escaped end to end**
   - RED `81be08a`: test(02-10): add failing tests for escaped URL scheme separator in preview
   - GREEN `acfe879`: feat(02-10): escape URL scheme separator so preview URLs are not autolinked
   - REFACTOR: none needed
2. **Task 2: www., e-mail addresses and '~' render literally**
   - RED `7223462`: test(02-10): add failing tests for www., e-mail and tilde escaping in preview
   - GREEN `debb599`: feat(02-10): neutralise www., e-mail and tilde in preview feed text
   - REFACTOR: none needed

**Plan metadata:** see the docs(02-10) commit that contains this SUMMARY.

## TDD Record

### Task 1 RED

- Command: `uv run pytest tests/xmltv/test_preview.py tests/test_subentry_flow.py -q --junitxml=.planning/phases/02-precise-filters-preview/tdd-evidence/02-10-red.xml`. Exit 1, with 6 failed and 51 passed.
- Failing tests, all on their equality assertion: the ids http, https-path, upper-case, ftp and markdown-link of `test_url_scheme_separator_is_escaped`, plus `test_preview_shows_feed_urls_as_plain_text`.
- **02-10-red-escape.json** (target `test_url_scheme_separator_is_escaped[http]`): RED_EVIDENCE_OK (target_test_failed).
  - Semantic assessment: the target executed and failed on its planned equality assertion. escape_markdown leaves `://` untouched, so the missing backslash before ':' is the cause. The other scheme ids fail the same way. No collection, import or fixture fault.
- **02-10-red-flow.json** (target `test_preview_shows_feed_urls_as_plain_text`): RED_EVIDENCE_OK (target_test_failed).
  - Semantic assessment: the target ran the real subentry flow through to the preview menu. The type, step_id and count assertions passed. It then failed on the planned `matches` equality, because the scheme separator reaches the placeholder unescaped (`…(http://x.y)`). No setup or fixture fault.

### Task 1 GREEN

- Added `import re` and `_AUTOLINK_TRIGGERS = re.compile(r":(?=//)")`. escape_markdown prefixes each match with one backslash after the `_MARKDOWN_CHARS` loop.
- Tracer gate: interactive run, `end-of-phase` mode, and the verify step is automated only. So I re-ran `<verify>`: 57 passed, no "Lingering". Then I moved on to Task 2.

### Task 2 RED

- Command: `uv run pytest tests/xmltv/test_preview.py -q --junitxml=.planning/phases/02-precise-filters-preview/tdd-evidence/02-10-red-2.xml`. Exit 1, with 10 failed and 27 passed.
- Failing tests: all 8 ids of `test_www_and_email_are_not_autolinked` and both ids of `test_tilde_is_escaped`. scheme-and-www failed only on the `www\.` part.
- **02-10-red-2-autolink.json** (target `test_www_and_email_are_not_autolinked[email]`): RED_EVIDENCE_OK (target_test_failed).
  - Semantic assessment: the target failed on its planned equality, because no backslash is added before '@'. All 8 autolink ids fail on the missing backslash, before either the '.' after 'www' or the '@'. All Task 1 ids and the existing escaping tests pass.
- **02-10-red-2-tilde.json** (target `test_tilde_is_escaped[strike-double]`): RED_EVIDENCE_OK (target_test_failed).
  - Semantic assessment: `~` is not in `_MARKDOWN_CHARS`, so no backslash is added (IN-04). strike-single fails the same way. No collection, import or fixture fault.

### Task 2 GREEN

- `_MARKDOWN_CHARS` gained "~", with the backslash still first.
- `_AUTOLINK_TRIGGERS` widened to `(?<=www)\.|:(?=//)|@`, compiled with `re.IGNORECASE`.
- The module comment now names the three GFM autolink forms and the case rule.
- The commit touches only `custom_components/xmltv_calendar/xmltv/preview.py`.

### Guards that passed before the change

- The `plain-colon` id (`Formel 1: Rennen` stays unchanged) passed in the Task 1 RED run.
- `test_markdown_and_html_in_feed_text_are_escaped` (`[Link](javascript:x)` keeps its colon) and `test_backslash_and_backtick_are_escaped_and_parentheses_kept` (`C:\path` becomes `C:\\path`) passed in both RED runs and after GREEN.
- `git diff 81be08a^..acfe879 -- tests/xmltv/test_preview.py` adds lines only. The one exception is the changed import line.

### TDD Gate Compliance

- Each task has a RED `test(02-10)` commit before its GREEN `feat(02-10)` commit. No violations.

## Files Created/Modified

- `custom_components/xmltv_calendar/xmltv/preview.py`: adds `import re`, `~` in `_MARKDOWN_CHARS`, the `_AUTOLINK_TRIGGERS` constant applied after the character loop, and the extended module comment.
- `tests/xmltv/test_preview.py`: imports escape_markdown and adds `test_url_scheme_separator_is_escaped` (6 ids), `test_www_and_email_are_not_autolinked` (8 ids) and `test_tilde_is_escaped` (2 ids).
- `tests/test_subentry_flow.py`: adds `test_preview_shows_feed_urls_as_plain_text`.
- `.planning/phases/02-precise-filters-preview/tdd-evidence/02-10-red*.{xml,json}`: RED evidence (2 JUnit reports, 4 records).

## Decisions Made

- I used a backslash escape before the trigger punctuation instead of zero-width characters. It works the same way as the existing escapes, and URLs still copy correctly. This was decided during planning and executed as written.
- The `www` branch is case-insensitive. It costs nothing, and older marked versions link `WWW.` too.

## Deviations from Plan

None. The plan executed exactly as written.

- Process note: per the orchestrator's sequential-mode instruction, commits went to `main`. `branching_strategy` is `none`, and the orchestrator accepted continuing on main. `git.base-branch --is-protected main` reports `true`, so the generic executor HEAD assertion would have halted. I followed the orchestrator's explicit directive instead, as previous phase-02 plans did.

## Verification

- `uv run pytest -q`: 539 passed, 1 skipped. The plan baseline was 517 passed and 1 skipped. The difference is the 17 new tests here plus the quick-task translation tests.
- `uv run ruff check . && uv run ruff format --check .`: clean.
- Spot-check: `escape_markdown('[link](http://x.y) www.a.de u@b.de ~~x~~')` returns `\[link\](http\://x.y) www\.a.de u\@b.de \~\~x\~\~`, with single backslashes and no doubled backslash.

## Issues Encountered

None.

## Pending End-of-Phase Human Check (UAT re-check on ha-dev)

This is harvested from Task 2's `<human-check>` and does not block this plan:

1. Restart ha-dev, which bind-mounts this repo's `custom_components/xmltv_calendar`, so it loads the new preview.py.
2. In `/home/akentner/Projects/dev/media/xmltv/uat-markdown.xml` (mounted as `/media/xmltv/uat-markdown.xml`), move every programme's start and stop into the future. The current entries end on 2026-10-16 00:50Z.
3. In the same file, add the titles 'Info: www.example.de', 'Mail: user@example.de' and 'HTTP://X.Y'.
4. Reload the source entry. Open "Add calendar" with no filters and go to the preview.
5. Expected results:
   - `[link](http://x.y)`, `www.example.de`, `user@example.de` and `HTTP://X.Y` show as plain, non-clickable text, and the preview list DOM contains no link element.
   - `~~strike~~ test` shows both tilde pairs and is not struck through.
   - *, _, [, <, &, backticks, #, '1.', | and the backslash still render literally.
   - No stray backslash is visible.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- G-02-2 and IN-04 are closed in code, pending the UAT re-check above. The IN-04 review disposition can move to `fixed`.
- Phase 02 is ready for re-verification.

## Self-Check: PASSED

- All 3 modified files and 6 evidence files exist on disk.
- Commits 81be08a, acfe879, 7223462 and debb599 are ancestors of HEAD.
- Acceptance criteria for both tasks were re-run and all pass. The plan-level verification commands pass.

---
*Phase: 02-precise-filters-preview*
*Completed: 2026-10-15*
