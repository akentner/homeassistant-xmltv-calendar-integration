---
phase: 03-resilient-sources
reviewed: 2026-10-16T17:48:42Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - custom_components/xmltv_calendar/config_flow.py
  - custom_components/xmltv_calendar/coordinator.py
  - custom_components/xmltv_calendar/xmltv/schedule.py
  - tests/test_config_flow.py
  - tests/test_identity.py
  - tests/test_repairs.py
  - tests/test_schedule_refresh.py
  - tests/xmltv/test_schedule.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 3: Code Review Report (incremental re-review after 03-09 / 03-10)

**Reviewed:** 2026-10-16T17:48:42Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

This is an incremental re-review of the gap-closure plans 03-09 (CR-01, CR-02) and 03-10 (WR-02, WR-03). Scope is `git diff 3687254..1a2fcca` over the 8 listed files. I read the changed files in full, together with the code they call: `cache.py` (`FeedCache.async_write`, `async_save_health`) and HA 2026.10.1 `helpers/update_coordinator.py` (`_schedule_refresh`, `_async_refresh`) and `config_entries.py` (`async_finish_flow`).

- Ruff is clean on all 8 files.
- The 5 touched test modules pass: 165 tests.
- I confirmed each new finding with a throwaway test against the real coordinator and HA's real timer, run in a scratch copy of the repo. The repo was not modified.

### Status of the previous findings in these files

| Prior finding | Status | Evidence |
|---|---|---|
| CR-01 early timer fire, slot served twice | **Resolved** | `refresh_base()` (`schedule.py:180-190`) is used in both `_set_regular_target` (`coordinator.py:142-146`) and `_async_handle_failure` (`coordinator.py:199-207`). Re-run of the original repro with HA's real timer: step to `16:14:59.99Z`, then `16:15:01Z`, then `16:15:03Z` gives exactly 1 extra download, and `next_refresh_at` moves to the next day. A manual refresh earlier than the 2 s tolerance still keeps the slot (`test_manual_refresh_before_slot_keeps_the_slot`). |
| CR-02 unexpected exception, 1 s retry loop, unrecorded | **Resolved for `Exception` subclasses** | `except Exception` at `coordinator.py:169-178` records the failure, backs off and re-raises it as `UpdateFailed`. One gap remains for `CancelledError`, see WR-04. |
| WR-01 "unchanged" shortcuts skip the empty-feed check | **Still open**, carried forward below | Not in the scope of 03-09 or 03-10. |
| WR-02 flow-seeded source has `last_success: None` | **Resolved** | `config_flow.py:357-366` saves `SourceHealth(last_success=fetched_at)` after a successful seed write. Covered by `test_config_flow.py:189-227`. Remaining nit: see IN-06. |
| WR-03 `test_identity.py` ran on the real clock | **Resolved** | `pytestmark = freeze_time(NOW)` (`test_identity.py:24-26`), plus `ConfigEntryState.LOADED` and single-download asserts. |
| IN-02 seeding before the duplicate check | **Still open** (Info), carried forward | The seed now also overwrites the Store's health. |
| IN-04 304 without data reads the cache without the source check | **Still open** (Info), carried forward | |
| IN-01, IN-03, IN-05 | **Not re-assessed** | They are in `__init__.py`, `cache.py` and `diagnostics.py`, which are outside this re-review's file scope. Their disposition stays as recorded. |

### New findings

Neither new warning is a regression introduced by the diff. Both are gaps that the CR-02 fix left open, and the new tests encode them as intended behaviour:

- **WR-04:** a `CancelledError` that HA swallows still produces the 1 s retry loop from CR-02.
- **WR-05:** an unexpected exception while parsing the disk cache never drops the cache, so the source never downloads and stays in SETUP_RETRY.

## Warnings

### WR-01: "Unchanged" shortcuts skip the empty-feed check, so a feed that stops updating is never reported (carried forward, still open)

**File:** `custom_components/xmltv_calendar/coordinator.py:355-359, 361-364, 370-379, 421-423`
**Issue:** This is unchanged since the previous review. `_require_programmes` (D-20) runs only after a fresh parse. A 304, an identical body, or an unchanged file returns the old `self.data` (or the re-parsed cache) and counts as a success.

A grabber or provider that stops updating therefore reports success forever:

- `consecutive_failures` stays 0.
- No Repairs issue is raised.
- Calendars silently run out of events once the last programme ends.

**Fix:** Before returning unchanged data, check that it still holds a current programme, using the parser's cut-off:
```python
def _still_current(epg: EpgData) -> bool:
    cutoff = dt_util.utcnow() - KEEP_PAST
    return any(p.stop >= cutoff for p in epg.programmes)

# in each unchanged branch (304, identical body, unchanged file)
if not _still_current(self.data):
    raise UpdateFailed(translation_domain=DOMAIN, translation_key="empty_feed")
```
Alternatively, store the feed's maximum `stop` on `EpgData` at parse time and compare against it.

### WR-04: A swallowed `CancelledError` on a timer-fired refresh still retries every second, unrecorded (CR-02 residual)

**File:** `custom_components/xmltv_calendar/coordinator.py:162-178` (test gap: `tests/test_schedule_refresh.py:590-613`)
**Issue:** The CR-02 fix deliberately lets `asyncio.CancelledError` pass. HA's `_async_refresh` (`update_coordinator.py:575-580`) only re-raises it when `asyncio.current_task().cancelling() > 0`. Otherwise it swallows the error, and its `finally` calls `_schedule_refresh()`.

On a timer-fired refresh, `_next_refresh_at` still holds the target that was just served, which is now in the past. `_schedule_refresh` then clamps the interval to `MIN_DELAY`, so the coordinator retries once per second indefinitely. That is the same loop CR-02 described: no failure is recorded, there is no backoff, and no Repairs issue is raised.

The trigger is a `CancelledError` that does not come from cancelling the refresh task itself, for example a cancelled inner future or executor job, or a library that raises it internally. That is rare, but the consequence is exactly the provider-hammering loop this phase set out to remove.

Verified with a throwaway test. `async_fetch_url` was patched to raise `CancelledError`, then time was stepped past the 24 h target in 2 s steps:

- 6 fetch attempts in 11 s.
- `consecutive_failures == 0`.
- `next_refresh_at` stayed at the past target `2026-10-14 06:00Z`.

`test_cancelled_refresh_records_no_failure` hides this. It runs a manual refresh at +1 h, when the target is still in the future, so asserting `next_refresh_at == target` looks safe there.
**Fix:** Make the default exit path safe. At the start of each refresh, set a provisional target, and pass the served target explicitly to the success and failure paths:
```python
async def _async_update_data(self) -> EpgData:
    served = self._next_refresh_at
    now = dt_util.utcnow()
    # Any exit that sets no target (a swallowed CancelledError) retries after the first backoff step, never every second
    self._next_refresh_at = max(served, now + BACKOFF_STEPS[0])
    ...
    # success:  self._next_refresh_at = next_regular(refresh_base(dt_util.utcnow(), served), self._schedule())
    # failure:  _async_handle_failure(reason, served) uses refresh_base(now, served)
```
`_async_start_from_cache` still overwrites the provisional target, so the stale-cache-at-start behaviour (`MIN_DELAY`) is unchanged. Also extend the cancellation test to a timer-fired refresh (`_step_to(target + 1 s)` and a few more steps), and assert that only one fetch happens.

### WR-05: An unexpected exception while parsing the disk cache keeps the cache, so the source never downloads and stays in SETUP_RETRY

**File:** `custom_components/xmltv_calendar/coordinator.py:193-196, 308-326` (behaviour encoded by `tests/test_repairs.py:356-378`)
**Issue:** `_async_parse_cached` drops the cache only on `UpdateFailed` or on an empty result. Any other exception propagates through `_async_start_from_cache`. CR-02's `except Exception` now records it and raises `UpdateFailed`, so setup ends in SETUP_RETRY.

Each setup retry builds a new coordinator with `self.data is None`. `_async_read_source` therefore goes back to the same cache every time, and the network path is never reached. The source stays stuck until someone deletes the cache file by hand:

- This happens even when the upstream feed has since changed.
- It also happens after a fixed transient condition.
- It defeats T-03-05, "a poisoned cache is never retried".

The setup-retry message also says "Unable to download the XMLTV feed", although no download was attempted.

Verified with a throwaway test: entry loaded, then unloaded, `parse` patched to raise `RuntimeError`, then three HA setup retries. Result: 4 cache parses, 0 downloads, state `SETUP_RETRY`. `test_unexpected_cache_parse_failure_is_recorded` asserts `call_count == 0`, which makes this the intended behaviour.

The behaviour existed before 03-09, because HA turned the raw exception into `ConfigEntryNotReady`. The new test now locks it in.
**Fix:** Treat an unexpected exception while parsing the cache as an unusable cache and fall through to the download. The download path then records a real failure if the bug persists:
```python
try:
    epg = await self._async_parse_payload(payload)
except UpdateFailed:
    epg = None
except MemoryError:
    raise  # transient: keep the offline fallback, retry later
except Exception:  # noqa: BLE001 - a cache that crashes the parser is poisoned (T-03-05)
    _LOGGER.debug("Source %s: the disk cache crashed the parser", self.config_entry.title, exc_info=True)
    epg = None
```
Trade-off: dropping on every exception, `MemoryError` included, is simpler. The cost is losing the offline fallback on a transient memory spike. Then update `test_unexpected_cache_parse_failure_is_recorded` to expect one download and a recorded failure from the parse of the downloaded body.

## Info

### IN-02: Cache seeding runs before the final duplicate check, and now also overwrites the Store's health (carried forward, still open)

**File:** `custom_components/xmltv_calendar/config_flow.py:333-335, 355-366`
**Issue:** `_async_seed_cache` writes the payload and Store under `self.unique_id` before `async_create_entry`.

- The window is small. HA's `async_finish_flow` (`config_entries.py:1846-1856`) aborts other in-progress flows with the same unique_id once one flow creates its entry. So only a second flow whose seed is already awaiting while the first one finishes can overwrite the live entry's files.
- In that case the WR-02 change also replaces the live entry's stored health with `SourceHealth(last_success=...)`, which wipes `failing_since` and `consecutive_failures` on disk until the live coordinator saves again.
- The key is still the raw unique_id, not `cache_key()`.

**Fix:** Call `self._abort_if_unique_id_configured()` again right before seeding. Derive the key through a shared helper (`cache_key_for(unique_id)`).

### IN-04: A 304 without data in memory reads the cache without the source check (carried forward, still open)

**File:** `custom_components/xmltv_calendar/coordinator.py:360-364`
**Issue:** This is unchanged. `_async_parse_cached()` reads whatever `self._cache.meta` points to without checking `valid_meta(self._source_id)`. The branch is reachable only when a server answers 304 to a request that carried no validators.
**Fix:** Guard with `if self._cache.valid_meta(self._source_id) is not None`, or treat a 304 to an unconditional request as `unable_to_fetch` right away.

### IN-06: The seeded `fetched_at` and `last_success` are the time of the name step, not of the download

**File:** `custom_components/xmltv_calendar/config_flow.py:357`
**Issue:** `fetched_at = dt_util.utcnow()` is taken when the user submits the name step. The download finished earlier, before the schedule and name steps, possibly minutes before. Two effects:

- Diagnostics and the Repairs text show a slightly late "last success".
- In daily mode, a slot that passes between the download and the name step counts as served. `is_fresh(fetched_at)` treats data downloaded before the slot as fetched after it, so that day's refresh is skipped until the next slot.

**Fix:** Record the time when the download task completes, for example `self._fetched_at = dt_util.utcnow()` next to `self._fetched = fetched` in `async_step_download` (`config_flow.py:271`). Use it for both the cache meta and the health.

### IN-07: Test hygiene in the new tests

**File:** `tests/test_repairs.py:122-124`, `tests/test_schedule_refresh.py:293-295`, `tests/xmltv/test_schedule.py:642-644`
**Issue:**
- `_raise_runtime_error` is duplicated in two test modules.
- `test_early_fire_tolerance` asserts that the constant equals its own literal (`timedelta(seconds=2) == S.EARLY_FIRE_TOLERANCE`). It adds no behavioural coverage. The parametrized `test_refresh_base` boundary cases already pin the tolerance.

**Fix:** Move the helper to `tests/conftest.py`. Drop the literal assert and keep only `EARLY_FIRE_TOLERANCE >= MIN_DELAY`, or drop the test entirely.

---

_Reviewed: 2026-10-16T17:48:42Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
