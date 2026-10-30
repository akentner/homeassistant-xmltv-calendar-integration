---
phase: 05-richer-title-and-description-templating
verified: 2026-10-30T00:00:00Z
status: passed
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
covered_digest: "v4:sha256:51ef4536014821e81203531db93f449796f0b7febad4bacb06877a95481ce1d7"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/5
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 5: Reichere Titel- und Beschreibungsvorlagen, Verifikationsbericht

**Phasenziel:** Der Nutzer kann Titel und Beschreibungen von Kalenderereignissen mit sandboxed Jinja-Vorlagen gestalten (Bedingungen, Textfilter, lokale Start- und Endzeit) statt mit den einfachen `str.format`-Platzhaltern, mit Fehlern im Formular, einer Vorschau auf echten Sendungen und dokumentierten Rezepten; gespeicherte Vorlagen mit einfachen Klammern fallen mit einer Warnung auf den Standard zurueck (harter Bruch, keine Migration).
**Verifiziert:** 2026-10-30
**Status:** passed
**Re-Verifikation:** Ja, nach Abschluss der menschlichen Pruefung (05-UAT.md, 4 von 4 bestanden). Die fruehere Fassung dieses Berichts (2026-10-24) hatte `human_needed`; die damaligen vier Punkte sind jetzt alle erledigt.

## Zielerreichung

### Beobachtbare Wahrheiten (ROADMAP-Erfolgskriterien)

| # | Wahrheit | Status | Beleg |
|---|----------|--------|-------|
| 1 | Titelvorlage kann das Praefix "Formel 1" entfernen, die erste Beschreibungszeile nutzen, einen Untertitel nur bei Vorhandensein zeigen; Vorschau und `calendar.get_events` zeigen das Ergebnis; Start und Ende in der HA-Zeitzone | VERIFIED | Eigener Probelauf (Skript im Scratchpad): `{{ title \| regex_replace('^Formel 1: ', '') }}{% if subtitle %} - {{ subtitle }}{% endif %}` ergibt "Grosser Preis - Quali"; `{{ description \| first_line }}` ergibt "Erste Zeile"; `Starts {{ start \| time('%H:%M') }} on {{ channel }}` ergibt "Starts 20:15 on Sky" fuer 19:15 UTC unter Europe/Berlin. Verdrahtung: `calendar.py` loest `dt_util.get_default_time_zone()` auf (Zeilen 61-62, 172, 185) und reicht `tz` an `to_event_fields`; `matcher.describe_match` (Zeilen 375-380) und `preview.py` (Zeilen 80-88) nutzen dieselben `EventTemplates`. Tests dazu laufen gruen. |
| 2 | Sandbox: Schleifen, Makros, Includes, Imports, Methodenaufrufe, teure Operatoren abgelehnt; Regex validiert; Vorlage, die bei Beispielsendung oder Laufzeit scheitert, bricht den Kalender nie (Ersatz, eine Warnung pro Kalender) | VERIFIED | Eigener Probelauf gegen `validate_template`: `for`, `macro`, `include`, `import`, `title.upper()`, `*`, `**`, `lipsum()` ergeben `unsupported_syntax`; `(a+)+` und `(` ergeben `invalid_template`; `{{ 1/0 }}` wird als `template_runtime_error` im Formular abgelehnt. Gespeichert und zur Laufzeit: `{{ 1/0 }}` rendert den Programmtitel als Ersatz mit einer Warnung ("Calendar RTCal: title template failed to render (ZeroDivisionError), using the fallback"). Bekannte, akzeptierte Grenze: Regex-Pruefung gilt nur fuer direkte `regex_replace`/`regex_search`-Aufrufe (T-05-03, AR-05-03, in README "Limits" dokumentiert). |
| 3 | Formular zeigt uebersetzte Fehler (EN und DE) fuer unbekannte Variablen/Filter, nicht unterstuetzte und ungueltige Syntax, abgeloeste Einfachklammer-Syntax und Fehler bei der Beispielsendung | VERIFIED | Probelauf liefert die Gruende `unknown_placeholder`, `unknown_filter`, `unsupported_syntax`, `invalid_template`, `legacy_placeholder`, `template_runtime_error`; `config_flow.py:547` ruft `validate_template`; `en.json` und `de.json` enthalten die Schluessel, `tests/test_translations.py` iteriert `TEMPLATE_ERROR_REASONS`. Wortlaut im echten deutschen Formular per UAT-Test 2 bestanden. |
| 4 | Alter Standard `{channel}: {title}` laeuft ohne Warnung weiter; eigene Alt-Vorlagen fallen mit Warnung auf `{{ channel }}: {{ title }}` zurueck; Formular verweigert Alt-Syntax | VERIFIED | Probelauf: `{channel}: {title}` rendert "Sky: Formel 1: Grosser Preis" ohne Log (`settings.with_defaults`, Zeilen 138-140); `{title} ({channel})` loggt "Calendar LegacyCal: stored title template is not usable (legacy_placeholder), using the default" und rendert den Standardtitel; Formular lehnt `{title} ({channel})` mit `legacy_placeholder` ab. Keine Storage-Migration. Neustart und Log im echten HA per UAT-Test 1 bestanden. |
| 5 | Bearbeiten einer Vorlage aendert nie Event-UIDs oder kuendigt Treffer erneut an; README dokumentiert Variablen, Filter, Grenzen, Upgrade und vier Rezepte, die Tests rendern | VERIFIED | `event_uid` hasht den rohen Programmtitel (`render.py:270`), im Probelauf stabil. README-Abschnitte Variables, Syntax, Filters, Limits (Zeile 269), Checking templates, Upgrading, Recipes vorhanden; `tests/test_readme_recipes.py` rendert jedes Rezept und prueft Vollstaendigkeit von Filtern und Variablen; Gesamtsuite gruen. |

**Score:** 5/5 Wahrheiten verifiziert (0 present, behavior-unverified)

Keines der Kriterien ist verhaltensabhaengig im Sinne von Zustandsuebergaengen ohne Test: Die Kuendigungs- und Fallback-Invarianten haben benannte, gruene Tests (`test_template_edit_does_not_reannounce_matches`, `test_noop_data_change_sends_no_template_signal`, Laufzeit-Fallback-Tests in `tests/test_template_runtime.py`).

### Erforderliche Artefakte

| Artefakt | Erwartet | Status | Details |
|----------|----------|--------|---------|
| `custom_components/xmltv_calendar/xmltv/template_engine.py` | Sandbox-Engine | VERIFIED | Substanziell, von `render.py` genutzt |
| `custom_components/xmltv_calendar/xmltv/render.py` | `EventTemplates`, `validate_template`, `event_uid` | VERIFIED | Von Flow, Matcher, Kalender, Vorschau genutzt |
| `custom_components/xmltv_calendar/xmltv/settings.py` | Neuer Standard, Legacy-Normalisierung | VERIFIED | `LEGACY_DEFAULT_TITLE_TEMPLATE` in `with_defaults` |
| `translations/en.json`, `translations/de.json` | Fehlertexte | VERIFIED | Durch Tests und UAT gedeckt |
| `README.md` Abschnitt Templates | Doku mit Rezepten | VERIFIED | Gelesen, durch Tests abgesichert |
| Test-Dateien der Phase | Tests | VERIFIED | Vorhanden, gruen |

### Schluesselverbindungen

| Von | Nach | Via | Status |
|-----|------|-----|--------|
| `render.py` | `template_engine.py` | `compile_template`, `TemplateError` | WIRED |
| `config_flow.py` | `render.validate_template` | `_advanced_errors` (Zeile 547) | WIRED |
| `matcher.py` | `EventTemplates.from_mapping(subentry.data, subentry.title)` | Zeilen 130, 418 | WIRED |
| `calendar.py` | `render.to_event_fields(..., tz=)` | `_to_event`, `build_events`, `async_get_events` | WIRED |
| `preview.py` | `EventTemplates.from_mapping` + `to_event_fields(tz=)` | Zeilen 80-88 | WIRED |

### Datenfluss (Level 4)

Werte fliessen aus `Programme`/`Channel` ueber `template_values` in den Render; Feed-Text wird nur als Variable, nie als Vorlagenquelltext verwendet (T-05-04). Status: FLOWING.

### Verhaltens-Stichproben

| Verhalten | Befehl | Ergebnis | Status |
|-----------|--------|----------|--------|
| Gesamtsuite (einmal) | `uv run --offline pytest -q` | 1268 passed, 1 skipped | PASS |
| Lint und Format | `ruff check .`, `ruff format --check .` | alles gruen, 80 Dateien formatiert | PASS |
| Sandbox-Ablehnungen, Rezepte, Legacy- und Laufzeit-Fallback | eigene Probeskripte gegen `render` | wie oben | PASS |
| Schuldenmarker `TBD`/`FIXME`/`XXX` | `grep` in `custom_components`, `README.md`, Rezept-Tests | keine Treffer | PASS |

### Probe-Ausfuehrung

SKIPPED: die Phase deklariert keine Probe-Skripte (`probe-*.sh`).

### Anforderungsabdeckung

| Anforderung | Quellplaene | Beschreibung | Status | Beleg |
|-------------|-------------|--------------|--------|-------|
| EVT-03 | 05-01, 05-02, 05-04, 05-05 | Titelvorlage als sandboxed Jinja; unbekannte Variablen/Filter/Syntax und Alt-Syntax im Flow abgelehnt | SATISFIED | Engine, Flow-Validierung, Uebersetzungen, Probelauf |
| EVT-04 | 05-01, 05-02, 05-04, 05-05 | Standardbeschreibung bleibt, Beschreibungsvorlage gleicher Art | SATISFIED | `render_description`, `default_description`, Ersatz bei Fehlern, "Starts 20:15 on Sky" |
| EVT-10 | 05-01, 05-03, 05-04, 05-05 | Bedingungen, Textfilter, lokale Start/Ende | SATISFIED | Filtersatz, `tz`-Durchreichung, Rezepte |

Alle drei IDs stehen in den PLAN-Frontmattern (05-01: alle drei, 05-02: EVT-03/04, 05-03: EVT-10, 05-04 und 05-05: alle drei) und in REQUIREMENTS.md (Zeilen 42, 43, 48; Traceability 131, 132, 137 "Phase 5, Complete"). Verwaiste Anforderungen: keine.

### Gefundene Anti-Patterns

Keine Blocker. Der bisherige Warnpunkt (Regex-Pruefung nicht bei `map`/`select`/`reject` mit Filtername als Text) ist als T-05-03 dokumentiert und als Restrisiko AR-05-03 angenommen (README Limits Zeilen 278-281, `05-SECURITY.md`, `threats_open: 0`); UAT-Test 4 bestaetigt die Entscheidung.

### Nicht blockierende Hinweise (offene Review-Befunde)

`05-REVIEW.md`: 0 kritisch, 4 Warnungen, 4 Infos; `05-REVIEW-DISPOSITION.md` fuehrt alle 8 als `open` (noch nicht triagiert). Sie sind beratend und beruehren keines der fuenf Erfolgskriterien:

- WR-01: Ein zweiter Vorlagenfehler zeigt das Detail des ersten.
- WR-02: Abwaehlen von "Advanced options" speichert eine hinterlegte Vorlage ohne Validierung.
- WR-03: Die Alt-Syntax-Pruefung wird von jedem Text mit `{{` oder `{%` umgangen.
- WR-04: `clean_description` haelt "hoechstens eine Leerzeile" nicht ein und kuerzt Zeilenraender nicht.
- IN-01 bis IN-04: stille Verwerfung angepasster Phase-2-bis-4-Titelvorlagen beim Upgrade, ungenutzte Beschreibung und UID in der Vorschau, irrefuehrender Kommentar und unsynchronisiertes Flag, Randtrenner-Entfernung bei Titeln und ungereinigte Standardbeschreibung.

Empfehlung: vor einem naechsten Release triagieren (`fixed`/`skipped`/`deferred`), vor allem WR-02 und WR-03, weil sie die Flow-Validierung betreffen.

### Menschliche Verifikation

Keine offenen Punkte. Alle vier frueheren Punkte sind in `05-UAT.md` mit `pass` abgeschlossen (deutsche UI auf ha-dev, deutsche Fehlertexte, hassfest und HACS gruen im Release-Lauf v1.0.0, Entscheidung zur Regex-Umgehung: Restrisiko dokumentiert).

### Zusammenfassung

Keine Luecken. Alle fuenf ROADMAP-Erfolgskriterien sind im Code belegt und durch eigene Probelaeufe bestaetigt, die Testsuite (1268 bestanden, 1 uebersprungen) und Ruff sind gruen, alle drei Anforderungs-IDs sind abgedeckt, Sicherheitsstand `threats_open: 0`.

---

_Verifiziert: 2026-10-30_
_Verifier: Claude (gsd-verifier)_
