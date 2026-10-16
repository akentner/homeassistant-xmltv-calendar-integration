---
status: testing
phase: 03-resilient-sources
source: [03-VERIFICATION.md]
started: 2026-10-16T18:25:00Z
updated: 2026-10-16T18:25:00Z
---

## Current Test

number: 1
name: ha-dev walkthrough (03-08 human-check)
expected: |
  Add a URL source (progress dialog, collapsed timezone section), restart HA, save options,
  run update_entity against the real feed, check curl -sI for ETag/Last-Modified, download
  diagnostics, check German texts. One download per setup; no download on restart or options
  save; update_entity sends validators; diagnostics redacted and show last_success right after
  setup; no tracebacks or blocking-call warnings.
awaiting: user response

## Tests

### 1. ha-dev walkthrough (03-08 human-check)
expected: One download per setup; no download on restart or options save; update_entity sends validators; diagnostics redacted and show last_success right after setup; German texts correct; no tracebacks or blocking-call warnings
result: [pending]

### 2. Debouncer serialization (backstop)
expected: Firing update_entity while a scheduled refresh runs makes the two refreshes run one after the other, with consistent health and cache
result: [pending]

### 3. Options save during a running parse (backstop)
expected: Only the new timezone options show after the reload
result: [pending]

### 4. Decide WR-04 / WR-05 / WR-01 dispositions
expected: Each of WR-01, WR-04, WR-05 has disposition fixed or deferred-with-reason in 03-REVIEW-DISPOSITION.md before the phase is marked complete (WR-04 is the swallowed-CancelledError fast retry; verifier recommends the small provisional-target fix before release)
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
