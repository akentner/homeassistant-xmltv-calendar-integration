---
phase: 03
review: 03-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "Daily refresh fires before its slot and runs twice (and burns a backoff step on failure)"
  - id: CR-02
    severity: critical
    disposition: open
    title: "An unexpected exception retries every second with a full download, unrecorded"
  - id: WR-01
    severity: warning
    disposition: open
    title: "\"Unchanged\" shortcuts skip the empty-feed check, so a feed that stops updating is never reported"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Setup from the flow-seeded cache never records a success (`last_success` stays None)"
  - id: WR-03
    severity: warning
    disposition: open
    title: "`test_identity.py` is unfrozen and its fixtures have expired, so it tests an entry in SETUP_RETRY"
  - id: IN-01
    severity: info
    disposition: open
    title: "Repairs issue survives unload and disable of the entry"
  - id: IN-02
    severity: info
    disposition: open
    title: "Cache seeding writes before the duplicate check of `async_create_entry`"
  - id: IN-03
    severity: info
    disposition: open
    title: "`sha256` is stored but never verified on read"
  - id: IN-04
    severity: info
    disposition: open
    title: "304 path without data reads the cache without the source check"
  - id: IN-05
    severity: info
    disposition: open
    title: "Diagnostics report `next_refresh` even when no timer is armed"
open: 10
total: 10
recorded: 2026-10-16T11:43:40.178Z
---

# Phase 03: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| CR-02 | critical | open | - |
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
