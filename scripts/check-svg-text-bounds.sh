#!/usr/bin/env bash
set -euo pipefail

# Script Description: Check that all text in docs/assets/*.svg stays within the viewBox.
# Author: beecave-homelab
# Version: 0.1.0
# License: MIT
# Creation Date: 21/09/2026
# Last Modified: 21/10/2026
# Usage: scripts/check-svg-text-bounds.sh [svg-path...]  (default: docs/assets/*.svg)
#
# Prevents a regression of issue #10 (labels clipped mid-word).
# Text is measured in root coordinates, so transforms on <g> count.

cd "$(dirname "$0")/.."

python - "$@" <<'PY'
import os
import shutil
import sys
from pathlib import Path

from playwright.sync_api import Error, sync_playwright

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


def launch_browser(pw):
    if executable := os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
        return pw.chromium.launch(executable_path=executable, headless=True)
    failures = []
    for channel in ("chrome", "msedge"):
        try:
            return pw.chromium.launch(channel=channel, headless=True)
        except Error as error:
            failures.append(f"{channel}: {error.message.splitlines()[0]}")
    for executable in (shutil.which("chromium"), shutil.which("chromium-browser")):
        if not executable:
            continue
        try:
            return pw.chromium.launch(executable_path=executable, headless=True)
        except Error as error:
            failures.append(f"{executable}: {error.message.splitlines()[0]}")
    try:
        return pw.chromium.launch(headless=True)
    except Error as error:
        failures.append(f"playwright-chromium: {error.message.splitlines()[0]}")
    print(
        "Geen bruikbare Chrome-, Edge- of Chromium-installatie gevonden. "
        + "; ".join(failures),
        file=sys.stderr,
    )
    sys.exit(2)


failures = []
with sync_playwright() as pw:
    browser = launch_browser(pw)
    for path in files:
        page = browser.new_page()
        page.goto(path.resolve().as_uri())
        problems = page.evaluate(
            """() => {
              const svg = document.querySelector("svg");
              if (!svg) return [{t: "<geen svg-root>"}];
              const vb = svg.viewBox.baseVal;
              if (!vb.width || !vb.height) return [{t: "geen viewBox"}];
              const bad = [];
              for (const t of svg.querySelectorAll("text")) {
                const m = svg.getScreenCTM().inverse().multiply(t.getScreenCTM());
                const bb = t.getBBox();
                const xs = [], ys = [];
                for (const [x, y] of [[bb.x, bb.y], [bb.x + bb.width, bb.y],
                                     [bb.x, bb.y + bb.height],
                                     [bb.x + bb.width, bb.y + bb.height]]) {
                  const p = new DOMPoint(x, y).matrixTransform(m);
                  xs.push(p.x);
                  ys.push(p.y);
                }
                const minx = Math.min(...xs), maxx = Math.max(...xs);
                const miny = Math.min(...ys), maxy = Math.max(...ys);
                if (minx < vb.x - 0.01 || maxx > vb.x + vb.width + 0.01
                    || miny < vb.y - 0.01 || maxy > vb.y + vb.height + 0.01) {
                  bad.push({t: t.textContent.trim(),
                            minx, maxx, miny, maxy,
                            vbx: vb.x, vby: vb.y, vbw: vb.width, vbh: vb.height});
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
            if "minx" not in p:
                print(f"[FAIL] {path}: {p['t']}")
            else:
                print(
                    f"[FAIL] {path}: tekst buiten viewBox: {p['t']!r} "
                    f"(tekst x=[{p['minx']:.2f}..{p['maxx']:.2f}] "
                    f"y=[{p['miny']:.2f}..{p['maxy']:.2f}]; "
                    f"viewBox x=[{p['vbx']}..{p['vbx'] + p['vbw']}] "
                    f"y=[{p['vby']}..{p['vby'] + p['vbh']}])"
                )
    sys.exit(1)

print(f"[svg-tekstcontrole] {len(files)} SVG-bestanden gecontroleerd: alle tekst binnen de viewBox.")
PY
