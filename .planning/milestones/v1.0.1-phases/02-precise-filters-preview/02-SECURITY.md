---
phase: "02"
slug: "precise-filters-preview"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-15"
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| User → config/subentry flow | Admin enters regex patterns, time window, durations, weekdays and title/description templates | Untrusted text (patterns, templates), bounded numbers/choices |
| Stored subentry data → calendar entity | Persisted settings are re-read on setup and on every in-place edit | Possibly stale or corrupt patterns/templates |
| XMLTV feed → filter/render/preview | Feed text (channel names, titles, descriptions) is matched, templated and shown in the preview | Untrusted third-party text |
| Integration → HA frontend (ha-markdown: marked GFM + js-xss) | Preview lines are rendered as Markdown in the flow menu description | Escaped feed text |
| Dev tooling → supply chain | uv-managed dev dependencies | Packages (none added in this phase) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-01 | Denial of service | calendar.async_apply_subentry, corrupt stored pattern | medium | mitigate | `_build_spec` catches PATTERN_ERRORS, keeps previous spec (calendar.py:50-61,176-179); test_corrupt_pattern_keeps_previous_matches | closed |
| T-02-02 | Denial of service | In-place refilter after edit | low | mitigate | `FilterSpec.apply` via executor (calendar.py:148-150) | closed |
| T-02-03 | Denial of service | FilterSpec.apply over descriptions | medium | mitigate | Description searched last, `any()` short-circuit, 300 char / 50 line caps (filter.py:48-49,204-222) | closed |
| T-02-04 | Tampering | with_defaults reading stored settings | low | mitigate | Type-checked tolerant read, unknown keys dropped (settings.py:76-137); test_with_defaults_never_raises_and_drops_unknown_keys | closed |
| T-02-05 | Tampering (UI injection) | preview.format_line in menu description | medium | mitigate | HTML entities + Markdown char escaping (preview.py:35-49,67); whitespace collapse from quick 261015-u6j | closed |
| T-02-06 | Denial of service | async_step_preview full feed scan | medium | mitigate | `build_preview` via executor (config_flow.py:446-454) | closed |
| T-02-07 | Denial of service | Preview/save on unloaded source | low | mitigate | `source_not_loaded` abort in basic/advanced/preview/save; test_save_on_unloaded_source_aborts | closed |
| T-02-08 | Denial of service | Regex validation / matching (ReDoS) | medium | mitigate | `has_nested_repeat` after caps, matching in executor (filter.py:143-200); test_nested_repetition_table | closed |
| T-02-09 | Tampering | from_mapping time/weekday/duration values | low | mitigate | `TimeWindow.from_times`, anchored `normalize_time`, `_choices`, duration clamp (filter.py:77-105, settings.py:65-96) | closed |
| T-02-10 | Tampering | Subentry reconfigure path | medium | mitigate | Reconfigure reuses validated basic step, saves `with_defaults` (config_flow.py:352-377,412,475-479) | closed |
| T-02-11 | Denial of service | async_step_save for edits | low | mitigate | `async_update_and_abort` + in-place listener, no reload/download (config_flow.py:478-480, __init__.py:32-44); test_reconfigure_flow_end_to_end | closed |
| T-02-12 | Information disclosure / DoS | compile_template / render_template | high | mitigate | Allow-listed placeholders only, no format spec/conversion/attribute/index, pure join (render.py:61-82,124-148); test_template_error_reasons | closed |
| T-02-13 | Tampering | Feed text with braces in templates | medium | mitigate | Values concatenated as data, never parsed (render.py:80-82); test_feed_text_with_braces_renders_literally | closed |
| T-02-14 | Tampering | async_step_advanced input | medium | mitigate | `_advanced_errors` (config_flow.py:285-317), NumberSelector bounds, pending updated only without errors; test_advanced_validation | closed |
| T-02-15 | Tampering | SelectSelector fields/weekdays | low | mitigate | No custom_value, schema `In(options)`, unknown names dropped on read (config_flow.py:233-239, settings.py:91-100) | closed |
| T-02-16 | Denial of service | Basic step include/exclude validation | medium | mitigate | `first_invalid_pattern` on every submit (config_flow.py:370-377); test_nested_repetition_rejected_in_form | closed |
| T-02-17 | Tampering | Edit-flow pending state | low | mitigate | Pending loaded once, Back reuses it, save writes `with_defaults` (config_flow.py:338-385,475-484); test_unchecking_advanced_keeps_stored_values | closed |
| T-02-18 | Denial of service | _build_spec with OverflowError/RecursionError | medium | mitigate | PATTERN_ERRORS includes both (filter.py:55), caught in calendar.py:57-61; test_invalid_stored_pattern_does_not_break_platform_setup | closed |
| T-02-19 | Denial of service | first_invalid_pattern with repeat-overflow | low | mitigate | PATTERN_ERRORS mapped to InvalidPattern (filter.py:194-198); test_invalid_pattern_line_keeps_form_open | closed |
| T-02-20 | Spoofing (UI injection) | escape_markdown autolinks (URL, www., e-mail) | low | mitigate | `_AUTOLINK_TRIGGERS` backslash-escaped (preview.py:37,49); test_preview_shows_feed_urls_as_plain_text; live re-check on ha-dev 2026-10-15 | closed |
| T-02-21 | Tampering (UI distortion) | escape_markdown `~` strikethrough | low | mitigate | `~` in `_MARKDOWN_CHARS` (preview.py:36); test_tilde_is_escaped | closed |
| T-02-SC | Tampering | uv dev installs (supply chain) | high | mitigate | No dependency/manifest/CI changes since 5a8952e; `requirements: []`; stdlib-only imports | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

**Residual risks (documented in the plan threat models, mitigations in place):**
- T-02-08: overlapping alternation such as `(a|aa)+` is not detected; `has_nested_repeat` fails open if the private `re._parser` changes. Length caps and executor matching still bound the impact.
- T-02-19: RecursionError is unreachable through the form (300-character cap); stored data is contained by T-02-18.
- T-02-20: a future marked release could add a new GFM autolink form that would need a new trigger.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|

No accepted risks.

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-15 | 22 | 22 | 0 | gsd-security-auditor (ASVS L1, block_on high) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-15
