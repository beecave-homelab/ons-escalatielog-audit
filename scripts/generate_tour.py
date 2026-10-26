"""Build the offline training artifact from the current app and synthetic fixture."""

import argparse
import base64
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "escalatielog-audit-rondleiding.html"


def validate_references(html: str, script: str, references: dict) -> None:
    """Validate authored control names and targets before building the guide."""

    class Controls(HTMLParser):
        def __init__(self):
            super().__init__()
            self.labels = {}
            self.current = None

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "button":
                self.current = "#" + attrs.get("id", "")
                if "tab" in attrs.get("class", "").split():
                    self.current = "#view-tab-" + attrs["data-view"]
                self.labels[self.current] = ""

        def handle_data(self, data):
            if self.current:
                self.labels[self.current] += data

        def handle_endtag(self, tag):
            if tag == "button":
                self.current = None

    controls = Controls()
    controls.feed(html)
    dynamic = {
        '#findingList [data-finding="0"]': "Bronregels",
        "#tourNext": "Zelf oefenen",
        "#tourResume": "Toon huidige stap",
        "#rerunBtn": "Analyse opnieuw uitvoeren",
    }
    used = set(re.findall(r"\[\[([-\w]+)\]\]", script))
    for key in used:
        if key not in references:
            raise ValueError(f"Rondleiding: onbekende knopverwijzing: {key}")
    for key, ref in references.items():
        label = " ".join(controls.labels.get(ref["selector"], "").split())
        anchor = ref["selector"].split()[0]
        if ref["selector"] not in controls.labels and f'id="{anchor[1:]}"' not in html:
            raise ValueError(f"Rondleiding: knopnaam of doel gewijzigd: {key}")
        if ref["label"] != label and dynamic.get(ref["selector"]) != ref["label"]:
            raise ValueError(f"Rondleiding: knopnaam of doel gewijzigd: {key}")


def build_tour() -> str:
    """Keep the app as the only source of analysis and UI behavior."""
    html = (ROOT / "escalatielog-audit-webui.html").read_text()
    layer = ROOT / "scripts/tour"
    script = (layer / "tour.js").read_text()
    # Literal selectors also form the contract checked before generation.
    anchors = re.findall(r'anchor: "(#[-\w]+)"', script)
    dynamic = {"#findingList", "#drillBody", "#set-activationDelayThresholdMinutes"}
    for anchor in anchors:
        if anchor not in dynamic and f'id="{anchor[1:]}"' not in html:
            raise ValueError(f"Rondleiding: DOM-anker ontbreekt: {anchor}")
    references = json.loads((layer / "references.json").read_text())
    validate_references(html + (layer / "body.html").read_text(), script, references)
    script = script.replace("__TOUR_REFERENCES__", json.dumps(references, ensure_ascii=False))
    replacements = {
        "async function loadFile(file){": (
            "async function loadFile(file){\n"
            "  if(file!==tourFixture){setStatus('Deze oefenomgeving gebruikt alleen "
            "de ingebouwde verzonnen gegevens.','error');return;}"
        ),
        next(
            line for line in html.splitlines() if line.startswith("function importSettings(file){")
        ): (
            "function importSettings(file){setStatus('Instellingen importeren is "
            "uitgeschakeld in de oefenomgeving.','error');}"
        ),
    }
    for old, new in replacements.items():
        if html.count(old) != 1:
            raise ValueError(f"Rondleiding: applicatieaansluiting gewijzigd: {old}")
        html = html.replace(old, new)
    fixture = base64.b64encode(
        (ROOT / "tests/fixtures/synthetic-escalatielog.xlsx").read_bytes()
    ).decode("ascii")
    script = script.replace("__FIXTURE_BASE64__", fixture)
    html = html.replace(
        "  </head>",
        '    <style id="tourStyles">\n'
        + (layer / "style.css").read_text()
        + "    </style>\n  </head>",
    )
    html = html.replace("  <body>", "  <body>\n" + (layer / "body.html").read_text())
    html = html.replace("  </body>", "    <script>\n" + script + "    </script>\n  </body>")
    html = html.replace(
        "<title>Ons Escalatielog Audit</title>",
        "<title>Rondleiding bij Ons Escalatielog Audit</title>",
    )
    return subprocess.run(
        [sys.executable, "-m", "djlint", "-", "--reformat", "--quiet"],
        input=html,
        text=True,
        capture_output=True,
        check=True,
        cwd=ROOT,
    ).stdout


def main() -> None:
    """Generate or verify the committed, reproducible training artifact."""
    parser = argparse.ArgumentParser(description="Genereer de zelfstandige offline rondleiding.")
    parser.add_argument(
        "--check", action="store_true", help="Controleer of het bestand actueel is."
    )
    args = parser.parse_args()
    html = build_tour()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != html:
            raise SystemExit("Rondleiding is verouderd. Voer scripts/generate_tour.py uit.")
        print("Rondleiding is actueel.")
    else:
        OUTPUT.write_text(html)
        print(f"Rondleiding gegenereerd: {OUTPUT.name}")


if __name__ == "__main__":
    main()
