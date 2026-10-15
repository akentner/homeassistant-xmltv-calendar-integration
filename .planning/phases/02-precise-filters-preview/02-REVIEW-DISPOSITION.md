---
phase: 02
review: 02-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "Basic step brings cleared fields back after a validation error (carried forward, still open)"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Missing `reconfigure_successful` abort translation for the calendar edit flow (carried forward, still open)"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Nested-repetition guard rejects harmless fixed-count repeats, which blocks saving Phase 1 calendars unchanged (carried forward, still open)"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Several invalid fields share one error placeholder, so the second field shows the first field's detail (carried forward, still open)"
  - id: IN-01
    severity: info
    disposition: open
    title: "\"Templates only, no refilter\" path is effectively dead; the comment is misleading (carried forward, still open)"
  - id: IN-02
    severity: info
    disposition: open
    title: "Unchecking \"Advanced options\" leaves hidden filters active without any hint (carried forward, still open)"
  - id: IN-03
    severity: info
    disposition: open
    title: "Basic step help texts are stale after Phase 2 (carried forward, still open)"
  - id: IN-04
    severity: info
    disposition: open
    title: "`escape_markdown` does not escape `~` (carried forward, still open)"
  - id: IN-05
    severity: info
    disposition: open
    title: "Channel regex lines are NFC-normalised, but channel IDs are not (carried forward, still open)"
  - id: IN-06
    severity: info
    disposition: open
    title: "Description cleanup strips legitimate trailing characters (carried forward, still open)"
  - id: IN-07
    severity: info
    disposition: open
    title: "Deep-nesting test fixture depends on the interpreter's recursion limit and is duplicated (new)"
  - id: CR-01
    severity: critical
    disposition: open
    title: "`OverflowError` from `re.compile` escapes pattern validation and crashes the flow (and entity setup)"
open: 12
total: 12
recorded: 2026-10-15T15:25:49.481Z
---

# Phase 02: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| CR-01 | critical | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
