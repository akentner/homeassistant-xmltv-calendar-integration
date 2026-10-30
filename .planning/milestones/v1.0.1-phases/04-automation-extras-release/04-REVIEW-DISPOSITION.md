---
phase: 04
review: 04-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "Disabling the calendar entity silently breaks the next-match sensor, the new-match event and retention"
  - id: WR-01
    severity: warning
    disposition: open
    title: "A data refilter that supersedes a filter-edit refilter fires new-match events for the edit and skips the D-17 retention re-check"
  - id: IN-01
    severity: info
    disposition: open
    title: "Template-only edits trigger a full CONFIG refilter; the retention comparison is dead code"
  - id: IN-02
    severity: info
    disposition: open
    title: "`http_status` is recorded as `None` for an oversized download that the server answered with 200"
  - id: IN-03
    severity: info
    disposition: open
    title: "A non-standard HTTP status (>= 600) makes the persisted run record unreadable after a restart"
  - id: IN-04
    severity: info
    disposition: open
    title: "The match-store fingerprint ignores Home Assistant's time zone when `naive_timezone` is `local`"
  - id: IN-05
    severity: info
    disposition: open
    title: "`failure_reason` attribute values have no state translations"
  - id: IN-06
    severity: info
    disposition: open
    title: "The blueprint's `title` variable holds the rendered summary, unlike `title` everywhere else"
open: 8
total: 8
recorded: 2026-10-21T10:40:36.678Z
---

# Phase 04: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| WR-01 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved.
