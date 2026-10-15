---
phase: 02-precise-filters-preview
verified: 2026-10-15T19:40:00Z
status: human_needed
score: 95/96 must-haves verified
covered_files: [".planning/phases/02-precise-filters-preview/02-01-PLAN.md", ".planning/phases/02-precise-filters-preview/02-01-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-02-PLAN.md", ".planning/phases/02-precise-filters-preview/02-02-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-03-PLAN.md", ".planning/phases/02-precise-filters-preview/02-03-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-04-PLAN.md", ".planning/phases/02-precise-filters-preview/02-04-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-05-PLAN.md", ".planning/phases/02-precise-filters-preview/02-05-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-06-PLAN.md", ".planning/phases/02-precise-filters-preview/02-06-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-07-PLAN.md", ".planning/phases/02-precise-filters-preview/02-07-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-08-PLAN.md", ".planning/phases/02-precise-filters-preview/02-08-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-09-PLAN.md", ".planning/phases/02-precise-filters-preview/02-09-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-10-PLAN.md", ".planning/phases/02-precise-filters-preview/02-10-SUMMARY.md", ".ruff.toml", "custom_components/xmltv_calendar/__init__.py", "custom_components/xmltv_calendar/calendar.py", "custom_components/xmltv_calendar/config_flow.py", "custom_components/xmltv_calendar/const.py", "custom_components/xmltv_calendar/translations/en.json", "custom_components/xmltv_calendar/xmltv/filter.py", "custom_components/xmltv_calendar/xmltv/parser.py", "custom_components/xmltv_calendar/xmltv/preview.py", "custom_components/xmltv_calendar/xmltv/render.py", "custom_components/xmltv_calendar/xmltv/settings.py", "custom_components/xmltv_calendar/xmltv/window.py", "tests/conftest.py", "tests/test_advanced_flow.py", "tests/test_calendar.py", "tests/test_filtering.py", "tests/test_init.py", "tests/test_reconfigure.py", "tests/test_subentry_flow.py", "tests/test_templates.py", "tests/test_tracer.py", "tests/xmltv/test_filter.py", "tests/xmltv/test_parser.py", "tests/xmltv/test_preview.py", "tests/xmltv/test_render.py", "tests/xmltv/test_settings.py", "tests/xmltv/test_window.py"]
covered_digest: "v3:sha256:4ba38411ad302fbc94ba43e0432b1ef6f50a99ab0264fca141e0e832a4a47814"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 89/90
  gaps_closed:
    - "G-02-2 (UAT test 2): Preview renders feed text literally; bare URLs, 'www.' hosts and e-mail addresses are no longer autolinked (in code; rendering re-check on ha-dev pending)"
    - "IN-04: '~~x~~' / '~x~' render literally (tilde escaped)"
  gaps_remaining: []
  regressions: []
advisory:
  - finding: "IN-07: DEEP_NESTING fixture ('(' * 2000) relies on the default recursion limit and is duplicated in tests/test_calendar.py:29 and tests/test_reconfigure.py:36"
    category: other
    reason: "Test-robustness concern from 02-REVIEW.md, not a product defect. Resolve by deriving the depth from sys.getrecursionlimit() in tests/conftest.py"
    evidence_status: "none provided (both parametrisations pass at the default limit; no failing run under the current harness)"
human_verification:
  - test: "UAT test 2 re-check on ha-dev (02-10 truth 6, G-02-2): restart ha-dev so it loads the new preview.py, reload the source for /media/xmltv/uat-markdown.xml, open 'Add calendar' with no filters and go to the preview. Do it before 2026-10-15 20:50Z to see all 8 programmes (the first one drops out after its stop; the last ends 2026-10-16 03:50Z)"
    expected: "'[link](http://x.y)', 'Info: www.ard.de', 'Mail an redaktion@example.de', 'HTTP://X.Y shouting' and 'https://www.zdf.de/live' show as plain, non-clickable text (no <a> in the preview list DOM); '~~strike~~ test' shows both tilde pairs and is not struck through; *, _, [, <, &, backticks still literal; no stray backslash anywhere"
    why_human: "Only the HA frontend's marked (GFM) in the markdown worker decides what becomes a link; pytest checks the escaped strings. Independent render with marked 14.0.0 (not HA's bundle) already shows no <a>/<del> for all 8 fixture lines"
  - test: "Decision WR-05 (escalation): a line break in a channel display name ('\\n', kept by parser._text) or a '\\r' in a title (clean_title only replaces '\\n') reaches the preview line unchanged and splits the Markdown list. Reproduced: display-name 'Sport\\n1. Liga' + title 'Spiel&#13;1. Halbzeit' -> marked renders '<ul>...Sport</ul><ol><li>Liga ...</li><li>Halbzeit</li></ol>', the '1.' is swallowed as a list marker"
    expected: "Either fix now (02-REVIEW.md WR-05: collapse \\s+ to one space at the start of escape_markdown, plus 3 test cases; optionally '\\r' in render.clean_title) or set WR-05 to 'deferred' with a reason in 02-REVIEW-DISPOSITION.md before /gsd-ship"
    why_human: "Product decision: same defect class as G-02-2 (feed text not rendered literally), but cosmetic (no link, no XSS), needs pathological feed input, and the 02-03/02-10 must_haves name characters and autolinks, not line breaks. Not counted as a failed truth"
---

# Phase 2: Precise Filters & Preview – Verifikationsbericht

**Phase Goal:** User can pinpoint specific shows with field-scoped, Unicode-safe regex plus duration and time-window filters, shape event title and description via templates, check the result in a live preview before saving, and retune any calendar instantly without touching the source.
**Verifiziert:** 2026-10-15T19:40:00Z
**Status:** human_needed
**Re-Verifikation:** Ja, nach Gap-Closure-Plan 02-10 (G-02-2 + IN-04). Vorher: human_needed, 89/90.
**Mode:** mvp (ROADMAP). Das Ziel ist eine Fähigkeitsbeschreibung, keine User Story. Wie bisher dienen Zieltext und die fünf Roadmap-Success-Criteria als Vertrag.

## Ergebnis in Kürze

- **G-02-2 ist im Code geschlossen.** `escape_markdown` (`xmltv/preview.py:33-44`) escaped nach der Zeichenschleife den `:` von `://`, den `.` nach `www` (case-insensitive) und jedes `@`. `~` ist in `_MARKDOWN_CHARS` (IN-04).
- **Red-before-green selbst nachgewiesen:** Die 16 neuen 02-10-Tests sind gegen `preview.py` aus `3b32cc4` rot und auf HEAD grün. Die zwei bestehenden Escaping-Tests sind unverändert und grün.
- **Rendering unabhängig geprüft:** Mit marked 14.0.0 (`gfm: true, breaks: true`) rendern alle 8 Zeilen der UAT-Fixture ohne `<a>` und ohne `<del>`. HAs eigenes marked-Bundle prüft das nicht; dafür bleibt der UAT-Re-Check.
- **Keine Regressionen.** Volle Suite 539 passed / 1 skipped; Ruff check und format sauber; Artefakte 39/39, Key-Links 21/21 über alle 10 Pläne.
- **UAT-Tests 1, 3, 4 bestanden** und erledigen die früheren Human-Items (Walkthrough, Backstop-Truth, drei Judgment-Prohibitions).
- **Offen:** UAT test 2 Re-Check auf ha-dev und eine Entscheidung zu **WR-05** (Zeilenumbrüche im Feedtext zerlegen die Vorschauliste, von mir reproduziert). Daher `human_needed`.

## User Flow Coverage

| Schritt | Erwartet | Evidenz | Status |
|---------|----------|---------|--------|
| "Add calendar" öffnen | Basisformular mit Name, Kanälen, Regex-Feldern, "Advanced options" | config_flow.py; UAT test 1 (pass) | ✓ |
| Ungültiges Muster eingeben | `invalid_regex` mit Muster und Meldung | 02-09; UAT test 1 (`a{99999999999}` zeigt den konkreten Grund) | ✓ |
| Advanced-Schritt | Felder, Case, Fenster, Wochentage, Dauer, Templates | test_advanced_flow.py; UAT test 1 | ✓ |
| Absenden → Vorschau | Anzahl plus bis zu 10 Zeilen, Feedtext wörtlich | preview.py; UAT test 1 (Vorschau == gespeicherter Kalender); Feedtext-Darstellung: 02-10 + Re-Check | ✓ (Rendering: human) |
| Back / Save | Back füllt vor, Save legt an | UAT test 1 | ✓ |
| Kalender zeigt Treffer | Nur Sendungen, die alle Bedingungen erfüllen, Template-Titel | test_filtering.py, test_templates.py; UAT test 1 (30 Events) | ✓ |
| "Edit calendar" → Save | In-place, ohne Download/Reload | test_reconfigure.py; UAT test 1 (kein "Downloaded"-Log nach zwei Edits) | ✓ |

## Goal Achievement

### Observable Truths: Roadmap Success Criteria (Regression-Check)

| # | Truth | Status | Evidenz |
|---|-------|--------|---------|
| SC1 | Felder für Include/Exclude getrennt wählbar; standardmäßig case-insensitive mit Toggle; Umlaute matchen in NFC und NFD | ✓ VERIFIED | Seit 02-09 kein Code-Diff außer preview.py; Tests in der vollen Suite grün |
| SC2 | Min/Max-Dauer, Zeitfenster über Mitternacht, Wochentage; jede Bedingung muss erfüllt sein | ✓ VERIFIED | Unverändert; Suite grün; UAT test 1 (Fenster Do 22:00 bis Fr 01:50) |
| SC3 | Vor dem Speichern: Trefferanzahl und nächste ~10 Treffer mit Kanal und Startzeit | ✓ VERIFIED | build_preview/format_line unverändert, nur escape_markdown erweitert; UAT test 1. Feedtext-Rendering: siehe 02-10 Truth 6 (human) |
| SC4 | Titel-Template mit sechs Platzhaltern, optionales Beschreibungs-Template, unbekannte Platzhalter abgelehnt, Default-Beschreibung | ✓ VERIFIED | render.py unverändert; Suite grün |
| SC5 | Filter und Templates umkonfigurieren ohne Re-Download/Re-Parse/Reload der Geschwister | ✓ VERIFIED | Unverändert; UAT test 1 bestätigt live |

### Observable Truths: Plan must_haves

| Plan | Truths | Status | Anmerkungen |
|------|--------|--------|-------------|
| 02-01 | 9 | 9 ✓ | Regression: Suite grün, calendar.py/__init__.py seit 02-09 unverändert |
| 02-02 | 13 | 13 ✓ | #13 (backstop, Nebenläufigkeit) jetzt durch UAT test 3 menschlich akzeptiert (FilterSpec frozen, Muster pro Kalender kompiliert, EpgData unveränderlich) |
| 02-03 | 10 | 10 ✓ | #7 "Markdown- oder HTML-Zeichen werden wörtlich dargestellt": für Zeichen erfüllt und durch 02-10 erweitert. Zeilenumbrüche sind nicht abgedeckt (WR-05, siehe unten) |
| 02-04 | 13 | 13 ✓ | Unverändert |
| 02-05 | 8 | 8 ✓ | Unverändert |
| 02-06 | 11 | 11 ✓ | Unverändert |
| 02-07 | 8 | 8 ✓ | Unverändert |
| 02-08 | 8 | 8 ✓ | Gate erneut: Suite, Ruff grün; UAT-Durchgang in UAT test 1 bestanden |
| 02-09 | 5 (1 dedupliziert mit 02-01 #6) | 5 ✓ | Unverändert |
| 02-10 (Gap Closure) | 6 | 5 ✓, 1 human | siehe Tabelle unten |

**02-10 Truths im Einzelnen**

| # | Truth (gekürzt) | Status | Evidenz |
|---|-----------------|--------|---------|
| 1 | http/https/ftp-URLs in jeder Schreibweise: genau ein Backslash vor dem `:` von `://` | ✓ VERIFIED | `_AUTOLINK_TRIGGERS` (preview.py:35) Zweig `:(?=//)`; test_url_scheme_separator_is_escaped (6 ids) grün, 5 davon rot auf 3b32cc4; eigener Probe `hTtPs://WwW.x.de` → `hTtPs\://WwW\.x.de` |
| 2 | `www.` (jede Schreibweise, auch `wwww.` und nach Schema) und E-Mail inkl. `mailto:`/`xmpp:`: `.` nach `www` und jedes `@` escaped | ✓ VERIFIED | Zweige `(?<=www)\.` und `@`, `re.IGNORECASE`; test_www_and_email_are_not_autolinked (8 ids) grün, alle rot auf 3b32cc4; eigener Probe `xmpp:a@b.cd/res` → `xmpp:a\@b.cd/res` |
| 3 | `~~x~~` und `~x~` wörtlich | ✓ VERIFIED | `"~"` in `_MARKDOWN_CHARS` (preview.py:34); test_tilde_is_escaped (2 ids) grün, rot auf 3b32cc4 |
| 4 | Jeder Backslash ist ein CommonMark-Escape; Zeilen ohne Trigger byte-identisch (`Formel 1: Rennen`, `javascript:x`, `C:\path`, `Channel: Running`) | ✓ VERIFIED | Eigener Probe: alle vier unverändert gegenüber vorher; `a\@b` → `a\\\@b` (kein verdoppelter Escape); die zwei bestehenden Escaping-Tests unverändert grün (`git diff 81be08a^..acfe879` entfernt nur die Importzeile); marked 14.0.0 rendert die Fixture-Zeilen zeichengleich zum Feedtext |
| 5 | Echter Subentry-Flow: `matches` == `- Tue 13.10. 14:00 · Das Erste · Das Erste: \[link\](http\://x.y)` | ✓ VERIFIED | test_preview_shows_feed_urls_as_plain_text (test_subentry_flow.py:404) prüft den kompletten Platzhalter; grün auf HEAD, rot auf 3b32cc4 |
| 6 | UAT-Re-Check auf ha-dev mit uat-markdown.xml | ? HUMAN | Fixture bereit (8 Programme 2026-10-15 20:00Z bis 2026-10-16 03:50Z, Titel mit URL, `www.`, E-Mail, `HTTP://`, `~~`). HAs Frontend-Rendering ist nicht automatisiert prüfbar |

**Score:** 95/96 Truths verifiziert (5/5 Roadmap-SC, 90/91 Plan-Truths nach Deduplizierung). 0 FAILED, 0 present-but-behavior-unverified, 1 human (02-10 #6).

### Advisory (New Scope, Unevidenced)

| # | Finding | Kategorie | Warum Advisory |
|---|---------|-----------|----------------|
| 1 | IN-07: `DEEP_NESTING` hängt vom Default-Rekursionslimit ab und ist doppelt definiert | other | Test-Robustheit, kein Produktdefekt; kein roter Lauf |

WR-05 ist **nicht** Advisory: Es ist deterministisch reproduziert (siehe Spot-Checks) und als Entscheidung unter Human Verification eskaliert.

### Required Artifacts

`verify.artifacts` über alle 10 Pläne: **39/39 bestanden** (02-10: 3/3).

| Artefakt | Status | Details |
|----------|--------|---------|
| xmltv/preview.py | ✓ VERIFIED | `import re`, `_MARKDOWN_CHARS` endet mit `"~"`, `_AUTOLINK_TRIGGERS = re.compile(r"(?<=www)\.\|:(?=//)\|@", re.IGNORECASE)`, angewendet nach der Schleife (Z. 44); Kommentar Z. 26-31 nennt G-02-2 und IN-04 |
| tests/xmltv/test_preview.py | ✓ VERIFIED | 3 neue parametrisierte Tests, 16 ids; `escape_markdown` importiert |
| tests/test_subentry_flow.py | ✓ VERIFIED | `test_preview_shows_feed_urls_as_plain_text` mit vollständigem Platzhalter-Assert |
| übrige Phase-2-Artefakte | ✓ VERIFIED | Seit 3b32cc4 hat sich unter `custom_components/` nur preview.py geändert |

### Key Link Verification

`verify.key-links` über alle 10 Pläne: **21/21 verifiziert** (02-10: 2/2).

| Von | Nach | Via | Status |
|-----|------|-----|--------|
| preview.py `format_line` | preview.py `escape_markdown` | Kanalname und gerenderter Titel laufen beide durch `escape_markdown` (Z. 62) | ✓ WIRED |
| config_flow.py `async_step_preview` | preview.py `build_preview` | `"matches": "\n".join(f"- {line}" ...)` im Platzhalter des Preview-Menüs | ✓ WIRED |

### Data-Flow Trace (Level 4)

| Artefakt | Daten | Quelle | Echte Daten | Status |
|----------|-------|--------|-------------|--------|
| Vorschau-Zeilen | `PreviewResult.lines` | `entry.runtime_data.coordinator.data` → `FilterSpec.apply` → `to_event_fields` → `format_line` → `escape_markdown` | Ja (Flow-Test mit echtem Feed, eigener Probe mit uat-markdown.xml: 8 Zeilen) | ✓ FLOWING |
| Kalender-Events | `self._index` | `coordinator.data` → `FilterSpec.apply` im Executor | Ja | ✓ FLOWING |
| Edit-Formular | `pending` | `with_defaults(subentry.data)` | Ja | ✓ FLOWING |

### Behavioral Spot-Checks

| Verhalten | Befehl | Ergebnis | Status |
|-----------|--------|----------|--------|
| Volle Suite (einmal) | `uv run pytest tests -q` | 539 passed, 1 skipped, 42 s | ✓ PASS |
| Lint/Format | `ruff check .` / `ruff format --check .` | sauber, 49 Dateien | ✓ PASS |
| 02-10-Tests plus Guards auf HEAD | `pytest -k "<3 neue Tests, Flow-Test, 2 Guards>"` | 19 passed | ✓ PASS |
| RED vor dem Fix | dieselben Testdateien gegen `git archive 3b32cc4` | 16 failed (alle neuen ids außer plain-colon), 51 passed | ✓ (erwartet rot) |
| Plan-Spot-Check | `escape_markdown('[link](http://x.y) www.a.de u@b.de ~~x~~')` | `\[link\](http\://x.y) www\.a.de u\@b.de \~\~x\~\~` | ✓ PASS |
| Commit-Umfang | `git show --stat acfe879 debb599` | jeweils nur preview.py | ✓ PASS |
| Commits existieren | `verify.commits 81be08a acfe879 7223462 debb599` | all_valid | ✓ PASS |
| Rendering der UAT-Fixture | `build_preview` über uat-markdown.xml → marked 14.0.0 `{gfm, breaks}` | 8 `<li>`, kein `<a>`, kein `<del>`, Text zeichengleich zum Feed | ✓ PASS (nicht HAs Bundle) |
| WR-05 Reproduktion | display-name `Sport\n1. Liga`, Titel `Spiel&#13;1. Halbzeit` → `build_preview` → marked | Zeile enthält `\n1. ` und `\r1. `; marked: `<ul>…Sport</ul><ol><li>Liga …</li><li>Halbzeit</li></ol>` | ⚠ WARN (eskaliert) |

### Probe Execution

Step 7c: keine Probes deklariert, kein `scripts/*/tests/probe-*.sh` im Repo. Nicht anwendbar.

### Requirements Coverage

| Requirement | Source Plan | Beschreibung | Status | Evidenz |
|-------------|-------------|--------------|--------|---------|
| FLT-05 | 02-02, 02-07 | Getrennte Feldauswahl für Include/Exclude | ✓ SATISFIED | SC1 |
| FLT-06 | 02-02, 02-07, 02-08 | Case-Toggle, Unicode-normalisierungssichere Umlaute | ✓ SATISFIED | SC1 |
| FLT-08 | 02-04, 02-07 | Min/Max-Dauer | ✓ SATISFIED | SC2 |
| FLT-09 | 02-04, 02-07 | Zeitfenster über Mitternacht, Wochentage | ✓ SATISFIED | SC2 |
| FLT-10 | 02-03, 02-07, 02-08, 02-10 | Vorschau mit Anzahl und nächsten ~10 Treffern | ✓ SATISFIED (Feedtext-Rendering: human Re-Check; WR-05 offen) | SC3, 02-10 Truths 1-5 |
| FLT-11 | 02-01, 02-05, 02-08, 02-09 | Alle Filter bearbeiten ohne Re-Download/Re-Parse | ✓ SATISFIED | SC5, UAT test 1 |
| EVT-03 | 02-06, 02-07 | Titel-Template, unbekannte Platzhalter abgelehnt | ✓ SATISFIED | SC4 |
| EVT-04 | 02-06, 02-07 | Default-Beschreibung plus Beschreibungs-Template | ✓ SATISFIED | SC4 |
| FLT-07 (Phase 1, von 02-09 mitbeansprucht) | 02-09 | Ungültige Regex im Flow abgelehnt | ✓ SATISFIED | 02-09; UAT test 1 |

Alle 8 Phase-IDs werden von mindestens einem Plan beansprucht; REQUIREMENTS.md ordnet Phase 2 keine weiteren IDs zu, keine verwaisten Requirements. Die Traceability-Tabelle in REQUIREMENTS.md steht für sieben der acht IDs noch auf "Gaps Found" (FLT-10 auf "Complete"); das aktualisiert der Orchestrator.

### Prohibitions (ADR-550)

| Plan | Prohibition | Tier | Status |
|------|-------------|------|--------|
| 02-02 | (a) keine programmspezifische Matching-Logik | judgment | ✓ human bestätigt (UAT test 4) |
| 02-02 | (b) keine Musteränderung über NFC hinaus | judgment | ✓ human bestätigt (UAT test 4); 02-10 berührt filter.py nicht |
| 02-03 | (c) Vorschau-Treffer und -Titel == gespeicherter Kalender | judgment | ✓ human bestätigt (UAT test 4, live in UAT test 1); 02-10 ändert nur das Display-Escaping, nicht Treffermenge oder Titel |

### Anti-Patterns Found

| Datei | Zeile | Muster | Schwere | Auswirkung |
|-------|-------|--------|---------|------------|
| xmltv/preview.py | 37-44, 62 | Zeilenumbrüche im Feedtext werden nicht neutralisiert (WR-05) | ⚠️ Warning (eskaliert) | Vorschauliste zerfällt, `1.`/`-`/`+`/`---` nach einem Umbruch werden Blocksyntax. Kein Link, kein XSS. Quellen: `parser._text` (Z. 56-58) behält interne `\n` im display-name, `render.clean_title` (Z. 87) ersetzt nur `\n`, nicht `\r` |
| config_flow.py | 405 | `pending \| (user_input or {})` im Fehlerpfad (WR-01) | ⚠️ Warning | Geleertes Feld kehrt nach Validierungsfehler zurück |
| translations/en.json, de.json | 138-140 | kein `reconfigure_successful`-Text (WR-02) | ⚠️ Warning | UAT test 1: HA zeigt den generischen Text "Die Neukonfiguration war erfolgreich"; funktional unkritisch |
| xmltv/filter.py | 149-151 | `unbounded = high > 1` (WR-03) | ⚠️ Warning | `(\d{2}:)+` im Flow abgelehnt |
| config_flow.py | 316, 376-377 | gemeinsamer `pattern`/`error`-Platzhalter (WR-04) | ⚠️ Warning | Zweites ungültiges Feld zeigt die Meldung des ersten |
| tests/test_calendar.py, tests/test_reconfigure.py | 29, 36 | `DEEP_NESTING` (IN-07) | 📋 Advisory | siehe oben |

Keine TBD/FIXME/XXX/TODO/HACK-Marker in den durch 02-10 geänderten Dateien oder in `custom_components/`. IN-04 ist behoben (`fixed` in 02-REVIEW-DISPOSITION.md); IN-01..IN-03, IN-05, IN-06, IN-08..IN-10 bleiben Info.

Außerhalb des Phasenumfangs (informativ): Quick-Task 261015-su3 hat `translations/de.json` und `tests/test_translations.py` ergänzt. Das ist nicht Teil der Phase-2-Must-Haves; die Suite inklusive dieser Tests ist grün.

### Human Verification Required

1. **UAT test 2 Re-Check auf ha-dev (02-10 Truth 6, G-02-2)**
   - **Test:** ha-dev neu starten, Quelle für `/media/xmltv/uat-markdown.xml` neu laden, "Add calendar" ohne Filter bis zur Vorschau. Am besten vor 2026-10-15 20:50Z, dann sind alle 8 Programme sichtbar; danach fallen die ersten Programme schrittweise heraus, das letzte endet 2026-10-16 03:50Z.
   - **Erwartet:** `[link](http://x.y)`, `Info: www.ard.de`, `Mail an redaktion@example.de`, `HTTP://X.Y shouting`, `https://www.zdf.de/live` als normaler, nicht klickbarer Text (kein `<a>` im DOM der Liste). `~~strike~~ test` mit beiden Tilden-Paaren, nicht durchgestrichen. `*`, `_`, `[`, `<`, `&`, Backticks weiterhin wörtlich. Kein sichtbarer Backslash.
   - **Warum human:** Nur HAs marked-Bundle im Markdown-Worker entscheidet über Links. Mein Render mit marked 14.0.0 zeigt bereits das erwartete Ergebnis.
2. **Entscheidung WR-05 (Eskalation)**
   - **Befund:** Ein Zeilenumbruch im Kanalnamen (`\n`) oder ein `\r` im Titel (`&#13;`) landet unverändert in der Vorschauzeile. Reproduziert: `Sport\n1. Liga` / `Spiel&#13;1. Halbzeit` → marked macht aus der Liste `<ul>` + `<ol>`, das `1.` verschwindet als Listenmarker.
   - **Optionen:**
     - **Jetzt beheben (empfohlen, klein):** am Anfang von `escape_markdown` jede Whitespace-Folge (`\s+`) zu einem Leerzeichen zusammenfassen, plus 3 Testfälle (Patch steht in 02-REVIEW.md WR-05). Optional `\r` auch in `render.clean_title`, weil Kalendertitel dieselbe Lücke haben.
     - **Bewusst verschieben:** in 02-REVIEW-DISPOSITION.md auf `deferred` mit Begründung setzen, zum Beispiel: kosmetisch, braucht pathologischen Feed.
   - **Warum human:** Gleiche Defektklasse wie G-02-2, aber kosmetisch und außerhalb der wörtlichen Must-Haves (die nennen Zeichen und Autolinks, keine Zeilenumbrüche). Deshalb kein FAILED, aber auch kein stilles Durchwinken.

### Gaps Summary

Keine blockierenden Gaps. G-02-2 und IN-04 sind im Code geschlossen und gegen den Stand vor dem Fix rot/grün nachgewiesen. Alle fünf Roadmap-Success-Criteria und 90 von 91 Plan-Truths sind verifiziert, der Rest ist der UAT-Re-Check im echten Frontend.

Vor `/gsd-ship` offen:

- **UAT test 2 Re-Check** (Human-Item 1).
- **WR-05** beheben oder auf `deferred` setzen (Human-Item 2).
- **WR-01..WR-04** stehen weiterhin auf `open`. Sie blockieren das Phasenziel nicht. Empfehlung wie zuvor: WR-02 (je eine Zeile in en.json und de.json) und WR-01 beheben oder bewusst auf `deferred` setzen.

---

_Verifiziert: 2026-10-15T19:40:00Z_
_Verifier: Claude (gsd-verifier)_
