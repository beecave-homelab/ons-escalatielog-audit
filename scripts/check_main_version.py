"""Require a version bump and release notes for application changes to main."""

from __future__ import annotations

import argparse
import re
import subprocess

from check_release_version import APP, check_version, one


def section(changelog: str, version: str) -> str:
    """Read only the section for the chosen version, including its date."""
    match = re.search(
        rf"^## \[{re.escape(version)}\].*?(?=^## |\Z)",
        changelog,
        re.MULTILINE | re.DOTALL,
    )
    return match[0].strip() if match else ""


def check_change(read_base, read_head, changed: set[str]) -> bool:
    """Documentation-, test- and CI-only changes need no product version bump."""
    if APP not in changed:
        return False
    old, _ = check_version(read_base)
    new, _ = check_version(read_head, release=True)
    if tuple(map(int, new.split("."))) <= tuple(map(int, old.split("."))):
        raise ValueError("Een applicatiewijziging naar main vereist een hogere SemVer.")
    if section(read_base("CHANGELOG.md"), new) == section(read_head("CHANGELOG.md"), new):
        raise ValueError("Voeg de changelogsectie voor de nieuwe versie toe of werk deze bij.")
    packages = read_head("uv.lock").split("[[package]]")
    package = [p for p in packages if re.search(r'^name = "ons-escalatielog-audit"$', p, re.M)]
    if len(package) != 1 or one(r'^version = "([^"]+)"', package[0], "lockversie") != new:
        raise ValueError("De projectversie in uv.lock moet gelijk zijn aan APP_VERSION.")
    return True


def git(*args: str) -> bytes:
    """Let missing Git refs and files fail explicitly."""
    return subprocess.check_output(["git", *args])


def check_refs(base: str, head: str = "HEAD") -> bool:
    """Compare complete Git trees, including a deleted or renamed app."""
    if re.fullmatch(r"0+", base):
        raise ValueError(
            "De basis is de null-SHA: een push die main aanmaakt of herstelt heeft "
            "geen vorige commit. De versiecontrole faalt daarom bewust; vergelijk "
            "handmatig met de laatst uitgebrachte versie."
        )
    base_sha = (
        git("rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}").decode().strip()
    )
    head_sha = (
        git("rev-parse", "--verify", "--end-of-options", f"{head}^{{commit}}").decode().strip()
    )
    changed = set(
        git("diff", "--no-renames", "--name-only", "-z", base_sha, head_sha, "--")
        .decode()
        .rstrip("\0")
        .split("\0")
    )
    return check_change(
        lambda name: git("show", f"{base_sha}:{name}").decode(),
        lambda name: git("show", f"{head_sha}:{name}").decode(),
        changed,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verplicht versie en releasebeschrijving bij applicatiewijzigingen naar main."
    )
    parser.add_argument("--base", required=True, help="Doelbranch-SHA vóór de wijziging")
    parser.add_argument("--head", default="HEAD", help="Te controleren commit (standaard HEAD)")
    args = parser.parse_args()
    if check_refs(args.base, args.head):
        print("Applicatiewijziging: hogere versie, lockfile en releasechangelog gecontroleerd.")
    else:
        print("Geen applicatiewijziging: geen verplichte version bump.")


if __name__ == "__main__":
    main()
