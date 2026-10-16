# Phase 3: Resilient Sources - Pattern Map

**Mapped:** 2026-10-16
**Files analyzed:** 22 (5 new source/test modules, 9 modified source files, 8 new/modified test files)
**Analogs found:** 21 / 22

All paths below are git-tracked (verified with `git ls-files`). Paths without a repo prefix are relative to
`/home/akentner/Projects/homeassistant-xmltv-calendar-integration/`. Sibling-repo analogs carry their repo name.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `custom_components/xmltv_calendar/schedule.py` (NEW) | utility (pure) | transform | `custom_components/xmltv_calendar/xmltv/timeparse.py` (pure, stdlib-only, test-first) | role-match |
| `custom_components/xmltv_calendar/cache.py` (NEW) | service (cache) | file-I/O | `homeassistant-kroki-integration/custom_components/kroki/cache.py` (files + `Store` metadata) | exact |
| `custom_components/xmltv_calendar/diagnostics.py` (NEW) | platform | request-response | `homeassistant-mqtt-actions-integration/custom_components/mqtt_actions/diagnostics.py` | exact |
| `custom_components/xmltv_calendar/coordinator.py` (MOD) | service (coordinator) | batch/polling | itself, lines 45-121 | exact (extend) |
| `custom_components/xmltv_calendar/source.py` (MOD) | service (HTTP/file) | request-response / file-I/O | itself, `async_fetch_url` lines 175-202 | exact (extend) |
| `custom_components/xmltv_calendar/config_flow.py` (MOD) | controller (flow) | request-response | itself, `async_step_url` 121-152, `_advanced_schema` 242-258, `_refresh_selector` 93-103 | exact (extend) |
| `custom_components/xmltv_calendar/__init__.py` (MOD) | lifecycle | event-driven | itself 139-177; cleanup analog `mqtt_actions/manager.py:427-434` | exact |
| `custom_components/xmltv_calendar/calendar.py` (MOD) | component (entity) | event-driven | itself 124-160 | exact (extend) |
| `custom_components/xmltv_calendar/const.py` (MOD) | config | — | itself 31-34 | exact |
| `custom_components/xmltv_calendar/data.py` (MOD, optional) | model | — | itself 192-202 | exact |
| `custom_components/xmltv_calendar/xmltv/timeparse.py` (MOD) | utility (pure) | transform | itself 30-60 | exact |
| `custom_components/xmltv_calendar/xmltv/parser.py` (MOD) | utility (pure) | streaming transform | itself `_programme` 78-96, `parse` 147+ | exact |
| `custom_components/xmltv_calendar/translations/{en,de}.json` (MOD) | config | — | existing `config.step.*`, `exceptions.*`, `selector.*` blocks | exact |
| `tests/conftest.py` (MOD) | test fixture | — | itself 27-30 (autouse fixture) | exact |
| `tests/test_schedule.py` (NEW) | test (pure) | — | `tests/xmltv/test_timeparse.py` | role-match |
| `tests/test_cache.py` (NEW) | test (HA) | file-I/O | `tests/test_ingestion.py` + `forbid_loop_io` (`tests/conftest.py:32-45`) | role-match |
| `tests/test_refresh.py` (NEW) | test (HA) | polling | `tests/test_ingestion.py:57-77` | exact |
| `tests/test_repairs.py` (NEW) | test (HA) | event-driven | `tests/test_ingestion.py:57-77` + `freezer` | role-match |
| `tests/test_diagnostics.py` (NEW) | test (HA) | request-response | none in repo; phcc `get_diagnostics_for_config_entry` | no repo analog |
| `tests/test_options_flow.py` (NEW) | test (flow) | request-response | `tests/test_config_flow.py`, `tests/test_reconfigure.py` | role-match |
| `tests/test_init.py`, `tests/test_config_flow.py`, `tests/test_calendar.py` (MOD) | test | — | themselves (Pitfall 2 in RESEARCH) | exact |
| `tests/xmltv/test_timeparse.py`, `tests/xmltv/test_parser.py` (MOD) | test (pure) | — | themselves | exact |

## Pattern Assignments

### `custom_components/xmltv_calendar/schedule.py` (utility, pure transform) — NEW

**Analog:** `custom_components/xmltv_calendar/xmltv/timeparse.py`
- Stdlib-only, never raises on bad input, module docstring, no HA imports.
- Purity note: `tests/xmltv/test_purity.py:7` only scans `LIBRARY = .../xmltv_calendar/xmltv`. `schedule.py` sits outside it. Either put it at `xmltv/schedule.py`, or add a second path to the purity test (copy `test_library_has_no_homeassistant_imports`, lines 19-28).
- Body: take RESEARCH.md Pattern 1 (`Schedule`, `last_slot`, `next_slot`, `is_fresh`, `backoff_delay`) as written. Arithmetic must happen in UTC (see the RESEARCH anti-patterns).
- Fallback convention to copy (timeparse.py:52): `tz = UTC  # D-14: no offset means UTC`. Decision IDs go in comments.

### `custom_components/xmltv_calendar/cache.py` (service, file-I/O) — NEW

**Analog:** `homeassistant-kroki-integration/custom_components/kroki/cache.py` (lines 1-60)

**Structure to copy** (binary files on disk plus metadata in `Store`, and an async factory that loads the metadata):
```python
from homeassistant.helpers.storage import Store
STORE_VERSION = 1

class KrokiCache:
    def __init__(self, hass, storage_dir: Path, max_size: int = 50) -> None:
        self._hass = hass
        self._storage_dir = storage_dir
        self._metadata: dict[str, dict] = {}
        self._store: Store = Store(hass, STORE_VERSION, STORE_KEY)

    @classmethod
    async def async_create(cls, hass, storage_dir, max_size=50):
        obj = cls(hass, storage_dir, max_size)
        await obj._async_initialize()
        return obj

    async def _async_initialize(self) -> None:
        await self._hass.async_add_executor_job(lambda: self._storage_dir.mkdir(parents=True, exist_ok=True))
        data = await self._store.async_load()
        self._metadata = data if isinstance(data, dict) else {}
```
Changes for this project:
- `Store(hass, 1, f"{DOMAIN}.{key}")` with one store per source. `key = entry.unique_id or entry.entry_id`, and never the URL.
- The payload path is `hass.config.cache_path(DOMAIN, f"{key}.feed")`. Write it with `homeassistant.util.file.write_utf8_file(path, payload, private=True, mode="wb")` in the executor, write the payload first, then `await store.async_save(...)` (Pitfall 5).
- The metadata includes `source_id` (compare it with `source.source_unique_id`, source.py:84-91), `size`, `etag`, `last_modified`, `fetched_at`, and the health fields (Pattern 6).
- Payload reads need builtin `open()` with `# noqa: PTH123`, as in source.py:148, so `forbid_loop_io` still catches loop IO.
- `async_remove()` unlinks the file in the executor (`missing_ok=True`) and then calls `Store.async_remove()`. The same call is used in `mqtt_actions/manager.py:427`.

### `custom_components/xmltv_calendar/diagnostics.py` (platform) — NEW

**Analog:** `homeassistant-mqtt-actions-integration/custom_components/mqtt_actions/diagnostics.py` (lines 1-60)

**Imports and allow-list style** (lines 10-20, 27-45):
```python
from typing import TYPE_CHECKING, Any
from homeassistant.components.diagnostics import async_redact_data
if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
TO_REDACT = frozenset({...})   # safety net; the result is built from an explicit allow-list
```
- Copy the docstring idea: "structure, never content". Build every key by name and run `async_redact_data` over the result as a safety net.
- Redacting `url`/`path` needs callables (RESEARCH Pattern 7: `_redact_url` returns scheme+host only, `_redact_path` returns the basename). Use `yarl.URL`, which source.py:15 already imports.
- Entry point: `async def async_get_config_entry_diagnostics(hass, entry: XmltvConfigEntry) -> dict[str, Any]`.
- Data comes from `entry.runtime_data.coordinator` (data.py:196), the `ParseStats` fields (xmltv/model.py:37-46), and `len(entity._index)` per calendar (calendar.py:120/154; `MatchIndex.__len__` is in xmltv/window.py:28). Expose a public `match_count` property instead of reading `_index`.
- Report presence only for ETag/Last-Modified, never the raw values.

### `custom_components/xmltv_calendar/coordinator.py` (coordinator) — MODIFY

**Analog:** itself.

**Constructor** (lines 50-58). Keep `config_entry=entry` and add `always_update=False` (RESEARCH Pattern 5):
```python
super().__init__(
    hass, _LOGGER, config_entry=entry, name=f"{DOMAIN}_{entry.title}",
    update_interval=timedelta(hours=entry.options.get(CONF_REFRESH_HOURS, DEFAULT_REFRESH_HOURS)),
)
```
- Missing keys fall back to defaults through `.get(KEY, DEFAULT)` (D-06). Use the same form for `refresh_mode`, `refresh_time`, `naive_timezone` and `offset_minutes`.

**Error mapping, the reason keys for Repairs and diagnostics** (lines 67-76, 100-121):
```python
except SourceTooLargeError as err:
    _LOGGER.debug("Source %s is too large: %s", self.config_entry.title, err)
    raise UpdateFailed(translation_domain=DOMAIN, translation_key="feed_too_large") from err
except SourceError as err:
    _LOGGER.debug("Source %s unavailable: %s", self.config_entry.title, err)
    raise UpdateFailed(translation_domain=DOMAIN, translation_key="unable_to_fetch") from err
...
@contextmanager
def _feed_errors(title: str) -> Iterator[None]:
    try:
        yield
    except FeedTooLargeError as err: ... translation_key="feed_too_large"
    except FeedError as err: ... translation_key="invalid_feed"
```
- The new D-20 failure follows the same form: `raise UpdateFailed(translation_domain=DOMAIN, translation_key="empty_feed")`.
- Logs stay at DEBUG and name the entry title, never the URL (Pitfall 8).

**Executor parse** (lines 77-85). Extend `partial(parse, ...)` with `naive_tz=` and `shift=`:
```python
return await self.hass.async_add_executor_job(
    partial(parse, io.BytesIO(payload), keep_after=dt_util.utcnow() - KEEP_PAST, default_duration=DEFAULT_DURATION)
)
```
- The decision skeleton, the `_schedule_refresh` override and health/Repairs come from RESEARCH.md "Coordinator decision skeleton" and Patterns 2, 3 and 6.
- The `@override` decorator convention is at lines 60-61.

**Repairs create/delete analog:** `homeassistant-mqtt-actions-integration/custom_components/mqtt_actions/manager.py:1343-1358`:
```python
ir.async_create_issue(
    self._hass, DOMAIN, ISSUE_NATIVE_CUTOVER_WAITING,
    is_fixable=False, severity=ir.IssueSeverity.WARNING,
    translation_key=ISSUE_NATIVE_CUTOVER_WAITING,
    translation_placeholders={"instances": instances},
)
...
ir.async_delete_issue(self._hass, DOMAIN, ISSUE_NATIVE_CUTOVER_WAITING)
```
- Here the issue id is `f"source_failing_{entry_id}"`, the key is `f"source_failing_{reason}"`, and the placeholders are `source` (title) and `last_success`. Import with `from homeassistant.helpers import issue_registry as ir`.

### `custom_components/xmltv_calendar/source.py` (HTTP/file) — MODIFY

**Analog:** itself, `async_fetch_url` lines 175-202:
```python
host = URL(url).host
session = async_get_clientsession(hass)
...
async with session.get(url, timeout=DOWNLOAD_TIMEOUT) as response:
    if response.status >= _HTTP_ERROR_MIN:
        _LOGGER.debug("Source host %s answered HTTP %s", host, response.status)
        raise SourceUnavailableError(f"HTTP {response.status} from {host}")
    stream = response.content  # bind once
    async for chunk in stream.iter_chunked(_CHUNK_SIZE):
        ... SourceTooLargeError cap ...
except (aiohttp.ClientError, TimeoutError) as err:
    _LOGGER.debug("Fetching from source host %s failed: %s", host, type(err).__name__)
    raise SourceUnavailableError(...) from None
```
- Add `headers=` built from `etag`/`last_modified` (`aiohttp.hdrs.IF_NONE_MATCH` / `IF_MODIFIED_SINCE`). Check `HTTPStatus.NOT_MODIFIED` **before** the `>= 400` check.
- Return `Fetched(payload, etag, last_modified)` or `NOT_MODIFIED` (RESEARCH Pattern 4). Validate the validators before using them (Pitfall 9).
- The call site at coordinator.py:70 needs updating, and so does the probe in config_flow.py:134.
- `async_probe_url` (101-130) is replaced by the full download in the flow. `looks_like_feed` (94-98) and `PROBE_BYTES` stay in use for the sniff.
- File mtime/size skip (D-11): add a stat helper next to `check_file` (133-142), executor only, with the same `real_path = check_file(config, path)` first.

### `custom_components/xmltv_calendar/config_flow.py` (flow) — MODIFY

**Analog:** itself.

**Selector builder style** (lines 93-103). Copy it for the offset-minutes selector (−720..720, `unit_of_measurement="min"`):
```python
def _refresh_selector() -> NumberSelector:
    return NumberSelector(NumberSelectorConfig(min=MIN_REFRESH_HOURS, max=MAX_REFRESH_HOURS, step=1,
                                               mode=NumberSelectorMode.BOX, unit_of_measurement="h"))
```
**Translated select options** (`_list_selector`, lines 233-240, `translation_key=`). Copy for `refresh_mode` and `naive_timezone`.

**Step with errors and re-suggest** (lines 121-152). The setup `url`/`file` steps keep this skeleton. `async_probe_url` becomes the move to `async_step_download`:
```python
errors: dict[str, str] = {}
if user_input is not None:
    ... normalize, async_set_unique_id(source_unique_id(...)); self._abort_if_unique_id_configured()
    ... self._data = {...}; self._options = {...}
schema = vol.Schema({...})
if user_input is not None:
    schema = self.add_suggested_values_to_schema(schema, user_input)
return self.async_show_form(step_id="url", data_schema=schema, errors=errors)
```
- Store the progress-step error on `self` and re-show the url step with the last input (RESEARCH Pattern 9).

**Final step = cache seed point** (lines 190-203). Write the cache right before `self.async_create_entry(title=name, data=self._data, options=self._options)`, keyed by `self.unique_id`.

**TimeSelector precedent:** `_advanced_schema` lines 249-250 (`vol.Optional(CONF_TIME_FROM): TimeSelector()`). Normalize the value with `xmltv/settings.py` `normalize_time` (lines 65-73), as Phase 2 does.

**Options-flow registration:** add it next to the existing `async_get_supported_subentry_types` classmethod (line 207). Use `@staticmethod @callback def async_get_options_flow(config_entry) -> XmltvOptionsFlow`. `callback` is already imported (line 15). Subclass plain `OptionsFlow` (add it to the `homeassistant.config_entries` import, lines 7-14) and never `OptionsFlowWithReload`. Multi-step state lives on `self` (as `CalendarSubentryFlow.__init__` does, lines 332-337), and `self.config_entry` is not used in `__init__`.

### `custom_components/xmltv_calendar/__init__.py` (lifecycle) — MODIFY

**Analog:** itself (lines 139-177).
- `async_setup_entry` (139-150) stays as it is: the first refresh goes through `coordinator.async_config_entry_first_refresh()`, and stale-while-revalidate lives inside the coordinator. If needed, load the cache before it with `await FeedCache.async_create(...)`.
- `_async_entry_updated` (153-158) already reloads when options change, so it does not need to change (D-07).
- New `async_remove_entry(hass, entry)`. Analog: `mqtt_actions/manager.py:427-434`:
```python
await Store(hass, STORE_VERSION, store_key).async_remove()
...
ir.async_delete_issue(hass, domain, issue_id)
```

### `custom_components/xmltv_calendar/calendar.py` (entity) — MODIFY

**Analog:** itself (lines 129-160):
```python
@callback
@override
def _handle_coordinator_update(self) -> None:
    """Re-filter in the executor on every coordinator update."""
    self._entry.async_create_task(self.hass, self._async_refilter(), name=f"{DOMAIN} refilter {self.entity_id}")
```
- Add an identity guard: when `self.coordinator.data is <last filtered epg>`, only call `self.async_write_ha_state()`. The epg is read at line 139, so store it there.
- Add an `@property @override def available(self) -> bool: return self.coordinator.data is not None`, using the same decorator stack.
- Add a `match_count` property over `self._index` for diagnostics.

### `custom_components/xmltv_calendar/const.py` — MODIFY

**Analog:** lines 31-34:
```python
CONF_REFRESH_HOURS = "refresh_hours"
DEFAULT_REFRESH_HOURS = 24  # D-13
MIN_REFRESH_HOURS = 1
MAX_REFRESH_HOURS = 168
```
- Add `CONF_REFRESH_MODE`, `REFRESH_MODE_INTERVAL/DAILY`, `CONF_REFRESH_TIME`, `CONF_NAIVE_TZ`, `NAIVE_TZ_UTC/LOCAL`, `CONF_OFFSET_MINUTES`, `DEFAULT_OFFSET_MINUTES = 0`, `MIN/MAX_OFFSET_MINUTES = ∓720` in the same block.
- The stored key strings follow D-06 and RESEARCH A2. Lock them in the plan.

### `xmltv/timeparse.py` and `xmltv/parser.py` (pure) — MODIFY

- `parse_xmltv_time(value)` (timeparse.py:30) gets `naive_tz: tzinfo = UTC`, and line 52 becomes `tz = naive_tz`.
- `_programme(elem)` (parser.py:78-85, calls at 80 and 85) and `parse(...)` (147) get `naive_tz` and `shift` keyword parameters. Apply `shift` in UTC only, and only if it is truthy.
- With the default arguments, output must stay bit-for-bit what it is today.

### Translations — MODIFY

- Mirror every new key in `translations/en.json` and `translations/de.json`. Parity is enforced by `tests/test_translations.py`.
- Shapes are in the RESEARCH "Translation skeleton": `config.progress.download`, `options.step.{init,schedule}` with `sections.timezone`, `issues.source_failing_<reason>` for each of the 6 reasons, `exceptions.empty_feed`, `selector.refresh_mode` / `selector.naive_timezone`, and the new flow error `feed_too_large`.

### Tests

- **`tests/conftest.py`:**
  - Add the autouse override in the style of lines 27-29: `@pytest.fixture(autouse=True) def hass_config_dir(hass_tmp_config_dir: str) -> str: return hass_tmp_config_dir` (Pitfall 1).
  - `setup_xmltv` (54-80) is the factory to extend with `options=` and a pre-seeded cache.
- **`tests/test_refresh.py` / `test_repairs.py`:** copy `tests/test_ingestion.py:57-77`:
```python
freezer.move_to("2026-10-13T00:00:00+00:00")
entry = await setup_xmltv(payload)
coordinator = entry.runtime_data.coordinator
previous = coordinator.data
aioclient_mock.clear_requests()
aioclient_mock.get(FEED_URL, content=..., headers=OCTET_STREAM)
await coordinator.async_refresh()
assert aioclient_mock.call_count == 1
assert coordinator.last_update_success is False
assert coordinator.last_exception.translation_key == "invalid_feed"
assert coordinator.data is previous
```
  - Check the sent headers with `aioclient_mock.mock_calls[-1][3]`.
  - Advance the schedule with `freezer.tick` plus `async_fire_time_changed`.
  - Check Repairs with `ir.async_get(hass).async_get_issue(DOMAIN, f"source_failing_{entry.entry_id}")`.
- **`tests/test_cache.py`:** use the `forbid_loop_io` fixture (conftest.py:32-45) for every cache read/write test.
- **`tests/test_schedule.py`:** pure, test-first, no `hass`. Model it on `tests/xmltv/test_timeparse.py`, with DST cases for Europe/Berlin through `zoneinfo`.
- **`tests/test_options_flow.py`:** flow-driving style from `tests/test_config_flow.py` / `tests/test_reconfigure.py`. Run `hass.config_entries.options.async_init(entry.entry_id)` → configure `init` → configure `schedule` → assert `entry.options`, and assert one reload as in `tests/test_init.py:121-138`.
- **Existing tests to update deliberately:** `test_init.py:121-138`, `test_calendar.py:30-35, 266-281`, and `test_config_flow.py:153-199`. Keep `test_ingestion.py:57-77` green.

## Shared Patterns

### Error → translation key
**Source:** `coordinator.py:67-121`. **Apply to:** coordinator, Repairs keys, diagnostics `last_failure.reason`, and the flow's `errors["base"]`.
- Errors are always raised as `UpdateFailed(translation_domain=DOMAIN, translation_key=...)`.
- The `.translation_key` doubles as the reason string.

### Host-only logging, no URL anywhere
**Source:** `source.py:1-6` (module docstring), 177, 185, 198. **Apply to:** source, cache, coordinator, diagnostics and issue placeholders.
- Log `URL(url).host` only.
- Cache and Store keys use the hashed `unique_id`.

### Executor-only blocking IO
**Source:** `coordinator.py:78, 91` (`hass.async_add_executor_job(partial(...))`), and `source.py:148` builtin `open` with `# noqa: PTH123`. **Apply to:** cache payload read/write/unlink, file stat, and parsing.

### Missing key = default, no migration
**Source:** `coordinator.py:57` `entry.options.get(CONF_REFRESH_HOURS, DEFAULT_REFRESH_HOURS)`. **Apply to:** all new option keys (D-06), in the coordinator, the options-flow defaults and diagnostics.

### Single diffing reload listener
**Source:** `__init__.py:153-158`. **Apply to:** the options flow. Saving with `async_create_entry(data=full_options)` is enough. Do not add a second listener or use `OptionsFlowWithReload`.

### Decorators and typing
- `@callback` + `@override` on overridden HA hooks (calendar.py:129-131).
- `TYPE_CHECKING`-only imports for `HomeAssistant` and `XmltvConfigEntry` (coordinator.py:35-40).
- Ruff `ALL`, 120 columns.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `tests/test_diagnostics.py` | test | request-response | No diagnostics tests in this repo. Use phcc `pytest_homeassistant_custom_component.components.diagnostics.get_diagnostics_for_config_entry(hass, hass_client, entry)` once, and otherwise call `async_get_config_entry_diagnostics` directly (RESEARCH Standard Stack) |

Partial gaps (no in-repo analog; use RESEARCH patterns):
- **`async_show_progress` download step:** RESEARCH Pattern 9. No local or sibling-repo usage was found in tracked code.
- **`_schedule_refresh` override:** RESEARCH Pattern 2.

## Metadata

**Analog search scope:**
- this repo: `custom_components/xmltv_calendar/**`, `tests/**`
- `/home/akentner/Projects/homeassistant-*/custom_components` (mqtt-actions, kroki, traefik, condition-gate)

**Files scanned:** ~30
**Pattern extraction date:** 2026-10-16
