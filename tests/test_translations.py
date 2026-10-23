"""German translation (de.json) is served by Home Assistant and mirrors en.json (CFG-04, UAT 02 test 1)."""

import ast
import json
import logging
import re
import string
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.helpers.translation import async_get_translations

import custom_components.xmltv_calendar as integration
from custom_components.xmltv_calendar import cache, const, coordinator
from custom_components.xmltv_calendar.const import DOMAIN
from custom_components.xmltv_calendar.xmltv import render, schedule, settings

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

TRANSLATIONS = Path(integration.__file__).parent / "translations"
EN_JSON = TRANSLATIONS / "en.json"
DE_JSON = TRANSLATIONS / "de.json"

# Same names as Home Assistant core's workday integration
GERMAN_WEEKDAYS = {
    "mon": "Montag",
    "tue": "Dienstag",
    "wed": "Mittwoch",
    "thu": "Donnerstag",
    "fri": "Freitag",
    "sat": "Samstag",
    "sun": "Sonntag",
}

# hassfest's value rules; hassfest skips de.json for custom integrations, so this test enforces them
_SINGLE_QUOTED_PLACEHOLDER = re.compile(r"'\{[^{}]*\}'")
_HTML_TAG = re.compile(r"<[A-Za-z/!]")
_URL = re.compile(r"\b(?:https?|ftps?|mqtts?)://[\w-]+(?:\.[\w-]+)+|\bwww\.[\w-]+(?:\.[\w-]+)+", re.IGNORECASE)
# English tokens that must survive translation verbatim: regexes, paths, identifiers, numbers, placeholders
_LITERAL_MARKERS = re.compile(r"[\d\\^$_/{]")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten(node: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(node, dict):
        return {prefix: node}
    flat: dict[str, Any] = {}
    for key, value in node.items():
        flat.update(_flatten(value, f"{prefix}.{key}" if prefix else key))
    return flat


def _placeholders(text: str) -> set[str]:
    # The extraction homeassistant.helpers.translation._validate_placeholders uses
    return {name for _, name, _, _ in string.Formatter().parse(text) if name is not None}


def _literals(text: str) -> list[str]:
    tokens = (token.rstrip(".,;:)").lstrip("(") for token in text.split())
    return [token for token in tokens if _LITERAL_MARKERS.search(token)]


async def test_home_assistant_serves_german_strings(hass: HomeAssistant, caplog: Any) -> None:
    served = await async_get_translations(hass, "de", "selector", [DOMAIN])
    weekdays = {day: served.get(f"component.{DOMAIN}.selector.weekday.options.{day}") for day in GERMAN_WEEKDAYS}
    assert weekdays == GERMAN_WEEKDAYS

    assert DE_JSON.is_file()
    for section, node in _load(DE_JSON).items():
        served = await async_get_translations(hass, "de", section, [DOMAIN])
        expected = _flatten(node, f"component.{DOMAIN}.{section}")
        assert {key: served.get(key) for key in expected} == expected, section

    errors = [
        record.getMessage()
        for record in caplog.records
        if record.name == "homeassistant.helpers.translation" and record.levelno >= logging.ERROR
    ]
    assert errors == []


def test_de_values_follow_hassfest_rules() -> None:
    assert DE_JSON.is_file()
    violations: dict[str, str] = {}
    for key, value in _flatten(_load(DE_JSON)).items():
        if not isinstance(value, str) or not value:
            violations[key] = "not a non-empty string"
        elif value != value.strip():
            violations[key] = "leading or trailing whitespace"
        elif "[%" in value:
            violations[key] = "[% reference"
        elif _SINGLE_QUOTED_PLACEHOLDER.search(value):
            violations[key] = "single-quoted placeholder"
        elif _HTML_TAG.search(value):
            violations[key] = "HTML tag"
        elif _URL.search(value):
            violations[key] = "URL"
        else:
            try:
                names = _placeholders(value)
            except ValueError as err:
                violations[key] = f"unparsable placeholder: {err}"
            else:
                if not all(name.isidentifier() for name in names):
                    violations[key] = f"placeholder is not an identifier: {sorted(names)}"
    assert violations == {}


def test_de_has_same_keys_as_en() -> None:
    en_keys = list(_flatten(_load(EN_JSON)))
    de_keys = list(_flatten(_load(DE_JSON)))

    assert sorted(set(en_keys) - set(de_keys)) == []  # missing in de.json
    assert sorted(set(de_keys) - set(en_keys)) == []  # extra in de.json
    assert de_keys == en_keys  # same order


def test_de_keeps_placeholders() -> None:
    en = _flatten(_load(EN_JSON))
    de = _flatten(_load(DE_JSON))

    assert any(_placeholders(text) for text in en.values())
    mismatches = {
        key: (sorted(_placeholders(text)), sorted(_placeholders(de.get(key, ""))))
        for key, text in en.items()
        if _placeholders(text) != _placeholders(de.get(key, ""))
    }
    assert mismatches == {}


def test_de_keeps_literals() -> None:
    en = _flatten(_load(EN_JSON))
    de = _flatten(_load(DE_JSON))

    collected = {token for text in en.values() for token in _literals(text)}
    assert {"^Tatort$", "formel\\s*1|formula\\s*1"} <= collected
    problems: dict[str, list[str]] = {}
    for key, text in en.items():
        german = de.get(key, "")
        missing = [token for token in _literals(text) if token not in german]
        if missing:
            problems.setdefault(key, []).extend(missing)
        if german.count("\n") != text.count("\n"):
            problems.setdefault(key, []).append("newline count")
    assert problems == {}


# --- Code-derived completeness (CFG-04, RESEARCH Pitfall 10): the required keys come from the code, not a list ---

PACKAGE = Path(integration.__file__).parent

# Flow class -> translation section of its steps, errors, aborts, menus and progress texts
FLOW_SECTIONS = {
    "XmltvConfigFlow": "config",
    "XmltvOptionsFlow": "options",
    "CalendarSubentryFlow": "config_subentries.calendar",
}

# Aborts Home Assistant raises on the flow's behalf, keyed by the flow method that triggers them
HA_ABORTS = {
    "_abort_if_unique_id_configured": "already_configured",
    "async_update_and_abort": "reconfigure_successful",
}

# A subentry flow's entry points; each needs its "Add" / "Edit" button text
SUBENTRY_ENTRY_POINTS = ("user", "reconfigure")

# Steps the flows have today; the collector must find at least these, so an AST change cannot make it vacuous
KNOWN_STEP_IDS = {
    "user",
    "url",
    "download",
    "schedule",
    "file",
    "name",
    "init",
    "basic",
    "advanced",
    "preview",
    "preview_empty",
}

# Selector translation_key -> the vocabulary of its option values
SELECTOR_VOCABULARIES = {
    "match_field": settings.MATCH_FIELDS,
    "weekday": settings.WEEKDAYS,
    "refresh_mode": schedule.REFRESH_MODES,
    "naive_timezone": schedule.NAIVE_TIMEZONES,
}

# Required texts that read the same in German as in English
SAME_IN_GERMAN = {"UTC"}

# Last fetch sensor attribute -> the vocabulary of its translated states
ATTEMPT_VOCABULARIES = {
    "trigger": cache.ATTEMPT_TRIGGERS,
    "outcome": cache.ATTEMPT_OUTCOMES,
    "cache": cache.ATTEMPT_CACHE,
    "failure_reason": coordinator.FAILURE_REASONS,
}


def _parse(name: str) -> ast.Module:
    return ast.parse((PACKAGE / name).read_text(encoding="utf-8"))


def _strings(node: ast.expr | None) -> list[str]:
    """Return the string values `node` can take: a literal, both branches of a conditional, or a const name."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _strings(node.body) + _strings(node.orelse)
    if isinstance(node, ast.Name) and isinstance(getattr(const, node.id, None), str):
        return [getattr(const, node.id)]
    return []


def _called_names(node: ast.AST) -> set[str]:
    return {call.func.id for call in ast.walk(node) if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)}


def _flow_scopes(module: ast.Module) -> dict[str, list[ast.AST]]:
    """Return per flow class its own body plus every module-level function it calls, transitively."""
    functions = {node.name: node for node in module.body if isinstance(node, ast.FunctionDef)}
    scopes: dict[str, list[ast.AST]] = {}
    for node in module.body:
        if not isinstance(node, ast.ClassDef) or node.name not in FLOW_SECTIONS:
            continue
        seen: set[str] = set()
        pending = _called_names(node) & functions.keys()
        while pending:
            name = pending.pop()
            seen.add(name)
            pending |= (_called_names(functions[name]) & functions.keys()) - seen
        scopes[node.name] = [node, *(functions[name] for name in sorted(seen))]
    return scopes


def _error_literals(scope: ast.AST) -> set[str]:
    """Return the error keys written into an errors dict: `errors[x] = "key"` and `{"base": "key"}`."""
    found: set[str] = set()
    for node in ast.walk(scope):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Subscript) for target in node.targets):
            if any(
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id.endswith("errors")
                for target in node.targets
            ):
                found.update(_strings(node.value))
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if isinstance(key, ast.Constant) and key.value == "base":
                    found.update(_strings(value))
    return found


def _flow_requirements() -> tuple[set[str], set[str]]:
    """Return (required translation leaf keys, step IDs found) for the three flows in config_flow.py."""
    required: set[str] = set()
    step_ids: set[str] = set()
    for class_name, scope_nodes in _flow_scopes(_parse("config_flow.py")).items():
        section = FLOW_SECTIONS[class_name]
        for scope in scope_nodes:
            for node in ast.walk(scope):
                if isinstance(node, ast.Call):
                    keywords = {keyword.arg: keyword.value for keyword in node.keywords}
                    steps = _strings(keywords.get("step_id"))
                    step_ids.update(steps)
                    required.update(f"{section}.step.{step}.title" for step in steps)
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr == "async_abort":
                            required.update(f"{section}.abort.{reason}" for reason in _strings(keywords.get("reason")))
                        if node.func.attr in HA_ABORTS:
                            required.add(f"{section}.abort.{HA_ABORTS[node.func.attr]}")
                    required.update(
                        f"{section}.progress.{action}" for action in _strings(keywords.get("progress_action"))
                    )
                    menu = keywords.get("menu_options")
                    if isinstance(menu, ast.List):
                        options = [option for element in menu.elts for option in _strings(element)]
                        assert len(options) == len(menu.elts), ast.unparse(menu)
                        required.update(
                            f"{section}.step.{step}.menu_options.{option}" for step in steps for option in options
                        )
                if isinstance(node, ast.Assign) and section.startswith("config_subentries."):
                    for target in node.targets:
                        if (
                            isinstance(target, ast.Name)
                            and target.id.removeprefix("async_step_") in SUBENTRY_ENTRY_POINTS
                        ):
                            required.add(f"{section}.initiate_flow.{target.id.removeprefix('async_step_')}")
            required.update(f"{section}.error.{error}" for error in _error_literals(scope))
        if section.startswith("config_subentries."):
            required.add(f"{section}.entry_type")
    # Template errors are raised by render.compile_template and passed through as err.reason
    subentry = FLOW_SECTIONS["CalendarSubentryFlow"]
    required.update(
        f"{subentry}.error.{error}" for error in (render.INVALID_TEMPLATE, render.UNKNOWN_PLACEHOLDER, "invalid_regex")
    )
    return required, step_ids


def _selector_keys() -> set[str]:
    """Return every selector translation_key literal used in config_flow.py."""
    return {
        value
        for node in ast.walk(_parse("config_flow.py"))
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "translation_key"
        for value in _strings(keyword.value)
    }


def _update_failed_keys() -> set[str]:
    """Return every literal translation_key of an UpdateFailed raised in coordinator.py."""
    return {
        value
        for node in ast.walk(_parse("coordinator.py"))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "UpdateFailed"
        for keyword in node.keywords
        if keyword.arg == "translation_key"
        for value in _strings(keyword.value)
    }


def _sensor_keys() -> set[str]:
    """Return every `_attr_translation_key = "..."` in sensor.py."""
    return {
        value
        for node in ast.walk(_parse("sensor.py"))
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "_attr_translation_key" for target in node.targets)
        for value in _strings(node.value)
    }


def _vocabulary_requirements() -> set[str]:
    """Return the required leaf keys of selectors, coordinator failures and sensors."""
    required: set[str] = set()
    assert _selector_keys() == set(SELECTOR_VOCABULARIES)
    for key, vocabulary in SELECTOR_VOCABULARIES.items():
        required.update(f"selector.{key}.options.{value}" for value in vocabulary)
    assert _update_failed_keys() <= coordinator.FAILURE_REASONS
    for reason in coordinator.FAILURE_REASONS:
        required.add(f"exceptions.{reason}.message")
        required.update(f"issues.source_failing_{reason}.{part}" for part in ("title", "description"))
    sensors = _sensor_keys()
    assert sensors == {"next_match", "last_fetch"}
    required.update(f"entity.sensor.{key}.name" for key in sensors)
    for attribute, vocabulary in ATTEMPT_VOCABULARIES.items():
        required.update(f"entity.sensor.last_fetch.state_attributes.{attribute}.state.{value}" for value in vocabulary)
    return required


def _missing(required: set[str], translations: dict[str, Any]) -> list[str]:
    return sorted(key for key in required if not (isinstance(translations.get(key), str) and translations[key].strip()))


def test_every_flow_key_is_translated() -> None:
    required, step_ids = _flow_requirements()
    assert step_ids >= KNOWN_STEP_IDS
    assert {"config.abort.already_configured", "config_subentries.calendar.abort.reconfigure_successful"} <= required
    assert {"config.progress.download", "config.step.user.menu_options.url"} <= required
    assert _missing(required, _flatten(_load(EN_JSON))) == []


def test_every_vocabulary_and_entity_key_is_translated() -> None:
    assert _missing(_vocabulary_requirements(), _flatten(_load(EN_JSON))) == []


def test_failure_reason_vocabulary_is_required() -> None:
    required = _vocabulary_requirements()
    reason_keys = {
        f"entity.sensor.last_fetch.state_attributes.failure_reason.state.{reason}"
        for reason in coordinator.FAILURE_REASONS
    }
    assert reason_keys <= required
    for path in (EN_JSON, DE_JSON):
        translations = _load(path)
        assert _missing(reason_keys, _flatten(translations)) == [], path.name
        states = translations["entity"]["sensor"]["last_fetch"]["state_attributes"]["failure_reason"]["state"]
        assert set(states) == coordinator.FAILURE_REASONS


@pytest.mark.parametrize("path", [EN_JSON, DE_JSON], ids=("en", "de"))
@pytest.mark.parametrize("reason", sorted(coordinator.FAILURE_REASONS))
def test_missing_failure_reason_translation_is_detected(path: Path, reason: str) -> None:
    translations = _flatten(_load(path))
    required = _vocabulary_requirements()
    assert _missing(required, translations) == []
    key = f"entity.sensor.last_fetch.state_attributes.failure_reason.state.{reason}"
    del translations[key]
    assert _missing(required, translations) == [key]


@pytest.mark.parametrize("reason", sorted(coordinator.FAILURE_REASONS))
def test_paired_failure_reason_omission_defeats_parity_but_not_completeness(reason: str) -> None:
    english = _flatten(_load(EN_JSON))
    german = _flatten(_load(DE_JSON))
    key = f"entity.sensor.last_fetch.state_attributes.failure_reason.state.{reason}"
    del english[key]
    del german[key]
    assert english.keys() == german.keys()
    required = _vocabulary_requirements()
    assert _missing(required, english) == [key]
    assert _missing(required, german) == [key]


def test_new_failure_reason_is_required_automatically(monkeypatch: pytest.MonkeyPatch) -> None:
    reason = "synthetic_reason"
    assert reason not in coordinator.FAILURE_REASONS
    before = _vocabulary_requirements()
    monkeypatch.setitem(ATTEMPT_VOCABULARIES, "failure_reason", coordinator.FAILURE_REASONS | {reason})
    required = _vocabulary_requirements()
    key = f"entity.sensor.last_fetch.state_attributes.failure_reason.state.{reason}"
    assert required - before == {key}
    for path in (EN_JSON, DE_JSON):
        assert _missing(required, _flatten(_load(path))) == [key]


async def test_german_ui_is_served_for_every_required_key(hass: HomeAssistant) -> None:
    required = _flow_requirements()[0] | _vocabulary_requirements()
    served: dict[str, Any] = {}
    for category in ("config", "options", "config_subentries", "selector", "exceptions", "issues", "entity"):
        translations = await async_get_translations(hass, "de", category, [DOMAIN])
        prefix = f"component.{DOMAIN}."
        served.update({key.removeprefix(prefix): value for key, value in translations.items()})
    english = _flatten(_load(EN_JSON))
    assert _missing(required, served) == []
    # Served in German: every required text differs from English unless it is a literal (UTC, a placeholder)
    untranslated = sorted(key for key in required if served[key] == english.get(key) and not _literals(served[key]))
    assert [key for key in untranslated if served[key] not in SAME_IN_GERMAN] == []
