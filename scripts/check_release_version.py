"""Controleer de applicatieversie en bijbehorende changelogsectie."""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

VERSION = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
APP = "escalatielog-audit-webui.html"


def one(pattern: str, text: str, name: str) -> str:
    matches = re.findall(pattern, text, re.MULTILINE)
    if len(matches) != 1:
        raise ValueError(f"Verwacht precies één {name}.")
    return matches[0]


def check_version(read, version: str | None = None, *, release: bool = False) -> tuple[str, str]:
    """Gewone CI staat ongepubliceerde wijzigingen toe; releasevoorbereiding blokkeert ze."""
    app = one(r"const APP_VERSION\s*=\s*[\"\']([^\"\']+)[\"\']", read(APP), "APP_VERSION")
    project = one(r'^version\s*=\s*"([^"]+)"', read("pyproject.toml"), "project.version")
    badge = one(r"badge/version-([^-]+)-", read("README.md"), "versiebadge")
    if not re.fullmatch(VERSION, app) or not (app == project == badge):
        raise ValueError("APP_VERSION, project.version en README moeten dezelfde SemVer bevatten.")
    if version is not None and (not re.fullmatch(VERSION, version) or version != app):
        raise ValueError("De gekozen releaseversie wijkt af of heeft geen geldig SemVer-formaat.")
    changelog = read("CHANGELOG.md")
    headings = list(re.finditer(r"^## \[([^\]]+)\](.*)$", changelog, re.MULTILINE))
    sections = {}
    for index, heading in enumerate(headings):
        name = heading[1]
        if name in sections:
            raise ValueError(f"Dubbele changelogsectie: {name}")
        end = headings[index + 1].start() if index + 1 < len(headings) else len(changelog)
        sections[name] = (heading[2], changelog[heading.end() : end].strip())
    if app not in sections:
        raise ValueError("De gedateerde changelogsectie ontbreekt.")
    suffix, notes = sections[app]
    if not re.fullmatch(r" - \d{4}-\d{2}-\d{2}", suffix):
        raise ValueError("De changelogsectie moet een datum bevatten.")
    date.fromisoformat(suffix[3:])
    if not notes:
        raise ValueError("De releasebeschrijving is leeg.")
    pending = sections.get("Nog niet uitgebracht", ("", ""))[1]
    if release and pending:
        raise ValueError("Koppel wijzigingen onder Nog niet uitgebracht eerst aan een versie.")
    return app, notes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version")
    parser.add_argument(
        "--release", action="store_true", help="Blokkeer ongepubliceerde wijzigingen"
    )
    args = parser.parse_args()
    check_version(lambda name: Path(name).read_text(), args.version, release=args.release)
    print("Versies en gedateerde changelogsectie komen overeen.")


if __name__ == "__main__":
    main()
