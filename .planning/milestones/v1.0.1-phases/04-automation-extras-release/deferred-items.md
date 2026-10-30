# Deferred verification environment items

## 04-09 (2026-10-23)

- Existing `tests/xmltv/test_real_feed.py:26` acceptance test skips without `XMLTV_REAL_FEED`; the licensed excerpt remains deferred by the prior user decision. No fixture was added. Tracked in WINDOWS.md.
- Three existing shellcheck cases at `tests/test_repo_structure.py:388` skip because shellcheck is not installed. Package installation is outside this plan. Tracked in WINDOWS.md.
- Keep all eleven Phase 04 human verification items, prohibition judgments and EDGE-01..EDGE-17 assumptions pending. This execution supplies automated evidence only; 04-10 and 04-11 remain separate plans.
  status: acknowledged
