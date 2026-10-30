---
status: complete
phase: 04-automation-extras-release
source: [04-VERIFICATION.md]
started: 2026-10-23T14:30:01Z
updated: 2026-10-23T14:43:53.099Z
---

## Current Test

[testing complete]

## Tests

### 1. 04-01 (ha-dev): open a calendar's device page in English, then in German; then disable the calendar entity, reload the entry, and look at the next-programme sensor
expected: 'Next programme' / 'Nächste Sendung' with title, channel, start and end attributes; the state is the next start in local time, also while the calendar entity is disabled
result: pass

### 2. 04-02 (ha-dev): import the blueprint with the README 'Import blueprint' button, set the lead time to minus 2 minutes in the duration field, pick a mobile-app notify entity, and wait for a match
expected: The import dialog opens pre-filled, the negative duration is saved as a valid offset, and one notification arrives per match, including two that start at the same time
result: pass

### 3. 04-04 (ha-dev): in Developer tools > Events, listen to xmltv_calendar_new_match, add a matching future programme to the test feed, run homeassistant.update_entity, then restart HA; repeat once with the calendar entity disabled
expected: Exactly one event with title, channel and local start, also with the calendar disabled; no repeat after the restart
result: pass

### 4. 04-05 (ha-dev): enable 'Last fetch' on a calendar device, run homeassistant.update_entity, switch the UI to German; provoke one failure (unreachable URL)
expected: State updates; trigger 'Manual'; 'Letzter Abruf' / 'Auslöser' / 'Ergebnis' / 'Fehlergrund' and the failure reason text ('Abruf fehlgeschlagen') are translated
result: pass

### 5. 04-06 (ha-dev): let a match end, drop it from the test feed, refresh, restart HA, then download diagnostics
expected: The match stays in the calendar view for the retention days and is listed under retained in diagnostics
result: pass

### 6. 04-07 (ha-dev, German): edit a calendar, tick 'Erweiterte Optionen'
expected: 'Vergangene Treffer behalten (Tage)' with help text, box field 0..7, saved value prefilled on the next edit, no reload
result: pass

### 7. 04-08 (ha-dev, German): walk through adding a URL and a file source, the options flow, adding and editing a calendar including the advanced step and preview, one validation error per form, both sensors
expected: No raw translation key anywhere, including failure_reason values
result: pass

### 8. 04-08: read README.md end to end (setup, regex examples, sensors, event payload, automation examples, limitations incl. 15-minute trigger window and overlapping events, releases)
expected: Prose is accurate. The backstop truth 'a match added < 15 min before its trigger time may not trigger' matches what HA does, or is accepted as documented HA core behaviour. Optionally add a sentence on the review IN-04 edge (a refresh that coincides with a filter edit is announced silently)
result: skipped
reason: "Deferred follow-up: skipped by user; phase accepted as passed manually"

### 9. DST-03 / SC5: confirm that HACS offers XMLTV Calendar 0.1.0-rc1 (prereleases enabled) and later push the final v0.1.0 (manifest.json to 0.1.0 first). Note that the 22 unpushed commits, including the whole gap-closure work (matcher.py), are NOT in the published v0.1.0-rc1
expected: The Release workflow passes check-version, CI and Validate and publishes the release; HACS lists the version. rc1 is published as a Pre-release (observed, run 39845820757 success). A final v0.1.0 containing the fixes is still to be tagged by the user
result: skipped
reason: "Deferred follow-up: skipped by user; phase accepted as passed manually"

### 10. 04-05 T13 (backstop): accept or test 'a refresh cancelled part-way records no run; a manual refresh during a scheduled one is serialized by the coordinator lock'
expected: Accepted as an HA guarantee, or a test asserting coordinator.last_attempt is unchanged after a cancelled refresh is added
result: skipped
reason: "Deferred follow-up: skipped by user; phase accepted as passed manually"

### 11. Confirm the non-authoritative judgment-tier prohibition verdicts (11 items, see table) and set dispositions for the findings. 04-REVIEW-DISPOSITION.md still lists the 8 findings of the FIRST review, all 'open'; the fresh 04-REVIEW.md has different IDs (WR-01..03, IN-01..05)
expected: All 11 prohibitions accepted as holding. Old CR-01, WR-01, IN-01, IN-05 recorded as fixed. IN-04 (time zone fingerprint), IN-02, IN-03, IN-06 and the new review warnings fixed or deferred with a reason
result: pass

## Summary

total: 11
passed: 8
issues: 0
pending: 0
skipped: 3
blocked: 0

## Deferred Follow-Ups

- test: 8
  idea: "Read README.md end to end"
  deferred_at: 2026-10-23
- test: 9
  idea: "Tag and push final v0.1.0 (includes gap-closure commits)"
  deferred_at: 2026-10-23
- test: 10
  idea: "Accept or test: cancelled refresh records no run"
  deferred_at: 2026-10-23

## Gaps
