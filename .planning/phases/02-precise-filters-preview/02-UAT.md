---
status: complete
phase: 02-precise-filters-preview
source: [02-VERIFICATION.md]
started: 2026-10-15T15:35:00Z
updated: 2026-10-15T18:37:34.894Z
---

## Current Test

[testing complete]

## Tests

### 1. ha-dev UAT walkthrough (steps 1-9 from 02-08-SUMMARY.md) plus repeat-overflow pattern
expected: Every step behaves as described in 02-08-SUMMARY.md "UAT Walkthrough"; 'a{99999999999}' shows invalid_regex with "the repetition number is too large" instead of "Unknown error". At step 5, record the success dialog shown after "Edit calendar" -> Save (WR-02).
result: pass
source: chrome-devtools MCP walkthrough on ha-dev (2026-10-15)
notes: |
  Steps 1-10 verified in the browser. Preview == saved calendar (30 events, Thu 22:00 - Fri 01:50, templated titles).
  Preview weekdays localized (Do/Fr). Edit pre-checks "Advanced options"; Back keeps all values.
  No "Downloaded ... bytes" line after two edits with custom_components.xmltv_calendar at debug.
  Nested repetition and a{99999999999} both show invalid_regex with the specific reason.
  WR-02: success dialog after reconfigure shows HA's generic "Die Neukonfiguration war erfolgreich".
  Observation: only translations/en.json exists, so flow labels (incl. weekday names) are English in a German UI.
  Tracebacks in the log come from chargefinder only.

### 2. Preview markdown rendering (02-03 D4)
expected: Open the preview with a feed whose channel names or titles contain markdown/HTML characters. The preview renders as a markdown list; *, _, [, <, & and backticks appear literally (known exception: '~~x~~' is struck through, IN-04).
result: issue
reported: "Checked via chrome-devtools MCP with a local feed (/media/xmltv/uat-markdown.xml): *, _, [, <, &, backticks, #, '1.', | and backslash render literally and '~~x~~' is struck through (IN-04, expected). Not covered by the expectation: a bare URL in a title ('[link](http://x.y)') is rendered as a clickable link (http://x.y autolinked)."
severity: minor

### 3. Backstop truth (02-02): concurrent per-calendar filtering is isolated
expected: Accept by structure (FilterSpec is a frozen dataclass, patterns compiled per calendar in from_mapping, EpgData immutable) or request a concurrency test.
result: pass
source: code inspection (2026-10-15)
notes: "FilterSpec is @dataclass(frozen=True) with frozenset/tuple fields and patterns compiled in from_mapping per calendar (filter.py:225-241); EpgData frozen with a tuple of frozen slotted Programme (model.py:19-55). No shared mutable state between calendars."

### 4. Judgment prohibitions (02-02 a/b, 02-03 c)
expected: (a) no programme-specific matching logic ('formel'/'Tatort' only as help-text examples); (b) user patterns only trimmed and NFC-normalised per line (no case folding, escaping, anchoring); (c) preview match set and titles equal the saved calendar (preview.py uses the same FilterSpec.from_mapping/EventTemplates.from_mapping calls and time zone as calendar.py).
result: pass
source: code inspection (2026-10-15)
notes: "(a) 'formel'/'Tatort' occur only in translations/en.json help texts; (b) _lines() only strips and NFC-normalises (filter.py:124-126), case handled solely by the re.IGNORECASE toggle; (c) preview.py:67-68 uses FilterSpec.from_mapping/EventTemplates.from_mapping like calendar.py:58/112, and both use dt_util.get_default_time_zone() (config_flow.py:452, calendar.py:149). Empirically confirmed in test 1 (preview == saved calendar)."

## Summary

total: 4
passed: 3
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-02-2
  truth: "Preview renders feed text literally; only the known '~~' exception (IN-04) differs"
  status: failed
  reason: "User reported: a bare URL in a programme title (e.g. http://x.y) is autolinked into a clickable link in the preview"
  severity: minor
  test: 2
  root_cause: "escape_markdown (xmltv/preview.py:24-35) escapes HTML entities and \ ` * _ [ ] # |, but HA's markdown renderer autolinks bare URLs (GFM autolink), so feed-controlled URLs become clickable in the config dialog"
  artifacts:
    - path: "custom_components/xmltv_calendar/xmltv/preview.py"
      issue: "escape_markdown does not neutralise bare URLs (and does not escape ~, IN-04)"
  missing:
    - "Neutralise autolinking of URLs in escape_markdown (e.g. break the scheme/'www.' pattern), plus a test"
  debug_session: ""
