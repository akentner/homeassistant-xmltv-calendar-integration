---
phase: 04-automation-extras-release
verified: 2026-10-21T11:05:00Z
status: gaps_found
score: 60/73 must-haves verified (5 roadmap SCs + 68 plan truths; 9 failed, 4 human/backstop)
covered_files: [".github/workflows/release.yml",".planning/phases/04-automation-extras-release/04-01-PLAN.md",".planning/phases/04-automation-extras-release/04-01-SUMMARY.md",".planning/phases/04-automation-extras-release/04-02-PLAN.md",".planning/phases/04-automation-extras-release/04-02-SUMMARY.md",".planning/phases/04-automation-extras-release/04-03-PLAN.md",".planning/phases/04-automation-extras-release/04-03-SUMMARY.md",".planning/phases/04-automation-extras-release/04-04-PLAN.md",".planning/phases/04-automation-extras-release/04-04-SUMMARY.md",".planning/phases/04-automation-extras-release/04-05-PLAN.md",".planning/phases/04-automation-extras-release/04-05-SUMMARY.md",".planning/phases/04-automation-extras-release/04-06-PLAN.md",".planning/phases/04-automation-extras-release/04-06-SUMMARY.md",".planning/phases/04-automation-extras-release/04-07-PLAN.md",".planning/phases/04-automation-extras-release/04-07-SUMMARY.md",".planning/phases/04-automation-extras-release/04-08-PLAN.md",".planning/phases/04-automation-extras-release/04-08-SUMMARY.md","README.md","blueprints/automation/xmltv_calendar/notify_before_programme.yaml","custom_components/xmltv_calendar/__init__.py","custom_components/xmltv_calendar/cache.py","custom_components/xmltv_calendar/calendar.py","custom_components/xmltv_calendar/config_flow.py","custom_components/xmltv_calendar/const.py","custom_components/xmltv_calendar/coordinator.py","custom_components/xmltv_calendar/data.py","custom_components/xmltv_calendar/diagnostics.py","custom_components/xmltv_calendar/match_store.py","custom_components/xmltv_calendar/sensor.py","custom_components/xmltv_calendar/source.py","custom_components/xmltv_calendar/translations/de.json","custom_components/xmltv_calendar/translations/en.json","custom_components/xmltv_calendar/xmltv/matches.py","custom_components/xmltv_calendar/xmltv/settings.py","custom_components/xmltv_calendar/xmltv/window.py","tests/test_advanced_flow.py","tests/test_blueprint.py","tests/test_cache.py","tests/test_diagnostics.py","tests/test_init.py","tests/test_last_fetch_sensor.py","tests/test_multiday_refresh.py","tests/test_new_match_event.py","tests/test_reconfigure.py","tests/test_repo_structure.py","tests/test_retention.py","tests/test_sensor.py","tests/test_source.py","tests/test_translations.py","tests/xmltv/test_matches.py","tests/xmltv/test_settings.py","tests/xmltv/test_window.py"]
covered_digest: "v3:sha256:ecc778e7310e5a0a7abdf826ae10d4bcc8fd8ed4b4f34e532ed8b80f798e104d"
behavior_unverified: 0
overrides_applied: 0
decision_coverage:
  honored: 31
  total: 31
  not_honored: []
gaps:
  - truth: "SC1 / 04-01 T1, T6: each calendar's next-match sensor shows the earliest future match and follows time, feed data and edits"
    status: failed
    reason: "CR-01, reproduced. All per-calendar match state (filter result, MatchIndex, seen-set writes, retention capture, event firing) lives in XmltvCalendarEntity._async_refilter, which only runs once the entity is added to hass. When the user disables the calendar entity, HA never adds it, but the object still sits in runtime.calendars with an empty MatchIndex. NextMatchSensor then shows unknown permanently, although future matches exist"
    artifacts:
      - path: "custom_components/xmltv_calendar/calendar.py"
        issue: "Match state is owned by the entity (lines 175-185, 187-194, 246-319). async_apply_subentry returns early at line 415 while hass is None, so edits to a disabled calendar do nothing"
      - path: "custom_components/xmltv_calendar/sensor.py"
        issue: "_recompute reads runtime.calendars[...].next_match(), an empty index for a disabled calendar (lines 247-252). LastFetchSensor reports matches 0 (line 338)"
      - path: "custom_components/xmltv_calendar/__init__.py"
        issue: "No per-subentry matcher independent of the entity (lines 61-76)"
      - path: "README.md"
        issue: "Line 164 says unknown means 'no upcoming match'. That is false for a disabled calendar, and the coupling is not documented"
    missing:
      - "Move the per-calendar match state into an entity-independent runtime object (one per calendar subentry, with its own coordinator listener) that the calendar and both sensors read from. Minimum alternative: log a warning and document that the sensor, event and retention require the calendar entity to be enabled, and override the affected truths"
      - "Regression test: disable calendar.<x>, reload, then assert the sensor state equals the next start and that a new feed match fires xmltv_calendar_new_match"
  - truth: "SC2 / 04-04 T1 / 04-06 T1: a new matching programme fires xmltv_calendar_new_match; ended matches stay for N days after the feed drops them, across restarts"
    status: failed
    reason: "CR-01, same root cause. With the calendar entity disabled, a refresh that adds a matching programme fires 0 events (verifier repro). The seen-set is never updated and ended matches are never captured, so after re-enabling within the retention window, matches that ended and were dropped while it was disabled are gone"
    artifacts:
      - path: "custom_components/xmltv_calendar/calendar.py"
        issue: "_fire_new_match_events and the match_store.put in _async_refilter only run for an added entity"
    missing:
      - "Same fix as above. The event and retention must not depend on the calendar entity being enabled"
  - truth: "04-04 T4 + prohibition: no event fires after a filter or template edit; 04-06 T5: a filter edit drops retained programmes the new filter no longer matches (D-17)"
    status: partial
    reason: "WR-01, reproduced. When a coordinator data refresh lands while a CONFIG refilter waits on its executor job, the DATA run bumps _generation and the CONFIG run is discarded (calendar.py:281). The DATA run uses recheck=None and fire=True. Verifier repro: widen F1 from daserste.de to daserste.de+zdf.de, block the CONFIG filter job, refresh with one new daserste match. Events fired: ['zdf.de', 'zdf.de', 'daserste.de']. Only the daserste one is legitimate. By code inspection, the same interleaving skips the D-17 retained re-check (allowed is None, lines 272-288). IN-01 widens the window: every template-only edit also runs a full CONFIG refilter (line 402)"
    artifacts:
      - path: "custom_components/xmltv_calendar/calendar.py"
        issue: "Config semantics are lost when a DATA refilter supersedes a CONFIG refilter (lines 255-319, 417-418)"
    missing:
      - "Make config semantics sticky until a refilter completes (e.g. a _config_pending flag ORed into recheck and suppressing fire), as proposed in 04-REVIEW.md WR-01"
      - "Regression test that blocks the CONFIG executor job, pushes new coordinator data, and asserts no event for edit-only matches plus the retained re-check (verifier repro: scratchpad verify04/test_wr01.py)"
  - truth: "04-08 T1: every sensor name and attribute state has an English string, and HA serves a German string for each (CFG-04)"
    status: partial
    reason: "IN-05. entity.sensor.last_fetch.state_attributes.failure_reason has a name but no 'state' map in en.json/de.json, although its values are the closed FAILURE_REASONS vocabulary. The German UI shows raw keys such as unable_to_fetch. tests/test_translations.py:355-356 only requires trigger/outcome/cache states, so CI does not catch it. Roadmap SC4 (flow steps, errors, aborts) is unaffected"
    artifacts:
      - path: "custom_components/xmltv_calendar/translations/en.json"
        issue: "failure_reason has no state translations"
      - path: "custom_components/xmltv_calendar/translations/de.json"
        issue: "failure_reason has no state translations"
      - path: "tests/test_translations.py"
        issue: "ATTEMPT_VOCABULARIES requirement omits failure_reason"
    missing:
      - "Add state.<reason> for every FAILURE_REASONS value in both files and extend _vocabulary_requirements"
human_verification:
  - test: "04-01 (ha-dev): open a calendar's device page in English, then in German"
    expected: "'Next programme' / 'Nächste Sendung' with title, channel, start and end attributes; state is the next start in local time"
    why_human: "Frontend rendering of entity and attribute names is not asserted by any test"
  - test: "04-02 (ha-dev): import the blueprint with the README 'Import blueprint' button, set the lead time to minus 2 minutes in the duration field, pick a mobile-app notify entity, and wait for a match"
    expected: "The import dialog opens pre-filled, the negative duration is saved as a valid offset, and one notification arrives per match, including two that start at the same time"
    why_human: "The frontend duration selector, the my.home-assistant redirect and a real notify entity cannot run under pytest"
  - test: "04-04 (ha-dev): in Developer tools > Events, listen to xmltv_calendar_new_match, add a matching future programme to the test feed, run homeassistant.update_entity, then restart HA"
    expected: "Exactly one event with title, channel and local start; no repeat after the restart"
    why_human: "The real event bus and a real HA restart (final write of the delayed Store save) are not exercised end to end"
  - test: "04-05 (ha-dev): enable 'Last fetch' on a calendar device, run homeassistant.update_entity, switch the UI to German"
    expected: "State updates; trigger 'Manual'; 'Letzter Abruf' / 'Auslöser' / 'Ergebnis' are translated. Note: failure_reason values stay raw until the IN-05 gap is fixed"
    why_human: "Frontend rendering of translated attribute states"
  - test: "04-06 (ha-dev): let a match end, drop it from the test feed, refresh, restart HA, then download diagnostics"
    expected: "The match stays in the calendar view for the retention days and is listed under retained in diagnostics"
    why_human: "Real calendar view, real stop event and .storage on disk, diagnostics download"
  - test: "04-07 (ha-dev, German): edit a calendar, tick 'Erweiterte Optionen'"
    expected: "'Vergangene Treffer behalten (Tage)' with help text, box field 0..7, saved value prefilled on the next edit, no reload"
    why_human: "Frontend rendering of the translated number field"
  - test: "04-08 (ha-dev, German): walk through adding a URL and a file source, the options flow, adding and editing a calendar including the advanced step and preview, one validation error per form, both sensors"
    expected: "No raw translation key anywhere (except failure_reason values, the IN-05 gap)"
    why_human: "How the frontend renders served strings needs a person looking at the German UI"
  - test: "04-08: read README.md end to end (setup, regex examples, sensors, event payload, automation examples, limitations incl. 15-minute trigger window and overlapping events, releases)"
    expected: "Prose is accurate. The backstop truth 'a match added < 15 min before its trigger time may not trigger' matches what HA does, or is accepted as documented HA core behaviour"
    why_human: "Tests check presence of content, not accuracy; the 15-minute window is HA core behaviour (backstop truth 04-08 T9)"
  - test: "DST-03 release (user step, D-29): after UAT and gap closure, push main and tag v0.1.0"
    expected: "The Release workflow passes check-version, CI and Validate, then publishes GitHub release v0.1.0 (not prerelease, not draft); HACS offers XMLTV Calendar 0.1.0 for install/update (SC5, 04-08 T10 backstop)"
    why_human: "Only the user pushes and tags; the publish and HACS pickup can only be observed afterwards. Verified locally: no tag exists, 72 commits unpushed, tag check script accepts v0.1.0 and rejects v0.1.1, 0.1.0, v0.1.0;id, v0.1.0-rc1"
  - test: "04-05 T13 (backstop): accept or test 'a refresh cancelled part-way records no run; a manual refresh during a scheduled one is serialized by the coordinator lock'"
    expected: "Accepted as an HA guarantee, or a test asserting coordinator.last_attempt is unchanged after a cancelled refresh is added"
    why_human: "test_same_instant_runs_keep_the_latest covers the same-instant half. test_cancelled_refresh_records_no_failure asserts health only, not last_attempt, so the cancellation half has no direct evidence (insufficient_spec)"
  - test: "Confirm the non-authoritative judgment-tier prohibition verdicts (9 items, see table) and set dispositions for all 8 findings in 04-REVIEW-DISPOSITION.md (all are 'open')"
    expected: "8 of 9 prohibitions accepted as holding. The 04-04 'MUST NOT announce because of an edit' prohibition is recorded as violated (WR-01 gap). Each IN-0x is fixed or deferred with a reason"
    why_human: "Judgment-tier prohibitions and review dispositions need a human decision; the verifier's verdict is not authoritative"
---

# Phase 4: Automation Extras & Release Verification Report

**Phase Goal:** User can automate around matches beyond plain calendar triggers (next-match sensor, new-match event, recent past matches, ready-made blueprint) and install a documented, bilingual, tagged release via HACS.
**Mode:** mvp (ROADMAP). As in Phases 2 and 3, the goal is a capability statement, not a User Story (`user-story.validate` → false), and the Phase 4 plans carry no user story either. The goal text and the five roadmap success criteria serve as the contract. If MVP framing is wanted, run `/gsd-mvp-phase 4` to reword the goal; this does not affect the verdict.
**Verified:** 2026-10-21T11:05:00Z
**Status:** gaps_found
**Re-verification:** No, initial verification

## Verdict in one paragraph

The default path works and is well tested: 981 passed, 1 skipped (re-run by the verifier), ruff clean, 31/31 CONTEXT decisions honored. The four automation features, the blueprint, the release workflow, the translations and the README all exist, are substantive and wired. Two code-review findings falsify must-have truths, and the verifier reproduced both:

- **CR-01 (BLOCKER).** Disabling the calendar entity silently disables the next-match sensor, the new-match event and retention for that calendar. That is a normal HA user action, and keeping only the sensor for automations is exactly the "beyond calendar triggers" use case the goal names.
- **WR-01.** A filter edit that overlaps a data refresh fires spurious new-match events, which violates a planned prohibition.

A small CFG-04 gap (IN-05) also remains. The tagged release is a user step and is routed to human verification, not counted as a gap.

## User Flow Coverage

| Step | Expected | Evidence | Status |
|------|----------|----------|--------|
| Automate on the next match | Each calendar has a "Next programme" timestamp sensor that follows time, feed and edits | `sensor.py:183-256`, `window.py:408-411`, 15 tests in `test_sensor.py` pass | FAILED for a disabled calendar (CR-01), VERIFIED otherwise |
| Automate on new programmes | `xmltv_calendar_new_match` once per new match, silent on first refresh, restart, reload, edits | `calendar.py:299-344`, `match_store.py`, 12 tests in `test_new_match_event.py` | FAILED: disabled calendar (CR-01) and edit/refresh race (WR-01) |
| See recent past matches | Ended matches stay N (0..7) days after the feed drops them, also across restarts | `matches.py:189-234`, `calendar.py:283-308`, 13 tests in `test_retention.py` | FAILED for a disabled calendar (CR-01); race skips the D-17 re-check (WR-01) |
| Use a ready-made blueprint | Import, mode queued, one run per match incl. overlap | `blueprints/.../notify_before_programme.yaml`, `test_overlapping_programmes_notify_once_each` (2 notifications at 09:50Z) | VERIFIED (frontend import is a human item) |
| Bilingual | All flow strings EN and DE | `test_every_flow_key_is_translated`, `test_german_ui_is_served_for_every_required_key` | VERIFIED for flows; failure_reason attribute states missing (IN-05) |
| Documented | README covers setup, regex, automations, limitations | README sections at lines 21-356; `test_readme_documents_*` | VERIFIED (prose accuracy is a human item) |
| Install a tagged release via HACS | Tag v0.1.0 → release → HACS offers it | `release.yml`, tag-check script executed by verifier | HUMAN (user step D-29; no tag pushed) |

## Goal Achievement

### Roadmap Success Criteria (contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | Next-match timestamp sensor with title, channel, start, end; updated as matches pass or the feed changes | ✗ FAILED (partial) | Enabled calendar: `test_next_match_sensor_shows_next_start`, `test_sensor_moves_on_at_match_start`, `test_sensor_follows_new_feed_data`, `test_sensor_follows_filter_and_template_edits` pass. Disabled calendar: verifier repro gives state `unknown` with no attributes, although the F1 match at 10:00Z exists (CR-01) |
| SC2 | New-match event (not first refresh, not after restart); past N days retained across restarts | ✗ FAILED (partial) | Enabled: `test_new_programme_fires_one_event`, `test_restart_does_not_announce_again`, `test_double_reload_keeps_seen_set`, `test_dropped_match_stays_for_retention_days`, `test_capture_on_stop` pass. Disabled calendar: 0 events for a new matching programme (repro, CR-01) |
| SC3 | Blueprint "notify before a matching programme starts", `mode: queued`, one notification per match incl. overlapping | ✓ VERIFIED | `mode: queued`, `max: 20` (yaml:65-67); HA blueprint schema accepts it (`test_blueprint_passes_home_assistant_schema`); two same-start programmes → 2 notifications (`test_overlapping_programmes_notify_once_each`) |
| SC4 | Every config, subentry and options flow step, error and abort reason in German / English | ✓ VERIFIED | AST-derived required keys (`test_every_flow_key_is_translated`); HA serves German for each (`test_german_ui_is_served_for_every_required_key`); en/de key parity |
| SC5 | Tag push publishes a release matching manifest.json, HACS offers it; README documents setup, regex, automations, limitations | ? HUMAN | Workflow shape and executed tag check verified (see spot-checks); manifest 0.1.0; README complete. The publish and HACS pickup are a user step (D-29) |

### Plan Must-Have Truths

| Plan | Truths | Verified | Failed | Human / backstop | Notes |
|------|--------|----------|--------|------------------|-------|
| 04-01 next-match sensor | 10 | 8 | T1, T6 | – | T1 (state = earliest future match) and T6 (follows feed data and edits without reload) are false for a disabled calendar (CR-01). T2-T5 and T7-T10 pass with named tests (`test_no_future_match_is_unknown_but_available`, `test_next_match_attributes`, `test_match_texts_are_not_recorded`, `test_german_entity_ids`, `test_calendar_added_later_gets_a_sensor`, `test_airing_match_is_not_next`, `test_invalid_stored_pattern_gives_unknown`, `test_same_start_picks_feed_order`) |
| 04-02 blueprint | 7 | 7 | – | – | Legacy calendar trigger with `offset: !input lead_time`, default -10 min, `allow_negative: true`, filtered entity selector, notify skipped without targets (`test_default_action_without_notify_entity_does_nothing`), min_version 2026.3.0 and main-branch source_url |
| 04-03 release workflow | 5 | 5 | – | – | Tag regex plus `jq -r .version` comparison; `needs: [check-version, ci, validate]`; `--prerelease` only for `*-*`; `permissions: {}`, contents write only on release, SHA pins, `persist-credentials: false`, `ubuntu-24.04`; ci.yml/validate.yml have `workflow_call` and `tags-ignore: v*.*.*` |
| 04-04 new-match event | 7 | 5 | T1, T4 | – | T1 fails for a disabled calendar (CR-01). T4 ("no event after a filter or template edit") fails under the edit/refresh interleaving (WR-01 repro). T2, T3, T5-T7 pass (`test_new_programme_fires_one_event` exact payload keys, `test_started_match_is_not_announced`, `test_seen_set_is_persisted`, `test_burst_is_capped`, `test_seen_is_pruned_after_the_window`, `test_removed_calendar_and_source_clean_up`) |
| 04-05 last-fetch sensor | 13 | 12 | – | T13 | T13 is a backstop truth with only half its evidence (see human item). T4 `matches` reads 0 for a disabled calendar (CR-01 side effect, not counted separately) |
| 04-06 retention | 11 | 9 | T1, T5 | – | T1 fails for a disabled calendar (CR-01: no capture while disabled). T5 (D-17 re-check after a filter edit) is skipped when a data refilter supersedes the edit (WR-01, code inspection of the reproduced interleaving). Others pass (`test_future_match_removed_from_feed_disappears`, `test_three_day_retention_survives_parser_cutoff`, `test_timezone_change_drops_retained`, `test_no_uid_is_shown_twice`, `test_retained_cap`, `test_retention_zero_keeps_nothing`) |
| 04-07 retention field | 5 | 5 | – | – | `_retention_selector()` 0..7 step 1 BOX (`config_flow.py:459-461`); cleared → default 1 (`:516`); in-place apply (`test_retention_set_in_the_ui_applies_in_place`); prefill and has_advanced (`test_edit_prefills_retention_and_checks_advanced`) |
| 04-08 translations, README, release readiness | 10 | 7 | T1 | T9, T10 | T1 partial: failure_reason attribute states untranslated (IN-05). T2-T8 verified (`test_translations.py` AST walk; README checks and manual read of lines 148-336). T9 and T10 are backstop truths (HA 15-minute window, user-pushed release) |
| **Roadmap SCs** | 5 | 2 | SC1, SC2 | SC5 | |
| **Total** | **73** | **60** | **9** | **4** | Behavior-unverified: 0 |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/xmltv_calendar/sensor.py` | NextMatchSensor, LastFetchSensor | ✓ VERIFIED | 217 lines; added per subentry via `async_add_subentry_sensors`; `Platform.SENSOR` in PLATFORMS |
| `custom_components/xmltv_calendar/xmltv/window.py` | `next_after` | ✓ VERIFIED | bisect_right, equal starts keep input order |
| `custom_components/xmltv_calendar/calendar.py` | signal_matches, next_match, describe_match, EVENT_NEW_MATCH, merge | ✓ VERIFIED (wired), but owns all match state (CR-01) | Wired to sensor, match store and event bus |
| `custom_components/xmltv_calendar/xmltv/matches.py` | seen-set and retention pure logic | ✓ VERIFIED | Tolerant reads, 5,000 cap |
| `custom_components/xmltv_calendar/match_store.py` | Per-source Store | ✓ VERIFIED | Copy-on-write, flush on unload, fingerprint drop |
| `custom_components/xmltv_calendar/cache.py` | RefreshAttempt | ✓ VERIFIED | Persisted with meta and health |
| `custom_components/xmltv_calendar/coordinator.py` | signal_attempt, run recording | ✓ VERIFIED | `async_dispatcher_send(signal_attempt)` line 283 |
| `blueprints/automation/xmltv_calendar/notify_before_programme.yaml` | Blueprint | ✓ VERIFIED | `mode: queued` |
| `.github/workflows/release.yml` | Tag-checked release | ✓ VERIFIED | Executed check step locally |
| `tests/test_translations.py` | Code-derived completeness | ✓ VERIFIED (scope misses failure_reason, IN-05) | |
| `README.md` | Docs incl. `xmltv_calendar_new_match`, import button | ✓ VERIFIED | Does not mention the calendar-enabled coupling (CR-01) |

`gsd verify.artifacts`: 29/29 across 8 plans.

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| calendar.py | sensor.py | `async_dispatcher_send(signal_matches)` after refilter and template edit (lines 268, 317, 421) | WIRED |
| sensor.py | window.py | `calendar.next_match(now)` → `MatchIndex.next_after` | WIRED |
| sensor.py | HA event helper | `async_track_point_in_utc_time` at next start (line 256) | WIRED |
| __init__.py | sensor.py | `Platform.SENSOR`, `async_add_subentry_sensors` in the update listener | WIRED |
| calendar.py | match_store.py | `store.get/put` (lines 219, 226, 273, 283, 301). The tool pattern `match_store\.(get\|put)\(` misses the local alias, so verified manually | WIRED |
| calendar.py | event bus | `self.hass.bus.async_fire(\n EVENT_NEW_MATCH, ...)` (lines 337-344). Multi-line, so the tool pattern misses it; verified manually | WIRED |
| __init__.py | match_store.py | `MatchStore(...)`, `async_load(fingerprint=...)`, `async_flush` on unload, `async_remove` on remove | WIRED |
| coordinator.py | sensor.py / cache.py / diagnostics.py | `signal_attempt`, `async_save_attempt`, `last_attempt` | WIRED |
| calendar.py | matches.py | `capture_ended → prune_retained → merge_matches → MatchIndex` | WIRED |
| config_flow.py | settings.py | `CONF_RETENTION_DAYS = KEY_RETENTION_DAYS` | WIRED |
| subentry reconfigure | calendar.py | `__init__._async_entry_updated` → `entity.async_apply_subentry` (line 64). The tool rejected the descriptive `from:`; verified manually | WIRED |
| release.yml | ci.yml / manifest.json | `uses: ./.github/workflows/ci.yml`, `jq -r .version` | WIRED |
| test_translations.py | config_flow.py | AST walk | WIRED |
| README.md | blueprint | `redirect/blueprint_import` with URL-encoded blob URL (line 296) | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| NextMatchSensor | `_attr_native_value`, attributes | `runtime.calendars[sid]._index` ← `_async_refilter` ← `coordinator.data` | Yes while the calendar entity is added. An empty `MatchIndex(())` while it is disabled | ⚠️ DISCONNECTED when the calendar is disabled (CR-01), ✓ FLOWING otherwise |
| new-match event | payload | `new_matches(result.matches, record.seen)` in `_async_refilter` | Same dependency | Same |
| LastFetchSensor | run attributes | `coordinator.last_attempt` (Store-backed) | Yes | ✓ FLOWING |
| Calendar events | `_index` | feed matches + `match_store` retained | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite (run once) | `uv run pytest -q -m "not benchmark"` | 981 passed, 1 skipped (real-feed gate), 4 deselected | ✓ PASS |
| Lint / format | `uv run ruff check .` / `ruff format --check .` | All checks passed / 72 files formatted | ✓ PASS |
| Tag check script from release.yml, real manifest | `GITHUB_REF_NAME=<tag> bash -c "$step"` | v0.1.0 → 0; v0.1.1, 0.1.0, `v0.1.0;id`, v0.1.0-rc1 → 1 | ✓ PASS |
| CR-01 repro (verifier, scratch test) | disable `calendar.f1`, reload, refresh with a new F1 match | Sensor `unknown`, no attributes; 0 new-match events. Control with the calendar enabled: `2026-10-13T10:00:00+00:00` | ✗ FAIL |
| WR-01 repro (verifier, scratch test) | widen filter, block the CONFIG executor job, refresh with one new daserste match | Events `['zdf.de', 'zdf.de', 'daserste.de']`. Sequential control: `['daserste.de']` | ✗ FAIL |
| No tag created by the assistant | `git tag`; `git log origin/main..HEAD` | No tags; 72 unpushed commits | ✓ PASS |

The repro tests are at `/tmp/akentner/claude-1000/-home-akentner-Projects-homeassistant-xmltv-calendar-integration/6419e4f9-e130-469d-8839-c154e2ed0c99/scratchpad/verify04/test_cr01.py` and `.../verify04/test_wr01.py`. Run them from the repo root with `PYTHONPATH=. uv run pytest -c pyproject.toml --rootdir=. <file>`. They are session scratch files; copy them into `tests/` during gap closure.

### Probe Execution

No probes declared or present (`scripts/` has no `tests/probe-*.sh`). SKIPPED.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| AUT-03 | 04-01 | Next-match timestamp sensor per calendar | ✗ BLOCKED (partial) | Works for enabled calendars; CR-01 for disabled ones |
| AUT-05 | 04-02 | Blueprint, `mode: queued` | ✓ SATISFIED | Blueprint plus schema and e2e tests |
| AUT-06 | 04-05 | Diagnostic "Last fetch" sensor, disabled by default, no URL | ✓ SATISFIED | `test_last_fetch_is_diagnostic_and_disabled_by_default`, `test_no_secrets_in_last_fetch` |
| EVT-07 | 04-06, 04-07 | Past N days (≤7) stay visible after the feed drops them | ✗ BLOCKED (partial) | Works for enabled calendars; CR-01 (no capture while disabled), WR-01 (D-17 re-check skipped in the race) |
| EVT-08 | 04-04 | Event on new matching programme, not first refresh, not after restart | ✗ BLOCKED (partial) | CR-01 (no event while disabled); WR-01 (spurious events after an edit) |
| CFG-04 | 04-01, 04-05, 04-07, 04-08 | UI in English and German | ? NEEDS HUMAN, partial | Flows complete; failure_reason values untranslated (IN-05); German UI walkthrough pending |
| DST-03 | 04-03, 04-08 | Tagged releases match manifest.json | ? NEEDS HUMAN | Workflow verified; first publish is a user step |
| DST-04 | 04-08 | README: setup, regex examples, automation examples, limitations | ✓ SATISFIED | README sections plus `test_readme_documents_automation_and_limitations`. CR-01 coupling undocumented (part of the CR-01 fix) |

All 8 phase IDs appear in plan frontmatter, and REQUIREMENTS.md maps exactly these 8 to Phase 4. No orphans. REQUIREMENTS.md already marks all 8 `[x] Complete`. Given the gaps, AUT-03, EVT-07 and EVT-08 are not complete in the strict sense.

### Prohibitions (judgment tier, non-authoritative verifier verdicts)

| Plan | Prohibition | Verdict |
|------|-------------|---------|
| 04-01 | MUST NOT record match descriptions/sub-titles/episodes | Holds (`_unrecorded_attributes`, `test_match_texts_are_not_recorded`) |
| 04-02 | MUST NOT drop overlapping programmes / use mode single | Holds |
| 04-03 | MUST NOT publish a release whose tag differs from manifest | Holds (executed check) |
| 04-04 | MUST NOT announce because of restart, reload, edit or timezone change | **Violated** in the edit/refresh race (WR-01 repro) |
| 04-04 | MUST NOT fire more than 50 events per calendar and refresh | Holds (`split_announcements`, `test_burst_is_capped`) |
| 04-05 | MUST NOT expose URL, host, path or credentials | Holds (`test_no_secrets_in_last_fetch`, diagnostics checks) |
| 04-06 | MUST NOT keep showing a future/airing match the feed removed | Holds (`capture_ended` only stop ≤ now; `test_future_match_removed_from_feed_disappears`) |
| 04-07 | MUST NOT reload or download on a retention-only edit | Holds (`test_retention_edit_applies_in_place`) |
| 04-08 | MUST NOT push commits/tags or create the release from the assistant | Holds (no tags, commits unpushed) |

### Test Quality Audit

| Test File | Linked Req | Skipped | Circular | Assertion Level | Verdict |
|-----------|------------|---------|----------|-----------------|---------|
| tests/test_sensor.py | AUT-03 | 0 | No | Value/behavioral | OK, but no disabled-calendar case |
| tests/test_new_match_event.py | EVT-08 | 0 | No | Value (exact payload) / behavioral | OK, but no edit/refresh interleaving case |
| tests/test_retention.py | EVT-07 | 0 | No | Behavioral (time travel, reload, stop) | OK |
| tests/test_last_fetch_sensor.py | AUT-06 | 0 | No | Value | OK |
| tests/test_blueprint.py | AUT-05 | 0 | No | Behavioral (real automation from blueprint) | OK |
| tests/test_translations.py | CFG-04 | 0 | No | Value (key presence, served German) | Scope gap: failure_reason states |
| tests/test_repo_structure.py | DST-03/04 | conditional on bash/jq/shellcheck (all present locally; 43 passed) | No | Value / executed script | OK |

Disabled tests on requirements: 0. Circular patterns: 0. Insufficient assertions: 0 (one coverage gap per finding above).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (all phase files) | – | TBD/FIXME/XXX | – | None found |
| calendar.py | 395-402 | Comment says templates rebuild "without a refilter", but `refilter = True` whenever the spec compiles (IN-01) | ⚠️ Warning | Dead retention comparison; widens the WR-01 window to template-only edits |
| source.py / coordinator.py | 243-246 / 466-470 | `SourceTooLargeError` without status (IN-02) | ℹ️ Info | http_status None on a 200 oversize |
| source.py / cache.py | 235-238 / 184-187 | Status ≥ 600 stored but rejected on read (IN-03) | ℹ️ Info | Run record lost after restart for odd CDNs |
| __init__.py | 29-32 | Fingerprint ignores the HA time zone for `naive_timezone: local` (IN-04) | ℹ️ Info | Retained times shifted after an HA tz change |
| blueprint yaml | 77 | `title` bound to the rendered summary (IN-06) | ℹ️ Info | Inconsistent with event/sensor `title`; 04-02 T5 literally holds |

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts (31/31).

### Human Verification Required

Eleven items are listed in the frontmatter `human_verification`:

- The seven deferred ha-dev checks from 04-01, 04-02, 04-04, 04-05, 04-06, 04-07 and 04-08.
- The README accuracy read, together with the 15-minute-window backstop.
- The v0.1.0 tag push and HACS pickup (user step D-29).
- The 04-05 T13 backstop.
- The prohibition and review-disposition confirmation.

They do not change the status, because gaps_found takes precedence. Run them after gap closure, so the ha-dev walkthrough covers the fixed code.

### Gaps Summary

There are three concerns. The first is the only real blocker:

1. **Entity-owned match state (CR-01, BLOCKER).** Root cause of 6 failed truths (SC1, SC2, 04-01 T1/T6, 04-04 T1, 04-06 T1). The next-match sensor, the new-match event and retention all depend on `XmltvCalendarEntity` being added to hass. If the user disables the calendar entity, these features stop without any error, and the README text for `unknown` becomes wrong. Fix: an entity-independent per-subentry matcher that the calendar and sensors read from. The minimum alternative is a warning, README documentation and overrides for the affected truths, which is a deliberate scope decision for the user.
2. **Config-refilter superseded by a data refilter (WR-01).** 2 failed truths (04-04 T4 plus its prohibition, 04-06 T5). Spurious `xmltv_calendar_new_match` events and a skipped D-17 re-check when an edit overlaps a refresh. The window is narrow but deterministic, and IN-01 widens it. Fix: sticky config semantics plus a regression test.
3. **failure_reason state translations (IN-05).** 1 partial truth (04-08 T1). Trivial fix in both translation files and the translation test.

These are not deferred: Phase 4 is the last phase of the milestone. The release itself (SC5 / DST-03 publish) is not a gap. It waits on the user's push after UAT, per D-29.

---

_Verified: 2026-10-21T11:05:00Z_
_Verifier: Claude (gsd-verifier)_
