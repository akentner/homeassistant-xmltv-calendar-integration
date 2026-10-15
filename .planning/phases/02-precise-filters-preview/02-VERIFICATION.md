---
phase: 02-precise-filters-preview
verified: 2026-10-15T15:29:02Z
status: human_needed
score: 89/90 must-haves verified
covered_files: [".planning/phases/02-precise-filters-preview/02-01-PLAN.md", ".planning/phases/02-precise-filters-preview/02-01-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-02-PLAN.md", ".planning/phases/02-precise-filters-preview/02-02-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-03-PLAN.md", ".planning/phases/02-precise-filters-preview/02-03-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-04-PLAN.md", ".planning/phases/02-precise-filters-preview/02-04-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-05-PLAN.md", ".planning/phases/02-precise-filters-preview/02-05-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-06-PLAN.md", ".planning/phases/02-precise-filters-preview/02-06-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-07-PLAN.md", ".planning/phases/02-precise-filters-preview/02-07-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-08-PLAN.md", ".planning/phases/02-precise-filters-preview/02-08-SUMMARY.md", ".planning/phases/02-precise-filters-preview/02-09-PLAN.md", ".planning/phases/02-precise-filters-preview/02-09-SUMMARY.md", ".ruff.toml", "custom_components/xmltv_calendar/__init__.py", "custom_components/xmltv_calendar/calendar.py", "custom_components/xmltv_calendar/config_flow.py", "custom_components/xmltv_calendar/const.py", "custom_components/xmltv_calendar/translations/en.json", "custom_components/xmltv_calendar/xmltv/filter.py", "custom_components/xmltv_calendar/xmltv/parser.py", "custom_components/xmltv_calendar/xmltv/preview.py", "custom_components/xmltv_calendar/xmltv/render.py", "custom_components/xmltv_calendar/xmltv/settings.py", "custom_components/xmltv_calendar/xmltv/window.py", "tests/conftest.py", "tests/test_advanced_flow.py", "tests/test_calendar.py", "tests/test_filtering.py", "tests/test_init.py", "tests/test_reconfigure.py", "tests/test_subentry_flow.py", "tests/test_templates.py", "tests/test_tracer.py", "tests/xmltv/test_filter.py", "tests/xmltv/test_parser.py", "tests/xmltv/test_preview.py", "tests/xmltv/test_render.py", "tests/xmltv/test_settings.py", "tests/xmltv/test_window.py"]
covered_digest: "v3:sha256:4efce9478cd8489eed7a0a60d855a3b8e47916ac187d3e8fdf98c26a63168a23"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 83/85
  gaps_closed:
    - "A stored pattern that does not compile (hand-edited storage) makes only that calendar keep its previous matches and logs a WARNING naming the calendar; other calendars changed in the same listener call are still updated (02-01 truth 6, T-02-01)"
  gaps_remaining: []
  regressions: []
advisory:
  - finding: "IN-07: DEEP_NESTING fixture ('(' * 2000) relies on the default recursion limit and is duplicated in tests/test_calendar.py:29 and tests/test_reconfigure.py:36; under a raised limit the deep-nesting parametrisations would stop exercising the RecursionError branch"
    category: other
    reason: "Test-robustness concern from 02-REVIEW.md, not a product defect. Resolve by deriving the depth from sys.getrecursionlimit() in tests/conftest.py"
    evidence_status: "none provided (both parametrisations pass at the default limit; no failing run under the current harness)"
human_verification:
  - test: "ha-dev UAT-Durchgang, Schritte 1-9 aus 02-08-SUMMARY.md (Formular 'Add calendar', Widgets/Hilfetexte des Advanced-Schritts, Fenster 22:00-02:00 + Wochentag + Vorschau '{title} – {subtitle}' inkl. deutscher Wochentagsnamen, Back behält Werte + Save entspricht der Vorschau, 'Edit calendar' vorausgewählt + In-place-Update ohne Download, Abwählen behält Advanced-Werte, '^(\\w+\\s?)+$' abgelehnt, leere Vorschau warnt und speichert trotzdem, Logs sauber). Zusätzlich: 'a{99999999999}' im Include-Feld eingeben"
    expected: "Jeder Schritt verhält sich wie in 02-08-SUMMARY.md 'UAT Walkthrough' beschrieben; 'a{99999999999}' zeigt invalid_regex mit 'the repetition number is too large' statt 'Unknown error'. Bei Schritt 5 notieren, was der Erfolgsdialog nach 'Edit calendar' -> Save anzeigt (WR-02: keine Übersetzung für reconfigure_successful)"
    why_human: "phcc hat kein Frontend: Selektor-Darstellung, übersetzte Labels, Menü-Buttons, Markdown-Vorschau und Live-Logs brauchen die echte UI (02-08 human-check, human_verify_mode end-of-phase)"
  - test: "02-03 D4: Vorschau mit einem Feed öffnen, dessen Kanalnamen oder Titel Markdown/HTML-Zeichen enthalten"
    expected: "Die Vorschau wird als Markdown-Liste dargestellt; *, _, [, <, & und Backticks erscheinen wörtlich (bekannt: '~~x~~' wird durchgestrichen, IN-04)"
    why_human: "Das ha-markdown-Rendering der Menübeschreibung wird von keinem Test ausgeübt"
  - test: "Backstop-Truth (02-02): Executor-Threads, die mehrere Kalender gleichzeitig filtern, können die Treffer der anderen nicht verändern; ein case_sensitive-Flag eines Kalenders wirkt nie auf einen anderen"
    expected: "Anhand der Struktur akzeptieren (FilterSpec ist eine frozen dataclass, Muster werden pro Kalender in from_mapping kompiliert, EpgData ist unveränderlich) oder einen Nebenläufigkeitstest anfordern"
    why_human: "verification: backstop -> insufficient_spec. Nur Präsenz-Evidenz (filter.py FilterSpec/from_mapping; test_field_selection_does_not_leak_between_specs läuft sequenziell, nicht nebenläufig)"
  - test: "Judgment-Prohibitions (nicht autoritatives LLM-Urteil: alle drei halten). Bestätigen: (a) 02-02 keine programmspezifische Matching-Logik; (b) 02-02 keine Änderung eines Nutzermusters über NFC hinaus (kein Case-Folding, Escaping, Anchoring); (c) 02-03 Treffermenge und Titel der Vorschau entsprechen dem gespeicherten Kalender"
    expected: "(a) 'formel'/'Tatort' nur als Hilfetext-Beispiele in translations/en.json; (b) filter.py _lines/compile_patterns trimmen und NFC-normalisieren nur jede Zeile, 02-09 ändert daran nichts; (c) preview.py:67-68 nutzt FilterSpec.from_mapping(data).apply(epg, tz=tz) und EventTemplates.from_mapping(data), dieselben Aufrufe wie calendar.py, mit derselben dt_util.get_default_time_zone()"
    why_human: "Judgment-Tier-Prohibitions brauchen eine explizite menschliche Entscheidung (ADR-550 D4)"
---

# Phase 2: Precise Filters & Preview – Verifikationsbericht

**Phase Goal:** User can pinpoint specific shows with field-scoped, Unicode-safe regex plus duration and time-window filters, shape event title and description via templates, check the result in a live preview before saving, and retune any calendar instantly without touching the source.
**Verifiziert:** 2026-10-15T15:29:02Z
**Status:** human_needed
**Re-Verifikation:** Ja, nach Gap-Closure-Plan 02-09 (vorher: gaps_found, 83/85)
**Mode:** mvp (ROADMAP). Das Ziel ist eine Fähigkeitsbeschreibung, keine User Story. Wie in der Erstverifikation dienen Zieltext und die fünf Roadmap-Success-Criteria als Vertrag.

## Ergebnis in Kürze

- **Gap CR-01 / 02-01 Truth 6 ist geschlossen.** `PATTERN_ERRORS = (re.error, OverflowError, RecursionError)` (`filter.py:55`) wird an beiden Kompilierstellen gefangen: `first_invalid_pattern` (`filter.py:194-198`) und `_build_spec` (`calendar.py:50-61`).
- **Red-before-green selbst nachgewiesen:** Die neuen Tests schlagen gegen die Commits vor dem jeweiligen Fix fehl und bestehen auf HEAD.
- **Keine Regressionen.** Volle Suite 517 passed / 1 skipped (vorher 505, +12 neue Tests); Ruff check und format sauber; Artefakte 36/36, Key-Links 19/19.
- **Offen bleibt nur Menschliches:** UAT-Durchgang in ha-dev, Markdown-Rendering, Backstop-Truth, drei Judgment-Prohibitions. Daher `human_needed`, nicht `passed`.

## User Flow Coverage

| Schritt | Erwartet | Evidenz | Status |
|---------|----------|---------|--------|
| "Add calendar" öffnen | Basisformular mit Name, Kanälen, Regex-Feldern, Checkbox "Advanced options" | config_flow.py:356-408; tests/test_subentry_flow.py | ✓ (Darstellung: human) |
| Ungültiges Muster eingeben (auch `a{99999999999}`) | Formular bleibt offen, `invalid_regex` mit Muster und Meldung | config_flow.py:369-377 → filter.py:194-198; test_invalid_pattern_line_keeps_form_open (6 ids inkl. 3× repeat-overflow) | ✓ (vorher ✗) |
| "Advanced options" ankreuzen | Feldauswahl, Case-Toggle, Fenster, Wochentage, Dauer, Templates | config_flow.py:414-439; test_advanced_options_end_to_end | ✓ (Darstellung: human) |
| Absenden | Vorschau: Anzahl plus bis zu 10 Zeilen | config_flow.py:441-463 → preview.py build_preview; tests/xmltv/test_preview.py | ✓ |
| Back / Save | Back füllt Formular vor; Save legt Kalender an | config_flow.py:468-484; test_back_returns_prefilled_form, test_back_keeps_advanced_values | ✓ |
| Kalender zeigt Treffer | Nur Sendungen, die alle Bedingungen erfüllen, Template-Titel, Default-Beschreibung | calendar.py:133-158; tests/test_filtering.py, tests/test_templates.py | ✓ |
| "Edit calendar" → ändern → Save | In-place-Update: kein Download, kein Parse, kein Reload, Geschwister unberührt | config_flow.py:412, 478; __init__.py:32-46; test_reconfigure_flow_end_to_end, test_edit_repairs_overflowing_stored_pattern | ✓ (vorher ✓ mit ✗-Randfall, jetzt geschlossen) |

## Goal Achievement

### Observable Truths: Roadmap Success Criteria (Regression-Check)

| # | Truth | Status | Evidenz |
|---|-------|--------|---------|
| SC1 | Include/Exclude-Felder getrennt wählbar; standardmäßig case-insensitive mit Toggle; Umlaute matchen in NFC und NFD | ✓ VERIFIED | Unverändert seit Erstverifikation außer filter.py-Fehlerpfad; zugehörige Tests in der vollen Suite grün |
| SC2 | Min/Max-Dauer, Zeitfenster (auch über Mitternacht), Wochentage; jede Bedingung muss erfüllt sein | ✓ VERIFIED | Unverändert; test_window_and_weekday_table, test_duration_bounds, test_every_constraint_must_pass grün |
| SC3 | Vor dem Speichern: Trefferanzahl und nächste ~10 Treffer mit Kanal und Startzeit | ✓ VERIFIED | preview.py, config_flow.py unverändert seit 3c53e0f; test_count_and_line_limit grün. Darstellung: human |
| SC4 | Titel-Template mit sechs Platzhaltern, optionales Beschreibungs-Template, unbekannte Platzhalter abgelehnt, Default-Beschreibung | ✓ VERIFIED | render.py unverändert; test_render.py, test_templates.py grün |
| SC5 | Alle Filter und Templates eines Kalenders umkonfigurieren, ohne Re-Download/Re-Parse/Reload der Geschwister | ✓ VERIFIED (mit Warnungen) | Hauptpfad wie zuvor; der Randfall "gespeichertes unkompilierbares Muster" bricht den Listener nicht mehr (siehe 02-09 Truths). Warnungen WR-01, WR-03 bleiben |

### Observable Truths: Plan must_haves

| Plan | Truths | Status | Anmerkungen |
|------|--------|--------|-------------|
| 02-01 | 9 | 9 ✓ | **#6 jetzt VERIFIED** (vorher FAILED): test_corrupt_pattern_keeps_previous_matches[syntax-error, repeat-overflow, deep-nesting] grün auf HEAD, rot auf 07bb291 für repeat-overflow und deep-nesting. Der Test stellt A vor B in die Listener-Schleife, übt also genau den früheren Abbruchpfad aus |
| 02-02 | 13 | 12 ✓, 1 ⚠ insufficient_spec | #13 `verification: backstop` (Nebenläufigkeit), unverändert → human |
| 02-03 | 10 | 10 ✓ | Keine Änderung an preview.py/config_flow.py |
| 02-04 | 13 | 13 ✓ | filter.py-Änderung betrifft nur den Fehlerpfad; Fenster-/Dauer-Tests grün |
| 02-05 | 8 | 8 ✓ | test_reconfigure.py komplett grün |
| 02-06 | 11 | 11 ✓ | Unverändert |
| 02-07 | 8 | 8 ✓ | Unverändert |
| 02-08 | 8 | 8 ✓ | Gate erneut ausgeführt (s. Spot-Checks) |
| 02-09 (Gap Closure) | 6 (1 dedupliziert mit 02-01 #6) | 5 ✓ neu | siehe Tabelle unten |

**02-09 Truths im Einzelnen**

| # | Truth (gekürzt) | Status | Evidenz |
|---|-----------------|--------|---------|
| 1 | Unkompilierbares gespeichertes Muster (Syntax, Overflow, Rekursion): nur dieser Kalender behält alte Treffer, eine WARNING, Geschwister werden aktualisiert | ✓ VERIFIED | = 02-01 #6, siehe oben; calendar.py:176-178 behält `self._spec`, wenn `_build_spec` None liefert |
| 2 | Plattform-Setup mit solchem Subentry bricht nicht: Entry LOADED, Entity existiert ohne Events, genau eine WARNING, andere Kalender zeigen Treffer | ✓ VERIFIED | calendar.py:111 → `_build_spec`; `_async_refilter` setzt leeren Index bei `_spec is None` (calendar.py:142-146); test_invalid_stored_pattern_does_not_break_platform_setup[3 ids] grün, rot auf 07bb291 |
| 3 | `a{99999999999}` / `a{1,99999999999}` in Include, Exclude oder Channel-Regex: Formular bleibt offen mit invalid_regex, Muster- und Fehler-Platzhalter, nichts gespeichert | ✓ VERIFIED | test_invalid_pattern_line_keeps_form_open[*-repeat-overflow] grün, rot auf 550d1a2 |
| 4 | `first_invalid_pattern` wirft nie für eine von re.compile abgelehnte Zeile | ✓ VERIFIED | filter.py:194-198; eigener Probe: 12 Muster × 2 Case-Flags, keine Exception (u. a. `x{4294967295,}`, `(?i)a{4294967295}`, `\N{NOT A NAME}`) |
| 5 | Edit eines Kalenders mit gespeichertem Overflow-Muster zeigt invalid_regex; gültiges Muster repariert in-place ohne Download/Reload | ✓ VERIFIED | test_edit_repairs_overflowing_stored_pattern grün (prüft `call_count` und `runtime_data is runtime`), rot auf 550d1a2 |
| 6 | `a{4294967294}` wird weiter akzeptiert | ✓ VERIFIED | test_first_invalid_pattern_accepts_valid_input; eigener Probe → None |

**Score:** 89/90 Truths verifiziert (5/5 Roadmap-SC, 84/85 Plan-Truths nach Deduplizierung). 0 FAILED, 1 insufficient_spec (Backstop, human), 0 present-but-behavior-unverified.

### Advisory (New Scope, Unevidenced)

| # | Finding | Kategorie | Warum Advisory |
|---|---------|-----------|----------------|
| 1 | IN-07: `DEEP_NESTING` hängt vom Default-Rekursionslimit ab und ist doppelt definiert | other | Test-Robustheit, kein Produktdefekt; kein roter Lauf im aktuellen Harness |

### Required Artifacts

`verify.artifacts` über alle 9 Pläne: **36/36 bestanden** (02-09: 6/6).

| Artefakt | Status | Details |
|----------|--------|---------|
| xmltv/filter.py | ✓ VERIFIED | `PATTERN_ERRORS` (Z. 55), `first_invalid_pattern` fängt das Tupel (Z. 196); `compile_patterns` dokumentiert, dass es die Fehler wirft |
| calendar.py | ✓ VERIFIED | `except PATTERN_ERRORS` in `_build_spec` (Z. 59), genutzt in `__init__` (Z. 111) und `async_apply_subentry` (Z. 176) |
| tests/test_reconfigure.py | ✓ VERIFIED | Listener-Parametrisierung + Edit-Reparatur |
| tests/test_calendar.py | ✓ VERIFIED | Plattform-Setup-Regression |
| tests/test_subentry_flow.py | ✓ VERIFIED | 3 Repeat-Overflow-ids |
| tests/xmltv/test_filter.py | ✓ VERIFIED | reine Validierung inkl. Grenze `a{4294967294}` |
| übrige Phase-2-Artefakte | ✓ VERIFIED | unverändert seit Erstverifikation, Checks erneut grün |

### Key Link Verification

`verify.key-links` über alle 9 Pläne: **19/19 verifiziert** (02-09: 3/3).

| Von | Nach | Via | Status |
|-----|------|-----|--------|
| calendar.py | xmltv/filter.py | `_build_spec` fängt `PATTERN_ERRORS` aus `FilterSpec.from_mapping` in `__init__` und im Listener | ✓ WIRED |
| config_flow.py | xmltv/filter.py | `async_step_basic` validiert alle drei Musterfelder mit `first_invalid_pattern` (Z. 371-377), bevor `advanced`/`preview` erreichbar sind | ✓ WIRED |
| filter.py | filter.py | Flow und Entity fangen dasselbe Tupel | ✓ WIRED |

Zusätzlich geprüft: Der einzige weitere ungeschützte Kompilierpfad, `build_preview` (preview.py:67), ist nur über einen erfolgreichen Basic-Submit erreichbar (`async_step_back` zeigt nur das Formular). Laut 02-REVIEW.md-Fuzzing kompiliert kein Muster unter einem Case-Flag und scheitert unter dem anderen, daher bleibt die Validierung mit dem pending-Flag auch nach einer Flag-Änderung im Advanced-Schritt gültig.

### Data-Flow Trace (Level 4)

| Artefakt | Daten | Quelle | Echte Daten | Status |
|----------|-------|--------|-------------|--------|
| Kalender-Events | `self._index` | `coordinator.data` → `FilterSpec.apply` im Executor; bei `_spec is None` leerer Index | Ja | ✓ FLOWING |
| Vorschau | `count`, `matches` | `entry.runtime_data.coordinator.data` → `build_preview` | Ja | ✓ FLOWING |
| Edit-Formular | `pending` | `with_defaults(subentry.data)` | Ja | ✓ FLOWING |

### Behavioral Spot-Checks

| Verhalten | Befehl | Ergebnis | Status |
|-----------|--------|----------|--------|
| 02-09-Regressionstests auf HEAD | `uv run pytest <6 benannte Tests>` | 20 passed | ✓ PASS |
| RED vor Flow-Fix | dieselben Tests auf `git archive 550d1a2` | 6 failed (3× Form, 2× Validierung, Edit-Reparatur) | ✓ (erwartet rot) |
| RED vor Entity-Fix | Listener-/Setup-Tests auf `git archive 07bb291` | 4 failed (repeat-overflow, deep-nesting je Listener und Setup) | ✓ (erwartet rot) |
| Volle Suite (einmal) | `uv run pytest tests -q` | 517 passed, 1 skipped, 42 s | ✓ PASS |
| Lint/Format | `ruff check .` / `ruff format --check .` | sauber, 48 Dateien | ✓ PASS |
| Validierung, eigener Probe | `first_invalid_pattern` über 12 Muster × 2 Flags | keine Exception; Overflow → "the repetition number is too large"; `a{4294967294}` → None | ✓ PASS |
| Gespeicherte Daten, eigener Probe | `FilterSpec.from_mapping` für include/exclude/channel_regex × Overflow/Rekursion/Syntax | wirft jeweils nur ein Element aus `PATTERN_ERRORS` | ✓ PASS |
| Fixed-Count-Repeat | `first_invalid_pattern(r"(\d{2}:)+")` | "nested repetition" | ⚠ WARN (WR-03, unverändert) |

### Probe Execution

Step 7c: keine Probes deklariert, kein `scripts/*/tests/probe-*.sh` im Repo. Nicht anwendbar.

### Requirements Coverage

| Requirement | Source Plan | Beschreibung | Status | Evidenz |
|-------------|-------------|--------------|--------|---------|
| FLT-05 | 02-02, 02-07 | Getrennte Feldauswahl für Include/Exclude | ✓ SATISFIED | SC1 |
| FLT-06 | 02-02, 02-07, 02-08 | Case-Toggle, Unicode-normalisierungssichere Umlaute | ✓ SATISFIED | SC1 |
| FLT-08 | 02-04, 02-07 | Min/Max-Dauer | ✓ SATISFIED | SC2 |
| FLT-09 | 02-04, 02-07 | Zeitfenster über Mitternacht, Wochentage | ✓ SATISFIED | SC2 |
| FLT-10 | 02-03, 02-07, 02-08 | Vorschau mit Anzahl und nächsten ~10 Treffern | ✓ SATISFIED (Darstellung: human) | SC3 |
| FLT-11 | 02-01, 02-05, 02-08, 02-09 | Alle Filter bearbeiten ohne Re-Download/Re-Parse | ✓ SATISFIED (vorher: mit Gap) | SC5 + 02-09 Truths 1, 2, 5 |
| EVT-03 | 02-06, 02-07 | Titel-Template, unbekannte Platzhalter abgelehnt | ✓ SATISFIED | SC4 |
| EVT-04 | 02-06, 02-07 | Default-Beschreibung plus Beschreibungs-Template | ✓ SATISFIED | SC4 |
| FLT-07 (Phase 1, von 02-09 mitbeansprucht) | 02-09 | Ungültige Regex im Flow mit Fehler abgelehnt | ✓ SATISFIED | 02-09 Truths 3, 4; Overflow-Muster führen nicht mehr zu "Unknown error" |

Alle 8 Phase-IDs werden von mindestens einem Plan beansprucht. REQUIREMENTS.md ordnet Phase 2 keine weiteren IDs zu, es gibt keine verwaisten Requirements. Hinweis: Die Traceability-Tabelle in REQUIREMENTS.md steht für die acht IDs noch auf "Gaps Found"; das aktualisiert der Orchestrator nach Abschluss.

### Anti-Patterns Found

| Datei | Zeile | Muster | Schwere | Auswirkung |
|-------|-------|--------|---------|------------|
| xmltv/filter.py | 182-185 (alt) | nur `except re.error` (CR-01) | ✓ behoben | jetzt `except PATTERN_ERRORS as err` (Z. 196) |
| calendar.py | 109-113 (alt) | nur `except re.error` (CR-01) | ✓ behoben | jetzt `except PATTERN_ERRORS` (Z. 59) |
| config_flow.py | 405 | `pending \| (user_input or {})` im Fehlerpfad (WR-01) | ⚠️ Warning | Geleertes Feld kehrt nach Validierungsfehler als Vorschlag zurück; der neue Reparaturpfad (Fehler → korrigieren → absenden) macht das wahrscheinlicher |
| xmltv/filter.py | 149-151 | `unbounded = high > 1` (WR-03) | ⚠️ Warning | `(\d{2}:)+` abgelehnt; Phase-1-Kalender mit solchem Muster lässt sich im Edit nicht unverändert speichern. War in der Erstverifikation bereits Warning, durch 02-09 nicht verändert |
| translations/en.json | 138-140 | kein `reconfigure_successful`-Text (WR-02) | ⚠️ Warning | Erfolgsdialog nach Edit ohne Text; Speichern funktioniert. Im UAT Schritt 5 prüfen |
| config_flow.py | 316, 376-377 | gemeinsamer `pattern`/`error`-Platzhalter (WR-04) | ℹ️ Info | Zweites ungültiges Feld zeigt die Meldung des ersten |
| tests/test_calendar.py, tests/test_reconfigure.py | 29, 36 | `DEEP_NESTING` abhängig vom Rekursionslimit (IN-07) | 📋 Advisory | siehe Advisory-Tabelle |

Keine TBD/FIXME/XXX/TODO/HACK-Marker in den durch 02-09 geänderten Dateien oder in `custom_components/`.

### Human Verification Required

1. **ha-dev UAT-Durchgang (9 Schritte aus 02-08-SUMMARY.md)**
   - **Test:** Formular, Advanced-Schritt, Vorschau, Back, Edit, Abwählen, verschachtelte Wiederholung, leere Vorschau, Logs. Zusätzlich `a{99999999999}` im Include-Feld eingeben.
   - **Erwartet:** wie in 02-08-SUMMARY.md beschrieben; das Overflow-Muster zeigt `invalid_regex` statt "Unknown error". Bei Schritt 5 notieren, was der Edit-Erfolgsdialog zeigt (WR-02).
   - **Warum human:** kein Frontend in phcc.
2. **Markdown-Rendering der Vorschau (02-03 D4)**
   - **Test:** Feed mit Sonderzeichen in Kanalnamen/Titeln.
   - **Erwartet:** Zeichen erscheinen wörtlich (Ausnahme `~~`, IN-04).
   - **Warum human:** ha-markdown wird von keinem Test gerendert.
3. **Backstop-Truth Nebenläufigkeit (02-02)**
   - **Test:** Struktur akzeptieren oder Nebenläufigkeitstest anfordern.
   - **Warum human:** `verification: backstop`, nur Präsenz-Evidenz.
4. **Drei Judgment-Prohibitions (02-02 a/b, 02-03 c)**
   - **Test:** LLM-Urteil (nicht autoritativ: alle halten) bestätigen.
   - **Warum human:** ADR-550 D4.

### Gaps Summary

Keine offenen Gaps. Der einzige Gap der Erstverifikation (CR-01, 02-01 Truth 6) ist im Code und in den Tests geschlossen:

- **Flow:** `first_invalid_pattern` wandelt `re.error`, `OverflowError` und `RecursionError` in `InvalidPattern` um. Overflow-Muster zeigen `invalid_regex` in allen drei Feldern.
- **Entity:** `_build_spec` fängt dasselbe Tupel. Ein gespeichertes unkompilierbares Muster leert beim Setup nur den eigenen Kalender und behält im Listener die vorherigen Treffer. Die Geschwister werden weiter aktualisiert.
- **Nachweis:** Die Tests sind auf den Commits vor dem jeweiligen Fix rot und auf HEAD grün.

Nicht blockierend, aber für "retune any calendar instantly" relevant und weiterhin offen: WR-01, WR-02, WR-03 (Warnungen) sowie WR-04 und IN-01..IN-07 (Info/Advisory). Sie stehen in 02-REVIEW-DISPOSITION.md auf `open`. Empfehlung: vor `/gsd-ship` mindestens WR-02 (eine Übersetzungszeile) und WR-01 beheben oder bewusst auf `deferred` setzen.

---

_Verifiziert: 2026-10-15T15:29:02Z_
_Verifier: Claude (gsd-verifier)_
