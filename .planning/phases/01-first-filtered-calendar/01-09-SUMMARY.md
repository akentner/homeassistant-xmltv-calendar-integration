---
phase: 01-first-filtered-calendar
plan: 09
subsystem: testing
tags: [home-assistant, podman, ha-dev, manual-check, xmltv, real-feed, uat]
requires:
  - phase: 01-06
    provides: "scripts/generate_benchmark_feed.py (deterministic 1 MB / 60 MB feeds, gzip byte-reproducible)"
  - phase: 01-07
    provides: "URL and file source steps; checks deferred to ha-dev (form texts, /media allowed)"
  - phase: 01-08
    provides: "Add calendar form with pattern fields; rendering checks deferred to ha-dev"
provides:
  - "ha-dev (HA 2026.10.1, TZ Europe/Berlin) runs xmltv_calendar from the working tree via a read-only mount, on http://localhost:18123"
  - "Read-only /media/xmltv in ha-dev with four feeds dated 2026-10-14 (small.xml, small-gzip.xml, large.xml, large.xml.gz)"
  - "tests/xmltv/test_real_feed.py: real-feed parser acceptance suite; skips until the D-15 excerpt exists, XMLTV_REAL_FEED runs it on any local feed"
  - "UAT human-check list for the ha-dev walkthrough (sources, calendars, picker, calendar trigger, blocking calls, delete/re-add)"
affects: [01-10, phase-01-uat, phase-02-reconfigure, phase-03-real-sources]
actuals:
  tokens: 1500   # chars/4 over the realized diff: test_real_feed.py (2,191 chars) + compose.yml lines outside the repo (~250 chars); excludes this SUMMARY
  tasks: 3
  commits: 1
plan_head_before: d162b85f5cbc50139489bbdc70b41700e00ba626
plan_head_after: 2af953f435cea52051be8d6aabe2d871eae86a15
tech-stack:
  added: []
  patterns:
    - "Real-data acceptance tests skip at module level when their fixture is absent; an env var (XMLTV_REAL_FEED) points them at a local feed without committing it"
key-files:
  created:
    - tests/xmltv/test_real_feed.py
  modified: []
key-decisions:
  - "01-09 Task 2: none. No real German feed excerpt is committed in Phase 1 (licensing risk in a public repo); D-15's real-feed excerpt is deferred in STATE.md and scripts/trim_feed.py was not written"
  - "01-09: ha-dev is published on host port 18123 through a transient compose override, because ha-a (host network, mqtt-actions test instance) holds 8123; compose.yml keeps 8123:8123"
  - "01-09: test_real_feed.py carries the full behaviour checks behind the skip guard, so adding the excerpt later activates them with no code change"
patterns-established:
  - "Manual-check environment: generated feeds live in ~/Projects/dev/media/xmltv (outside the repo), mounted read-only at /media/xmltv"
requirements-completed: [SRC-01, SRC-02, SRC-09, FLT-02, AUT-01, CFG-01]
coverage:
  - id: D1
    description: "ha-dev runs the working-tree integration through a read-only mount and has a read-only /media/xmltv with four generated feeds dated today; HA serves on 18123"
    requirement: "SRC-02"
    verification:
      - kind: other
        ref: "podman exec ha-dev test -f /config/custom_components/xmltv_calendar/manifest.json"
        status: pass
      - kind: other
        ref: "podman exec ha-dev test -f /media/xmltv/large.xml"
        status: pass
      - kind: other
        ref: "curl -sf -o /dev/null http://localhost:18123/manifest.json"
        status: pass
      - kind: other
        ref: "podman inspect ha-dev (xmltv_calendar rw=false, /media/xmltv rw=false)"
        status: pass
    human_judgment: false
  - id: D2
    description: "ha-dev starts with no xmltv_calendar error or traceback and no 'Detected blocking call' naming xmltv_calendar; the integration imports and parses all four feeds inside the HA 2026.10.1 runtime"
    requirement: "SRC-09"
    verification:
      - kind: other
        ref: "podman logs ha-dev | grep -E 'xmltv_calendar.*(ERROR|Traceback)|Detected blocking call.*xmltv_calendar' (no lines)"
        status: pass
      - kind: other
        ref: "podman exec -w /config ha-dev python3 -c 'parse /media/xmltv/*' (1,332 / 80,773 / 80,773 programmes, 0 malformed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Real-feed parser acceptance suite: parses, malformed share at most 1%, aware start/stop with stop >= start, every programme channel known and named, anchored title include matches; skips while the D-15 excerpt is absent"
    verification:
      - kind: unit
        ref: "uv run pytest tests/xmltv/test_real_feed.py -q -rs (1 skipped: excerpt deferred)"
        status: pass
      - kind: unit
        ref: "XMLTV_REAL_FEED=tests/fixtures/basic.xml | small-gzip.xml | large.xml.gz uv run pytest tests/xmltv/test_real_feed.py (5 passed each)"
        status: pass
    human_judgment: false
  - id: D4
    description: "In the real HA UI: file source from /media/xmltv (gzip under .xml name), URL source, calendar with include pattern showing only matches titled '<channel>: <title>', inline invalid_regex error, path_not_allowed for /config/secrets.yaml, already_configured on duplicate; form texts and multiline fields render (01-07 D7, 01-08 D6)"
    requirement: "CFG-01"
    verification: []
    human_judgment: true
    rationale: "No frontend in the test harness; UI rendering and the real allowlist behaviour need a human in ha-dev"
  - id: D5
    description: "Channel picker stays usable (search and select) with the 120-channel 60 MB feed; channel regex works as the fallback (RESEARCH A4, D-02)"
    requirement: "FLT-02"
    verification: []
    human_judgment: true
    rationale: "Picker usability is a UX judgment in the real frontend"
  - id: D6
    description: "UI stays responsive while the 60 MB file source loads, and no 'Detected blocking call' for xmltv_calendar appears during any walkthrough step"
    requirement: "SRC-09"
    verification: []
    human_judgment: true
    rationale: "Startup is clean (D2), but no source is configured yet; the load path in the running HA is exercised only by the walkthrough"
  - id: D7
    description: "A calendar-trigger automation (event start, offset -0:05:00) fires five minutes before a matching programme"
    requirement: "AUT-01"
    verification: []
    human_judgment: true
    rationale: "Real automation firing in a running HA over wall-clock time; pytest covers it with freezer only"
  - id: D8
    description: "Delete-and-re-add workflow for changing a calendar until Phase 2 reconfigure: no Reconfigure action, entity and device disappear on delete, re-add keeps the entity_id and shows new matches"
    requirement: "SRC-01"
    verification: []
    human_judgment: true
    rationale: "User must judge whether the workflow is acceptable until FLT-11 lands"
duration: 5min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 09: Real-World Check on ha-dev Summary

**ha-dev now runs HA 2026.10.1 with xmltv_calendar mounted read-only from the working tree. Four feeds dated today sit read-only under /media/xmltv, startup logs are clean, and the integration parses all four feeds inside the container runtime (60 MB plain in 2.8 s). By the user's decision there is no real German excerpt (D-15 deferred). A skip-guarded real-feed acceptance suite is ready for one, and the UI walkthrough is queued for UAT.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-10-14T00:14:23Z
- **Completed:** 2026-10-14T00:19:31Z
- **Tasks:** 3 (Task 1 outside the repo, Task 2 resolved before dispatch, Task 3 committed)
- **Files modified:** 1 in the repo; `~/Projects/dev/compose.yml` and `~/Projects/dev/media/xmltv/` outside it

## Accomplishments

- **ha-dev deployment (D-16):**
  - compose.yml has the two read-only mounts.
  - The image was pulled at `stable`, which is now 2026.10.1, the same HA version the tests pin.
  - The container is recreated with only the `homeassistant` service touched.
  - HA answered on `/manifest.json` about 10 s after start.
- **Feeds in `~/Projects/dev/media/xmltv/` (mounted at `/media/xmltv`, all generated with `--start-date 2026-10-14`):**

  | File | Size | Programmes | Covers |
  |------|------|-----------|--------|
  | `small.xml` | 1.0 MB | 1,332 | 00:00–12:01 today |
  | `small-gzip.xml` | 176 KB, gzip content under a `.xml` name | 1,332 | 00:00–12:01 today |
  | `large.xml` | 60 MB | 80,773 | through 2026-11-08 |
  | `large.xml.gz` | 10.7 MB | 80,773 | through 2026-11-08 |

  All four have 120 channels.
- **Container smoke test:** the HA loader discovered `xmltv_calendar` (the custom-integration warning appears). Parsing each feed inside the HA runtime:
  - `small-gzip.xml`: 0.09 s
  - `large.xml`: 2.80 s
  - `large.xml.gz`: 3.07 s
  - every feed: 0 malformed, 0 duplicates
- **Log check:** `podman logs ha-dev` shows no xmltv_calendar error, traceback or blocking-call warning. Across the whole log there are 0 "Detected blocking call" lines. The only startup errors are pre-existing ones from chargefinder and aiodhcpwatcher.
- **`tests/xmltv/test_real_feed.py`:** five behaviour checks behind a module-level skip.
  - It skips while `tests/fixtures/real_de_excerpt.xml` is absent.
  - `XMLTV_REAL_FEED=<path>` runs the checks on any local feed. Each of `basic.xml`, `small-gzip.xml` and `large.xml.gz` gives 5 passed.
  - Pointed at `edge_cases.xml`, which contains deliberately malformed programmes, it fails the malformed-share check. So the suite does catch a bad feed.

### Compose diff (outside the repository; backup at `~/Projects/dev/compose.yml.bak`)

```diff
--- /home/akentner/Projects/dev/compose.yml.bak
+++ /home/akentner/Projects/dev/compose.yml
@@ -10,6 +10,9 @@
       - ../homeassistant-kroki-integration/custom_components/kroki:/config/custom_components/kroki:ro
       - ../phone-logger-integration/custom_components/phone_logger:/config/custom_components/phone_logger:ro
       - ../homeassistant-chargefinder-integration/custom_components/chargefinder:/config/custom_components/chargefinder:ro
+      - ../homeassistant-xmltv-integration/custom_components/xmltv_calendar:/config/custom_components/xmltv_calendar:ro
+      # Local XMLTV feeds for file-source tests (generated, not version-controlled)
+      - ./media/xmltv:/media/xmltv:ro
     environment:
       - TZ=Europe/Berlin
     ports:
```

The container was started with:

```
podman compose -f compose.yml -f <scratchpad>/ha-dev-port.override.yml up -d --no-deps homeassistant
```

The override file contains only `services.homeassistant.ports: !override ["18123:8123"]` (see Deviations 1).

## Task Commits

1. **Task 1: Tracer, ha-dev runs the integration with today's feeds.** No repository commit, as the plan specifies.
   - Tracer feedback gate: the run is interactive, `human_verify_mode` is `end-of-phase`, and the verify step is automated-only. Re-running verify passed: mount, media and HTTP checks all OK, logs clean. Execution then expanded to the next tasks.
2. **Task 2: Choose the real German feed (D-15).** Resolved by the user before dispatch: **none**. No commit.
3. **Task 3: Real-feed acceptance suite, UAT handover.**
   - `2af953f` test(01-09): real-feed parser acceptance suite, skipped until the D-15 excerpt exists

## TDD Gate Compliance

Task 3 is `tdd="true"`, but the user chose "none", which means no production code: no `scripts/trim_feed.py` and no excerpt. The task is therefore test-only:

- **RED:** not applicable. The suite is an acceptance and characterization check against the existing 01-02/01-05 parser and the 01-03 filter. With no fixture it skips by design, and nothing is implemented in this plan for it to fail against.
- **GREEN:** none, because there is no production change.
- **Evidence that the suite bites:** 5 passed on three valid feeds. On `tests/fixtures/edge_cases.xml` it gave 1 failed and 4 passed: `test_malformed_share_is_at_most_one_percent` fired on the fixture's deliberately malformed programmes.

Once D-15 is resumed, `trim_feed.py` should get a proper RED → GREEN cycle.

## Files Created/Modified

- `tests/xmltv/test_real_feed.py`: real-feed acceptance suite (module skip guard, `XMLTV_REAL_FEED` override, 5 checks).
- Outside the repo:
  - `~/Projects/dev/compose.yml` (two volume lines plus a comment; backup at `compose.yml.bak`)
  - `~/Projects/dev/media/xmltv/` (four generated feeds)

## Decisions Made

- **Task 2: none.** The user decided before dispatch that no real German feed excerpt is committed in Phase 1, to avoid licensing risk in the soon-to-be-public repository.
  - D-15's real-feed excerpt is recorded as a Deferred Item in STATE.md.
  - `scripts/trim_feed.py` and `tests/fixtures/real_de_excerpt.xml` were therefore not created.
  - Real-world parsing is checked only by hand in ha-dev.
  - Prohibition T-01-25 holds: no third-party EPG data was committed.
- ha-dev is published on host port **18123**. `ha-a`, a host-network HA 2026.9.4 test instance for mqtt-actions, holds 8123. compose.yml itself still maps 8123.
- `test_real_feed.py` holds the full behaviour checks rather than a bare skip. Adding an excerpt later activates them with no code change, and the env override lets the user check their own feed locally.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Host port 8123 already in use**
- **Found during:** Task 1
- **Issue:** `ha-a` (network mode host, from `~/ha-test/a`, mqtt-actions testing) listens on 0.0.0.0:8123, so `8123:8123` for ha-dev cannot bind. The plan's verify command `curl localhost:8123/manifest.json` would also have passed against ha-a and verified nothing. The `mqtt` dependency (`ha-dev-mqtt`, 1883) would likewise clash with `mosq`, which holds 1883 on the host.
- **Fix:**
  - Started ha-dev with a transient override file in the session scratchpad (`ports: !override ["18123:8123"]`) and `--no-deps`.
  - No other container was stopped or recreated. compose.yml's port mapping is unchanged.
  - The HTTP verify ran against `http://localhost:18123`.
- **Consequence:** a later plain `podman compose up -d homeassistant` (without the override) fails while ha-a runs. The running container keeps its 18123 mapping across restarts, because it has `restart: unless-stopped`.
- **Files modified:** none in the repo.

**2. [Rule 3 - Blocking] `stable` image not present locally**
- **Found during:** Task 1
- **Fix:** `compose up` pulled `ghcr.io/home-assistant/home-assistant:stable`, which is 2026.10.1, the same version the tests pin. No package install was involved.

**3. [Scope - test content] Full checks behind the skip guard**
- **Found during:** Task 3
- **Issue:** For "none", the plan says "test_real_feed.py with the skip guard only".
- **Fix:** Wrote the plan's `<behavior>` checks behind the module-level skip, plus the `XMLTV_REAL_FEED` override. The default run is still exactly one skip.
- **Committed in:** 2af953f

**4. [Verification addition] Smoke test inside the container runtime**
- **Found during:** Task 1
- **Fix:** Imported the integration and parsed all four feeds with the container's Python and HA environment, so the clean log is not only the result of an unconfigured integration. Read-only, no state change.

**5. [Process] Commit on `main`**
- `git.base-branch --is-protected main` reports `true`. The orchestrator stated that commits on main are expected for this run (`branching_strategy: none`), and 01-01 to 01-08 did the same.

---

**Total deviations:** 5 (2 blocking environment fixes, 1 test-scope widening, 1 verification addition, 1 process note)
**Impact on plan:** No interface or production change. The walkthrough URL becomes http://localhost:18123.

## Known Stubs

- `tests/xmltv/test_real_feed.py:23`: the module skips by design while `tests/fixtures/real_de_excerpt.xml` is absent (D-15 deferred by the user's Task 2 decision). It is recorded in `.planning/WINDOWS.md` as a skipped test. It resolves when an approved excerpt is committed.

## Issues Encountered

- Pre-existing, unrelated errors in the ha-dev log, out of scope:
  - chargefinder's `ConfigEntryNotReady` ("Failed to decrypt station data")
  - aiodhcpwatcher "Operation not permitted" (rootless container)
- The small feeds cover only 2026-10-14 00:00–12:01. If UAT runs later, the verifier should regenerate them with `--start-date $(date +%F)`; the container needs no restart, because the mount is live. The large feeds cover through 2026-11-08.
- RESEARCH A2: parse time on ha-host is still unmeasured. On the dev laptop container, the 60 MB plain feed parsed in 2.8 s in a worker thread.

## User Setup Required

None. ha-dev is running. For the walkthrough, the user needs only the ha-dev login.

## Human Checks for End-of-Phase UAT

<human-check>
On http://localhost:18123 (ha-dev, HA 2026.10.1). **Not :8123, which is the unrelated ha-a instance.** Verify and note the result of each step:

1. Settings > Devices & services > Add integration > "XMLTV Calendar" > "Local file" > `/media/xmltv/small-gzip.xml`.
   - The Name step is pre-filled with "small-gzip.xml" and the source loads.
   - The menu, file step texts and error messages read correctly (01-07 D7).
   - `/media` is accepted, so it is allowed by default.
2. On that source choose "Add calendar". Pick no channels, and use an include pattern built from one word in the generator's title list, e.g. `Tatort` or `Formel`.
   - The multiline channel regex, include and exclude fields render with their examples (01-08 D6).
   - The Calendar panel shows only matching programmes for today, titled "<channel>: <title>", with the channel as location.
   - The small feed covers today 00:00–12:01 only.
3. Try include `(` and confirm an inline error that shows the pattern and the regex error (invalid_regex, 01-08 D6). Try adding `/config/secrets.yaml` as a file source and confirm "path not allowed".
4. Add `/media/xmltv/small-gzip.xml` again and confirm "already configured".
5. Add a file source `/media/xmltv/large.xml` and check:
   - The UI stays responsive while it loads.
   - In "Add calendar", the channel picker (120 channels) searches and selects quickly.
   - The channel regex field works as the fallback (RESEARCH A4).
   - Also add one URL source (any reachable XMLTV URL) and confirm it loads.
   - (No real feed: Task 2 chose "none".)
6. Create an automation with a Calendar trigger (event: start, offset -0:05:00) on a calendar whose next match starts within about 20 minutes. Use the large feed, which covers through 2026-11-08. Its trace shows it fired five minutes before the start.
7. `podman logs ha-dev` shows no "Detected blocking call" for xmltv_calendar during any of the steps above.
8. Phase 1 has no way to edit a calendar; reconfigure (FLT-11) comes in Phase 2. Changing a calendar's channels or patterns means deleting it and adding it again. Check that workflow on the calendar from step 2:
   - Confirm the calendar subentry offers no "Reconfigure" action.
   - Delete it, and confirm its calendar entity and device disappear.
   - Add it again under the same name with a different include pattern.
   - Confirm the re-added calendar gets the same entity_id and shows the new matches, and that automations referencing it keep working.
   - Note in UAT whether this workflow is acceptable until Phase 2.

Known limitation, not testable through the UI: patterns are validated only when a calendar is created. If stored subentry data holds an invalid pattern (edited outside the flow), that calendar stays empty. The only signal is an error in the HA log, and other calendars are unaffected (01-08 Flagged Assumptions). Surfacing it as a Repairs issue is Phase 3. Record that you have seen this note.
</human-check>

## Next Phase Readiness

- 01-10 (publishing) can proceed. No third-party EPG data is in the repository.
- UAT needs the human-check above. ha-dev stays running on 18123.
- Deferred to later:
  - D-15 real-feed excerpt plus `scripts/trim_feed.py` (STATE.md Deferred Items)
  - parse timing on ha-host (RESEARCH A2)

## Self-Check: PASSED

- FOUND: tests/xmltv/test_real_feed.py; ~/Projects/dev/compose.yml.bak; ~/Projects/dev/media/xmltv/{small.xml,small-gzip.xml,large.xml,large.xml.gz}
- FOUND commit: 2af953f (on main, ancestor of HEAD)
- Task 1 acceptance:
  - the three verify commands pass (HTTP on 18123)
  - the log grep prints nothing
  - `grep -q 'xmltv_calendar:ro' compose.yml` succeeds
  - `git status --porcelain` showed no new files from Task 1
- Task 3 acceptance:
  - `uv run pytest tests/xmltv/test_real_feed.py -q -rs` exits 0 with 1 skipped (Task 2 chose none)
  - `uv run ruff check scripts tests` is clean
- Plan verification:
  - `uv run pytest -q`: 213 passed, 1 skipped (benchmark included)
  - `uv run pytest -q -m "not benchmark"`: 209 passed, 1 skipped
  - `uv run ruff check . && uv run ruff format --check .`: clean

---
*Phase: 01-first-filtered-calendar*
*Completed: 2026-10-14*
