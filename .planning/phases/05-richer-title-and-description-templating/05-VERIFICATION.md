---
phase: 05-richer-title-and-description-templating
verified: 2026-10-24T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
covered_files:
  - ".planning/phases/05-richer-title-and-description-templating/05-01-PLAN.md"
  - ".planning/phases/05-richer-title-and-description-templating/05-01-SUMMARY.md"
  - ".planning/phases/05-richer-title-and-description-templating/05-02-PLAN.md"
  - ".planning/phases/05-richer-title-and-description-templating/05-02-SUMMARY.md"
  - ".planning/phases/05-richer-title-and-description-templating/05-03-PLAN.md"
  - ".planning/phases/05-richer-title-and-description-templating/05-03-SUMMARY.md"
  - ".planning/phases/05-richer-title-and-description-templating/05-04-PLAN.md"
  - ".planning/phases/05-richer-title-and-description-templating/05-04-SUMMARY.md"
  - ".planning/phases/05-richer-title-and-description-templating/05-05-PLAN.md"
  - ".planning/phases/05-richer-title-and-description-templating/05-05-SUMMARY.md"
  - "README.md"
  - "custom_components/xmltv_calendar/calendar.py"
  - "custom_components/xmltv_calendar/config_flow.py"
  - "custom_components/xmltv_calendar/matcher.py"
  - "custom_components/xmltv_calendar/translations/de.json"
  - "custom_components/xmltv_calendar/translations/en.json"
  - "custom_components/xmltv_calendar/xmltv/preview.py"
  - "custom_components/xmltv_calendar/xmltv/render.py"
  - "custom_components/xmltv_calendar/xmltv/settings.py"
  - "custom_components/xmltv_calendar/xmltv/template_engine.py"
  - "tests/test_readme_recipes.py"
  - "tests/test_template_runtime.py"
  - "tests/test_templates.py"
  - "tests/xmltv/test_template_engine.py"
  - "tests/xmltv/test_template_filters.py"
covered_digest: "v3:sha256:f7b9c3d5632d7849a83e14da6fee3dd28c790778b99dcfa0bafc284c8b1c210b"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Deutsche UI auf ha-dev durchgehen: Kalender mit dem Formel-1-Rezept als Titelvorlage anlegen, Vorschauzeile und Kalenderansicht pruefen; Beschreibungsvorlage 'Starts {{ start | time('%H:%M') }} on {{ channel }}' setzen und die lokale Uhrzeit pruefen; Home Assistant neu starten und bestaetigen, dass bestehende Kalender mit dem alten Standardtitel keine Template-Warnung loggen; eine eigene Vorlage in alter Syntax ueber Entwicklerwerkzeuge oder die Storage-Datei ablegen und genau eine Warnung mit Kalendername pruefen."
    expected: "Vorschau und Kalender zeigen den bereinigten Titel, die lokale Startzeit stimmt, kein Warnung fuer den alten Standardtitel, genau eine Warnung fuer die eigene Alt-Vorlage mit Standardtitel im Kalender."
    why_human: "Echte UI, Neustart und Logausgabe lassen sich nicht ohne laufende Home-Assistant-Instanz pruefen (in 05-05-SUMMARY als ausstehend vermerkt)."
  - test: "Deutsche Fehlertexte im Formular lesen: Schleife, unbekannter Filter, Tippfehler (titel), alte Syntax, Laufzeitfehler auf der Beispielsendung."
    expected: "Texte lesen sich natuerlich, {template_error}, {variables} und {default_title} werden korrekt eingesetzt."
    why_human: "Textqualitaet und Platzhalter-Rendering im echten Formular (in 05-02-SUMMARY als not_run vermerkt). Schluessel und Platzhalternamen sind per Test abgesichert."
  - test: "hassfest und HACS-Action nach dem Push in CI pruefen."
    expected: "Beide Pruefungen gruen (translations/strings, manifest ohne neue requirements)."
    why_human: "Laeuft nur in der GitHub-CI nach dem Push, lokal nicht ausfuehrbar."
  - test: "Entscheidung: Umgehung der Regex-Validierung ueber Filter-Namen als Text (siehe Warnung unten) schliessen oder als akzeptiertes Restrisiko dokumentieren."
    expected: "Entweder wird die Validierung auf map/select/reject mit den Filternamen regex_replace und regex_search ausgedehnt (oder diese Aufrufe werden abgelehnt), oder das Restrisiko wird neben dem exponentiellen set/Tilde-Wachstum in ROADMAP und README genannt."
    why_human: "Es ist eine Risikoabwaegung des Entwicklers: nur ein Administrator kann so eine Vorlage schreiben, das Problem ist aber im Plan nicht als Restrisiko genannt."
---

# Phase 5: Reichere Titel- und Beschreibungsvorlagen, Verifikationsbericht

**Phasenziel:** Der Nutzer kann Titel und Beschreibungen von Kalenderereignissen mit sandboxed Jinja-Vorlagen gestalten (Bedingungen, Textfilter, lokale Start- und Endzeit) statt mit den einfachen `str.format`-Platzhaltern, mit Fehlern im Formular, einer Vorschau auf echten Sendungen und dokumentierten Rezepten; gespeicherte Vorlagen mit einfachen Klammern fallen mit einer Warnung auf den Standard zurueck (harter Bruch, keine Migration).
**Verifiziert:** 2026-10-24
**Status:** human_needed
**Re-Verifikation:** Nein, Erstverifikation

## Zielerreichung

### Beobachtbare Wahrheiten (ROADMAP-Erfolgskriterien)

| # | Wahrheit | Status | Beleg |
|---|----------|--------|-------|
| 1 | Titelvorlage kann das Praefix "Formel 1" entfernen, die erste Beschreibungszeile als Titelteil nutzen, einen Untertitel nur bei Vorhandensein zeigen; Vorschau und `calendar.get_events` zeigen das Ergebnis; Start und Ende erscheinen in der HA-Zeitzone | VERIFIED | Eigener Lauf gegen `render`: `regex_replace('^Formel 1: ', '')` ergibt "Grosser Preis", `first_line` ergibt "Erste Zeile", `if subtitle` haengt " - Quali" an, `start\|time` ergibt `20:15-21:45` fuer 19:15 UTC unter Europe/Berlin. Verdrahtung: `calendar.py` loest `dt_util.get_default_time_zone()` einmal auf (Zeilen 61-62, 172, 185) und reicht `tz` an `to_event_fields`; `matcher.describe_match` (Zeile 375-376) und `preview.py` (Zeile 81-88) rendern ueber dieselben `EventTemplates`. Tests: `test_formula_one_prefix_stripped_end_to_end`, `test_start_variable_is_local_time_everywhere`, `test_formula_one_recipe_end_to_end`, `test_local_start_time_recipe_end_to_end` laufen gruen. |
| 2 | Sandbox: Schleifen, Makros, Includes, Imports, Methodenaufrufe und teure Operatoren werden abgelehnt, regulaere Ausdruecke validiert, eine Vorlage, die bei der Beispielsendung oder zur Laufzeit scheitert, bricht den Kalender nie (Ersatztitel oder Standardbeschreibung, eine Warnung pro Kalender) | VERIFIED (mit Warnung) | Eigener Probelauf: `for`, `macro`, `include`, `import`, `title.upper()`, `*`, `**`, `lipsum()`, `self`, Block-`set` ergeben `unsupported_syntax`; `(a+)+` und `(` ergeben `invalid_template`. `{{ 1/0 }}` zur Laufzeit liefert den Programmtitel und genau eine Warnung ("Calendar Cal3 ... ZeroDivisionError"), der zweite Aufruf loggt nicht erneut. `__class__`, `__mro__` und Methoden-Attribute rendern leer (ImmutableSandbox). Umgehung der Regex-Pruefung ueber `map('regex_replace', ...)`, siehe Warnung unten. |
| 3 | Das erweiterte Formular zeigt uebersetzte Fehler (EN und DE) fuer unbekannte Variablen oder Filter, nicht unterstuetzte Syntax, ungueltige Syntax, die abgeloeste Einfachklammer-Syntax und Fehler bei der Beispielsendung | VERIFIED (UI-Wortlaut menschlich offen) | `en.json` und `de.json` enthalten alle sechs Schluessel (`invalid_template`, `unknown_placeholder`, `unsupported_syntax`, `unknown_filter`, `legacy_placeholder`, `template_runtime_error`) mit identischen Platzhalternamen; `tests/test_translations.py` iteriert `TEMPLATE_ERROR_REASONS`. Die Flow-Tests `test_every_compile_time_reason_reaches_the_form`, `test_runtime_failure_on_a_sample_programme_is_rejected` laufen gruen. Echter Formularwortlaut siehe Human-Verification. |
| 4 | Alter Standard `{channel}: {title}` laeuft ohne Warnung weiter; eigene Alt-Vorlagen fallen mit einer Warnung auf `{{ channel }}: {{ title }}` zurueck; das Formular verweigert das Speichern von Alt-Syntax | VERIFIED | Eigener Lauf: `{channel}: {title}` rendert "Sky: Formel 1: ..." ohne Log (normalisiert in `settings.with_defaults`, Zeile 139-140); `{title} ({channel})` loggt "stored title template is not usable (legacy_placeholder), using the default" und rendert den Standard. Formular: `legacy_placeholder` im Probelauf, Test `test_stored_legacy_template_cannot_be_saved_again` gruen. Storage-`VERSION` unveraendert (keine Migration). |
| 5 | Bearbeiten einer Vorlage aendert nie Event-UIDs oder kuendigt Treffer erneut an; README dokumentiert Variablen, Filter, Grenzen, Upgrade und vier Rezepte, die Tests rendern | VERIFIED | `event_uid` hasht den rohen Programmtitel (`render.py`, `event_uid`); `EventTemplates`-Gleichheit vergleicht nur Quelltexte. Tests `test_template_edit_does_not_reannounce_matches`, `test_noop_data_change_sends_no_template_signal` gruen. README hat die Abschnitte Variables, Syntax, Whitespace, Filters, Time directives, Limits, Checking templates, Upgrading, Recipes (vier Rezepte); `test_recipe_is_documented_verbatim`, `test_recipe_renders_as_documented`, `test_every_registered_filter_is_documented`, `test_every_variable_is_documented`, `test_limits_are_documented` gruen. |

**Score:** 5/5 Wahrheiten verifiziert (0 present, behavior-unverified)

### Plan-spezifische Wahrheiten (Stichproben gegen den Code)

| Wahrheit | Status | Beleg |
|----------|--------|-------|
| Reiner Engine-Modul `template_engine.py` mit `ImmutableSandboxedEnvironment`, Allow-Liste von 28 Knotenklassen, beschnittene Filter, leere Globals | VERIFIED | Datei gelesen (436 Zeilen), `_build_env`, `ALLOWED_NODES`, `_check_tree` vor `ENV.from_string(tree)`. |
| D-06-Filtersatz vorhanden (`regex_replace`, `regex_search`, `strip_prefix`, `strip_suffix`, `remove`, `split`, `lines`, `first_line`, `time`) plus `replace` mit Groessengrenze | VERIFIED | `CUSTOM_FILTERS` in `template_engine.py`; Grenzen `MAX_FILTER_CHAIN=16`, `MAX_LITERAL_LENGTH=300`, `MAX_RESULT_CHARS=50000`. |
| `validate_template` rendert Voll- und Leerprobe | VERIFIED | `render.py`, `SAMPLE_FULL`/`SAMPLE_SPARSE`, Fehler werden zu `template_runtime_error` (200 Zeichen). |
| REQUIREMENTS.md und PROJECT.md nennen die umgekehrte Entscheidung; Stack-Notizen neu geschrieben | VERIFIED | REQUIREMENTS.md Zeilen 42, 43, 48 und Traceability (131, 132, 137) "Complete"; `.claude/CLAUDE.md` und `STACK.md` nennen `ImmutableSandboxedEnvironment`; FEATURES, ARCHITECTURE, SUMMARY tragen Hinweise "Superseded in Phase 5". |

### Erforderliche Artefakte

| Artefakt | Erwartet | Status | Details |
|----------|----------|--------|---------|
| `custom_components/xmltv_calendar/xmltv/template_engine.py` | Sandbox-Engine | VERIFIED | Substanziell, von `render.py` importiert und genutzt |
| `custom_components/xmltv_calendar/xmltv/render.py` | Fassade, `EventTemplates`, `validate_template` | VERIFIED | Von Flow, Matcher, Kalender und Vorschau genutzt |
| `custom_components/xmltv_calendar/xmltv/settings.py` | Neuer Standard, Legacy-Normalisierung | VERIFIED | `LEGACY_DEFAULT_TITLE_TEMPLATE` in `with_defaults` |
| `translations/en.json`, `translations/de.json` | Fehlertexte | VERIFIED | Alle sechs Schluessel in beiden Sprachen |
| `README.md` Abschnitt Templates | Doku mit vier Rezepten | VERIFIED | Gelesen, durch Tests abgesichert |
| `tests/test_readme_recipes.py`, `tests/test_template_runtime.py`, `tests/test_templates.py`, `tests/xmltv/test_template_engine.py`, `tests/xmltv/test_template_filters.py` | Tests | VERIFIED | Vorhanden, substanziell, gruen |

### Schluesselverbindungen

| Von | Nach | Via | Status |
|-----|------|-----|--------|
| `render.py` | `template_engine.py` | `compile_template`, `TemplateError` | WIRED |
| `config_flow.py` | `render.validate_template` | `_advanced_errors` | WIRED |
| `matcher.py` | `EventTemplates.from_mapping(subentry.data, subentry.title)` | Zeilen 130, 418 | WIRED |
| `calendar.py` | `render.to_event_fields(..., tz=)` | `_to_event`, `build_events`, `async_get_events` | WIRED |
| `matcher.describe_match` | `template_values`/`render_title` mit lokaler Zone | Zeilen 375-380, speist Sensor und Neu-Treffer-Event | WIRED |
| `preview.py` | `EventTemplates.from_mapping` + `to_event_fields(tz=)` | Zeilen 81-88 | WIRED |
| `tests/test_readme_recipes.py` | `README.md` und `ENV.filters`/`VARIABLE_ORDER` | Vollstaendigkeitstests | WIRED |

### Datenfluss (Level 4)

Die Werte fliessen aus `Programme`/`Channel` (Feed-Parser) ueber `template_values` in den Render; keine statischen Rueckgaben oder Hohlparameter gefunden. Status: FLOWING.

### Verhaltens-Stichproben

| Verhalten | Befehl | Ergebnis | Status |
|-----------|--------|----------|--------|
| Gesamte Testsuite (einmal) | `uv run --offline pytest -q` | 1268 passed, 1 skipped | PASS |
| Lint | `ruff check .` und `ruff format --check .` | alles gruen, 80 Dateien formatiert | PASS |
| Probelauf Sandbox-Ablehnungen und Rezepte | eigenes Skript gegen `render` | wie in der Tabelle oben | PASS |
| `{{ title.__class__ }}` | Render | leerer Text | PASS |
| Regex-Umgehung ueber `map('regex_replace', '(a+)+$', 'x')` | `validate_template` und Render | wird akzeptiert; Render mit 26 `a` plus `!` dauert 3,2 s (exponentiell) | WARNUNG |

### Probe-Ausfuehrung

SKIPPED: die Phase deklariert keine Probe-Skripte (`probe-*.sh`).

### Anforderungsabdeckung

| Anforderung | Quellplaene | Beschreibung | Status | Beleg |
|-------------|-------------|--------------|--------|-------|
| EVT-03 | 05-01, 05-02, 05-04, 05-05 | Titelvorlage als sandboxed Jinja, unbekannte Variablen/Filter/Syntax und Alt-Syntax im Flow abgelehnt | SATISFIED | Engine, Flow-Validierung, Uebersetzungen, Tests |
| EVT-04 | 05-01, 05-02, 05-04, 05-05 | Standardbeschreibung bleibt, Beschreibungsvorlage gleicher Art | SATISFIED | `render_description`, `default_description`, Ersatz bei Fehlern |
| EVT-10 | 05-01, 05-03, 05-04, 05-05 | Bedingungen, Textfilter, lokale Start/Ende | SATISFIED | Filtersatz, Zeitzonen-Durchreichung, README-Rezepte |

Alle drei Phasen-IDs stehen in den PLAN-Frontmattern und in REQUIREMENTS.md (Zeilen 42, 43, 48; Traceability 131, 132, 137 "Phase 5, Complete"). Verwaiste Anforderungen: keine.

### Gefundene Anti-Patterns

| Datei | Zeile | Muster | Schwere | Auswirkung |
|-------|-------|--------|---------|------------|
| `custom_components/xmltv_calendar/xmltv/template_engine.py` | `_check_filter` | Regex-Argumente werden nur bei direktem Filteraufruf geprueft, nicht bei `map('regex_replace', ...)`, `select`/`reject` mit Filter- oder Testnamen als Text | Warnung | Eine vom Administrator geschriebene Vorlage kann die Verschachtelungs-Pruefung umgehen und mit einem passenden Feed-Titel eine Katastrophen-Backtracking-Laufzeit erzeugen (Probe: 3,2 s bei 26 Zeichen). Nur Administratoren koennen Vorlagen schreiben, im Plan nicht als Restrisiko genannt. |

Schuldenmarker (`TBD`, `FIXME`, `XXX`): keine in `custom_components`, `README.md` oder den Rezept-Tests. Keine Stubs.

### Menschliche Verifikation erforderlich

Die ersten drei Punkte sind in den Plan-SUMMARYs als ausstehend vermerkt und kein Fehler.

1. **Deutsche UI auf ha-dev durchgehen**
   **Test:** Formel-1-Rezept als Titelvorlage, lokales Startzeit-Rezept als Beschreibung, Neustart, Alt-Vorlage per Storage.
   **Erwartet:** Bereinigter Titel in Vorschau und Kalender, korrekte Uhrzeit, keine Warnung fuer den alten Standard, genau eine Warnung fuer eine eigene Alt-Vorlage.
   **Warum menschlich:** Echte UI, Neustart und Log.
2. **Deutsche Fehlertexte im Formular lesen**
   **Test:** Schleife, unbekannter Filter, Tippfehler, alte Syntax, Laufzeitfehler eingeben.
   **Erwartet:** Natuerliche Texte, Platzhalter korrekt eingesetzt.
   **Warum menschlich:** Wortlaut und Formular-Rendering.
3. **hassfest und HACS nach dem Push**
   **Test:** CI-Lauf ansehen.
   **Erwartet:** Beide gruen.
   **Warum menschlich:** Laeuft nur in der CI.
4. **Entscheidung zur Regex-Umgehung ueber `map`**
   **Test:** Entscheiden, ob die Validierung auf `map`, `select` und `reject` mit Filternamen als Text ausgedehnt wird (oder diese Aufrufe abgelehnt werden) oder ob das Restrisiko dokumentiert wird.
   **Erwartet:** Eine der beiden Loesungen ist umgesetzt oder festgehalten.
   **Warum menschlich:** Risikoabwaegung, kein funktionaler Fehler des Phasenziels.

### Zusammenfassung der Luecken

Keine blockierenden Luecken. Alle fuenf ROADMAP-Erfolgskriterien sind im Code belegt, die Testsuite (1268 bestanden) und Ruff sind gruen, alle drei Anforderungs-IDs sind abgedeckt. Offen sind die in den SUMMARYs vermerkten menschlichen Pruefungen und eine Warnung zur Regex-Umgehung ueber `map`, ueber die der Entwickler entscheiden sollte.

---

_Verifiziert: 2026-10-24_
_Verifier: Claude (gsd-verifier)_
