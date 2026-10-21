# Phase 4: Automation Extras & Release - Context

**Gathered:** 2026-10-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can automate around matches beyond plain calendar triggers, and they can install a documented, tagged release via HACS:
- one next-match timestamp sensor per calendar (AUT-03)
- an HA event when a new matching programme appears in the feed (EVT-08)
- past matches retained for N days after the feed drops them, across restarts (EVT-07)
- a shipped blueprint "notify before a matching programme starts", `mode: queued` (AUT-05)
- every flow step, error and abort reason in German and English (CFG-04)
- tagged GitHub releases whose version matches `manifest.json` (DST-03), and a full README (DST-04)
- **added in this discussion:** a "last fetch" diagnostic sensor per calendar device (new requirement, proposed ID **AUT-06**; the planner adds it to REQUIREMENTS.md and the Phase 4 requirement list in ROADMAP.md)

Requirements: AUT-03, AUT-05, AUT-06 (new), EVT-07, EVT-08, CFG-04, DST-03, DST-04.
Not in this phase: the refresh bug reported during this discussion (handled separately via `/gsd-debug`, see Blocker below), the v2 filters (FLT-12..14), episode normalization (EVT-09).

### Blocker (outside this phase's plans)
The user ran a calendar for several days on their test HA instance. New entries only showed up after a **manual reload of the integration**. Scheduled refreshes, the cache or the refilter apparently did not bring new feed data into the calendar. The root cause is unknown. It is handled in a **separate `/gsd-debug` session** before or alongside Phase 4 planning. EVT-07, EVT-08 and the next-match sensor all depend on refreshes that work, so Phase 4 verification must not pass while the bug is open. The new last-fetch sensor (D-20..D-24) is meant to make this kind of problem visible without a debugger.

</domain>

<decisions>
## Implementation Decisions

### Next-match sensor (AUT-03)
- **D-01:** The state is the start of the next match that has **not started yet** (`start > now`). A match that is airing does not count. "Airing now" is already covered by the calendar entity's `event` (AUT-02). `device_class: timestamp`.
- **D-02:** With no future match, the sensor stays **available** and its state is `unknown`. The match attributes are absent or `None`. `unavailable` is only used the way the calendar uses it (no coordinator data at all, Phase 3 D-19).
- **D-03:** Attributes: `title` (raw feed title), `summary` (event title rendered from the calendar's title template), `channel` (display name), `channel_id`, `start`, `end`, `subtitle`, `episode`, `description`. — **Reversibility:** costly — attribute names become a contract for user automations and templates. Renaming them breaks those automations.
- **D-04:** `description` is excluded from the recorder via `_unrecorded_attributes`. `subtitle`/`episode` may also be excluded (Claude's discretion). The recorder must not grow with every state change.
- **D-05:** The sensor sits on the **same device as its calendar** (the subentry device), with `has_entity_name` and a `translation_key`. The translated name is "Next programme" / "Nächste Sendung", so a German UI gives an entity ID like `sensor.formel_1_nachste_sendung`. It is **enabled by default**. Unique ID is derived from the subentry ID.
- **D-06:** The sensor updates when a match passes its start, without waiting for a coordinator refresh (point-in-time tracking or equivalent), when the feed data changes, and when the calendar's filter or templates are edited (in place, no reload, Phase 2 D-04).

### New-match event (EVT-08)
- **D-07:** **One event per new match**, event type `xmltv_calendar_new_match`. The payload has `entity_id` (calendar), `calendar` (calendar name), `title`, `summary`, `channel`, `channel_id`, `start`, `end`, `uid`. — **Reversibility:** one-way — the event type and payload keys are a published contract that user automations and the README examples depend on.
- **D-08:** A match is "new" when its **UID** (`<channel_id>-<UTC start>-<crc32(title)>`, EVT-06) is not in the calendar's persisted seen-set. A programme that moves or is renamed gets a new UID and fires again. This is accepted.
- **D-09:** Only matches with `start > now` fire. Matches that have started or ended join the seen-set silently.
- **D-10:** No events on the first refresh of a new calendar, and none after a restart or reload. The seen-set is persisted per calendar in an HA `Store`, shared with retention (D-14) as the roadmap notes.
- **D-11:** A **configuration change sets a new baseline silently**: when a calendar's filter changes (subentry edit), and when a source's timezone/offset options change (all UIDs change, Phase 3 D-16), the newly matching UIDs join the seen-set without events. Events only come from new feed data, never from config edits.
- **D-12:** **Burst cap:** at most about 50 events per calendar per refresh (exact number is Claude's discretion). The rest join the seen-set silently, with one WARNING log line naming the calendar and the number suppressed.
- **D-13:** The seen-set is pruned. A UID can be dropped once its programme has ended and is out of the retention window, so the Store does not grow without bound.

### Past matches (EVT-07)
- **D-14:** Retention is **per calendar**: a new key in the calendar subentry's advanced section, stored flat next to the Phase 2 keys, integer days 0..7. Editing it applies in place through the diffing listener, with no reload. — **Reversibility:** costly — a new stored subentry key. Renaming it later needs a migration, or a with_defaults fallback that reads both names.
- **D-15:** **Default 1 day**, which matches today's behaviour (`KEEP_PAST = 1 day`, `const.py:75`). A missing key means the default (Phase 2 D-06 rule, no migration).
- **D-16:** Only **ended** matches (`end <= now`) are retained. A future or airing match that disappears from the feed also disappears from the calendar, because the feed is the truth about the future.
- **D-17:** The store holds the **raw programme data** of retained matches, not rendered events. When the filter changes, retained programmes are checked against the new filter, and the ones that no longer match are dropped. Templates are applied at render time, as for feed matches. A widened filter cannot bring back past programmes that were never stored. That is accepted.
- **D-18:** Merge rule: the calendar shows feed matches plus retained programmes whose **UID is not in the current feed**. A corrected past slot with a different title, and so a different UID, can show twice. That is accepted.
- **D-19:** Diagnostics list `matches` (from the feed) and `retained` (store only) separately per calendar. This extends the Phase 3 D-21 calendar entry.

### Last-fetch diagnostic sensor (AUT-06, added)
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

### Blueprint (AUT-05)
- **D-26:** Trigger: `platform: calendar`, `event: start`, with a negative `offset` from a lead-time input. `mode: queued`, so overlapping matches each notify once (success criterion 3).
- **D-27:** Inputs: calendar entity (selector filtered to integration `xmltv_calendar`, domain `calendar`), lead time (duration, sensible default such as 10 min), and an **action selector** whose default is `notify.send_message` to a selectable notify entity. The blueprint defines variables (`title`, `channel`, `start`, and so on, from `trigger.calendar_event`) for use in the actions. That covers mobile app, TTS and Telegram.
- **D-28:** The blueprint ships in the repo under `blueprints/automation/…`. The README has the "Import blueprint" button (my.home-assistant.io redirect).

### Release & docs (DST-03, DST-04, CFG-04)
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope & requirements
- `.planning/ROADMAP.md` § "Phase 4: Automation Extras & Release": goal, success criteria 1–5, note "EVT-07 and EVT-08 share one persisted match store", copy the release workflow from mqtt-actions
- `.planning/REQUIREMENTS.md`: AUT-03, AUT-05, EVT-07, EVT-08, CFG-04, DST-03, DST-04. **Add AUT-06** (last-fetch diagnostic sensor, D-20..D-25) and map it to Phase 4
- `.planning/PROJECT.md` § Key Decisions: source = config entry, calendar = subentry, UI-only config, German translation

### Prior decisions & research
- `.planning/phases/01-first-filtered-calendar/01-CONTEXT.md`: UID format (EVT-06), `KEEP_PAST`
- `.planning/phases/02-precise-filters-preview/02-CONTEXT.md`: D-04 (subentry edits in place, no reload), D-06 (missing keys = defaults, no migration), advanced section layout, template rendering
- `.planning/phases/03-resilient-sources/03-CONTEXT.md`: D-16 (tz change changes UIDs), D-19 (calendars stay available; no stale attributes on the calendar, partly revised by D-25), D-21 (diagnostics layout)
- `.planning/phases/03-resilient-sources/03-REVIEW-DISPOSITION.md`: deferred WR-06 / IN-09 (refresh-path logging and cancellation), possibly related to the refresh blocker
- `.planning/research/FEATURES.md`: DF-6 (next-match sensor), DF-7 (new-match event, persisted seen-set, suppress first refresh), DF-14 (retention), DF-15 (blueprint: calendar trigger, negative offset, `mode: queued`)
- `.planning/research/PITFALLS.md`, `.planning/research/ARCHITECTURE.md`: entity/attribute size limits, Store usage

### Sibling repo (release workflow)
- `../homeassistant-mqtt-actions-integration/.github/workflows/release.yml`: tag == manifest version check, reusable ci/validate, `gh release create`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `custom_components/xmltv_calendar/calendar.py`:
  - `XmltvCalendarEntity` holds `_index: MatchIndex`, `_epg`, `_templates`, `_spec` and runs `_async_refilter` in the executor. The next-match sensor, the new-match diff and retention merging all hook in at the point where `result.matches` arrive.
  - `_to_event` / `build_events` render programmes with templates and are reusable for `summary` and event payloads.
  - `async_apply_subentry` is where filter edits are applied in place. That is the hook for the silent baseline (D-11) and the retention re-filter (D-17).
- `MatchIndex` (`current_or_next`, `overlapping`): the next-match sensor needs a "next starting after now" lookup, and retained programmes must be merged into the index or queried alongside it.
- `custom_components/xmltv_calendar/cache.py`: `SourceHealth` (line 124) and `FeedCache` with Store `{meta, health}`. Extend it with the last-attempt record (D-23).
- `custom_components/xmltv_calendar/coordinator.py`: `_async_update_data` and the URL/file/cache-start paths are where the outcome, HTTP status and cache handling for the last-fetch sensor are known. `KEEP_PAST` is used at line 302.
- `custom_components/xmltv_calendar/diagnostics.py`: the calendars list gets `retained` (D-19), and possibly the last attempt.
- `custom_components/xmltv_calendar/translations/en.json` + `de.json`, `tests/test_translations.py`: the parity test.

### Established Patterns
- `__init__.py:17` `PLATFORMS = [Platform.CALENDAR]`. Add `Platform.SENSOR`. Sensors are created per subentry with `async_add_entities(..., config_subentry_id=...)` like the calendar.
- The single diffing update listener `__init__.py:_async_entry_updated`: subentry edits apply in place, source data/options changes reload once from cache.
- Missing stored keys mean defaults (`with_defaults`), with no migration and no VERSION bump.
- Never log or expose URLs, only the host at most. Error texts are translation keys (`FAILURE_REASONS`).
- All blocking work runs in the executor. The pure `xmltv/` library has no HA imports and is built test-first. HA glue is tested with phcc (`freezer`, `aioclient_mock`).

### Integration Points
- New `sensor.py` platform (next-match + last-fetch sensors).
- A new match store module (seen-set + retained programmes, HA `Store`).
- `config_flow.py` calendar subentry advanced section: the retention days field. `data.py`/`with_defaults` gets the new key.
- `blueprints/automation/<…>.yaml`, `.github/workflows/release.yml`, `README.md`.
- `tests/test_repo_structure.py` can assert that the blueprint and release workflow exist (workflow supply-chain checks already parametrize over `.github/workflows`).

</code_context>

<specifics>
## Specific Ideas

- The user's motivation for the last-fetch sensor is concrete: on their test instance a calendar went days without updating until a manual reload, and they want to see "when did it last try, what HTTP status, what did the cache do" straight from the device page.
- Blueprint use case: "notify me X minutes before each matching programme", with overlapping programmes each getting their own notification.

</specifics>

<deferred>
## Deferred Ideas

- **Refresh bug (calendar only updates after manual reload):** not deferred as an idea but handled outside this phase's plans via `/gsd-debug` (see Blocker in Phase Boundary).
- Earlier backlog items still open: per-source channel ID → friendly name mapping (Phase 1), time placeholders in templates (Phase 2), source URL/path reconfigure, multiple daily refresh times, free IANA timezone, fixable Repairs flow (Phase 3).

</deferred>

---

*Phase: 04-automation-extras-release*
*Context gathered: 2026-10-21*
