---
phase: "01"
slug: "first-filtered-calendar"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-15"
---

# Phase 01 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Remote feed host → integration | Untrusted XML bytes over HTTP(S); untrusted size, speed, status, compression ratio | Feed bytes (untrusted) |
| HA admin UI → config/subentry flow | Admin-supplied URL, file path, names, regular expressions | Config input (trusted admin, validated) |
| HA admin UI → file system | Admin-entered path read by the HA process | Local files (potentially sensitive, e.g. secrets.yaml) |
| HA frontend / services → calendar entity | Arbitrary date ranges from dashboards, get_events, trigger poll | Query ranges |
| Integration → HA logs / exception text | Readable by all HA admins, pasted into bug reports | URL host only (URL tokens must not leak) |
| GitHub Actions / Renovate → repo & CI | Third-party action code, automated pin bumps | Workflow token, dependency pins |
| Local repository → public GitHub | Every tracked file becomes world-readable | Source, planning docs, fixtures |
| Third-party EPG provider → public repository | Copyrighted listings may be redistributed | Test fixtures |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-01 | Information disclosure | source.py, coordinator.py logging | medium | mitigate | Logs carry only URL host; UpdateFailed uses translation keys | closed |
| T-01-02 | Denial of service | coordinator.py parse path | high | mitigate | Parse via async_add_executor_job; forbid_loop_io fixture; yield_every in parser | closed |
| T-01-03 | Tampering | xmltv/parser.py iterparse | medium | mitigate | stdlib ET never resolves external entities/DTDs; S314 suppressed on one line | closed |
| T-01-04 | Denial of service | xmltv/timeparse.py | medium | mitigate | Anchored, bounded regex; ValueError → None | closed |
| T-01-05 | Denial of service | xmltv/normalize.py → CalendarEvent | medium | mitigate | Stop inference guarantees stop ≥ start | closed |
| T-01-06 | Denial of service | xmltv/filter.py (ReDoS) | medium | mitigate | MAX_PATTERN_LENGTH 300, MAX_PATTERN_LINES 50; matching in executor | closed |
| T-01-07 | Tampering | compile_patterns blank lines | medium | mitigate | Blank lines skipped before compile | closed |
| T-01-08 | Denial of service | calendar.py async_get_events | high | mitigate | MAX_EVENTS_PER_QUERY 5000 (calendar.py:35), bisect index (xmltv/window.py), executor build above EXECUTOR_BUILD_THRESHOLD | closed |
| T-01-09 | Denial of service | calendar.py build_events | medium | mitigate | Per-event try/except with skip + debug log | closed |
| T-01-10 | Denial of service | parser gzip decompression (bomb) | high | mitigate | _CappedReader / MAX_DECOMPRESSED_BYTES 1 GiB; streaming iterparse + clear | closed |
| T-01-11 | Denial of service | Expat entity expansion | medium | transfer | Python-bundled Expat ≥2.7.2 amplification limits | closed |
| T-01-12 | Information disclosure | FeedError messages | medium | mitigate | Messages from exception class + line/col; sentinel test | closed |
| T-01-13 | Denial of service | source.py download | high | mitigate | MAX_DOWNLOAD_BYTES 256 MiB; ClientTimeout(total=300, sock_read=60) | closed |
| T-01-14 | Information disclosure | source.py / coordinator.py logs | medium | mitigate | Host-only logging; caplog assertions in tests/test_source.py | closed |
| T-01-15 | Tampering | .github/workflows action refs | high | mitigate | All `uses:` SHA-pinned; test_all_action_refs_are_pinned_by_sha | closed |
| T-01-16 | Elevation of privilege | Workflow GITHUB_TOKEN | medium | mitigate | permissions: {}, per-job contents: read, persist-credentials: false | closed |
| T-01-17 | Tampering | renovate.json phcc bumps | medium | mitigate | dependencyDashboardApproval for phcc | closed |
| T-01-18 | Information disclosure | source.check_file / read_and_parse_file | high | mitigate | Absolute path + hass.config.is_allowed_path (source.py:136) | closed |
| T-01-19 | Information disclosure | config entry unique_id | medium | mitigate | sha256 of normalized source keeps URL tokens out | closed |
| T-01-20 | Spoofing / SSRF | probe and coordinator fetch | low | accept | Admin-only flow; http/https only | closed |
| T-01-21 | Tampering | normalize_url scheme handling | medium | mitigate | Non-http(s) schemes rejected with invalid_url | closed |
| T-01-22 | Denial of service | async_probe_url | medium | mitigate | PROBE_BYTES 64 KiB + DOWNLOAD_TIMEOUT | closed |
| T-01-23 | Denial of service | CalendarSubentryFlow pattern input | medium | mitigate | first_invalid_pattern before storing; executor matching | closed |
| T-01-24 | Elevation of privilege / DoS | CalendarSubentryFlow on unloaded source | low | mitigate | Abort source_not_loaded | closed |
| T-01-25 | Information disclosure / legal | tests/fixtures/real_de_excerpt.xml | medium | mitigate | Not committed; only synthetic fixtures tracked | closed |
| T-01-26 | Tampering | ha-dev bind mounts | low | mitigate | New mounts `:ro` in dev compose.yml | closed |
| T-01-27 | Information disclosure | Tracked files pushed publicly | high | mitigate | Pre-push secret scan with manual review; .gitignore for caches/state | closed |
| T-01-28 | Tampering | Repo settings and CI token | medium | mitigate | permissions: {} + per-job contents: read (01-06 structure tests) | closed |
| T-01-29 | Denial of service | xmltv/timeparse.py parse_xmltv_time | high | mitigate | Offset/year bounds; ValueError/OverflowError → None | closed |
| T-01-30 | Denial of service | xmltv/parser.py _collect | medium | mitigate | (ValueError, OverflowError) counted in skipped_malformed | closed |
| T-01-31 | Information disclosure | parser exceptions that propagate (WR-06) | low | accept | Only programming bugs propagate; data errors swallowed, FeedError content-free | closed |
| T-01-32 | Denial of service | calendar.py build_events / event | medium | mitigate | Except (HomeAssistantError, OverflowError, ValueError) with skip + debug log | closed |
| T-01-SC | Tampering | uv dev installs, hassfest image, CI | high | mitigate | Exact `==` pins, committed uv.lock, `uv sync --locked` in CI; hassfest image mounted `:ro` | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01-01 | T-01-20 | SSRF to internal hosts requires HA admin rights, same trust level as core remote_calendar; only http/https schemes allowed | plan 01-07 threat model | 2026-10-14 |
| AR-01-02 | T-01-31 | Only programming-bug exceptions propagate with traceback; feed-data errors are swallowed or content-free | plan 01-11 threat model | 2026-10-14 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-15 | 33 | 33 | 0 | /gsd-secure-phase (L1 grep-depth, orchestrator) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-15
