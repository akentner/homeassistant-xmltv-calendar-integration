---
phase: 01-first-filtered-calendar
plan: 07
subsystem: config-flow
tags: [home-assistant, config-flow, local-file, is_allowed_path, unique_id, sha256, yarl, probe, tdd]

requires:
  - phase: 01-first-filtered-calendar
    provides: "01-01 source flow (menu -> url -> name), XmltvCoordinator, forbid_loop_io harness; 01-05 parser gzip sniff and caps, async_fetch_url, SourceError family"
provides:
  - "Local-file sources (SRC-02): menu url|file, file step, executor-only check_file / probe_file / read_and_parse_file with absolute path + hass.config.is_allowed_path on every read"
  - "Persisted source identity (SRC-13): normalize_url (yarl) and source_unique_id = sha256('<type>:<normalized>'); duplicates abort already_configured before any probe"
  - "Flow-time validation with translated errors: invalid_url, cannot_connect, invalid_feed, path_not_allowed, file_not_found, name_required"
  - "async_probe_url: reads at most PROBE_BYTES (64 KiB), requires gzip magic or '<' after BOM/whitespace"
  - "Coordinator file branch with translation keys path_not_allowed and file_not_found"
affects: [01-08, 01-09, 01-10, diagnostics, options-flow, source-migration]

actuals:
  tokens: 76146   # chars/4 over the full realized diff (304,584 chars); code + tests alone are 36,212 chars (~9,053), the rest is JUnit/JSON RED evidence
  tasks: 3
  commits: 4
plan_head_before: 03caa13da72f43e00e53bb7a6e576056397e5b52
plan_head_after: d67143af6ce1f57c24e95cb1126cbee75bcc578b

tech-stack:
  added: []
  patterns:
    - "Source identity = typed locator: unique_id = sha256(f'{source_type}:{normalized}'); URL normalized by yarl, file by realpath"
    - "Flow order: validate locator -> async_set_unique_id + _abort_if_unique_id_configured -> probe (no network/file read for duplicates)"
    - "All file IO and is_allowed_path in one executor job; builtin open() (noqa PTH123) so forbid_loop_io can see loop calls"
    - "Parser errors mapped to UpdateFailed through one _feed_errors context manager shared by url and file branches"

key-files:
  created:
    - tests/test_config_flow.py
    - tests/test_identity.py
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-07-red.{xml,json}
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-07-red-2.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-07-red-2-{duplicate,normalize,cannot-connect,invalid-feed,file-errors,titles}.json
  modified:
    - custom_components/xmltv_calendar/config_flow.py
    - custom_components/xmltv_calendar/source.py
    - custom_components/xmltv_calendar/coordinator.py
    - custom_components/xmltv_calendar/translations/en.json

key-decisions:
  - "Task 2: sha256. Config entry unique_id = SHA-256 hex of '<source_type>:<normalized locator>' ('url:' / 'file:' prefix). Keeps URL query tokens out of a second persisted field; changing it later needs async_migrate_entry + VERSION bump"
  - "01-07: entry.data stores the normalized URL (fragment dropped, query kept) or the resolved real path, not the raw input"
  - "01-07: file read failures (OSError, e.g. permission denied) show file_not_found in the flow and unable_to_fetch at setup"
  - "01-07: file helpers use builtin open() with noqa PTH123, because Path.open bypasses the forbid_loop_io guard"

patterns-established:
  - "Duplicate check runs before the probe, so re-adding an existing source never touches the network or the file"
  - "Flow-level path tests build an allowed/ and outside/ layout (escaping symlink, traversal, directory, non-XML) under a resolved tmp_path"

requirements-completed: [SRC-01, SRC-02, SRC-03, SRC-04, SRC-13, CFG-01]

coverage:
  - id: D1
    description: "A gzip file under a .xml name in an allowed directory is added through the menu -> file -> name flow (name pre-filled 'guide.xml'); entry LOADED; an unfiltered calendar returns 4 events; no open() on the event loop"
    requirement: "SRC-02"
    verification:
      - kind: integration
        ref: "tests/test_config_flow.py#test_file_source_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "Relative, outside-allowlist, symlink-escaping and traversal paths give path_not_allowed; missing file or directory gives file_not_found; non-XML gives invalid_feed; no file content in the result; outside-allowlist and truncated files retry setup"
    requirement: "SRC-02"
    verification:
      - kind: integration
        ref: "tests/test_config_flow.py#test_file_step_errors, #test_file_outside_allowlist_is_refused_at_setup, #test_truncated_file_retries_setup"
        status: pass
    human_judgment: false
  - id: D3
    description: "URL validation: non-http(s)/hostless URLs invalid_url; ClientError, timeout, 404, 500 cannot_connect; 'hello' invalid_feed; BOM + whitespace before '<' passes; probe consumes at most 64 KiB of a 1 MiB body"
    requirement: "SRC-01"
    verification:
      - kind: integration
        ref: "tests/test_config_flow.py#test_url_with_other_scheme_is_invalid, #test_unreachable_url_cannot_connect, #test_non_feed_body_is_invalid_feed, #test_bom_and_whitespace_before_xml_pass, #test_probe_reads_at_most_probe_bytes"
        status: pass
    human_judgment: false
  - id: D4
    description: "Equivalent URL spellings and a symlink to the same file abort already_configured (no probe request); unique_id is the sha256 of the typed locator and holds no query token; same title with different URLs gives two entries"
    requirement: "SRC-13"
    verification:
      - kind: unit
        ref: "tests/test_identity.py#test_normalize_url_canonical_form, #test_normalize_url_rejects, #test_source_unique_id_is_sha256_of_typed_locator"
        status: pass
      - kind: integration
        ref: "tests/test_identity.py#test_url_variant_identity_invariant, #test_file_variant_identity_invariant, #test_url_entry_stores_normalized_url_and_hashed_id; tests/test_config_flow.py#test_same_name_different_urls_both_created"
        status: pass
    human_judgment: false
  - id: D5
    description: "Refresh interval: 1 h accepted (update_interval 1 h), 0 and 169 rejected by the schema, default 24 h, missing option means 24 h"
    requirement: "SRC-04"
    verification:
      - kind: integration
        ref: "tests/test_config_flow.py#test_minimum_refresh_is_one_hour, #test_refresh_out_of_bounds_is_rejected, #test_refresh_default_is_24_hours, #test_missing_refresh_option_means_24_hours"
        status: pass
    human_judgment: false
  - id: D6
    description: "Blank or whitespace name rejected with name_required"
    requirement: "CFG-01"
    verification:
      - kind: integration
        ref: "tests/test_config_flow.py#test_blank_name_is_rejected"
        status: pass
    human_judgment: false
  - id: D7
    description: "Menu, file step texts and error messages render correctly in the real HA frontend; /media is allowed by default on the user's HA install"
    verification: []
    human_judgment: true
    rationale: "No frontend in the test harness and the allowlist default depends on the HA install type; checked on the ha-dev container / ha-host in plan 01-09"

duration: 6min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 07: Source Setup Completion Summary

**Local XMLTV files (plain or gzip, any name) can now be added as sources, and they are read only from directories Home Assistant allows. Every source gets a hashed, normalized identity (`sha256("url:"/"file:" + locator)`), so the same source added twice aborts with `already_configured`. Bad URLs, unreachable hosts, non-feeds, disallowed or missing paths and blank names are refused in the flow with translated errors. The URL probe reads at most 64 KiB.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-13T23:42:46Z
- **Completed:** 2026-10-13T23:48:46Z
- **Tasks:** 3 (Task 2 resolved before dispatch: sha256)
- **Files modified:** 6 code/test files plus 9 RED-evidence artifacts

## Accomplishments

- The source menu offers `url` then `file`.
- The file step:
  - runs `check_file` (absolute path, `hass.config.is_allowed_path`, regular file) and `probe_file` in the executor
  - stores the resolved real path
  - pre-fills the name with the file name
- `read_and_parse_file` repeats the allowed-path check on every setup and refresh, then parses with the same gzip sniff and caps as URL sources (SRC-03 for files).
- `normalize_url` uses yarl: it lower-cases scheme and host, drops the default port, the dot segments and the fragment, and keeps the query. Only http and https URLs with a host are accepted.
- `source_unique_id` is SHA-256 of the typed locator. The flow sets it and aborts duplicates before probing.
- `async_probe_url` streams at most `PROBE_BYTES = 64 * 1024`. It maps ClientError, timeouts and HTTP 4xx/5xx to `cannot_connect`, and non-gzip/non-`<` bodies to `invalid_feed`. Logs name only the host.
- The coordinator branches on `source_type`. File errors map to `path_not_allowed` / `file_not_found` / `unable_to_fetch`, and parser errors go through one shared `_feed_errors` mapping.
- The full suite is 181 passed (up from 145 after Task 1, 113+ before). Ruff is clean.

## Task Commits

1. **Task 1: Tracer: local gzip file with a .xml name**
   - `7d753ea` test(01-07): RED, tracer plus evidence
   - `43d7872` feat(01-07): GREEN, file step, file helpers, coordinator branch, translations
   - Tracer feedback gate: interactive, `end-of-phase`, automated-only verify. Re-ran the verify (2 passed, no "blocking open()"), then expanded.
2. **Task 2: Persisted source identity**: checkpoint:decision resolved by the user before dispatch, answer **sha256**. No commit.
3. **Task 3: Flow validation, duplicates, name default, refresh bounds**
   - `6ca7606` test(01-07): RED, identity and flow tests plus evidence
   - `d67143a` feat(01-07): GREEN, normalize/unique_id/probe, validated url and file steps, error translations

## TDD Gate Compliance

| Cycle | RED | GREEN | REFACTOR |
|-------|-----|-------|----------|
| Task 1 (tracer) | `7d753ea` | `43d7872` | none needed |
| Task 3 | `6ca7606` | `d67143a` | none needed |

**RED 1:** `test_file_source_end_to_end` (`01-07-red.json`). Classifier: RED_EVIDENCE_OK (target_test_failed).
- Semantic: the test ran with `forbid_loop_io` active and failed on the planned menu assertion (`['url'] != ['url', 'file']`). It was not a collection or fixture fault.

**RED 2:** one report (`01-07-red-2.xml`) with 25 failures and 12 passes. All six targets are RED_EVIDENCE_OK.
- `test_url_variant_identity_invariant`: the first entry was created, then the test failed in its body on `source.source_unique_id` (missing identity, so no duplicate abort).
- `test_normalize_url_canonical_form`: `AttributeError` on `source.normalize_url`. The behaviour is missing; the module was reached through the package, so collection succeeded.
- `test_unreachable_url_cannot_connect[http-404]`: `errors == {}`, because the flow did not probe.
- `test_non_feed_body_is_invalid_feed`: `errors == {}`, no probe.
- `test_file_step_errors[symlink-escape]`: the step went to `name`, because there was no path validation in the flow.
- `test_same_name_different_urls_both_created`: both unique_ids were None.
- The 12 passing tests are characterization tests (see Deviations, item 3).

**GREEN:** every target passes. `uv run pytest -q -m "not benchmark"` gives 181 passed.

## Files Created/Modified

- `custom_components/xmltv_calendar/source.py`:
  - errors: `PathNotAllowedError`, `FileMissingError`, `InvalidFeedError`, `InvalidUrlError`
  - identity: `normalize_url`, `source_unique_id`
  - probes: `PROBE_BYTES`, `looks_like_feed`, `async_probe_url`
  - file reads: `check_file`, `probe_file`, `read_and_parse_file`
- `custom_components/xmltv_calendar/config_flow.py`:
  - the menu now offers `url` and `file`
  - shared `_refresh_selector`
  - validated `async_step_url` and new `async_step_file`, both setting the unique_id and aborting duplicates
  - `_host_of` removed, replaced by `normalize_url`
- `custom_components/xmltv_calendar/coordinator.py`: `_async_update_url` / `_async_update_file` and the `_feed_errors` context manager.
- `custom_components/xmltv_calendar/translations/en.json`:
  - `config.step.file` and the menu option `file`
  - the six `config.error` keys
  - `exceptions.path_not_allowed` and `exceptions.file_not_found`
- `tests/test_config_flow.py`: tracer plus 29 flow, setup and refresh tests. Every flow test uses `forbid_loop_io`.
- `tests/test_identity.py`: normalization, the sha256 format pin, and the duplicate invariant for the url and file variants.

## Decisions Made

- **Task 2: sha256.** unique_id = SHA-256 hex of `"<source_type>:<normalized locator>"`. This keeps API keys in URL queries out of the unique_id and out of later diagnostics. `test_source_unique_id_is_sha256_of_typed_locator` pins the persisted format.
- entry.data stores the normalized URL or the real path, so the stored locator and the identity always agree.
- Read failures of an allowed, existing file (for example permission denied) show `file_not_found` ("does not exist, is not a regular file or cannot be read") in the flow, and `unable_to_fetch` at setup.
- File reads use builtin `open()` with `noqa: PTH123`: `Path.open` goes through `io.open`, and that bypasses the `forbid_loop_io` test guard.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Security] Extra path-escape cases in the file step tests**
- **Found during:** Task 3 RED
- **Issue:** The plan named relative, disallowed-directory, missing and non-XML paths. It did not name the two classic bypasses of T-01-18: a symlink inside the allowed directory that points outside, and `../` traversal.
- **Fix:** Added `symlink-escape`, `traversal` and `directory` cases plus a SENTINEL-content check. `is_allowed_path` resolves both bypasses, so no extra production code was needed.
- **Files modified:** tests/test_config_flow.py
- **Committed in:** 6ca7606

**2. [Rule 2 - Missing critical] OSError on file reads mapped to typed errors**
- **Found during:** Task 1 GREEN
- **Issue:** An unreadable file (permissions) would have raised a raw `OSError` out of the executor job, crashing the flow or failing setup without a translation key.
- **Fix:** `probe_file` and `read_and_parse_file` raise `SourceUnavailableError` (type name only, `from None`). The flow shows `file_not_found`; the coordinator raises `unable_to_fetch`.
- **Files modified:** source.py, config_flow.py, coordinator.py
- **Committed in:** 43d7872, d67143a

**3. [Plan inconsistency] 12 Task 3 tests were green in RED**
- **Found during:** Task 3 RED
- **Issue:** Some behaviour already existed before Task 3: `name_required` and the refresh bounds and default came from 01-01, and the truncated-file retry and setup-time allowlist refusal came from Task 1 GREEN. Their tests passed in RED.
- **Fix:** Kept them as characterization tests. The Task 3 RED evidence rests on the six failing targets.
- **Committed in:** 6ca7606

**4. [Rule 3 - Blocking] `allowed_dir` sync fixture**
- **Found during:** Task 1 RED
- **Issue:** Ruff ASYNC240 rejects `tmp_path.resolve()` inside an async test.
- **Fix:** The resolve runs in a sync `allowed_dir` fixture. `is_allowed_path` compares resolved paths, so the allowlist entry must be resolved.
- **Committed in:** 7d753ea

---

**Total deviations:** 4 (2 security/missing critical, 1 plan inconsistency, 1 blocking lint)
**Impact on plan:** No interface changes beyond the planned additions, and no scope creep. `const.py` was listed in files_modified but needed no change: all keys already existed.

## Issues Encountered

- Commits landed on `main`, which the GSD protected-branch check reports as protected. The orchestrator dispatched this executor sequentially on the main working tree (`branching_strategy: none`, no remote) and explicitly authorized commits there, as for 01-01 to 01-06.

## User Setup Required

None for the tests. On a real install, local files must sit in a directory HA allows: the media folders by default, or any directory listed in `allowlist_external_dirs`. The file step's help text says so.

## Next Phase Readiness

- The options flow and reconfigure (later plan) can reuse `normalize_url`, `check_file` and `source_unique_id`. A changed locator must update the unique_id too.
- Diagnostics (Phase 3) can show `entry.unique_id` without redaction, because it is a hash.

## Self-Check: PASSED

- All 6 code/test key files and the 9 evidence files exist on disk.
- Commits 7d753ea, 43d7872, 6ca7606 and d67143a are ancestors of HEAD (4 commits since 03caa13, measured with `git rev-list --count`).
- `uv run pytest -q -m "not benchmark"` gives 181 passed. `uv run ruff check . && uv run ruff format --check .` is clean.
- Acceptance checks pass:
  - greps: `is_allowed_path` (source.py), `read_and_parse_file` (coordinator.py), `_abort_if_unique_id_configured` (config_flow.py), `PROBE_BYTES = 64 * 1024`
  - the en.json error-key assertion
  - the tracer requests `forbid_loop_io`
  - the unique_id scheme matches the Task 2 decision (sha256)

---
*Phase: 01-first-filtered-calendar*
*Completed: 2026-10-14*
