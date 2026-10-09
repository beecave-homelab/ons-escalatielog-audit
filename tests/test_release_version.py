import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "version_check", ROOT / "scripts/check_release_version.py"
)
version_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(version_check)


def source(version="1.2.3", pending=""):
    return {
        version_check.APP: f"const APP_VERSION='{version}';",
        "pyproject.toml": f'version = "{version}"',
        "README.md": f"![Version](https://img.shields.io/badge/version-{version}-blue)",
        "CHANGELOG.md": f"## [Nog niet uitgebracht]\n{pending}\n"
        f"## [{version}] - 2026-10-09\n\n- Verandering.\n\n"
        "## [0.1.0] - 2020-01-01\n- Oud.\n",
    }


def test_versions_and_selected_notes():
    files = source(pending="- Onderhoud.")
    assert version_check.check_version(files.__getitem__) == ("1.2.3", "- Verandering.")
    with pytest.raises(ValueError, match="Nog niet uitgebracht"):
        version_check.check_version(files.__getitem__, "1.2.3", release=True)
    files = source()
    assert version_check.check_version(files.__getitem__, "1.2.3", release=True)[0] == "1.2.3"


@pytest.mark.parametrize("version", ["v1.2.3", "01.2.3", "1.2", "1.2.3;touch", "1.2.4"])
def test_invalid_requested_version(version):
    with pytest.raises(ValueError):
        version_check.check_version(source().__getitem__, version)


@pytest.mark.parametrize(
    "name,value",
    [
        ("pyproject.toml", 'version = "1.2.4"'),
        ("README.md", ""),
        ("CHANGELOG.md", "## [1.2.3]\n- Geen datum."),
        ("CHANGELOG.md", "## [1.2.3] - 2026-02-30\n- Ongeldige datum."),
        ("CHANGELOG.md", "## [1.2.3] - 2026-10-09\n"),
        ("CHANGELOG.md", "## [1.2.3] - 2026-10-09\n- Een\n## [1.2.3]\n- Twee"),
    ],
)
def test_invalid_version_sources(name, value):
    files = source()
    files[name] = value
    with pytest.raises(ValueError):
        version_check.check_version(files.__getitem__)
