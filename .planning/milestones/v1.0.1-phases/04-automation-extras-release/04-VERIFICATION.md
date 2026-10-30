---
phase: 04-automation-extras-release
verified: 2026-10-23T13:00:00Z
status: passed
score: 83/87 must-haves verified (5 roadmap SCs + 68 plan truths of 04-01..04-08 + 14 gap-closure truths of 04-09..04-11; 0 failed, 4 human/backstop)
covered_files: [".github/workflows/release.yml",".planning/phases/04-automation-extras-release/04-01-PLAN.md",".planning/phases/04-automation-extras-release/04-01-SUMMARY.md",".planning/phases/04-automation-extras-release/04-02-PLAN.md",".planning/phases/04-automation-extras-release/04-02-SUMMARY.md",".planning/phases/04-automation-extras-release/04-03-PLAN.md",".planning/phases/04-automation-extras-release/04-03-SUMMARY.md",".planning/phases/04-automation-extras-release/04-04-PLAN.md",".planning/phases/04-automation-extras-release/04-04-SUMMARY.md",".planning/phases/04-automation-extras-release/04-05-PLAN.md",".planning/phases/04-automation-extras-release/04-05-SUMMARY.md",".planning/phases/04-automation-extras-release/04-06-PLAN.md",".planning/phases/04-automation-extras-release/04-06-SUMMARY.md",".planning/phases/04-automation-extras-release/04-07-PLAN.md",".planning/phases/04-automation-extras-release/04-07-SUMMARY.md",".planning/phases/04-automation-extras-release/04-08-PLAN.md",".planning/phases/04-automation-extras-release/04-08-SUMMARY.md",".planning/phases/04-automation-extras-release/04-09-PLAN.md",".planning/phases/04-automation-extras-release/04-09-SUMMARY.md",".planning/phases/04-automation-extras-release/04-10-PLAN.md",".planning/phases/04-automation-extras-release/04-10-SUMMARY.md",".planning/phases/04-automation-extras-release/04-11-PLAN.md",".planning/phases/04-automation-extras-release/04-11-SUMMARY.md","README.md","blueprints/automation/xmltv_calendar/notify_before_programme.yaml","custom_components/xmltv_calendar/__init__.py","custom_components/xmltv_calendar/cache.py","custom_components/xmltv_calendar/calendar.py","custom_components/xmltv_calendar/config_flow.py","custom_components/xmltv_calendar/const.py","custom_components/xmltv_calendar/coordinator.py","custom_components/xmltv_calendar/data.py","custom_components/xmltv_calendar/diagnostics.py","custom_components/xmltv_calendar/manifest.json","custom_components/xmltv_calendar/match_store.py","custom_components/xmltv_calendar/matcher.py","custom_components/xmltv_calendar/sensor.py","custom_components/xmltv_calendar/source.py","custom_components/xmltv_calendar/translations/de.json","custom_components/xmltv_calendar/translations/en.json","custom_components/xmltv_calendar/xmltv/matches.py","custom_components/xmltv_calendar/xmltv/settings.py","custom_components/xmltv_calendar/xmltv/window.py","tests/test_advanced_flow.py","tests/test_blueprint.py","tests/test_cache.py","tests/test_diagnostics.py","tests/test_init.py","tests/test_last_fetch_sensor.py","tests/test_matcher_races.py","tests/test_matcher_runtime.py","tests/test_multiday_refresh.py","tests/test_new_match_event.py","tests/test_reconfigure.py","tests/test_repo_structure.py","tests/test_retention.py","tests/test_sensor.py","tests/test_source.py","tests/test_translations.py","tests/xmltv/test_matches.py","tests/xmltv/test_settings.py","tests/xmltv/test_window.py"]
covered_digest: "v3:sha256:d23cff9b6a9a1b94c185aa9e3f79be458f6d6b12bf48bc284847cb8fda218bc0"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 60/73
  gaps_closed:
    - "CR-01: SC1 / SC2 / 04-01 T1+T6 / 04-04 T1 / 04-06 T1: match state, events and retention no longer depend on the calendar entity being added (CalendarMatcher, plan 04-09)"
    - "WR-01: 04-04 T4 + prohibition, 04-06 T5: a DATA refilter can no longer supersede a CONFIG baseline / D-17 recheck (plan 04-10)"
    - "IN-05: 04-08 T1: all six failure_reason states translated in en.json and de.json, completeness test derived from coordinator.FAILURE_REASONS (plan 04-11)"
  gaps_remaining: []
  regressions: []
advisory:
  - finding: "Review WR-01 (2026-10-23): matchers are started before async_forward_entry_setups, but teardown exists only in async_unload_entry. If setup raises after a matcher started, HA does not call unload, so listeners and refilters leak and a retry creates a second set of matchers (duplicate events)"
    category: other
    reason: "Failure-path lifecycle defect, confirmed by reading __init__.py:48-56 (only the update listener is registered with entry.async_on_unload). No must-have truth covers a failed setup, so it is not a gap. Fix: register matcher.async_stop(capture=False) with entry.async_on_unload"
    evidence_status: "code inspection, no test"
  - finding: "Review WR-02: matcher.py:429-430 uses DeviceRegistry.async_get_device_by_identifier while hacs.json promises HA 2026.3.0"
    category: other
    reason: "Not introduced by gap closure: the identical call exists at base 1226412 (calendar.py:412). The minimum HA version that has the method could not be checked offline (installed HA is 2026.10.1). A calendar rename could raise AttributeError on an older HA"
    evidence_status: "unproven for older HA versions"
  - finding: "Review WR-03 / IN-04: match-store fingerprint ignores the HA time zone when naive_timezone is local"
    category: other
    reason: "Carried over from the first review, outside the gap-closure scope. Retained matches can show at shifted times for up to the retention window after an HA time zone change"
    evidence_status: "code inspection"
  - finding: "Review IN-04 (2026-10-23): a new match brought by a refresh is announced silently if a filter edit lands during that refresh's filter scan"
    category: other
    reason: "Consequence of the D-10 'edits are silent' rule; the window is one filter scan. README does not mention that a coinciding refresh is swallowed"
    evidence_status: "code inspection (matcher.py:266-279)"
human_verification:
  - test: "04-01 (ha-dev): open a calendar's device page in English, then in German; then disable the calendar entity, reload the entry, and look at the next-programme sensor"
    expected: "'Next programme' / 'Nächste Sendung' with title, channel, start and end attributes; the state is the next start in local time, also while the calendar entity is disabled"
    why_human: "Frontend rendering of entity and attribute names is not asserted by any test"
  - test: "04-02 (ha-dev): import the blueprint with the README 'Import blueprint' button, set the lead time to minus 2 minutes in the duration field, pick a mobile-app notify entity, and wait for a match"
    expected: "The import dialog opens pre-filled, the negative duration is saved as a valid offset, and one notification arrives per match, including two that start at the same time"
    why_human: "The frontend duration selector, the my.home-assistant redirect and a real notify entity cannot run under pytest"
  - test: "04-04 (ha-dev): in Developer tools > Events, listen to xmltv_calendar_new_match, add a matching future programme to the test feed, run homeassistant.update_entity, then restart HA; repeat once with the calendar entity disabled"
    expected: "Exactly one event with title, channel and local start, also with the calendar disabled; no repeat after the restart"
    why_human: "The real event bus and a real HA restart (final write of the delayed Store save) are not exercised end to end"
  - test: "04-05 (ha-dev): enable 'Last fetch' on a calendar device, run homeassistant.update_entity, switch the UI to German; provoke one failure (unreachable URL)"
    expected: "State updates; trigger 'Manual'; 'Letzter Abruf' / 'Auslöser' / 'Ergebnis' / 'Fehlergrund' and the failure reason text ('Abruf fehlgeschlagen') are translated"
    why_human: "Frontend rendering of translated attribute states"
  - test: "04-06 (ha-dev): let a match end, drop it from the test feed, refresh, restart HA, then download diagnostics"
    expected: "The match stays in the calendar view for the retention days and is listed under retained in diagnostics"
    why_human: "Real calendar view, real stop event and .storage on disk, diagnostics download"
  - test: "04-07 (ha-dev, German): edit a calendar, tick 'Erweiterte Optionen'"
    expected: "'Vergangene Treffer behalten (Tage)' with help text, box field 0..7, saved value prefilled on the next edit, no reload"
    why_human: "Frontend rendering of the translated number field"
  - test: "04-08 (ha-dev, German): walk through adding a URL and a file source, the options flow, adding and editing a calendar including the advanced step and preview, one validation error per form, both sensors"
    expected: "No raw translation key anywhere, including failure_reason values"
    why_human: "How the frontend renders served strings needs a person looking at the German UI"
  - test: "04-08: read README.md end to end (setup, regex examples, sensors, event payload, automation examples, limitations incl. 15-minute trigger window and overlapping events, releases)"
    expected: "Prose is accurate. The backstop truth 'a match added < 15 min before its trigger time may not trigger' matches what HA does, or is accepted as documented HA core behaviour. Optionally add a sentence on the review IN-04 edge (a refresh that coincides with a filter edit is announced silently)"
    why_human: "Tests check presence of content, not accuracy; the 15-minute window is HA core behaviour (backstop truth 04-08 T9)"
  - test: "DST-03 / SC5: confirm that HACS offers XMLTV Calendar 0.1.0-rc1 (prereleases enabled) and later push the final v0.1.0 (manifest.json to 0.1.0 first). Note that the 22 unpushed commits, including the whole gap-closure work (matcher.py), are NOT in the published v0.1.0-rc1"
    expected: "The Release workflow passes check-version, CI and Validate and publishes the release; HACS lists the version. rc1 is published as a Pre-release (observed, run 39845820757 success). A final v0.1.0 containing the fixes is still to be tagged by the user"
    why_human: "Only the user pushes and tags; HACS pickup can only be observed in a HACS client (D-29, 04-08 T10 backstop)"
  - test: "04-05 T13 (backstop): accept or test 'a refresh cancelled part-way records no run; a manual refresh during a scheduled one is serialized by the coordinator lock'"
    expected: "Accepted as an HA guarantee, or a test asserting coordinator.last_attempt is unchanged after a cancelled refresh is added"
    why_human: "test_same_instant_runs_keep_the_latest covers the same-instant half. test_cancelled_refresh_records_no_failure asserts health only, not last_attempt, so the cancellation half has no direct evidence (insufficient_spec)"
  - test: "Confirm the non-authoritative judgment-tier prohibition verdicts (11 items, see table) and set dispositions for the findings. 04-REVIEW-DISPOSITION.md still lists the 8 findings of the FIRST review, all 'open'; the fresh 04-REVIEW.md has different IDs (WR-01..03, IN-01..05)"
    expected: "All 11 prohibitions accepted as holding. Old CR-01, WR-01, IN-01, IN-05 recorded as fixed. IN-04 (time zone fingerprint), IN-02, IN-03, IN-06 and the new review warnings fixed or deferred with a reason"
    why_human: "Judgment-tier prohibitions and review dispositions need a human decision; the verifier's verdict is not authoritative"
---

# Phase 4: Automation Extras & Release Verification Report

**Phase Goal:** User can automate around matches beyond plain calendar triggers (next-match sensor, new-match event, recent past matches, ready-made blueprint) and install a documented, bilingual, tagged release via HACS.
**Mode:** mvp (ROADMAP). As in the earlier phases, the goal is a capability statement, not a User Story, and the plans carry no user story. The goal text and the five roadmap success criteria serve as the contract. This does not affect the verdict.
**Verified:** 2026-10-23T13:00:00Z
**Status:** human_needed
**Re-verification:** Yes, after gap closure (plans 04-09, 04-10, 04-11)

## Verdict in one paragraph

All three gaps of the 21 Oct report are closed in the code, not only in the SUMMARYs. Per-calendar match state now lives in `CalendarMatcher` (`matcher.py`, 474 lines), created and started in `async_setup_entry` before platform admission, and read by the calendar entity, both sensors and diagnostics. A disabled calendar entity no longer disables the sensor, the new-match event or retention. A DATA refilter can no longer supersede a CONFIG refilter, because an accepted edit is stored as a `_ConfigSnapshot` in `_pending_config`. It carries its own feed snapshot and recheck set, and only a completed commit clears it. All six `failure_reason` values are translated in English and German, and the completeness test derives its requirement from `coordinator.FAILURE_REASONS`. No must-have is failed, so the status is `human_needed`: only the previously known human items remain (frontend checks, README accuracy, HACS pickup and final tag, one backstop truth, judgment-tier prohibitions). The fresh review has 0 critical findings and 3 warnings. None falsifies a truth, but WR-01 (matcher leak when setup fails) is worth fixing before the final tag.

## User Flow Coverage

| Step | Expected | Evidence | Status |
|------|----------|----------|--------|
| Automate on the next match | Each calendar has a "Next programme" timestamp sensor that follows time, feed and edits, also with the calendar entity disabled | `sensor.py:115-134` reads `runtime.matchers[sid].next_match`; `test_disabled_calendar_keeps_matching` asserts the sensor state with `calendar.f1` disabled and moving to 07:00Z after a refresh; `test_disabled_counts_without_calendar_objects` pops the calendar object and still gets the right sensor state | VERIFIED |
| Automate on new programmes | `xmltv_calendar_new_match` once per new match, silent on first refresh, restart, reload, edits, also with a disabled calendar | `matcher.py:232-282`, `_commit_filter` fire gate (line 274); exact nine-key payload asserted for the disabled calendar (`test_disabled_calendar_keeps_matching`) and after a concurrent edit (`test_data_during_config_preserves_baseline_and_retention`) | VERIFIED |
| See recent past matches | Ended matches stay N (0..7) days after the feed drops them, across restarts and while the calendar is disabled | `matcher.py:203-215, 300-324`; `test_disabled_edits_and_retained_reenable`, `test_retention.py`, `test_retention_only_edits_zero_and_seven` | VERIFIED |
| Use a ready-made blueprint | Import, mode queued, one run per match incl. overlap | `notify_before_programme.yaml`; `test_overlapping_programmes_notify_once_each` | VERIFIED (frontend import is a human item) |
| Bilingual | All flow strings and sensor attribute states in EN and DE | `test_every_flow_key_is_translated`, `test_german_ui_is_served_for_every_required_key`, `test_failure_reason_vocabulary_is_required` | VERIFIED |
| Documented | README covers setup, regex, automations, limitations | README sections; `test_readme_documents_*` | VERIFIED (prose accuracy is a human item) |
| Install a tagged release via HACS | Tag push, release, HACS offers it | `v0.1.0-rc1` pushed by the user, Release run 39845820757 succeeded, `gh release list` shows `v0.1.0-rc1 Pre-release`; manifest at the tag is 0.1.0-rc1 | PARTIAL, HUMAN (HACS pickup, final v0.1.0 tag) |

## Goal Achievement

### Re-check of the previously failed gaps

| Gap | Previous status | Now | Evidence |
|-----|-----------------|-----|----------|
| CR-01 disabled calendar entity | Failed (6 truths) | CLOSED | `__init__.py:48-52` creates and `async_start`s one `CalendarMatcher` per calendar subentry before `async_forward_entry_setups`. The entity (`calendar.py:76-96`) only attaches to `runtime.matchers[sid]`. Event entity ID comes from the entity registry (`matcher.py:177-180`), which has an entry for a disabled entity. Sensors and diagnostics read `runtime.matchers` (`sensor.py:125, 210`, `diagnostics.py:99-105`). Tests: `test_disabled_calendar_keeps_matching`, `test_disabled_counts_without_calendar_objects`, `test_disabled_edits_and_retained_reenable`, `test_late_add_rename_and_entity_toggle_keep_one_matcher` |
| WR-01 CONFIG/DATA refilter race | Partial (04-04 T4, 04-06 T5, prohibition violated) | CLOSED | `matcher.py:236-282`: while `_pending_config` is set, every refilter runs with the edit's own `spec`, `epg` snapshot and `recheck` set; `fire` requires `change is None`; a revision bump `continue`s instead of returning; only a completed commit clears `_pending_config`. The exact earlier repro (widen from daserste.de to daserste.de + zdf.de, hold the executor job, deliver one new daserste programme) is `test_data_during_config_preserves_baseline_and_retention[widen]` and asserts exactly one event (daserste, full payload), both zdf UIDs in the seen-set, retained matches removed, and no repeat after refresh and reload. Narrow, enabled and disabled variants run too |
| IN-01 template-only edit scans | Warning | CLOSED | `matcher.py:421` compares compiled specs; `test_template_only_edit_does_not_scan` asserts zero scans for valid, normalized and invalid patterns |
| IN-05 failure_reason states | Partial (04-08 T1) | CLOSED | Programmatic check: en.json and de.json both hold `entity.sensor.last_fetch.state_attributes.failure_reason.state` for all six `FAILURE_REASONS`. `tests/test_translations.py:204` derives the requirement from `coordinator.FAILURE_REASONS`; negative tests `test_missing_failure_reason_translation_is_detected`, `test_paired_failure_reason_omission_defeats_parity_but_not_completeness`, `test_new_failure_reason_is_required_automatically` |

### Roadmap Success Criteria (contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | Next-match timestamp sensor with title, channel, start, end; updated as matches pass or the feed changes | ✓ VERIFIED | `test_next_match_sensor_shows_next_start`, `test_sensor_moves_on_at_match_start`, `test_sensor_follows_new_feed_data`, `test_sensor_follows_filter_and_template_edits`; disabled calendar case now covered (`test_disabled_calendar_keeps_matching`) |
| SC2 | New-match event (not first refresh, not after restart); past N days retained across restarts | ✓ VERIFIED | `test_new_programme_fires_one_event`, `test_restart_does_not_announce_again`, `test_double_reload_keeps_seen_set`, `test_dropped_match_stays_for_retention_days`, `test_capture_on_stop`, plus the disabled and race tests above |
| SC3 | Blueprint, `mode: queued`, one notification per match incl. overlapping | ✓ VERIFIED | unchanged from the first verification (blueprint untouched since; test passes in this run) |
| SC4 | Every config, subentry and options flow step, error and abort reason in German / English | ✓ VERIFIED | AST-derived completeness plus served German; now also the attribute states |
| SC5 | Tag push publishes a release matching `manifest.json`, HACS offers it; README documents setup, regex, automations, limitations | ? HUMAN | Publish is now observed: `v0.1.0-rc1` tag at origin, Release run success, GitHub release exists as Pre-release, tag equals manifest version `0.1.0-rc1`. HACS pickup is not observable here; the final v0.1.0 is a user step |

### Plan Must-Have Truths

| Plan | Truths | Verified | Failed | Human / backstop | Notes |
|------|--------|----------|--------|------------------|-------|
| 04-01 next-match sensor | 10 | 10 | – | – | T1 and T6 now hold for disabled calendars |
| 04-02 blueprint | 7 | 7 | – | – | unchanged |
| 04-03 release workflow | 5 | 5 | – | – | `release.yml` unchanged; it ran for real on rc1 |
| 04-04 new-match event | 7 | 7 | – | – | T1 (CR-01) and T4 (WR-01) closed |
| 04-05 last-fetch sensor | 13 | 12 | – | T13 | T4 `matches` now correct for a disabled calendar. T13 stays a backstop (see human item) |
| 04-06 retention | 11 | 11 | – | – | T1 and T5 closed |
| 04-07 retention field | 5 | 5 | – | – | unchanged |
| 04-08 translations, README, release readiness | 10 | 8 | – | T9, T10 | T1 closed (IN-05). T9 and T10 are backstop truths |
| 04-09 matcher (CR-01) | 6 | 6 | – | – | See below |
| 04-10 ordering (WR-01, IN-01) | 5 | 5 | – | – | See below |
| 04-11 failure_reason translations | 3 | 3 | – | – | en/de content, vocabulary-derived test, URL-free attribute unchanged |
| **Roadmap SCs** | 5 | 4 | – | SC5 | |
| **Total** | **87** | **83** | **0** | **4** | Behavior-unverified: 0 |

Gap-closure truths checked against code, not SUMMARY:

- **04-09 T1-T3** (disabled calendar keeps sensor, events, retention): `test_disabled_calendar_keeps_matching`, `test_disabled_edits_and_retained_reenable` (production path through the real setup, registry disable, reload and refresh; no matcher mocking).
- **04-09 T4** (sensors and diagnostics read the matcher): `sensor.py:125,210`, `diagnostics.py:99-105`; `test_disabled_counts_without_calendar_objects` removes the calendar object from `runtime.calendars` and still gets `matches` 3 and 2 in sensor and diagnostics.
- **04-09 T5** (lifecycle: one matcher per subentry, unload captures, invalidates, flushes; failed unload keeps matchers): `__init__.py:67-92, 109-117`, `matcher.py:163-175` (`async_stop` captures, bumps `_generation`, unsubscribes both listeners); `test_stop_captures_and_invalidates_worker`, `test_blocked_worker_teardown`, `test_failed_unload_keeps_runtime_live`, `test_removed_during_initial_filter_does_not_recreate_presentation`.
- **04-09 T6** (existing edge contracts): 04-01 tests in `tests/test_sensor.py` still pass.
- **04-10 T1-T5**: `test_data_during_config_preserves_baseline_and_retention` (4 variants), `test_newer_edit_keeps_pending_config_semantics`, `test_template_only_edit_does_not_scan` (3 variants), `test_template_edit_during_data_preserves_new_event`, `test_newer_data_supersedes_held_data`, `test_held_config_teardown_does_not_commit`, `test_retention_only_edits_zero_and_seven`, `test_invalid_initial_filter_retention_edit_finishes`. The gate (`_held_filter`) holds one real executor call of `matcher._apply_filter`, so the tests exercise the real interleaving.
- **04-11 T1-T3**: programmatic key check above; `test_german_ui_is_served_for_every_required_key` serves German through HA's loader.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/xmltv_calendar/matcher.py` | CalendarMatcher independent of Entity lifecycle | ✓ VERIFIED | 474 lines, wired from `__init__.py`, `calendar.py`, `sensor.py`, `diagnostics.py`, `data.py` |
| `custom_components/xmltv_calendar/data.py` | `XmltvRuntimeData.matchers` | ✓ VERIFIED | `matchers: dict[str, CalendarMatcher]` line 26 |
| `custom_components/xmltv_calendar/calendar.py` | Presentation only | ✓ VERIFIED | 184 lines, delegates to the matcher. About 45 lines of test-only facade remain (review IN-01) |
| `custom_components/xmltv_calendar/sensor.py` | NextMatchSensor, LastFetchSensor reading matchers | ✓ VERIFIED | Imports `device_info`, `signal_matches` via `.calendar` instead of `.matcher` (review IN-02, cosmetic) |
| `custom_components/xmltv_calendar/translations/{en,de}.json` | failure_reason states | ✓ VERIFIED | 6/6 in both |
| `tests/test_matcher_runtime.py`, `tests/test_matcher_races.py`, `tests/test_translations.py` | Regression tests | ✓ VERIFIED | 8 + 8 test functions (parametrized), plus translation tests; all pass |
| Artifacts of 04-01..04-08 | | ✓ VERIFIED | No regression found; full suite passes |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `__init__.py` | `matcher.py` | `CalendarMatcher(hass, entry, subentry)`, `await matcher.async_start()`, before `async_forward_entry_setups` (lines 50-53, 84-86) | WIRED |
| `sensor.py` | `data.py` | `self._entry.runtime_data.matchers.get(...)` (lines 125, 210) | WIRED |
| `diagnostics.py` | `data.py` | `runtime.matchers.items()` (line 99) | WIRED |
| `matcher.py` | `match_store.py` | `store.get/put` in `_commit_filter` and `_capture_now`; flush in `async_unload_entry` | WIRED |
| `matcher.py` | event bus | `hass.bus.async_fire(EVENT_NEW_MATCH, ...)` with registry entity ID (lines 342-362) | WIRED |
| `matcher.py` | coordinator | `coordinator.async_add_listener(_handle_coordinator_update)` (line 159), removed in `async_stop` | WIRED |
| `matcher.py` | sensors/calendar | `async_dispatcher_send(signal_matches(...))` after each commit and template edit | WIRED |
| `__init__._async_entry_updated` | `matcher.async_apply_subentry` | line 77 | WIRED |
| `tests/test_translations.py` | `coordinator.FAILURE_REASONS` | line 204 | WIRED |
| Earlier links (release.yml, blueprint, README, config_flow/settings) | | unchanged from the first verification | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| NextMatchSensor | `_attr_native_value`, attributes | `matchers[sid]._index` ← `_commit_filter` ← `coordinator.data` via `_apply_filter` in the executor | Yes, also for a disabled calendar (test asserts the real sensor state) | ✓ FLOWING |
| new-match event | payload | `new_matches(result.matches, record.seen)` in `_commit_filter` | Yes | ✓ FLOWING |
| LastFetchSensor / diagnostics | `matches`, `retained` | `matcher.match_count`, `retained_count` | Yes | ✓ FLOWING |
| Calendar events | `_index`, `_retained_shown` | matcher | Yes | ✓ FLOWING |
| failure_reason attribute | `attempt.failure_reason` (vocabulary key) | `coordinator.py:300-303` | Yes, translated by HA | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite (run once) | `uv run pytest -q -m "not benchmark"` | 1025 passed, 4 skipped, 4 deselected (the orchestrator's 1029 passed counts the 4 benchmark tests) | ✓ PASS |
| Gap-closure and regression modules | `pytest tests/test_matcher_runtime.py tests/test_matcher_races.py tests/test_translations.py tests/test_sensor.py tests/test_new_match_event.py tests/test_retention.py` | 96 passed | ✓ PASS |
| Lint / format | `uv run ruff check .` / `ruff format --check .` | All checks passed / 75 files formatted | ✓ PASS |
| failure_reason states in both languages | JSON load of en.json and de.json | 6 states each, keys equal `FAILURE_REASONS` | ✓ PASS |
| Release published for the pushed tag | `gh release list`, `gh run list`, `git ls-remote --tags origin` | `v0.1.0-rc1` Pre-release; Release run success; tag at origin equals manifest 0.1.0-rc1 | ✓ PASS |
| No commits or tags created by the assistant | `git status -sb`, `git log origin/main..HEAD` | the rc1 tag and commit are the user's (`a176b17`, author Alexander Kentner); 22 commits unpushed | ✓ PASS |

The CR-01 and WR-01 repro scratch files from the first run no longer exist. They are superseded by the production-path regressions above, which reproduce the same scenarios (disabled calendar plus new feed match; widened filter, held executor job, one new daserste programme).

### Probe Execution

No probes declared or present (`scripts/` has no `tests/probe-*.sh`). SKIPPED.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| AUT-03 | 04-01, 04-09, 04-10 | Next-match timestamp sensor per calendar | ✓ SATISFIED | Enabled and disabled calendars, follows time, feed and edits |
| AUT-05 | 04-02 | Blueprint, `mode: queued` | ✓ SATISFIED | Blueprint plus schema and e2e tests. REQUIREMENTS.md still shows `[ ]` / "Gaps Found" (stale bookkeeping) |
| AUT-06 | 04-05, 04-09, 04-11 | Diagnostic "Last fetch" sensor, disabled by default, no URL | ✓ SATISFIED | `test_last_fetch_is_diagnostic_and_disabled_by_default`, `test_no_secrets_in_last_fetch`, matcher-backed `matches` |
| EVT-07 | 04-06, 04-07, 04-09, 04-10 | Past N days (≤7) stay visible after the feed drops them | ✓ SATISFIED | Disabled and race cases closed |
| EVT-08 | 04-04, 04-09, 04-10 | Event on new matching programme, not first refresh, not after restart | ✓ SATISFIED | Disabled and race cases closed |
| CFG-04 | 04-01, 04-05, 04-07, 04-08, 04-11 | UI in English and German | ✓ SATISFIED (automated); German UI walkthrough is a human item | Flows and attribute states complete |
| DST-03 | 04-03, 04-08 | Tagged releases match `manifest.json` | ? NEEDS HUMAN | Workflow ran for real on `v0.1.0-rc1`; HACS pickup and the final v0.1.0 are user steps. REQUIREMENTS.md still "Gaps Found" |
| DST-04 | 04-08 | README: setup, regex, automation examples, limitations | ✓ SATISFIED | README sections plus `test_readme_documents_automation_and_limitations`. REQUIREMENTS.md still shows `[ ]` / "Gaps Found" (stale bookkeeping) |

All 8 phase IDs appear in plan frontmatter (04-09: AUT-03, AUT-06, EVT-07, EVT-08; 04-10: EVT-08, EVT-07, AUT-03; 04-11: CFG-04, AUT-06; earlier plans as before). REQUIREMENTS.md maps exactly these 8 to Phase 4. No orphans. REQUIREMENTS.md bookkeeping: AUT-03, AUT-06, EVT-07, EVT-08, CFG-04 are marked Complete again; AUT-05, DST-03, DST-04 are still `[ ]` / "Gaps Found" from the earlier revert (commit 1031424), although AUT-05 and DST-04 are satisfied. The orchestrator should update them (DST-03 only after the final tag).

### Prohibitions (judgment tier, non-authoritative verifier verdicts)

| Plan | Prohibition | Verdict |
|------|-------------|---------|
| 04-01 | MUST NOT record match descriptions/sub-titles/episodes | Holds (`_unrecorded_attributes`, `test_match_texts_are_not_recorded`) |
| 04-02 | MUST NOT drop overlapping programmes / use mode single | Holds |
| 04-03 | MUST NOT publish a release whose tag differs from manifest | Holds (check step; rc1 run matched) |
| 04-04 | MUST NOT announce because of restart, reload, edit or timezone change | Holds now (was violated). Edge: a refresh that coincides with an edit is announced silently (review IN-04, by the D-10 design) |
| 04-04 | MUST NOT fire more than 50 events per calendar and refresh | Holds (`split_announcements`, `test_burst_is_capped`) |
| 04-05 | MUST NOT expose URL, host, path or credentials | Holds |
| 04-06 | MUST NOT keep showing a future/airing match the feed removed | Holds |
| 04-07 | MUST NOT reload or download on a retention-only edit | Holds |
| 04-08 | MUST NOT push commits/tags or create the release from the assistant | Holds |
| 04-09 | MUST NOT make disabling the calendar presentation silently opt out of sensor automation, events or retention (CR-01) | Holds (`test_disabled_calendar_keeps_matching`, `test_disabled_edits_and_retained_reenable`) |
| 04-09 | MUST NOT record long match texts as state history (D-04) | Holds (`_unrecorded_attributes` unchanged) |
| 04-10 | MUST NOT notify about programmes merely exposed by filter/template edits, restart, reload or timezone changes | Holds (race regressions) |

These are flagged as `unverified-prohibition, human review recommended` per the judgment-tier rule; none is a gap.

### Test Quality Audit

| Test File | Linked Req | Skipped | Circular | Assertion Level | Verdict |
|-----------|------------|---------|----------|-----------------|---------|
| tests/test_matcher_runtime.py | AUT-03, AUT-06, EVT-07, EVT-08 | 0 | No | Behavioral, real setup, registry disable, reload, stored seen-set, exact payload | OK |
| tests/test_matcher_races.py | EVT-07, EVT-08, AUT-03 | 0 | No | Behavioral, gates a real executor call, exact payload and persisted state | OK. `_held_filter` is duplicated in both modules (review IN-05) |
| tests/test_translations.py | CFG-04 | 0 | No | Code-derived vocabulary plus served German; negative tests | OK |
| tests/test_sensor.py, test_new_match_event.py, test_retention.py, test_last_fetch_sensor.py, test_blueprint.py, test_repo_structure.py | | 0 | No | Unchanged and passing | OK |

Disabled tests on requirements: 0. The 4 skipped tests are conditional or real-feed gates, not requirement tests.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (phase files) | – | TBD/FIXME/XXX | – | None found (grep over `custom_components`, new tests, README) |
| `__init__.py` | 48-56 | Matcher teardown only in `async_unload_entry`; a failed setup leaks started matchers (review WR-01) | ⚠️ Warning | Possible duplicate events after a failed setup and retry. No truth covers it |
| `matcher.py` | 429-430 | `async_get_device_by_identifier` vs HA floor 2026.3.0 (review WR-02, pre-existing at 1226412) | ⚠️ Warning | Possible `AttributeError` on a calendar rename on an older HA |
| `__init__.py` | 31-35 | Fingerprint ignores the HA time zone (review WR-03 / IN-04, carried) | ⚠️ Warning | Shifted retained times after a time zone change |
| `matcher.py` | 266-279 | Refresh that coincides with an edit is announced silently (review IN-04) | ℹ️ Info | By D-10 design |
| `matcher.py` | 239-241 | Pending edit with `epg=None` could never complete (review IN-03) | ℹ️ Info | Not reachable today |
| `calendar.py` | 104-149 | ~45 lines of test-only compatibility facade (review IN-01) | ℹ️ Info | Drift risk |
| `sensor.py` | 14 | Implicit re-export from `.calendar` (review IN-02) | ℹ️ Info | `mypy --strict` would reject |
| `source.py`, `cache.py`, blueprint yaml | | Old IN-02, IN-03, IN-06 | ℹ️ Info | Unchanged, low impact |

None of the new warnings are debt markers or blockers.

### Decision Coverage

All trackable CONTEXT.md decisions remain honored (31/31 in the first report; the gap-closure plans cite D-01..D-25 and D-31 and the matching tests cover them).

### Human Verification Required

Eleven items are listed in the frontmatter `human_verification`: the seven deferred ha-dev checks (now also covering a disabled calendar and the failure_reason text), the README accuracy read with the 15-minute-window backstop, the HACS pickup and final v0.1.0 tag (user step D-29), the 04-05 T13 backstop, and the prohibition and disposition confirmation. 04-REVIEW-DISPOSITION.md is stale: it lists the first review's eight findings, all `open`.

### Gaps Summary

None. All previously failed truths pass with named, production-path tests that were run in this verification, and no regression appeared in the other 73 truths. The remaining work is human: the ha-dev walkthrough (run it on the post-gap-closure code), the decision on the review warnings (WR-01 matcher leak on failed setup is the one worth fixing before the final tag), and the user's push of the 22 unpushed commits plus the final `v0.1.0` tag. The published `v0.1.0-rc1` does not contain the gap-closure work.

---

_Verified: 2026-10-23T13:00:00Z_
_Verifier: Claude (gsd-verifier)_

## Acknowledged Gaps

Status set to `passed` manually by the user on 2026-10-23 after UAT (8 passed, 0 issues, 3 skipped). Open items accepted without verification:

- UAT test 8: README end-to-end read (15-minute trigger-window wording, optional IN-04 sentence) not performed.
- UAT test 9: final v0.1.0 tag/push not done; only v0.1.0-rc1 is published and the 22 unpushed commits (incl. gap-closure `matcher.py`) are not in it.
- UAT test 10: backstop "cancelled refresh records no run" neither accepted formally nor covered by a test.
- Advisory review findings (WR-01 matcher teardown on failed setup, WR-02 DeviceRegistry method vs. HA 2026.3.0 floor, WR-03/IN-04 time zone fingerprint) remain open.
