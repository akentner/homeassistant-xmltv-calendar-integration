---
gsd_state_version: "1.0"
current_phase: 02
current_phase_name: Precise Filters & Preview
status: executing
stopped_at: Completed 02-09-PLAN.md
last_updated: "2026-10-15T18:59:37.829Z"
last_activity: 2026-10-15
last_activity_desc: Phase 02 execution started
state_head: 4345d537afb84cb212fcf1c3d0581e99da25cdfa
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 20
  completed_plans: 20
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-15)

**Core value:** Configured filters reliably turn a (possibly large) XMLTV feed into a calendar showing exactly the programmes the user cares about, with channel and start time clearly visible.
**Current focus:** Phase 02 — Precise Filters & Preview

## Current Position

Phase: 02 (Precise Filters & Preview) — EXECUTING
Plan: 9 of 9
Status: All plans executed (02-09 gap closure done) — ready for re-verification
Last activity: 2026-10-15 - Completed quick task 261015-su3: Add German translation de.json mirroring en.json with key/placeholder parity test

Progress: [███░░░░░░░] 25%

## Performance Metrics

**Velocity:**
- Total plans completed: 11
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 11 | - | - |

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
| Phase 02 P01 | 4 min | 2 tasks | 5 files |
| Phase 02 P02 | 7 min | 3 tasks | 8 files |
| Phase 02 P03 | 7 min | 3 tasks | 14 files |
| Phase 02 P04 | 6 min | 3 tasks | 6 files |
| Phase 02 P05 | 4 min | 2 tasks | 8 files |
| Phase 02 P06 | 6 min | 3 tasks | 8 files |
| Phase 02 P07 | 6 min | 2 tasks | 5 files |
| Phase 02 P08 | 5 min | 2 tasks | 4 files |
| Phase 02 P09 | 7 min | 2 tasks | 6 files |

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
- [Phase 02]: 02-01: device rename uses async_get_device_by_identifier((DOMAIN, subentry_id), entry_id); async_get_device raises in HA 2026.10
- [Phase 02]: 02-01: listener applies edited calendars in place over a copy of runtime.calendars (update listener calls run as concurrent tasks); the entity stores its (title, data) diff base before any await
- [Phase 02]: 02-01: uncompilable stored pattern gives an empty index at entity creation; on an edit the previous spec and matches are kept and the bad data still becomes the diff base, so it is logged once
- [Phase 02]: 02-02 Task 2: flat. Stored calendar keys sit beside the Phase 1 keys: include_fields, exclude_fields, case_sensitive, time_from, time_to, weekdays, min_duration, max_duration, title_template, description_template; field values title/subtitle/description/category; weekdays mon..sun (== homeassistant.const.WEEKDAYS); times "HH:MM", durations int minutes, templates plain strings; Advanced checkbox never stored (has_advanced derives it)
- [Phase 02]: 02-02: normalize_time checks HH:MM[:SS] by ASCII pattern, not time.fromisoformat (Python 3.14 accepts 24:00 as 00:00, bare hours and offsets)
- [Phase 02]: 02-02: with_defaults returns exactly the 14 contract keys (unknown keys dropped); whitespace-only templates read as defaults; NaN/inf durations read as None; large int durations are kept (clamp in 02-04)
- [Phase 02]: 02-03: preview_empty is a separate menu step id (translatable warning); its handler aliases async_step_preview because HA requires a handler for every shown step id
- [Phase 02]: 02-03: the calendar subentry still stores only the four Phase 1 keys; later plans extend _pending/_filter_data
- [Phase 02]: 02-03: preview weekday names keyed by the primary subtag of hass.config.language (de -> Mo..So, else Mon..Sun), no locale
- [Phase 02]: 02-03: escape_markdown turns & < > into entities, then backslash-escapes backslash, backtick, * _ [ ] # and pipe; parentheses stay
- [Phase 02]: 02-04: stored durations above timedelta.max minutes are clamped (huge min hides everything, huge max is unbounded); FilterSpec.from_mapping never raises OverflowError
- [Phase 02]: 02-04: nested-repetition check treats max > 1 as unbounded (so (a{2,3})* is rejected), also walks GROUPREF_EXISTS, and is fail-open (incl. RecursionError) when re._parser changes
- [Phase 02]: 02-04: weekdays without a window use the local start date; with a window the weekday is the day the window opened (D-11); apply(epg) without tz evaluates in UTC
- [Phase 02]: 02-05: Calendar edits save via async_update_and_abort only; the update listener applies them in place (no reload, no re-download)
- [Phase 02]: 02-05: The basic form submit merges into pending values instead of replacing them, so stored keys outside the form survive an edit
- [Phase 02]: 02-05: Channel selector options are sorted(feed IDs | stored IDs) so calendars with channels missing from the feed can be saved unchanged
- [Phase 02]: 02-06: Description edge cleanup keeps a leading dash/middle-dot bullet; strips whitespace and : , ; | / at the start and all separators at the end
- [Phase 02]: 02-06: Template-only calendar edits rebuild EventTemplates and write state without a refilter
- [Phase 02]: 02-06: TemplateError reasons exported as INVALID_TEMPLATE and UNKNOWN_PLACEHOLDER constants for the flow (02-07)
- [Phase 02]: 02-07: the title template is stored stripped; blank title stores DEFAULT_TITLE_TEMPLATE, blank description stores '' (default description)
- [Phase 02]: 02-07: a missing include_fields/exclude_fields key counts as an empty selection and is rejected with fields_required
- [Phase 02]: 02-07: time_incomplete goes on the missing side; time_equal on To, duration_order on Maximum; after an error the advanced form suggests exactly the submitted input
- [Phase 02]: 02-07: _load_pending sets self._show_advanced = False; 02-08 replaces that single assignment with has_advanced (D-03)
- [Phase 02]: 02-08: _show_advanced = has_advanced(self._pending) inside the run-once _load_pending, so Back and re-submits keep the user's own checkbox choice (D-03)
- [Phase 02]: 02-08: Task 2 is a regression suite (all cases green before changes); basic-step include/exclude validation now uses the calendar's case flag as a refactor (re.compile acceptance does not depend on IGNORECASE)
- [Phase 02]: 02-09: PATTERN_ERRORS = (re.error, OverflowError, RecursionError) is the single definition of an uncompilable pattern; _build_spec and first_invalid_pattern both catch it (CR-01)
- [Phase 02]: 02-09: pytest JUnit double-fail reports (call failure + teardown error) are rejected by the RED classifier; such RED records use a TAP rerun from a stdlib pytest reporter plugin

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1] UAT test 3 (calendar trigger with −5 min offset in a live automation) deferred; automated trigger tests cover it — see 01-UAT.md Deferred Follow-Ups
- [Phase 2] Review warnings accepted as non-blocking in Phase 1 UAT: WR-07 (absurd in-window stop → duration cap / FLT-08), IN-14 (get_events OverflowError near year 0001 → clamp in window.py); WR-08 (skipped_malformed not logged) → Phase 3 SRC-12
- [Phase 3] Only fixtures and the generated 60 MB feed are tracked; one reachable real URL source was exercised in Phase 1 UAT, but Phase 3 behaviour (caching, conditional requests) still needs real feeds
- [Phase 3] Parse time on `ha-host` hardware is unmeasured (dev-box ha-dev: 60 MB in 2.8 s, UI stayed responsive in Phase 1 UAT)
- Research suggested deferring FLT-09, EVT-07 and EVT-08 to v2, but REQUIREMENTS.md keeps them in v1 (mapped to Phases 2 and 4)
- Event-loop gap under the 60 MB benchmark is 86-164 ms on the dev box (limit 250 ms): CI benchmark job may be flaky on slower runners; 01-09 ran on the dev-laptop ha-dev only (60 MB parse 2.8 s in-container), ha-host still unmeasured (RESEARCH A2)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261015-su3 | Add German translation de.json mirroring en.json with key/placeholder parity test | 2026-10-15 | 4345d53 | [261015-su3-add-german-translation-de-json-mirroring](./quick/261015-su3-add-german-translation-de-json-mirroring/) |

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| fixture | D-15 real German feed excerpt (`tests/fixtures/real_de_excerpt.xml`) plus `scripts/trim_feed.py`; `tests/xmltv/test_real_feed.py` skips until it exists | deferred (user decision "none", 01-09 Task 2: licensing risk in a public repo) | 2026-10-14 (01-09) | v1 |

## Session Continuity

Last session: 2026-10-15T15:19:27.567Z
Stopped at: Completed 02-09-PLAN.md
Resume file: None
