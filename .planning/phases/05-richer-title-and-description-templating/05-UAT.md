---
status: complete
phase: 05-richer-title-and-description-templating
source: [05-VERIFICATION.md]
started: 2026-10-23T22:03:55Z
updated: 2026-10-29T22:16:40.415Z
---

## Current Test

[testing complete]

## Tests

### 1. German UI walkthrough on ha-dev
expected: Formel 1 recipe shows the stripped title in preview and calendar; description recipe shows local time; restart logs no template warning for the old default; one custom old-syntax template logs exactly one warning with the calendar name.
result: pass

### 2. German error texts in the real form
expected: Loop, unknown filter, typo (titel), old syntax and runtime error on the sample programme read naturally; {template_error}, {variables}, {default_title} are substituted.
result: pass

### 3. hassfest and HACS action after push
expected: Both green (translations/strings, manifest without new requirements).
result: pass

### 4. Decision: regex validation bypass via map/select/reject with filter names as text
expected: Either extend validation to map/select/reject with regex_replace/regex_search (or reject those calls), or document the residual risk next to the set/tilde growth in ROADMAP and README.
result: pass

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
