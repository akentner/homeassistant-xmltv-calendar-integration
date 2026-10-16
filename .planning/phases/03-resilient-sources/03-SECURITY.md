---
phase: "03"
slug: "resilient-sources"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-16"
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Feed host -> coordinator | Status codes, validators and bodies are untrusted | untrusted network bytes, headers |
| Feed host -> cache | Untrusted bytes and response headers are persisted and later re-parsed | untrusted feed payload, ETag/Last-Modified |
| Feed host -> flow download | Untrusted body and size, during an interactive flow | untrusted feed payload |
| Feed host failures -> retry loop | A failing host decides how often the integration retries | timing / request rate |
| Coordinator schedule -> feed host | The computed refresh target decides how often an external host is contacted | request rate |
| Feed timestamps -> parser | Untrusted timestamp strings in any of the XMLTV variants | untrusted strings |
| Local file system -> coordinator | A configured path may leave the allowlist or change at any time | local file contents |
| Entry data -> file system | The cache file name is derived from entry identifiers | identifiers used as path components |
| Cache files -> other local users and backups | Feed data and validators sit in the HA config directory | feed data (low sensitivity) |
| Flow -> cache | The flow persists the downloaded body before the entry exists | feed payload |
| Store -> coordinator | Persisted health may be corrupt or hand-edited | JSON health record |
| Stored entry options -> coordinator / parser | entry.options may come from an older version or be hand-edited in .storage | schedule, offset, timezone values |
| Admin input -> flow / options flow | URL, path, schedule and timezone values typed into the forms | admin input |
| Options flow -> entry identity | The source identity (unique_id, URL/path) must not be changeable here | entry identity |
| UI/automation -> update_entity | Any user or automation can request refreshes | request rate |
| Coordinator -> Repairs UI | Issue texts and placeholders are shown to every admin and may end up in screenshots and bug reports | entry title, timestamps |
| Integration state -> diagnostics file | Diagnostics are downloaded by the user and often attached to public bug reports | redacted source, health, stats |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-01 | Tampering | SourceOptions.from_mapping | low | mitigate | xmltv/schedule.py:68-78, :91-110 defaults/clamps bad values | closed |
| T-03-02 | DoS | XmltvCoordinator._schedule_refresh | medium | mitigate | coordinator.py:98, :133 `max(target - now, MIN_DELAY)` | closed |
| T-03-SC | Tampering | dev installs / dependencies | high | mitigate | manifest.json `"requirements": []`; no dependency-file diff in Phase 3 | closed |
| T-03-03 | Info disclosure | cache file name, Store, logs | high | mitigate | cache.py:42-47 hashed key; Store holds no URL; logs host/type only | closed |
| T-03-04 | Tampering | cache_key | medium | mitigate | cache.py:37, :45-47 safe-key regex else SHA-256 | closed |
| T-03-05 | Tampering/DoS | cache write, cached parse | medium | mitigate | coordinator.py:347-348, :275-293; cache.py:225-231 size check | closed |
| T-03-06 | DoS | cached payload parse | medium | mitigate | parser `_CappedReader` / MAX_DECOMPRESSED_BYTES on cached bytes | closed |
| T-03-07 | Info disclosure | payload file | low | mitigate | cache.py:308 private write; :175 private Store; `.cache` excluded from backups | closed |
| T-03-08 | Tampering | ETag/Last-Modified | medium | mitigate | source.py:64-75 `clean_validator` on receive, load, touch | closed |
| T-03-09 | DoS | 304 handling | low | mitigate | coordinator.py:320-336 validators only from valid meta; refetch without validators | closed |
| T-03-10 | EoP | read_and_parse_file | medium | mitigate | source.py:187 `check_file` / `is_allowed_path` on every read | closed |
| T-03-11 | DoS | homeassistant.update_entity | low | accept | see Accepted Risks Log AR-03-01 | closed |
| T-03-12 | Info disclosure | Repairs issue placeholders | high | mitigate | coordinator.py:218-227 title + time only; fixed translation keys | closed |
| T-03-13 | DoS | failure retry scheduling | medium | mitigate | xmltv/schedule.py:45-51, :197-205 backoff capped at next regular refresh | closed |
| T-03-14 | Tampering | SourceHealth.from_dict | low | mitigate | cache.py:143-165 type/regex checks; :201-209 load errors caught | closed |
| T-03-15 | DoS | Store writes per refresh | low | accept | see Accepted Risks Log AR-03-02 | closed |
| T-03-16 | Tampering | offset_minutes | low | mitigate | xmltv/schedule.py:100-102 clamp -720..720 | closed |
| T-03-17 | DoS | shift near year bounds | low | mitigate | xmltv/parser.py:139-146 per-programme ValueError/OverflowError handling | closed |
| T-03-18 | Info disclosure | flow errors, progress text, logs | medium | mitigate | config_flow.py fixed error keys; progress text without placeholders | closed |
| T-03-19 | DoS | async_step_download | medium | mitigate | `async_fetch_url` size/time limits; progress task cancelled on flow removal | closed |
| T-03-20 | Tampering | cache seeding in async_step_name | low | mitigate | config_flow.py:333-361 seeds only on final submit under confirmed unique_id | closed |
| T-03-21 | Tampering | schedule and timezone inputs | low | mitigate | config_flow.py selector bounds + `normalize_time` + `from_mapping` | closed |
| T-03-22 | Info disclosure | diagnostics source block | high | mitigate | diagnostics.py:37-54 URL/path redaction; TO_REDACT safety net | closed |
| T-03-23 | Info disclosure | diagnostics content | low | mitigate | diagnostics.py:108-130 fixed key set; no programme text | closed |
| T-03-24 | Tampering | XmltvOptionsFlow inputs | low | mitigate | config_flow.py:407-426 shared selectors, `normalize_time`, `_options_to_store` | closed |
| T-03-25 | Tampering | source identity | medium | mitigate | options schemas have no URL/path field; entry.data unchanged (test) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

T-03-SC appears in every plan's register (8 rows); it is listed once above. Audit total: 33 register rows, 26 distinct threat IDs.

### Audit notes (non-blocking)

- T-03-14: no regression test for malformed persisted health; covered only by the audit probe.
- T-03-20 / T-03-04: `config_flow.py:353` builds `FeedCache(hass, self.unique_id)` directly instead of via `cache_key()`. Safe while unique_id is the SHA-256 hex from `source_unique_id`; route through `cache_key()` if that scheme changes.
- T-03-10: escaping-symlink case is tested in the flow only; at refresh it relies on `is_allowed_path` resolving symlinks.
- T-03-12: the entry title is user-typed; a user who names the source with the full URL will see it in the Repairs issue.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-03-01 | T-03-11 | The coordinator debouncer (10 s cooldown) collapses bursts; each request is conditional, so a burst costs small 304 answers, not downloads (03-03-PLAN) | plan threat model (03-03), verified by gsd-security-auditor | 2026-10-16 |
| AR-03-02 | T-03-15 | Small JSON Store saves per refresh outcome (in practice two per success: cache meta and health); refreshes are at most hourly or follow the backoff (03-04-PLAN) | plan threat model (03-04), verified by gsd-security-auditor | 2026-10-16 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-16 | 33 | 33 | 0 | gsd-security-auditor (ASVS L1, block_on: high) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-16
