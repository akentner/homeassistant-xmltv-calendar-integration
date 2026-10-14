---
phase: 01-first-filtered-calendar
verified: 2026-10-14T14:31:56Z
status: human_needed
score: 90/96 must-haves verified
covered_files: [".github/workflows/ci.yml", ".github/workflows/validate.yml", ".planning/phases/01-first-filtered-calendar/01-01-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-01-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-02-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-02-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-03-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-03-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-04-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-04-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-05-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-05-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-06-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-06-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-07-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-07-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-08-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-08-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-09-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-09-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-10-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-10-SUMMARY.md", ".planning/phases/01-first-filtered-calendar/01-11-PLAN.md", ".planning/phases/01-first-filtered-calendar/01-11-SUMMARY.md", ".ruff.toml", "LICENSE", "README.md", "custom_components/xmltv_calendar/__init__.py", "custom_components/xmltv_calendar/calendar.py", "custom_components/xmltv_calendar/config_flow.py", "custom_components/xmltv_calendar/const.py", "custom_components/xmltv_calendar/coordinator.py", "custom_components/xmltv_calendar/data.py", "custom_components/xmltv_calendar/manifest.json", "custom_components/xmltv_calendar/source.py", "custom_components/xmltv_calendar/translations/en.json", "custom_components/xmltv_calendar/xmltv/__init__.py", "custom_components/xmltv_calendar/xmltv/filter.py", "custom_components/xmltv_calendar/xmltv/model.py", "custom_components/xmltv_calendar/xmltv/normalize.py", "custom_components/xmltv_calendar/xmltv/parser.py", "custom_components/xmltv_calendar/xmltv/render.py", "custom_components/xmltv_calendar/xmltv/timeparse.py", "custom_components/xmltv_calendar/xmltv/window.py", "docs/assets/icon.svg", "hacs.json", "pyproject.toml", "renovate.json", "scripts/generate_benchmark_feed.py", "tests/__init__.py", "tests/conftest.py", "tests/fixtures/basic.xml", "tests/fixtures/edge_cases.xml", "tests/fixtures/latin1.xml", "tests/test_calendar.py", "tests/test_config_flow.py", "tests/test_filtering.py", "tests/test_identity.py", "tests/test_ingestion.py", "tests/test_init.py", "tests/test_repo_structure.py", "tests/test_source.py", "tests/test_subentry_flow.py", "tests/test_timing.py", "tests/test_tracer.py", "tests/xmltv/__init__.py", "tests/xmltv/conftest.py", "tests/xmltv/test_benchmark.py", "tests/xmltv/test_filter.py", "tests/xmltv/test_normalize.py", "tests/xmltv/test_parser.py", "tests/xmltv/test_purity.py", "tests/xmltv/test_real_feed.py", "tests/xmltv/test_render.py", "tests/xmltv/test_timeparse.py", "tests/xmltv/test_window.py"]
covered_digest: "v3:sha256:0d6c95f0287a3d1f431ccda7c9da79315256c8d61935583c910abb6c35448265"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 76/88
  gaps_closed:
    - "ROADMAP SC3: a single malformed programme never breaks the calendar (with plan truths 01-02 #1/#4, 01-04 #1/#7, 01-05 #7)"
  gaps_remaining: []
  regressions: []
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
  - test: "ha-dev walkthrough step 7: podman logs ha-dev after all steps (redeploy first so ha-dev runs the 01-11 code)"
    expected: "No 'Detected blocking call' and no xmltv_calendar error/traceback"
    why_human: "The load path in the running HA is only exercised by the walkthrough"
  - test: "ha-dev walkthrough step 8: delete-and-re-add a calendar (no Reconfigure until Phase 2 FLT-11); acknowledge the note that an invalid stored pattern only surfaces in the HA log"
    expected: "No Reconfigure action; entity and device disappear on delete; re-add under the same name keeps the entity_id and shows the new matches; user records whether the workflow is acceptable until Phase 2"
    why_human: "Acceptability of the interim workflow is a user decision (01-09 D8)"
  - test: "HACS on ha-host: Custom repositories -> add https://github.com/akentner/homeassistant-xmltv-integration as type Integration; then push the 01-11 commits"
    expected: "HACS accepts it without validation error and lists 'XMLTV Calendar' with its brand icon; after the push, CI (Ruff, Unit tests, Benchmark) and Validate (hassfest, HACS) run green for a push event on the 01-11 code"
    why_human: "HACS custom-repository add flow and icon rendering need a live HACS (DST-01). The 01-11 code is not pushed yet; the last remote runs are for ffd5363 (all green). Pushing is the user's job"
  - test: "Backstop truth (01-07): two sources with equal refresh intervals refresh independently"
    expected: "Refreshing one source never triggers a download or parse of another"
    why_human: "verification: backstop; no test exercises it. Structurally each config entry owns its own XmltvCoordinator (coordinator.py, __init__.py), which is presence evidence only (insufficient_spec)"
  - test: "Judgment-tier prohibitions (non-authoritative LLM verdict: all hold) — confirm: (a) no network endpoint other than the configured source URL is contacted (01-01); (b) no programme- or use-case-specific matching logic (01-03); (c) no third-party EPG data committed (01-09)"
    expected: "(a) only source.py session.get(url) for the user URL; (b) 'formel'/'Tatort' appear only as help-text examples in translations/en.json; (c) tracked fixtures basic.xml, edge_cases.xml, latin1.xml are synthetic; real_de_excerpt.xml not committed"
    why_human: "unverified-prohibition — human review recommended; judgment-tier prohibitions need explicit human resolution"
  - test: "Decision on review warnings that touch SC3/SC4 wording: WR-07 (a well-formed programme with an absurd but in-window stop, e.g. year 2200, becomes the calendar's current event until that stop), IN-14 (get_events raises OverflowError for a caller-supplied query start near year 0001) and WR-08 (skipped_malformed is never logged)"
    expected: "User accepts them as non-blocking for Phase 1 and routes them (WR-07 -> duration cap in parser or Phase 2 FLT-08 context; WR-08 -> Phase 3 SRC-12 diagnostics; IN-14 -> clamp in window.py), or asks for a small gap-closure plan before closing Phase 1"
    why_human: "Verifier judges them non-blocking (well-formed data rendered faithfully / absurd caller input / observability), but WR-07 is close to SC3's 'never breaks the calendar' wording, so the call belongs to the user"
---

# Phase 1: First Filtered Calendar Verification Report

**Phase Goal:** User can add an XMLTV source (URL or local file) in the HA UI, attach calendars filtered by channel and include/exclude regex, and see exactly the matching programmes as correctly timed calendar events that drive calendar triggers.
**Verified:** 2026-10-14T14:31:56Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (plan 01-11, commits 0237355..05fe9fe; docs up to a91d562)
**Mode:** mvp (ROADMAP). The goal is a capability statement; 01-11-PLAN restates it as a user story ("As a Home Assistant user, I want to add an XMLTV source ... so that I see exactly the matching programmes as correctly timed calendar events that drive my calendar-trigger automations."). Verification follows the goal text plus the five roadmap Success Criteria.

## User Flow Coverage

| Step | Expected | Evidence in codebase | Status |
|------|----------|----------------------|--------|
| Add URL source | Menu url -> URL + refresh -> Name (host) -> entry | `config_flow.py` async_step_user/url/name; `tests/test_tracer.py::test_url_source_to_calendar_events` | ✓ |
| Add local file source | Menu file -> allowed path -> Name (file name) | `config_flow.py` async_step_file, `source.check_file`; `tests/test_config_flow.py::test_file_source_end_to_end` | ✓ (UI render: human) |
| Gzip regardless of name | magic-byte sniff | `xmltv/parser.py:165` `GzipFile(` on `GZIP_MAGIC`; `test_ingestion.py::test_gzip_behind_xml_url_end_to_end` | ✓ |
| Duplicate source rejected | already_configured | `async_set_unique_id(source_unique_id(...))`; `test_identity.py` | ✓ |
| Attach filtered calendars | subentry flow, channels + channel regex + include/exclude | `CalendarSubentryFlow`; `test_subentry_flow.py`, `test_init.py::test_two_calendars_one_download` | ✓ |
| See exactly the matching programmes | channel AND include AND NOT exclude | `xmltv/filter.py` FilterSpec.apply; `tests/xmltv/test_filter.py::test_truth_table` | ✓ |
| Correctly timed events, malformed programme never breaks the calendar | tz-aware, all variants, stop inference, stable UID, containment | `timeparse.py:40-56` range checks, `parser.py:96-142` per-programme guard + read-only error translation, `calendar.py:56,142` widened guards; `test_timing.py::test_malformed_timestamps_never_break_the_calendar` (LOADED + exact events) | ✓ (was ✗) |
| Events drive calendar triggers | start/end + offset fire; state on while airing | `test_calendar.py::test_start_offset_and_end_triggers_fire`, `::test_state_turns_on_and_off_without_refresh` | ✓ (live firing: human) |

## Goal Achievement

### Re-verification of the previous gap (CR-01)

Code read (not SUMMARY):

- `xmltv/timeparse.py:40-56` — written year checked against `_MIN_YEAR=1900.._MAX_YEAR=2200` for every variant (numeric, alpha, none); numeric offsets rejected when `off_m >= 60` or magnitude `> 18*60` *before* `_tz()` builds the timezone; `datetime(...)` guarded by `except ValueError, OverflowError` (PEP 758 form, valid on py314).
- `xmltv/parser.py:96-112` — `_read_events` wraps only `next(iterparse)`; `ET.ParseError` and `_STREAM_ERRORS` become content-free `FeedError ... from None`. `parser.py:126-131` — `_programme(elem)` guarded by `except ValueError, OverflowError` → `skipped_malformed += 1`. `parse()` keeps only the `StopIteration` handler.
- `calendar.py:56` (`build_events`) and `calendar.py:142` (`event`) — `except HomeAssistantError, OverflowError, ValueError`.

Independent reproduction by the verifier (scratchpad `cr01_rv.py`, project venv, not committed). Feed = one good programme + one extra:

| Extra programme | Result |
|-----------------|--------|
| start `+2500`, `-2500`, `+0099`, `+1801` | parses; titles `['Good']`, `skipped_malformed=1` |
| start year 0001 (`+0100`, `CEST`, no offset) | parses; `['Good']`, `skipped_malformed=1` |
| start year 9999 (`-0100` with stop, `+0000` without stop, `Z`) | parses; `['Good']`, `skipped_malformed=1` |
| start `20260230...` (impossible date) | parses; `['Good']`, `skipped_malformed=1` |
| valid start, stop `+2500` / stop year 9999 | kept, stop inferred = start + 60 min, `inferred_stops=1` |
| window edges `22001231235959 -1800`, `19000101000000 +1800` | kept, no overflow in normalize |
| `parse_xmltv_time` over 7 years x 5 dates x 4 times x 11 zones (1,540 inputs incl. year 0000, month 13, hour 24, `-9999`, `+99:99`) | 0 exceptions |

All three previously reproduced failure paths (FeedError for `+2500`, OverflowError from normalize for year 0001/9999, OverflowError from `build_events` under Europe/Berlin) are closed and each is pinned by a passing test.

### Observable Truths — Roadmap Success Criteria (contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | UI-only source setup (URL or allowed file, gzip regardless of extension, refresh interval), one or more calendar subentries, duplicate source rejected | ✓ VERIFIED (regression check) | `config_flow.py`, `source.py`, `__init__.py` unchanged since previous verification (`git diff f18479c HEAD` touches only timeparse/parser/calendar + 4 test files); flow/identity tests pass in the full run. UI rendering → human check 1 |
| SC2 | Channel picker (empty = all) + include/exclude regex; one event per programme; exact duplicates collapsed; location = display name; title `{channel}: {title}`; invalid regex rejected; empty patterns ignored | ✓ VERIFIED (regression check) | `filter.py`, `render.py`, `normalize.py`, `config_flow.py` unchanged; `test_truth_table`, `test_exact_duplicates_collapse_first_wins`, `test_invalid_pattern_line_keeps_form_open` pass. WR-03 remains a warning |
| SC3 | Start/end tz-aware and correct for every timestamp variant; missing stops inferred; UIDs stable; **a single malformed programme never breaks the calendar** | ✓ VERIFIED (was ✗ FAILED) | Code + reproduction above; `test_malformed_timestamps_never_break_the_calendar` (entry LOADED, `get_events` returns exactly "X: Good" and "X: Broken stop"), `test_malformed_timestamp_skips_only_that_programme` (6 cases), `test_unparsable_stop_offset_infers_stop`, `test_conversion_error_skips_only_that_programme` (2), `test_build_events_skips_out_of_range_programme`, `test_event_property_skips_out_of_range_match`; variant/UID tests still green. See WR-07 note in Anti-Patterns |
| SC4 | Calendar trigger (start/end, offset) fires; get_events returns all overlapping events; state on while airing with current/next attributes | ✓ VERIFIED | `test_start_offset_and_end_triggers_fire`, `test_overlapping_*`, `test_state_turns_on_and_off_without_refresh` pass; `event` no longer raises for an unbuildable match. Live firing → human check 3 |
| SC5 | 50+ MB feed without blocking the loop, bounded memory; hassfest/HACS/Ruff/pytest green on every push; HACS accepts the repo | ? UNCERTAIN (HACS + push for new code) | Local benchmark re-run on the changed parser hot loop: 60 MB parse 2.78 s, max_loop_gap 210.7 ms (plain) / 174.3 ms (gz), tracemalloc peak 102 MB, all 4 benchmark tests pass (limits 30 s / 250 ms / 150 MB). Ruff check/format clean. Remote CI last ran on `ffd5363` (all green); the 01-11 commits are not pushed yet → human check 6 |

### Observable Truths — PLAN frontmatter must-haves (by plan)

| Plan | Truths | Verified | Failed | Human / uncertain | Notes |
|------|--------|----------|--------|-------------------|-------|
| 01-01 tracer | 7 | 7 | 0 | 0 | Regression: unchanged files; tracer test passes |
| 01-02 timing | 8 | 8 | 0 | 0 | #1 now holds (`+2500`, `+0099`, out-of-window years return None; 1,540-input sweep raises nothing); #4 holds (skipped and counted, never raising) |
| 01-03 filter | 9 | 9 | 0 | 0 | Regression only |
| 01-04 window | 8 | 8 | 0 | 0 | #1 "get_events ... never raises" and #7 "one match that cannot become a CalendarEvent is skipped" now hold for data-driven failures (`calendar.py:56,142`, tests above). IN-14 (absurd caller-supplied query start near year 0001) noted as warning, not counted as a failure — see Anti-Patterns |
| 01-05 ingestion | 8 | 8 | 0 | 0 | #7 holds; #3/#4 (truncated gzip/XML, empty input → content-free FeedError) still green after the `_read_events` restructure (`test_error_message_has_no_feed_content`, Shift_JIS guard) |
| 01-06 HACS/CI/bench | 10 | 10 | 0 | 0 | Benchmark re-run locally on new parser (see SC5) |
| 01-07 file/identity | 12 | 11 | 0 | 1 | Backstop "sources refresh independently" → human check 7 |
| 01-08 subentry form | 11 | 11 | 0 | 0 | Regression only |
| 01-09 ha-dev | 5 (+1 N/A) | 2 | 0 | 3 | UI walkthrough, picker, live trigger → human. Excerpt truth N/A (user chose "none") |
| 01-10 publish | 5 | 4 | 0 | 1 | HACS acceptance → human |
| 01-11 gap closure | 8 | 8 | 0 | 0 | All 8 verified by code read, reproduction and the named tests (15 collected, all pass) |

**Score:** 90/96 truths verified (5 roadmap SCs + 91 applicable plan truths); 0 FAILED; 6 human/uncertain (SC5 HACS/push, 01-07 backstop, 3x 01-09 UAT, 01-10 HACS); 0 present-but-behavior-unverified. Behavior-dependent truths (containment, skip/count, inferred stop, entity state) are each exercised by a passing test.

### Prohibitions

| Plan | Statement | Tier | Disposition |
|------|-----------|------|-------------|
| 01-01 | MUST NOT log/expose URL path or query; host only | test | ✓ VERIFIED — `test_source.py::test_logs_name_host_only`, `::test_failure_logs_name_host_only` pass |
| 01-01 | MUST NOT contact any endpoint but the configured URL | judgment | ⚠ flagged — LLM verdict holds; human check 8 |
| 01-03 | MUST NOT contain use-case-specific matching logic | judgment | ⚠ flagged — LLM verdict holds; human check 8 |
| 01-09 | MUST NOT commit third-party EPG data without permission | judgment | ⚠ flagged — LLM verdict holds; human check 8 |

### Advisory (New Scope, Unevidenced)

None. The new review findings (WR-07, WR-08, IN-11..IN-14) were checked with deterministic evidence; they are classified as warnings/info below on impact, not as unevidenced advisories.

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| 01-01..01-06, 01-08 artifacts | ✓ VERIFIED | `verify.artifacts` all passed (regression run) |
| 01-11 `timeparse.py` (`_MAX_OFFSET_MINUTES`), `parser.py` (`def _read_events`), tests `test_malformed_timestamps_never_break_the_calendar`, `test_malformed_timestamp_skips_only_that_programme`, `test_build_events_skips_out_of_range_programme` | ✓ VERIFIED | `verify.artifacts` 5/6 pass |
| 01-11 `calendar.py` contains `except (HomeAssistantError, OverflowError, ValueError):` | ✓ VERIFIED (syntax deviation) | Pattern check fails only on parentheses: code has the PEP 758 form `except HomeAssistantError, OverflowError, ValueError:` (2 hits, lines 56 and 142), enforced by `ruff format` with target py314. Semantics identical; behavior pinned by 3 passing calendar tests. Documented deviation in 01-11-SUMMARY |
| `source.py` contains `def normalize_source` (01-07) | ⚠ naming deviation (carried) | `normalize_url` + `check_file().resolve()`; identity tests pass. Override suggested below |
| `scripts/trim_feed.py`, `tests/fixtures/real_de_excerpt.xml` (01-09) | ⚠ intentionally absent (carried) | User decision "none" (D-15 deferred). Override suggested below |

**Suggested overrides (intentional deviations, unchanged from previous report):**

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
| coordinator.py | xmltv/parser.py | `async_add_executor_job(partial(parse, ...))`; `FeedError` → `UpdateFailed(invalid_feed)` | ✓ WIRED |
| parser.py `_programme` | timeparse.py | `parse_xmltv_time` for start (None → skip+count) and stop (None → `stop == start` → D-12 inference) | ✓ WIRED |
| parser.py | normalize.py | `normalize_programmes(...)` receives only 1900..2200 instants | ✓ WIRED |
| calendar.py | homeassistant.util.dt.as_local | `_to_event` inside widened try in `build_events` and `event` | ✓ WIRED (tool pattern miss on parentheses only; manual grep 2 hits) |
| calendar.py | xmltv/filter.py, window.py | `FilterSpec.apply` in executor; `MatchIndex(result.matches)` | ✓ WIRED |
| __init__.py | calendar.py | `runtime.add_entities(..., config_subentry_id=...)` | ✓ WIRED |
| config_flow.py | data.py / source.py / filter.py | channel list from runtime_data; `source_unique_id`; `first_invalid_pattern` | ✓ WIRED |
| ci.yml | pyproject.toml / generator | `-m benchmark`; benchmark fixture uses `generate_benchmark_feed` | ✓ WIRED |
| ~/Projects/dev/compose.yml (outside repo) | custom_components/xmltv_calendar | read-only bind mount | ✓ WIRED (carried; tool cannot resolve out-of-repo paths) |
| GitHub repo | ci.yml / validate.yml | push trigger (tags-ignore only) | ✓ WIRED (carried) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| XmltvCalendarEntity | `_index` / `_epg` | coordinator.data (EpgData from `parse`) → `FilterSpec.apply` | Yes | ✓ FLOWING |
| CalendarSubentryFlow channel picker | `channel_ids` | `entry.runtime_data.coordinator.data.channels` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full unit suite (one run) | `uv run pytest -q -m "not benchmark"` | 238 passed, 1 skipped (real-feed excerpt, by design), 4 deselected | ✓ PASS |
| Lint/format | `uv run ruff check .` / `uv run ruff format --check .` | All checks passed / 41 files already formatted | ✓ PASS |
| 60 MB benchmark on changed parser | `uv run pytest -q -m benchmark -s` | 4 passed, 1 skipped; parse 2.78 s, max loop gap 210.7 / 174.3 ms, peak 102 MB | ✓ PASS (loop-gap margin narrower than before: 210.7 vs 250 ms limit) |
| CR-01 paths (offsets, years, impossible date, stop variants, window edges) | scratchpad `cr01_rv.py` | every case parses, good programme kept, counters correct | ✓ PASS |
| `parse_xmltv_time` never raises | same script, 1,540-input sweep | 0 exceptions | ✓ PASS |
| 01-11 named tests exist | `pytest --collect-only -k ...` | 15 items collected (all passed in the full run) | ✓ PASS |
| WR-07 characterization | scratchpad `wr07.py` | stop year 2200 → `current_or_next` returns it; `overlapping(today)` still returns the real programme too | ⚠ see Anti-Patterns |
| IN-14 characterization | same script | `overlapping(start=0001-01-01)` raises OverflowError; start 1900 fine | ⚠ see Anti-Patterns |
| TDD gates | `git log 0237355^..HEAD`; `ls tdd-evidence/` | test → feat/fix order for all 3 cycles; 5 RED records + 3 JUnit reports present | ✓ PASS |

### Probe Execution

Step 7c: SKIPPED — no `scripts/*/tests/probe-*.sh` exist and no plan declares a probe.

### Requirements Coverage

All 20 phase requirement IDs are claimed by at least one plan (01-11 adds EVT-05, AUT-01, AUT-02); REQUIREMENTS.md maps exactly these 20 IDs to Phase 1 (no orphans).

| Requirement | Source Plan(s) | Status | Evidence |
|-------------|----------------|--------|----------|
| SRC-01 | 01-01, 01-07, 01-09 | ✓ SATISFIED | URL flow + tracer test |
| SRC-02 | 01-07, 01-09 | ✓ SATISFIED | file flow, allowlist check at setup and refresh |
| SRC-03 | 01-05, 01-07 | ✓ SATISFIED | magic-byte sniff |
| SRC-04 | 01-01, 01-07 | ✓ SATISFIED | refresh_hours 1..168 |
| SRC-09 | 01-05, 01-06, 01-09 | ✓ SATISFIED | executor parse, byte caps, local benchmark green on new parser (WR-02 warning) |
| SRC-13 | 01-07 | ✓ SATISFIED | normalized identity, already_configured |
| FLT-01 | 01-01, 01-08 | ✓ SATISFIED | multiple subentries, one download |
| FLT-02 | 01-01, 01-03, 01-08 | ✓ SATISFIED (picker UX: human) | sorted channel IDs, empty = all |
| FLT-03 | 01-03, 01-08 | ✓ SATISFIED | OR-combined include |
| FLT-04 | 01-03, 01-08 | ✓ SATISFIED | channel AND include AND NOT exclude |
| FLT-07 | 01-03, 01-08 | ✓ SATISFIED (WR-03 warning) | invalid regex keeps form open; blank lines ignored |
| EVT-01 | 01-02 | ✓ SATISFIED | exact-duplicate collapse |
| EVT-02 | 01-01, 01-05 | ✓ SATISFIED | location = display name, fallback channel id |
| EVT-05 | 01-02, 01-11 | ✓ SATISFIED (was PARTIAL) | all variants correct; out-of-range values skipped or stop inferred instead of crashing |
| EVT-06 | 01-02 | ✓ SATISFIED | stable UID format, order-independence |
| AUT-01 | 01-01, 01-04, 01-09, 01-11 | ✓ SATISFIED (live: human) | trigger test; get_events never raises for an unbuildable match |
| AUT-02 | 01-01, 01-04, 01-11 | ✓ SATISFIED | state on/off without refresh; `event` returns None instead of raising |
| CFG-01 | 01-01, 01-07, 01-08, 01-09 | ✓ SATISFIED (UI render: human) | config + subentry flows only |
| DST-01 | 01-06, 01-10 | ? NEEDS HUMAN | structure valid, HACS action green on ffd5363; custom-repo acceptance pending UAT |
| DST-02 | 01-06, 01-10 | ✓ SATISFIED | both workflows on push; next push will cover the 01-11 code (human check 6) |

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK` markers in the 7 files changed by 01-11. No stubs. Review findings (01-REVIEW.md, re-review after 01-11), checked against code:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| xmltv/parser.py, timeparse.py, window.py | 82-83 / 17-20 / 26,39-44 | WR-07: no duration plausibility; a well-formed programme with stop up to 2200 stays "current" (reproduced) | ⚠️ Warning | Only calendars whose filter matches that programme: `event`/state attributes show it instead of the real current match until its stop. `get_events` still returns the other events and their triggers still fire. Not a malformed timestamp in the SC3 sense (input is valid XMLTV, rendered faithfully). Escalated as human decision item 9 |
| coordinator.py / parser.py | 77-98 / 126-131 | WR-08: `ParseStats` (incl. `skipped_malformed`) never logged or exposed | ⚠️ Warning | Observability only; 01-02 #4 / 01-05 #7 require "skipped and counted", which holds. Phase 3 SC5 (diagnostics with counts, SRC-12) is the natural home |
| xmltv/window.py | 35, 41 | IN-14: `overlapping`/`current_or_next` overflow for a caller-supplied start within `_max_duration` of year 0001 (reproduced) | ⚠️ Warning (raised from info) | Only reachable with an absurd `calendar.get_events` start; HA frontend and triggers never send it. Literal "never raises" of 01-04 #1 holds for all data-driven paths. window.py unchanged since 2026-10-13 (pre-dates prior verification) |
| xmltv/parser.py | 21-25 | IN-11: `from None` hides but keeps `__context__` (feed text attached, not displayed) | ℹ️ Info | 01-05 #4 is about the message, which stays content-free |
| xmltv/parser.py | 166-170 | IN-12: "empty document" branch unreachable; empty input yields "invalid XML at line 1" | ℹ️ Info | Still a content-free FeedError (01-05 #4 holds) |
| calendar.py | 137-144 | IN-13: `event` returns None when the current match cannot be built | ℹ️ Info | Defensive path only; parser can no longer produce such a programme |
| xmltv/filter.py, parser.py | 16-18 / 59-60 | WR-01: ReDoS caps do not bound backtracking | ⚠️ Warning | Phase 2 notes plan ReDoS-aware validation |
| source.py / parser.py | 180-202 / 177-181 | WR-02: download join doubles peak; past programmes retained until after normalize | ⚠️ Warning | Benchmark budget still met (102 MB peak) |
| config_flow.py | 205-209 | WR-03: wrong pattern shown when two fields are invalid | ⚠️ Warning | Cosmetic error text |
| source.py / config_flow.py | 133-142 / 148 | WR-04: resolved symlink target persisted | ⚠️ Warning | Symlink-rotated file feeds go stale |
| README.md | 3-4, 38 | WR-05: "title and description" vs code's title and sub-title | ⚠️ Warning | Docs; README overhaul is DST-04 (Phase 4) |
| various | — | IN-01..IN-10 | ℹ️ Info | See 01-REVIEW.md |

Benchmark note (ℹ️): max loop gap rose from 66.9 ms (planning prototype) / 172.5 ms (01-11 summary) to 210.7 ms in this run, still under the 250 ms limit. Watch the CI benchmark job on the next push.

### Human Verification Required

Items 1-5 are the 01-09 ha-dev walkthrough on http://localhost:18123 (not :8123). Redeploy ha-dev first so it runs the 01-11 code. The small feeds cover 2026-10-14 00:00–12:01 only; regenerate with `--start-date $(date +%F)`.

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
**Expected:** No Reconfigure action; entity/device removed; same entity_id with new matches. Record acceptability until Phase 2.
**Why human:** User decision.

### 6. HACS custom repository and push CI (DST-01, DST-02, SC5)
**Test:** HACS → Custom repositories → add the GitHub URL as Integration; push the 01-11 commits.
**Expected:** Accepted, "XMLTV Calendar" listed with brand icon; CI (Ruff, Unit tests, Benchmark) and Validate (hassfest, HACS) green for the push.
**Why human:** Live HACS UI; pushing is the user's job.

### 7. Backstop: independent refresh of sources (01-07)
**Test:** Two sources with equal interval; refresh one.
**Expected:** No download/parse of the other.
**Why human:** No test; structural evidence only (insufficient_spec).

### 8. Judgment-tier prohibitions
**Test:** Confirm the three LLM verdicts in the Prohibitions table.
**Expected:** All hold.
**Why human:** unverified-prohibition — human review recommended.

### 9. Decision on WR-07 / IN-14 / WR-08
**Test:** Read WR-07, WR-08 and IN-14 in 01-REVIEW.md and the Anti-Patterns rows above.
**Expected:** Accept as non-blocking for Phase 1 and route them (recommended: WR-07 duration cap in `_programme`, ~3 lines plus one test, either as a quick task now or with Phase 2 FLT-08; WR-08 with Phase 3 SRC-12; IN-14 clamp in `window.py`), or request a second gap-closure plan.
**Why human:** WR-07 is close to the wording of SC3 ("never breaks the calendar"); the verifier judges it non-blocking because the input is well-formed and other events and triggers keep working, but the call belongs to the user.

### Gaps Summary

**The previous gap is closed.** CR-01 ("a single malformed programme never breaks the calendar", ROADMAP SC3) is fixed at every layer:

- `parse_xmltv_time` validates offset and year ranges and never raises;
- the parser skips and counts any programme whose conversion fails;
- only genuine read/decode failures become `FeedError` (WR-06);
- the calendar skips matches that cannot become a `CalendarEvent`.

The verifier reproduced every original failure path against the current code: all are contained, the valid programmes of the same feed survive, and the counters are correct. 15 new named tests pin the behavior. The full suite (238 passed), Ruff and the 60 MB benchmark are green.

**No regressions.** Only `timeparse.py`, `parser.py` and `calendar.py` changed in code, plus 4 test files. The ingestion error-message contract and the size caps are still green after the `_read_events` restructure.

**No goal-blocking gaps remain.** Status is `human_needed` because of the open UAT and decision items:

- the ha-dev walkthrough;
- HACS acceptance plus the first push of the 01-11 code;
- one backstop truth;
- three judgment-tier prohibitions;
- one decision on the review warnings WR-07, IN-14 and WR-08, which are classified non-blocking with the reasoning recorded above.

---

_Verified: 2026-10-14T14:31:56Z_
_Verifier: Claude (gsd-verifier)_
