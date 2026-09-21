#!/usr/bin/env bash
# Controleer dat alle tekst in docs/assets/*.svg binnen de viewBox valt.
# Voorkomt herhaling van issue #10: labels die midden in een woord afgekapt worden.
#
# Gebruik: scripts/check-svg-text-bounds.sh [pad-naar-svg...]  (default: docs/assets/*.svg)
set -euo pipefail

cd "$(dirname "$0")/.."

python - "$@" <<'PY'
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

patterns = sys.argv[1:] or ["docs/assets/*.svg"]
files = []
for pat in patterns:
    p = Path(pat)
    if p.is_file():
        files.append(p)
    else:
        files.extend(Path(".").glob(pat))
files = sorted(set(files))
if not files:
    print("Geen SVG-bestanden gevonden.", file=sys.stderr)
    sys.exit(2)

failures = []
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    for path in files:
        page = browser.new_page()
        page.goto(path.resolve().as_uri())
        problems = page.evaluate(
            """() => {
              const svg = document.querySelector("svg");
              if (!svg) return [{t: "<geen svg-root>", right: 0}];
              const vb = svg.viewBox.baseVal;
              const bad = [];
              for (const t of svg.querySelectorAll("text")) {
                const bb = t.getBBox();
                if (bb.x + bb.width > vb.width || bb.x < 0
                    || bb.y + bb.height > vb.height || bb.y < 0) {
                  bad.push({t: t.textContent.trim(), right: Math.round(bb.x + bb.width), bottom: Math.round(bb.y + bb.height), vbw: vb.width, vbh: vb.height});
                }
              }
              return bad;
            }"""
        )
        page.close()
        if problems:
            failures.append((path, problems))

    browser.close()

if failures:
    for path, problems in failures:
        for p in problems:
            print(f"[FAIL] {path}: tekst buiten viewBox: {p['t']!r} (rechterrand {p['right']}, onderrand {p['bottom']}, viewBox {p.get('vbw')}x{p.get('vbh')})")
    sys.exit(1)

print(f"[svg-tekstcontrole] {len(files)} SVG-bestanden gecontroleerd: alle tekst binnen de viewBox.")
PY
