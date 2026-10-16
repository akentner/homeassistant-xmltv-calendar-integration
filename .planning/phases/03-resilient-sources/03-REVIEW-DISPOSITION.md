---
phase: 03
review: 03-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "\"Unchanged\" shortcuts skip the empty-feed check, so a feed that stops updating is never reported (carried forward, still open)"
  - id: WR-04
    severity: warning
    disposition: open
    title: "A swallowed `CancelledError` on a timer-fired refresh still retries every second, unrecorded (CR-02 residual)"
  - id: WR-05
    severity: warning
    disposition: open
    title: "An unexpected exception while parsing the disk cache keeps the cache, so the source never downloads and stays in SETUP_RETRY"
  - id: IN-02
    severity: info
    disposition: open
    title: "Cache seeding runs before the final duplicate check, and now also overwrites the Store's health (carried forward, still open)"
  - id: IN-04
    severity: info
    disposition: open
    title: "A 304 without data in memory reads the cache without the source check (carried forward, still open)"
  - id: IN-06
    severity: info
    disposition: open
    title: "The seeded `fetched_at` and `last_success` are the time of the name step, not of the download"
  - id: IN-07
    severity: info
    disposition: open
    title: "Test hygiene in the new tests"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Daily refresh fires before its slot and runs twice (and burns a backoff step on failure)"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "An unexpected exception retries every second with a full download, unrecorded"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Setup from the flow-seeded cache never records a success (`last_success` stays None)"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "`test_identity.py` is unfrozen and its fixtures have expired, so it tests an entry in SETUP_RETRY"
  - id: IN-01
    severity: info
    disposition: open
    title: "Repairs issue survives unload and disable of the entry"
  - id: IN-03
    severity: info
    disposition: open
    title: "`sha256` is stored but never verified on read"
  - id: IN-05
    severity: info
    disposition: open
    title: "Diagnostics report `next_refresh` even when no timer is armed"
open: 14
total: 14
recorded: 2026-10-16T17:50:08.718Z
---

# Phase 03: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| IN-02 | info | open | - |
| IN-04 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| CR-01 | critical | fixed | 03-09 (af12ce8, 8283e60): `refresh_base` on success and failure path; re-review confirmed resolved |
| CR-02 | critical | fixed | 03-09 (4271ad6): one failure handler for every `Exception`; re-review confirmed resolved (residual gap tracked as WR-04) |
| WR-02 | warning | fixed | 03-10 (f0cefd7): setup download seeded as last_success; re-review confirmed resolved |
| WR-03 | warning | fixed | 03-10 (bb521c1, 77c9a14): identity tests frozen at fixture date, assert LOADED; re-review confirmed resolved |
| IN-01 | info | open | - (not in the current review) |
| IN-03 | info | open | - (not in the current review) |
| IN-05 | info | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
