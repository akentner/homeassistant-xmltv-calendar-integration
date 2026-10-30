---
phase: 02-precise-filters-preview
verified: 2026-10-15T20:08:11Z
status: passed
score: 96/96 must-haves verified
covered_files: [".planning/phases/02-precise-filters-preview/02-01-PLAN.md", ".planning/phases/02-precise-filters-preview/02-01-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-02-PLAN.md", ".planning/phases/02-precise-filters-preview/02-02-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-03-PLAN.md", ".planning/phases/02-precise-filters-preview/02-03-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-04-PLAN.md", ".planning/phases/02-precise-filters-preview/02-04-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-05-PLAN.md", ".planning/phases/02-precise-filters-preview/02-05-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-06-PLAN.md", ".planning/phases/02-precise-filters-preview/02-06-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-07-PLAN.md", ".planning/phases/02-precise-filters-preview/02-07-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-08-PLAN.md", ".planning/phases/02-precise-filters-preview/02-08-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-09-PLAN.md", ".planning/phases/02-precise-filters-preview/02-09-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-10-PLAN.md", ".planning/phases/02-precise-filters-preview/02-10-SUMMARY.md", ".ruff.toml", "custom_components/xmltv_calendar/__init__.py", "custom_components/xmltv_calendar/calendar.py", "custom_components/xmltv_calendar/config_flow.py", "custom_components/xmltv_calendar/const.py", "custom_components/xmltv_calendar/translations/en.json", "custom_components/xmltv_calendar/xmltv/filter.py", "custom_components/xmltv_calendar/xmltv/parser.py", "custom_components/xmltv_calendar/xmltv/preview.py", "custom_components/xmltv_calendar/xmltv/render.py", "custom_components/xmltv_calendar/xmltv/settings.py", "custom_components/xmltv_calendar/xmltv/window.py", "tests/conftest.py", "tests/test_advanced_flow.py", "tests/test_calendar.py", "tests/test_filtering.py", "tests/test_init.py", "tests/test_reconfigure.py", "tests/test_subentry_flow.py", "tests/test_templates.py", "tests/test_tracer.py", "tests/xmltv/test_filter.py", "tests/xmltv/test_parser.py", "tests/xmltv/test_preview.py", "tests/xmltv/test_render.py", "tests/xmltv/test_settings.py", "tests/xmltv/test_window.py"]
covered_digest: "v3:sha256:358d1454661ea7e185607c05949b72e0191d48749f246c83e29931dd68157d43"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 95/96
  gaps_closed:
    - "02-10 truth 6 / G-02-2: UAT test 2 re-check on ha-dev done 2026-10-15 (02-UAT.md: G-02-2 resolved, recheck notes; UAT complete 4/4)"
    - "WR-05 escalation: fixed by quick task 261015-u6j (escape_markdown collapses every \\s+ run before escaping; 9b87e7f), 02-REVIEW-DISPOSITION.md WR-05 = fixed"
  gaps_remaining: []
  regressions: []
coincidental_reliance_items:
  - truth: "02-09 truths 1-2: a stored pattern that raises RecursionError in re.compile is contained (listener and platform setup), deep-nesting ids"
    reason: undeclared-precondition
    harden: "DEEP_NESTING = '(' * 2000 + ')' * 2000 only raises RecursionError at the interpreter's default recursion limit (about 500 levels at limit 1000). Derive the depth from sys.getrecursionlimit() and define it once in tests/conftest.py (review IN-07). The production catch (PATTERN_ERRORS includes RecursionError) does not depend on this."
---

# Phase 2: Precise Filters & Preview – Verifikationsbericht

**Phase Goal:** User can pinpoint specific shows with field-scoped, Unicode-safe regex plus duration and time-window filters, shape event title and description via templates, check the result in a live preview before saving, and retune any calendar instantly without touching the source.
**Verifiziert:** 2026-10-15T20:08:11Z
**Status:** passed
**Re-Verifikation:** Ja, Neuerstellung nach Quick-Task 261015-u6j (WR-05) und erledigtem UAT-Re-Check. Vorher: human_needed, 95/96. Der vorige Bericht hatte keinen `gaps:`-Block, daher lief die volle Prüfung (alle Truths, Artefakte, Key-Links), nicht nur ein Regressions-Check.
**Mode:** mvp (ROADMAP). Das Ziel ist eine Fähigkeitsbeschreibung, keine User Story. Wie bisher dienen Zieltext und die fünf Roadmap-Success-Criteria als Vertrag; die Pläne tragen die User-Story-Form.

## Ergebnis in Kürze

- **Beide offenen Human-Items sind erledigt:**
  - UAT test 2 Re-Check auf ha-dev ist in `02-UAT.md` dokumentiert (G-02-2 `resolved`, `recheck`-Notiz, UAT 4/4 bestanden).
  - WR-05 ist behoben (`9b87e7f`).
- **WR-05 selbst nachgeprüft:**
  - `escape_markdown` (`xmltv/preview.py:41-49`) fasst zuerst jede `\s+`-Folge zu einem Leerzeichen zusammen und trimmt die Ränder. Erst danach laufen HTML-Entities, Zeichenschleife und Autolink-Trigger.
  - Die 18 neuen Tests sind gegen `preview.py` aus `4322456` rot: 14 failed, die 4 Byte-Identitäts-Guards grün. Auf HEAD sind alle grün.
- **Kein Einfluss auf den UAT-Re-Check.** Alle 9 Titel und Display-Namen aus `uat-markdown.xml` escapen auf HEAD byte-identisch zum Stand vor WR-05. Der Browser-Re-Check auf 02-10-Code gilt damit auch für HEAD.
- **Keine Regressionen:**
  - Volle Suite: 557 passed, 1 skipped (einmal ausgeführt).
  - Ruff check und format sind sauber (49 Dateien).
  - Artefakte 39/39 und Key-Links 21/21 über alle 10 Pläne.
- **Keine Human-Items mehr, keine Gaps.** Status `passed`.

## User Flow Coverage

| Schritt | Erwartet | Evidenz | Status |
|---------|----------|---------|--------|
| "Add calendar" öffnen | Basisformular mit Name, Kanälen, Regex-Feldern, "Advanced options" | config_flow.py:356-412; UAT test 1 | ✓ |
| Ungültiges Muster eingeben | `invalid_regex` mit Muster und Meldung | filter.py:174-194 (`PATTERN_ERRORS`, Nested-Repeat); UAT test 1 | ✓ |
| Advanced-Schritt | Felder, Case, Fenster, Wochentage, Dauer, Templates mit Validierung | config_flow.py:243-325, 414-438; test_advanced_flow.py | ✓ |
| Absenden → Vorschau | Anzahl plus bis zu 10 Zeilen, Feedtext wörtlich und einzeilig | preview.py:70-89; config_flow.py:440-466; UAT tests 1+2 | ✓ |
| Back / Save | Back füllt vor, Save legt an | config_flow.py:468-484; UAT test 1 | ✓ |
| Kalender zeigt Treffer | Nur Sendungen, die alle Bedingungen erfüllen, Template-Titel | filter.py `apply`; render.py; test_filtering.py, test_templates.py | ✓ |
| "Edit calendar" → Save | In-place, ohne Download/Reload | `async_update_and_abort` + `_async_entry_updated`; test_reconfigure.py; UAT test 1 | ✓ |

## Goal Achievement

### Observable Truths: Roadmap Success Criteria

| # | Truth | Status | Evidenz |
|---|-------|--------|---------|
| SC1 | Include/Exclude-Felder getrennt wählbar; standardmäßig case-insensitive mit Toggle; Umlaute matchen in NFC und NFD | ✓ VERIFIED | `FilterSpec.include_fields`/`exclude_fields`, `_field_values` (filter.py:197-216); `_flags` und Kanal-Regex immer IGNORECASE (filter.py:251-253); `_lines` NFC (filter.py:124-126), `parser._text` NFC (parser.py:58). Tests: test_umlaut_pattern_matches_decomposed_feed, test_category_field_selection_end_to_end, test_field_and_case_table, test_case_sensitive_in_flow |
| SC2 | Min/Max-Dauer, Zeitfenster über Mitternacht, Wochentage; jede Bedingung muss erfüllt sein | ✓ VERIFIED | `TimeWindow.anchor_date` (halboffen, Mitternachts-Anker), `_duration_matches` auf Fixed-Offset-Datetimes, `apply` prüft Kanal → Dauer → Fenster/Wochentag → Include → Exclude (filter.py:84-316). Tests: test_friday_night_window_end_to_end [berlin, new-york], DST-Zeilen 2026-10-25/2027-03-28, test_duration_bounds, test_every_constraint_must_pass |
| SC3 | Vor dem Speichern: Trefferanzahl und nächste ~10 Treffer mit Kanal und Startzeit | ✓ VERIFIED | `build_preview` im Executor (config_flow.py:447-454), `stop > now`, `PREVIEW_LIMIT = 10`, Zeilenformat `<Wt> <dd.mm.> <HH:MM> · <Kanal> · <Titel>`. Feedtext wird wörtlich (02-10) und einzeilig (WR-05) dargestellt. Tests: test_tracer, test_preview.py, test_preview_shows_feed_urls_as_plain_text, test_preview_keeps_one_line_per_match_despite_feed_line_breaks; UAT tests 1+2 |
| SC4 | Titel-Template mit sechs Platzhaltern, optionales Beschreibungs-Template, unbekannte Platzhalter im Flow abgelehnt, Default-Beschreibung | ✓ VERIFIED | `TITLE_FIELDS` (render.py:20), `compile_template` lehnt Feld/Spec/Conversion ab; `default_description` (render.py:97-109); Flow-Validierung `_advanced_errors` (config_flow.py:285-318). Tests: test_template_error_reasons, test_title_template_end_to_end, test_default_description_end_to_end, test_advanced_validation |
| SC5 | Filter und Templates umkonfigurieren ohne Re-Download/Re-Parse/Reload der Geschwister | ✓ VERIFIED | `async_step_reconfigure = async_step_basic`, `async_update_and_abort` (config_flow.py:478-480, nie die Reload-Variante); Listener wendet in-place an (`__init__.py:39-43`, calendar.py:160-198). Tests: test_reconfigure_flow_end_to_end, test_advanced_checkbox_prechecked_on_edit (assert call_count unverändert, `entry.runtime_data is runtime`, `coordinator.data is epg`, Geschwister-Entity identisch); UAT test 1 (kein "Downloaded"-Log nach zwei Edits) |

### Observable Truths: Plan must_haves

| Plan | Truths | Status | Anmerkungen |
|------|--------|--------|-------------|
| 02-01 | 9 | 9 ✓ | Verhaltensabhängige Truths (#8 No-op, #9 Generation-Counter/Reihenfolge, #5 vor dem Hinzufügen) durch Tests abgedeckt: test_unchanged_update_is_a_no_op, test_two_calendars_changed_together, test_last_of_two_updates_wins, test_apply_before_added_stores_settings; Suite grün |
| 02-02 | 13 | 13 ✓ | #13 (backstop, Nebenläufigkeit) human akzeptiert in UAT test 3; Code-Struktur unverändert (`FilterSpec` frozen, Muster pro Kalender kompiliert) |
| 02-03 | 10 | 10 ✓ | #7 "Markdown- oder HTML-Zeichen werden wörtlich dargestellt": durch 02-10 (Autolinks, `~`) und WR-05 (Zeilenumbrüche) jetzt vollständig; der im vorigen Bericht offene Teil (Zeilenumbrüche) ist geschlossen |
| 02-04 | 13 | 13 ✓ | Unverändert seit 79054e2; Suite grün |
| 02-05 | 8 | 8 ✓ | Unverändert; Suite grün |
| 02-06 | 11 | 11 ✓ | Unverändert; Suite grün |
| 02-07 | 8 | 8 ✓ | Unverändert; Suite grün |
| 02-08 | 8 | 8 ✓ | #8: Suite und Ruff grün, UAT-Walkthrough in UAT test 1 bestanden |
| 02-09 | 5 (1 dedupliziert mit 02-01 #6) | 5 ✓ | Deep-Nesting-Ids siehe `coincidental_reliance_items` (nur Hinweis) |
| 02-10 | 6 | 6 ✓ | siehe Tabelle unten |

**02-10 Truths im Einzelnen**

| # | Truth (gekürzt) | Status | Evidenz |
|---|-----------------|--------|---------|
| 1 | http/https/ftp-URLs in jeder Schreibweise: ein Backslash vor dem `:` von `://` | ✓ VERIFIED | `_AUTOLINK_TRIGGERS` (preview.py:37); test_url_scheme_separator_is_escaped grün; eigener Probe: `[link](http://x.y)` → `\[link\](http\://x.y)` |
| 2 | `www.` (jede Schreibweise) und E-Mail inkl. `mailto:`/`xmpp:`: `.` nach `www` und jedes `@` escaped | ✓ VERIFIED | test_www_and_email_are_not_autolinked grün; Probe `www.a.de u@b.de` → `www\.a.de u\@b.de` |
| 3 | `~~x~~` und `~x~` wörtlich | ✓ VERIFIED | `"~"` in `_MARKDOWN_CHARS` (preview.py:36); test_tilde_is_escaped grün |
| 4 | Jeder Backslash ist ein CommonMark-Escape; Zeilen ohne Trigger byte-identisch | ✓ VERIFIED | Probe auf HEAD: `Formel 1: Rennen`, `javascript:x`, `Channel: Running` unverändert, `C:\path` → `C:\\path`, `a\@b` → `a\\\@b`. Die WR-05-Zusammenfassung läuft vor allen Escapes und erzeugt keinen Trigger: `http:\n//x` → `http: //x`, `www\n.x` → `www .x`. test_single_line_text_is_byte_identical (4 ids) grün |
| 5 | Echter Subentry-Flow: `matches` == `- Tue 13.10. 14:00 · Das Erste · Das Erste: \[link\](http\://x.y)` | ✓ VERIFIED | test_preview_shows_feed_urls_as_plain_text grün (einzeln ausgeführt) |
| 6 | UAT-Re-Check auf ha-dev mit uat-markdown.xml | ✓ VERIFIED | 02-UAT.md G-02-2: `status: resolved`, `recheck: "2026-10-15 ha-dev via chrome-devtools: http://, HTTP://, https://www., www.ard.de and redaktion@example.de render as plain text (no <a>), ~~strike~~ keeps its tildes, no stray backslashes"`. Gilt für HEAD: alle 9 Fixture-Texte escapen mit HEAD und mit `4322456` identisch (eigener Vergleich) |

**Score:** 96/96 Truths verifiziert. Davon 5/5 Roadmap-SC und 91/91 Plan-Truths nach Deduplizierung. 0 FAILED, 0 present-but-behavior-unverified, 0 human.

### Required Artifacts

`verify.artifacts` über alle 10 Pläne: **39/39 bestanden**. Jeder Aufruf endete mit Exit 0.

| Artefakt | Status | Details |
|----------|--------|---------|
| xmltv/preview.py | ✓ VERIFIED | `_WHITESPACE_RUNS = re.compile(r"\s+")` (Z. 38), erste Anweisung in `escape_markdown` (Z. 43); `_AUTOLINK_TRIGGERS`, `~` in `_MARKDOWN_CHARS`; Kommentar Z. 32-34 nennt WR-05 |
| xmltv/filter.py, settings.py, render.py, window.py, parser.py | ✓ VERIFIED | Seit 79054e2 unverändert; Inhalte gelesen und gegen die Truths geprüft (siehe SC-Tabelle) |
| calendar.py, __init__.py, config_flow.py, const.py, translations/en.json | ✓ VERIFIED | Seit 79054e2 unverändert; `async_apply_subentry`, `_build_spec` mit `PATTERN_ERRORS`, `has_advanced`-Precheck, `async_update_and_abort` vorhanden |
| tests/xmltv/test_preview.py, tests/test_subentry_flow.py | ✓ VERIFIED | WR-05-Tests: test_whitespace_runs_collapse_to_one_space (12 ids), test_feed_line_breaks_stay_on_one_preview_line, test_single_line_text_is_byte_identical (4 ids), test_preview_keeps_one_line_per_match_despite_feed_line_breaks |

### Key Link Verification

`verify.key-links` über alle 10 Pläne: **21/21 verifiziert**.

| Von | Nach | Via | Status |
|-----|------|-----|--------|
| preview.py `format_line` | preview.py `escape_markdown` | Kanalname und gerenderter Titel laufen durch `escape_markdown` (Z. 67) | ✓ WIRED |
| config_flow.py `async_step_preview` | preview.py `build_preview` | `async_add_executor_job(build_preview, ...)`, `"matches": "\n".join(f"- {line}" ...)` | ✓ WIRED |
| config_flow.py `async_step_save` | `__init__._async_entry_updated` → `entity.async_apply_subentry` | `async_update_and_abort` → Update-Listener → In-place-Anwendung | ✓ WIRED |
| calendar.py `_build_spec` | filter.py `PATTERN_ERRORS` | `except PATTERN_ERRORS` in `__init__` und `async_apply_subentry` | ✓ WIRED |
| calendar.py / preview.py | filter.py `apply(..., tz=)`, render.py `EventTemplates.from_mapping` | Entity und Vorschau nutzen denselben Filter-, Zeitzonen- und Template-Pfad | ✓ WIRED |

### Data-Flow Trace (Level 4)

| Artefakt | Daten | Quelle | Echte Daten | Status |
|----------|-------|--------|-------------|--------|
| Vorschau-Zeilen | `PreviewResult.lines` | `entry.runtime_data.coordinator.data` → `FilterSpec.apply` → `to_event_fields` → `format_line` → `escape_markdown` | Ja (Flow-Tests mit echtem Feed über aioclient_mock und Coordinator-Parse) | ✓ FLOWING |
| Kalender-Events | `self._index` | `coordinator.data` → `FilterSpec.apply` im Executor | Ja | ✓ FLOWING |
| Edit-Formular | `_pending` | `with_defaults(subentry.data)` + Titel | Ja | ✓ FLOWING |

### Behavioral Spot-Checks

| Verhalten | Befehl | Ergebnis | Status |
|-----------|--------|----------|--------|
| Volle Suite (einmal) | `uv run pytest tests -q` | 557 passed, 1 skipped, 42.5 s | ✓ PASS |
| Lint/Format | `ruff check .` / `ruff format --check .` | All checks passed / 49 files already formatted | ✓ PASS |
| WR-05- und G-02-2-Tests auf HEAD | `pytest tests/test_subentry_flow.py tests/xmltv/test_preview.py -k "<WR-05- und 02-10-Tests>"` | 35 passed | ✓ PASS |
| WR-05 rot vor dem Fix | dieselben WR-05-Tests gegen `preview.py` aus `4322456` (danach wiederhergestellt, `cmp` identisch) | 14 failed, 4 passed (die Byte-Identitäts-Guards) | ✓ (erwartet rot) |
| WR-05-Reproduktion | `escape_markdown('Sport\n1. Liga')`, `'Spiel\r1. Halbzeit'`, `'a\r\n---\r\nb'`, `'x\u2028+ y'` | `Sport 1. Liga`, `Spiel 1. Halbzeit`, `a --- b`, `x + y` (kein Umbruch mehr) | ✓ PASS |
| 02-10 Plan-Spot-Check | `escape_markdown('[link](http://x.y) www.a.de u@b.de ~~x~~')` | `\[link\](http\://x.y) www\.a.de u\@b.de \~\~x\~\~` | ✓ PASS |
| 02-09 Plan-Spot-Check | `first_invalid_pattern('a{99999999999}')` | `InvalidPattern(pattern='a{99999999999}', message='the repetition number is too large')` | ✓ PASS |
| UAT-Evidenz gilt für HEAD | escape_markdown alt (`4322456`) vs. HEAD über alle `title`/`display-name`/`sub-title` von `uat-markdown.xml` | 9 Texte, 0 Unterschiede | ✓ PASS |
| Commit-Umfang WR-05 | `git show --stat 1132145 9b87e7f` | test: nur Tests und Evidenz; feat: nur `xmltv/preview.py` | ✓ PASS |
| Commits existieren | `verify.commits` über 10 Phase-/Quick-Commits | all_valid | ✓ PASS |

### Probe Execution

Step 7c: keine Probes deklariert, kein `scripts/*/tests/probe-*.sh` im Repo. Nicht anwendbar.

### Requirements Coverage

| Requirement | Source Plan | Beschreibung | Status | Evidenz |
|-------------|-------------|--------------|--------|---------|
| FLT-05 | 02-02, 02-07 | Getrennte Feldauswahl für Include/Exclude | ✓ SATISFIED | SC1 |
| FLT-06 | 02-02, 02-07, 02-08 | Case-Toggle, Unicode-normalisierungssichere Umlaute | ✓ SATISFIED | SC1 |
| FLT-08 | 02-04, 02-07 | Min/Max-Dauer | ✓ SATISFIED | SC2 |
| FLT-09 | 02-04, 02-07 | Zeitfenster über Mitternacht, Wochentage | ✓ SATISFIED | SC2 |
| FLT-10 | 02-03, 02-07, 02-08, 02-10 (+ Quick 261015-u6j) | Vorschau mit Anzahl und nächsten ~10 Treffern | ✓ SATISFIED | SC3, 02-10 Truths 1-6, WR-05 |
| FLT-11 | 02-01, 02-05, 02-08, 02-09 | Alle Filter bearbeiten ohne Re-Download/Re-Parse | ✓ SATISFIED | SC5, UAT test 1 |
| EVT-03 | 02-06, 02-07 | Titel-Template, unbekannte Platzhalter abgelehnt | ✓ SATISFIED | SC4 |
| EVT-04 | 02-06, 02-07 | Default-Beschreibung plus Beschreibungs-Template | ✓ SATISFIED | SC4 |
| FLT-07 (Phase 1, von 02-09 mitbeansprucht) | 02-09 | Ungültige Regex im Flow abgelehnt | ✓ SATISFIED | 02-09; UAT test 1 |

- Alle 8 Phase-IDs werden von mindestens einem Plan beansprucht.
- REQUIREMENTS.md ordnet Phase 2 keine weiteren IDs zu. Es gibt keine verwaisten Requirements.
- Die Traceability-Tabelle in REQUIREMENTS.md steht für FLT-05, FLT-06, FLT-08, FLT-09, FLT-11, EVT-03 und EVT-04 noch auf "Gaps Found". Nur FLT-10 steht auf "Complete", und die Checkboxen oben sind entsprechend offen. Das aktualisiert der Orchestrator nach diesem Bericht.

### Prohibitions (ADR-550)

| Plan | Prohibition | Tier | Status |
|------|-------------|------|--------|
| 02-02 | (a) keine programmspezifische Matching-Logik | judgment | ✓ human bestätigt (UAT test 4) |
| 02-02 | (b) keine Musteränderung über NFC hinaus | judgment | ✓ human bestätigt (UAT test 4); filter.py seit 79054e2 unverändert |
| 02-03 | (c) Vorschau-Treffer und -Titel == gespeicherter Kalender | judgment | ✓ human bestätigt (UAT test 4, live in UAT test 1). WR-05 ändert nur die Anzeige im Flow: `escape_markdown` sitzt nur in `format_line`, nicht in `to_event_fields`. Treffermenge und Titeltext bleiben gleich, nur Whitespace wird für die Markdown-Liste vereinheitlicht |

### Anti-Patterns Found

| Datei | Zeile | Muster | Schwere | Auswirkung |
|-------|-------|--------|---------|------------|
| config_flow.py | 405 | `pending \| (user_input or {})` im Fehlerpfad (WR-01) | ⚠️ Warning | Ein geleertes Feld kommt nach einem Validierungsfehler zurück; offen laut 02-REVIEW-DISPOSITION.md |
| translations/en.json, de.json | 138-140 | kein `reconfigure_successful`-Text (WR-02) | ⚠️ Warning | HA zeigt den generischen Text "Die Neukonfiguration war erfolgreich" (UAT test 1); funktional unkritisch |
| xmltv/filter.py | 149-151 | `unbounded = high > 1` (WR-03) | ⚠️ Warning | `(\d{2}:)+` wird im Flow abgelehnt, obwohl harmlos (Over-Rejection, kein Sicherheitsproblem) |
| config_flow.py | 376-377 | gemeinsamer `pattern`/`error`-Platzhalter (WR-04) | ⚠️ Warning | Ein zweites ungültiges Feld zeigt die Meldung des ersten |
| xmltv/render.py | 88 | `clean_title` ersetzt nur `\n`, nicht `\r`/`\u2028` | ℹ️ Info | Nur Kalender-Summary (Klartext, kein Markdown), kosmetisch; vom Review als Folgepunkt genannt, kein Finding |
| xmltv/preview.py | 43 | `\s+`-Zusammenfassung erfasst auch NBSP, `\u202f`, `\u3000` | ℹ️ Info | Beabsichtigt (Testfall `nbsp`); betrifft nur die Vorschauanzeige, nicht gespeicherte Daten oder Kalender |
| tests/test_calendar.py, tests/test_reconfigure.py | 29, 36 | `DEEP_NESTING` hängt vom Default-Rekursionslimit ab (IN-07) | ℹ️ Info | siehe `coincidental_reliance_items`; nur Test-Robustheit |

- Es gibt keine TBD/FIXME/XXX/TODO/HACK-Marker in `custom_components/` oder in den durch WR-05 geänderten Testdateien.
- Die übrigen offenen Review-Punkte (IN-01..IN-03, IN-05, IN-06, IN-08..IN-10) bleiben Info.
- Keiner der offenen Punkte widerspricht einer Must-Have-Truth oder einem Success Criterion.

### Human Verification Required

Keine. Beide Punkte des vorigen Berichts sind erledigt:

1. **UAT test 2 Re-Check:** auf ha-dev am 2026-10-15 durchgeführt und in 02-UAT.md festgehalten. Die WR-05-Änderung lässt alle Fixture-Ausgaben byte-identisch.
2. **WR-05-Entscheidung:** der Nutzer hat "jetzt beheben" gewählt. Behoben in `9b87e7f`, Disposition `fixed`.

### Gaps Summary

Keine Gaps:

- Alle fünf Roadmap-Success-Criteria und alle 91 Plan-Truths sind gegen den Code und durch Tests belegt.
- Die drei Judgment-Prohibitions und die Backstop-Truth sind menschlich abgenommen (UAT tests 3 und 4).
- Der letzte offene Human-Punkt (02-10 Truth 6) ist durch den dokumentierten ha-dev-Re-Check erledigt.
- Das Phasenziel ist erreicht.

Vor `/gsd-ship` (nicht blockierend):

- **WR-01..WR-04 stehen weiterhin auf `open`.** Empfehlung wie zuvor:
  - WR-02 beheben (je eine Zeile in en.json und de.json) und WR-01 beheben.
  - Den Rest bewusst auf `deferred` setzen.
- **REQUIREMENTS.md:** Die Traceability-Zeilen der sieben IDs von "Gaps Found" auf "Complete" setzen und die Checkboxen abhaken (Orchestrator).

---

_Verifiziert: 2026-10-15T20:08:11Z_
_Verifier: Claude (gsd-verifier)_
