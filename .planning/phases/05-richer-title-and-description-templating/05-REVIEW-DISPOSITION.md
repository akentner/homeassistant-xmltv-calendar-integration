---
phase: 05
review: 05-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "A second template error shows the first template's detail"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Unchecking \"Advanced options\" saves a stored template without validating it"
  - id: WR-03
    severity: warning
    disposition: open
    title: "The legacy-syntax check is bypassed by any text containing `{{` or `{%`"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`clean_description` does not honour \"at most one blank line\" or strip line edges"
  - id: IN-01
    severity: info
    disposition: open
    title: "Customised Phase 2-4 title templates are dropped silently on upgrade"
  - id: IN-02
    severity: info
    disposition: open
    title: "The preview renders descriptions and UIDs it never uses"
  - id: IN-03
    severity: info
    disposition: open
    title: "Misleading comment and an unsynchronised flag"
  - id: IN-04
    severity: info
    disposition: open
    title: "Edge-separator stripping can eat legitimate trailing characters, and the default description path is not cleaned"
open: 8
total: 8
---

# Phase 05: Code Review Disposition

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

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
