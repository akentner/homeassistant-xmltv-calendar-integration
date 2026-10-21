# Phase 4: Automation Extras & Release - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-21
**Phase:** 04-automation-extras-release
**Areas discussed:** Next-match sensor, New-match event, Past matches, Last-fetch diagnostic sensor (added by user), Blueprint & release

---

## Next-match sensor

| Option | Description | Selected |
|--------|-------------|----------|
| Only future | State = start of next not-yet-started match | ✓ |
| Current or next | Like calendar `event`, duplicates the calendar | |

| Option | Description | Selected |
|--------|-------------|----------|
| unknown | Sensor stays available, state unknown | ✓ |
| unavailable | Mixes "no match" with "source broken" | |

| Option | Description | Selected |
|--------|-------------|----------|
| Both | `title` raw + `summary` rendered | ✓ |
| Raw only | | |
| Rendered only | | |

Extra attributes (multi): channel_id ✓, subtitle/episode ✓, description ✓, none.
Recorder: description unrecorded ✓ / record all.
Naming: same device, "Nächste Sendung" / "Next programme" ✓ / "Nächster Treffer".
Enabled by default ✓ / disabled.

## New-match event

| Option | Description | Selected |
|--------|-------------|----------|
| Per match | One `xmltv_calendar_new_match` event per match | ✓ |
| Per refresh | One event with a list | |

What is new: new UID ✓ / new (channel, title).
Filter edit adds matches: silent baseline ✓ / fire events.
Started/past matches: only future fire ✓ / all new.
Source tz/offset change: silent baseline ✓ / fire normally.
Burst cap: cap (~50) with log warning ✓ / no cap.

## Past matches

Where N is set: per calendar ✓ / per source.
Default: 1 day ✓ / 0 / 7.
Filter edit: re-filter retained ✓ / keep.
Diagnostics: separate counts ✓ / Claude decides.
Dropped not-yet-ended match: only ended retained ✓ / also running.
Corrected past slot (other UID): show both ✓ / feed displaces overlaps.

**User's free-text input at the end of this area:** reported that on their test instance a calendar ran for several days and only got new entries after a manual integration reload; asked for an additional diagnostic entity per calendar device showing the last fetch attempt with attributes (HTTP status, cache handling, etc.).

## Refresh bug & last-fetch diagnostic sensor

Bug handling: separate `/gsd-debug` ✓ / plan in Phase 4.
Diagnostic sensor scope: fold into Phase 4 as AUT-06 ✓ / backlog.
What counts as attempt: every refresh run ✓ / only network/file access.
Attributes (multi): outcome + HTTP status ✓, cache handling ✓, schedule ✓, data metrics ✓.
Persist across restart: yes ✓ / runtime only.
Visibility: diagnostic enabled / diagnostic disabled ✓.

## Blueprint & release

Trigger: calendar trigger with offset ✓ / next-match sensor.
Notification: free action selector (default notify.send_message) ✓ / notify entity only / mobile app device.
First version: 0.1.0 ✓ / 1.0.0.
README: English, one file ✓ / English + README.de.md.

## Claude's Discretion

Store layout and write strategy for seen-set/retention; config-change fingerprint; exact burst cap; next-match sensor update mechanism; last-fetch attribute keys/vocabulary; retention selector type; blueprint message text and lead-time default.

## Deferred Ideas

Refresh bug routed to `/gsd-debug` (outside phase plans). No new deferred ideas.
