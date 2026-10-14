---
gsd_state_version: "1.0"
current_phase: 01
current_phase_name: first-filtered-calendar
status: verifying
stopped_at: Completed 01-11-PLAN.md
last_updated: "2026-10-14T14:21:31.699Z"
last_activity: 2026-10-13
last_activity_desc: Phase 01 execution started
state_head: 05fe9fe301ff13db011253b0920cee2f7262dfe2
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 11
  completed_plans: 11
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-12)

**Core value:** Configured filters reliably turn a (possibly large) XMLTV feed into a calendar showing exactly the programmes the user cares about, with channel and start time clearly visible.
**Current focus:** Phase 01 — First Filtered Calendar

## Current Position

Phase: 01 (first-filtered-calendar) — READY TO EXECUTE
Plan: 11 of 11
Status: Phase complete — ready for verification
Last activity: 2026-10-13 — Phase 01 execution started

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 6 min | 3 tasks | 27 files |
| Phase 01 P02 | 4 min | 2 tasks | 7 files |
| Phase 01 P03 | 4 min | 2 tasks | 3 files |
| Phase 01 P04 | 6 min | 2 tasks | 9 files |
| Phase 01 P05 | 6 min | 3 tasks | 9 files |
| Phase 01 P06 | 10 min | 3 tasks | 13 files |
| Phase 01 P07 | 6 min | 3 tasks | 6 files |
| Phase 01 P08 | 4 min | 3 tasks | 4 files |
| Phase 01 P09 | 5 min | 3 tasks | 1 files |
| Phase 01 P10 | 5 min | 3 tasks | 0 files |
| Phase 01 P11 | 6min | 3 tasks | 7 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: Source = config entry (coordinator in `runtime_data`), calendar = config subentry
- [Init]: Vertical MVP roadmap (4 coarse phases); the pure `xmltv/` library is still built first, inside Phase 1
- [Init]: Plain `OptionsFlow` + exactly one diffing update listener; never `OptionsFlowWithReload`
- [Init]: Zero runtime deps (stdlib `iterparse` + `gzip` in executor); titles via restricted `str.format_map`, no Jinja
- [Phase 01]: 01-01 Task 1 approved: dev pins pytest-homeassistant-custom-component 0.13.372 (HA 2026.10.1) and ruff 0.17.0
- [Phase 01]: iot_class cloud_polling (most sources are internet feeds, like core remote_calendar)
- [Phase 01]: Parser passes a missing stop as stop == start; normalize infers any stop <= start; keep_after drop runs after normalize
- [Phase 01]: 01-02: dedup before grouping, keyed on (channel_id, UTC start, title), first occurrence wins
- [Phase 01]: 01-02: EventFields.uid narrowed to str; UID = <channel_id>-<UTC start>-<crc32(title):08x> (A7)
- [Phase 01]: 01-03: channel_regex parsed like include/exclude (multiline, IGNORECASE) and re.search-ed on the channel ID
- [Phase 01]: 01-03: missing_channels subtracts channel IDs seen in programmes, so programme-only channels are not reported missing
- [Phase 01]: 01-03: first_invalid_pattern checks line-count cap, then length cap, then re.compile per non-blank line
- [Phase 01]: 01-04: get_events over the cap returns the earliest-starting 5,000 matches of the range (start-sorted slice) with a debug log
- [Phase 01]: 01-04: MatchIndex sorts its own input (stable) instead of trusting caller order
- [Phase 01]: 01-04: boundary end-trigger test asserts event end 11:30 and firing by 11:31 (freezer runs the already-due alarm on the next tick)
- [Phase 01]: 01-05: LookupError and ValueError are also translated into content-free FeedError (unknown encoding declarations leak feed text via LookupError)
- [Phase 01]: 01-05: programme-only channels are synthesized as Channel(id, id) from all parsed programmes, before the keep_after drop
- [Phase 01]: 01-05: successful downloads log byte count and host only; size failures use translation key feed_too_large
- [Phase 01]: 01-06: SRC-09 max event-loop gap is 86-164 ms on the dev box (limit 250 ms), driven by gen2 GC pauses and the C-level sorts in normalize_programmes; yield_every only covers iterparse. Parser unchanged; heapq.merge is the candidate fix if CI or ha-host runs get close to the limit
- [Phase 01]: 01-06: brand icons asserted at exactly 256x256 / 512x512; workflow supply-chain checks parametrize over every file in .github/workflows
- [Phase 01]: 01-06: hassfest container clean locally (0 invalid integrations); generator gzip output is byte-reproducible (mtime 0) and target_bytes counts uncompressed XML
- [Phase 01]: 01-07 Task 2: sha256. Config entry unique_id = SHA-256 hex of <source_type>:<normalized locator> (url: / file: prefix); changing it needs async_migrate_entry + VERSION bump
- [Phase 01]: 01-07: entry.data stores the normalized URL (fragment dropped, query kept) or the resolved real path; the duplicate check runs before the flow probe
- [Phase 01]: 01-07: file read OSError shows file_not_found in the flow and unable_to_fetch at setup; file helpers keep builtin open() so forbid_loop_io sees loop calls
- [Phase 01]: 01-08: pattern fields stored as raw text; FilterSpec strips and skips blank lines at filter time
- [Phase 01]: 01-08: several invalid pattern fields each get invalid_regex; placeholders show the first bad line (channel_regex, include, exclude order)
- [Phase 01]: 01-08: the 01-01 diffing listener already met FLT-01; tests/test_init.py is its regression suite, __init__.py unchanged
- [Phase 01]: 01-09 Task 2: none. No real German feed excerpt committed in Phase 1; D-15 real-feed excerpt and scripts/trim_feed.py deferred
- [Phase 01]: 01-09: ha-dev published on host port 18123 via a transient compose override (ha-a holds 8123); compose.yml keeps 8123:8123
- [Phase 01]: 01-09: test_real_feed.py holds the full checks behind a module skip; XMLTV_REAL_FEED runs them on any local feed
- [Phase 01]: 01-10 Task 2: before the first push, at the user's request, host names were rewritten across the full local history of main (git filter-repo --replace-text: dev laptop -> dev-host, HA host -> ha-host, 78 hits). All SHAs changed (HEAD dcebd6f -> ffd5363); SHAs cited in 01-01..01-09 SUMMARYs are pre-rewrite (find commits by subject); local backup/pre-anonymize keeps the old history, unpushed. New text uses ha-host / dev-host only
- [Phase 01]: 01-10 Task 3: the initial push of main emitted no push event, so CI and Validate for ffd5363 were started via workflow_dispatch (both success: runs 38553243429, 38553246496); the next push is the first push-triggered run
- [Phase 01]: 01-10: Renovate is active on the public repo (PR #1 home-assistant/actions digest, PR #2 setup-uv v10.3.0, both green); merging is left to the user
- [Phase 01]: 01-11: parse_xmltv_time accepts offsets up to +-18:00 and written years 1900..2200; everything else returns None (CR-01)
- [Phase 01]: 01-11 (WR-06): _STREAM_ERRORS keeps LookupError/ValueError (Expat raises them at read time); scope narrowed to iterparse next() in _read_events
- [Phase 01]: 01-11: multi-exception clauses use PEP 758 unparenthesized form because ruff format 0.17 (py314) rewrites the parenthesized form

### Pending Todos

None yet.

### Blockers/Concerns

- No real XMLTV source yet: fixtures only; real feeds are needed to validate Phase 3 behaviour
- Parse time on `ha-host` hardware is unmeasured; the Phase 1 benchmark decides whether reload-on-change is an acceptable interim listener
- `SelectSelector` with thousands of channels is unverified (Phase 1 research flag)
- `iot_class` (`cloud_polling` vs `local_polling`) still open; decide in Phase 1
- Research suggested deferring FLT-09, EVT-07 and EVT-08 to v2, but REQUIREMENTS.md keeps them in v1 (mapped to Phases 2 and 4)
- Event-loop gap under the 60 MB benchmark is 86-164 ms on the dev box (limit 250 ms): CI benchmark job may be flaky on slower runners; 01-09 ran on the dev-laptop ha-dev only (60 MB parse 2.8 s in-container), ha-host still unmeasured (RESEARCH A2)

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| fixture | D-15 real German feed excerpt (`tests/fixtures/real_de_excerpt.xml`) plus `scripts/trim_feed.py`; `tests/xmltv/test_real_feed.py` skips until it exists | deferred (user decision "none", 01-09 Task 2: licensing risk in a public repo) | 2026-10-14 (01-09) | v1 |

## Session Continuity

Last session: 2026-10-14T14:21:31.644Z
Stopped at: Completed 01-11-PLAN.md
Resume file: None
