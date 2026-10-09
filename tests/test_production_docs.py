"""Controleer de productiegrens in lokale bestanden en resulterende Git-bomen."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check-production-docs.py"
PRODUCT_FILES = [
    "berekeningen-en-patroonherkenning.md",
    "assets/analyseketen.svg",
    "assets/auditpopulatie.svg",
    "assets/her-escalatie.svg",
    "assets/peervergelijking.svg",
    "assets/signaaloverlap.svg",
    "assets/tijdvensters.svg",
]


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "--quiet")
    for name in PRODUCT_FILES:
        file = tmp_path / "docs" / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("synthetisch document")
    return tmp_path


def check(root, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=root, text=True, capture_output=True
    )


def tree(root):
    git(root, "add", "docs")
    return git(root, "write-tree")


def test_product_files_pass_locally_and_in_git(repo):
    assert check(repo).returncode == 0
    assert check(repo, "--revision", tree(repo)).returncode == 0


def test_untracked_development_file_is_rejected(repo):
    (repo / "docs" / "nieuw-ontwerp.md").write_text("ontwerp")
    result = check(repo)
    assert result.returncode == 1
    assert "Niet toegestaan" in result.stdout
    assert "nieuw-ontwerp.md" in result.stdout


def test_git_tree_rejects_mockups_even_when_deleted_locally(repo):
    mockup = repo / "docs" / "mockups" / "rapport.html"
    mockup.parent.mkdir()
    mockup.write_text("mock-up")
    revision = tree(repo)
    mockup.unlink()
    assert check(repo).returncode == 0
    result = check(repo, "--revision", revision)
    assert result.returncode == 1
    assert "docs/mockups/rapport.html" in result.stdout


def test_missing_product_document_is_rejected(repo):
    (repo / "docs" / PRODUCT_FILES[0]).unlink()
    for args in [(), ("--revision", tree(repo))]:
        result = check(repo, *args)
        assert result.returncode == 1
        assert "Ontbrekende productiedocumentatie" in result.stdout


def test_symlink_cannot_replace_product_document(repo):
    file = repo / "docs" / PRODUCT_FILES[0]
    file.unlink()
    file.symlink_to("assets/analyseketen.svg")
    for args in [(), ("--revision", tree(repo))]:
        result = check(repo, *args)
        assert result.returncode == 1
        assert "Geen regulier documentatiebestand" in result.stdout
