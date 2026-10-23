---
status: testing
phase: 05-richer-title-and-description-templating
source: [05-VERIFICATION.md]
started: 2026-10-23T22:03:55Z
updated: 2026-10-23T22:03:55Z
---

## Current Test

number: 1
name: German UI walkthrough on ha-dev
expected: |
  Preview and calendar show the stripped title, the local start time is correct, no warning for the old default title, exactly one warning for a custom old-syntax template.
awaiting: user response

## Tests

### 1. German UI walkthrough on ha-dev
expected: Formel 1 recipe shows the stripped title in preview and calendar; description recipe shows local time; restart logs no template warning for the old default; one custom old-syntax template logs exactly one warning with the calendar name.
result: [pending]

### 2. German error texts in the real form
expected: Loop, unknown filter, typo (titel), old syntax and runtime error on the sample programme read naturally; {template_error}, {variables}, {default_title} are substituted.
result: [pending]

### 3. hassfest and HACS action after push
expected: Both green (translations/strings, manifest without new requirements).
result: [pending]

### 4. Decision: regex validation bypass via map/select/reject with filter names as text
expected: Either extend validation to map/select/reject with regex_replace/regex_search (or reject those calls), or document the residual risk next to the set/tilde growth in ROADMAP and README.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
