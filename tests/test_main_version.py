"""Borg het versiebeleid met synthetische bronnen en echte tijdelijke Git-bomen."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from test_release_version import source

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "main_version", ROOT / "scripts/check_main_version.py"
)
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


def files(version: str = "1.2.3", pending: str = "") -> dict[str, str]:
    """Geef volledig fictieve versiebestanden inclusief virtuele lockpackage."""
    result = source(version, pending)
    result["uv.lock"] = f'[[package]]\nname = "ons-escalatielog-audit"\nversion = "{version}"\n'
    return result


@pytest.mark.parametrize("version", ["1.2.4", "1.3.0", "2.0.0", "1.10.0"])
def test_product_change_requires_higher_version(version: str) -> None:
    """Patch, minor, major en numerieke meercijferige SemVer zijn toegestaan."""
    assert policy.check_change(files().__getitem__, files(version).__getitem__, {policy.APP})


@pytest.mark.parametrize("version", ["1.2.3", "1.2.2", "1.1.9", "0.9.9"])
def test_product_change_rejects_equal_or_lower_version(version: str) -> None:
    """Een oude releasebeschrijving legitimeert geen ongewijzigde/lager versie."""
    with pytest.raises(ValueError, match="hogere SemVer"):
        policy.check_change(files().__getitem__, files(version).__getitem__, {policy.APP})


@pytest.mark.parametrize(
    "changed",
    [
        {"README.md"},
        {"tests/test_x.py"},
        {".github/workflows/ci.yml"},
        {"scripts/check_main_version.py"},
        set(),
    ],
)
def test_non_product_change_does_not_require_bump(changed: set[str]) -> None:
    """Niet-runtimewijzigingen mogen ongepubliceerde notities behouden."""
    data = files(pending="- Toekomstige wijziging.")
    assert not policy.check_change(data.__getitem__, data.__getitem__, changed)


@pytest.mark.parametrize(
    "name,value,error",
    [
        ("CHANGELOG.md", "## [1.2.4]\n- Geen datum.", "datum"),
        ("CHANGELOG.md", "## [1.2.3] - 2026-10-12\n- Oude versie.", "ontbreekt"),
        ("pyproject.toml", 'version = "1.2.3"', "dezelfde SemVer"),
        ("README.md", "Geen badge", "versiebadge"),
        ("uv.lock", '[[package]]\nname = "ons-escalatielog-audit"\nversion = "1.2.3"', "uv.lock"),
        ("uv.lock", "", "uv.lock"),
    ],
)
def test_product_change_rejects_invalid_release(name: str, value: str, error: str) -> None:
    """Controleer ontbrekende beschrijving, datum en uiteenlopende versies."""
    head = files("1.2.4")
    head[name] = value
    with pytest.raises(ValueError, match=error):
        policy.check_change(files().__getitem__, head.__getitem__, {policy.APP, name})


def test_product_change_rejects_unreleased_notes() -> None:
    """Een productmerge moet volledig aan een releaseversie gekoppeld zijn."""
    with pytest.raises(ValueError, match="Nog niet uitgebracht"):
        policy.check_change(
            files().__getitem__, files("1.2.4", "- Rest.").__getitem__, {policy.APP}
        )


def test_preexisting_future_section_must_be_updated() -> None:
    """Een wijziging elders in de changelog vervangt geen nieuwe releasebeschrijving."""
    base, head = files(), files("1.2.4")
    base["CHANGELOG.md"] += policy.section(head["CHANGELOG.md"], "1.2.4") + "\n"
    with pytest.raises(ValueError, match="changelogsectie"):
        policy.check_change(base.__getitem__, head.__getitem__, {policy.APP, "CHANGELOG.md"})
    head["CHANGELOG.md"] = head["CHANGELOG.md"].replace(
        "- Verandering.", "- Nieuwe functionaliteit."
    )
    assert policy.check_change(base.__getitem__, head.__getitem__, {policy.APP, "CHANGELOG.md"})


@pytest.fixture
def repository(tmp_path: Path, monkeypatch):
    """Maak een echte Git-basis, zonder afhankelijkheid van de werkrepository."""
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "config", "user.name", "Synthetische test"], check=True)

    def commit(data: dict[str, str]) -> str:
        for name, value in data.items():
            (tmp_path / name).write_text(value)
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(["git", "commit", "-qm", "Synthetische wijziging"], check=True)
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()

    return tmp_path, commit, commit(files())


def test_git_comparison_and_cli(repository) -> None:
    """De CLI vergelijkt commitbomen en negeert ongecommitteerde bronwijzigingen."""
    root, commit, base = repository
    commit(files("1.2.4"))
    (root / policy.APP).write_text("Ongecommitteerd")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_main_version.py"), "--base", base],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Applicatiewijziging" in result.stdout


def test_git_doc_only_and_missing_refs(repository) -> None:
    """Een documentatiecommit slaagt; een onbekende ref faalt expliciet."""
    _, commit, base = repository
    head = files()
    head["README.md"] += "\nGebruikersuitleg."
    commit(head)
    assert not policy.check_refs(base)
    for ref in ("ontbreekt", "0" * 40):
        with pytest.raises(subprocess.CalledProcessError):
            policy.check_refs(ref)
    with pytest.raises(subprocess.CalledProcessError):
        policy.check_refs(base, "ontbreekt")


@pytest.mark.parametrize("rename", [True, False])
def test_removed_or_renamed_app_is_not_exempt(repository, rename: bool) -> None:
    """Verwijderen of hernoemen mag de productcontrole niet omzeilen."""
    root, commit, base = repository
    app = root / policy.APP
    if rename:
        app.rename(root / "nieuwe-app.html")
    else:
        app.unlink()
    commit({})
    with pytest.raises(subprocess.CalledProcessError):
        policy.check_refs(base)


def test_version_workflow_compares_all_main_events() -> None:
    """De verplichte status haalt geschiedenis op en controleert alle main-events."""
    workflow = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    for event in ("pull_request", "push", "merge_group"):
        assert workflow["on"][event] == {"branches": ["main"]}
    job = workflow["jobs"]["version"]
    assert job["name"] == "Versiecontrole"
    checkout = job["steps"][0]
    assert checkout["with"]["fetch-depth"] == "0"
    step = next(
        s for s in job["steps"] if s.get("name") == "Controleer productwijzigingen naar main"
    )
    assert (
        step["if"]
        == 'contains(fromJSON(\'["pull_request", "merge_group", "push"]\'), github.event_name)'
    )
    assert (
        step["env"]["BASE_SHA"] == "${{ github.event.pull_request.base.sha || "
        "github.event.merge_group.base_sha || github.event.before }}"
    )
    assert step["run"] == 'python scripts/check_main_version.py --base "$BASE_SHA" --head HEAD'
