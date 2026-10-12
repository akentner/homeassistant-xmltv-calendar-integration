# Stack Research

**Domain:** Home Assistant custom integration (HACS) that turns XMLTV EPG feeds into filtered `calendar.*` entities
**Researched:** 2026-10-12
**Confidence:** HIGH for HA APIs, versions, and parsing (checked against HA 2026.9.4 / 2026.10.1 source, the PyPI JSON API, and local benchmarks). MEDIUM for HACS/brand rules (official docs only, not run in CI yet).

> Confidence basis: The GSD `classify-confidence` seam rates web-only sources LOW or MEDIUM. I marked a claim HIGH only when I also checked it against primary artifacts: the installed `homeassistant` package source (2026.9.4, in the sibling repo `homeassistant-mqtt-actions-integration/.venv`), HA core at tag `2026.10.1` on GitHub, `pypi.org/pypi/<pkg>/json`, or a benchmark I ran on this machine. Claims backed only by docs are MEDIUM. Claims I inferred are LOW.

## TL;DR (prescriptive)

- **HA ≥ 2026.3.0, Python 3.14.** Develop and test against HA **2026.10.1** using `pytest-homeassistant-custom-component==0.13.372`.
- **No runtime requirements** (`"requirements": []`). Parse with stdlib `xml.etree.ElementTree.iterparse` plus stdlib `gzip`, inside the executor.
- **Config topology:** one config entry per **source** (URL/file, refresh interval), holding one `DataUpdateCoordinator`. One **config subentry** per **calendar** (filter set), giving one `CalendarEntity` each. This is how HA natively shares one download/parse across several calendars. It does mean revisiting the PROJECT.md decision "one calendar per config entry" (see "Stack Patterns by Variant").
- **Title templating** uses a restricted `str.format`-style formatter (`{channel}: {title}`), **not** HA Jinja templates.
- **Regex** uses stdlib `re`, compiled once and validated in the flow.
- **Tooling:** uv 0.13, Ruff 0.17.0 (`select = ["ALL"]` with the blueprint ignores, line-length 120, py314). CI runs hassfest, `hacs/action`, Ruff, and pytest.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Home Assistant Core | min **2026.3.0** (`hacs.json` `"homeassistant"`); dev/test **2026.10.1** | Runtime | 2026.3 is the first release that requires Python 3.14 (`REQUIRED_PYTHON_VER = (3, 14, 2)`; 2026.2 still had 3.13.2). It is also the first that supports **local brand images** in `custom_components/<domain>/brand/`. Everything else we use is older: `OptionsFlowWithReload` (2025.8), config subentries plus subentry reconfigure (2025.3/2025.4), `entry.runtime_data` (2024.x). The user runs current HA on `ha-host`, so we don't need older floors. | HIGH (const.py at tags 2026.2.0/2026.3.0, config_entries.py at 2025.7/2025.8) |
| Python | **3.14** (`requires-python = ">=3.14.2"`) | Language | Matches HA's `REQUIRED_PYTHON_VER` and the `requires-python >=3.14` of both HA 2026.10.1 and pytest-homeassistant-custom-component. Same as the sibling repos (`homeassistant-mqtt-actions-integration`, `homeassistant-traefik-integration`). | HIGH |
| `homeassistant.components.calendar.CalendarEntity` | HA built-in | The one entity per calendar | Gives native support for calendar triggers (`platform: calendar`, start/end + offset), the calendar dashboard, `calendar.get_events`, and the websocket `calendar/event/subscribe` live updates. Implement the read-only parts: `event` property plus `async_get_events()`. Set no `CalendarEntityFeature` flags. | HIGH (source) |
| `homeassistant.helpers.update_coordinator.DataUpdateCoordinator` | HA built-in | One per source: periodic fetch + parse, fan-out to entities | Standard polling pattern with built-in retry/backoff, `UpdateFailed(retry_after=…)`, `_async_setup()` for one-time setup, and `always_update=False` to skip listener churn when data is unchanged. Pass `config_entry=` explicitly: it's the documented pattern and gets rid of the ContextVar usage warning. | HIGH (source) |
| Config Flow + `OptionsFlowWithReload` + `ConfigSubentryFlow` | HA built-in | UI-only setup and editing | Parent-entry flow handles the source: URL or local path, refresh interval. Options flow (`OptionsFlowWithReload`, auto-reloads on change, no update listener needed) edits source settings. The subentry flow (`async_get_supported_subentry_types` → `{"calendar": CalendarSubentryFlow}`) adds and **reconfigures** calendars: channels, regexes, title template. | HIGH (source) |
| `homeassistant.helpers.aiohttp_client.async_get_clientsession` | HA built-in (aiohttp 3.14.3) | HTTP(S) download | Shared HA session: connection pooling, HA user agent, SSL context, cleanup. Never create your own `aiohttp.ClientSession`. | HIGH |
| `xml.etree.ElementTree.iterparse` (stdlib, C-accelerated, Expat) | Python 3.14 stdlib | Streaming XMLTV parse | No dependencies and no pin conflicts with HA core. It was **faster than lxml** in our benchmark, and with `root.clear()` its memory stays flat regardless of file size (numbers below). External entities are never fetched, and current Expat (≥2.7.2) has billion-laughs/quadratic-blowup protection. | HIGH (benchmark + Python docs) |
| `gzip` (stdlib) | Python 3.14 stdlib | `.xml.gz` support | Wrap the source in `gzip.GzipFile(fileobj=…)` and feed it straight into `iterparse` for streaming decompression. Detect gzip by **magic bytes `1f 8b`**, not by file extension or Content-Type. | HIGH |
| `re` (stdlib) | Python 3.14 stdlib | Include/exclude filters on title + description | Compile once per calendar. Validate with `re.compile` in the flow and return `errors={"include_regex": "invalid_regex"}`. Offer an "ignore case" boolean that maps to `re.IGNORECASE` instead of making users write `(?i)`. | HIGH |

### Supporting Libraries / HA helpers (all built-in, nothing to install)

| Library / Helper | Version | Purpose | When to Use |
|------------------|---------|---------|-------------|
| `homeassistant.helpers.selector` | HA built-in | Flow form widgets | `TextSelector(TextSelectorConfig(type=TextSelectorType.URL))` for the source. `NumberSelector` (minutes/hours, `mode=BOX`) or `DurationSelector` for the interval. **`SelectSelector(SelectSelectorConfig(options=[SelectOptionDict(value=id, label=display_name)…], multiple=True, mode=DROPDOWN, sort=True))`** for the channel list, built from parsed `<channel>` elements. `TextSelector` for regexes and the title template. `BooleanSelector` for ignore-case. |
| `homeassistant.data_entry_flow.section` | HA built-in | Collapsible "Advanced" groups in forms | Put the title template, ignore-case, and description fields in a collapsed `section("advanced", {"collapsed": True})` so the basic form stays short. |
| `homeassistant.util.dt` | HA built-in | Time handling | `dt_util.now()` / `dt_util.utcnow()` for comparisons. Return tz-aware datetimes: `CalendarEvent.__post_init__` **rejects naive datetimes and `end < start`**. |
| `homeassistant.components.calendar.CalendarEvent` | HA built-in | Event DTO | Fields: `start, end, summary, description, location, uid, recurrence_id, rrule` plus `status` (new in 2026.10). Use `location=channel display name` and a stable `uid` (e.g. `f"{channel_id}-{start:%Y%m%d%H%M%S}"`). **Construction costs about 38 µs**, because it runs voluptuous validation every time. Only build these for the window requested in `async_get_events` (see Pitfalls). |
| `CalendarEntityDescription(initial_color=…)` / `_attr_initial_color` | HA built-in | Default calendar color | Optional polish. The color is stored in entity registry options when the entity is first added. |
| `homeassistant.helpers.storage.Store` | HA built-in | Optional cache of the last parse | Lets calendars show events right after an HA restart even when the source is unreachable. Store only the compact filtered result plus the channel list, never the raw XML. |
| `string.Formatter` (stdlib) subclass | stdlib | Title templating `{channel}: {title}` | Reject field names containing `.` or `[`, which blocks attribute/index traversal. Use `format_map` with a defaulting dict so missing fields like `{episode}` become `""`. Validate in the flow. |
| `diagnostics` platform | HA built-in | Debugging support | Return source metadata (URL redacted with `async_redact_data`), last fetch time, programme and channel counts, and per-calendar match counts. |

### Development Tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| **uv** | 0.13.0 (2026-10-09) | Env + lockfile | `[tool.uv] package = false`. Dev deps in `[dependency-groups] dev`. CI runs `uv sync --locked`. Same pattern as `homeassistant-mqtt-actions-integration`. |
| **pytest-homeassistant-custom-component** | **0.13.372** (2026-10-11) | Test harness | Pins `homeassistant==2026.10.1`, `pytest==9.0.3`, `pytest-asyncio==1.4.0`, `syrupy==6.1.1`, `freezegun==1.5.5`, `pytest-freezer`, `respx`, `pytest-socket`, `pytest-cov`, `pytest-timeout`, `pytest-xdist`. **Do not add any of these separately.** Use the built-in fixtures: `hass`, `aioclient_mock` (aiohttp mock; real sockets are blocked by pytest-socket), `freezer`, `snapshot`, `enable_custom_integrations`, plus `MockConfigEntry`. Pin it exactly, because each release pins one HA version. |
| **Ruff** | **0.17.0** (2026-10-09), pin exactly | Lint + format | `target-version = "py314"`, `line-length = 120`, `select = ["ALL"]` with the integration_blueprint ignores (`ANN401, D203, D212, COM812, ISC001, CPY001`), relaxed per-file rules for `tests/**`. Copy `.ruff.toml` from `homeassistant-mqtt-actions-integration` (it uses 0.16.10). Add `extend-exclude = [".planning", ".claude"]`: per the sibling repo's own config comment, Ruff ≥0.16 also reformats Markdown under those directories. Pin the version: with `ALL`, a minor bump can add rules and break CI. |
| mypy (optional) | ≥2.1 | Strict typing | `homeassistant-traefik-integration` runs `mypy --strict`. Worth adding once the coordinator and data model exist. Not required for HACS. |
| `home-assistant/actions/hassfest` | `@master` (pin SHA) | Manifest/translation/strings validation | Required for credible HACS publishing. It validates `manifest.json`, `strings.json`/`translations`, and config-flow consistency. |
| `hacs/action` | `@main` or SHA-pinned `22.5.0` | HACS repo validation | `category: integration`. If the `brand/` folder isn't there yet, add `ignore: brands` temporarily. |
| `astral-sh/setup-uv` | v10.3.0 | CI uv install | `with: python-version: "3.14", enable-cache: true`. |
| `actions/checkout` | v7.0.1 | CI | `persist-credentials: false`, SHA-pinned, `permissions: {}` at workflow level (sibling convention). |
| Renovate | — | Dependency bumps | Copy `renovate.json` from mqtt-actions: phcc bumps require dashboard approval, because each one also bumps HA. |

## Installation

```bash
# Project bootstrap (no runtime deps; HA itself is provided by phcc in dev)
uv init --bare --python 3.14
uv add --dev "pytest-homeassistant-custom-component==0.13.372" "ruff==0.17.0"
# optional
uv add --dev "mypy>=2.1"
```

`pyproject.toml` skeleton (mirrors the sibling repos):

```toml
[project]
name = "homeassistant-xmltv-integration"
version = "0.0.0"
requires-python = ">=3.14.2"
dependencies = []

[tool.uv]
package = false

[dependency-groups]
dev = [
    "pytest-homeassistant-custom-component==0.13.372",
    "ruff==0.17.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--strict-markers"
```

`custom_components/xmltv_calendar/manifest.json`:

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

`hacs.json`:

```json
{ "name": "XMLTV Calendar", "homeassistant": "2026.3.0" }
```

Repo layout HACS expects: exactly one dir under `custom_components/`; `custom_components/xmltv_calendar/brand/icon.png` (plus optional `logo.png`, `dark_*`, `@2x`); a public repo with a description and GitHub topics; GitHub **releases**, not just tags (HACS uses the release tag name as the version); a README with usage.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| stdlib `ElementTree.iterparse` | `lxml.etree.iterparse` (6.1.3) | Only if profiling on a real feed shows ET is the bottleneck, which it wasn't in our benchmark. If you do use it, list it in `requirements` **unpinned or `>=`**. HA core pins `lxml==6.1.2` (for `scrape`), and an exact pin from us would conflict with that. |
| Config subentries (entry = source, subentry = calendar) | Entry-per-calendar plus a module-level shared-source registry (`hass.data[DOMAIN][normalized_source] → coordinator`, ref-counted, `config_entry=None` coordinator) | Use this if the user insists on "one config entry = one calendar". It works, but you have to hand-roll ref-counting, unload ordering, and "which entry's interval wins" (take the minimum). The coordinator also can't be tied to a config entry, so `async_config_entry_first_refresh` and `ConfigEntryNotReady` semantics get awkward. |
| Restricted `str.format` placeholders | HA Jinja `Template` with `TemplateSelector` | Use it only if users need conditionals (`{% if episode %}`). The costs: `Template.render()` from the executor goes back to the event loop through `run_callback_threadsafe`, so rendering thousands of titles blocks the loop. Jinja is also much slower per call than `str.format`, and it's heavier to validate. A middle ground is `{subtitle}`-style placeholders that collapse when empty, which covers 95% of the need. |
| Buffer download to `bytes` (with a size cap), then parse `BytesIO` in the executor | Stream response chunks into `ET.XMLPullParser.feed()` | Use this only if a source turns out to be several hundred MB **uncompressed**. Feeding on the event loop is CPU work and blocks, and feeding through the executor per chunk is complicated. Compressed feeds (the common case) are a few MB in memory and decompress as a stream anyway. |
| `aioclient_mock` (phcc fixture) | `aioresponses` 0.7.9 | `homeassistant-traefik-integration` uses `aioresponses`, but `aioclient_mock` ships with phcc and patches HA's own session factory. One less dependency. |
| `NumberSelector` (minutes) for refresh interval | `DurationSelector` | A Duration selector is nicer UX, but it stores a dict (`{"hours":..,"minutes":..}`). An int in minutes is simpler to store and migrate. Either is fine. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `python-xmltv` (1.4.3, **2014**) | Abandoned and loads the whole document. | stdlib `iterparse` plus a ~60-line parser of our own |
| `py-xmltv` (1.0.8, **2021**) | Generated from xsdata, so it pulls in `xsdata`, `sh`, and `setuptools` at runtime. Full-tree model, unmaintained. | stdlib `iterparse` |
| `pydantic-xml` (the approach in `shadow578/homeassistant_xmltv-epg`) | Builds a full object tree: our benchmark measured ~396 MB RSS for 78 MB XML with full-tree parsing. That repo also parses **inside the event loop**. And pydantic pins can clash with HA core's `pydantic` pin. | stdlib `iterparse` in `hass.async_add_executor_job` |
| `ET.parse()` / `ET.fromstring()` on the whole feed | 78 MB XML → **396 MB peak RSS**, against 14 MB for iterparse with `root.clear()`. That's a real risk on an Odroid N2+ or a small LXC. | `iterparse(events=("start","end"))`, grab the root from the first `start` event, `root.clear()` after each `</programme>`/`</channel>` |
| `datetime.strptime(s, "%Y%m%d%H%M%S %z")` per programme | **1.11 s** per 120k timestamps, against **0.15 s** for slicing ints plus a cached `datetime.timezone` per offset string. | A small `parse_xmltv_time()` that also handles a missing offset (treat as UTC per XMLTV DTD; MEDIUM) and missing seconds |
| `defusedxml` | Its ElementTree wrappers are effectively unmaintained (0.7.1, 2021). Current Expat already prevents entity-expansion attacks, and `iterparse` never resolves external entities. | stdlib ET. Cap the **decompressed byte count**: the Python docs call out decompression bombs for all compressed XML streams. |
| `aiohttp.ClientSession()` / `requests` / `httpx` directly | Breaks HA session lifecycle and connection pooling. `requests` blocks, and HA's `block_async_io` detects blocking HTTP calls on the loop. | `async_get_clientsession(hass)` with an explicit `aiohttp.ClientTimeout(total=…)` (large downloads) |
| `open()` / `gzip.open()` / `os.path.exists()` in async code | `builtins.open` is on HA's blocking-call watchlist, and it slows the loop on large files. | Do all file IO and parsing in one executor job. `hass.config.is_allowed_path()` is also blocking and must run in the executor too. |
| `OptionsFlowWithConfigEntry` | Deprecated: "being phased out, should not be referenced in new code". | `OptionsFlowWithReload` (or `OptionsFlow` + `self.config_entry`) |
| `hass.data[DOMAIN][entry.entry_id]` for per-entry state | Superseded pattern, and the quality scale expects `runtime_data`. | `type XmltvConfigEntry = ConfigEntry[XmltvCoordinator]` and `entry.runtime_data = coordinator` |
| `DataUpdateCoordinator(hass, logger, name=…)` without `config_entry=` | Relies on a ContextVar. Silent for custom integrations today, but it's an ERROR for core. | Pass `config_entry=entry` |
| YAML `platform: xmltv` setup | Out of scope by user choice, and HA discourages it for new integrations. | Config/Options/Subentry flows only |

## Stack Patterns by Variant

**If the user accepts subentries (recommended):**
- `ConfigEntry` = XMLTV source (`url` or `path`, `refresh_minutes`). `unique_id` = normalized source, which prevents duplicate sources.
- `entry.runtime_data` = one `XmltvCoordinator`. `coordinator.data` = channels plus a compact programme store (slotted dataclass or tuples, interned channel ids).
- One `ConfigSubentry` (type `"calendar"`) per calendar holds channels, include/exclude regex, ignore-case, and title template. `async_add_entities([...], config_subentry_id=subentry_id)` once per subentry.
- The subentry flow reads `self._get_entry().runtime_data.data.channels` to build the channel `SelectSelector`. Abort with `entry_not_loaded` if the parent isn't loaded.
- This satisfies "instances sharing a source share one download/parse" and "refresh interval per source" structurally, with no custom sharing code.

**If the user insists on one config entry per calendar (as written in PROJECT.md):**
- Add a module-level `SourceRegistry` in `hass.data` keyed by normalized source and ref-counted in `async_setup_entry`/`async_unload_entry`.
- Effective interval = min over subscribers. The coordinator gets `config_entry=None`, and `ConfigEntryNotReady` is raised manually.
- Expect noticeably more lifecycle code and tests. The roadmap should budget for it.

**If feeds are huge (≥100 MB uncompressed, e.g. full iptv-org country dumps):**
- Filter during parsing: the coordinator passes the union of all calendars' channel sets into the parser, and programmes on unwanted channels are dropped before they're stored. Optionally limit stored programmes to a window (e.g. now-1d … now+14d).
- Use HTTP conditional requests (`If-None-Match`/`If-Modified-Since`) and skip the parse on `304`.

**If the source is a local file:**
- Check `hass.config.is_allowed_path(path)` in the executor during the flow. By default only `/config/www` and media dirs are allowed, so document `allowlist_external_dirs`. Use `os.stat().st_mtime` to skip re-parsing an unchanged file.

## Benchmarks (local, Python 3.14.7, Expat 2.9.0)

Synthetic XMLTV: 300 channels × 400 programmes = 120,000 programmes; 77.7 MB uncompressed / 1.96 MB gzip.

| Approach | Time | Peak RSS |
|----------|------|----------|
| `ET.iterparse` over `gzip`, keep 5-tuple per programme | 1.17 s | 111 MB (dominated by retained descriptions) |
| `lxml.etree.iterparse(tag=…)` over `gzip`, same retention | 1.45 s | 123 MB |
| `ET.iterparse` + `root.clear()`, no retention | 1.22 s | **14 MB** |
| `ET.parse()` full tree | 1.56 s | **396 MB** |
| `CalendarEvent(...)` construction ×10,000 (HA 2026.9.4) | 0.38 s | — |

Takeaways:
- Parsing is cheap and belongs in the executor.
- Memory depends on what we **keep**, so store a compact model and drop unneeded fields early.
- Materialize `CalendarEvent` lazily, per requested window.

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| pytest-homeassistant-custom-component 0.13.372 | homeassistant 2026.10.1, Python ≥3.14 | Exact pin. Bump via Renovate with dashboard approval. Each bump can surface new HA deprecations. |
| homeassistant 2026.10.x | Python 3.14.2+ | `CalendarEvent.status` exists from 2026.10. **Don't use it** if the floor stays at 2026.3, or raise the `hacs.json` floor. |
| hacs.json `"homeassistant": "2026.3.0"` | Local `brand/` images, Python 3.14 | Below 2026.3 HA ignores `brand/` and runs Python 3.13. Our py314 syntax/target would still need checking. |
| Ruff 0.17.0 | `target-version = "py314"` | Sibling repo uses 0.16.10 with the same config. Expect a few new `ALL` rules after upgrading. |
| lxml (if ever used) | HA core pins `lxml==6.1.2` (scrape) | Never pin it exactly in `manifest.json`. |
| aiohttp 3.14.3 (HA-provided) | — | The session auto-decompresses `Content-Encoding: gzip`. A `.xml.gz` served as `application/gzip` is **not** auto-decompressed, so always sniff the magic bytes. |

## Sources

- Installed HA 2026.9.4 source (`~/Projects/homeassistant-mqtt-actions-integration/.venv/.../homeassistant/`): `components/calendar/__init__.py` (CalendarEvent validation, `_has_timezone`, `MIN_EVENT_DURATION = 0`, websocket subscriptions, `initial_color`), `components/calendar/trigger.py` (`UPDATE_INTERVAL = 15 min` polling), `helpers/update_coordinator.py` (`config_entry`, `always_update`, `_async_setup`, `retry_after`), `config_entries.py` (`ConfigSubentryFlow`, `OptionsFlowWithReload`, `OptionsFlowWithConfigEntry` deprecated), `helpers/selector.py`, `block_async_io.py`, `core_config.py` (`is_allowed_path`, default allowlist), `helpers/template/__init__.py` (`render` → `run_callback_threadsafe`). HIGH
- HA core on GitHub at tags 2025.7.0/2025.8.0/2026.2.0/2026.3.0/2026.10.1: `const.py` Python floors, `OptionsFlowWithReload` introduction, `CalendarEvent.status`, `requirements_all.txt` (`lxml==6.1.2`, `defusedxml==0.7.1`). HIGH
- PyPI JSON API (2026-10-12): homeassistant 2026.10.1, pytest-homeassistant-custom-component 0.13.372 (+ requires_dist), ruff 0.17.0, uv 0.13.0, lxml 6.1.3, python-xmltv 1.4.3 (2014), py-xmltv 1.0.8 (2021), defusedxml 0.7.1 (2021), aioresponses 0.7.9, syrupy 6.1.1. HIGH
- GitHub API: hacs/action latest 22.5.0, astral-sh/setup-uv v10.3.0, actions/checkout v7.0.1, home-assistant/actions master active (2026-10-12). HIGH
- https://developers.home-assistant.io/docs/core/entity/calendar/: event/async_get_events contract, ordering, window semantics, subscriptions. MEDIUM (matches source)
- https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api and /docs/core/integration/brand_images: local `brand/` folder from 2026.3. MEDIUM
- https://developers.home-assistant.io/blog/2025/02/16/config-subentries and /blog/2025/03/24/config-subentry-flow-changes: subentries, `_get_entry()`/`_entry_id`. MEDIUM
- https://hacs.xyz/docs/publish/start/ and /docs/publish/integration/: hacs.json keys, manifest keys, brand, releases, topics. MEDIUM
- https://docs.python.org/3.14/library/xml.html: XML vulnerabilities (Expat <2.7.2, decompression bombs). MEDIUM
- https://github.com/ludeeus/integration_blueprint: hacs.json/validate.yml conventions (`ignore: brands` note). MEDIUM
- https://github.com/shadow578/homeassistant_xmltv-epg: prior art (sensor-based, pydantic-xml, parses in the event loop). Used as a counter-example. MEDIUM
- Sibling repos `homeassistant-mqtt-actions-integration` (2026-10) and `homeassistant-traefik-integration`: pyproject/ruff/CI/release/renovate conventions. HIGH (local)
- Local benchmarks (this research session, scratchpad): iterparse vs lxml vs full parse, strptime vs manual, CalendarEvent cost. HIGH for relative numbers, MEDIUM for absolute numbers on HAOS hardware (slower CPU expected).

---
*Stack research for: Home Assistant custom integration (XMLTV → calendar), HACS-distributed*
*Researched: 2026-10-12*
