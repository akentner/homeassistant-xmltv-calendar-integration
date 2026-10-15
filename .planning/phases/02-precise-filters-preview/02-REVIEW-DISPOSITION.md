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
    title: "Missing `reconfigure_successful` abort translation for the calendar edit flow, now in en and de (carried forward, still open)"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Nested-repetition guard rejects harmless fixed-count repeats (carried forward, still open)"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Several invalid fields share one error placeholder (carried forward, still open)"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "`escape_markdown` lets line breaks through, so feed text can break the preview list (new)"
  - id: IN-01
    severity: info
    disposition: open
    title: "\"Templates only, no refilter\" path is effectively dead; the comment is misleading (carried forward, still open)"
  - id: IN-02
    severity: info
    disposition: open
    title: "Unchecking \"Advanced options\" leaves hidden filters active without any hint, now in en and de (carried forward, still open)"
  - id: IN-03
    severity: info
    disposition: open
    title: "Basic step help texts are stale after Phase 2, now in en and de (carried forward, still open)"
  - id: IN-04
    severity: info
    disposition: fixed
    title: "`escape_markdown` does not escape `~`"
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
    title: "Deep-nesting test fixture depends on the interpreter's recursion limit and is duplicated (carried forward, still open)"
  - id: IN-08
    severity: info
    disposition: open
    title: "Preview weekday language follows the server, the surrounding text follows the user (new, made reachable by de.json)"
  - id: IN-09
    severity: info
    disposition: open
    title: "\"1 passende Sendungen\" / \"1 matching programmes\" (new)"
  - id: IN-10
    severity: info
    disposition: open
    title: "`test_de_keeps_literals` uses substring matching, so short numeric literals pass vacuously (new)"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "`OverflowError` from `re.compile` escapes pattern validation and crashes the flow (and entity setup)"
open: 13
total: 16
recorded: 2026-10-15T19:34:50.076Z
---

# Phase 02: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | fixed | quick 261015-u6j (9b87e7f) |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | fixed | 02-10 (debb599); not in the current review |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| IN-08 | info | open | - |
| IN-09 | info | open | - |
| IN-10 | info | open | - |
| CR-01 | critical | fixed | 02-09 (1ca6646); not in the current review |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
