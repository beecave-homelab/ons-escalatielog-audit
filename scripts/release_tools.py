"""Controleer versies, verpak een Git-commit en hervat uitsluitend identieke conceptreleases."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from check_release_version import APP, VERSION, check_version

FILES = (
    APP,
    "README.md",
    "LICENSE",
    "docs/berekeningen-en-patroonherkenning.md",
    "docs/assets/analyseketen.svg",
    "docs/assets/auditpopulatie.svg",
    "docs/assets/her-escalatie.svg",
    "docs/assets/peervergelijking.svg",
    "docs/assets/signaaloverlap.svg",
    "docs/assets/tijdvensters.svg",
)


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args])


def check_links(files: dict[str, bytes]) -> None:
    for name in ("README.md", "docs/berekeningen-en-patroonherkenning.md"):
        for target in re.findall(r"\]\(([^)]+)\)", files[name].decode()):
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            parts = list(PurePosixPath(name).parent.parts)
            for part in PurePosixPath(unquote(url.path)).parts:
                if part == "..":
                    if not parts:
                        raise ValueError(f"Verwijzing buiten het pakket: {target}")
                    parts.pop()
                elif part != ".":
                    parts.append(part)
            resolved = "/".join(parts)
            if resolved not in files:
                raise ValueError(f"Ontbrekende lokale verwijzing in {name}: {target}")


def package(revision: str, version: str, output: Path) -> str:
    sha = git("rev-parse", "--verify", f"{revision}^{{commit}}").decode().strip()
    entries = git("ls-tree", "-rz", sha).split(b"\0")
    modes = {entry.split(b"\t")[1].decode(): entry.split()[0] for entry in entries if entry}
    for name in (*FILES, "pyproject.toml", "CHANGELOG.md"):
        if modes.get(name) not in {b"100644", b"100755"}:
            raise ValueError(f"Geen regulier bestand in de commit: {name}")
    read = lambda name: git("show", f"{sha}:{name}").decode()  # noqa: E731
    _, notes = check_version(read, version, release=True)
    files = {name: git("show", f"{sha}:{name}") for name in FILES}
    check_links(files)
    output.mkdir(parents=True, exist_ok=False)
    (output / APP).write_bytes(files[APP])
    archive = output / f"ons-escalatielog-audit-{version}.zip"
    with ZipFile(archive, "w", compression=ZIP_STORED) as bundle:
        for name, content in files.items():
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, content)
    sums = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
        for path in (output / APP, archive)
    )
    (output / "SHA256SUMS.txt").write_text(sums)
    (output / "release-notes.md").write_text(notes + "\n")
    (output / "commit.txt").write_text(sha + "\n")
    return sha


class GitHub:
    """Gebruik gh-authenticatie zonder tokens te lezen of weer te geven."""

    def __init__(self, repository: str):
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
            raise ValueError("Ongeldige repository.")
        self.prefix = f"repos/{repository}"

    def request(self, endpoint, *, method="GET", payload=None, binary=False, file=None):
        endpoint = endpoint if endpoint.startswith("https://") else f"{self.prefix}/{endpoint}"
        command = ["gh", "api", endpoint, "--method", method]
        if binary:
            command += ["-H", "Accept: application/octet-stream"]
        if file is not None:
            command += ["-H", "Content-Type: application/octet-stream", "--input", str(file)]
        elif payload is not None:
            command += ["--input", "-"]
        result = subprocess.run(
            command,
            input=json.dumps(payload).encode() if payload is not None else None,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            if method == "GET" and "HTTP 404" in result.stderr.decode():
                return None
            raise RuntimeError(f"GitHub-aanvraag mislukt: {method} {endpoint}")
        return result.stdout if binary else json.loads(result.stdout or b"null")

    def tag_commit(self, version):
        ref = self.request(f"git/ref/tags/{version}")
        if ref is None:
            return None
        obj = ref["object"]
        for _ in range(10):
            if obj["type"] == "commit":
                return obj["sha"]
            if obj["type"] != "tag":
                break
            obj = self.request(f"git/tags/{obj['sha']}")["object"]
        raise ValueError("Tag verwijst niet naar een commit.")


def prepare(api, version: str, sha: str, assets: dict[str, Path], notes: str):
    if not re.fullmatch(VERSION, version) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Ongeldige versie of commit.")
    tag = api.tag_commit(version)
    if tag is not None and tag != sha:
        raise ValueError("Bestaande tag verwijst naar een andere commit.")
    matches = []
    page = 1
    while True:
        releases = api.request(f"releases?per_page=100&page={page}")
        matches.extend(item for item in releases if item["tag_name"] == version)
        if len(releases) < 100:
            break
        page += 1
    if len(matches) > 1:
        raise ValueError("Meerdere releases voor dezelfde versie.")
    release = matches[0] if matches else None
    present = set()
    seen = set()
    failed = []
    if release is not None:
        if not release["draft"] or release["target_commitish"] != sha or tag != sha:
            raise ValueError("Alleen een conceptrelease voor dezelfde tag en commit mag hervatten.")
        if release["body"].strip() != notes.strip():
            raise ValueError("Bestaande releasebeschrijving wijkt af.")
        page = 1
        while True:
            existing = api.request(f"releases/{release['id']}/assets?per_page=100&page={page}")
            for asset in existing:
                name = asset["name"]
                if name not in assets or name in seen:
                    raise ValueError("Onbekende of dubbele release-asset.")
                seen.add(name)
                if asset["state"] == "starter" and asset["size"] == 0:
                    failed.append(asset["id"])
                    continue
                if asset["state"] != "uploaded":
                    raise ValueError("Onvolledige release-asset.")
                content = api.request(f"releases/assets/{asset['id']}", binary=True)
                if content != assets[name].read_bytes():
                    raise ValueError(f"Bestaande asset wijkt af: {name}")
                present.add(name)
            if len(existing) < 100:
                break
            page += 1
    # Alle bestaande objecten zijn gecontroleerd vóór de eerste mutatie.
    if tag is None:
        api.request("git/refs", method="POST", payload={"ref": f"refs/tags/{version}", "sha": sha})
    if release is None:
        release = api.request(
            "releases",
            method="POST",
            payload={
                "tag_name": version,
                "target_commitish": sha,
                "name": version,
                "body": notes,
                "draft": True,
                "prerelease": False,
            },
        )
    for asset_id in failed:
        api.request(f"releases/assets/{asset_id}", method="DELETE")
    upload = release["upload_url"].split("{")[0]
    for name, path in assets.items():
        if name not in present:
            asset = api.request(f"{upload}?name={name}", method="POST", file=path)
            if asset["state"] != "uploaded" or asset["name"] != name:
                raise ValueError(f"Upload is niet volledig: {name}")
            if api.request(f"releases/assets/{asset['id']}", binary=True) != path.read_bytes():
                raise ValueError(f"Geüploade asset wijkt af: {name}")
    return release["html_url"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "package", "prepare"))
    parser.add_argument("--version")
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repository")
    args = parser.parse_args()
    if args.command == "check":
        check_version(lambda name: Path(name).read_text(), args.version)
        print("Versies en gedateerde changelogsectie komen overeen.")
    elif args.command == "package":
        if not args.version or not args.output:
            parser.error("package vereist --version en --output")
        print(package(args.revision, args.version, args.output))
    else:
        if not args.version or not args.output or not args.repository:
            parser.error("prepare vereist --version, --output en --repository")
        # Bouw opnieuw uit dezelfde Git-commit; vertrouw geen externe artefacten.
        sha = git("rev-parse", "HEAD").decode().strip()
        package(sha, args.version, args.output)
        assets = {
            name: args.output / name
            for name in (
                APP,
                f"ons-escalatielog-audit-{args.version}.zip",
                "SHA256SUMS.txt",
            )
        }
        print(
            prepare(
                GitHub(args.repository),
                args.version,
                sha,
                assets,
                (args.output / "release-notes.md").read_text(),
            )
        )


if __name__ == "__main__":
    main()
