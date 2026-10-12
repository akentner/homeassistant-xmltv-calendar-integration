# Phase 1: First Filtered Calendar - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-12
**Phase:** 01-first-filtered-calendar
**Areas discussed:** Senderauswahl, Regex-Eingabe, Benennung & Geräte, Zeit-Defaults & Testdaten

---

## Senderauswahl

| Option | Description | Selected |
|--------|-------------|----------|
| Dropdown + Regex-Fallback | Searchable multi-select + optional channel regex; both empty = all | ✓ |
| Nur Dropdown | Multi-select only | |
| Nur Regex | Channel regex only | |

| Option | Description | Selected |
|--------|-------------|----------|
| Name (id) | Display name with ID | |
| Nur Name | Display name only | |
| (Other) | "id, aber evtl. Mapping für user friendly Namen" | ✓ |

Follow-up on mapping: Feed-Name als Label / Eigenes Mapping pro Quelle / **Erstmal nur ID, Mapping später** ✓

| Option | Description | Selected |
|--------|-------------|----------|
| Still ignorieren + Log | Calendar continues, warning logged | ✓ |
| Im Picker behalten | Unknown IDs shown as "(nicht im Feed)" | |
| Du entscheidest | | |

**User's choice:** Dropdown + regex fallback; ID only for now; ignore missing channels with log.

---

## Regex-Eingabe

| Option | Description | Selected |
|--------|-------------|----------|
| Ein Pattern pro Zeile | Multiline text, OR-combined | ✓ |
| Liste (Text-Selector multiple) | | |
| Ein einziges Regex | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Alles (der Sender) matcht | Empty include = all programmes of selected channels | ✓ |
| Pflichtfeld | | |
| Alles, aber Warnung | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Titel + Untertitel | Phase 1 match fields | ✓ |
| Titel + Untertitel + Beschreibung | | |
| Include: Titel+Untertitel, Exclude: +Beschreibung | | |

Regex help question (Kurze Beispiele / Nur README): not answered → Claude's discretion.

---

## Benennung & Geräte

| Option | Description | Selected |
|--------|-------------|----------|
| Pflichtfeld 'Name' im Flow | Default suggestion from host/file name | ✓ |
| Automatisch aus URL/Pfad | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Nur Kalendername | calendar.formel_1 | ✓ |
| Quelle + Kalender | calendar.tvheadend_epg_formel_1 | |

| Option | Description | Selected |
|--------|-------------|----------|
| Ein Gerät pro Kalender | Matches subentry device rule | ✓ |
| Ein Gerät pro Quelle | | |
| Keine Geräte | | |

Domain name: **xmltv_calendar** ✓ (alternatives: xmltv, epg_calendar)

---

## Zeit-Defaults & Testdaten

| Option | Description | Selected |
|--------|-------------|----------|
| Default 60 min | Last programme without stop | ✓ |
| Verwerfen | | |
| Du entscheidest | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Default 12h, Min 1h | | |
| Default 6h, Min 1h | | |
| Default 24h, Min 1h | Matches daily-generated source | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Synthetisch + generierter Groß-Feed | | |
| Zusätzlich echter DE-Ausschnitt | Synthetic + generator + real German excerpt | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Taskfile/SCP wie phone_logger | | |
| Nur über HACS | | |
| Beides | | |
| (Other) | "lokal HA Instanz auf Podman" → `~/Projects/dev/compose.yml` | ✓ |

---

## Claude's Discretion

- Regex examples in form field descriptions
- `iot_class`
- Large channel list handling in selector (regex fallback agreed)
- Repo scaffold details

## Deferred Ideas

- Per-source channel ID → friendly name mapping
