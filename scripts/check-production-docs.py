#!/usr/bin/env python3
"""Beperk documentatie op main tot de gebruikte productiedocumentatie."""

import argparse
import subprocess
from pathlib import Path

ALLOWED = frozenset(
    {
        "docs/berekeningen-en-patroonherkenning.md",
        "docs/assets/analyseketen.svg",
        "docs/assets/auditpopulatie.svg",
        "docs/assets/her-escalatie.svg",
        "docs/assets/peervergelijking.svg",
        "docs/assets/signaaloverlap.svg",
        "docs/assets/tijdvensters.svg",
    }
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", help="Controleer een Git-boom in plaats van lokale bestanden")
    args = parser.parse_args()
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    if args.revision:
        entries = subprocess.check_output(
            ["git", "ls-tree", "-rz", args.revision, "--", "docs"], cwd=root
        )
        paths = set()
        invalid = set()
        for entry in entries.split(b"\0"):
            if not entry:
                continue
            metadata, name = entry.decode().split("\t", 1)
            paths.add(name)
            if metadata.split()[0] not in {"100644", "100755"}:
                invalid.add(name)
    else:
        paths = {
            p.relative_to(root).as_posix()
            for p in (root / "docs").rglob("*")
            if not p.is_dir() or p.is_symlink()
        }
        invalid = {name for name in paths if (root / name).is_symlink()}
    for name in sorted(paths - ALLOWED):
        print(f"Niet toegestaan in productiedocumentatie: {name}")
    for name in sorted(ALLOWED - paths):
        print(f"Ontbrekende productiedocumentatie: {name}")
    for name in sorted(invalid):
        print(f"Geen regulier documentatiebestand: {name}")
    if paths != ALLOWED or invalid:
        return 1
    print("Productiedocumentatie: alleen de zeven toegestane bestanden aanwezig.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
