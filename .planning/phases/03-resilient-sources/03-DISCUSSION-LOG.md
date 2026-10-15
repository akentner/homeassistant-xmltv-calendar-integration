# Phase 3: Resilient Sources - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-16
**Phase:** 03-resilient-sources
**Areas discussed:** Refresh schedule & options, Cache & startup, Timezone options, Failure visibility

---

## Refresh schedule & options

| Option | Description | Selected |
|--------|-------------|----------|
| Mode select | Interval / daily at, then only the matching field | ✓ |
| Both fields, time wins | One form, time overrides interval | |
| Interval + anchor time | Interval counted from an anchor time | |

| Option | Description | Selected |
|--------|-------------|----------|
| Exactly one daily time | Matches SRC-05 | ✓ |
| Multiple times | List of times | |

| Option | Description | Selected |
|--------|-------------|----------|
| Options = schedule + timezone only | CFG-02 exactly; URL/path fixed | ✓ |
| Also URL/path reconfigure | Own reconfigure flow with duplicate check | |

| Option | Description | Selected |
|--------|-------------|----------|
| Catch up missed daily slot on start | Cache stale if last slot after fetch time | ✓ |
| Wait for next slot | Cache valid until next time | |

| Option | Description | Selected |
|--------|-------------|----------|
| Schedule/timezone in setup + options | First parse uses correct timezone | ✓ |
| Setup interval only | Rest in options flow | |

| Option | Description | Selected |
|--------|-------------|----------|
| Missing mode = interval | Defaults for missing keys, no migration | ✓ |
| Explicit entry migration | Version bump | |

## Cache & startup

| Option | Description | Selected |
|--------|-------------|----------|
| Raw feed + metadata | Original bytes + ETag/Last-Modified/time | ✓ |
| Parsed model | Serialized EpgData | |

| Option | Description | Selected |
|--------|-------------|----------|
| Show cached data + retry | Setup succeeds with stale cache | ✓ |
| ConfigEntryNotReady | Setup fails until reachable | |
| Cached only up to max age | e.g. 7 days, then NotReady | |

| Option | Description | Selected |
|--------|-------------|----------|
| Local files: mtime check only | Reparse when mtime/size changed | ✓ |
| Cache like URL sources | Duplicate storage | |

| Option | Description | Selected |
|--------|-------------|----------|
| update_entity: immediate, conditional GET | 304 = no reparse | ✓ |
| Forced full download | No conditional headers | |

| Option | Description | Selected |
|--------|-------------|----------|
| Setup download seeds the cache | No double download | ✓ |
| Validation only | Coordinator downloads again | |

| Option | Description | Selected |
|--------|-------------|----------|
| Backoff capped at schedule | 5 → 15 → 60 min … | ✓ |
| Regular schedule only | No extra retries | |
| You decide | | |

## Timezone options

| Option | Description | Selected |
|--------|-------------|----------|
| Select UTC / HA timezone | Default UTC | ✓ |
| Free IANA timezone | Dropdown of all zones | |

| Option | Description | Selected |
|--------|-------------|----------|
| Correction on all timestamps | Fixed shift after interpretation | ✓ |
| Only on no-offset timestamps | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Minutes, ±720 | Covers half/quarter hours | ✓ |
| Hours, ±12 | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Reload, reparse from cache | No network | ✓ |
| Shift in RAM | No reparse | |

## Failure visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Time-based: >24 h without success | Independent of retry count | ✓ |
| N consecutive failures | | |
| Both, whichever first | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Calendars stay available | Last good data, triggers keep working | ✓ |
| Available + stale attribute | | |
| Unavailable after threshold | | |

| Option | Description | Selected |
|--------|-------------|----------|
| 0 programmes = failure | Keep last good data | ✓ |
| Valid is valid | Empty feed replaces data | |

| Option | Description | Selected |
|--------|-------------|----------|
| Repairs info only | Auto-clears after success | ✓ |
| Fix flow → options | | |

**Notes:** The user was ready for CONTEXT after these four areas. The diagnostics content is set from the requirements (incl. WR-08 `skipped_malformed`).

## Claude's Discretion

- Backoff steps and daily-time scheduling mechanics
- Cache file layout and atomic writes
- Progress-flow mechanics
- Persisting the failure timestamps across restarts
- Logging levels

## Deferred Ideas

- Source URL/path reconfigure flow
- Multiple daily refresh times
- Free IANA timezone choice
- Stale attributes on calendar entities
- Fixable Repairs flow
