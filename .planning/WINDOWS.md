---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 1
total_count: 2
last_updated: 2026-10-14T00:21:07.631Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 01 | stub | custom_components/xmltv_calendar/xmltv/render.py | 24 | CalendarEvent uid is None until plan 01-02 sets a stable uid | fixed |  | 2026-10-12T22:38:35.240Z | 2026-10-12T22:45:03.614Z |
| 2 | 01 | skipped-test | tests/xmltv/test_real_feed.py | 23 | Real-feed acceptance suite skips until the D-15 real German excerpt is committed (deferred by user decision in 01-09 Task 2) | open |  | 2026-10-14T00:21:07.631Z |  |

````json
[
  {
    "id": 1,
    "kind": "stub",
    "phase": "01",
    "file": "custom_components/xmltv_calendar/xmltv/render.py",
    "line": 24,
    "description": "CalendarEvent uid is None until plan 01-02 sets a stable uid",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-10-12T22:38:35.240Z",
    "resolved_at": "2026-10-12T22:45:03.614Z",
    "milestone": null
  },
  {
    "id": 2,
    "kind": "skipped-test",
    "phase": "01",
    "file": "tests/xmltv/test_real_feed.py",
    "line": 23,
    "description": "Real-feed acceptance suite skips until the D-15 real German excerpt is committed (deferred by user decision in 01-09 Task 2)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-14T00:21:07.631Z",
    "resolved_at": null,
    "milestone": null
  }
]
````
