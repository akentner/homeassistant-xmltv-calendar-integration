---
phase: 04-automation-extras-release
reviewed: 2026-10-23T12:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - custom_components/xmltv_calendar/__init__.py
  - custom_components/xmltv_calendar/calendar.py
  - custom_components/xmltv_calendar/data.py
  - custom_components/xmltv_calendar/diagnostics.py
  - custom_components/xmltv_calendar/manifest.json
  - custom_components/xmltv_calendar/matcher.py
  - custom_components/xmltv_calendar/sensor.py
  - custom_components/xmltv_calendar/translations/de.json
  - custom_components/xmltv_calendar/translations/en.json
  - tests/test_matcher_races.py
  - tests/test_matcher_runtime.py
  - tests/test_translations.py
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: issues_found
---

# Phase 4: Code Review Report (re-review after gap closure 04-09..04-11)

**Reviewed:** 2026-10-23T12:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

This is an incremental re-review of the gap-closure work (plans 04-09..04-11) against base `1226412`. Per-calendar match
state moved out of `XmltvCalendarEntity` into the runtime-owned `CalendarMatcher` (`matcher.py`). The matcher registers
its own coordinator and STOP listeners, resolves its entity ID from the entity registry, and serializes commits behind
an `asyncio.Lock`. Sensors and diagnostics now read the matcher.

Baseline checks run during this review: `ruff check custom_components tests` is clean. The three in-scope test modules
(`test_matcher_races.py`, `test_matcher_runtime.py`, `test_translations.py`) give 55 passed.

Severity mapping: Critical = **BLOCKER**. Warning and Info = **WARNING** (Info items are low-impact WARNINGs).

### Resolution of the previous findings

| ID | Previous finding | Status |
|----|------------------|--------|
| CR-01 | Disabled calendar entity breaks sensor, event and retention | **Resolved.** Matching, store writes and event firing live in `CalendarMatcher`, which is started in `async_setup_entry` before platform admission. The entity ID comes from the registry (`matcher.py:177-180`), so disabled and renamed calendars still fire with the right ID. `tests/test_matcher_runtime.py` covers disabled calendars, disabled edits and re-enable. |
| WR-01 | A DATA refilter supersedes a CONFIG refilter (spurious events, skipped D-17 re-check) | **Resolved.** The edit is now a `_ConfigSnapshot` in `_pending_config`. It carries its own feed snapshot and recheck set, and DATA cannot cancel it. The DATA caller resumes with newer data after the silent baseline. I traced the four orderings in `test_newer_edit_keeps_pending_config_semantics`, and the `revision` / `generation` / superseded-data `continue` branches in `_async_refilter` (`matcher.py:232-282`). They hold. |
| IN-01 | Template-only edits trigger a full refilter | **Resolved.** `refilter = refilter or spec != self._spec` compares compiled specs (`matcher.py:421`). `test_template_only_edit_does_not_scan` asserts zero scans. |
| IN-05 | No `failure_reason` state translations | **Resolved.** en/de both carry all six `FAILURE_REASONS`. `tests/test_translations.py` derives the required keys from `coordinator.FAILURE_REASONS`, and a paired omission is still caught. |
| IN-04 | Match-store fingerprint ignores HA time zone | **Still open** (WR-03 below). |
| IN-02 | `http_status` None for oversized 200 download | **Still open** (`source.py:246`, outside this scope; untouched since `1226412`). |
| IN-03 | Status >= 600 makes run record unreadable | **Still open** (`source.py:238`, outside this scope; untouched). |
| IN-06 | Blueprint `title` holds the rendered summary | **Still open** (`blueprints/.../notify_before_programme.yaml:77`, outside this scope; untouched). |

No new Critical findings. The new defects are lifecycle and compatibility issues around the matcher, plus leftover
test-only code in production modules.

## Warnings

### WR-01: [WARNING] Matchers leak (listeners, polling, event firing) when entry setup fails after they started

**File:** `custom_components/xmltv_calendar/__init__.py:48-56`, `custom_components/xmltv_calendar/matcher.py:153-161`

**Issue:** `async_setup_entry` starts every matcher (coordinator listener and `EVENT_HOMEASSISTANT_STOP` listener)
before `async_forward_entry_setups`. Their teardown exists only in `async_unload_entry`. When setup raises after the
first matcher has started, HA does not call `async_unload_entry`. The `async_setup` error path runs
`_async_process_on_unload` only (`config_entries.py:1003-1005`). Two triggers reach this path:

- `await matcher.async_start()` raises for a later subentry, e.g. an executor error in `_apply_filter`.
- `async_forward_entry_setups` raises.

The already-started matchers keep their coordinator listener. `entry.runtime_data` is not deleted on a failed setup, so
`_is_current()` stays true. Those matchers keep the source polling and keep refiltering. They can keep firing
`xmltv_calendar_new_match` for an entry in `SETUP_ERROR` or `SETUP_RETRY`. A retry then builds a second runtime with
second matchers on a new coordinator, and both fire events.

**Fix:** Tie matcher teardown to the entry's unload callbacks, as is already done for the update listener:

```python
entry.runtime_data = XmltvRuntimeData(...)
entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
entry.async_on_unload(
    lambda: [m.async_stop(capture=False) for m in entry.runtime_data.matchers.values()]
)
```

Capturing the matchers is still done in `async_unload_entry` before the flush. Because `async_stop` is idempotent, the
extra callback is harmless on a successful unload. Alternatively, wrap the start loop in `try/except` and stop the
matchers started so far before re-raising.

### WR-02: [WARNING] `async_get_device_by_identifier` is used although `hacs.json` promises HA 2026.3.0

**File:** `custom_components/xmltv_calendar/matcher.py:429-432`, `hacs.json`

**Issue:** The device rename on a calendar title edit calls `registry.async_get_device_by_identifier(...)`. In the
installed HA 2026.10.1 this method is the replacement for the deprecated `async_get_device`. The deprecation carries
`breaks_in_ha_version="2027.8.0"`, so the replacement is recent. The integration declares a floor of 2026.3.0
(`hacs.json`). I could only inspect 2026.10.1 offline, so I cannot prove the exact version that introduced the method.
It very likely does not exist on the older versions the floor admits. On those versions, renaming a calendar raises
`AttributeError` inside the update listener.

The listener has already stored `self._subentry_title` and `_subentry_data` before this call. The `if refilter:` block
below it is then skipped, so a filter edit saved together with the rename is not applied until a reload. The new
`differs_from` check also reports "no difference", so nothing retries.

**Fix:** Use an API that exists across the supported range. For example, scan the entry's devices:

```python
registry = dr.async_get(self.hass)
device = next(
    (d for d in dr.async_entries_for_config_entry(registry, self._entry.entry_id)
     if (DOMAIN, self._subentry_id) in d.identifiers),
    None,
)
```

Alternatively, raise the `hacs.json` floor to the first release that has the method and document it, and add a test
that fails if the floor and the used API diverge.

### WR-03: [WARNING] (carried over, IN-04) Match-store fingerprint ignores the HA time zone when `naive_timezone` is `local`

**File:** `custom_components/xmltv_calendar/__init__.py:31-35`

**Issue:** Unchanged since the previous review. With `naive_timezone == "local"` the parser reads offset-less feed
times in `dt_util.get_default_time_zone()`. The fingerprint passed to `match_store.async_load` contains only
`naive_timezone` and `offset_minutes`. After a change of the HA time zone, the stored retained programmes keep their old
offsets and stay in the calendar at shifted times for up to the retention window (default 3 days, up to the configured
maximum).

**Fix:**

```python
fingerprint = {
    "naive_timezone": options.naive_timezone,
    "offset_minutes": options.offset_minutes,
    "zone": str(dt_util.get_default_time_zone()) if options.naive_timezone == NAIVE_TZ_LOCAL else None,
}
```

A changed fingerprint already drops `retained` and keeps `seen`, so no other change is needed.

## Info

### IN-01: [WARNING] Production `XmltvCalendarEntity` carries about 45 lines of test-only compatibility facade

**File:** `custom_components/xmltv_calendar/calendar.py:104-149`, `custom_components/xmltv_calendar/data.py:29`

**Issue:** `next_match`, `describe_match`, `match_count`, `retained_count`, `differs_from`, `async_apply_subentry`, the
`_index` property with a setter that writes `matcher._index`, and the read properties `_spec`, `_feed_matches` and
`_retained_shown` are referenced only from tests (`tests/test_calendar.py:147`, `test_retention.py:365-366`,
`test_reconfigure.py:227-231`). Production code uses the matcher directly. The facade needs five
`# noqa: SLF001` suppressions and keeps a second public surface that can drift from the matcher. `runtime.calendars`
now stores entities only so `subentry_id in runtime.calendars` works as a "presentation added" flag.

**Fix:** Port those tests to `runtime.matchers[sid]` and delete the facade. Reduce `runtime.calendars` to a
`set[str]`, as is done for `runtime.sensors`.

### IN-02: [WARNING] `sensor.py` imports `device_info` and `signal_matches` through `calendar.py`

**File:** `custom_components/xmltv_calendar/sensor.py:14`

**Issue:** The two helpers now live in `matcher.py`. `sensor.py` still imports them from `.calendar`, which only
re-imports them. Ruff accepts this because they are used. It is an implicit re-export, which `mypy --strict` rejects
(`implicit_reexport`), and it couples the sensor platform to the calendar platform module for no reason.

**Fix:** `from .matcher import device_info, signal_matches`.

### IN-03: [WARNING] A pending filter edit whose feed snapshot is `None` can never complete

**File:** `custom_components/xmltv_calendar/matcher.py:436-440, 239-241`

**Issue:** `async_apply_subentry` snapshots `epg=self.coordinator.data`. If that is `None`, `_async_refilter` takes
`epg = change.epg`, hits `if epg is None: return`, and leaves `_pending_config` and `_config_pending` set. Every later
DATA call re-reads the same `None` snapshot and returns, so the matcher would stop following the feed. This is not
reachable today: `async_config_entry_first_refresh` guarantees data before matchers exist, and the coordinator keeps its
last data on failure. It is a latent trap if the coordinator ever clears `data`.

**Fix:** Fall back to the live data when the snapshot has none:
`epg = (change.epg if change is not None else None) or self.coordinator.data`.

### IN-04: [WARNING] New matches that arrive in a refresh are announced silently if a filter edit lands during that refresh's refilter

**File:** `custom_components/xmltv_calendar/matcher.py:266-279`

**Issue:** If a filter-affecting edit lands while a DATA worker for feed D2 is in the executor, the edit's snapshot
epg is `coordinator.data`, which is already D2. The DATA worker is discarded on the revision bump. The CONFIG commit
then adds every D2 match under the new filter to `seen` without firing, and the follow-up DATA pass returns because
`epg is self._epg`. Programmes that D2 newly brought in, and that match both the old and the new filter, are never
announced. The window is the length of one filter scan, and this follows the D-10 "edits are silent" rule, so it is a
design limitation rather than a regression.

**Fix:** Optional. Document it, or compute the new-match set with the pre-edit spec for the D2 pass. Today the README
promises "no events when the filters are edited" but does not mention that a coinciding refresh is swallowed too.

### IN-05: [WARNING] Duplicated, diverging `_held_filter` helper in two test modules

**File:** `tests/test_matcher_races.py:40-67`, `tests/test_matcher_runtime.py:161-188`

**Issue:** Two copies of the executor gate exist. The races copy uses a thread event plus an async event and an
`entered.is_set()` guard. The runtime copy uses a `first` flag. A fix to one gate (for example the 5 s wait) will not
reach the other. A hung gate would fail a test only after 5 s with an assertion raised in the executor thread, which
surfaces as an unrelated "task exception".

**Fix:** Move one implementation to `tests/conftest.py` as a fixture or a shared helper and import it in both modules.

---

_Reviewed: 2026-10-23T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
