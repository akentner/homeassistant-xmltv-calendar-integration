---
phase: 01-first-filtered-calendar
plan: 05
subsystem: ingestion
tags: [xmltv, gzip, iterparse, aiohttp, dos-guard, logging, tdd]

requires:
  - phase: 01-first-filtered-calendar
    provides: "01-01 walking skeleton: parser.parse/FeedError, source.async_fetch_url/SourceError, XmltvCoordinator error mapping, setup_xmltv/forbid_loop_io harness"
provides:
  - "parser.py: gzip detected by magic bytes 1f 8b, MAX_DECOMPRESSED_BYTES (1 GiB) via _CappedReader, FeedTooLargeError, keyword max_bytes, content-free FeedError messages, programme-only channels listed as Channel(id, id)"
  - "source.py: MAX_DOWNLOAD_BYTES (256 MiB), DOWNLOAD_TIMEOUT, SourceTooLargeError, streamed iter_chunked download, host-only logs (also on success)"
  - "coordinator.py: feed_too_large / unable_to_fetch / invalid_feed translation keys"
  - "Synthetic fixtures edge_cases.xml and latin1.xml (D-15)"
affects: [01-06, 01-07, 01-08, 01-09, 01-10, source, parser, diagnostics]

actuals:
  tokens: 37562   # chars/4 over the full realized diff (150,248 chars); code + tests alone are 19,794 chars (~4,949), the rest is JUnit/JSON RED evidence
  tasks: 3
  commits: 6
plan_head_before: 9fec3e8466bc8cb20a1ca5dc8fabb9064370b12e
plan_head_after: c20f4ecd4c293b4a551e049f87617fe7d336c3a5

tech-stack:
  added: []
  patterns:
    - "Every byte stream into iterparse goes through _CappedReader; read(-1) is clamped to one byte past the cap"
    - "Hostile-input exceptions (EOFError, BadGzipFile, zlib.error, LookupError, ValueError, ParseError) become FeedError with class name and position only, raised from None"
    - "Downloads bind resp.content once and count iter_chunked bytes against a module-level cap read at call time"
    - "Size failures map to their own translation key (feed_too_large), separate from unable_to_fetch and invalid_feed"

key-files:
  created:
    - tests/xmltv/test_parser.py
    - tests/test_ingestion.py
    - tests/test_source.py
    - tests/fixtures/edge_cases.xml
    - tests/fixtures/latin1.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-05-red.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-05-red.json
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-05-red-2.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-05-red-2-{cap,truncated-gzip,orphan,no-content}.json
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-05-red-3.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-05-red-3-{download-cap,decompressed-cap,logs}.json
  modified:
    - custom_components/xmltv_calendar/xmltv/parser.py
    - custom_components/xmltv_calendar/source.py
    - custom_components/xmltv_calendar/coordinator.py
    - custom_components/xmltv_calendar/translations/en.json

key-decisions:
  - "01-05: LookupError and ValueError are translated into FeedError too, because an unknown encoding declaration leaks feed text through LookupError('unknown encoding: <declared name>') and multi-byte encodings raise ValueError"
  - "01-05: programme-only channels are synthesized from all parsed programmes (before keep_after), so the picker lists them even when their programmes are all past"
  - "01-05: a successful download logs byte count and host at debug level, so logs can tell sources apart without the path or query"
  - "01-05: FeedError messages for stream failures carry the class name and the decompressed byte offset reached (position), never exception text"

patterns-established:
  - "Pure parser tests that need a not-yet-existing API reach it through the module (parser.FeedTooLargeError) so RED fails in the test body, not at collection"
  - "HA tests override setup_xmltv's response by registering an aioclient_mock entry first (first match wins)"

requirements-completed: [SRC-03, SRC-09, EVT-02]

coverage:
  - id: D1
    description: "A gzip body behind a .xml URL served as application/octet-stream loads; the calendar shows the 4 basic.xml events (gzip detected by magic bytes only)"
    requirement: SRC-03
    verification:
      - kind: integration
        ref: "tests/test_ingestion.py#test_gzip_behind_xml_url_end_to_end"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_parser.py#test_gzip_parses_like_plain, #test_plain_bytes_named_gz_parse"
        status: pass
    human_judgment: false
  - id: D2
    description: "Decompressed bytes capped (FeedTooLargeError, plain and gzip) and downloads capped (SourceTooLargeError); both retry setup with reason feed_too_large"
    requirement: SRC-09
    verification:
      - kind: unit
        ref: "tests/xmltv/test_parser.py#test_gzip_decompressed_cap, #test_plain_input_is_capped_too, #test_input_within_cap_parses"
        status: pass
      - kind: integration
        ref: "tests/test_source.py#test_download_cap_retries_setup, #test_body_within_download_cap_loads, #test_decompressed_cap_retries_setup"
        status: pass
    human_judgment: false
  - id: D3
    description: "Truncated/corrupt gzip, truncated XML, empty and non-XML input raise FeedError without feed content; a truncated-gzip refresh keeps the previous EpgData object"
    requirement: SRC-09
    verification:
      - kind: unit
        ref: "tests/xmltv/test_parser.py#test_truncated_gzip_raises_feed_error, #test_corrupt_gzip_raises_feed_error, #test_broken_input_raises_feed_error, #test_error_message_has_no_feed_content"
        status: pass
      - kind: integration
        ref: "tests/test_ingestion.py#test_refresh_with_truncated_gzip_keeps_previous_data"
        status: pass
    human_judgment: false
  - id: D4
    description: "Channel without display-name and programme-only channels use the channel ID as location and are listed in EpgData.channels; umlauts (UTF-8 and ISO-8859-1) preserved; 3 malformed programmes skipped and counted"
    requirement: EVT-02
    verification:
      - kind: unit
        ref: "tests/xmltv/test_parser.py#test_display_name_fallback, #test_programme_only_channel_is_listed, #test_skips_malformed_programmes, #test_umlaut_title_preserved, #test_latin1_declared_encoding"
        status: pass
    human_judgment: false
  - id: D5
    description: "HTTP 404/500, TimeoutError and ClientError retry setup with unable_to_fetch; logs never contain the URL token or path and name the host (success and failure)"
    verification:
      - kind: integration
        ref: "tests/test_source.py#test_fetch_failures_retry_setup, #test_logs_name_host_only, #test_failure_logs_name_host_only"
        status: pass
    human_judgment: false
  - id: D6
    description: "Parser yields the GIL every yield_every programmes (4 sleeps per 1,000 at 250, none at 0)"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_parser.py#test_yield_every_calls_sleep"
        status: pass
    human_judgment: false
  - id: D7
    description: "Download timeout DOWNLOAD_TIMEOUT (total=300, sock_read=60) is applied to the real aiohttp request"
    verification: []
    human_judgment: true
    rationale: "The aiohttp mock ignores the timeout argument; only code review of source.py (session.get(url, timeout=DOWNLOAD_TIMEOUT)) shows it"

duration: 6min
completed: 2026-10-13
status: complete
---

# Phase 1 Plan 05: Robust Feed Ingestion Summary

**Gzip is now detected by its magic bytes, not the URL or Content-Type. Decompressed XML is capped at 1 GiB and downloads are streamed with a 256 MiB cap and timeouts. Every broken, truncated or hostile payload becomes a typed, translated failure (`feed_too_large`, `unable_to_fetch`, `invalid_feed`) without feed content, and the previous data stays in place. Programme-only channels are listed under their ID.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-12T23:02:04Z
- **Completed:** 2026-10-12T23:08:02Z
- **Tasks:** 3
- **Files modified:** 9 code/test files plus 11 RED-evidence artifacts

## Accomplishments

- `parse()` (parser.py):
  - peeks two bytes and seeks back; on `1f 8b` it wraps the stream in `gzip.GzipFile`
  - reads plain and gzip input through `_CappedReader`, which raises `FeedTooLargeError` past `max_bytes` (default `MAX_DECOMPRESSED_BYTES = 1 << 30`)
- Typed parser errors:
  - `EOFError`, `BadGzipFile`, `zlib.error`, `LookupError`, `ValueError` and `ET.ParseError` all become `FeedError`
  - the message holds only the class name plus the line/column or byte offset, raised `from None`
  - a planted sentinel never reaches `str(error)`
- Programme channels without a `<channel>` element are added as `Channel(id, id)`, so the channel picker lists them (EVT-02).
- `async_fetch_url` (source.py):
  - binds `resp.content` once and counts `iter_chunked(1 << 16)` bytes against `MAX_DOWNLOAD_BYTES` (read at call time)
  - uses `DOWNLOAD_TIMEOUT`
  - raises `SourceTooLargeError` past the cap
  - logs only the host, now also on success
- The coordinator maps both size errors to `feed_too_large`. Other errors keep `unable_to_fetch` / `invalid_feed`. Matching `en.json` string added.
- The full suite is 113 passed (up from 82). Ruff is clean.

## Task Commits

1. **Task 1: Tracer: gzip behind a .xml URL**
   - `d4ed7d2` test(01-05): RED, tracer plus evidence
   - `b9abc1c` feat(01-05): GREEN, magic-byte sniff
   - Tracer feedback gate: interactive, `end-of-phase`, automated-only verify. Re-ran the verify, it passed, then expanded.
2. **Task 2: Bounded, typed parsing of hostile and odd feeds**
   - `6ce6626` test(01-05): RED, parser tests plus fixtures plus evidence
   - `d65eb7d` feat(01-05): GREEN, cap, error family, programme-only channels, `_collect` extraction
3. **Task 3: Streamed, capped, timed-out download with host-only logging**
   - `302adc4` test(01-05): RED, source tests plus truncated-refresh test plus evidence
   - `c20f4ec` feat(01-05): GREEN, streamed download, `feed_too_large` mapping, translation

## TDD Gate Compliance

| Cycle | RED | GREEN | REFACTOR |
|-------|-----|-------|----------|
| Task 1 (tracer) | `d4ed7d2` | `b9abc1c` | none needed |
| Task 2 | `6ce6626` | `d65eb7d` | none needed (the loop extraction was required for lint PLR0912 and is part of GREEN) |
| Task 3 | `302adc4` | `c20f4ec` | none needed |

**RED 1:** `test_gzip_behind_xml_url_end_to_end` (`01-05-red.json`). Classifier: RED_EVIDENCE_OK (target_test_failed).
- Semantic: the gzip mock matched and setup ran. The test failed on the planned entry-state assertion (SETUP_RETRY is not LOADED), because the parser fed gzip bytes to iterparse and the coordinator raised `invalid_feed`.

**RED 2:** one report (`01-05-red-2.xml`) with 8 failures and 13 passes. All four targets are RED_EVIDENCE_OK.
- `test_gzip_decompressed_cap`: failed in the body with `TypeError` on `max_bytes`. The cap API did not exist yet, so this is a missing-behaviour failure, not a collection fault.
- `test_truncated_gzip_raises_feed_error`: raw `EOFError` escaped `pytest.raises(FeedError)`.
- `test_programme_only_channel_is_listed`: failed on the assertion (`channels.get('orphan.de')` is None).
- `test_error_message_has_no_feed_content[unknown-encoding]`: raw `LookupError('unknown encoding: SENTINEL-x9q7')` escaped. This is the content leak the test guards.

**RED 3:** one report (`01-05-red-3.xml`) with 3 failures and 8 passes. All three targets are RED_EVIDENCE_OK.
- `test_download_cap_retries_setup`: LOADED instead of SETUP_RETRY, because there was no download cap.
- `test_decompressed_cap_retries_setup`: `'invalid_feed' == 'feed_too_large'` failed. The `feed_too_large` mapping was missing.
- `test_logs_name_host_only`: the secret/path absence assertions held, but no record named the host on a successful download.

**GREEN:** every target passes. `uv run pytest -q -m "not benchmark"` gives 113 passed.

## Files Created/Modified

- `custom_components/xmltv_calendar/xmltv/parser.py`:
  - `GZIP_MAGIC`, `MAX_DECOMPRESSED_BYTES`
  - `_STREAM_ERRORS`, `FeedTooLargeError`, `_CappedReader`
  - `_collect` (the event loop), `parse(..., max_bytes=...)`
  - programme-only channel synthesis
- `custom_components/xmltv_calendar/source.py`: `MAX_DOWNLOAD_BYTES`, `DOWNLOAD_TIMEOUT`, `SourceTooLargeError`, and the streamed, capped `async_fetch_url`.
- `custom_components/xmltv_calendar/coordinator.py`: `feed_too_large` mapping for both size errors.
- `custom_components/xmltv_calendar/translations/en.json`: `exceptions.feed_too_large.message`.
- `tests/xmltv/test_parser.py`: 21 pure parser tests (gzip, caps, typed errors, sentinel, edge cases, Latin-1, yield).
- `tests/test_ingestion.py`: gzip-behind-.xml tracer, truncated-gzip refresh that keeps the previous data.
- `tests/test_source.py`: download cap, decompressed cap, HTTP/timeout/client errors, host-only logs on success and failure. Every test uses `forbid_loop_io`.
- `tests/fixtures/edge_cases.xml`, `tests/fixtures/latin1.xml`: hand-written synthetic fixtures (D-15). latin1.xml is stored as real ISO-8859-1 bytes.

## Decisions Made

- `LookupError` and `ValueError` are added to the planned list of translated exceptions:
  - an unknown encoding declaration leaks feed text through `LookupError`
  - multi-byte encodings raise `ValueError`
- Programme-only channels are synthesized from every parsed programme, before the `keep_after` drop.
- A successful download logs `Downloaded N bytes from source host <host>` at debug level.
- Stream-failure messages give the decompressed byte offset reached as their position.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Security] Unknown-encoding and multi-byte-encoding errors translated into FeedError**
- **Found during:** Task 2 RED (probing hostile inputs)
- **Issue:** `<?xml encoding="X"?>` raised a raw `LookupError` whose text contains the declared encoding. That is feed content in the error and the logs (T-01-12), and the error was not a typed FeedError.
- **Fix:** `_STREAM_ERRORS` includes `LookupError` and `ValueError`. The sentinel test plants its marker in the encoding declaration.
- **Files modified:** custom_components/xmltv_calendar/xmltv/parser.py
- **Committed in:** d65eb7d

**2. [Rule 3 - Blocking] Event loop extracted into `_collect`**
- **Found during:** Task 2 GREEN
- **Issue:** the extra except clauses pushed `parse` over Ruff PLR0912 (14 > 12 branches).
- **Fix:** the iterparse loop moved into `_collect(reader, stats, yield_every)`. Behaviour is unchanged.
- **Committed in:** d65eb7d

**3. [Plan inconsistency] `test_refresh_with_truncated_gzip_keeps_previous_data` was not RED**
- **Found during:** Task 3 RED
- **Issue:** the plan names it a Task 3 RED target, but Task 2 GREEN already turns truncated gzip into FeedError, so the coordinator keeps the previous data.
- **Fix:** kept as a characterization test. Task 3 RED evidence rests on the three other targets.
- **Committed in:** 302adc4

**4. [Rule 2 - Missing critical] Host named in logs on a successful download**
- **Found during:** Task 3 RED
- **Issue:** the plan truth "at least one log record contains epg.example.com" only held on failures. A successful download logged nothing about its source.
- **Fix:** debug log with byte count and host after the download.
- **Committed in:** c20f4ec

---

**Total deviations:** 4 (2 missing critical/security, 1 blocking lint, 1 plan inconsistency)
**Impact on plan:** No interface changes beyond the planned additions, and no scope creep.

## Issues Encountered

- Commits landed on `main`, which the GSD protected-branch check reports as protected. The orchestrator dispatched this executor sequentially on the main working tree (`branching_strategy: none`, no remote) and explicitly authorized commits there, as for 01-01 to 01-04.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- Plan 01-07 (file sources) can pass an opened file to `parse` unchanged: the API takes any seekable binary file object and applies the same gzip sniffing and cap.
- Diagnostics (later plan) can surface `FeedError` text safely, because it never contains feed content or URLs.

## Self-Check: PASSED

- All 9 code/test key files exist on disk.
- Commits d4ed7d2, b9abc1c, 6ce6626, d65eb7d, 302adc4 and c20f4ec are ancestors of HEAD (6 commits since 9fec3e8, measured with `git rev-list --count`).
- `uv run pytest -q -m "not benchmark"` gives 113 passed. `uv run ruff check . && uv run ruff format --check .` is clean.
- Acceptance greps pass: GzipFile, no `endswith(`, `MAX_DECOMPRESSED_BYTES = 1 << 30`, `class FeedTooLargeError`, `noqa: S314`, `iter_chunked`, `MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024`, `feed_too_large` message, and the caplog `s3cret` assertion.

---
*Phase: 01-first-filtered-calendar*
*Completed: 2026-10-13*
