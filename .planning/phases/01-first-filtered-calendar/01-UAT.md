---
status: partial
phase: 01-first-filtered-calendar
source: [01-VERIFICATION.md]
started: 2026-10-14T14:34:31Z
updated: 2026-10-15T08:55:21.732Z
---

## Current Test

[testing complete]

## Tests

### 1. ha-dev walkthrough steps 1-4 on http://localhost:18123 (not :8123): add file source /media/xmltv/small-gzip.xml (gzip under .xml), add a calendar with include pattern (e.g. Tatort), try include '(' and file path /config/secrets.yaml, re-add the same file
expected: Name pre-filled 'small-gzip.xml', source loads; menu/file-step texts and errors read correctly (01-07 D7); multiline channel regex/include/exclude fields render with examples (01-08 D6); Calendar panel shows only matches as '<channel>: <title>' with channel as location; inline invalid_regex with pattern and error; 'path not allowed'; 'already configured'
result: pass

### 2. ha-dev walkthrough step 5: add /media/xmltv/large.xml (60 MB, 120 channels) and one reachable XMLTV URL source; open Add calendar
expected: UI stays responsive while loading; channel picker searches/selects quickly; channel regex works as fallback; URL source loads
result: pass

### 3. ha-dev walkthrough step 6: automation with Calendar trigger (event start, offset -0:05:00) on a calendar whose next match starts within ~20 minutes (large feed)
expected: Automation trace shows it fired five minutes before the programme start
result: skipped

### 4. ha-dev walkthrough step 7: podman logs ha-dev after all steps (redeploy first so ha-dev runs the 01-11 code)
expected: No 'Detected blocking call' and no xmltv_calendar error/traceback
result: skipped

### 5. ha-dev walkthrough step 8: delete-and-re-add a calendar (no Reconfigure until Phase 2 FLT-11); acknowledge the note that an invalid stored pattern only surfaces in the HA log
expected: No Reconfigure action; entity and device disappear on delete; re-add under the same name keeps the entity_id and shows the new matches; user records whether the workflow is acceptable until Phase 2
result: pass

### 6. HACS on ha-host: Custom repositories -> add https://github.com/akentner/homeassistant-xmltv-integration as type Integration; then push the 01-11 commits
expected: HACS accepts it without validation error and lists 'XMLTV Calendar' with its brand icon; after the push, CI (Ruff, Unit tests, Benchmark) and Validate (hassfest, HACS) run green for a push event on the 01-11 code
result: pass

### 7. Backstop truth (01-07): two sources with equal refresh intervals refresh independently
expected: Refreshing one source never triggers a download or parse of another
result: skipped

### 8. Judgment-tier prohibitions (non-authoritative LLM verdict: all hold) — confirm: (a) no network endpoint other than the configured source URL is contacted (01-01); (b) no programme- or use-case-specific matching logic (01-03); (c) no third-party EPG data committed (01-09)
expected: (a) only source.py session.get(url) for the user URL; (b) 'formel'/'Tatort' appear only as help-text examples in translations/en.json; (c) tracked fixtures basic.xml, edge_cases.xml, latin1.xml are synthetic; real_de_excerpt.xml not committed
result: pass

### 9. Decision on review warnings that touch SC3/SC4 wording: WR-07 (a well-formed programme with an absurd but in-window stop, e.g. year 2200, becomes the calendar's current event until that stop), IN-14 (get_events raises OverflowError for a caller-supplied query start near year 0001) and WR-08 (skipped_malformed is never logged)
expected: User accepts them as non-blocking for Phase 1 and routes them (WR-07 -> duration cap in parser or Phase 2 FLT-08 context; WR-08 -> Phase 3 SRC-12 diagnostics; IN-14 -> clamp in window.py), or asks for a small gap-closure plan before closing Phase 1
result: pass

## Summary

total: 9
passed: 6
issues: 0
pending: 0
skipped: 3
blocked: 0

## Gaps
