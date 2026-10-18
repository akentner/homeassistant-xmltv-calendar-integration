---
phase: 01-first-filtered-calendar
reviewed: 2026-10-14T14:26:15Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - custom_components/xmltv_calendar/calendar.py
  - custom_components/xmltv_calendar/xmltv/parser.py
  - custom_components/xmltv_calendar/xmltv/timeparse.py
  - tests/test_calendar.py
  - tests/test_timing.py
  - tests/xmltv/test_parser.py
  - tests/xmltv/test_timeparse.py
findings:
  critical: 0
  warning: 7
  info: 14
  total: 21
status: issues_found
reverified: 2026-10-18T19:54:16Z
reverification_mode: inline
---

# Phase 01: Code Review Report

## Re-verification — 2026-10-18

The report below this section is the historical 01-11 review; its frontmatter finding counts describe that review.
This inline regression review inspected source.py, coordinator.py, __init__.py, calendar.py, config_flow.py,
xmltv/parser.py, timeparse.py, normalize.py, filter.py, window.py and render.py, plus the CI/HACS configuration
and requirement-linked tests. Source HEAD: 19e262dab163da4114809a248883102c93ceb9a8.

Validation: 821 passed, 1 intentionally skipped (real feed), Ruff check and format check passed.
No new blocking regression was demonstrated in the Phase 1 contract. Existing advisory findings are retained;
this is not a claim that every historical warning has been fixed.

| Existing finding | Current evidence / disposition |
|------------------|--------------------------------|
| CR-01 | Still fixed: malformed timestamp tracer, parser conversion guards and event-building tests pass. |
| WR-06 | Still fixed: stream error translation is confined to iterparse reads; programming-error propagation test passes. |
| WR-01 | Partial mitigation in Phase 2: nested repeats rejected. Overlapping alternation remains possible; no hard regex timeout. Keep open. |
| WR-02 | Remains open: chunk list plus bytes join and retained programmes are not a universal memory bound. The generated 60 MB benchmark passes at about 102 MB peak. |
| WR-04 | Remains open: check_file stores the resolved path, so later symlink rotation does not change the stored target. |
| WR-07 | Existing non-blocking decision retained from UAT test 9; a duration filter is available, but there is no unconditional parser duration cap. |
| WR-08 | Fixed in Phase 3: diagnostics exposes ParseStats, including skipped_malformed; test_diagnostics.py passes. |
| IN-01 | Fixed in Phase 3: identical EpgData bypasses refiltering in _handle_coordinator_update. |
| IN-14 | Fixed in Phase 2: MatchIndex._lower clamps underflow; boundary query tests pass. |

The previous review's remaining warnings/info stay in REVIEW-DISPOSITION.md for separate triage.
The HA 2026.3 compatibility floor has not been tested by this run (the harness uses HA 2026.10.1).

## Historical review — 2026-10-14

**Reviewed:** 2026-10-14T14:26:15Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

This is an incremental re-review of plan 01-11 (`git diff f18479c..HEAD`). Since `f18479c`, 01-11 changed only the 7
files listed above. It targeted CR-01 and WR-06 from the previous report.

Baseline: the 4 touched test modules pass (80 passed), and `ruff check` / `ruff format --check` are clean. I also
probed the changed code directly with hostile feeds: offsets, years, an empty document, an unknown encoding, truncated
gzip, and stop before start.

### Status of the previous findings

| ID | Previous severity | Status | Evidence |
|----|-------------------|--------|----------|
| CR-01 | critical | **Resolved** | See note 1 below the table. |
| WR-06 | warning | **Resolved** | See note 2 below the table. |
| WR-01 | warning | Still open | `parser._texts` (parser.py:59-60) still keeps title and sub-title text unbounded. `filter.py` is unchanged. |
| WR-02 | warning | Still open | `keep_after` is still applied after `normalize_programmes` (parser.py:177-181). `source.py` is unchanged. |
| WR-03, WR-04, WR-05 | warning | Still open (not touched) | `config_flow.py`, `source.py` and `README.md` are unchanged since `f18479c`. |
| IN-01 | info | Still open | `_async_refilter` (calendar.py:111-131) still re-filters when `epg is self._epg`. |
| IN-02 … IN-10 | info | Still open (not touched) | None of the affected files changed since `f18479c`. |

1. **CR-01 resolved.**
   - `parse_xmltv_time` now rejects offsets above 18 h, offset minutes of 60 or more, and written years outside 1900..2200. `datetime()` overflow is caught.
   - `_collect` skips and counts any `ValueError`/`OverflowError` raised while converting a programme.
   - `build_events` and `event` also catch `OverflowError` and `ValueError`.
   - I confirmed that within the year window, `start ± 18 h + 60 min`, `astimezone(UTC)` and `as_local` all stay in range.
2. **WR-06 resolved.** `_STREAM_ERRORS` is now translated only around `next(iterparse)`, in `_read_events`. A `KeyError` from per-element code now propagates (`test_programming_error_is_not_reported_as_feed_error`).

The carried-over findings below keep their original IDs and titles, so the disposition record stays intact. New findings
start at WR-07 and IN-11.

The new findings:
- **WR-07:** the year window bounds datetime arithmetic but not a programme's *duration*. One programme with a valid
  but absurd stop (for example year 2200) takes over the calendar's state for good.
- **WR-08:** the CR-01 fix turns a fatal error into a *completely silent* drop. `ParseStats` is never logged or exposed
  anywhere, so a feed where every programme is malformed loads as an empty calendar without a trace.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: ReDoS mitigation is ineffective; one pattern plus one long title can hang an executor thread for good

**File:** `custom_components/xmltv_calendar/xmltv/parser.py:59-60`, `custom_components/xmltv_calendar/xmltv/filter.py:16-18,73-74,104`
**Status:** Carried over and still open. `parser.py` changed in 01-11, but `_texts` still keeps text unbounded; `filter.py` is unchanged.
**Issue:**
- The 300-char and 50-line caps do not bound backtracking. For example, `^(\w+\s?)+$` is accepted, and its run time grows exponentially with the length of a title that ends in punctuation.
- Titles and sub-titles come from the untrusted feed and have no length limit.
- Python `re` cannot be interrupted, so the executor thread is lost for good, and the calendar never updates again.

**Fix:** Truncate text in `parser._texts`, for example to `_MAX_TEXT = 512`. Reject nested-quantifier shapes in
`first_invalid_pattern`.

### WR-02: Peak memory is twice the download cap, and the 1 GiB decompressed cap does not bound retained objects

**File:** `custom_components/xmltv_calendar/xmltv/parser.py:115-142,177-181`, `custom_components/xmltv_calendar/source.py:180-202`
**Status:** Carried over and still open. It was re-verified against the current `parser.py`.
**Issue:**
- `async_fetch_url` joins its chunk list, so two copies of the body are alive at once.
- `_collect` keeps every programme, including past ones, because `keep_after` is applied only after normalization.
- Nothing bounds the number of retained programmes.

**Fix:**
- Accumulate the download into one `bytearray`.
- Pass `keep_after` into `_collect` and skip programmes whose stop is known and earlier.
- Add a `MAX_PROGRAMMES` cap that raises `FeedTooLargeError`.

### WR-03: The invalid-regex error shows the wrong pattern when more than one field is invalid

**File:** `custom_components/xmltv_calendar/config_flow.py:205-209`, `custom_components/xmltv_calendar/translations/en.json:84`
**Status:** Carried over and still open. The files are unchanged since `f18479c` and are not in this review's scope.
**Issue:** `placeholders.setdefault("pattern", …)` records only the first bad pattern, but every invalid field renders
it.
**Fix:** Use one error key and placeholder pair per field, or report only the first invalid field.

### WR-04: A file source stores the resolved symlink target, so symlink-rotated feeds go stale

**File:** `custom_components/xmltv_calendar/source.py:133-142`, `custom_components/xmltv_calendar/config_flow.py:148`
**Status:** Carried over and still open. The files are unchanged since `f18479c`.
**Issue:** `check_file` returns `candidate.resolve()`, and that resolved path is persisted as `CONF_PATH`. When the
symlink is re-pointed, the integration keeps reading the old target.
**Fix:** Persist the user's absolute path. Keep the resolved path only for `unique_id` and for the allowlist check.

### WR-05: The README describes filter semantics the code does not implement

**File:** `README.md:3-4,38`
**Status:** Carried over and still open. The file is unchanged since `f18479c`.
**Issue:** The README says patterns are "matched against title and description". The code matches title and sub-title
only (D-07). The README also does not document `channel_regex`.
**Fix:** Change the README to say "title and sub-title", and document `channel_regex`.

### WR-07: The year window does not bound duration; one programme with an absurd stop takes over the calendar state

**File:** `custom_components/xmltv_calendar/xmltv/parser.py:82-83`, `custom_components/xmltv_calendar/xmltv/timeparse.py:17-20`, `custom_components/xmltv_calendar/xmltv/window.py:27,43-46`
**Issue:**
- The CR-01 fix accepts any start and stop inside 1900..2200, but nothing relates the stop to the start.
- One broken line such as `<programme channel="a.de" start="20261013100000 +0000" stop="22001231235959 +0000">` passes parsing and normalization.
- `keep_after` never drops it, because its stop is in the future.

I reproduced this. With that programme plus a normal one, `MatchIndex.current_or_next(2027-06-01)` returns the
"Hijack" programme, and `_max_duration` is 63,631 days. If the programme matches a calendar's filter:
- `event` returns it for the next 174 years, so the entity state is permanently `on`.
- The real current or next programme is never shown as `event`.
- Calendar end triggers for it never fire.
- Every `overlapping()` query scans from the beginning of the index, because `start - _max_duration` falls before every
  start.

This is the same kind of failure CR-01 was about: one line in a third-party EPG breaks the calendar. The year window's
comment says it keeps values "inside datetime's range", which is true, but it does not keep them sane.

**Fix:** Treat an implausibly long programme like an unparsable stop, so normalization infers the stop:
```python
# parser.py
MAX_PROGRAMME_DURATION = timedelta(hours=24)  # longer XMLTV programmes are broken data

def _programme(elem: ET.Element) -> Programme | None:
    ...
    stop = parse_xmltv_time(elem.get("stop"))
    if stop is None or stop - start > MAX_PROGRAMME_DURATION:
        stop = start  # inferred from the next start or default_duration (D-12)
```
Add a parser test asserting that a stop in year 2200 is inferred and counted in `inferred_stops`. Also add a
`MatchIndex` test asserting that `current_or_next` returns the real programme. Cap inferred stops too (IN-04) for
consistency.

### WR-08: Skipped malformed programmes are never reported, so the CR-01 fix makes broken feeds fail silently

**File:** `custom_components/xmltv_calendar/xmltv/parser.py:126-131`, `custom_components/xmltv_calendar/coordinator.py:77-98`
**Issue:**
- Before 01-11, a feed with bad timestamps surfaced as `invalid_feed`, which was wrong but visible.
- Now each one is silently turned into `stats.skipped_malformed += 1`.
- `ParseStats` is never logged, never put into an entity attribute and never exposed through diagnostics. `grep stats` over `custom_components/` finds no consumer outside `xmltv/`.

As a result:
- A grabber bug that writes `+2500` offsets on every programme gives a `LOADED` entry with empty calendars and zero log
  output at any level.
- The new `except ValueError, OverflowError` around `_programme` (line 128) also swallows any *future programming
  error* that raises `ValueError` in `_programme`, `_texts` or `parse_xmltv_time`. It is counted as "malformed", again
  silently. That partly undoes the intent of WR-06: a regression in per-element code looks like a clean feed with fewer
  programmes.

**Fix:** Surface the counters after every successful parse. Warn when a significant share of the feed was dropped:
```python
# coordinator.py, after parse returns `data`
stats = data.stats
if stats.skipped_malformed:
    level = logging.WARNING if stats.skipped_malformed > max(stats.programmes, 1) * 0.05 else logging.DEBUG
    _LOGGER.log(level, "Source %s: skipped %d malformed programmes (%d kept)",
                self.config_entry.title, stats.skipped_malformed, stats.programmes)
```
Also log the first skipped programme's exception class at DEBUG in `_collect`, so a swallowed bug can still be found.
Expose `ParseStats` in the planned diagnostics platform.

## Info

### IN-01: A failed refresh re-filters unchanged data and repeats the missing-channel warning

**File:** `custom_components/xmltv_calendar/calendar.py:105-131`
**Status:** Carried over and still open. It was re-verified against the current file.
**Issue:** `_handle_coordinator_update` re-runs `spec.apply` on the same `EpgData`. It also repeats the "selected
channels not in the feed" WARNING whenever availability flips.
**Fix:** In `_async_refilter`, when `epg is self._epg`, skip filtering and only write the state.

### IN-02: The `already_in_progress` abort reason has no translation

**File:** `custom_components/xmltv_calendar/translations/en.json:53-55`
**Status:** Carried over and still open. The file is unchanged.
**Fix:** Add `"already_in_progress": "Setup of this source is already in progress."`.

### IN-03: Limits are duplicated as literals in translations

**File:** `custom_components/xmltv_calendar/translations/en.json:84,99`
**Status:** Carried over and still open. The file is unchanged.
**Fix:** Pass the limits as placeholders, or assert in `test_repo_structure.py` that the strings match the constants.

### IN-04: Inferred stops have no upper bound

**File:** `custom_components/xmltv_calendar/xmltv/normalize.py:18-36`
**Status:** Carried over and still open. The file is unchanged. See WR-07 for the explicit-stop variant.
**Fix:** Use `min(following, start + MAX_INFERRED)`.

### IN-05: Only the first `<title>` is matched; other-language titles are ignored

**File:** `custom_components/xmltv_calendar/xmltv/filter.py:68-70`
**Status:** Carried over and still open. The file is unchanged.
**Fix:** Match against `(*programme.titles, *programme.sub_titles)`, or document the limitation until FLT-14.

### IN-06: `iot_class` is `cloud_polling` for local-file sources too

**File:** `custom_components/xmltv_calendar/manifest.json:8`
**Status:** Carried over and still open. The file is unchanged.
**Fix:** Accept it, or note it in the README.

### IN-07: The HA floor in `hacs.json` (2026.3.0) is never tested

**File:** `hacs.json:3`, `.github/workflows/ci.yml:32-46`
**Status:** Carried over and still open. The files are unchanged.
**Fix:** Add a CI matrix job at the floor version, or raise the floor.

### IN-08: The `hacs` job has no explicit `permissions` block

**File:** `.github/workflows/validate.yml:28-34`
**Status:** Carried over and still open. The file is unchanged.
**Fix:** Add `permissions: { contents: read }` to the job.

### IN-09: The `forbid_loop_io` guard only covers `builtins.open`

**File:** `tests/conftest.py:31-44`
**Status:** Carried over and still open. The file is unchanged.
**Fix:** Also guard `io.open` and `os.stat`, or enable HA's `block_async_io` detector in tests.

### IN-10: `monkeypatch.setattr(..., raising=False)` hides a renamed constant

**File:** `tests/test_source.py:38,53`
**Status:** Carried over and still open. The file is unchanged.
**Fix:** Drop `raising=False`.

### IN-11: The encoding-error test cannot detect a lost `from None`, and the original error is still attached

**File:** `tests/xmltv/test_parser.py:244-248`, `custom_components/xmltv_calendar/xmltv/parser.py:21-25,109-111`
**Issue:**
- `test_multibyte_encoding_declaration_raises_feed_error` asserts `excinfo.value.__cause__ is None`. That is true for any bare `raise FeedError(msg)` inside an `except`, with or without `from None`. If someone drops `from None`, the test still passes, but the traceback then prints the original error.
- `from None` only sets `__suppress_context__`. `__context__` still holds the original exception. I reproduced this: `encoding="SECRETCONTENT"` gives `__context__ == LookupError('unknown encoding: SECRETCONTENT')`, so text from the feed is still attached to the error object.
- The comment "it is never kept" (line 24) is therefore inaccurate. It is never *displayed*. That is fine for logs, but the comment and the test should say what is actually guaranteed.

**Fix:** Assert `excinfo.value.__suppress_context__ is True`, and add the same assertion for the `ParseError` and
`EOFError` paths. Reword the comment to "never displayed". If the error must not hold feed text at all, raise outside
the `except` block, using a flag.

### IN-12: The "empty document" branch in `parse` is dead code

**File:** `custom_components/xmltv_calendar/xmltv/parser.py:166-170`
**Issue:** Expat reports every empty or root-less input as a `ParseError` before `_read_events` can finish without
yielding. I checked `b""`, `b"   "` and a lone XML declaration: all three give `FeedError("invalid XML at line 1, …")`.
So `next(events)` in `_collect` never raises `StopIteration`, and the `"empty document"` message is never produced.
**Fix:** Remove the branch. Alternatively, keep it as an explicit defensive guard by handling it inside `_collect`
(`if (first := next(events, None)) is None: raise FeedError("empty document")`) instead of a broad `except StopIteration`
around the whole call.

### IN-13: `event` returns None when the current match cannot be built, hiding later valid matches

**File:** `custom_components/xmltv_calendar/calendar.py:137-144`
**Issue:**
- When `_to_event` fails for the programme that `current_or_next` returns, the property returns `None`, so the calendar shows `off` with no upcoming event even when later valid matches exist.
- Since the 01-11 time-parse guards, the parser can no longer produce such a programme: `test_event_property_skips_out_of_range_match` injects one directly. So this is a defensive path only.

**Fix:** Optional: iterate forward from `current_or_next` to the first programme that builds. Or document that the guard
only prevents a crash.

### IN-14: `async_get_events` raises `OverflowError` for queries starting near `datetime.min`

**File:** `custom_components/xmltv_calendar/xmltv/window.py:35`, `custom_components/xmltv_calendar/calendar.py:154`
**Issue:**
- `bisect_left(self._starts, start - self._max_duration)` overflows when `start_date` lies within `_max_duration` of year 1. I reproduced it: `overlapping(datetime(1, 1, 1, tzinfo=UTC), …)` with a 1-hour max duration raises `OverflowError: date value out of range`.
- HA's calendar handlers catch only `HomeAssistantError`, so a `calendar.get_events` / websocket query with an absurd start fails with an unhandled error instead of returning events.
- With WR-07 unfixed, the threshold rises to start years below about 300.

**Fix:** Clamp the lookback: `lo_key = start - self._max_duration if start - datetime.min.replace(tzinfo=UTC) > self._max_duration else self._starts[0] if self._starts else start`.
The simpler alternative is a `try/except OverflowError` that falls back to `lo = 0`. Apply the same to `current_or_next`.

---

_Reviewed: 2026-10-14T14:26:15Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
