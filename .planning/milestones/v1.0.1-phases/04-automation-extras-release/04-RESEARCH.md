# Phase 4: Automation Extras & Release - Research

**Researched:** 2026-10-21
**Domain:** Home Assistant custom integration (sensor platform, HA event bus, `Store` persistence, automation blueprint, translations, GitHub release workflow)
**Confidence:** HIGH (nearly every claim was checked against the installed HA 2026.10.1 source, HA core/frontend at tag 2026.3.0, or files in this repo)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Next-match sensor (AUT-03)
- **D-01:** The state is the start of the next match that has **not started yet** (`start > now`). A match that is airing does not count. "Airing now" is already covered by the calendar entity's `event` (AUT-02). `device_class: timestamp`.
- **D-02:** With no future match, the sensor stays **available** and its state is `unknown`. The match attributes are absent or `None`. `unavailable` is only used the way the calendar uses it (no coordinator data at all, Phase 3 D-19).
- **D-03:** Attributes: `title` (raw feed title), `summary` (event title rendered from the calendar's title template), `channel` (display name), `channel_id`, `start`, `end`, `subtitle`, `episode`, `description`. — **Reversibility:** costly — attribute names become a contract for user automations and templates. Renaming them breaks those automations.
- **D-04:** `description` is excluded from the recorder via `_unrecorded_attributes`. `subtitle`/`episode` may also be excluded (Claude's discretion). The recorder must not grow with every state change.
- **D-05:** The sensor sits on the **same device as its calendar** (the subentry device), with `has_entity_name` and a `translation_key`. The translated name is "Next programme" / "Nächste Sendung", so a German UI gives an entity ID like `sensor.formel_1_nachste_sendung`. It is **enabled by default**. Unique ID is derived from the subentry ID.
- **D-06:** The sensor updates when a match passes its start, without waiting for a coordinator refresh (point-in-time tracking or equivalent), when the feed data changes, and when the calendar's filter or templates are edited (in place, no reload, Phase 2 D-04).

#### New-match event (EVT-08)
- **D-07:** **One event per new match**, event type `xmltv_calendar_new_match`. The payload has `entity_id` (calendar), `calendar` (calendar name), `title`, `summary`, `channel`, `channel_id`, `start`, `end`, `uid`. — **Reversibility:** one-way — the event type and payload keys are a published contract that user automations and the README examples depend on.
- **D-08:** A match is "new" when its **UID** (`<channel_id>-<UTC start>-<crc32(title)>`, EVT-06) is not in the calendar's persisted seen-set. A programme that moves or is renamed gets a new UID and fires again. This is accepted.
- **D-09:** Only matches with `start > now` fire. Matches that have started or ended join the seen-set silently.
- **D-10:** No events on the first refresh of a new calendar, and none after a restart or reload. The seen-set is persisted per calendar in an HA `Store`, shared with retention (D-14) as the roadmap notes.
- **D-11:** A **configuration change sets a new baseline silently**: when a calendar's filter changes (subentry edit), and when a source's timezone/offset options change (all UIDs change, Phase 3 D-16), the newly matching UIDs join the seen-set without events. Events only come from new feed data, never from config edits.
- **D-12:** **Burst cap:** at most about 50 events per calendar per refresh (exact number is Claude's discretion). The rest join the seen-set silently, with one WARNING log line naming the calendar and the number suppressed.
- **D-13:** The seen-set is pruned. A UID can be dropped once its programme has ended and is out of the retention window, so the Store does not grow without bound.

#### Past matches (EVT-07)
- **D-14:** Retention is **per calendar**: a new key in the calendar subentry's advanced section, stored flat next to the Phase 2 keys, integer days 0..7. Editing it applies in place through the diffing listener, with no reload. — **Reversibility:** costly — a new stored subentry key. Renaming it later needs a migration, or a with_defaults fallback that reads both names.
- **D-15:** **Default 1 day**, which matches today's behaviour (`KEEP_PAST = 1 day`, `const.py:75`). A missing key means the default (Phase 2 D-06 rule, no migration).
- **D-16:** Only **ended** matches (`end <= now`) are retained. A future or airing match that disappears from the feed also disappears from the calendar, because the feed is the truth about the future.
- **D-17:** The store holds the **raw programme data** of retained matches, not rendered events. When the filter changes, retained programmes are checked against the new filter, and the ones that no longer match are dropped. Templates are applied at render time, as for feed matches. A widened filter cannot bring back past programmes that were never stored. That is accepted.
- **D-18:** Merge rule: the calendar shows feed matches plus retained programmes whose **UID is not in the current feed**. A corrected past slot with a different title, and so a different UID, can show twice. That is accepted.
- **D-19:** Diagnostics list `matches` (from the feed) and `retained` (store only) separately per calendar. This extends the Phase 3 D-21 calendar entry.

#### Last-fetch diagnostic sensor (AUT-06, added)
- **D-20:** There is one diagnostic sensor on **every calendar device**. All calendars of one source show that source's data. The state is the timestamp of the **last refresh run** (`device_class: timestamp`).
- **D-21:** **Every refresh run counts as an attempt**: scheduled, backoff retry, manual (`update_entity`), and the start from cache. An attribute records what kind of run it was. This shows whether the schedule fires at all.
- **D-22:** Attribute groups. Exact key names and value vocabularies are Claude's discretion; keep them consistent with diagnostics.
  - Outcome: `outcome` (e.g. downloaded / not_modified / unchanged / cache_start / failed), `http_status` (empty for file sources), `failure_reason` (translated reason key from `FAILURE_REASONS`, never the URL), and the run trigger.
  - Cache handling: e.g. fresh cache hit / stale cache revalidating / cache written / bypassed / none. Also whether ETag and If-Modified-Since were sent.
  - Schedule: `last_success`, `next_refresh`, `consecutive_failures`.
  - Data: `bytes`, `programmes`, `channels`, `parse_duration`, `matches` (this calendar).
- **D-23:** The last attempt is **persisted** in the existing cache Store next to `SourceHealth` (`cache.py:124`, stored as `{meta, health}`), so after a restart the sensor shows the last real attempt. File sources already store health there (Phase 3 03-04).
- **D-24:** `entity_category: diagnostic`, **disabled by default**. No URL, host or credentials in any attribute.
- **D-25:** This partly revises Phase 3 D-19 ("no extra stale attributes on the calendar"). The calendar entity itself still gets no extra attributes. The information goes on a separate diagnostic entity.

#### Blueprint (AUT-05)
- **D-26:** Trigger: `platform: calendar`, `event: start`, with a negative `offset` from a lead-time input. `mode: queued`, so overlapping matches each notify once (success criterion 3).
- **D-27:** Inputs: calendar entity (selector filtered to integration `xmltv_calendar`, domain `calendar`), lead time (duration, sensible default such as 10 min), and an **action selector** whose default is `notify.send_message` to a selectable notify entity. The blueprint defines variables (`title`, `channel`, `start`, and so on, from `trigger.calendar_event`) for use in the actions. That covers mobile app, TTS and Telegram.
- **D-28:** The blueprint ships in the repo under `blueprints/automation/…`. The README has the "Import blueprint" button (my.home-assistant.io redirect).

#### Release & docs (DST-03, DST-04, CFG-04)
- **D-29:** The first release is **0.1.0** (already in `manifest.json`), tag `v0.1.0`, SemVer after that. Copy the release workflow from mqtt-actions (`../homeassistant-mqtt-actions-integration/.github/workflows/release.yml`): the tag must match `manifest.json`, CI and validate run as reusable workflows, `gh release create --generate-notes`, and a hyphen suffix marks a prerelease. Change the manifest path to `xmltv_calendar`. **The user pushes tags.** The assistant never pushes.
- **D-30:** The README is **English, one file**. Sections per DST-04: setup, regex filter examples, automation examples (calendar trigger, next-match sensor, new-match event), calendar limitations (15-min trigger window, overlapping events, `mode: queued`). It also documents both sensors, the event payload, retention, and the blueprint import. "Bilingual" in the phase goal refers to the UI only.
- **D-31:** CFG-04: `de.json` already exists with the key/placeholder parity test (`tests/test_translations.py`). All new strings (sensor names via `entity.sensor.*`, the retention field, attribute state translations where useful) are added to both `en.json` and `de.json`. The parity test keeps them in sync.

### Claude's Discretion
- How the seen-set and the retained programmes are stored: one Store per calendar or one per source keyed by subentry ID, the serialization format, and when to write (debounced `async_delay_save`).
- How the "config changed → silent baseline" detection works (D-11), e.g. a fingerprint of the filter spec plus the source tz options stored next to the seen-set.
- The exact burst cap (around 50).
- The update mechanism for the next-match sensor (D-06), and whether `subtitle`/`episode` are also unrecorded.
- Exact attribute keys and value vocabularies of the last-fetch sensor. The retention field's selector type (NumberSelector box/slider).
- The blueprint's default message text and lead-time default.

### Deferred Ideas (OUT OF SCOPE)
- **Refresh bug (calendar only updates after manual reload):** resolved via `/gsd-debug` as expected behaviour (see "Former blocker" in Phase Boundary).
- Earlier backlog items still open: per-source channel ID → friendly name mapping (Phase 1), time placeholders in templates (Phase 2), source URL/path reconfigure, multiple daily refresh times, free IANA timezone, fixable Repairs flow (Phase 3).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUT-03 | Each calendar has a next-match timestamp sensor (attributes: title, channel, start, end) | Pattern 2 (sensor fed by a per-calendar dispatcher signal, `async_track_point_in_utc_time` at the next start), `MatchIndex.next_after` helper, `_unrecorded_attributes` (verified in `helpers/entity.py:557-564`), entity-ID language rule (`NATIVE_ENTITY_IDS` contains `"de"`) |
| AUT-05 | Repo ships a blueprint "notify before a matching programme starts" (`mode: queued`) | Pattern 6: legacy `trigger: calendar` (the new `calendar.event_started` trigger is labs-gated at the 2026.3 floor), duration input with `allow_negative` (core and frontend 2026.3 verified), action selector default that uses blueprint variables, e2e test through `use_blueprint` |
| AUT-06 (new) | Per calendar device, a disabled-by-default diagnostic "last fetch" sensor showing the last refresh run | Pattern 4: `RefreshAttempt` record built in `_async_update_data`, run-trigger detection via `_handle_refresh_interval` override (present in 2026.3 and 2026.10), persisted as a third key in the cache Store, pushed by dispatcher because `always_update=False` skips listeners on unchanged data |
| EVT-07 | Matches from the past N days (configurable, ≤7) remain visible even after the feed drops them | Pattern 3: capture ended matches from the **previous and the new** index on every refilter (the parser drops programmes ended more than `KEEP_PAST` ago), merge by UID, re-check against the filter on edits, `retention_days` key in `with_defaults` |
| EVT-08 | An HA event fires for a new matching programme (not on the first refresh, not again after a restart) | Pattern 3: refilter `reason` (`initial`/`data`/`config`), so only `data` refilters after a completed baseline fire. Persisted seen-set (`uid -> stop`), burst cap 50, `hass.bus.async_fire` with JSON-safe ISO strings |
| CFG-04 | UI available in English and German | Existing parity tests (`tests/test_translations.py`) plus a new completeness test that collects every `step_id`/`reason`/error key from `config_flow.py` and asserts it exists in `en.json`. New keys: `entity.sensor.*`, retention field, attribute state names |
| DST-03 | Tagged releases with version matching `manifest.json` | Sibling `release.yml` (read verbatim, 66 lines) with the manifest path changed. It already passes every parametrized supply-chain test in `tests/test_repo_structure.py`. HACS needs a **release**, not only a tag |
| DST-04 | README documents setup, regex examples, automation examples, calendar limitations | Pattern 7 outline. Limitations verified: calendar triggers poll every 15 min (`trigger.py:46 UPDATE_INTERVAL = datetime.timedelta(minutes=15)`), docs say "Calendar triggers should not generally use automation mode `single`" |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

From `./.claude/CLAUDE.md`, `/home/akentner/Projects/CLAUDE.md` and `~/CLAUDE.md`:

- Python, HA custom component. `uv` for deps (`uv run --with`, no global pip). Ruff 0.17.0 pinned, `select = ["ALL"]`, 120-char lines, py314.
- **Zero runtime requirements** (`"requirements": []`, asserted by `tests/test_repo_structure.py::test_manifest_has_hacs_required_keys`). Nothing in this phase may add one.
- Config Flow + Options Flow + Subentry Flow only. No YAML configuration.
- Large data must not block the event loop. Parse and other heavy work go in the executor.
- Code, comments, commits in English. UI text is English and German. The user chats in German.
- Never log or expose URLs (host at most). Error texts are translation keys.
- GSD workflow: edits only inside `/gsd-*` commands. Plans must be goal-backward verifiable, implementations minimal and atomic.
- **The assistant never pushes** (dotfiles and D-29). The user pushes tags.
- Shell scripts must pass `shellcheck` (monorepo rule). This applies to the `run:` blocks of the release workflow.
- Use `ha` / `ha-ws` for Home Assistant interaction during UAT (not raw curl).

## Summary

Phase 4 adds a `sensor` platform with two entities per calendar subentry, a persisted per-source match store (seen-set + retained past programmes), an HA bus event, a shipped automation blueprint, translation completeness, a tag-triggered release workflow and a full README. Nothing needs a new library: every capability is HA built-in (`SensorEntity`, `Store`, `async_track_point_in_utc_time`, dispatcher, `hass.bus.async_fire`, blueprint schema) or stdlib.

The code has three seams. (1) `XmltvCalendarEntity._async_refilter` (`calendar.py:145-171`) is where new matches arrive. New-match diffing, retention capture/merge and the next-match notification all hook in there. The refilter needs a **reason** (`initial` / `data` / `config`), so only data-driven refilters after an established baseline fire events. That satisfies D-10 and D-11 without any fingerprint. (2) `XmltvCoordinator._async_update_data` (`coordinator.py:149-190`) knows the outcome of every refresh run. The last-fetch record is built there and persisted beside `meta` and `health` in the existing cache Store. Listeners must be poked through a dispatcher signal, because `always_update=False` means HA does not call listeners when the data object is unchanged. (3) `__init__.py` must forward `Platform.SENSOR` and create sensors for subentries added later. HA sets platforms up **concurrently** (`asyncio.gather` in `config_entries.py:2947`), so a sensor can be added before its calendar entity exists.

Two traps decide the blueprint and the retention design. The newer target-based `calendar.event_started` trigger with `offset_type: before` would be the natural fit, but at the 2026.3 floor it sits behind the `new_triggers_conditions` labs flag. The blueprint must use the legacy `trigger: calendar` with a **negative** `offset`, taken from a duration input with `allow_negative: true` (supported in core and frontend 2026.3). The parser drops programmes that ended more than `KEEP_PAST` (1 day) ago on every parse. Retention of 2..7 days therefore works only when ended matches are captured from the **previous** index before it is replaced, and are persisted.

**Primary recommendation:** Keep the calendar entity as the owner of match state. Give `_async_refilter` a reason parameter and a per-source `MatchStore` (one HA `Store` per source entry, keyed by subentry ID, `async_delay_save` plus an explicit flush on unload). Publish per-calendar changes on a dispatcher signal that the new `sensor.py` subscribes to. Ship the blueprint with a legacy calendar trigger and a negative-duration input. Copy the sibling `release.yml` with one path changed.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Next-match lookup (`start > now`) | Pure library (`xmltv/window.py`, `MatchIndex`) | HA glue (sensor) | Bisect over sorted starts. Pure and TDD-able like the existing `current_or_next` |
| Next-match sensor state + timer | HA glue (`sensor.py`) | Calendar entity (publishes changes) | Entity lifecycle, `async_track_point_in_utc_time`, translations |
| New-match diff, burst cap, event firing | HA glue (calendar entity refilter) | Pure helper (diff/prune functions) | Needs `hass.bus`. Set arithmetic and pruning are pure and testable |
| Retained programmes (capture, prune, re-filter, merge) | Pure helpers (`xmltv/`) | HA glue (`MatchStore`) | Programme (de)serialization and the merge rule are pure. Persistence is HA `Store` |
| Persistence of seen-set + retained | HA `Store` (`.storage/xmltv_calendar.matches.<key>`) | — | Survives restarts (D-10, EVT-07). Separate from the disposable feed cache |
| Last-fetch record | Coordinator (`_async_update_data`) | Cache Store (persist), sensor (display) | Only the coordinator knows trigger, HTTP status, cache path and parse duration |
| Retention setting | Subentry flow (advanced step) + `xmltv/settings.py` contract | Calendar entity (applies in place) | Flat stored key per D-14, `with_defaults` tolerant read |
| Blueprint | Repo file `blueprints/automation/…` | README (import button) | Runs in the user's HA automation engine, not in the integration |
| Release | GitHub Actions (`release.yml`) | HACS (reads releases) | Tag → checks → `gh release create` |
| Translations | `translations/en.json` + `de.json` | Tests | HA serves them. Tests enforce parity and completeness |

## Standard Stack

### Core (all built-in, nothing to install)

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `homeassistant.components.sensor.SensorEntity` + `SensorDeviceClass.TIMESTAMP` | HA 2026.10.1 (dev), floor 2026.3.0 | Both new sensors | Timestamp sensors must return an aware `datetime`. HA raises `ValueError` for naive values and converts to UTC (`components/sensor/__init__.py:659-668`, read this session) [VERIFIED: .venv HA 2026.10.1 source] |
| `Entity._unrecorded_attributes` | HA built-in | Keep `description` (and optionally `subtitle`, `episode`, large diagnostic attrs) out of the recorder | `helpers/entity.py:557-564`: `_entity_component_unrecorded_attributes: frozenset[str] = frozenset()` / `_unrecorded_attributes: frozenset[str] = frozenset()`, combined per class [VERIFIED: .venv HA source] |
| `homeassistant.helpers.event.async_track_point_in_utc_time` | HA built-in | Re-evaluate the next-match sensor exactly when the next match starts (D-06) | Present at `helpers/event.py:1499` [VERIFIED: .venv HA source] |
| `homeassistant.helpers.dispatcher` (`async_dispatcher_connect` / `async_dispatcher_send`) | HA built-in | Calendar → sensor change signal, coordinator → last-fetch signal | Decouples entities that platform setup creates concurrently (see Pitfall 1) [ASSUMED: standard HA idiom. Not re-read this session] |
| `homeassistant.helpers.storage.Store` | HA built-in | Seen-set + retained programmes, last attempt | `Store(hass, version, key, private=False, *, atomic_writes=False, encoder=None, max_readable_version=None, minor_version=1, read_only=False, serialize_in_event_loop=True)` (`helpers/storage.py:228-241`). `async_delay_save(data_func, delay)` is flushed on `EVENT_HOMEASSISTANT_FINAL_WRITE` [VERIFIED: .venv HA source] |
| `hass.bus.async_fire` | HA built-in | `xmltv_calendar_new_match` event | Standard event bus [ASSUMED: API well known. Not re-read] |
| Blueprint schema (`components/blueprint/schemas.py`) | HA built-in | Validate the shipped blueprint in a test | Requires `blueprint.name` and `blueprint.domain`. Optional: `description`, `source_url`, `author`, `homeassistant.min_version` (`{major}.{minor}.{patch}`), `input` (also sections) [VERIFIED: .venv HA source] |
| `actions/checkout`, `gh` CLI on `ubuntu-24.04` | pinned SHA `3d3c42e5aac5ba805825da76410c181273ba90b1` (v7.0.1) | Release workflow | Same pin as `ci.yml`/`validate.yml` in this repo [VERIFIED: .github/workflows/ci.yml:21] |

### Supporting

| Component | Purpose | When to Use |
|-----------|---------|-------------|
| `homeassistant.util.dt` (`as_local`, `utcnow`) | ISO strings in event payloads and attributes | Every datetime leaving the integration |
| `PyYAML` (already in the dev env through phcc; `tests/test_repo_structure.py` imports `yaml`) | Loading workflow YAML in tests | Release-workflow tests. For the blueprint use HA's `homeassistant.util.yaml.load_yaml`/`parse_yaml`, which understands `!input` |
| `pytest_homeassistant_custom_component.common.async_capture_events` (`common.py:1695`), `async_fire_time_changed`, `async_mock_service`, `hass_storage` fixture | Tests | Event assertions, timer tests, blueprint action capture, Store contents |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Legacy `trigger: calendar` + negative offset | `calendar.event_started` with `options: {offset, offset_type: before}` and `target` | Cleaner UX (positive lead time), but at HA 2026.3 the new triggers are gated by the labs preview flag `new_triggers_conditions` (2026.3.0 `helpers/trigger.py:145-164`, `automation.is_disabled_experimental_trigger`). That would break the 2026.3 floor. Revisit when the floor rises past the release that un-gates them |
| One Store per source keyed by subentry ID | One Store per calendar (subentry) | Per-calendar stores need explicit removal on subentry delete, and HA removes the entity before our listener runs. A per-source store prunes unknown subentry IDs on every save and is removed once in `async_remove_entry` |
| Dispatcher signal | Callback set on the calendar entity / runtime | Equivalent. Dispatcher survives the "sensor added before calendar exists" order without extra bookkeeping |
| Refilter `reason` | Filter/tz fingerprint stored with the seen-set (CONTEXT suggestion) | A fingerprint is not needed to decide *whether to fire*: every config change either refilters in place (`reason=config`) or reloads (`reason=initial`), and both are silent. A tz fingerprint is still useful to **drop retained programmes** recorded under an old offset (see Open Question 2) |

**Installation:** none. `"requirements": []` stays. No dev dependency changes.

## Package Legitimacy Audit

This phase installs **no** external packages: no runtime requirements, no new dev dependencies. The release workflow reuses the already SHA-pinned `actions/checkout` and the runner's preinstalled `gh`.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| — | — | — | — | — | — | No packages added |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                 HA timer (_handle_refresh_interval)   update_entity (manual)   setup (first refresh)
                                  \                         |                     /
                                   v                        v                    v
                         XmltvCoordinator._async_update_data  ── sets trigger kind ──┐
                           |  cache start / 304 / identical / download+parse / file   |
                           |  failure -> backoff                                      |
                           v                                                          v
                 RefreshAttempt record ──persist──> cache Store {meta, health, attempt}
                           |                                    
                           +──dispatcher "attempt_<entry_id>"──> LastFetchSensor (per calendar device)
                           |
                 coordinator.data (EpgData, identity-compared)
                           | (only when the object changed)
                           v
          XmltvCalendarEntity._async_refilter(reason)
             executor: spec.apply(epg) -> feed matches
             loop:  1. capture ended matches from OLD index + NEW matches -> retained (if N>0)
                    2. prune retained (stop < now - N days), re-filter retained on config edits
                    3. index = feed matches + retained with UID not in feed (D-18)
                    4. diff future UIDs vs seen-set:
                         reason == data and baseline ready -> fire <= 50 events, rest silent + WARNING
                         reason in (initial, config)       -> add silently
                    5. prune seen-set, MatchStore.async_delay_save
                    6. write calendar state; dispatcher "matches_<subentry_id>"
                           |                                   |
                           v                                   v
              hass.bus "xmltv_calendar_new_match"     NextMatchSensor: state = next start > now
                           |                           async_track_point_in_utc_time(next.start) -> recompute
                           v
                 user automations / README examples

  Calendar entity ──(HA calendar trigger polls every 15 min)──> Blueprint automation (mode: queued)
                                                               -> notify.send_message / custom actions
  Subentry edit -> diffing listener -> async_apply_subentry -> _async_refilter(reason=config)
  Source options edit -> reload -> new entities -> _async_refilter(reason=initial)
  Tag push v0.1.0 -> release.yml: tag==manifest -> ci.yml + validate.yml (workflow_call) -> gh release create
```

### Recommended Project Structure

```
custom_components/xmltv_calendar/
├── __init__.py          # PLATFORMS += SENSOR; listener adds sensors for new subentries; unload flushes MatchStore
├── calendar.py          # refilter(reason), retention merge, new-match events, change signal
├── sensor.py            # NEW: NextMatchSensor, LastFetchSensor
├── match_store.py       # NEW: per-source Store of {subentry_id: {seen, retained}} (HA glue)
├── coordinator.py       # RefreshAttempt construction, trigger detection, dispatcher send
├── cache.py             # FeedCache stores {meta, health, attempt}
├── source.py            # Fetched.status / SourceUnavailableError.status for http_status
├── data.py              # runtime: add_entities per platform, match_store
├── diagnostics.py       # calendars[].retained, optional last_attempt
├── xmltv/
│   ├── settings.py      # KEY_RETENTION_DAYS + default 1, clamp 0..7 (with_defaults)
│   ├── window.py        # MatchIndex.next_after(now)
│   └── retention.py     # NEW pure: programme <-> dict, capture/prune/merge, seen-set diff/prune
└── translations/{en,de}.json   # entity.sensor.*, retention field, attribute states
blueprints/automation/xmltv_calendar/notify_before_programme.yaml   # NEW
.github/workflows/release.yml                                         # NEW
README.md                                                             # rewritten
```

New file and key names (`match_store.py`, `retention.py`, `retention_days`, signal names) are **proposals** [ASSUMED]. The planner fixes them in the plan.

### Pattern 1: Refilter with a reason (EVT-08 semantics without a fingerprint)

**What:** `_async_refilter(reason)` where `reason` is `"initial"` (from `async_added_to_hass`), `"data"` (from `_handle_coordinator_update`) or `"config"` (from `async_apply_subentry`). Events fire only when `reason == "data"` **and** a refilter has already completed in this entity's lifetime (`self._baseline_ready`).

**Why this covers D-10/D-11:**
- New calendar, restart and reload all start with an `initial` refilter, which is silent.
- A filter or template edit applies in place, so the refilter reason is `config`, which is silent (D-11 subentry part).
- A source timezone/offset change goes through `hass.config_entries.async_schedule_reload` (`__init__.py:36-37`), producing new entities and an `initial` refilter, which is silent (D-11 tz part).
- A coordinator update that arrives before the first refilter completes (the generation counter supersedes it) is still silent, because `_baseline_ready` is false.
- The persisted seen-set prevents re-fires for matches that drop out of the feed and come back across a restart.

**Generation counter interaction:** `calendar.py:147-162` already discards superseded runs. If a `config` run supersedes an in-flight `data` run, the new feed matches are absorbed silently. This is rare (an edit during a refresh) and acceptable. Document it in code.

```python
# Sketch only; names are proposals [ASSUMED]
async def _async_refilter(self, reason: str) -> None:
    self._generation += 1
    generation = self._generation
    epg = self.coordinator.data
    ...
    result = await self.hass.async_add_executor_job(partial(self._spec.apply, epg, tz=dt_util.get_default_time_zone()))
    if generation != self._generation:
        return
    now = dt_util.utcnow()
    record = self._match_store.calendar(self._subentry_id)          # seen + retained
    previous = self._feed_matches                                     # feed matches of the old index
    record.capture_ended(previous, result.matches, now)               # D-16, only if retention_days > 0
    if reason == "config":
        record.refilter_retained(self._spec, tz)                      # D-17
    record.prune(now, self._retention_days)                           # D-13, D-15
    new = record.diff_future(result.matches, now)                     # D-08, D-09; adds all to seen
    fire = reason == "data" and self._baseline_ready
    self._feed_matches = result.matches
    self._index = MatchIndex(merge(result.matches, record.retained))  # D-18
    self._baseline_ready = True
    self._match_store.async_schedule_save()
    self.async_write_ha_state()
    async_dispatcher_send(self.hass, signal_matches(self._subentry_id))
    if fire:
        self._fire_new_match_events(new)                              # cap 50 (D-12)
```

### Pattern 2: Next-match sensor (AUT-03, D-01..D-06)

- `MatchIndex.next_after(now)`: `i = bisect_right(self._starts, now)`, then return `self._programmes[i]` or `None`. Pure, add a TDD test in `tests/xmltv/test_window.py`. Retained programmes have ended, so they never qualify.
- The sensor holds `subentry_id` and on every signal reads `entry.runtime_data.calendars.get(subentry_id)`. If that is `None` (calendar not created yet, Pitfall 1), the state is `unknown`.
- `native_value` returns the aware start (`programme.start`). Attributes: `title` = `programme.title`, `summary` = `templates.render_title(...)` via `render.template_values`, `channel` (display name else ID, the same rule as `render.template_values`), `channel_id`, `start`/`end` as local ISO strings, `subtitle`, `episode`, `description`.
- `_unrecorded_attributes = frozenset({"description", "subtitle", "episode"})`. Recommend all three: they change with every match and add nothing to history.
- Timer: after every recompute, cancel the old unsub and arm `async_track_point_in_utc_time(hass, self._handle_start, next.start)`. Cancel it in `async_will_remove_from_hass` (or via `self.async_on_remove`).
- `available`: `self.coordinator.data is not None` (same as `calendar.py:131-133`). Subclass `CoordinatorEntity` so availability transitions write state.
- Device: identical `DeviceInfo` to the calendar's (`identifiers={(DOMAIN, subentry_id)}`, `name=subentry.title`, `entry_type=DeviceEntryType.SERVICE`, `calendar.py:114-118`). Factor out a helper so the three entities can't drift. Add the sensor with `async_add_entities([...], config_subentry_id=subentry_id)`.
- Naming: `_attr_has_entity_name = True`, `_attr_translation_key = "next_match"` (proposal), unique ID `f"{subentry_id}_next_match"` (proposal). With HA in German the object ID comes from the German name: `NATIVE_ENTITY_IDS` contains `"de"` (`generated/languages.py:75`), and `entity_platform.py:224-228` picks `hass.config.language` when it is in that set. Result: `sensor.<device>_nachste_sendung`, which matches D-05 [VERIFIED: .venv HA source].

### Pattern 3: Match store (seen-set + retention), one Store per source

```python
# Stored shape (proposal) [ASSUMED]
{
  "calendars": {
    "<subentry_id>": {
      "seen": {"<uid>": 1793000000, ...},          # uid -> stop as epoch seconds (pruning, D-13)
      "retained": [ {"channel_id": "...", "channel_name": "...", "start": "...Z", "stop": "...Z",
                     "titles": [...], "sub_titles": [...], "description": "...|null",
                     "categories": [...], "episode": "...|null"}, ... ]
    }
  },
  "source": {"naive_timezone": "utc", "offset_minutes": 0}   # optional tz fingerprint, Open Question 2
}
```

- **Key:** `f"{DOMAIN}.matches.{cache_key(entry)}"` (proposal). `cache_key` (`cache.py:223-228`) already produces a safe file-name component. It must not collide with the cache Store key `f"{DOMAIN}.{key}"` (`cache.py:175`). The `matches.` infix guarantees that.
- `private=True` (programme text is user data), `serialize_in_event_loop=False` with **immutable snapshots** (tuples, frozen `Programme`, dicts replaced instead of mutated). Retained data for a broad calendar can reach thousands of programmes. The Store docstring tells large stores to serialize off-loop (`storage.py:249-260`) [VERIFIED].
- Writes: `async_delay_save(self._data, 10)` after each refilter. **Flush on unload** with `await store.async_save(snapshot)` in `async_unload_entry`, before the platforms are unloaded or after (the state lives in the store object, so the order doesn't matter). A reload creates a **new** `Store` object for the same key. `async_load` only sees pending data held by the *same* object (`storage.py:342-352`), and the old object's timer can fire after the new one loaded (Pitfall 3).
- Load once in `async_setup_entry` before `async_forward_entry_setups` (no I/O in entity constructors).
- Remove in `async_remove_entry` next to `FeedCache(...).async_remove()` (`__init__.py:61-64`).
- Drop calendars whose subentry ID is no longer in `entry.subentries` when building the save snapshot.
- Tolerant reader like `CacheMeta.from_dict`/`SourceHealth.from_dict` (`cache.py:273-346`): anything malformed reads as empty, never raises. Hand-edited storage must not break setup.
- **Capture rule (EVT-07):** on every refilter, add matches with `stop <= now` from the old feed matches and from the new result. The old index matters because `coordinator._parser()` drops programmes with `stop < utcnow() - KEEP_PAST` at parse time (`coordinator.py:300-302`: `keep_after=dt_util.utcnow() - KEEP_PAST`). A match that ends between refreshes and is gone in the next feed exists only in the old index. Also capture once in `async_will_remove_from_hass`, then flush.
- **Prune:** retained with `stop < now - retention_days`. Seen entries with `stop < now - retention_days` (D-13). Pruning at `stop < now` would also be safe because only `start > now` fires (D-09), but D-13 asks for the retention window.
- **Retention 0:** no capture, retained cleared.
- **Cap:** recommend `MAX_RETAINED = 5000` per calendar (keep the newest by start) plus a DEBUG log. This bounds the Store for "all channels" calendars [ASSUMED: sizing judgement].

### Pattern 4: Last-fetch record (AUT-06, D-20..D-24)

Build one `RefreshAttempt` (frozen dataclass, proposal) per `_async_update_data` call, in a `try/finally` around the existing body (`coordinator.py:163-190`). Persist it with the health save.

| Attribute (proposal) | Values | Source in code |
|---|---|---|
| state (`native_value`) | aware UTC time the run started | `dt_util.utcnow()` at entry |
| `trigger` | `startup` / `scheduled` / `retry` / `revalidate` / `manual` | `startup` when `self.data is None`; otherwise the kind of the target the timer served (see below); else `manual` |
| `outcome` | `downloaded` / `read` / `not_modified` / `unchanged` / `cache_start` / `failed` | `_async_update_url` branches (`coordinator.py:353-399`), `_async_update_file` (`401-436`), `_async_start_from_cache` (`267-290`) |
| `http_status` | int or `None` | needs `Fetched.status` + a status on `SourceUnavailableError` (`source.py:224-228` raise `SourceUnavailableError(msg)` for `>= 400`). `None` for file sources and network errors |
| `failure_reason` | one of `FAILURE_REASONS` or `None` | `coordinator.py:65-67` |
| `cache` | `fresh_hit` / `stale_hit` / `written` / `touched` / `write_failed` / `dropped` / `none` | cache-start branch, `async_write` return value (`cache.py:414-440` returns `bool`), `async_touch` |
| `sent_etag`, `sent_last_modified` | bool | `meta.etag is not None` / `meta.last_modified is not None` when `meta` was passed to `_async_fetch` |
| `last_success`, `consecutive_failures` | from `SourceHealth` | `coordinator.health` |
| `next_refresh` | ISO | `coordinator.next_refresh_at` (read live, not persisted) |
| `bytes`, `programmes`, `channels`, `parse_duration` | ints / seconds | payload length, `EpgData.stats` (`ParseStats.programmes`, `.channels`), `time.monotonic()` around the parse |
| `matches` | int | this calendar's `match_count` (feed matches only) |

**Trigger detection** [VERIFIED: `helpers/update_coordinator.py:313-317` in 2026.10.1 and `:292-296` in 2026.3.0 both define `async def _handle_refresh_interval(self, _now=None)` which calls `_async_refresh(log_failures=True, scheduled=True)`]:

```python
# Sketch [ASSUMED names]
@override
async def _handle_refresh_interval(self, _now: datetime | None = None) -> None:
    self._run_trigger = self._target_kind   # "scheduled" | "retry" | "revalidate", set wherever _next_refresh_at is set
    try:
        await super()._handle_refresh_interval(_now)
    finally:
        self._run_trigger = None
# in _async_update_data: trigger = "startup" if self.data is None else (self._run_trigger or "manual")
```

`_target_kind` is set next to every `_next_refresh_at` assignment: `_set_regular_target` sets "scheduled", `_async_handle_failure` sets "retry", a stale cache start (`self._next_refresh_at = now`, `coordinator.py:289`) sets "revalidate", `fresh_until` sets "scheduled".

**Notification:** `_async_update_data` sends `async_dispatcher_send(hass, signal_attempt(entry_id))` after recording. Don't rely on coordinator listeners: with `always_update=False`, `_async_refresh` only calls `async_update_listeners()` when the data object or the success state changed (`update_coordinator.py:604-612`) [VERIFIED].

**Persistence (D-23):** extend `FeedCache._stored` (`cache.py:371-372`, currently `{"meta": ..., "health": ...}`) with `"attempt": ...`. Save health and attempt in **one** `async_save` so each run writes once. A cache start currently saves nothing, so it needs one save for the attempt. `async_drop`/`async_write`/`async_touch` all go through `_stored`, so the attempt survives them automatically. Use a tolerant `RefreshAttempt.from_dict`. Reason strings re-checked with the `_REASON` pattern (`cache.py:220`).

**Entity:** `EntityCategory.DIAGNOSTIC`, `_attr_entity_registry_enabled_default = False`, `device_class=TIMESTAMP`, unique ID `f"{subentry_id}_last_fetch"` (proposal), same device as the calendar. `_unrecorded_attributes`: everything except `outcome`/`trigger` is a candidate, at minimum `next_refresh`, `parse_duration`, `bytes` (they change on every run).

### Pattern 5: Retention setting in the advanced step (D-14, D-15)

- `xmltv/settings.py`: add `KEY_RETENTION_DAYS = "retention_days"` (proposal), default `1`, and a tolerant reader `_retention(value)`. Bool, non-int and NaN read as the default. Clamp to `0..7`. Add it to `ADVANCED_DEFAULTS` **at the end**: `tests/xmltv/test_settings.py:96,193` assert `ADVANCED_DEFAULTS == {key: FULL_DEFAULTS[key] for key in list(FULL_DEFAULTS)[4:]}`, so key order matters. `with_defaults` currently returns exactly the 14 contract keys (STATE 02-02), so that test's expected dict grows by one.
- Since `has_advanced` uses `ADVANCED_DEFAULTS`, a non-default retention pre-checks the "Advanced options" box. That's correct.
- `config_flow.py:_advanced_schema` (`465-480`): add `vol.Optional(CONF_RETENTION_DAYS): NumberSelector(NumberSelectorConfig(min=0, max=7, step=1, mode=NumberSelectorMode.BOX))`. `_advanced_values` (`483-505`): `int(value)` if present, else default 1 (a cleared field means default, D-15). `_advanced_suggestions` picks it up through `ADVANCED_DEFAULTS` without changes.
- `FilterSpec.from_mapping` and `EventTemplates.from_mapping` go through `with_defaults` and ignore keys they don't use. A retention-only edit still triggers a refilter (`calendar.py:186-194`). That's cheap and handles the D-17 re-check uniformly.
- Unit: NumberSelector's `unit_of_measurement` is a raw, untranslated string. Put "days"/"Tage" in the translated label instead ("Keep past matches (days)" / "Vergangene Treffer behalten (Tage)").

### Pattern 6: Blueprint (AUT-05, D-26..D-28)

```yaml
# blueprints/automation/xmltv_calendar/notify_before_programme.yaml  (sketch; texts are proposals)
blueprint:
  name: XMLTV Calendar - notify before a matching programme starts
  description: >-
    Runs the actions once per matching programme, a set time before it starts.
    Overlapping programmes each run once (mode queued).
  domain: automation
  source_url: https://github.com/akentner/homeassistant-xmltv-calendar-integration/blob/main/blueprints/automation/xmltv_calendar/notify_before_programme.yaml
  homeassistant:
    min_version: 2026.3.0
  input:
    calendar:
      name: Calendar
      selector:
        entity:
          filter:
            - integration: xmltv_calendar
              domain: calendar
    offset:
      name: Offset
      description: Negative = before the programme starts.
      default: "-00:10:00"
      selector:
        duration:
          allow_negative: true
    notify_entity:
      name: Notify entity
      default: []
      selector:
        entity:
          multiple: true
          filter:
            - domain: notify
    actions:
      name: Actions
      description: Runs once per programme. Variables: title, channel, start, end, description.
      default:
        - action: notify.send_message
          target:
            entity_id: "{{ notify_entity }}"
          data:
            title: "{{ title }}"
            message: "{{ channel }}, {{ start_time }}"
      selector:
        action: {}
mode: queued
max: 20
max_exceeded: warning
triggers:
  - trigger: calendar
    event: start
    entity_id: !input calendar
    offset: !input offset
variables:
  notify_entity: !input notify_entity
  title: "{{ trigger.calendar_event.summary }}"
  channel: "{{ trigger.calendar_event.location }}"
  start: "{{ trigger.calendar_event.start }}"
  end: "{{ trigger.calendar_event.end }}"
  description: "{{ trigger.calendar_event.description }}"
  start_time: "{{ as_timestamp(trigger.calendar_event.start) | timestamp_custom('%H:%M') }}"
actions: !input actions
```

Verified facts behind this sketch:
- The legacy single-entity trigger takes `entity_id`, `event` (`start`/`end`) and `offset` (`cv.time_period`). The offset is **not templatable** (`components/calendar/trigger.py:53-59`). So the negative sign must come from the input value, not a template [VERIFIED].
- `cv.time_period` accepts the string `"-00:10:00"` and the dict the frontend sends [ASSUMED: string parsing of a leading minus from training knowledge. Cover it with the e2e test].
- Duration selector `allow_negative` exists in core 2026.3.0 (`helpers/selector.py:843-872`) and 2026.10.1 (`selector.py:1043-1082`). Frontend `20260304.0` `ha-selector-duration.ts` passes `.allowNegative=${this.selector.duration?.allow_negative}` and parses a leading `-` in string values [VERIFIED: raw GitHub, this session].
- `trigger.calendar_event` is `CalendarEvent.as_dict()`: `start, end, summary, description, location, uid, recurrence_id, rrule, status` plus `all_day`. Datetimes become strings via `event_dict_factory` [VERIFIED: `components/calendar/__init__.py:179-213`]. `location` is the channel display name (EVT-02), and `summary` is the rendered title.
- `notify.send_message` targets `notify` entities and has a required `message` and an optional `title` (feature-filtered) [VERIFIED: `components/notify/services.yaml`]. In 2026.10 `mobile_app` registers `Platform.NOTIFY` entities (`mobile_app/__init__.py:70`, `notify.py:76 class MobileAppNotifyEntity(NotifyEntity)`). At 2026.3.0 `mobile_app` still loads notify via `discovery.async_load_platform`, so older installs may have no mobile notify **entity**. The README must say: replace the default action with `notify.mobile_app_<device>` there [VERIFIED: raw GitHub 2026.3.0].
- Blueprint import from GitHub: the importer turns `https://github.com/<repo>/blob/<path>` into a raw URL and stores the blueprint as `<owner>/<file>` (`blueprint/importer.py:28-29,160-177`). The README button: `https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=<url-encoded blob URL>` [CITED: home-assistant.io/docs/automation/using_blueprints]. The repo must be public. STATE says it is.
- HA docs: "Calendar triggers should not generally use automation mode `single` … use `queued` or `parallel` instead." [CITED: home-assistant.io/integrations/calendar]. The calendar listener dispatches every queued event of a window separately (`trigger.py:278-288`), so with `mode: queued` two programmes that start together give two runs.
- `default:` of the action input contains plain templates that reference **blueprint variables**. `!input` is not resolved inside another input's default [ASSUMED. The e2e test must cover the default action].

### Pattern 7: Release workflow (DST-03) and README (DST-04)

- Copy `../homeassistant-mqtt-actions-integration/.github/workflows/release.yml` verbatim. Change only line 28: `manifest_version=$(jq -r .version custom_components/mqtt_actions/manifest.json)` becomes `custom_components/xmltv_calendar/manifest.json`. The tag regex `^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$`, `--verify-tag --generate-notes` and the `*-*` → `--prerelease` case stay [VERIFIED: sibling file read this session].
- It already satisfies every parametrized check in `tests/test_repo_structure.py`: `permissions: {}`, SHA-pinned checkout with `persist-credentials: false`, local `./.github/workflows/*.yml` refs that exist, `ubuntu-24.04`, a push trigger without branch filters or path filters. Add `"release.yml"` to `WORKFLOW_FILES` (line 16) and add a test asserting the tag check reads `custom_components/xmltv_calendar/manifest.json` and `needs: [check-version, ci, validate]`.
- `ci.yml`/`validate.yml` already have `workflow_call` and `tags-ignore: ["v*.*.*"]` (`ci.yml:3-10`, `validate.yml:3-12`), so a tag push runs checks once, through the release workflow.
- HACS: "If the repository uses GitHub releases, the tag name from the latest release is used to set the remote version." and "Just publishing tags is not enough, you need to publish releases." [CITED: hacs.xyz/docs/publish/start]. `manifest.json` is `"version": "0.1.0"` (`manifest.json:11`), so the first tag is `v0.1.0` (D-29).
- README outline: Installation (HACS custom repo, HA ≥ 2026.3; `tests/test_repo_structure.py:148-152` asserts the repo URL, "HACS" and "2026.3"), Adding a source (URL/file, refresh interval vs daily-at, timezone options, cache), Adding calendars (channels, channel regex, include/exclude with examples such as `formel\s*1|formula\s*1`, `^Tatort$`, `Wiederholung`, advanced options, templates and placeholders, retention), Entities (calendar, next-programme sensor + attributes, last-fetch diagnostic sensor + how to enable it), Event `xmltv_calendar_new_match` with payload table, Automation examples (calendar trigger with offset, next-match sensor template, new-match event), Blueprint import button, Limitations (15-min polling: "calendars are read once every 15 minutes", events added less than 15 min ahead may not trigger; overlapping events: the calendar state/attributes show only one, triggers fire per event, use `queued`; manual refresh via `homeassistant.update_entity`; refresh interval anchored to the last restart, so prefer daily-at), Diagnostics, License.

### Anti-Patterns to Avoid
- **Listening to coordinator updates for the last-fetch sensor.** Unchanged data (304, identical body, unchanged file) doesn't notify listeners. Use the dispatcher signal.
- **Firing events from every refilter.** Reload, restart, tz change and filter edits would spam. Gate on `reason == "data"` plus `_baseline_ready`.
- **Using `calendar.event_started` in the blueprint.** It is labs-gated at the 2026.3 floor.
- **Templating `offset` in the calendar trigger.** Not supported (`cv.time_period`, no template).
- **Putting the full retained list or the seen-set into entity attributes.** Recorder bloat, 16 KB attribute limit (PITFALLS 25, AF-4).
- **Mutating the Store snapshot after `async_delay_save` with `serialize_in_event_loop=False`.** The data function runs in a worker thread. Replace containers instead.
- **Doing Store I/O in entity `__init__`.** Load in `async_setup_entry`.
- **A per-calendar Store deleted from `async_will_remove_from_hass`.** That runs on every reload too, which would wipe the seen-set.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Timer at next match start | `asyncio.sleep` loops, own `call_later` | `async_track_point_in_utc_time` | Works with HA time-change events in tests (`async_fire_time_changed`), cancels cleanly |
| Persistent JSON state | Own JSON file writes | `homeassistant.helpers.storage.Store` (+ `async_delay_save`) | Atomic-ish writes, final-write flush on shutdown, versioning, `hass_storage` test fixture |
| Cross-entity notification | Shared mutable globals | `homeassistant.helpers.dispatcher` | Ordering-independent, auto-unsub via `async_on_remove` |
| Blueprint validation | Hand-written YAML checks | `homeassistant.components.blueprint.models.Blueprint(data, expected_domain="automation")` / `BLUEPRINT_SCHEMA`, plus loading the blueprint into an automation in a test | Same validator HA uses on import |
| Release publishing | Custom scripts, tag-creating bots | Sibling `release.yml` (`gh release create --verify-tag --generate-notes`) | Already reviewed and tested in the sibling repo |
| Entity ID localization | Building object IDs yourself | `has_entity_name` + `translation_key` | HA chooses the language via `NATIVE_ENTITY_IDS` |
| UID computation | A new hash | `render.event_uid` (`xmltv/render.py:164-168`): `f"{programme.channel_id}-{start:%Y%m%dT%H%M%SZ}-{zlib.crc32(programme.title.encode()):08x}"` | D-08 ties "new" to the existing UID contract |

**Key insight:** every new capability is a thin layer on HA primitives plus small pure functions. The risk is in lifecycle ordering (concurrent platform setup, reload vs delayed save, generation supersession), not in algorithms.

## Runtime State Inventory

Not a rename/refactor phase. One runtime-state note still applies: the **new Store** `xmltv_calendar.matches.<key>` and the new `attempt` key in the existing `xmltv_calendar.<key>` Store are additive. Old Stores without `attempt` read as "no attempt yet" through a tolerant reader. No migration, no `STORE_VERSION` bump (`cache.py:217 STORE_VERSION = 1`) as long as the reader tolerates the missing key.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Existing cache Store `{meta, health}` per source on `ha-host` (Phase 3) | Code edit only: tolerant read of a missing `attempt` |
| Live service config | None. Verified: no external service holds integration names | none |
| OS-registered state | None | none |
| Secrets/env vars | None | none |
| Build artifacts | None (no packaging) | none |

## Common Pitfalls

### Pitfall 1: Sensors set up before their calendar entity
**What goes wrong:** `async_forward_entry_setups` runs the platforms concurrently (`config_entries.py:2944-2959`: `await asyncio.gather(*(create_eager_task(self._async_forward_entry_setup(entry, platform, False), ...) for platform in platforms))`), so the sensor's `async_added_to_hass` can run before `runtime.calendars[subentry_id]` exists.
**How to avoid:** the sensor treats a missing calendar as "no data yet" (state `unknown`) and subscribes to the signal. The calendar sends the signal after its first refilter.
**Warning signs:** `KeyError` / `AttributeError` in sensor setup in tests that create several subentries.

### Pitfall 2: The listener only knows one `add_entities`
**What goes wrong:** `_async_entry_updated` (`__init__.py:34-51`) adds calendars for new subentries through `runtime.add_entities` (the calendar platform callback) and returns early when it is `None`. Sensors for a subentry added later would never be created.
**How to avoid:** store one callback per platform (`runtime.add_entities: dict[Platform, AddConfigEntryEntitiesCallback]`), and create the sensors in the sensor platform's own loop plus in the listener. Update `test_init.py` expectations that count entities.

### Pitfall 3: Delayed save of the old Store overwrites data after a reload
**What goes wrong:** `async_delay_save` arms a loop timer on the Store object. A reload builds a new `Store` for the same key, which loads from disk without the old object's pending data. The old timer then writes stale data.
**How to avoid:** on `async_unload_entry`, call an explicit flush (`await store.async_save(snapshot)`, which runs `_async_handle_write_data` and cancels the delay listener, `storage.py:569-583`). Test: edit source options (reload), fire a new-match refresh, reload again, and assert the seen-set contains the UID.

### Pitfall 4: Retention > 1 day silently ineffective
**What goes wrong:** only capturing ended matches from the *new* parse misses everything the parser already dropped (`keep_after = now - KEEP_PAST`) or the feed stopped publishing.
**How to avoid:** capture from the old index before swapping, on every refilter, and on entity removal. Test with freezer: day 0 match, day 1 refresh with a feed lacking it, day 3 `get_events` for day 0 still returns it (retention 3), and after `hass` restart (unload/setup) too.

### Pitfall 5: Event burst after a feed shift
**What goes wrong:** a provider changes channel IDs or times. Hundreds of new UIDs fire at once.
**How to avoid:** cap at 50 per calendar per refresh (D-12), ordered by start ascending, one WARNING with calendar name and suppressed count, and all of them added to the seen-set.

### Pitfall 6: Non-JSON event data
**What goes wrong:** `datetime` objects in `hass.bus.async_fire` data show up inconsistently in websocket/logbook consumers and templates.
**How to avoid:** payload `start`/`end` as `dt_util.as_local(...).isoformat()` strings. Users can `as_datetime()` them in templates. Document it in the README.

### Pitfall 7: Disabled-by-default entity invisible in tests
**What goes wrong:** the last-fetch sensor has no state object in tests. phcc does not ship core's `entity_registry_enabled_by_default` fixture (only defined in HA core's own `tests/conftest.py`. Checked: absent from `pytest_homeassistant_custom_component/plugins.py`).
**How to avoid:** add a local fixture that patches `Entity.entity_registry_enabled_default` to `True` (PropertyMock) or enables the entry via `entity_registry.async_update_entity(..., disabled_by=None)` plus a reload.

### Pitfall 8: Blueprint default action runs with an empty notify target
**What goes wrong:** the user imports, picks a calendar, keeps the default action, and picks no notify entity. `notify.send_message` with an empty `entity_id` errors at runtime.
**How to avoid:** either make `notify_entity` required (no `default`) and document "replace the action if you don't use notify entities", or wrap the default action in `if: "{{ notify_entity | count > 0 }}"`. Recommendation: required input. It is simpler and fails visibly in the editor.

### Pitfall 9: 15-minute trigger window vs refresh timing
**What goes wrong:** the calendar trigger fetches events for the next 15-minute window (`UPDATE_INTERVAL`). A match that appears in the calendar after its window was fetched (refresh within the last 15 min before start, or within `offset` of it) never triggers.
**How to avoid:** document it (D-30). Recommend the daily-at refresh time well ahead of prime time and the new-match event for "appears late" cases.

### Pitfall 10: Translation keys that exist only in code
**What goes wrong:** a new abort reason or error key added to a flow without an `en.json` entry shows the raw key in both languages. The existing parity test only compares en vs de.
**How to avoid:** add a completeness test that collects `step_id="..."`, `reason="..."`, `errors[...] = "..."`, `{"base": "..."}`, `progress_action="..."` and the `TemplateError` reasons (`INVALID_TEMPLATE`, `UNKNOWN_PLACEHOLDER`) from `config_flow.py` (AST walk) and asserts their keys exist. HA-generated aborts used here: `already_configured` (from `_abort_if_unique_id_configured`) and `reconfigure_successful` (from `async_update_and_abort`). Both are present today (`en.json:94-96`, `183-185`).

### Pitfall 11: Retained programmes rendered after their channel left the feed
**What goes wrong:** `render.template_values` falls back to the channel ID when `channels.get()` is `None`. A retained match whose channel no longer exists in `EpgData.channels` would show the raw ID as location and `{channel}`.
**How to avoid:** store `channel_name` with each retained programme and pass a merged channel map (feed channels + retained names) to rendering.

## Code Examples

### Firing capped new-match events
```python
# Sketch; constants and helper names are proposals [ASSUMED]
MAX_NEW_MATCH_EVENTS = 50
EVENT_NEW_MATCH = f"{DOMAIN}_new_match"   # == "xmltv_calendar_new_match" (D-07); DOMAIN from const.py:41

def _fire_new_match_events(self, new: Sequence[Programme]) -> None:
    channels = self._epg.channels if self._epg is not None else {}
    ordered = sorted(new, key=attrgetter("start"))
    for programme in ordered[:MAX_NEW_MATCH_EVENTS]:
        channel = channels.get(programme.channel_id)
        values = render.template_values(programme, channel)
        self.hass.bus.async_fire(EVENT_NEW_MATCH, {
            "entity_id": self.entity_id,
            "calendar": self._subentry_title,
            "title": programme.title,
            "summary": self._templates.render_title(programme, values),
            "channel": values["channel"],
            "channel_id": programme.channel_id,
            "start": dt_util.as_local(programme.start).isoformat(),
            "end": dt_util.as_local(programme.stop).isoformat(),
            "uid": render.event_uid(programme),
        })
    if (suppressed := len(ordered) - MAX_NEW_MATCH_EVENTS) > 0:
        _LOGGER.warning("Calendar %s: %d new matches not announced (limit %d per refresh)",
                        self.entity_id, suppressed, MAX_NEW_MATCH_EVENTS)
```

### Next-match lookup (pure)
```python
# xmltv/window.py addition (sketch)
from bisect import bisect_right

def next_after(self, now: datetime) -> Programme | None:
    """Return the earliest match whose start is strictly after `now` (D-01)."""
    i = bisect_right(self._starts, now)
    return self._programmes[i] if i < len(self._programmes) else None
```

### Test: blueprint end to end (shape)
```python
# Sketch: copy the shipped YAML into the test config dir, then use_blueprint
target = Path(hass.config.path("blueprints/automation/xmltv_calendar"))
target.mkdir(parents=True)
shutil.copy(ROOT / "blueprints/automation/xmltv_calendar/notify_before_programme.yaml", target)
calls = async_mock_service(hass, "test", "automation")
assert await async_setup_component(hass, "automation", {"automation": {"use_blueprint": {
    "path": "xmltv_calendar/notify_before_programme.yaml",
    "input": {"calendar": "calendar.f1", "offset": "-00:05:00", "notify_entity": [],
              "actions": [{"action": "test.automation", "data": {"title": "{{ title }}"}}]}}}})
# freezer: step minute by minute across a 15-min boundary as tests/test_calendar.py:236-239 does;
# two programmes at the same start -> len(calls) == 2
```
Run the blueprint file I/O in the executor in the test, or use `hass.async_add_executor_job`. The `forbid_loop_io` fixture only guards integration code.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `platform: calendar` key | `trigger: calendar` inside `triggers:` | HA 2024.10 | Blueprint uses `triggers:`/`trigger:`/`actions:` syntax (tests in this repo already do, `test_calendar.py:211-215`) |
| Legacy calendar trigger only | Target-based `calendar.event_started` / `event_ended` with `offset_type` | Present at 2026.3 behind labs flag `new_triggers_conditions`. Not gated in 2026.10.1 source (no labs check found in `helpers/trigger/`) | Legacy trigger for the 2026.3 floor. Re-evaluate when raising the floor |
| `notify.<service>` legacy services | `notify.send_message` to notify entities | Notify entities 2024.x. `mobile_app` entities by 2026.10 | Default action targets entities; README covers the legacy fallback |
| voluptuous | `probatio` (schema library in HA 2026.10 blueprint/selector code) | HA 2026.x | Irrelevant to the integration (it uses `vol` in flows, which still works) [VERIFIED: imports seen in `blueprint/schemas.py`] |

**Deprecated/outdated:** none of the APIs used here are deprecated in 2026.10.1.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `cv.time_period` parses the string `"-00:10:00"` as −10 min, and the frontend's negative duration dict is accepted by the legacy calendar trigger | Pattern 6 | Blueprint default fires at the wrong time. The e2e test with `offset: "-00:05:00"` plus a UAT import covers it |
| A2 | `!input` is not resolved inside another input's `default`, so the default action must use blueprint variables | Pattern 6 | Low. The variables approach works either way |
| A3 | Dispatcher / `hass.bus.async_fire` APIs unchanged (not re-read this session) | Standard Stack | Very low |
| A4 | `MAX_RETAINED = 5000` per calendar is a sensible Store bound | Pattern 3 | Store size or a truncated "past days" view for very broad calendars |
| A5 | HACS offers prereleases only to users who enable beta | Pattern 7 | Low. Affects only `-rc` tags |
| A6 | Proposed names (`retention_days`, `next_match`, `last_fetch`, store key, signal names, attribute vocabularies) | Patterns 2-5 | Naming only, but several become contracts (D-03, D-07, D-14). The planner must lock them in the plan |

## Open Questions

1. **Should the last-fetch record also appear in diagnostics?**
   - What we know: D-22 says "keep them consistent with diagnostics". The CONTEXT says "possibly the last attempt".
   - Recommendation: yes. Add `last_attempt` with the same keys as the sensor attributes, produced by one shared `as_dict()`. Diagnostics tests assert exact shapes (`test_diagnostics.py:74,107,137,168`), so they need updates anyway for `retained`.

2. **What happens to retained programmes when the source tz/offset options change?**
   - What we know: D-11 covers events only. Retained programmes carry times shifted by the old correction (`coordinator._parser` applies `shift`), so after a change they show at old times, possibly next to re-captured copies.
   - Recommendation: store the source's `(naive_timezone, offset_minutes)` in the match store and drop all retained programmes (keep the seen-set) on mismatch at load. Cheap and consistent with "all UIDs change".

3. **Retention capture for downtime longer than `KEEP_PAST`.**
   - What we know: matches that end while HA is down are captured after restart only if the cached feed still holds them (ended < 1 day ago).
   - Recommendation: accept and document. No point-in-time capture timers.

4. **AUT-06 bookkeeping.** The planner must add AUT-06 to REQUIREMENTS.md (v1 Automation + traceability, Phase 4) and to the ROADMAP Phase 4 requirement list (CONTEXT canonical refs).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv with HA 2026.10.1 + phcc 0.13.372 | all tests | ✓ | `.venv/lib/python3.14`, HA `2026.10.1` (`const.py:24-26`) | — |
| uv | test/lint runs | ✓ | 0.12.7 locally (CI uses setup-uv) | — |
| Test suite | regression gate | ✓ | 820 passed, 1 skipped, 4 deselected in 18.7 s (`uv run pytest -q -m "not benchmark"`, this session) | — |
| gh CLI | user-side release inspection | ✓ | 2.102.0 | GitHub web UI |
| Docker | local hassfest container | ✗ (podman 6.1.4 present) | — | podman, or rely on the CI hassfest job |
| GitHub repo (public), Actions | DST-03 | ✓ remote `origin` set. No tags yet (`git tag` empty) | — | — |
| `ha-host` / `ha-dev` | UAT of sensors, blueprint import, German UI | not probed (UAT only) | — | `ha-dev` on host port 18123 (STATE 01-09) |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** Docker → podman or CI.

## Security Domain

`security_enforcement: true`, ASVS level 1.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | HA handles entity/event access |
| V5 Input Validation | yes | `with_defaults` tolerant read + clamp for `retention_days`. Tolerant `from_dict` readers for the match Store and `attempt`. Release tag validated by regex before use (sibling workflow) |
| V6 Cryptography | no | crc32 in UIDs is an identifier, not security |
| V7 Error Handling & Logging | yes | No URL/host/path in sensor attributes, event payloads or logs (D-24). Failure reasons only as `FAILURE_REASONS` keys. `http_status` is a number |
| V8 Data Protection | yes | Match Store `private=True` (file mode 0600 like the cache Store). Diagnostics stay allow-list based |
| V10 Malicious Code / supply chain | yes | Release workflow: `permissions: {}` at top, `contents: write` only on the release job, SHA-pinned actions, `persist-credentials: false` (tests enforce) |
| V12 Files & Resources | yes | Store key derived from `cache_key` (safe charset or SHA-256). Retained/seen caps bound disk use |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Tag-name injection into shell (`GITHUB_REF_NAME`) | Tampering | Validate with the SemVer regex first, use it only as a quoted variable (sibling `release.yml:23-27`) |
| Feed text in event payload / attributes used in user templates | Tampering | Payload values are data. HA does not render event data as templates. Templates in the blueprint only interpolate them |
| Hand-edited `.storage` crashing setup | DoS | Tolerant readers, never raise, malformed reads as empty |
| Event flood from a malicious/changed feed | DoS | Burst cap 50 per calendar per refresh + seen-set |
| Store growth | DoS | Prune by retention window, cap retained programmes, drop removed subentries |
| Leaking source URL via the new diagnostic sensor | Information disclosure | Attribute allow-list without host/URL. Add a test that asserts the feed URL/host is absent from all states and attributes |

## Sources

### Primary (HIGH confidence)
- Installed HA 2026.10.1 source (`.venv/lib/python3.14/site-packages/homeassistant/`): `helpers/update_coordinator.py` (refresh flow, `always_update`, `_handle_refresh_interval`), `helpers/storage.py` (Store API, delayed save, pending-data load), `helpers/entity.py` (unrecorded attributes, attribute translations), `helpers/entity_platform.py` + `generated/languages.py` (object-ID language), `config_entries.py` (concurrent platform setup), `components/calendar/trigger.py` + `triggers.yaml` + `__init__.py`, `components/blueprint/schemas.py` + `importer.py`, `components/notify/services.yaml`, `components/mobile_app/`, `helpers/selector.py`, `components/sensor/__init__.py`
- HA core at tag 2026.3.0 (raw GitHub, this session): `components/calendar/trigger.py` (TRIGGERS incl. `event_started`), `helpers/trigger.py` (labs gating), `helpers/selector.py` (`allow_negative`), `helpers/update_coordinator.py` (`_handle_refresh_interval`), `components/mobile_app/__init__.py`
- HA frontend tag `20260304.0` and `dev`: `ha-selector-duration.ts`, `ha-duration-input.ts` (negative durations)
- Repo files read this session: `calendar.py`, `coordinator.py`, `cache.py`, `source.py`, `__init__.py`, `const.py`, `data.py`, `diagnostics.py`, `config_flow.py` (436-710), `xmltv/{settings,render,window,model,filter}.py`, `translations/en.json`, `manifest.json`, `hacs.json`, workflows, `tests/{conftest,test_translations,test_repo_structure}.py`
- Sibling `homeassistant-mqtt-actions-integration/.github/workflows/release.yml` (full file)

### Secondary (MEDIUM confidence)
- https://www.home-assistant.io/integrations/calendar/ (15-min read cycle, `queued`/`parallel` advice)
- https://www.home-assistant.io/docs/automation/using_blueprints/ (import link format, storage path)
- https://www.hacs.xyz/docs/publish/start/ (releases vs tags)

### Tertiary (LOW confidence)
- None used for decisions.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. Every API was read in the installed HA source, and the floor-sensitive ones also at 2026.3.0.
- Architecture: HIGH for seams and lifecycle facts (read in source). MEDIUM for proposed structure (judgement).
- Pitfalls: HIGH. Each is derived from code read this session (parser cut-off, `always_update`, concurrent setup, Store pending data).
- Blueprint runtime behaviour: MEDIUM until the e2e test runs (A1, A2).

**Research date:** 2026-10-21
**Valid until:** 2026-11-20 (HA monthly release cadence. Re-check labs gating of `calendar.event_started` when raising the floor)
