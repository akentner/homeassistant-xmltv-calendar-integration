"""The pure XMLTV library never imports Home Assistant, so it stays testable and reusable without it."""

import ast
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[2] / "custom_components" / "xmltv_calendar" / "xmltv"


def _imported_modules(path: Path) -> list[str]:
    modules: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
        if isinstance(node, ast.Import):
            modules += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.append(node.module)
    return modules


def test_library_has_no_homeassistant_imports() -> None:
    sources = sorted(LIBRARY.rglob("*.py"))
    assert sources, "xmltv library has no modules"
    offenders = [
        f"{path.relative_to(LIBRARY)}: {module}"
        for path in sources
        for module in _imported_modules(path)
        if module == "homeassistant" or module.startswith("homeassistant.")
    ]
    assert offenders == []


def test_purity_guard_detects_homeassistant_import(tmp_path: Path) -> None:
    module = tmp_path / "bad.py"
    source = "import os\nfrom homeassistant.core import HomeAssistant\nimport homeassistant\n"
    module.write_text(source, encoding="utf-8")
    assert _imported_modules(module) == ["os", "homeassistant.core", "homeassistant"]
