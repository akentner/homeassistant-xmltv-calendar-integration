# Phase 4: Automation Extras & Release - Pattern Map

**Mapped:** 2026-10-21
**Files analyzed:** 22 (new + modified)
**Analogs found:** 20 / 22

All paths are relative to the repo root `homeassistant-xmltv-calendar-integration/` unless prefixed with `../` (sibling repo). All analogs are git-tracked source.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `custom_components/xmltv_calendar/sensor.py` (NEW) | entity platform | event-driven (dispatcher + timer) | `custom_components/xmltv_calendar/calendar.py` | role-match |
| `custom_components/xmltv_calendar/match_store.py` (NEW) | store / persistence | file-I/O (HA Store) | `custom_components/xmltv_calendar/cache.py` (`FeedCache`, `SourceHealth`) | exact |
| `custom_components/xmltv_calendar/xmltv/retention.py` (NEW, pure) | utility | transform | `custom_components/xmltv_calendar/xmltv/window.py`, `cache.py` `from_dict` readers | role-match |
| `custom_components/xmltv_calendar/calendar.py` (MOD) | entity | event-driven | itself (`_async_refilter`, `async_apply_subentry`) | exact |
| `custom_components/xmltv_calendar/__init__.py` (MOD) | setup/lifecycle | request-response | itself | exact |
| `custom_components/xmltv_calendar/data.py` (MOD) | model (runtime) | — | itself | exact |
| `custom_components/xmltv_calendar/coordinator.py` (MOD) | service | batch/polling | itself (`_async_update_data` 149-190) | exact |
| `custom_components/xmltv_calendar/cache.py` (MOD, `RefreshAttempt` + `attempt` key) | store | file-I/O | `SourceHealth` in same file (124-166) | exact |
| `custom_components/xmltv_calendar/source.py` (MOD, http status) | service | request-response | itself (`SourceUnavailableError`, ~224-228) | exact |
| `custom_components/xmltv_calendar/diagnostics.py` (MOD) | utility | transform | itself `_calendars` (87-93) | exact |
| `custom_components/xmltv_calendar/xmltv/settings.py` (MOD, `retention_days`) | config contract | transform | itself (`_minutes`, `with_defaults`, `ADVANCED_DEFAULTS`) | exact |
| `custom_components/xmltv_calendar/xmltv/window.py` (MOD, `next_after`) | utility | transform | `MatchIndex.current_or_next` | exact |
| `custom_components/xmltv_calendar/config_flow.py` (MOD, retention field) | config flow | request-response | `_advanced_schema` / `_advanced_values` (465-505) | exact |
| `custom_components/xmltv_calendar/translations/en.json` + `de.json` (MOD) | config | — | existing files (no `entity` section yet) | partial |
| `blueprints/automation/xmltv_calendar/notify_before_programme.yaml` (NEW) | config (blueprint) | event-driven | `tests/test_calendar.py:195-230` (calendar trigger w/ negative offset) | partial |
| `.github/workflows/release.yml` (NEW) | config (CI) | batch | `../homeassistant-mqtt-actions-integration/.github/workflows/release.yml` | exact |
| `README.md` (REWRITE) | docs | — | `../homeassistant-mqtt-actions-integration/README.md` (section layout) | role-match |
| `tests/test_sensor.py` (NEW) | test | — | `tests/test_calendar.py` | role-match |
| `tests/test_new_match_event.py` / `tests/test_retention.py` (NEW) | test | — | `tests/test_multiday_refresh.py`, `tests/test_cache.py` (`hass_storage`) | role-match |
| `tests/xmltv/test_retention.py`, additions to `tests/xmltv/test_window.py`, `tests/xmltv/test_settings.py` | test (pure) | — | existing `tests/xmltv/test_window.py`, `test_settings.py` | exact |
| `tests/test_blueprint.py` (NEW) | test | — | `tests/test_calendar.py:195-265` | partial |
| `tests/test_repo_structure.py`, `tests/test_translations.py` (MOD) | test | — | themselves | exact |

## Pattern Assignments

### `custom_components/xmltv_calendar/sensor.py` (entity platform, event-driven)

**Analog:** `custom_components/xmltv_calendar/calendar.py`

**Imports / TYPE_CHECKING split** (calendar.py lines 1-31): runtime imports at top, HA types and `.data` imports under `if TYPE_CHECKING:`; `_LOGGER = logging.getLogger(__name__)`; `PARALLEL_UPDATES = 0` (line 34).

**Platform setup per subentry** (calendar.py lines 75-88) — copy and keep a per-platform callback (Pitfall 2):
```python
async def async_setup_entry(hass, entry: XmltvConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    runtime = entry.runtime_data
    runtime.add_entities = async_add_entities
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_CALENDAR or subentry_id in runtime.calendars:
            continue
        entity = XmltvCalendarEntity(runtime.coordinator, entry, subentry)
        runtime.calendars[subentry_id] = entity
        async_add_entities([entity], config_subentry_id=subentry_id)
```
Sensors need their own registry (e.g. `runtime.sensors: dict[str, tuple[...]]`) and `runtime.add_entities` becomes `dict[Platform, callback]`.

**Entity base / device** (calendar.py lines 91-120): `CoordinatorEntity[XmltvCoordinator]`, `_attr_has_entity_name = True`, `DeviceInfo(identifiers={(DOMAIN, subentry.subentry_id)}, name=subentry.title, entry_type=DeviceEntryType.SERVICE)`. This DeviceInfo is built twice already (lines 114-118 and 199-203) — factor into a shared helper (e.g. `device_info(subentry_id, title)`) used by calendar + both sensors. Sensor differences: `_attr_translation_key = "next_match"` / `"last_fetch"`, unique ID `f"{subentry_id}_next_match"`, `SensorDeviceClass.TIMESTAMP`, `_unrecorded_attributes = frozenset({...})`; last-fetch adds `EntityCategory.DIAGNOSTIC`, `_attr_entity_registry_enabled_default = False`.

**Availability** (calendar.py lines 129-133):
```python
@property
@override
def available(self) -> bool:
    return self.coordinator.data is not None
```

**Lifecycle hook** (calendar.py lines 122-127): `@override async def async_added_to_hass` calling `super()` first; register `async_dispatcher_connect` + `async_track_point_in_utc_time` unsubs via `self.async_on_remove(...)`.

**Rendering summary** — reuse `render.to_event_fields` / `render.template_values` exactly as `_to_event` (calendar.py lines 41-46) does; read templates from the calendar entity in `runtime.calendars.get(subentry_id)` (may be `None`, Pitfall 1 → state unknown).

---

### `custom_components/xmltv_calendar/match_store.py` (store, file-I/O)

**Analog:** `custom_components/xmltv_calendar/cache.py`

**Store construction** (cache.py lines 36, 171-178):
```python
STORE_VERSION = 1
...
self._store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, f"{DOMAIN}.{key}", private=True)
```
New key: `f"{DOMAIN}.matches.{cache_key(entry)}"` (`cache_key` at cache.py:42). Add `serialize_in_event_loop=False` and use `async_delay_save` (immutable snapshots).

**Load with tolerant fallback** (cache.py lines 201-209):
```python
async def async_load(self) -> None:
    try:
        data = await self._store.async_load()
    except HomeAssistantError as err:
        _LOGGER.debug("Cache %s metadata unreadable: %s", self._key, type(err).__name__)
        data = None
    self._meta = CacheMeta.from_dict(data.get("meta")) if isinstance(data, dict) else None
```

**Save with logged failure** (cache.py lines 193-199):
```python
try:
    await self._store.async_save(self._stored(self._meta))
except (OSError, HomeAssistantError) as err:
    _LOGGER.debug("Cache %s health not saved: %s", self._key, type(err).__name__)
```
Use the same for the explicit flush in `async_unload_entry` (Pitfall 3). Removal: mirror `FeedCache.async_remove` (cache.py:293) and call it from `__init__.py:async_remove_entry` (lines 61-64).

---

### `custom_components/xmltv_calendar/xmltv/retention.py` (pure utility, transform)

**Analogs:** `xmltv/window.py` (pure, no HA imports — enforced by `tests/xmltv/test_purity.py`) and `cache.py` `SourceHealth.from_dict` (lines 143-166) for the tolerant (de)serializer:
```python
@classmethod
def from_dict(cls, value: object) -> Self:
    """Tolerant reader: anything malformed gives the default (healthy) state, never an exception (T-03-14)."""
    if not isinstance(value, dict):
        return cls()
    ...
    parsed = [_aware_datetime(stored) for stored in times]
```
`_aware_datetime`/`_isoformat` live in cache.py (55-69) which imports HA; the pure module must re-implement or move them into `xmltv/`. UID via `render.event_uid` (`xmltv/render.py:164-168`), never a new hash.

---

### `custom_components/xmltv_calendar/xmltv/window.py` — add `MatchIndex.next_after`

**Analog:** same class (lines 39-51):
```python
def overlapping(self, start, end):
    lo = self._lower(start)
    hi = bisect_left(self._starts, end)
    return [p for p in self._programmes[lo:hi] if p.stop >= start]
```
New method: `i = bisect_right(self._starts, now); return self._programmes[i] if i < len(self._programmes) else None` (import `bisect_right`). Docstring style: one line, imperative.

---

### `custom_components/xmltv_calendar/calendar.py` (MOD)

**Hook points:**
- `async_added_to_hass` (122-127) → `_async_refilter("initial")`
- `_handle_coordinator_update` (135-143) → `_async_refilter("data")` via `self._entry.async_create_task(...)`
- `_async_refilter` (145-171): generation counter at 147-162 stays; insert capture/prune/diff/fire **after** `if generation != self._generation: return` and before `self.async_write_ha_state()`. The `_spec is None` early branch (152-156) must also send the dispatcher signal.
- `async_apply_subentry` (182-216): `await self._async_refilter()` at line 214 → `reason="config"`. Retention-only edits must set `refilter = True` (currently only when `spec is not None`).
- `match_count` (173-176) stays feed-only; add `retained_count` for diagnostics.
- WARNING log style for burst cap: copy lines 166-171 (`"Calendar %s: ..."`, `self.entity_id`).

---

### `custom_components/xmltv_calendar/__init__.py` + `data.py` (MOD)

- `PLATFORMS` line 17 → `[Platform.CALENDAR, Platform.SENSOR]`.
- `async_setup_entry` (20-31): load `MatchStore` before `async_forward_entry_setups`; put it on `XmltvRuntimeData`.
- `_async_entry_updated` (34-51): the `runtime.add_entities is None` early return (45) must become per-platform; add a sensor creation loop parallel to lines 47-51; also pop sensors in the removed-subentry loop (39-40).
- `async_unload_entry` (54-56): flush match store, then unload platforms.
- `data.py` (15-22): add `match_store`, `sensors` dict, change `add_entities` to `dict[Platform, AddConfigEntryEntitiesCallback]` (default_factory=dict).

---

### `custom_components/xmltv_calendar/coordinator.py` + `cache.py` (MOD, last-fetch record)

**Analog for `RefreshAttempt`:** `SourceHealth` (cache.py 123-166): `@dataclass(frozen=True, slots=True)`, `as_dict` with `_isoformat`, tolerant `from_dict`; reason strings re-validated with `_REASON` (cache.py ~220).

**Persistence** — extend `_stored` (cache.py 190-191):
```python
def _stored(self, meta: CacheMeta | None) -> dict[str, Any]:
    return {"meta": meta.as_dict() if meta is not None else None, "health": self._health.as_dict()}
```
→ add `"attempt": self._attempt.as_dict() if ... else None`; `async_load` (201-209) reads it tolerantly.

**Record point** — `_async_update_data` (coordinator.py 149-190): wrap the body (from `served = self._next_refresh_at` onward) in `try/finally`, building the attempt; branches already distinguish `UpdateFailed` (failure with `err.translation_key`), generic `Exception` (`_DEFAULT_REASON`), `from_cache`, success. Never put URL text in it (see the T-03-28 comment at lines 172-178). Send `async_dispatcher_send(self.hass, signal_attempt(entry_id))` — listeners are not called on unchanged data (`always_update=False`).

**Trigger detection:** `@override async def _handle_refresh_interval(self, _now=None)` setting `self._run_trigger` before `super()`; set `_target_kind` next to every `_next_refresh_at` assignment (e.g. `_set_regular_target`, line ~145).

---

### `custom_components/xmltv_calendar/xmltv/settings.py` (MOD, `retention_days`)

**Analog:** `_minutes` (lines 103-109) and `ADVANCED_DEFAULTS` (~lines 40-54):
```python
def _minutes(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return int(value) if value >= 0 else None
```
Write `_retention(value) -> int` (default 1, clamp 0..7). Append `KEY_RETENTION_DAYS: 1` **last** in `ADVANCED_DEFAULTS` and add to `with_defaults` return (112-137). Update the comment "Defaults of the ten Phase 2 keys". `tests/xmltv/test_settings.py:96,193` compare key order.

---

### `custom_components/xmltv_calendar/config_flow.py` (MOD)

**Analog:** `_advanced_schema` / `_advanced_values` (465-505):
```python
vol.Optional(CONF_MIN_DURATION): _duration_selector(),
...
# The NumberSelector sends float; stored as whole minutes
CONF_MIN_DURATION: int(minimum) if minimum is not None else None,
```
Add `vol.Optional(CONF_RETENTION_DAYS): NumberSelector(NumberSelectorConfig(min=0, max=7, step=1, mode=NumberSelectorMode.BOX))` and `CONF_RETENTION_DAYS: int(r) if r is not None else 1`. No `default=` (fields stay clearable, docstring line 466).

---

### `custom_components/xmltv_calendar/diagnostics.py` (MOD)

**Analog:** `_calendars` (87-93):
```python
rows.append({"title": subentry.title if subentry is not None else subentry_id, "matches": entity.match_count})
```
Add `"retained": entity.retained_count`. Optional last attempt next to `_health(...)` (line 61) using the same `_iso` helper (57).

---

### `translations/en.json` + `de.json` (MOD)

Top-level keys today: `config, config_subentries, options, issues, exceptions, selector` — **no `entity` section yet**. Add `entity.sensor.next_match.name` ("Next programme"/"Nächste Sendung"), `entity.sensor.last_fetch.name` + optional `state_attributes.*.state.*` for `outcome`/`trigger`/`cache` vocabularies, and the retention label under the calendar subentry advanced step `data` + `data_description`. Parity enforced by `tests/test_translations.py:110-140`; hassfest value rules at line 83.

---

### `blueprints/automation/xmltv_calendar/notify_before_programme.yaml` (NEW)

No blueprint exists in this repo or in `../homeassistant-mqtt-actions-integration` (no `blueprints/` dir). Use RESEARCH.md Pattern 6 verbatim as the starting point. The trigger shape is proven in `tests/test_calendar.py:195-230`:
```python
{"trigger": "calendar", "event": "start", "offset": "-0:05:00", "entity_id": "calendar.f1"}
...
{"action": "test.automation", "data": {"summary": "{{ trigger.calendar_event.summary }}"}}
```

---

### `.github/workflows/release.yml` (NEW)

**Analog:** `../homeassistant-mqtt-actions-integration/.github/workflows/release.yml` (66 lines). Copy verbatim; change only line 28:
```bash
manifest_version=$(jq -r .version custom_components/mqtt_actions/manifest.json)
```
→ `custom_components/xmltv_calendar/manifest.json`. Keeps `permissions: {}`, checkout SHA `3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1` with `persist-credentials: false`, `ubuntu-24.04`, `uses: ./.github/workflows/ci.yml` / `validate.yml`, `needs: [check-version, ci, validate]`, `gh release create ... --verify-tag --generate-notes`, `*-*` → `--prerelease`.

---

### `README.md` (REWRITE, currently 47 lines)

**Analog:** `../homeassistant-mqtt-actions-integration/README.md` (594 lines) heading layout: `# Name` → `## Requirements` → `## Installation` → `## Setup` → feature sections → `## Behavior` → `## Limitations` → `## Security` → `## Releases`. Keep assertions of `tests/test_repo_structure.py:148-152` (repo URL, "HACS", "2026.3"). Content outline: RESEARCH.md Pattern 7.

---

### Tests

- **`tests/test_sensor.py`, event/retention HA tests** — analog `tests/test_calendar.py` (`setup_xmltv` fixture from `tests/conftest.py:71-100`, `freezer`, `berlin_tz` at conftest 65-69, `async_mock_service`). Multi-refresh flow: `tests/test_multiday_refresh.py`. Store assertions: `tests/test_cache.py:59-60`:
  ```python
  def _stored_meta(hass_storage, entry):
      return hass_storage[f"{DOMAIN}.{entry.entry_id}"]["data"]["meta"]
  ```
  Disabled-by-default last-fetch sensor needs a local fixture (Pitfall 7) — add to `tests/conftest.py`.
- **`tests/test_blueprint.py`** — load YAML with `homeassistant.util.yaml.load_yaml`, validate via `Blueprint(data, expected_domain="automation")`, e2e via `use_blueprint` + `async_mock_service`, modelled on `tests/test_calendar.py:195-265`.
- **`tests/test_repo_structure.py`** — add `"release.yml"` to `WORKFLOW_FILES` (line 16); add manifest-path/needs assertion; add blueprint existence test.
- **`tests/test_translations.py`** — add AST completeness test (Pitfall 10) beside existing `_flatten` (line 45) helper.
- **Pure tests** — `tests/xmltv/test_window.py` (next_after), `tests/xmltv/test_settings.py` (retention key, order), new `tests/xmltv/test_retention.py`; purity guard `tests/xmltv/test_purity.py` automatically covers `retention.py`.

## Shared Patterns

### Tolerant readers (never raise on stored data)
**Source:** `cache.py:143-166` (`SourceHealth.from_dict`), `xmltv/settings.py:112-137` (`with_defaults`)
**Apply to:** `RefreshAttempt.from_dict`, match store reader, `retention_days`.

### No URLs / exception text in logs or attributes
**Source:** `coordinator.py:172-178` — log `type(err).__name__` only, title not URL; failure reasons are `FAILURE_REASONS` translation keys (`coordinator.py:65-67`).
**Apply to:** last-fetch sensor attributes, event payload, store.

### Executor for heavy work, generation supersession
**Source:** `calendar.py:157-162`
```python
result = await self.hass.async_add_executor_job(partial(self._spec.apply, epg, tz=dt_util.get_default_time_zone()))
if generation != self._generation:
    return
```
**Apply to:** any retained re-filter (D-17) run through `FilterSpec.apply`.

### Device sharing per subentry
**Source:** `calendar.py:114-118`, `199-209` (rename updates device registry). **Apply to:** both sensors (same identifiers `(DOMAIN, subentry_id)`).

### Docstrings / style
Ruff `ALL`, 120 chars, `@override` on HA overrides, `from typing import TYPE_CHECKING, override`, decision IDs cited in comments (e.g. `(D-04)`).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `blueprints/automation/xmltv_calendar/notify_before_programme.yaml` | blueprint | event-driven | No blueprint in this repo or sibling; use RESEARCH Pattern 6 |
| sensor `_unrecorded_attributes` / `async_track_point_in_utc_time` / dispatcher usage | — | event-driven | No sensors, timers or dispatcher in codebase yet; use RESEARCH Patterns 2 and 4 |

## Metadata

**Analog search scope:** `custom_components/xmltv_calendar/**`, `tests/**`, `.github/workflows/`, `../homeassistant-mqtt-actions-integration/{.github/workflows,README.md}`
**Files scanned:** ~20
**Pattern extraction date:** 2026-10-21
