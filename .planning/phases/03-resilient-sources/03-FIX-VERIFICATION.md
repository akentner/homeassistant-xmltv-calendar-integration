# Phase 03 warning fixes — 2026-10-17

Scope: WR-01, WR-04 and WR-05 from 03-REVIEW.md. This supplements the canonical
phase report; it does not replace its goal verification or fingerprint.

| Finding | Changed behavior | Regression evidence |
|---------|------------------|---------------------|
| WR-01 | 304, identical-body and unchanged-file paths reject data whose last programme is before `utcnow() - KEEP_PAST`, matching parser retention. Failure keeps the previous data and metadata and records `empty_feed`; shortcuts still avoid parsing. | `test_expired_unchanged_feed_fails_without_reparse` (304 and identical body), `test_expired_unchanged_file_fails_without_reparse`; existing unchanged-success and Repairs tests |
| WR-04 | Every refresh starts with a provisional target no earlier than five minutes ahead or the existing target. Success and failure calculations retain the original served target, preserving daily early-fire handling and manual-refresh behavior. Cancellation remains unrecorded and propagates to HA. | `test_timer_cancelled_refresh_does_not_retry_every_second`: one attempt over ten seconds, retry at five minutes; existing cancellation, early-fire, fast-failure and manual-refresh tests |
| WR-05 | An unexpected cache parser exception drops the poisoned cache and falls through to an unconditional download. A persistently broken parser records the downloaded parse failure; a changed upstream feed can recover immediately. `MemoryError` retains the cached bytes and records a failure. | `test_unexpected_cache_parse_failure_downloads_and_is_recorded`, `test_cache_parser_crash_recovers_from_changed_download`, `test_cache_memory_error_preserves_offline_fallback` |

Validation:

- Targeted refresh/file/scheduling/Repairs modules: 45 passed.
- `.venv/bin/pytest tests/ -q -rs --tb=short`: 821 passed, 1 skipped in 52.62 s.
- The skip is the existing real-feed fixture gate (`XMLTV_REAL_FEED` absent).
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/ruff format --check .`: 62 files already formatted.
- `git diff --check`: passed.

The three review dispositions are fixed. No other findings were changed.
The canonical phase report requires regeneration after these source changes;
phase 03 has not been advanced on the strength of this supplemental report.
