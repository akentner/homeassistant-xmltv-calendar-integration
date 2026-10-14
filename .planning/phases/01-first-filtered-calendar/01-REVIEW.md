---
phase: 01-first-filtered-calendar
reviewed: 2026-10-14T11:07:53Z
depth: standard
files_reviewed: 48
files_reviewed_list:
  - custom_components/xmltv_calendar/__init__.py
  - custom_components/xmltv_calendar/calendar.py
  - custom_components/xmltv_calendar/config_flow.py
  - custom_components/xmltv_calendar/const.py
  - custom_components/xmltv_calendar/coordinator.py
  - custom_components/xmltv_calendar/data.py
  - custom_components/xmltv_calendar/manifest.json
  - custom_components/xmltv_calendar/source.py
  - custom_components/xmltv_calendar/translations/en.json
  - custom_components/xmltv_calendar/xmltv/__init__.py
  - custom_components/xmltv_calendar/xmltv/filter.py
  - custom_components/xmltv_calendar/xmltv/model.py
  - custom_components/xmltv_calendar/xmltv/normalize.py
  - custom_components/xmltv_calendar/xmltv/parser.py
  - custom_components/xmltv_calendar/xmltv/render.py
  - custom_components/xmltv_calendar/xmltv/timeparse.py
  - custom_components/xmltv_calendar/xmltv/window.py
  - .github/workflows/ci.yml
  - .github/workflows/validate.yml
  - hacs.json
  - pyproject.toml
  - .ruff.toml
  - .gitignore
  - renovate.json
  - README.md
  - scripts/generate_benchmark_feed.py
  - tests/conftest.py
  - tests/test_calendar.py
  - tests/test_config_flow.py
  - tests/test_filtering.py
  - tests/test_identity.py
  - tests/test_ingestion.py
  - tests/test_init.py
  - tests/test_repo_structure.py
  - tests/test_source.py
  - tests/test_subentry_flow.py
  - tests/test_timing.py
  - tests/test_tracer.py
  - tests/xmltv/conftest.py
  - tests/xmltv/test_benchmark.py
  - tests/xmltv/test_filter.py
  - tests/xmltv/test_normalize.py
  - tests/xmltv/test_parser.py
  - tests/xmltv/test_purity.py
  - tests/xmltv/test_real_feed.py
  - tests/xmltv/test_render.py
  - tests/xmltv/test_timeparse.py
  - tests/xmltv/test_window.py
findings:
  critical: 1
  warning: 6
  info: 10
  total: 17
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-10-14T11:07:53Z
**Depth:** standard
**Files Reviewed:** 48
**Status:** issues_found

## Summary

I reviewed the whole phase-01 scope: the integration (`custom_components/xmltv_calendar/**`), the CI workflows and repo
metadata, the README, the benchmark generator and every test module. Baseline: `pytest -m "not benchmark"` passes
(209 passed, 1 skipped), and `ruff check` / `ruff format --check` are clean.

The architecture is solid:
- Parsing and filtering run in the executor.
- File IO and `is_allowed_path` run off the loop.
- Logs name only the host.
- Gzip is sniffed by magic bytes, and both the download and the decompressed size are capped.

The central defect is in the hostile/broken-feed path. **A single malformed `<programme>` timestamp aborts the parse of
the entire feed, or crashes event building.** This contradicts the parser's "skip and count malformed programmes"
contract. I reproduced every case in this finding against the real code. The other problems are:
- The ReDoS mitigation is ineffective.
- Peak memory around a download is twice the cap.
- Wrong error placeholders appear in the subentry form.
- A file source silently pins to a symlink target.
- The README contradicts the filter semantics.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: One malformed programme timestamp kills the whole feed (and far-future dates crash event building)

**File:** `custom_components/xmltv_calendar/xmltv/timeparse.py:29-41`, `custom_components/xmltv_calendar/xmltv/normalize.py:33,53`, `custom_components/xmltv_calendar/calendar.py:40-56,139-143`
**Issue:** `parse_xmltv_time` says it returns `None` for invalid values, and `_programme` relies on that to skip and count
malformed programmes. Three paths break this contract. I reproduced each one with the project venv:

1. **Offset of 24 h or more** (`start="20261013120000 +2500"`): `_tz()` at line 31 calls `timezone(timedelta(minutes=1500))`. That raises `ValueError` *outside* the `try` at line 38. The `ValueError` escapes `_programme`, and `parse()` catches it via `_STREAM_ERRORS`. Result: `FeedError: unreadable feed: ValueError after 277 bytes`. The **whole feed** is rejected (`invalid_feed`, setup retry / stale data forever), not just that one programme.
2. **Extreme years** (`00010101000000 +0100`, `99991231233000 -0100`, or `99991231233000 +0000` without a stop): `normalize_programmes` line 53 (`start.astimezone(UTC)`) or `_infer_stops` line 33 (`start + default_duration`) raises `OverflowError`. That is neither a `FeedError` nor in `_STREAM_ERRORS`. `_feed_errors` does not catch it, so the coordinator logs "Unexpected error fetching … data" with a traceback, and setup fails with no translation key.
3. **Far-future programme that survives parsing** (`start="99991231230000 +0000" stop="99991231235959 +0000"`): `dt_util.as_local()` in `_to_event` raises `OverflowError` for any timezone east of UTC. `build_events` (line 55) and `event` (line 141) only catch `HomeAssistantError`. So `async_get_events` fails, and when this is the next match, the `event` property raises during `async_write_ha_state`.

One bad line in a third-party EPG of tens of MB should never take every calendar of the source offline.

**Fix:** Validate the offset range, and convert overflows into "not a timestamp". Also skip per programme defensively:
```python
# timeparse.py
_MAX_OFFSET_MINUTES = 18 * 60  # real-world offsets are within +-14h

def parse_xmltv_time(value: str | None) -> datetime | None:
    ...
    if sign:
        offset = int(off_h) * 60 + int(off_m)
        if int(off_m) >= 60 or offset > _MAX_OFFSET_MINUTES:
            return None
        tz = _tz(-offset if sign == "-" else offset)
    ...
    try:
        result = datetime(int(year), ..., tzinfo=tz)
        result.astimezone(UTC)  # rejects instants outside datetime's range
    except (ValueError, OverflowError):
        return None
    if not (1900 <= result.year <= 2200):  # keeps start + duration and as_local() in range
        return None
    return result
```
Also widen the guards in `calendar.py` to `except (HomeAssistantError, OverflowError, ValueError)` in both
`build_events` and `event`. Add parser tests for `+2500`, `+0099`, year 0001 and year 9999. Each test should assert that
the good programme of the same feed still parses and that `skipped_malformed` is incremented.

## Warnings

### WR-01: ReDoS mitigation is ineffective; one pattern plus one long title can hang an executor thread for good

**File:** `custom_components/xmltv_calendar/xmltv/filter.py:16-18,73-74,104`, `custom_components/xmltv_calendar/xmltv/parser.py:49-54`
**Issue:** The 300-char / 50-line caps do not bound backtracking. `^(\w+\s?)+$` is accepted by `first_invalid_pattern`.
Matching it against `"a"*24 + "!"` took 1.25 s, and the time doubles with every extra character. A 40-character title
with trailing punctuation never finishes in practice. Programme titles and sub-titles come from the untrusted feed and
have no length limit; a title can be megabytes inside the 1 GiB cap.

The comment "matching runs in the executor anyway" understates the impact:
- Python `re` cannot be interrupted, so the thread is lost permanently.
- `_async_refilter` never completes, so the calendar never updates.
- Every coordinator refresh queues another stuck job.
- Entry unload waits on the task, and HA shutdown waits on the executor.

**Fix:**
- Bound the input. Truncate each title and sub-title at parse time (for example `_MAX_TEXT = 512` in `parser._texts`). This also bounds memory.
- In `first_invalid_pattern`, reject the obvious catastrophic shapes: a nested quantifier such as `(...+)+`, `(...*)*` or `(...+)*`, detectable with `re.search(r"\((?:[^()\\]|\\.)*[+*}]\)[+*{]", line)`.
- Fix the misleading comment.

Phase 2 already plans "validate patterns with ReDoS in mind". Until then, the length truncation is the cheap effective
guard.

### WR-02: Peak memory is twice the download cap, and the 1 GiB decompressed cap does not bound retained objects

**File:** `custom_components/xmltv_calendar/source.py:180-202`, `custom_components/xmltv_calendar/xmltv/parser.py:16,90-114,155-159`
**Issue:**
- `async_fetch_url` keeps every chunk in `chunks` and then returns `b"".join(chunks)`. During the join, both copies are alive, so a feed at the cap needs about 512 MiB.
- After that, `parse()` retains a `Programme` (with description, categories and episode) for **every** programme. That includes programmes that are already in the past: `keep_after` is applied only after `normalize_programmes`.
- The benchmark measured about 111 MB RSS for 60 MB of XML. A feed near the 1 GiB decompressed cap would therefore need roughly 2 GB.
- During a refresh, the old `EpgData` is alive as well.

On the Odroid N2+ / small LXC targets named in the project constraints, this risks an OOM kill of HA core. The
per-source "memory bound" in practice comes from the feed's content, not from a configured limit.

**Fix:**
- Accumulate the download into one `bytearray` (`buf += chunk`), then `io.BytesIO(buf)`. That gives one copy plus amortized growth instead of two copies.
- Drop past programmes inside `_collect`: pass `keep_after` down and skip a programme whose stop is known and earlier.
- Add a hard `MAX_PROGRAMMES` (for example 500k) that raises `FeedTooLargeError`.
- Consider a lower decompressed cap (256–512 MiB). That is still several times the largest real feeds.

### WR-03: The invalid-regex error shows the wrong pattern when more than one field is invalid

**File:** `custom_components/xmltv_calendar/config_flow.py:205-209`, `custom_components/xmltv_calendar/translations/en.json:84`
**Issue:** `placeholders.setdefault("pattern", …)` records only the first bad pattern. Every field with an error then
renders the same `invalid_regex` string, which interpolates the same `{pattern}` and `{error}`. With `include="("` and
`exclude="[a-"`, the exclude field reports "Invalid pattern (: missing ), unterminated subpattern". The user is told
their valid-looking exclude line is broken in a way it is not.

**Fix:** Use one error key and one placeholder pair per field, for example `errors[field] = f"invalid_regex_{field}"`
with placeholders `{field}_pattern` and `{field}_error`. Alternatively, report the first bad field only:
```python
for field in _PATTERN_FIELDS:
    if (bad := first_invalid_pattern(str(user_input.get(field, "")))) is not None:
        errors[field] = "invalid_regex"
        placeholders = {"pattern": bad.pattern, "error": bad.message}
        break
```
Add a test that submits two invalid fields.

### WR-04: A file source stores the resolved symlink target, so symlink-rotated feeds go stale

**File:** `custom_components/xmltv_calendar/source.py:133-142`, `custom_components/xmltv_calendar/config_flow.py:148`
**Issue:** `check_file` returns `candidate.resolve()`, and the flow persists that path as `CONF_PATH`. Every refresh
then reads the *original target*. Many EPG grabbers publish via a stable symlink such as `/media/epg/guide.xml →
guide-2026-10-14.xml`. After the next rotation:
- The integration keeps re-reading yesterday's file and shows stale data silently.
- Once the old file is deleted, the source fails with `file_not_found`, even though the configured path is fine.

Resolving the path is right for the `unique_id` (dedup) and for the allowlist check, which `is_allowed_path` already
does on every refresh. It is wrong for the locator that gets read.

**Fix:** Store the user's absolute path (`str(Path(path))`), and keep `source_unique_id(SOURCE_TYPE_FILE, real_path)` for
dedup. `read_and_parse_file` already re-runs `check_file` (allowlist plus `resolve`) on every refresh, so security is
unchanged. Add a test that re-points the symlink between two refreshes.

### WR-05: The README describes filter semantics the code does not implement

**File:** `README.md:3-4,38`
**Issue:** The README says include and exclude patterns are "matched against title and description". The code, per
decision D-07, matches **title and sub-title** only (`filter._fields`). The flow help text in `en.json` says so too.
Users following the README will write description patterns that never match, and they get no feedback. The README also
omits the channel-regex field, and it does not say that both channel fields empty means all channels plus channel
regex OR picked channels.

**Fix:** Change both sentences to "title and sub-title" and document `channel_regex`. When FLT-05 (field selection)
lands in Phase 2, update the README in the same change.

### WR-06: `_STREAM_ERRORS` catches `ValueError` and `LookupError`, which turns programming bugs into "invalid feed"

**File:** `custom_components/xmltv_calendar/xmltv/parser.py:19,146-148`
**Issue:** The `try` covers the whole `_collect` loop, including `_programme`, `_channel` and `parse_xmltv_time`. Any
`ValueError`, `KeyError` or `IndexError` raised there becomes "unreadable feed: <Type> after N bytes" with `from None`,
so the traceback is discarded. This is how CR-01 path 1 surfaced as "invalid feed" and was never noticed. A future
regression in per-element code will look like a broken upstream feed.

**Fix:**
- Keep `_STREAM_ERRORS` for errors raised by `reader.read()` and expat. Narrow it to `(EOFError, gzip.BadGzipFile, zlib.error, UnicodeDecodeError)` and `LookupError` raised for an unknown encoding at the first read.
- Guard per-element conversion separately, and count failures as `skipped_malformed`:
```python
try:
    programme = _programme(elem)
except (ValueError, OverflowError):
    programme = None
```

## Info

### IN-01: A failed refresh re-filters unchanged data and repeats the missing-channel warning

**File:** `custom_components/xmltv_calendar/calendar.py:104-108,124-129`
**Issue:** When `last_update_success` flips to False, the coordinator notifies listeners. `_handle_coordinator_update`
then re-runs the full filter on the same `EpgData` and logs the "selected channels not in the feed" WARNING again.
**Fix:** In `_async_refilter`, skip the filter step when `epg is self._epg`, and only call `async_write_ha_state()` for
the availability change.

### IN-02: The `already_in_progress` abort reason has no translation

**File:** `custom_components/xmltv_calendar/translations/en.json:53-55`
**Issue:** `async_set_unique_id()` aborts with `already_in_progress` when a second flow for the same source is open.
`[%key:…%]` references are not resolved for custom integrations, so the user sees the raw key.
**Fix:** Add `"already_in_progress": "Setup of this source is already in progress."`.

### IN-03: Limits are duplicated as literals in translations

**File:** `custom_components/xmltv_calendar/translations/en.json:84,99`
**Issue:** "300 characters", "50 lines", "256 MiB" and "1 GiB" duplicate `MAX_PATTERN_LENGTH`, `MAX_PATTERN_LINES`,
`MAX_DOWNLOAD_BYTES` and `MAX_DECOMPRESSED_BYTES`. A change to any constant leaves the UI text wrong.
**Fix:** Pass the limits as placeholders, or add a test in `test_repo_structure.py` that asserts the strings match the
constants.

### IN-04: Inferred stops have no upper bound

**File:** `custom_components/xmltv_calendar/xmltv/normalize.py:18-36`
**Issue:** A programme with a missing stop runs until the next start on its channel, even when that start is days later
(a feed gap). The calendar state stays "on" for days, and `MatchIndex._max_duration` grows, which widens every lookback.
**Fix:** Cap the inferred duration, for example `min(following, start + MAX_INFERRED)` with `MAX_INFERRED = 12 h`.

### IN-05: Only the first `<title>` is matched; other-language titles are ignored

**File:** `custom_components/xmltv_calendar/xmltv/filter.py:68-70`
**Issue:** `Programme.titles` keeps every title, but `_fields` uses `programme.title` (`titles[0]`) only. In
multi-language feeds, an include pattern on the second-language title never matches.
**Fix:** Use `(*programme.titles, *programme.sub_titles)`, or document this until FLT-14.

### IN-06: `iot_class` is `cloud_polling` for local-file sources too

**File:** `custom_components/xmltv_calendar/manifest.json:8`
**Issue:** File sources are `local_polling`. The manifest supports only one value, but the current one is misleading for
half of the source types.
**Fix:** Accept as is, or note it in the README. `cloud_polling` is the better default for URL feeds.

### IN-07: The HA floor in `hacs.json` (2026.3.0) is never tested

**File:** `hacs.json:3`, `.github/workflows/ci.yml:32-46`
**Issue:** CI runs only against the HA version that phcc 0.13.372 pins (2026.10.1). Nothing verifies that the subentry,
`config_subentry_id` and `UpdateFailed(translation_key=…)` APIs behave the same at the declared floor.
**Fix:** Add a matrix job with the phcc release that pins 2026.3.x, or raise the floor to the tested version.

### IN-08: The `hacs` job has no explicit `permissions` block

**File:** `.github/workflows/validate.yml:28-34`
**Issue:** Every other job declares `permissions: contents: read`. The `hacs` job inherits `permissions: {}`. It works
for a public repo, but it is inconsistent and can break if the repo becomes private or the action starts needing
`contents: read`.
**Fix:** Add `permissions: { contents: read }` to the job.

### IN-09: The `forbid_loop_io` guard only covers `builtins.open`

**File:** `tests/conftest.py:31-44`
**Issue:** `Path.open`, `io.open`, `gzip.open`, `os.stat` and `Path.resolve` / `is_file` bypass the guard. The
production code avoids `Path.open` only so that the guard stays effective (`source.py:148` noqa comment). A regression
that uses `Path.read_bytes()` or `is_allowed_path` on the loop would pass the tests.
**Fix:** Also patch `io.open` and `os.stat` with the same caller/thread check, or enable HA's `block_async_io` detector
in tests.

### IN-10: `monkeypatch.setattr(..., raising=False)` hides a renamed constant

**File:** `tests/test_source.py:38,53`
**Issue:** If `MAX_DOWNLOAD_BYTES` is renamed, `test_body_within_download_cap_loads` still passes without patching
anything.
**Fix:** Drop `raising=False`.

---

_Reviewed: 2026-10-14T11:07:53Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
