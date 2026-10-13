"""Executable checks for HACS distribution (DST-01) and the CI supply chain (DST-02)."""

import json
import re
import struct
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
COMPONENTS = ROOT / "custom_components"
INTEGRATION = COMPONENTS / "xmltv_calendar"
WORKFLOWS = ROOT / ".github" / "workflows"
WORKFLOW_FILES = ("validate.yml", "ci.yml")

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
SHA_PIN = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
RUNNER = re.compile(r"^ubuntu-\d{2}\.\d{2}$")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
HACS_REQUIRED_MANIFEST_KEYS = ("codeowners", "documentation", "domain", "issue_tracker", "name", "version")
HACS_ALLOWED_KEYS = {
    "name",
    "content_in_root",
    "country",
    "filename",
    "hacs",
    "hide_default_branch",
    "homeassistant",
    "persistent_directory",
    "render_readme",
    "zip_release",
}


def _existing_workflows() -> list[str]:
    """Return every workflow file in the directory, so a new file cannot escape the supply-chain checks."""
    if not WORKFLOWS.is_dir():
        return []
    return sorted(path.name for path in [*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")])


def _load_workflow(filename: str) -> dict[Any, Any]:
    document = yaml.safe_load((WORKFLOWS / filename).read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _triggers(document: dict[Any, Any]) -> dict[str, Any]:
    # PyYAML parses the bare key `on` as the boolean True.
    triggers = document.get("on", document.get(True))
    assert isinstance(triggers, dict), "workflow needs a mapping of triggers"
    return triggers


def _steps(document: dict[Any, Any]) -> list[dict[str, Any]]:
    # A job that only calls a reusable workflow has no steps.
    return [step for job in document["jobs"].values() for step in job.get("steps", [])]


def _uses_refs(document: dict[Any, Any]) -> list[str]:
    refs = [step["uses"] for step in _steps(document) if "uses" in step]
    # Job-level reusable workflows also carry a `uses` key.
    refs += [job["uses"] for job in document["jobs"].values() if "uses" in job]
    return refs


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == PNG_SIGNATURE, f"{path.name} is not a PNG"
    assert data[12:16] == b"IHDR", f"{path.name} has no IHDR chunk first"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def workflow_runners(directory: Path) -> dict[tuple[str, str], Any]:
    """Return the `runs-on` value of every job in every workflow file of a directory.

    A job without `runs-on` (a caller of a reusable workflow) is skipped.
    """
    runners: dict[tuple[str, str], Any] = {}
    for path in sorted([*directory.glob("*.yml"), *directory.glob("*.yaml")]):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        jobs = document.get("jobs") if isinstance(document, dict) else None
        if not isinstance(jobs, dict):
            continue
        for name, job in jobs.items():
            if isinstance(job, dict) and "runs-on" in job:
                runners[(path.name, str(name))] = job["runs-on"]
    return runners


def pinned_runner_problems(runners: dict[tuple[str, str], Any]) -> list[str]:
    """Describe every way the runners of a workflow directory miss the single pinned runner.

    Pinned means one OS label (`ubuntu-NN.NN`), not one image build: GitHub still rolls the
    hosted image of that label weekly, so reproducibility is bounded by the OS label.
    """
    problems = [
        f"{filename}:{job} runs on {value!r}"
        for (filename, job), value in runners.items()
        if not (isinstance(value, str) and RUNNER.match(value))
    ]
    distinct = sorted({str(value) for value in runners.values()})
    if len(distinct) > 1:
        problems.append(f"more than one runner version: {distinct}")
    if not runners:
        problems.append("no workflow job declares a runner")
    return problems


workflow_files = pytest.mark.parametrize("filename", _existing_workflows())


def test_manifest_has_hacs_required_keys() -> None:
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    for key in HACS_REQUIRED_MANIFEST_KEYS:
        assert manifest.get(key), f"manifest.json misses {key}"
    assert manifest["requirements"] == []
    assert SEMVER.match(manifest["version"]), manifest["version"]


def test_domain_matches_folder_name() -> None:
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    folders = [path.name for path in COMPONENTS.iterdir() if path.is_dir() and not path.name.startswith("__")]
    assert folders == [manifest["domain"]] == ["xmltv_calendar"]


def test_hacs_json_keys_allowed_and_floor() -> None:
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    assert set(hacs) <= HACS_ALLOWED_KEYS, set(hacs) - HACS_ALLOWED_KEYS
    assert hacs["name"] == "XMLTV Calendar"
    assert hacs["homeassistant"] == "2026.3.0"


@pytest.mark.parametrize(("filename", "size"), [("icon.png", 256), ("icon@2x.png", 512)])
def test_brand_icon_is_valid_png(filename: str, size: int) -> None:
    assert _png_size(INTEGRATION / "brand" / filename) == (size, size)


def test_license_is_mit_with_holder() -> None:
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.startswith("MIT License")
    assert "Copyright (c) 2026 Alexander Kentner" in text


def test_readme_documents_hacs_install_and_floor() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "https://github.com/akentner/homeassistant-xmltv-integration" in text
    assert "HACS" in text
    assert "2026.3" in text


def test_validate_workflow_has_hassfest_and_hacs_jobs() -> None:
    document = _load_workflow("validate.yml")
    assert document["name"] == "Validate"
    assert {"hassfest", "hacs"} <= set(document["jobs"])
    refs = _uses_refs(document)
    assert any(ref.startswith("home-assistant/actions/hassfest@") for ref in refs)
    assert any(ref.startswith("hacs/action@") for ref in refs)
    assert "schedule" in _triggers(document)


def test_hacs_action_has_category_and_no_ignore() -> None:
    steps = [step for step in _steps(_load_workflow("validate.yml")) if step.get("uses", "").startswith("hacs/action@")]
    assert len(steps) == 1
    inputs = steps[0].get("with", {})
    assert inputs.get("category") == "integration"
    assert "ignore" not in inputs


@workflow_files
def test_workflows_have_empty_permissions(filename: str) -> None:
    assert _load_workflow(filename)["permissions"] == {}


@workflow_files
def test_all_action_refs_are_pinned_by_sha(filename: str) -> None:
    refs = _uses_refs(_load_workflow(filename))
    assert refs, "workflow uses no actions at all"
    for ref in refs:
        if ref.startswith("./"):
            # A local reusable workflow has no SHA; it must exist in this repository.
            assert (ROOT / ref).is_file(), f"{ref} does not exist in the repository"
            continue
        assert SHA_PIN.match(ref), f"{ref} is not pinned by a 40-character commit SHA"


@workflow_files
def test_checkout_does_not_persist_credentials(filename: str) -> None:
    workflow = _load_workflow(filename)
    checkouts = [step for step in _steps(workflow) if step.get("uses", "").startswith("actions/checkout@")]
    for step in checkouts:
        assert step.get("with", {}).get("persist-credentials") is False


@workflow_files
def test_push_trigger_has_no_branch_filter(filename: str) -> None:
    triggers = _triggers(_load_workflow(filename))
    assert "push" in triggers
    assert "branches" not in (triggers["push"] or {})
    assert "branches-ignore" not in (triggers["push"] or {})


def test_every_job_runs_on_one_pinned_runner() -> None:
    assert pinned_runner_problems(workflow_runners(WORKFLOWS)) == []


def test_runner_guard_flags_unpinned_and_mixed_runners() -> None:
    runners = {("a.yml", "x"): "ubuntu-latest", ("a.yml", "y"): "ubuntu-24.04", ("b.yml", "z"): "ubuntu-22.04"}
    problems = pinned_runner_problems(runners)
    assert "a.yml:x runs on 'ubuntu-latest'" in problems
    assert any(problem.startswith("more than one runner version") for problem in problems)
    assert pinned_runner_problems({}) == ["no workflow job declares a runner"]


def test_expected_workflows_exist() -> None:
    missing = [name for name in WORKFLOW_FILES if not (WORKFLOWS / name).is_file()]
    assert missing == [], f"missing workflow files: {missing}"


def test_ci_runs_locked_sync_lint_format_and_pytest() -> None:
    commands = [step["run"].strip() for step in _steps(_load_workflow("ci.yml")) if "run" in step]
    expected = (
        "uv sync --locked",
        "uv run ruff check .",
        "uv run ruff format --check .",
        'uv run pytest -q -m "not benchmark"',
    )
    for command in expected:
        assert command in commands, f"ci.yml never runs {command}"


@workflow_files
def test_workflows_have_no_path_filters(filename: str) -> None:
    for name, trigger in _triggers(_load_workflow(filename)).items():
        settings = trigger if isinstance(trigger, dict) else {}
        assert "paths" not in settings, f"{filename}: {name} has a paths filter"
        assert "paths-ignore" not in settings, f"{filename}: {name} has a paths-ignore filter"


def test_ci_jobs_are_independent() -> None:
    jobs = _load_workflow("ci.yml")["jobs"]
    dependent = [name for name, job in jobs.items() if "needs" in job]
    assert dependent == [], f"ci.yml jobs with needs: {dependent}"


def test_renovate_requires_approval_for_phcc() -> None:
    config = json.loads((ROOT / "renovate.json").read_text(encoding="utf-8"))
    rules = [
        rule
        for rule in config.get("packageRules", [])
        if "pytest-homeassistant-custom-component" in rule.get("matchPackageNames", [])
    ]
    assert len(rules) == 1
    assert rules[0].get("dependencyDashboardApproval") is True
