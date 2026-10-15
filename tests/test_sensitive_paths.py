"""Controleer de privacygrens met een tijdelijke Git-repository."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-sensitive-paths.sh"


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(SCRIPT, scripts / "check-sensitive-paths.sh")
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Synthetische test")
    return tmp_path


def run_check(repo, *args):
    return subprocess.run(
        ["bash", "scripts/check-sensitive-paths.sh", *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def add(repo, name):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("synthetisch")
    git(repo, "add", "-f", name)


@pytest.mark.parametrize(
    "name",
    [
        "export.xlsx",
        "sub/escalatie_log_controle_x_rapport.html",
        "Exports/rapport.html",
        "escalatielogs/echt.xlsx",
        "exports/rapport.html",
        "tests/fixtures/genest/voorbeeld.xlsx",
    ],
)
def test_forbidden_paths_fail_the_index_check(repo, name):
    add(repo, "docs/onschuldig.md")
    add(repo, name)
    result = run_check(repo, "--index")
    assert result.returncode == 1
    assert name in result.stderr


@pytest.mark.parametrize(
    "name",
    [
        "tests/fixtures/synthetic.xlsx",
        "escalatielogs/.gitkeep",
        "exports/.gitkeep",
        "docs/notitie.md",
    ],
)
def test_allowed_paths_pass_the_index_check(repo, name):
    add(repo, name)
    result = run_check(repo, "--index")
    assert result.returncode == 0, result.stderr


def test_range_check_detects_forbidden_commit(repo):
    add(repo, "escalatielogs/geheim.xlsx")
    git(repo, "commit", "-qm", "Verboden bestand")
    result = run_check(repo, "--range", "HEAD")
    assert result.returncode == 1
    assert "escalatielogs/geheim.xlsx" in result.stderr


def test_range_check_accepts_clean_commit(repo):
    add(repo, "tests/fixtures/synthetic.xlsx")
    git(repo, "commit", "-qm", "Schone commit")
    assert run_check(repo, "--range", "HEAD").returncode == 0
