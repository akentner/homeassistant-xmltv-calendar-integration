---
status: resolved
trigger: "Kalender aktualisiert sich erst nach manuellem Reload"
created: 2026-10-21T00:00:00Z
updated: 2026-10-21T09:00:00Z
---

## Current Focus
<!-- OVERWRITE on each update - always reflects NOW -->

hypothesis: "R1 accepted by the user as the explanation: designed 24 h interval anchored to the last HA restart / entry reload (not a code defect)."
test: "tests/test_multiday_refresh.py (3 multi-day freezer guards) committed as regression guard"
expecting: n/a (session resolved)
next_action: none. User switches the AT source to schedule mode "daily at HH:MM" (after the provider's daily update) once current main is deployed.
bug_class: "not reproduced; expected behaviour (refresh-interval anchoring), no defect"
reasoning_checkpoint: null
tdd_checkpoint: "not entered: no confirmed defect, so no RED test exists (both builds pass the multi-day tests)"
knowledge_base: ".planning/debug/knowledge-base.md does not exist; MemPalace not consulted (not available in this session). No known-pattern candidate."

## Symptoms
<!-- Written during gathering, then immutable -->

expected: A calendar picks up new programmes from the feed on every scheduled source refresh (URL source, interval mode, 24 h), without user action.
actual: User let a calendar run for several days on HA host `haos-op3050-1`. New entries only appeared after a manual reload of the integration (config entry reload).
errors: None seen. No Repairs issue, nothing noticed in the HA log (user did not inspect logs in detail).
reproduction: Configure a URL source with refresh interval 24 h and a calendar; leave HA running for several days; observe that the calendar's events do not advance to newly published feed days until the entry is reloaded.
started: Observed on an OLDER deployed build (before Phase 3 completion; exact commit unknown, deploy method unknown). The Phase 3 fixes in commit 19e262d (WR-01/WR-04/WR-05, refresh path / backoff / early-fire tolerance) may or may not already address it. Determine whether current main still has the bug.

## Environment notes

- HA host reachable via SSH: `haos-op3050-1` (Tailscale). Use the `ha` wrapper (`ha core logs`) and SSH; never curl the API directly. Integration files live under `/config/custom_components/xmltv_calendar/` on the host; cache under `/config/.cache/xmltv_calendar/`; Store files under `/config/.storage/xmltv_calendar.*`.
- Read-only on the host unless the user approves changes (no restarts, no deploys, no edits without asking).
- Compare the deployed code on the host against git history to identify the deployed commit (e.g. diff file hashes against `git log` versions of `custom_components/xmltv_calendar/`).
- Relevant code: `custom_components/xmltv_calendar/coordinator.py` (`_schedule_refresh` override, `_next_refresh_at`, `refresh_base`, `EARLY_FIRE_TOLERANCE`, backoff), `calendar.py` (`_handle_coordinator_update` identity guard `coordinator.data is self._epg`, `_async_refilter`), `cache.py`, `__init__.py`. Coordinator uses `always_update=False`; unchanged sources return the identical `EpgData` object (03-03).
- Deferred Phase 3 review findings possibly related: WR-06, IN-09 in `.planning/phases/03-resilient-sources/03-REVIEW-DISPOSITION.md`.
- Phase 4 context `.planning/phases/04-automation-extras-release/04-CONTEXT.md` lists this bug as a blocker.

## Eliminated
<!-- APPEND only - prevents re-investigating after /clear -->

- hypothesis: "Current main: a 24 h URL source stops advancing the calendar after scheduled refreshes when the feed changes daily (plain path, no restart)"
  evidence: tests/test_multiday_refresh.py::test_calendar_advances_every_day_without_reload passes (4 consecutive daily refreshes, newest day present each time)
  timestamp: 2026-10-21T07:35:00Z

- hypothesis: "Deployed build 93ad979: same as above"
  evidence: same test (adapted to the old conftest) passes in a worktree of 93ad979, import path verified to be the old coordinator
  timestamp: 2026-10-21T07:40:00Z

- hypothesis: "Current main: daily restarts/reloads with a fresh disk cache derail the schedule (cache start sets next refresh to fetched_at + 24 h, later refreshes stop reaching the calendar)"
  evidence: test_calendar_advances_with_daily_reloads_in_between passes (5 days, reload 14 h after each slot, cache served at start, newest day present after every slot)
  timestamp: 2026-10-21T08:00:00Z

- hypothesis: "Current main: 304 / identity path (always_update=False + calendar identity guard) swallows the first changed feed after unchanged days"
  evidence: test_calendar_advances_after_unchanged_days passes (two 304s, then a changed feed reaches calendar.get_events)
  timestamp: 2026-10-21T08:00:00Z

- hypothesis: "Config: polling disabled on the entry (pref_disable_polling)"
  evidence: core.config_entries shows pref_disable_polling false for both sources
  timestamp: 2026-10-21T07:05:00Z

- hypothesis: "Environment: the provider serves a stale (ISR / stale-while-revalidate) copy to a once-a-day client, so every scheduled fetch gets yesterday's feed while a reload shortly after gets the fresh one"
  evidence: ETag/Last-Modified of both feeds change about every 30 min (06:34:25 -> 07:01:45 GMT for AT, DE 07:00:12 GMT), repeated GETs return the current version, no ISR cache headers; 304 only on matching If-None-Match
  timestamp: 2026-10-21T07:25:00Z

- hypothesis: "Old build: a scheduled refresh failed (no backoff in Phase 2 -> stale for another 24 h) during the observation"
  evidence: no "Error fetching/requesting xmltv_calendar_*" line in the core journal (2026-10-18 07:18 .. now); recorder history shows no gap that needs a failure to explain it. Cannot be excluded for 10-16 .. 10-18 07:18 (journal rotated), so kept as residual R2 rather than fully eliminated.
  timestamp: 2026-10-21T07:50:00Z

## Evidence
<!-- APPEND only - facts discovered during investigation -->

- timestamp: 2026-10-21T07:00:00Z
  checked: git blob hashes of all 22 files in /config/custom_components/xmltv_calendar/ on haos-op3050-1 vs every commit on main touching custom_components/xmltv_calendar
  found: 22/22 exact match with 93ad979 (chore: rename repository, 2026-10-16 01:25, end of Phase 2). /config/.storage/hacs.repositories records installed_commit e9d0f5e (docs-only child of 93ad979, same code). No cache.py / schedule.py / diagnostics.py deployed. Deployed coordinator = plain DataUpdateCoordinator with update_interval=timedelta(hours=refresh_hours), always_update=True, no disk cache, no conditional requests; calendar refilters on every coordinator update (no identity guard).
  implication: Observation was made on Phase-2 code. None of the Phase-3 schedule/cache/304/identity code ran on the host. Whether current main has the bug must be established separately (test).

- timestamp: 2026-10-21T07:05:00Z
  checked: core.config_entries on host (xmltv_calendar entries)
  found: two URL sources (free-epg.de DE and AT), options {refresh_hours: 24}, pref_disable_polling false. DE has 0 calendar subentries; AT has 2 (Formel 1 filter + "ORF/ServusTV alle", the latter added 2026-10-21 06:32Z). pycache of the integration written 2026-10-19 15:09 (first import of the deployed code at the core restart 15:06).
  implication: polling is not disabled (eliminates config cause "pref_disable_polling"). DE entry has no listener so it never polls (irrelevant: no calendars).

- timestamp: 2026-10-21T07:10:00Z
  checked: `ha core logs` (journal from 2026-10-18 07:18) and `ha supervisor logs` (from 2026-10-18 07:32)
  found: zero xmltv_calendar errors ("Error fetching xmltv_calendar_* data" never logged). Core restarts (supervisor "Restarting homeassistant"): 2026-10-19 15:06, 2026-10-19 20:22, 2026-10-20 18:23. Other "custom integration xmltv_calendar" loader warnings (10-18 20:23, 10-19 14:53, 10-20 11:15/11:20, 10-21 01:01-01:02) are HACS rescans, not restarts. Only one >24 h gap without restart is visible (10-18 07:32 -> 10-19 15:06), and it ran the PREVIOUS build (pyc proves the deployed build was first imported at 10-19 15:09).
  implication: The deployed build never ran 24 h without a restart in the visible log window, so the scheduled 24 h refresh of the deployed build was never exercised there. Host logs cannot confirm or refute the old-build symptom; no refresh ever failed loudly.

- timestamp: 2026-10-21T07:15:00Z
  checked: live AT feed (curl, headers + content)
  found: HTTP 200, ETag + Last-Modified (Last-Modified 2026-10-21 06:34:25 GMT, i.e. regenerated daily or more often), Cache-Control public max-age=3600, Content-Type application/gzip but body is plain XML (18 MB, 52k programmes). Programme days: rolling window 2026-10-20 .. 2026-10-25 plus stale 2025 junk days.
  implication: Feed changes every day; a correct 24 h refresh must add a new day each time. Server supports conditional requests (current main will send If-None-Match / If-Modified-Since).

- timestamp: 2026-10-21T07:20:00Z
  checked: filter.py / window.py / calendar.py (current main)
  found: no "now"-relative window in the filter; MatchIndex is rebuilt only in _async_refilter, which runs on async_added_to_hass and on coordinator updates whose data is a new EpgData object. CalendarEntity._async_write_ha_state pushes to websocket subscribers (calendar/event/subscribe) on every state write.
  implication: If the coordinator delivers a new EpgData object, the calendar refreshes; a stale calendar requires either no refresh, a refresh that returns the identical object, or a refilter that never writes.

- timestamp: 2026-10-21T07:25:00Z
  checked: free-epg.de conditional behaviour (curl): If-None-Match current ETag; If-Modified-Since alone; old ETag + current IMS; repeated GETs of DE and AT minutes apart
  found: 304 only for a matching If-None-Match; IMS ignored (200). ETag/Last-Modified change roughly every 30 min (AT: 06:34:25 -> 07:01:45 GMT, same gzip size 3026465 but new ETag; DE: 07:00:12 GMT). No x-nextjs-cache / stale-while-revalidate marker.
  implication: Server-side staleness (ISR serving a 24 h old copy to a once-a-day client) is not plausible; every 200 is at most ~30-60 min old. Conditional requests from current main are answered correctly (no false 304).

- timestamp: 2026-10-21T07:35:00Z
  checked: new investigation test tests/test_multiday_refresh.py::test_calendar_advances_every_day_without_reload (berlin tz, refresh_hours 24, RollingServer: feed rolls one day forward per day, per-version ETag, 304 for matching If-None-Match), run on current main AND on a worktree of the deployed commit 93ad979 (import path verified to be the worktree's coordinator)
  found: PASS on both. Every scheduled 24 h refresh fires (async_fire_time_changed), downloads the new version and calendar.get_events contains the newest day after each of 4 consecutive days.
  implication: Neither build reproduces "no update without reload" in the plain no-restart path. A defect, if any, needs an extra condition (restart/cache path, failure, listener churn, environment).

- timestamp: 2026-10-21T07:45:00Z
  checked: recorder history (history/history_during_period via ha-ws websocket client, read-only) of calendar.xmltv_formula1 and calendar.orf_servustv_alle since 2026-10-15; calendar.get_events on both (read-only)
  found: state rows (UTC) at 10-15 23:51, 10-16 00:02, 00:04, 18:01, 20:36, 10-17 08:44, 18:40, 21:39, 22:38 (all "off", no event), 10-19 13:09 (first F1 event "Formel 1" 2026-10-23 22:15 local), 10-19 18:25, 10-20 16:26, then 10-21 06:35:31 unavailable -> 06:35:43 (a config-entry reload; the only reload in the history). Rows without "unavailable" coincide with HA core restarts (10-19 13:09 / 18:25, 10-20 16:26 UTC match supervisor restarts). Calendar "ORF/ServusTV alle" created 10-21 06:32:28 UTC, reload 3 min later. Current events: F1 calendar Oct 23 (2), 24 (3), 25 (1); "alle" calendar Oct 20..25.
  implication: HA was restarted almost daily; the only >24 h run without restart was 10-17 22:38 -> 10-19 13:09 UTC. The F1 event (Oct 23 22:15 local) first appeared at the 10-19 13:09 restart. ServusTV horizon in today's feed is "today+3 full days + spill-over"; the provider adds the next day during the day, so at the would-be scheduled refresh (~10-18 22:38 UTC) Oct 23 was most likely not in the feed yet. The history is consistent with a working 24 h refresh anchored to the last restart; it does not show a missed refresh. Today's reload happened 14 h after the last restart, i.e. before the next 24 h refresh was due (10-21 ~16:26 UTC).

- timestamp: 2026-10-21T09:00:00Z
  checked: user decision at the decision checkpoint (options A close as expected behaviour / B observation run on host / C product change)
  found: user chose A. Close as expected behaviour (R1); user will switch the AT source to "daily at HH:MM" after deploying current main; Phase 4 blocker lifted; keep and commit tests/test_multiday_refresh.py as regression guard.
  implication: Session resolved without a code fix. R2/R3 stay as documented residuals; no host experiment.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: "No code defect. R1 (expected behaviour): interval mode counts the 24 h refresh interval from the last HA restart / config-entry reload, so calendar data can lag newly published feed days by up to 24 h. HA was restarted almost daily and each restart (and the single reload on 2026-10-21 06:35 UTC, 14 h after the last restart, before the next refresh was due ~16:26 UTC) fetched the feed immediately, which reads as 'only a reload updates'. The observation was made on the Phase-2 build 93ad979; no refresh defect reproduces there or on current main 47ba168. Residuals (not excluded, judged unlikely): R2 an old-build refresh failure before 2026-10-18 07:18 (journal rotated; Phase 2 had no backoff), R3 a production-only timer issue (unobservable without debug logging)."
fix: "No code fix (not applied by design: expected behaviour). Recommendation: switch the URL source to schedule mode 'daily at HH:MM' (Phase 3) at a time after the provider's daily update, e.g. 16:00. Note for deploying current main: a reload with a fresh disk cache no longer re-downloads (by design D-08/D-09, tests/test_cache.py::test_reload_uses_fresh_cache); use homeassistant.update_entity on any calendar of the source to refresh now (tests/test_refresh.py::test_update_entity_refreshes_now_with_validators)."
verification: "full suite 824 passed, 1 skipped; tests/test_multiday_refresh.py 3 passed, ruff check + format clean. Multi-day guard also passes against a worktree of 93ad979."
oracle_type: "specified (calendar.get_events must contain the newest feed day after every scheduled refresh)"
guardrail_verdict: "n/a (no fix applied)"
files_changed: ["tests/test_multiday_refresh.py (new, regression guard: daily refresh without reload, daily reloads in between, changed feed after 304 days)"]
prevention: "why not caught: none (no multi-day refresh test existed for this class); guard: tests/test_multiday_refresh.py"
