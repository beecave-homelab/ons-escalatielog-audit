import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest
from test_release_version import source

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("release_tools", ROOT / "scripts/release_tools.py")
release_tools = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_tools)
SHA = "a" * 40


def test_package_only_commit_bytes_and_reproducible_zip(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    files = source()
    files.update({name: "synthetisch" for name in release_tools.FILES if name not in files})
    files["README.md"] += "\n[Doc](docs/berekeningen-en-patroonherkenning.md)"
    files["docs/berekeningen-en-patroonherkenning.md"] = "![Diagram](assets/analyseketen.svg)"
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    for command in (
        ["init", "-q"],
        ["add", "."],
        ["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Test"],
    ):
        subprocess.run(["git", *command], cwd=repo, check=True)
    monkeypatch.chdir(repo)
    (repo / release_tools.APP).write_text("lokale afwijking")
    (repo / "exports").mkdir()
    (repo / "exports/geheim.txt").write_text("mag niet mee")
    first, second = tmp_path / "first", tmp_path / "second"
    sha = release_tools.package("HEAD", "1.2.3", first)
    assert sha == subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    release_tools.package("HEAD", "1.2.3", second)
    archive = "ons-escalatielog-audit-1.2.3.zip"
    assert (first / archive).read_bytes() == (second / archive).read_bytes()
    with ZipFile(first / archive) as bundle:
        assert set(bundle.namelist()) == set(release_tools.FILES)
        assert bundle.read(release_tools.APP) == files[release_tools.APP].encode()
        extracted = tmp_path / "unpacked"
        bundle.extractall(extracted)
    release_tools.check_links(
        {name: (extracted / name).read_bytes() for name in release_tools.FILES}
    )
    for line in (first / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split("  ")
        assert hashlib.sha256((first / name).read_bytes()).hexdigest() == digest
    assert (first / "release-notes.md").read_text() == "- Verandering.\n"


@pytest.mark.parametrize("target", ["missing.md", "../outside.md", "/absolute.md"])
def test_missing_package_links(target):
    with pytest.raises(ValueError):
        release_tools.check_links(
            {
                "README.md": f"[Link]({target})".encode(),
                "docs/berekeningen-en-patroonherkenning.md": b"",
            }
        )


class FakeGitHub:
    def __init__(self):
        self.tag = None
        self.release = None
        self.assets = {}
        self.writes = []
        self.fail_name = None

    def tag_commit(self, _version):
        return self.tag

    def request(self, endpoint, *, method="GET", payload=None, binary=False, file=None):
        if method == "POST":
            self.writes.append(endpoint)
            if endpoint == "git/refs":
                self.tag = payload["sha"]
            elif endpoint == "releases":
                self.release = {
                    **payload,
                    "id": 1,
                    "html_url": "https://github.com/test/release",
                    "upload_url": "https://uploads.github.com/assets{?name,label}",
                }
            else:
                name = endpoint.split("?name=")[1]
                if name == self.fail_name:
                    raise RuntimeError("Upload mislukt")
                self.assets[name] = file.read_bytes()
                return {"id": name, "name": name, "state": "uploaded"}
            return self.release
        if endpoint.startswith("releases/tags/"):
            return self.release
        if endpoint.startswith("releases/1/assets?"):
            return [{"id": name, "name": name, "state": "uploaded"} for name in self.assets]
        if binary:
            return self.assets[endpoint.split("/")[-1]]
        raise AssertionError(endpoint)


@pytest.fixture
def assets(tmp_path):
    files = {}
    for name in ("app.html", "app.zip", "SHA256SUMS.txt"):
        path = tmp_path / name
        path.write_bytes(name.encode())
        files[name] = path
    return files


def test_create_and_resume_after_partial_upload(assets):
    api = FakeGitHub()
    api.fail_name = "app.zip"
    with pytest.raises(RuntimeError, match="Upload"):
        release_tools.prepare(api, "1.2.3", SHA, assets, "- Verandering.")
    assert api.tag == SHA and api.release["draft"]
    assert set(api.assets) == {"app.html"}
    api.fail_name = None
    api.writes.clear()
    release_tools.prepare(api, "1.2.3", SHA, assets, "- Verandering.")
    assert len(api.writes) == 2
    assert set(api.assets) == set(assets)
    api.writes.clear()
    release_tools.prepare(api, "1.2.3", SHA, assets, "- Verandering.")
    assert api.writes == []


@pytest.mark.parametrize("conflict", ["tag", "commit", "published", "bytes", "extra", "notes"])
def test_conflicts_never_mutate_existing_objects(assets, conflict):
    api = FakeGitHub()
    release_tools.prepare(api, "1.2.3", SHA, assets, "- Verandering.")
    api.writes.clear()
    if conflict == "tag":
        api.tag = "b" * 40
    elif conflict == "commit":
        api.release["target_commitish"] = "main"
    elif conflict == "published":
        api.release["draft"] = False
    elif conflict == "bytes":
        api.assets["app.zip"] = b"afwijkend"
    elif conflict == "extra":
        api.assets["vreemd.txt"] = b"onbekend"
    else:
        api.release["body"] = "afwijkend"
    with pytest.raises(ValueError):
        release_tools.prepare(api, "1.2.3", SHA, assets, "- Verandering.")
    assert api.writes == []


def test_existing_identical_tag_without_release(assets):
    api = FakeGitHub()
    api.tag = SHA
    release_tools.prepare(api, "1.2.3", SHA, assets, "- Verandering.")
    assert "git/refs" not in api.writes


def test_api_handles_404_but_not_authentication_errors(monkeypatch):
    def command(_args, **_kwargs):
        return subprocess.CompletedProcess([], 1, b"{}", b"gh: Not Found (HTTP 404)")

    monkeypatch.setattr(release_tools.subprocess, "run", command)
    api = release_tools.GitHub("owner/repo")
    assert api.request("releases/tags/1.2.3") is None
    with pytest.raises(RuntimeError):
        api.request("releases", method="POST", payload={"draft": True})


def test_annotated_tag_is_resolved(monkeypatch):
    api = release_tools.GitHub("owner/repo")
    objects = iter(
        [{"object": {"type": "tag", "sha": "b" * 40}}, {"object": {"type": "commit", "sha": SHA}}]
    )
    monkeypatch.setattr(api, "request", lambda _endpoint: next(objects))
    assert api.tag_commit("1.2.3") == SHA


def test_gh_upload_sends_bytes_and_preserves_draft_payload(monkeypatch, tmp_path):
    commands = []

    def command(args, **kwargs):
        commands.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, b'{"draft":true}', b"")

    monkeypatch.setattr(release_tools.subprocess, "run", command)
    api = release_tools.GitHub("owner/repo")
    api.request("releases", method="POST", payload={"draft": True})
    assert json.loads(commands[0][1]["input"]) == {"draft": True}
    path = tmp_path / "file"
    path.write_bytes(b"example")
    api.request("https://uploads.github.com/assets?name=file", method="POST", file=path)
    assert "--input" in commands[1][0] and str(path) in commands[1][0]
