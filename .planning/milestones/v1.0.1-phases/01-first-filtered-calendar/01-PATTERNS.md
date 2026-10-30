# Phase 1: First Filtered Calendar - Pattern Map

**Mapped:** 2026-10-12
**Files analyzed:** 30 (incl. test files and scaffold)
**Analogs found:** 22 / 30

Notation: `MQ` = `/home/akentner/Projects/homeassistant-mqtt-actions-integration` (all paths git-tracked).
`HA` = `MQ/.venv/lib/python3.14/site-packages/homeassistant` (installed HA core source, read-only reference, not a project file. Planner cites it, executor never edits it).

## File Classification

| New File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `pyproject.toml` | config | - | `MQ/pyproject.toml` | exact |
| `.ruff.toml` | config | - | `MQ/.ruff.toml` | exact |
| `hacs.json` | config | - | `MQ/hacs.json` | exact |
| `renovate.json` | config | - | `MQ/renovate.json` | exact |
| `.gitignore` | config | - | `MQ/.gitignore` | exact (merge) |
| `LICENSE`, `README.md` | docs | - | `MQ/LICENSE`, `MQ/README.md` | exact / role |
| `.github/workflows/ci.yml` | CI | batch | `MQ/.github/workflows/ci.yml` | exact (drop broker/multi-instance jobs, add benchmark job) |
| `.github/workflows/validate.yml` | CI | batch | `MQ/.github/workflows/validate.yml` | exact |
| `custom_components/xmltv_calendar/manifest.json` | config | - | `MQ/custom_components/mqtt_actions/manifest.json` | exact |
| `.../__init__.py` | setup/lifecycle | event-driven (update listener) | `MQ/custom_components/mqtt_actions/__init__.py` | exact |
| `.../const.py` | config | - | `HA/components/remote_calendar/const.py` + MQ `const.py` | role |
| `.../data.py` | model | - | `HA/components/remote_calendar/coordinator.py:20` (typed entry alias) | partial |
| `.../coordinator.py` | service | request-response (poll) | `HA/components/remote_calendar/coordinator.py` | exact |
| `.../source.py` | service | file-I/O + HTTP | `HA/components/remote_calendar/coordinator.py:53-83` (error mapping) | partial |
| `.../calendar.py` | component (entity) | event-driven + request-response | `HA/components/remote_calendar/calendar.py` | exact |
| `.../config_flow.py` | controller (flow) | request-response | `MQ/custom_components/mqtt_actions/config_flow.py` + `HA/components/remote_calendar/config_flow.py` | exact |
| `.../translations/en.json` | config | - | `MQ/custom_components/mqtt_actions/translations/en.json` | exact |
| `.../brand/icon.png`, `icon@2x.png` | asset | - | `MQ/custom_components/mqtt_actions/brand/` | exact |
| `.../xmltv/timeparse.py` | utility (pure) | transform | none (RESEARCH.md Code Examples) | none |
| `.../xmltv/model.py` | model (pure) | - | none | none |
| `.../xmltv/parser.py` | utility (pure) | streaming | none (RESEARCH.md "Streaming parse loop skeleton") | none |
| `.../xmltv/filter.py` | utility (pure) | transform | none | none |
| `.../xmltv/render.py` | utility (pure) | transform | `HA/components/remote_calendar/calendar.py:135-155` (CalendarEvent build) | partial |
| `tests/conftest.py` | test | - | `MQ/tests/conftest.py` | exact |
| `tests/test_repo_structure.py` | test | - | `MQ/tests/test_repo_structure.py` | exact |
| `tests/test_config_flow.py`, `test_init.py`, `test_calendar.py`, `test_source.py` | test | - | `MQ/tests/test_config_flow.py` (structure) + RESEARCH.md harness | role |
| `tests/xmltv/test_*.py`, `test_purity` | test (pure) | - | none (plain pytest) | none |
| `tests/test_benchmark.py`, `scripts/generate_benchmark_feed.py` | test/tool | batch | none | none |

## Pattern Assignments

### `pyproject.toml` — copy `MQ/pyproject.toml` (lines 1-23)
```toml
[project]
name = "homeassistant-mqtt-actions-integration"   # -> homeassistant-xmltv-integration
version = "0.0.0"
requires-python = ">=3.14.2"
dependencies = []

[tool.uv]
package = false

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--strict-markers"
markers = [ ... ]          # -> ["benchmark: generates a 60 MB feed; slow"]

[dependency-groups]
dev = [
    "pytest-homeassistant-custom-component==0.13.367",   # -> ==0.13.372
    "ruff==0.16.10",                                    # -> ==0.17.0
]
```
Then `uv lock` to create `uv.lock`.

### `.ruff.toml` — copy `MQ/.ruff.toml` verbatim (lines 1-44)
Key lines: `target-version = "py314"`, `line-length = 120`, `extend-exclude = [".planning", ".claude"]`, `select = ["ALL"]`, ignore `ANN401, CPY001, D203, D212, COM812, ISC001`, tests per-file-ignores `S101, ANN, D, ARG, PLR0913, PLR0917, PLR2004, PLC0415, SLF001, PT018, FBT`, `max-complexity = 25`. Per RESEARCH Pitfall 10, add a targeted `# noqa: S314` on the `iterparse` call (not a global ignore).

### `hacs.json` — `MQ/hacs.json`
```json
{ "name": "MQTT Actions", "homeassistant": "2026.9.0" }
```
-> `"name": "XMLTV Calendar"`, `"homeassistant": "2026.3.0"` (see RESEARCH Assumption A3).

### `renovate.json` — copy `MQ/renovate.json` verbatim (phcc requires `dependencyDashboardApproval`).

### `.gitignore` — merge `MQ/.gitignore` (Python, tooling caches, `.gsd/`, `.planning/state.json`, `.planning/milestone.lock`) with this repo's existing `.planning/research/.cache/`. Add benchmark output path if generated outside `tmp_path`.

### `.github/workflows/ci.yml` — `MQ/.github/workflows/ci.yml`
Keep lines 1-46 (triggers with `tags-ignore`, `permissions: {}`, jobs `lint` + `unit`, SHA-pinned actions, `persist-credentials: false`, `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`). Drop `broker`/`multi-instance` jobs; change unit run to `uv run pytest -q -m "not benchmark"` and add a `benchmark` job (same steps, `uv run pytest -q -m benchmark`). Pins to reuse:
```yaml
- uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
  with:
    persist-credentials: false
- uses: astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7 # v10.2.0
  with:
    python-version: "3.14"
    enable-cache: true
```
(STACK.md names setup-uv v10.3.0; bump SHA only if resolved, otherwise keep this verified pin.) `workflow_call` trigger can stay; no release.yml in Phase 1.

### `.github/workflows/validate.yml` — copy `MQ/.github/workflows/validate.yml` verbatim (lines 1-34)
hassfest `home-assistant/actions/hassfest@06749dd8c0b54f350bc69c8752456cee498808a3`, `hacs/action@d556e736723344f83838d08488c983a15381059a # 22.5.0` with `category: integration`, daily cron. Brand icons must exist so no `ignore: brands` is needed.

### `custom_components/xmltv_calendar/manifest.json` — `MQ/.../manifest.json` (lines 1-14)
```json
{
  "domain": "xmltv_calendar",
  "name": "XMLTV Calendar",
  "codeowners": ["@akentner"],
  "config_flow": true,
  "documentation": "https://github.com/akentner/homeassistant-xmltv-integration",
  "integration_type": "service",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/akentner/homeassistant-xmltv-integration/issues",
  "requirements": [],
  "version": "0.1.0"
}
```
Drop `dependencies: ["mqtt"]` and `single_config_entry` (multiple sources allowed). `domain`, `name`, then alphabetical (hassfest rule). `iot_class` is discretion.

### `custom_components/xmltv_calendar/__init__.py` (lifecycle, event-driven) — `MQ/.../__init__.py`
**Imports / typed entry** (lines 1-22):
```python
from typing import TYPE_CHECKING
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
...
if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

type MqttActionsConfigEntry = ConfigEntry[Manager]   # -> lives in data.py as XmltvConfigEntry
PLATFORMS: list[Platform] = [...]                     # -> [Platform.CALENDAR]
```
No `async_setup` and therefore no `CONFIG_SCHEMA` (MQ needs it only because of services; lines 24-31 do NOT copy).

**Setup with listener registered before forward** (lines 34-60, simplified):
```python
async def async_setup_entry(hass: HomeAssistant, entry: MqttActionsConfigEntry) -> bool:
    ...
    entry.runtime_data = manager
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    ...
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
```
For xmltv: build `XmltvCoordinator(hass, entry)`, `await coordinator.async_config_entry_first_refresh()` (raises ConfigEntryNotReady), set `entry.runtime_data = XmltvRuntimeData(coordinator=..., source_snapshot=(dict(entry.data), dict(entry.options)), calendars={}, add_entities=None)`, then listener, then forward.

**Update listener**: use RESEARCH.md Pattern 1 (`_async_entry_updated` diffing snapshot, 01-RESEARCH.md lines 263-279) in place of MQ lines 63-65.

**Unload** (lines 68-79):
```python
async def async_unload_entry(hass, entry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

### `const.py` (config)
Analog: `HA/components/remote_calendar/const.py` (4 lines: `DOMAIN`, `CONF_*`). Contents per RESEARCH: `DOMAIN = "xmltv_calendar"`, `SUBENTRY_TYPE_CALENDAR = "calendar"`, `CONF_SOURCE_TYPE/URL/PATH/REFRESH_HOURS`, `CONF_CHANNELS/CHANNEL_REGEX/INCLUDE/EXCLUDE`, `DEFAULT_REFRESH = timedelta(hours=24)`, `MIN_REFRESH = timedelta(hours=1)`, `DEFAULT_DURATION = timedelta(minutes=60)`, size caps. Use `homeassistant.const.CONF_NAME/CONF_URL/CONF_PATH` where they exist (MQ config_flow imports `CONF_NAME` that way).

### `data.py` (model)
Pattern: `HA/components/remote_calendar/coordinator.py:20`
```python
type RemoteCalendarConfigEntry = ConfigEntry[RemoteCalendarDataUpdateCoordinator]
```
-> `@dataclass class XmltvRuntimeData` (coordinator, source_snapshot, calendars: dict[str, XmltvCalendarEntity], add_entities: AddConfigEntryEntitiesCallback | None) and `type XmltvConfigEntry = ConfigEntry[XmltvRuntimeData]`. Put entity type under `TYPE_CHECKING` to avoid import cycle.

### `coordinator.py` (service, polling) — `HA/components/remote_calendar/coordinator.py` (lines 22-83)
```python
_LOGGER = logging.getLogger(__name__)

class RemoteCalendarDataUpdateCoordinator(DataUpdateCoordinator[Calendar]):
    config_entry: RemoteCalendarConfigEntry

    def __init__(self, hass, config_entry) -> None:
        super().__init__(
            hass, _LOGGER,
            name=f"{DOMAIN}_{config_entry.title}",
            update_interval=SCAN_INTERVAL,          # -> from entry.options/data, default 24 h
            config_entry=config_entry,
            always_update=True,                     # -> False is fine: EpgData eq=False
        )

    @override
    async def _async_update_data(self) -> Calendar:
        try:
            res = await get_calendar(...)
        except TimeoutException as err:
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="timeout") from err
        except (HTTPError, InvalidURL) as err:
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="unable_to_fetch") from err
        try:
            return await parse_calendar(self.hass, res.text)     # executor parse
        except InvalidIcsException as err:
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="unable_to_parse") from err
```
Adapt: aiohttp (`async_get_clientsession`) not httpx; call `source.fetch_url()` / executor `source.open_file()` then `hass.async_add_executor_job(parser.parse, ...)`. Translation keys go under `exceptions` in en.json.

### `source.py` (service, HTTP + file I/O)
No direct analog. Reuse error-mapping shape from coordinator excerpt above (typed source errors -> `UpdateFailed`/flow `errors`). Implement per RESEARCH Pattern 5 + Pitfalls: `async_get_clientsession(hass)`, explicit `aiohttp.ClientTimeout`, byte cap, gzip magic `1f 8b` sniff, `hass.config.is_allowed_path` and `open()` only inside executor jobs.

### `calendar.py` (entity) — `HA/components/remote_calendar/calendar.py`
**Imports + PARALLEL_UPDATES** (lines 1-23):
```python
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
PARALLEL_UPDATES = 0
```
**Entity class** (lines 45-61): `class X(CoordinatorEntity[Coord], CalendarEntity)`, `_attr_has_entity_name = True`. Change per RESEARCH Pattern 2: `_attr_name = None`, `_attr_unique_id = subentry.subentry_id`, `DeviceInfo(identifiers={(DOMAIN, subentry.subentry_id)}, name=subentry.title, entry_type=DeviceEntryType.SERVICE)` (DeviceInfo shape: `MQ/custom_components/mqtt_actions/entities.py:55-61`, import line 6).
**event / async_get_events** (lines 63-89): keep the shape, replace timeline with bisect over sorted matches (RESEARCH Pattern 3, end-inclusive `m.end >= start`; confirmed by `HA/components/demo/calendar.py:74` `if self._event.end_datetime_local < start_date: return []`).
**Refilter on coordinator update** (lines 112-132):
```python
async def async_added_to_hass(self) -> None:
    await super().async_added_to_hass()
    await self._async_update_timeline()     # -> self._async_refilter() (executor FilterSpec.apply)
    self.async_write_ha_state()

@callback
def _handle_coordinator_update(self) -> None:
    self.coordinator.config_entry.async_create_task(
        self.hass, self._async_handle_coordinator_update(), name="...")
```
Add generation counter guard (RESEARCH Pattern 4).
**Platform setup per subentry** — `MQ/custom_components/mqtt_actions/switch.py:55-72`:
```python
async_add_entities([DeviceSwitch(manager, device_id)], config_subentry_id=manager.subentry_id_of(device_id))
```
-> loop `entry.subentries`, type `SUBENTRY_TYPE_CALENDAR`, one call per subentry with `config_subentry_id=subentry_id`; store `async_add_entities` in `runtime_data.add_entities` so the update listener can add later subentries.
**Event build** (lines 135-155): `CalendarEvent(summary=..., start=dt_util.as_local(...), end=..., description=..., uid=..., location=...)` — move field logic into `xmltv/render.py` (pure strings), construct `CalendarEvent` only in `calendar.py`, only for the requested window.

### `config_flow.py` (flow) — `MQ/custom_components/mqtt_actions/config_flow.py`
**Parent flow + subentry registration** (lines 79-138):
```python
class MqttActionsConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            ... validate -> errors[FIELD] = "key"
            if not errors:
                return self.async_create_entry(title=name, data={...})
        schema = vol.Schema({vol.Required(CONF_X, default=...): str, ...})
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry):  # noqa: ARG003
        return {SUBENTRY_SWITCH: SwitchSubentryFlow, ...}   # -> {SUBENTRY_TYPE_CALENDAR: CalendarSubentryFlow}
```
Use `import voluptuous as vol` (RESEARCH line 489), NOT `probatio` as MQ does (MQ floor is 2026.9). For xmltv: `async_step_user` shows a menu (`url`/`file`), each step sets `await self.async_set_unique_id(normalize_source(...)); self._abort_if_unique_id_configured()` (remote_calendar uses `_async_abort_entries_match`, `HA/components/remote_calendar/config_flow.py:56-63`), then test-fetches via `source.py` and maps exceptions to `errors["base"]` like remote_calendar lines 64-80.
**Subentry form handling** (MQ lines 315-374): `errors` dict, strip name, `self.async_create_entry(title=name, data=...)`, `add_suggested_values_to_schema` on re-show. In CalendarSubentryFlow read channels from `self._get_entry().runtime_data` and `async_abort(reason="source_not_loaded")` if entry not loaded; full skeleton in 01-RESEARCH.md lines 459-488. No reconfigure step in Phase 1 (listener forbids `async_update_reload_and_abort`).
No options flow in Phase 1 unless refresh interval editing is planned; then `OptionsFlowWithReload`.

### `translations/en.json` — `MQ/custom_components/mqtt_actions/translations/en.json`
Structure to copy:
```json
{
  "config": {
    "step": {"user": {"title": "...", "description": "...", "data": {...}, "data_description": {...}}},
    "error": {"invalid_url": "...", ...},
    "abort": {"already_configured": "..."}
  },
  "config_subentries": {
    "calendar": {
      "initiate_flow": {"user": "Add calendar"},
      "entry_type": "Calendar",
      "step": {"user": {"title": "...", "data": {...}, "data_description": {...}}},
      "error": {"invalid_regex": "..."},
      "abort": {"source_not_loaded": "..."}
    }
  },
  "exceptions": {"timeout": {"message": "..."}, "unable_to_fetch": {...}, "invalid_feed": {...}}
}
```
Required keys list: RESEARCH Pitfall 12 (line 395). `config.step` must include `menu_options` for the url/file menu.

### `tests/conftest.py` — `MQ/tests/conftest.py`
Module-level import + autouse fixture (lines 11-12, 42-44):
```python
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.mqtt_actions import const   # -> import custom_components.xmltv_calendar  # noqa: F401

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow Home Assistant to load integrations from custom_components in every test."""
```
Optionally copy `always_slow_event_loop` (lines 47-55) to surface loop-blocking. Add Berlin TZ fixture and `forbid_loop_io` per RESEARCH lines 491-536. Keep `tests/__init__.py` (MQ has one) but no `custom_components/__init__.py`. Subentries in tests: `MockConfigEntry(..., subentries_data=[ConfigSubentryData(...)])` (MQ imports `ConfigSubentryData` at line 9).

### `tests/test_repo_structure.py` — `MQ/tests/test_repo_structure.py`
Copy constants (lines 1-30) and tests at lines 104-136 and 224-283 (manifest keys, domain==folder, hacs.json floor, brand PNG ≥256, LICENSE MIT, workflows `permissions: {}`, SHA pins, `persist-credentials: false`, hacs category no ignore, push w/o branch filter, ci runs locked sync/ruff/format/pytest, validate has hassfest+hacs+schedule). Adapt: `INTEGRATION = COMPONENTS / "xmltv_calendar"`, `WORKFLOW_FILES = ("validate.yml", "ci.yml")`, floor `"2026.3.0"`, drop mosquitto/dependabot/README-phase/broker-tier tests (lines 139-216, 285-400). Add an AST purity check for `xmltv/` (no `homeassistant` imports) here or in `tests/xmltv/test_purity.py` (MQ already imports `ast`).

### `brand/icon.png`, `brand/icon@2x.png`
Same layout as `MQ/custom_components/mqtt_actions/brand/` (256x256 / 512x512 PNG; source SVG under `docs/assets/` like `MQ/docs/assets/icon.svg`).

## Shared Patterns

- **Typed runtime_data:** `type XmltvConfigEntry = ConfigEntry[XmltvRuntimeData]`; never `hass.data[DOMAIN]` (`HA/components/remote_calendar/coordinator.py:20`, `MQ/.../__init__.py:19`).
- **Executor for CPU/IO:** `await self.hass.async_add_executor_job(fn)` (`HA/components/remote_calendar/calendar.py:89,110`). Applies to parser, filter apply, file open, `is_allowed_path`.
- **Error to translated UpdateFailed:** `raise UpdateFailed(translation_domain=DOMAIN, translation_key="...") from err` with `_LOGGER.debug` of the raw error (`HA/components/remote_calendar/coordinator.py:64-83`).
- **Flow error convention:** `errors: dict[str, str]`, field-keyed (`errors[CONF_INCLUDE] = "invalid_regex"`) or `errors["base"]`; re-show with `add_suggested_values_to_schema` (`MQ/.../config_flow.py:95-127`).
- **`noqa` style:** inline targeted codes with HA-required unused args, e.g. `# noqa: ARG001` / `ARG003` (MQ `__init__.py:63`, `config_flow.py:136`).
- **Docstrings:** every public module/class/function has one (ruff `D` enabled outside tests).

## No Analog Found

| File | Role | Data Flow | Use instead |
|---|---|---|---|
| `xmltv/timeparse.py` | utility | transform | 01-RESEARCH.md lines 399-435 (tested parser) |
| `xmltv/parser.py` | utility | streaming | 01-RESEARCH.md lines 437-457 (iterparse + `root.clear()`) |
| `xmltv/model.py` | model | - | `@dataclass(slots=True, frozen=True)` Channel/Programme, `EpgData(eq=False)` per RESEARCH structure |
| `xmltv/filter.py` | utility | transform | D-05..D-08; `compile_patterns(text) -> (patterns, error)` |
| `xmltv/render.py` | utility | transform | field mapping from remote_calendar `_get_calendar_event`, but pure strings |
| `source.py` | service | HTTP + file-I/O | RESEARCH Pattern 5 + Pitfalls 2, 4 |
| `tests/xmltv/*`, `tests/test_benchmark.py`, `scripts/generate_benchmark_feed.py`, `tests/fixtures/*` | test/tool | batch | plain pytest; RESEARCH Validation Architecture lines 591-650 |

## Metadata

**Analog search scope:** `~/Projects/homeassistant-mqtt-actions-integration` (tracked files), installed HA core `components/remote_calendar/*`, `components/demo/calendar.py`
**Files scanned:** ~20
**Pattern extraction date:** 2026-10-12
