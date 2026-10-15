---
status: testing
phase: 02-precise-filters-preview
source: [02-VERIFICATION.md]
started: 2026-10-15T15:35:00Z
updated: 2026-10-15T15:35:00Z
---

## Current Test

number: 1
name: ha-dev UAT walkthrough (steps 1-9 from 02-08-SUMMARY.md) plus repeat-overflow pattern
expected: |
  Every step behaves as described in 02-08-SUMMARY.md "UAT Walkthrough"; entering 'a{99999999999}'
  in the include field shows invalid_regex with "the repetition number is too large" instead of
  "Unknown error". At step 5, note what the success dialog after "Edit calendar" -> Save shows
  (WR-02: no translation for reconfigure_successful).
awaiting: user response

## Tests

### 1. ha-dev UAT walkthrough (steps 1-9 from 02-08-SUMMARY.md) plus repeat-overflow pattern
expected: Every step behaves as described in 02-08-SUMMARY.md "UAT Walkthrough"; 'a{99999999999}' shows invalid_regex with "the repetition number is too large" instead of "Unknown error". At step 5, record the success dialog shown after "Edit calendar" -> Save (WR-02).
result: [pending]

### 2. Preview markdown rendering (02-03 D4)
expected: Open the preview with a feed whose channel names or titles contain markdown/HTML characters. The preview renders as a markdown list; *, _, [, <, & and backticks appear literally (known exception: '~~x~~' is struck through, IN-04).
result: [pending]

### 3. Backstop truth (02-02): concurrent per-calendar filtering is isolated
expected: Accept by structure (FilterSpec is a frozen dataclass, patterns compiled per calendar in from_mapping, EpgData immutable) or request a concurrency test.
result: [pending]

### 4. Judgment prohibitions (02-02 a/b, 02-03 c)
expected: (a) no programme-specific matching logic ('formel'/'Tatort' only as help-text examples); (b) user patterns only trimmed and NFC-normalised per line (no case folding, escaping, anchoring); (c) preview match set and titles equal the saved calendar (preview.py uses the same FilterSpec.from_mapping/EventTemplates.from_mapping calls and time zone as calendar.py).
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
