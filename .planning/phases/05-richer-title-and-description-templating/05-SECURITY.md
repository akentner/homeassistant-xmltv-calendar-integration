---
phase: "05"
slug: richer-title-and-description-templating
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-30"
---

# Phase 05 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Admin-authored template to sandbox | Title and description templates typed in the flow or edited in storage are compiled and rendered by the sandboxed Jinja engine | Template source (admin-trusted, still validated) |
| Feed to render context | XMLTV programme fields are passed as render variables only, never compiled as template source | Programme title, description, channel (untrusted) |
| Logs | Template failures are logged with calendar name and reason only | Calendar name, exception type or reason key |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-05-01 | Elevation of privilege | template_engine sandbox | high | mitigate | `ImmutableSandboxedEnvironment`, node allow-list, pruned filters and tests, no globals (`template_engine.py:72-100,292-295,392-432`) | closed |
| T-05-02 | DoS | compile and render cost via operators | high | mitigate | `+ * ** %` absent from the allow-list, tree checked before compile | closed |
| T-05-03 | DoS | regex backtracking via `map`/`select`/`reject` naming `regex_replace`/`regex_search` as text | medium | accept | Direct calls validated (`template_engine.py:347-372`); the text-named route is not; documented in README Limits and ROADMAP | open — below high threshold (non-blocking), accepted (AR-05-03) |
| T-05-04 | Tampering | feed text read as template source | high | mitigate | Feed values enter only through `render(**values)` (`render.py:152-175,249`) | closed |
| T-05-05 | Information disclosure | WARNING and DEBUG log content | medium | mitigate | Calendar name, kind and exception type or reason only (`render.py:185-205`) | closed |
| T-05-06 | Tampering | hand-edited storage bypasses flow validation | medium | mitigate | `from_mapping` compiles with the same whitelist, falls back to default with one WARNING | closed |
| T-05-07 | Tampering | flow accepts a template that fails at render | medium | mitigate | Trial render on two synthetic programmes (`render.py:134-149`, `config_flow.py:541-551`) | closed |
| T-05-08 | Information disclosure | exception text in the error placeholder | low | accept | Synthetic samples, detail cut to 200 characters | closed (accepted, AR-05-01) |
| T-05-09 | DoS | trial render on the event loop | low | mitigate | Whitelist and length caps bound the cost | closed |
| T-05-10 | DoS | compile stall or non-Jinja crash | medium | mitigate | Length and nesting caps, SyntaxError/RecursionError mapped to `invalid_template` | closed |
| T-05-11 | DoS | output amplification by `replace` / `regex_replace` | medium | mitigate | `_bounded` output limit of 50000 characters (`template_engine.py:190-207`) | closed |
| T-05-12 | DoS | exponential growth through `set` and `~` | low | accept | Admin-only, bounded by length caps; documented in README Limits | closed (accepted, AR-05-02) |
| T-05-13 | Information disclosure | WARNING content on stored-template failure | medium | mitigate | Same controls as T-05-05 | closed |
| T-05-14 | Tampering | template edit re-announces matches or changes UIDs | medium | mitigate | UID hashed from raw programme title, seen-set keyed on `event_uid` | closed |
| T-05-15 | DoS | per-event rendering on the event loop | low | mitigate | Compile once per calendar, zone resolved once, large slices in the executor | closed |
| T-05-16 | Tampering | documentation drift | low | mitigate | `tests/test_readme_recipes.py` renders every documented recipe | closed |
| T-05-SC | Tampering | package installs | high | mitigate | `requirements` stays empty, no dependency changes | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-08 | The form is admin-only. The trial render uses synthetic data, so no feed content can appear. The detail is cut to 200 characters. | project owner (plan 05-02 disposition) | 2026-10-23 |
| AR-05-02 | T-05-12 | Exponential growth through `set` and `~` needs a hand-crafted template from an HA admin, is bounded by the 2000 and 5000 character caps and cannot be reached from feed content. Documented in README Limits and ROADMAP. | project owner (plans 05-03 and 05-05) | 2026-10-23 |
| AR-05-03 | T-05-03 | The regex checks do not cover `map`/`select`/`reject` calls that name `regex_replace`/`regex_search` as text. Exploiting it needs an admin-authored template and a matching feed title, and it only slows a render. Chosen in the UAT test 4 decision flow, documented in README Limits and ROADMAP. A code fix remains possible in a later release. | project owner (UAT test 4, secure-phase decision) | 2026-10-30 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-30 | 17 | 16 | 1 (non-blocking, accepted) | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-30
