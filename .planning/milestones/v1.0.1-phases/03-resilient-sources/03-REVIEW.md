---
phase: 03-resilient-sources
reviewed: 2026-10-20T23:04:27Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - custom_components/xmltv_calendar/coordinator.py
  - tests/test_file_source.py
  - tests/test_refresh.py
  - tests/test_repairs.py
  - tests/test_schedule_refresh.py
findings:
  critical: 0
  warning: 1
  info: 7
  total: 8
status: issues_found
---

# Phase 3: Code Review Report (incremental re-review after 19e262d)

**Reviewed:** 2026-10-20T23:04:27Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

This is an incremental re-review of commit 19e262d, "fix(03): close source resilience warnings". Scope is `git diff 71d7d8f..HEAD` over the 5 listed files. That commit addressed WR-01, WR-04 and WR-05 from the previous report.

- I read `coordinator.py` in full, plus the helpers the changed code calls: `cache.py` `async_touch`, `schedule.py` `refresh_base`/`BACKOFF_STEPS`, the `parser.py` `keep_after` filter, and the `const.py` `KEEP_PAST`/`MAX_DECOMPRESSED_BYTES`.
- Ruff check and `ruff format --check` are clean on all 5 files.
- The 4 touched test modules pass: 45 tests.
- Side effect: `uv run` recreated the git-ignored `.venv` (it reported "Removed virtual environment"). No tracked file was modified.

No new blocker. The three warnings are fixed as dispositioned. One new warning concerns the WR-05 fix itself: it now swallows a parser crash on the cache with no trace. The remaining items are residuals of the fixes and test-strength gaps.

### Status of the previous findings

| Prior finding | Status | Evidence |
|---|---|---|
| WR-01 unchanged shortcuts skip the empty-feed check | **Fixed** (residual: IN-08) | `_require_programmes` now requires a programme with `stop >= utcnow() - KEEP_PAST` (`coordinator.py:446-447`). It runs on the 304 path (`:367`), the identical-body path (`:388`) and the unchanged-file path (`:434`), each before `async_touch`, so expired data neither refreshes `fetched_at` nor counts as a success. Covered by `test_refresh.py:328-354` (both variants) and `test_file_source.py:158-172`. |
| WR-04 swallowed `CancelledError` retries every second | **Fixed** (residual: IN-09) | A provisional target `max(served, now + BACKOFF_STEPS[0])` is set before any await (`coordinator.py:163-166`). Success and failure now take the original `served` target explicitly (`:146`, `:211`), so the CR-01 early-fire handling is intact. Manual refreshes keep their future target, because the `max` keeps `served`. Covered by `test_schedule_refresh.py:380-408`. |
| WR-05 unexpected cache-parse exception never downloads | **Fixed** (new issue: WR-06; residual: IN-10) | `_async_parse_cached` drops the cache on any `Exception` except `MemoryError` (`coordinator.py:323-330`), so the source falls through to a download. Covered by `test_repairs.py:159-181` and `:400-430`, and by `:433-455` for `MemoryError`. |
| IN-02 seeding before the final duplicate check | **Carried forward, open by disposition** | `config_flow.py` is not in this commit's scope, so it was not re-assessed. |
| IN-04 304 without data reads the cache without the source check | **Carried forward, open** | Still present at `coordinator.py:370-374`, see below. |
| IN-06 seeded `fetched_at` is the time of the name step | **Carried forward, open by disposition** | `config_flow.py`, out of scope, not re-assessed. |
| IN-07 test hygiene | **Carried forward, open** | `_raise_runtime_error` is still duplicated (`tests/test_repairs.py:123`, `tests/test_schedule_refresh.py:293`). The tautological assert at `tests/xmltv/test_schedule.py:182` is out of scope. |

## Narrative Findings (AI reviewer)

## Warnings

### WR-06: The WR-05 catch-all swallows a cache-parse crash without its type or traceback, and logs the drop twice

**File:** `custom_components/xmltv_calendar/coordinator.py:328-333`
**Issue:** The new `except Exception: # noqa: BLE001` branch logs only `"dropping a cache the parser could not read"` at DEBUG. There is no exception class and no `exc_info`. Before this commit, the same exception reached `_async_update_data` (`:174-183`), which logs the class name at WARNING and the traceback at DEBUG.

So after the WR-05 fix, a latent parser or coordinator bug that only the cached payload triggers now vanishes without a trace:

- The cache is deleted.
- The download parses a changed body fine (the scenario of `test_cache_parser_crash_recovers_from_changed_download`).
- Nothing is recorded in health or the Repairs issue, and nothing appears in the log at default level. Even DEBUG has no exception type.

That is exactly the "hidden latent bug" class CR-02 set out to make visible. The fix the previous review proposed included `exc_info=True`, but it was not applied.

A second, smaller problem is that the fall-through then logs `"dropping an unusable disk cache"` at `:332` for the same event. That is two DEBUG lines per drop, and an expected `UpdateFailed` (invalid or too large) cannot be told apart from an unexpected crash.

**Fix:** Keep expected parser failures quiet. Make unexpected ones visible by class name, keeping to the project's no-exception-text rule (T-03-28), and log the drop once:
```python
try:
    epg = await self._async_parse_payload(payload)
except MemoryError:
    raise
except UpdateFailed:
    epg = None  # invalid / too large: the drop below logs it
except Exception as err:  # noqa: BLE001 - poisoned caches must fall through to a new download (T-03-05)
    _LOGGER.warning(
        "Source %s: unexpected %s while parsing the disk cache; downloading again",
        self.config_entry.title,
        type(err).__name__,
    )
    _LOGGER.debug("Source %s: cache parse failure", self.config_entry.title, exc_info=err)
    epg = None
```
Add a `caplog` assertion to `test_cache_parser_crash_recovers_from_changed_download` that checks the class name is logged and the exception text is not.

## Info

### IN-04: A 304 without data in memory reads the cache without the source check (carried forward, still open)

**File:** `custom_components/xmltv_calendar/coordinator.py:370-374`
**Issue:** This code is unchanged. `_async_parse_cached()` reads whatever `self._cache.meta` points to, without `valid_meta(self._source_id)`. The branch is reachable only when a server answers 304 to a request that carried no validators.
**Fix:** Guard the branch with `if self._cache.valid_meta(self._source_id) is not None`, or treat a 304 to an unconditional request as `unable_to_fetch` right away.

### IN-07: Test hygiene (carried forward, partially in scope)

**File:** `tests/test_repairs.py:123`, `tests/test_schedule_refresh.py:293`
**Issue:** `_raise_runtime_error` is still defined identically in both modules. The commit also added a third ad-hoc raiser (`out_of_memory`, `tests/test_repairs.py:441-442`).
**Fix:** Move a parametrizable `raiser(exc)` helper to `tests/conftest.py`.

### IN-08: Expired-data detection lags by `KEEP_PAST`, so a stopped grabber still reports success for a day after the calendar runs dry

**File:** `custom_components/xmltv_calendar/coordinator.py:446-447`
**Issue:** "Current" means `stop >= now - KEEP_PAST`, which is 1 day (`const.py:75`). Take a feed whose last programme ends at time X:

- It keeps counting as a successful refresh until X + 24 h, even though the calendars have had no current or upcoming events since X.
- `failing_since` starts only at X + 24 h, so the Repairs issue (`PERSISTENT_FAILURE`, 24 h) appears at about X + 48 h.

WR-01's symptom, "calendars silently run out of events", is therefore cut down from forever to about one day, not removed. The cut-off matches the parser's retention window, which is a deliberate choice. It is still not what the user-facing text says: "the feed contains no current programmes".

A related inconsistency is that `_async_parse_cached` (`:331`) still tests `not epg.programmes` rather than the same predicate. That works only because the parser already filters with the same cut-off. The two definitions of a usable feed can drift apart. The docstring at `:441` still says "when it holds programmes".
**Fix:** Optional. Require a programme that has not ended yet: `any(p.stop > dt_util.utcnow() for p in epg.programmes)`. Use the same helper in `_async_parse_cached`, and update the docstring. If the 1-day grace is intended, document it in D-20 and in the docstring.

### IN-09: A persistently swallowed `CancelledError` now retries every 5 min forever, with no escalation and no record

**File:** `custom_components/xmltv_calendar/coordinator.py:163-166` (encoded by `tests/test_schedule_refresh.py:405`)
**Issue:** The provisional target removes the 1 s loop. Each swallowed cancellation still re-arms at a fixed `BACKOFF_STEPS[0]`. `consecutive_failures` never grows, the backoff never escalates past 5 min, it is not capped by the regular slot, and no Repairs issue is raised. For a daily source whose fetch keeps hitting an internal cancellation, that is about 288 attempts a day, invisible to health and diagnostics. The trigger is rare: an inner future or executor job cancelled while the refresh task itself is not.
**Fix:** Optional. Escalate the provisional target without recording a failure, for example with a private `self._cancel_streak` counter feeding `backoff_delay(self._cancel_streak, now, next_regular(...))`, reset on success or failure. Alternatively, accept the residual and note it in the `_async_update_data` docstring.

### IN-10: `MemoryError` on the cache keeps the payload, but the entry stays in SETUP_RETRY with no download

**File:** `custom_components/xmltv_calendar/coordinator.py:325-327` (encoded by `tests/test_repairs.py:433-455`)
**Issue:** The "offline fallback" survives only on disk. While the `MemoryError` repeats, no calendar is shown and nothing is downloaded. A `MemoryError` caused by the payload itself is deterministic, for example a cache near `MAX_DECOMPRESSED_BYTES` (1 GiB) on a small LXC or an Odroid. That case reproduces the WR-05 lock-in for this one exception class, and a smaller upstream feed is never fetched. On Linux the OOM killer usually acts before Python raises `MemoryError`, so this is unlikely.
**Fix:** Optional. Drop the cache after N consecutive `MemoryError`s, using `health.consecutive_failures`. Alternatively, accept the trade-off and rename the test to say what it asserts: the cache survives on disk.

### IN-11: The WR-05 tests do not prove that the cache path was exercised and dropped

**File:** `tests/test_repairs.py:159-181`, `tests/test_repairs.py:400-430`
**Issue:**
- `test_cache_parser_crash_recovers_from_changed_download` would also pass if the cache were skipped entirely, for example if `valid_meta` returned `None`. The download alone yields "Tagesthemen" and `call_count == 1`. No assertion shows that the poisoned parse ran or that the cache was replaced with the changed body.
- `test_unexpected_cache_parse_failure_downloads_and_is_recorded` likewise does not check that the cache is gone afterwards (`await cache.async_read() is None`).
**Fix:**
- Count the poisoned-payload calls in `parse_except_poisoned` and assert that it ran once.
- Assert `await FeedCache(hass, cache_key(entry)).async_read() == changed` after recovery.
- Assert that the payload is absent after the failing variant.

### IN-12: `test_timer_cancelled_refresh_does_not_retry_every_second` relies on the frozen clock equalling the fire time exactly

**File:** `tests/test_schedule_refresh.py:399-400`
**Issue:** `assert coordinator.next_refresh_at == fired_at + timedelta(minutes=5)` holds only because `dt_util.utcnow()` inside the refresh is exactly `fired_at` under `freezer`. That is fine today. If the refresh ever reads time after a `freezer.tick` or an auto-tick, the test breaks for a reason unrelated to the behaviour. The property under test is "no retry before 5 min", which the later attempt-count loop already covers.
**Fix:** Optional. Assert `coordinator.next_refresh_at >= fired_at + timedelta(minutes=5)`, or keep the exact check but document the dependence on the frozen clock.

---

_Reviewed: 2026-10-20T23:04:27Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
