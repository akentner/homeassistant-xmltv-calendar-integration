# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0.1 — v1.0 Release

**Shipped:** 2026-10-30 (v1.0.0 on 2026-10-26, v1.0.1 on 2026-10-30)
**Phases:** 5 | **Plans:** 47 | **Tasks:** 113 | **Commits:** about 450 since 2026-10-12

### What Was Built
- A filtered XMLTV calendar for Home Assistant: one config entry per source, one subentry per calendar, shared download and parse, streaming parser with no runtime requirements.
- Field-scoped, Unicode-safe regex, duration, time-window and weekday filters with a live preview and in-place editing.
- A resilient source layer: disk cache, conditional requests, backoff, a Repairs issue after 24 h of failures, diagnostics, schedule and timezone options.
- Automation extras (next-match sensor, new-match event, retained past matches, blueprint) and a tag-driven HACS release.
- Sandboxed Jinja templates for titles and descriptions with translated flow errors, local time and tested README recipes.

### What Worked
- Pure, HA-free library first (parser, filter, schedule, template engine), then thin HA wiring: nearly every behaviour had a fast table test.
- Plan-time threat registers per phase made the Phase 5 security audit mechanical: 16 of 17 threats closed with file and test evidence.
- Hostile-input corpora and size caps found sandbox and ReDoS issues before release.
- Release workflow that gates the tag on manifest version, CI, hassfest and HACS.

### What Was Inefficient
- Verification reports of Phases 1-5 went stale after later source changes (Phases 1-4 were never refreshed before the milestone closed).
- UAT test 4 was passed as "documented" while the README and ROADMAP text did not exist yet; the security audit found the gap.
- hassfest and HACS were only exercised by the tag run, so one UAT item waited for the release.
- Code review and security audit ran after the v1.0.0 tag, so two review warnings (WR-02, WR-03) needed a v1.0.1.

### Patterns Established
- Config entry = source, config subentry = calendar; changes apply in place through one diffing update listener.
- Templates compile once per calendar behind one render facade shared by entity, sensor, event and preview.
- Every user-facing flow error has an English and a German text, guarded by a code-derived completeness test.
- Quick tasks (`/gsd-quick`) for review findings, one atomic commit per finding with a regression test.

### Key Lessons
1. Run code review, security audit and verification before tagging, not after; a late finding costs a patch release.
2. A UAT "decision" pass must be checked against the repository (the promised doc or code change exists) before it counts.
3. Run Validate (hassfest, HACS) on pushes to `main`, so release-gate checks do not wait for the tag.
4. Refresh stale verification at milestone close (`/gsd-execute-phase N`), or accept the override explicitly as done here.

### Cost Observations
- Model mix and session count were not recorded for this milestone.
- Notable: planner, executor, reviewer and verifier subagents ran sequentially on the main working tree.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0.1 | n/a | 5 | First milestone: MVP slices, then hardening, release and templating |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0.1 | 1283 passed, 1 skipped | not measured | all (`requirements: []`) |

### Top Lessons (Verified Across Milestones)

1. (Needs a second milestone to verify.)
