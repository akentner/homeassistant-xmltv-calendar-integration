---
phase: 04-automation-extras-release
reviewed: 2026-10-21T10:39:12Z
depth: standard
files_reviewed: 35
files_reviewed_list:
  - .github/workflows/release.yml
  - README.md
  - blueprints/automation/xmltv_calendar/notify_before_programme.yaml
  - custom_components/xmltv_calendar/__init__.py
  - custom_components/xmltv_calendar/cache.py
  - custom_components/xmltv_calendar/calendar.py
  - custom_components/xmltv_calendar/config_flow.py
  - custom_components/xmltv_calendar/const.py
  - custom_components/xmltv_calendar/coordinator.py
  - custom_components/xmltv_calendar/data.py
  - custom_components/xmltv_calendar/diagnostics.py
  - custom_components/xmltv_calendar/match_store.py
  - custom_components/xmltv_calendar/sensor.py
  - custom_components/xmltv_calendar/source.py
  - custom_components/xmltv_calendar/translations/de.json
  - custom_components/xmltv_calendar/translations/en.json
  - custom_components/xmltv_calendar/xmltv/matches.py
  - custom_components/xmltv_calendar/xmltv/settings.py
  - custom_components/xmltv_calendar/xmltv/window.py
  - tests/test_advanced_flow.py
  - tests/test_blueprint.py
  - tests/test_cache.py
  - tests/test_diagnostics.py
  - tests/test_init.py
  - tests/test_last_fetch_sensor.py
  - tests/test_new_match_event.py
  - tests/test_reconfigure.py
  - tests/test_repo_structure.py
  - tests/test_retention.py
  - tests/test_sensor.py
  - tests/test_source.py
  - tests/test_translations.py
  - tests/xmltv/test_matches.py
  - tests/xmltv/test_settings.py
  - tests/xmltv/test_window.py
findings:
  critical: 1
  warning: 1
  info: 6
  total: 8
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-10-21T10:39:12Z
**Depth:** standard
**Files Reviewed:** 35
**Status:** issues_found

## Summary

I reviewed the Phase 4 changes since `3dc625f`: the next-match and last-fetch sensors, the new-match event with its
persisted seen-set, past-match retention (match store), the refresh-run record in the cache Store, the diagnostics
additions, the blueprint, the release workflow, translations and README. Baseline checks: `uv run pytest -m "not
benchmark"` gives 981 passed and 1 skipped. `ruff check` is clean. en/de translation key sets are identical.

The persistence layer (`cache.py`, `match_store.py`, `xmltv/matches.py`) is careful. Its readers are tolerant, saves are
copy-on-write, and unload flushes. The main structural defect is that all per-calendar match state (filter result, index,
seen-set updates, retention capture) lives inside the calendar entity, while the next-match sensor and the new-match
event depend on it. When the calendar entity is disabled, those features stop working without any error (CR-01). The
second defect is a refilter race: a data refilter can supersede a filter-edit refilter. The edit is then treated as new
feed data, which fires new-match events and skips the retention re-check (WR-01). Everything else is low-impact
correctness or quality debt.

Severity mapping: Critical = **BLOCKER**. Warning and Info = **WARNING** (Info items are low-impact WARNINGs).

## Critical Issues

### CR-01: [BLOCKER] Disabling the calendar entity silently breaks the next-match sensor, the new-match event and retention

**File:** `custom_components/xmltv_calendar/calendar.py:140-153, 187-194, 415-416`, `custom_components/xmltv_calendar/sensor.py:115-134`, `custom_components/xmltv_calendar/__init__.py:61-74`

**Issue:** All filtering happens in `XmltvCalendarEntity._async_refilter`, which only runs from `async_added_to_hass`
and from coordinator listener callbacks. Its outputs are `_index`, `_feed_matches`, the match-store `put` (seen-set and
retained) and the event firing. If the user disables the calendar entity in the entity registry, HA's entity platform
skips it (`entity_platform.py`: "Not adding entity ... because it's disabled" → `add_to_platform_abort()`). The object
still goes into `runtime.calendars`, though, so:

- `NextMatchSensor._recompute` calls `calendar.next_match(now)` on an empty `MatchIndex(())`. The sensor stays
  `unknown` forever. README:164 says that means "the calendar has no upcoming match", which is false here.
- `xmltv_calendar_new_match` never fires, and the seen-set is never updated.
- `LastFetchSensor` reports `matches: 0`, and diagnostics report `matches: 0` / `retained: 0` for that calendar.
- Edits go to `async_apply_subentry`, which returns early at `if self.hass is None` (line 415), so they do nothing.

Disabling the calendar while keeping the "Next programme" sensor for automations is a normal thing to do. Nothing is
logged, and the README does not mention the coupling.

**Fix:** Move the per-calendar match state out of the entity into a small runtime object, created per subentry in
`async_setup_entry` / `_async_entry_updated`. It registers its own coordinator listener (`coordinator.async_add_listener`
with `entry.async_on_unload`) and owns `_async_refilter`, the index, the store writes and the event firing. The calendar
entity and both sensors then read from it:

```python
# data.py
@dataclass
class XmltvRuntimeData:
    ...
    matchers: dict[str, CalendarMatcher] = field(default_factory=dict)  # one per calendar subentry, entity-independent

# sensor.py
matcher = self._entry.runtime_data.matchers.get(self._subentry_id)
programme = matcher.next_match(now) if matcher is not None else None
```

If the refactor is out of scope, the minimum is to log a warning when a calendar subentry's entity is disabled. Also
document in the README that the next-match sensor and the new-match event require the calendar entity to be enabled.

## Warnings

### WR-01: [WARNING] A data refilter that supersedes a filter-edit refilter fires new-match events for the edit and skips the D-17 retention re-check

**File:** `custom_components/xmltv_calendar/calendar.py:236-244, 255-319, 417-418`

**Issue:** `async_apply_subentry` starts `_async_refilter(REFILTER_CONFIG)`. While that run is waiting on its executor
job, a coordinator refresh may deliver new data. `_handle_coordinator_update` then starts
`_async_refilter(REFILTER_DATA)`, which bumps `_generation`, so the CONFIG run is discarded at line 281. The DATA run
then:

- Computes `recheck = None` (line 272-276). The retained programmes and the previous run's matches that the *edited*
  filter no longer matches are not dropped (`allowed is None`, line 286). The old filter's ended matches are also
  captured into `retained` from `previous` (line 294). This violates D-17.
- Sets `fire = reason == REFILTER_DATA and self._baseline_ready` → `True`. Every programme the *new* filter matches that
  the old one did not is unseen, because the CONFIG run never reached `store.put`. Each one fires
  `xmltv_calendar_new_match`, up to 50. README:197-199 promises no events "when the calendar's filters are edited".

The docstring covers only the opposite order (config supersedes data). This order is not handled. The window is the
duration of a full-feed filter scan (up to about a second on big feeds), so it is narrow but deterministic once
triggered. When it hits, users get a burst of spurious notifications.

**Fix:** Make the config semantics stick until a refilter completes:

```python
# in async_apply_subentry, before awaiting
self._config_pending = True

# in _async_refilter
config = reason == REFILTER_CONFIG or self._config_pending
recheck = (... ) if config else None
...
if generation != self._generation:
    return
...
fire = reason == REFILTER_DATA and self._baseline_ready and not config
self._config_pending = False  # only after the run is applied
```

Add a test that blocks the executor job of a CONFIG refilter, pushes new coordinator data, and asserts that no
`xmltv_calendar_new_match` fires and that retained items failing the new filter are dropped.

## Info

### IN-01: [WARNING] Template-only edits trigger a full CONFIG refilter; the retention comparison is dead code

**File:** `custom_components/xmltv_calendar/calendar.py:390-402`

**Issue:** `refilter = retention_days != self._retention_days` (line 393) is overwritten by `refilter = True` at line 402
whenever the stored filter compiles, which is almost always. The comment at line 395 ("Templates only change the event
text: rebuilt without a refilter") is therefore wrong: every data edit, template-only ones included, runs a full feed
scan plus the retained re-check in the executor. It also opens the WR-01 race window on edits that cannot change the
matches.

**Fix:** Compare the new spec with the old one (or the filter-relevant keys of `subentry.data`) and set `refilter` only
when the filter or the retention changed:
`refilter = retention_changed or (spec is not None and spec != self._spec)`. `FilterSpec` needs `__eq__` on its source
values for this.

### IN-02: [WARNING] `http_status` is recorded as `None` for an oversized download that the server answered with 200

**File:** `custom_components/xmltv_calendar/coordinator.py:466-470`, `custom_components/xmltv_calendar/source.py:243-246`

**Issue:** `SourceTooLargeError(msg)` is raised after a successful response without `status=`, so
`run.http_status = err.status` stores `None`. The last-fetch sensor and diagnostics then show `failure_reason:
feed_too_large` with no HTTP status, although the server answered 200.

**Fix:** `raise SourceTooLargeError(msg, status=response.status)` in `async_fetch_url`.

### IN-03: [WARNING] A non-standard HTTP status (>= 600) makes the persisted run record unreadable after a restart

**File:** `custom_components/xmltv_calendar/source.py:235-238`, `custom_components/xmltv_calendar/cache.py:184-187`

**Issue:** `SourceUnavailableError(..., status=response.status)` stores any status >= 400. `RefreshAttempt.from_dict`
accepts only 100..599, and when one field is invalid it discards the whole record. After a restart, a source that
returned e.g. 999 (seen on some CDNs and anti-bot front ends) shows an unknown last-fetch sensor and `last_attempt: null`
in diagnostics.

**Fix:** Clamp or drop the value at capture time, for example
`status=response.status if response.status <= 599 else None`, so the writer never stores what the reader rejects.

### IN-04: [WARNING] The match-store fingerprint ignores Home Assistant's time zone when `naive_timezone` is `local`

**File:** `custom_components/xmltv_calendar/__init__.py:29-32`, `custom_components/xmltv_calendar/coordinator.py:412`

**Issue:** With `naive_timezone == "local"`, the parser interprets naive feed times in `dt_util.get_default_time_zone()`.
The fingerprint `{naive_timezone, offset_minutes}` does not include that zone. If the HA time zone changes, retained
programmes keep the old offsets and stay in the calendar at shifted times. README:145-146 only promises the drop for the
source's own timezone settings.

**Fix:** Add the effective zone to the fingerprint when it applies, for example
`"zone": str(dt_util.get_default_time_zone()) if options.naive_timezone == NAIVE_TZ_LOCAL else None`.

### IN-05: [WARNING] `failure_reason` attribute values have no state translations

**File:** `custom_components/xmltv_calendar/translations/en.json` (`entity.sensor.last_fetch.state_attributes.failure_reason`), `de.json` (same key)

**Issue:** `trigger`, `outcome` and `cache` get `state` translations, but `failure_reason` does not. The UI therefore
shows raw keys such as `unable_to_fetch` and `path_not_allowed`, including in a German UI. The vocabulary is closed
(`coordinator.FAILURE_REASONS`), so it can be translated.

**Fix:** Add `"state": {"unable_to_fetch": ..., "invalid_feed": ..., "feed_too_large": ..., "path_not_allowed": ...,
"file_not_found": ..., "empty_feed": ...}` in both files, and extend `tests/test_translations.py` to check it against
`FAILURE_REASONS`.

### IN-06: [WARNING] The blueprint's `title` variable holds the rendered summary, unlike `title` everywhere else

**File:** `blueprints/automation/xmltv_calendar/notify_before_programme.yaml:143`, `README.md:307-309`

**Issue:** In the new-match event and the next-match sensor, `title` is the raw feed title and `summary` is the rendered
event title (README:169-170, 207-208). The blueprint binds `title: "{{ trigger.calendar_event.summary }}"`, which with the
default template is `"Das Erste: Tatort"`. Custom actions that use `title` get the channel prefix. The default
notification then repeats the channel ("Das Erste: Tatort" / "Starts at 20:15 on Das Erste").

**Fix:** Rename the variable to `summary`, keeping `title` as an alias for compatibility if wanted, and document it.
Alternatively, state explicitly in the input description and the README that `title` is the rendered event title.

---

_Reviewed: 2026-10-21T10:39:12Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
