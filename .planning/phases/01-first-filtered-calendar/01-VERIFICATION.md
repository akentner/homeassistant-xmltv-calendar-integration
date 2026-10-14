---
phase: 01-first-filtered-calendar
verified: 2026-10-14T12:30:00Z
status: gaps_found
score: 76/88 must-haves verified
covered_files: [".github/workflows/ci.yml", ".github/workflows/validate.yml", ".planning/phases/01-first-filtered-calendar/01-01-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-01-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-02-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-02-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-03-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-03-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-04-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-04-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-05-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-05-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-06-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-06-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-07-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-07-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-08-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-08-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-09-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-09-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-10-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-10-SUMMARY.md", ".ruff.toml", "LICENSE", "README.md", "custom_components/xmltv_calendar/__init__.py", "custom_components/xmltv_calendar/calendar.py", "custom_components/xmltv_calendar/config_flow.py", "custom_components/xmltv_calendar/const.py", "custom_components/xmltv_calendar/coordinator.py", "custom_components/xmltv_calendar/data.py", "custom_components/xmltv_calendar/manifest.json", "custom_components/xmltv_calendar/source.py", "custom_components/xmltv_calendar/translations/en.json", "custom_components/xmltv_calendar/xmltv/__init__.py", "custom_components/xmltv_calendar/xmltv/filter.py", "custom_components/xmltv_calendar/xmltv/model.py", "custom_components/xmltv_calendar/xmltv/normalize.py", "custom_components/xmltv_calendar/xmltv/parser.py", "custom_components/xmltv_calendar/xmltv/render.py", "custom_components/xmltv_calendar/xmltv/timeparse.py", "custom_components/xmltv_calendar/xmltv/window.py", "docs/assets/icon.svg", "hacs.json", "pyproject.toml", "renovate.json", "scripts/generate_benchmark_feed.py", "tests/__init__.py", "tests/conftest.py", "tests/fixtures/basic.xml", "tests/fixtures/edge_cases.xml", "tests/fixtures/latin1.xml", "tests/test_calendar.py", "tests/test_config_flow.py", "tests/test_filtering.py", "tests/test_identity.py", "tests/test_ingestion.py", "tests/test_init.py", "tests/test_repo_structure.py", "tests/test_source.py", "tests/test_subentry_flow.py", "tests/test_timing.py", "tests/test_tracer.py", "tests/xmltv/__init__.py", "tests/xmltv/conftest.py", "tests/xmltv/test_benchmark.py", "tests/xmltv/test_filter.py", "tests/xmltv/test_normalize.py", "tests/xmltv/test_parser.py", "tests/xmltv/test_purity.py", "tests/xmltv/test_real_feed.py", "tests/xmltv/test_render.py", "tests/xmltv/test_timeparse.py", "tests/xmltv/test_window.py"]
covered_digest: "v3:sha256:bdf8e931b517c632b138666ba065ee441043328b7e35f540aec87cedc4da7e5a"
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "ROADMAP SC3: a single malformed programme never breaks the calendar (with plan truths 01-02 #1/#4, 01-04 #1/#7, 01-05 #7: invalid timestamps return None, unparsable programmes are skipped and counted, one malformed programme never fails the parse, get_events never raises, a match that cannot become a CalendarEvent is skipped)"
    status: failed
    reason: "CR-01 reproduced by the verifier with the project venv. (1) One programme with start offset '+2500' makes parse() raise FeedError('unreadable feed: ValueError ...'): the whole feed is rejected and the valid programme in the same feed is lost. (2) One programme at year 0001 (+0100) or year 9999 (-0100, or +0000 without stop) makes parse() raise an uncaught OverflowError from normalize.py (astimezone / start + default_duration). (3) A year-9999 programme that survives parsing makes calendar.build_events() raise OverflowError from dt_util.as_local (Europe/Berlin); build_events and the event property only catch HomeAssistantError. Existing tests (test_skips_malformed_programmes, test_invalid_timestamps_return_none, test_build_events_skips_invalid) cover only values that fail the regex or datetime() and miss these paths."
    artifacts:
      - path: "custom_components/xmltv_calendar/xmltv/timeparse.py"
        issue: "_tz() builds timezone(timedelta(minutes=offset)) outside the try block, so an offset >= 24 h raises ValueError instead of returning None; off_m >= 60 is accepted silently (e.g. '+0099'); instants outside datetime range are not rejected"
      - path: "custom_components/xmltv_calendar/xmltv/normalize.py"
        issue: "start.astimezone(UTC) (line 53) and start + default_duration (line 33) raise OverflowError for extreme years"
      - path: "custom_components/xmltv_calendar/xmltv/parser.py"
        issue: "_STREAM_ERRORS (incl. ValueError) wraps per-programme conversion, so one bad element becomes a whole-feed FeedError; OverflowError is not handled at all"
      - path: "custom_components/xmltv_calendar/calendar.py"
        issue: "build_events() and event only catch HomeAssistantError; OverflowError/ValueError from dt_util.as_local escapes"
    missing:
      - "parse_xmltv_time: reject offsets with minutes >= 60 or magnitude above ~18 h, convert ValueError/OverflowError to None, and reject years outside a sane window (e.g. 1900..2200)"
      - "parser._collect: guard per-programme conversion (try/except ValueError, OverflowError -> skipped_malformed) and narrow _STREAM_ERRORS to stream/decode errors (WR-06)"
      - "calendar.build_events and XmltvCalendarEntity.event: catch (HomeAssistantError, OverflowError, ValueError)"
      - "Regression tests: '+2500', '+0099', year 0001, year 9999 with and without stop; each asserts the good programme of the same feed still parses and skipped_malformed increments; plus a build_events test with a year-9999 programme"
human_verification:
  - test: "ha-dev walkthrough steps 1-4 on http://localhost:18123 (not :8123): add file source /media/xmltv/small-gzip.xml (gzip under .xml), add a calendar with include pattern (e.g. Tatort), try include '(' and file path /config/secrets.yaml, re-add the same file"
    expected: "Name pre-filled 'small-gzip.xml', source loads; menu/file-step texts and errors read correctly (01-07 D7); multiline channel regex/include/exclude fields render with examples (01-08 D6); Calendar panel shows only matches as '<channel>: <title>' with channel as location; inline invalid_regex with pattern and error; 'path not allowed'; 'already configured'"
    why_human: "No frontend in the test harness; form rendering, translations and the real allowlist need the live UI. Regenerate the small feeds with --start-date $(date +%F) if UAT runs after 2026-10-14 12:01"
  - test: "ha-dev walkthrough step 5: add /media/xmltv/large.xml (60 MB, 120 channels) and one reachable XMLTV URL source; open Add calendar"
    expected: "UI stays responsive while loading; channel picker searches/selects quickly; channel regex works as fallback; URL source loads"
    why_human: "Picker usability and UI responsiveness are UX judgments in the real frontend (RESEARCH A4, 01-09 D5/D6)"
  - test: "ha-dev walkthrough step 6: automation with Calendar trigger (event start, offset -0:05:00) on a calendar whose next match starts within ~20 minutes (large feed)"
    expected: "Automation trace shows it fired five minutes before the programme start"
    why_human: "Real wall-clock firing in a running HA; pytest covers it only with freezer (01-09 D7, AUT-01)"
  - test: "ha-dev walkthrough step 7: podman logs ha-dev after all steps"
    expected: "No 'Detected blocking call' and no xmltv_calendar error/traceback (verifier confirmed 0 such lines before the walkthrough, with no source configured)"
    why_human: "The load path in the running HA is only exercised by the walkthrough"
  - test: "ha-dev walkthrough step 8: delete-and-re-add a calendar (no Reconfigure until Phase 2 FLT-11); acknowledge the note that an invalid stored pattern only surfaces in the HA log"
    expected: "No Reconfigure action; entity and device disappear on delete; re-add under the same name keeps the entity_id and shows the new matches; user records whether the workflow is acceptable until Phase 2"
    why_human: "Acceptability of the interim workflow is a user decision (01-09 D8)"
  - test: "HACS on ha-host: Custom repositories -> add https://github.com/akentner/homeassistant-xmltv-integration as type Integration"
    expected: "HACS accepts it without validation error and lists 'XMLTV Calendar' with its brand icon; after the next user push, CI and Validate also run green for a push event"
    why_human: "HACS custom-repository add flow and icon rendering need a live HACS (DST-01, 01-10 D5); the hacs/action job only validates structure"
  - test: "Backstop truth (01-07): two sources with equal refresh intervals refresh independently"
    expected: "Refreshing one source never triggers a download or parse of another"
    why_human: "verification: backstop; no test exercises it. Structurally each config entry owns its own XmltvCoordinator (coordinator.py, __init__.py), which is presence evidence only (insufficient_spec)"
  - test: "Judgment-tier prohibitions (non-authoritative LLM verdict: all hold) — confirm: (a) no network endpoint other than the configured source URL is contacted (01-01); (b) no programme- or use-case-specific matching logic (01-03); (c) no third-party EPG data committed (01-09)"
    expected: "(a) only source.py session.get(url) for the user URL; (b) 'formel'/'Tatort' appear only as help-text examples in translations/en.json; (c) tracked fixtures basic.xml, edge_cases.xml, latin1.xml are synthetic (generator-info-name 'xmltv-calendar tests'); real_de_excerpt.xml not committed"
    why_human: "unverified-prohibition — human review recommended; judgment-tier prohibitions need explicit human resolution"
---

# Phase 1: First Filtered Calendar Verification Report

**Phase Goal:** User can add an XMLTV source (URL or local file) in the HA UI, attach calendars filtered by channel and include/exclude regex, and see exactly the matching programmes as correctly timed calendar events that drive calendar triggers.
**Verified:** 2026-10-14T12:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification
**Mode:** mvp (ROADMAP). The phase goal is written as a capability statement, not a strict "As a ..., I want to ..., so that ..." user story; verification follows the goal-backward method on the goal text plus the five roadmap Success Criteria.

## User Flow Coverage

| Step | Expected | Evidence in codebase | Status |
|------|----------|----------------------|--------|
| Add URL source | Menu url -> URL + refresh -> Name (host) -> entry | `config_flow.py` async_step_user/url/name; `tests/test_tracer.py::test_url_source_to_calendar_events` | ✓ |
| Add local file source | Menu file -> allowed path -> Name (file name) | `config_flow.py` async_step_file, `source.check_file`; `tests/test_config_flow.py::test_file_source_end_to_end`, `::test_file_step_errors` | ✓ (UI render: human) |
| Gzip regardless of name | magic-byte sniff | `xmltv/parser.py` `GzipFile(` on `GZIP_MAGIC`; `test_ingestion.py::test_gzip_behind_xml_url_end_to_end` | ✓ |
| Duplicate source rejected | already_configured | `async_set_unique_id(source_unique_id(...))`; `test_identity.py::test_url_variant_identity_invariant`, `::test_file_variant_identity_invariant` | ✓ |
| Attach filtered calendars | subentry flow, channels + channel regex + include/exclude | `CalendarSubentryFlow`; `test_subentry_flow.py`, `test_init.py::test_two_calendars_one_download` | ✓ |
| See exactly the matching programmes | channel AND include AND NOT exclude, one event each | `xmltv/filter.py` FilterSpec.apply; `tests/xmltv/test_filter.py::test_truth_table` | ✓ |
| Correctly timed events | tz-aware, all variants, stop inference, stable UID, **malformed programme never breaks the calendar** | `timeparse.py`, `normalize.py`, `render.py`; robustness clause **fails** (CR-01, reproduced) | ✗ |
| Events drive calendar triggers | start/end + offset fire; state on while airing | `test_calendar.py::test_start_offset_and_end_triggers_fire`, `::test_state_turns_on_and_off_without_refresh` | ✓ (live firing: human) |

## Goal Achievement

### Observable Truths — Roadmap Success Criteria (contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | UI-only source setup (URL or allowed file, gzip regardless of extension, refresh interval), one or more calendar subentries, duplicate source rejected | ✓ VERIFIED | Flow + setup tests above; `test_minimum_refresh_is_one_hour`, `test_refresh_out_of_bounds_is_rejected`; menu order `["url","file"]` asserted at `tests/test_config_flow.py:68`. UI rendering routed to human check 1 |
| SC2 | Channel picker (empty = all) + include/exclude regex; one event per programme; exact duplicates collapsed; location = display name; title `{channel}: {title}`; invalid regex rejected with error; empty patterns ignored | ✓ VERIFIED | `filter.py`, `render.to_event_fields`, `normalize_programmes`; `test_truth_table`, `test_exact_duplicates_collapse_first_wins`, `test_summary_and_location_unchanged`, `test_invalid_pattern_line_keeps_form_open`, `test_blank_lines_only_are_ignored`. WR-03 (wrong placeholder when two fields are invalid) is a warning |
| SC3 | Start/end tz-aware and correct for every timestamp variant; missing stops inferred; UIDs stable; **a single malformed programme never breaks the calendar** | ✗ FAILED | Variants/inference/UIDs verified (`test_valid_timestamps` 17 cases, `test_missing_stops_inferred_from_next_start`, `test_uid_format_and_stability`, `test_shuffled_input_gives_identical_output`). Robustness clause fails — see Gaps (CR-01 reproduced) |
| SC4 | Calendar trigger (start/end, offset) fires; get_events returns all overlapping events; state on while airing with current/next attributes | ✓ VERIFIED | `test_start_offset_and_end_triggers_fire` (start -5 min fires at 09:55; end on 15-min boundary fires), `test_overlapping_includes_programme_ending_at_range_start`, `test_overlapping_long_programme_lookback`, `test_state_turns_on_and_off_without_refresh`. Live firing in ha-dev routed to human check 3 |
| SC5 | 50+ MB feed without blocking the loop, bounded memory; hassfest, HACS validation, Ruff, pytest green on every push; HACS accepts the repo as a custom repository | ? UNCERTAIN (HACS part) | Benchmark asserts 60 MB, <30 s, tracemalloc peak <150 MB, loop gap <250 ms (`tests/xmltv/test_benchmark.py`); GitHub run 38553243429 jobs Ruff/Unit tests/Benchmark = success and 38553246496 hassfest/HACS = success for `ffd5363` (code unchanged since: `git diff ffd5363 HEAD` touches only `.planning/`); push trigger without branch filter in both workflows. HACS custom-repo acceptance needs human check 6 |

### Observable Truths — PLAN frontmatter must-haves (by plan)

| Plan | Truths | Verified | Failed | Human / uncertain | Notes |
|------|--------|----------|--------|-------------------|-------|
| 01-01 tracer | 7 | 7 | 0 | 0 | Executor parse in `coordinator.py`; purity AST test; device per subentry `test_init.py:175-179` |
| 01-02 timing | 8 | 6 | 2 | 0 | ✗ #1 "impossible ... return None" (`+2500` raises ValueError); ✗ #4 "programme without parsable start is skipped and counted, never raising" |
| 01-03 filter | 9 | 9 | 0 | 0 | `test_truth_table`, `test_channel_regex_selects_by_id`, `test_missing_channel_warning_once_per_refresh` |
| 01-04 window | 8 | 6 | 2 | 0 | ✗ #1 "get_events ... never raises" and ✗ #7 "one match that cannot become a CalendarEvent is skipped" — `build_events` lets OverflowError escape (reproduced) |
| 01-05 ingestion | 8 | 7 | 1 | 0 | ✗ #7 "one malformed programme never fails the parse" (reproduced) |
| 01-06 HACS/CI/bench | 10 | 10 | 0 | 0 | Backstop "CI jobs independent": `test_ci_jobs_are_independent` passes, `ci.yml` has no `needs:`, and the live run concluded all three jobs |
| 01-07 file/identity | 12 | 11 | 0 | 1 | Backstop "sources refresh independently": no test → insufficient_spec (human check 7). Backstop "menu url first, file second": asserted at `test_config_flow.py:68` |
| 01-08 subentry form | 11 | 11 | 0 | 0 | Backstop order-independence: `test_add_and_remove_order_does_not_change_events` |
| 01-09 ha-dev | 5 (+1 N/A) | 2 | 0 | 3 | ha-dev Up on 0.0.0.0:18123; `podman logs ha-dev` grep → 0 xmltv errors / blocking calls. UI walkthrough, picker, live trigger → human. Truth #6 (excerpt) N/A: user chose "none" (STATE.md deferred item) |
| 01-10 publish | 5 | 4 | 0 | 1 | Repo public, 7 topics, issues on (gh); runs green; secret scan clean. HACS acceptance → human |

**Score:** 76/88 truths verified (5 roadmap SCs + 83 applicable plan truths); 6 FAILED (one root cause, CR-01); 6 human/uncertain; 0 present-but-behavior-unverified.

### Prohibitions

| Plan | Statement | Tier | Disposition |
|------|-----------|------|-------------|
| 01-01 | MUST NOT log/expose URL path or query; host only | test | ✓ VERIFIED — enforced by `test_source.py::test_logs_name_host_only`, `::test_failure_logs_name_host_only` (pass) |
| 01-01 | MUST NOT contact any endpoint but the configured URL | judgment | ⚠ flagged — LLM verdict holds (only `source.py` `session.get(url)`); human review recommended |
| 01-03 | MUST NOT contain use-case-specific matching logic | judgment | ⚠ flagged — LLM verdict holds (F1/Tatort only in help text examples); human review recommended |
| 01-09 | MUST NOT commit third-party EPG data without permission | judgment | ⚠ flagged — LLM verdict holds (fixtures synthetic; excerpt not committed); human review recommended |

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| 01-01..01-06, 01-08 artifacts (30) | ✓ VERIFIED | `verify.artifacts` all passed; substantive and imported/used |
| `source.py` contains `def normalize_source` (01-07) | ⚠ naming deviation | Function is `normalize_url` (URL) plus `check_file().resolve()` (file); behaviour and tests present (`test_normalize_url_canonical_form`, `test_file_variant_identity_invariant`). Not counted as a gap; override suggested below |
| `scripts/trim_feed.py`, `tests/fixtures/real_de_excerpt.xml` (01-09) | ⚠ intentionally absent | User decision "none" (D-15 deferred, STATE.md line 104/130); `test_real_feed.py` skips by design. Override suggested below |

**Suggested overrides (intentional deviations):**

```yaml
overrides:
  - must_have: "custom_components/xmltv_calendar/source.py provides read_and_parse_file, normalize_source, source_unique_id, async_probe_url, probe_file"
    reason: "Implemented as normalize_url (URL) plus check_file().resolve() (file path); identity invariants are tested"
    accepted_by: "{name}"
    accepted_at: "{ISO timestamp}"
  - must_have: "scripts/trim_feed.py and tests/fixtures/real_de_excerpt.xml (D-15 real feed excerpt)"
    reason: "User chose 'none' in 01-09 Task 2 (licensing risk in a public repo); deferred in STATE.md"
    accepted_by: "{name}"
    accepted_at: "{ISO timestamp}"
```

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| coordinator.py | xmltv/parser.py | `async_add_executor_job(partial(parse, ...))` | ✓ WIRED |
| calendar.py | xmltv/filter.py | `FilterSpec.from_mapping(...).apply` in executor | ✓ WIRED |
| __init__.py | calendar.py | `runtime.add_entities(..., config_subentry_id=...)` | ✓ WIRED |
| config_flow.py | data.py | `entry.runtime_data.coordinator.data.channels` | ✓ WIRED |
| parser.py | normalize.py | `normalize_programmes(...)` | ✓ WIRED |
| render.py | calendar.py | `render.to_event_fields` → `CalendarEvent(uid=...)` | ✓ WIRED |
| calendar.py | window.py | `MatchIndex(result.matches)` | ✓ WIRED |
| coordinator.py | source.py | `SourceTooLargeError`/`SourceError` → `UpdateFailed(translation_key)`; `read_and_parse_file` in executor | ✓ WIRED |
| parser.py | gzip | `GzipFile(fileobj=...)` on magic bytes | ✓ WIRED |
| config_flow.py | source.py / filter.py | `async_set_unique_id(source_unique_id(...))`; `first_invalid_pattern` | ✓ WIRED |
| ci.yml | pyproject.toml / generator | `-m benchmark`; benchmark fixture loads `generate_benchmark_feed` | ✓ WIRED |
| ~/Projects/dev/compose.yml (outside repo) | custom_components/xmltv_calendar | read-only bind mount `xmltv_calendar:ro` | ✓ WIRED (grep line 13; `/media/xmltv:ro` line 15) |
| GitHub repo | ci.yml / validate.yml | push trigger (tags-ignore only) | ✓ WIRED (runs observed via workflow_dispatch and pull_request) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| XmltvCalendarEntity | `_index` / `_epg` | coordinator.data (EpgData from `parse` of downloaded/file bytes) → `FilterSpec.apply` | Yes | ✓ FLOWING |
| CalendarSubentryFlow channel picker | `channel_ids` | `entry.runtime_data.coordinator.data.channels` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full unit suite (one run) | `uv run pytest -q -m "not benchmark"` | 209 passed, 1 skipped (real feed excerpt), 4 deselected | ✓ PASS |
| Lint/format | `uv run ruff check . && uv run ruff format --check .` | clean | ✓ PASS |
| CI incl. 60 MB benchmark on GitHub | `gh run view 38553243429 --json jobs` | Ruff, Unit tests, Benchmark = success | ✓ PASS |
| hassfest + HACS action | `gh run view 38553246496 --json jobs` | hassfest, HACS = success | ✓ PASS |
| Malformed offset `+2500` | scratchpad `cr01.py` via `PYTHONPATH=. uv run python` | `FeedError: unreadable feed: ValueError after 300 bytes` — good programme lost | ✗ FAIL |
| Year 0001 / 9999 programme | same script | `OverflowError: date value out of range` uncaught from `parse()` | ✗ FAIL |
| Year-9999 programme in `build_events` (Europe/Berlin) | scratchpad `cr01b.py` | `OverflowError` escapes `build_events` | ✗ FAIL |
| Offset `+0099` | same script | accepted silently (offset minutes >= 60 not rejected) | ⚠ wrong but non-crashing |
| ha-dev runtime | `podman ps`, `podman logs ha-dev \| grep ...` | Up, 18123->8123; 0 matching error lines | ✓ PASS |

### Probe Execution

Step 7c: SKIPPED — no `scripts/*/tests/probe-*.sh` exist and no plan declares a probe.

### Requirements Coverage

All 20 phase requirement IDs are claimed by at least one plan; REQUIREMENTS.md maps no additional ID to Phase 1 (no orphans).

| Requirement | Source Plan(s) | Status | Evidence |
|-------------|----------------|--------|----------|
| SRC-01 | 01-01, 01-07, 01-09 | ✓ SATISFIED | URL flow + tracer test |
| SRC-02 | 01-07, 01-09 | ✓ SATISFIED | file flow, allowlist check in flow and on every refresh (`test_file_outside_allowlist_is_refused_at_setup`) |
| SRC-03 | 01-05, 01-07 | ✓ SATISFIED | magic-byte sniff; gzip under `.xml` for URL and file |
| SRC-04 | 01-01, 01-07 | ✓ SATISFIED | refresh_hours 1..168, default 24 |
| SRC-09 | 01-05, 01-06, 01-09 | ✓ SATISFIED | executor parse, byte caps, benchmark green on CI (WR-02 memory warning) |
| SRC-13 | 01-07 | ✓ SATISFIED | normalized identity, already_configured before probe |
| FLT-01 | 01-01, 01-08 | ✓ SATISFIED | multiple subentries, one download |
| FLT-02 | 01-01, 01-03, 01-08 | ✓ SATISFIED (picker UX: human) | sorted channel IDs, empty = all |
| FLT-03 | 01-03, 01-08 | ✓ SATISFIED | OR-combined include |
| FLT-04 | 01-03, 01-08 | ✓ SATISFIED | channel AND include AND NOT exclude |
| FLT-07 | 01-03, 01-08 | ✓ SATISFIED (WR-03 warning) | invalid regex keeps form open with error; blank lines ignored |
| EVT-01 | 01-02 | ✓ SATISFIED | exact-duplicate collapse, back-to-back kept |
| EVT-02 | 01-01, 01-05 | ✓ SATISFIED | location = display name, fallback channel id |
| EVT-05 | 01-02 | ⚠ PARTIAL — linked to SC3 gap | all real-world variants correct and inferred; a syntactically valid far-future/past timestamp or an out-of-range offset crashes instead of being skipped |
| EVT-06 | 01-02 | ✓ SATISFIED | stable UID format and order-independence |
| AUT-01 | 01-01, 01-04, 01-09 | ✓ SATISFIED (live: human) | trigger test; `get_events` overlap tests |
| AUT-02 | 01-01, 01-04 | ✓ SATISFIED | state on/off live without refresh |
| CFG-01 | 01-01, 01-07, 01-08, 01-09 | ✓ SATISFIED (UI render: human) | config + subentry flows only, no YAML |
| DST-01 | 01-06, 01-10 | ? NEEDS HUMAN | hacs.json/manifest/brand icons valid (`test_repo_structure.py`, HACS action green); custom-repo acceptance pending UAT |
| DST-02 | 01-06, 01-10 | ✓ SATISFIED | both workflows on push (no branch filter), all jobs green |

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK` markers in phase files. No stubs. Findings from 01-REVIEW.md, independently checked against code:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| xmltv/timeparse.py, normalize.py, parser.py, calendar.py | see gap | CR-01: per-programme errors escape (reproduced) | 🛑 Blocker | Defeats SC3 robustness clause |
| xmltv/filter.py | 16-18 | WR-01: length/line caps do not bound regex backtracking; feed titles unbounded | ⚠️ Warning | Executor thread can hang; Phase 2 note plans ReDoS-aware validation |
| source.py / parser.py | 180-202 / 90-114 | WR-02: download join doubles peak; past programmes retained until after normalize | ⚠️ Warning | Memory on small targets; benchmark budget still met |
| config_flow.py | 205-209 | WR-03: `setdefault` shows the first bad pattern for every invalid field | ⚠️ Warning | Misleading error text when two fields are invalid (confirmed by reading code) |
| source.py / config_flow.py | 133-142 / 148 | WR-04: resolved symlink target persisted as CONF_PATH | ⚠️ Warning | Symlink-rotated file feeds go stale |
| README.md | 3-4, 38 | WR-05: says "title and description"; code matches title and sub-title | ⚠️ Warning | User-facing docs wrong (README overhaul is DST-04, Phase 4) |
| xmltv/parser.py | 19 | WR-06: `_STREAM_ERRORS` includes ValueError/LookupError | ⚠️ Warning | Root-cause contributor to CR-01 path 1 |
| various | — | IN-01..IN-10 | ℹ️ Info | See 01-REVIEW.md |

### Human Verification Required

Items 1-5 are the 01-09 ha-dev walkthrough on http://localhost:18123 (not :8123, which is an unrelated instance). The small feeds cover 2026-10-14 00:00–12:01 only; regenerate with `--start-date $(date +%F)` if UAT runs later.

### 1. ha-dev walkthrough: file source, calendar, validation errors (01-07 D7, 01-08 D6)
**Test:** Add `/media/xmltv/small-gzip.xml`, add a calendar with an include pattern, try include `(`, try `/config/secrets.yaml`, re-add the same file.
**Expected:** Pre-filled name, loads; texts correct; multiline fields with examples; only matches shown as `<channel>: <title>`; inline invalid_regex; path not allowed; already configured.
**Why human:** No frontend in the harness.

### 2. Large feed, picker and URL source
**Test:** Add `/media/xmltv/large.xml` and a reachable URL source; open Add calendar.
**Expected:** UI responsive; picker (120 channels) searches/selects quickly; channel regex fallback works; URL source loads.
**Why human:** UX judgment.

### 3. Live calendar trigger
**Test:** Calendar-trigger automation (start, offset -0:05:00) on a match ~20 min ahead.
**Expected:** Trace shows firing 5 minutes before start.
**Why human:** Wall-clock behaviour in running HA.

### 4. No blocking-call warnings during the walkthrough
**Test:** `podman logs ha-dev` after steps 1-3.
**Expected:** No "Detected blocking call" / xmltv_calendar errors.
**Why human:** Load path only exercised by the walkthrough.

### 5. Delete-and-re-add workflow
**Test:** Delete the step-1 calendar, re-add under the same name with another include.
**Expected:** No Reconfigure action; entity/device removed; same entity_id with new matches. Record acceptability until Phase 2 and acknowledge the invalid-stored-pattern note.
**Why human:** User decision.

### 6. HACS custom repository on ha-host (DST-01)
**Test:** HACS → Custom repositories → add the GitHub URL as Integration.
**Expected:** Accepted, "XMLTV Calendar" listed with brand icon; after the next push, CI/Validate green for a push event.
**Why human:** Live HACS UI.

### 7. Backstop: independent refresh of sources (01-07)
**Test:** Two sources with equal interval; refresh one.
**Expected:** No download/parse of the other.
**Why human:** No test; structural evidence only (insufficient_spec).

### 8. Judgment-tier prohibitions
**Test:** Confirm the three LLM verdicts in the Prohibitions table.
**Expected:** All hold.
**Why human:** unverified-prohibition — human review recommended.

### Gaps Summary

One root cause blocks the phase goal: **CR-01 — per-programme timestamp errors are not contained.** Roadmap SC3 explicitly requires that "a single malformed programme never breaks the calendar", and three plan contracts (01-02, 01-04, 01-05) repeat it. The verifier reproduced every path against the real code:

- an out-of-range UTC offset (`+2500`) rejects the entire feed (all calendars of the source go to setup-retry or stale), taking the valid programmes with it;
- a year-0001 or year-9999 timestamp raises an uncaught `OverflowError` from `normalize_programmes`;
- a year-9999 programme that survives parsing crashes `build_events` (and the `event` property when it is the next match).

This is classified as a gap, not an advisory: the failing clause is a roadmap Success Criterion, the evidence is deterministic, and no later phase covers it (Phase 3 SC4 "keep last good data" would only mask refresh failures, not first setup, not the loss of the valid programmes of the same feed, and not the `build_events` crash). The fix is small and local (timeparse range checks, per-programme guard in `_collect`, wider exception tuple in `calendar.py`, plus regression tests); see `gaps[0].missing`.

Everything else in the goal is implemented, wired and tested: URL and file sources, gzip by content, refresh interval, duplicate protection, multi-calendar subentries with channel/channel-regex/include/exclude filters, exact-duplicate collapse, stable UIDs, location and default title, capped end-inclusive `get_events`, live on/off state, start/end/offset triggers, executor parsing with a green 60 MB benchmark, and green CI/Validate on GitHub. Remaining open items are the human UAT checks above (ha-dev walkthrough, HACS acceptance, one backstop truth, three judgment-tier prohibitions) and six review warnings that do not block the goal.

---

_Verified: 2026-10-14T12:30:00Z_
_Verifier: Claude (gsd-verifier)_
