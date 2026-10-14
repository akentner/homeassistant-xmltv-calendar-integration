---
phase: 01
review: 01-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "ReDoS mitigation is ineffective; one pattern plus one long title can hang an executor thread for good"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Peak memory is twice the download cap, and the 1 GiB decompressed cap does not bound retained objects"
  - id: WR-03
    severity: warning
    disposition: open
    title: "The invalid-regex error shows the wrong pattern when more than one field is invalid"
  - id: WR-04
    severity: warning
    disposition: open
    title: "A file source stores the resolved symlink target, so symlink-rotated feeds go stale"
  - id: WR-05
    severity: warning
    disposition: open
    title: "The README describes filter semantics the code does not implement"
  - id: WR-07
    severity: warning
    disposition: open
    title: "The year window does not bound duration; one programme with an absurd stop takes over the calendar state"
  - id: WR-08
    severity: warning
    disposition: open
    title: "Skipped malformed programmes are never reported, so the CR-01 fix makes broken feeds fail silently"
  - id: IN-01
    severity: info
    disposition: open
    title: "A failed refresh re-filters unchanged data and repeats the missing-channel warning"
  - id: IN-02
    severity: info
    disposition: open
    title: "The `already_in_progress` abort reason has no translation"
  - id: IN-03
    severity: info
    disposition: open
    title: "Limits are duplicated as literals in translations"
  - id: IN-04
    severity: info
    disposition: open
    title: "Inferred stops have no upper bound"
  - id: IN-05
    severity: info
    disposition: open
    title: "Only the first `<title>` is matched; other-language titles are ignored"
  - id: IN-06
    severity: info
    disposition: open
    title: "`iot_class` is `cloud_polling` for local-file sources too"
  - id: IN-07
    severity: info
    disposition: open
    title: "The HA floor in `hacs.json` (2026.3.0) is never tested"
  - id: IN-08
    severity: info
    disposition: open
    title: "The `hacs` job has no explicit `permissions` block"
  - id: IN-09
    severity: info
    disposition: open
    title: "The `forbid_loop_io` guard only covers `builtins.open`"
  - id: IN-10
    severity: info
    disposition: open
    title: "`monkeypatch.setattr(..., raising=False)` hides a renamed constant"
  - id: IN-11
    severity: info
    disposition: open
    title: "The encoding-error test cannot detect a lost `from None`, and the original error is still attached"
  - id: IN-12
    severity: info
    disposition: open
    title: "The \"empty document\" branch in `parse` is dead code"
  - id: IN-13
    severity: info
    disposition: open
    title: "`event` returns None when the current match cannot be built, hiding later valid matches"
  - id: IN-14
    severity: info
    disposition: open
    title: "`async_get_events` raises `OverflowError` for queries starting near `datetime.min`"
  - id: CR-01
    severity: critical
    disposition: open
    title: "One malformed programme timestamp kills the whole feed (and far-future dates crash event building)"
  - id: WR-06
    severity: warning
    disposition: open
    title: "`_STREAM_ERRORS` catches `ValueError` and `LookupError`, which turns programming bugs into \"invalid feed\""
open: 23
total: 23
recorded: 2026-10-14T14:27:50.530Z
---

# Phase 01: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-07 | warning | open | - |
| WR-08 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| IN-08 | info | open | - |
| IN-09 | info | open | - |
| IN-10 | info | open | - |
| IN-11 | info | open | - |
| IN-12 | info | open | - |
| IN-13 | info | open | - |
| IN-14 | info | open | - |
| CR-01 | critical | open | - (not in the current review) |
| WR-06 | warning | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
