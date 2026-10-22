"""Measure analyze() and render() times of the webui on a large synthetic set.

The page deterministically builds 50,000 rows with 3,000 employees and
20,000 clients (plus 40 locations) via normalizeRows(). Per run the
script measures the duration of analyze(), render() and the sub-renders.
The output is JSON with all runs and the median per phase. No files are
read from escalatielogs/ or exports/.

Usage:
  uv run python scripts/measure_render_performance.py
  uv run python scripts/measure_render_performance.py --html path/to/webui.html --runs 5
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BUILD = """() => {
  let seed = 51;
  const rnd = n => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed % n; };
  const p2 = n => String(n).padStart(2, '0');
  const reasons = Array.from({length: 30}, (_, i) => `Reden ${i + 1}`);
  const teams = Array.from({length: 60}, (_, i) => `Team ${i + 1}`);
  const roles = Array.from({length: 8}, (_, i) => `Deskundigheid ${i + 1}`);
  const lines = [REQUIRED_HEADERS];
  for (let i = 0; i < 50000; i++) {
    const e = i < 3000 ? i : rnd(3000), c = i < 20000 ? i : rnd(20000);
    const client = i < 20000 || rnd(10) > 0;
    const day = 1 + rnd(31), hour = rnd(24), minute = rnd(60);
    const start = `${p2(day)}-05-2026, ${p2(hour)}:${p2(minute)}:00`;
    const act = rnd(10) < 7
      ? `${p2(day)}-05-2026, ${p2(hour)}:${p2(Math.min(59, minute + 1 + rnd(5)))}:00`
      : 'niet geactiveerd';
    const row = {'Gebruiker': `Medewerker ${e}`, 'Medewerkernummer': `E${e}`,
      'Medewerkersteam': teams[e % 60], 'Deskundigheid medewerker': roles[e % 8],
      'Gebruikersnaam': `mw${e}`, 'Escalatie reden': reasons[rnd(30)],
      'Tijdsduur (min.)': '840',
      'Escalatiedoel type': client ? 'Cliënt' : 'Locatie',
      'Escalatiedoel naam': client ? `Cliënt ${c}` : `Locatie ${rnd(40)}`,
      'Escalatiedoel identificatienummer': client ? `C${c}` : `L${rnd(40)}`,
      'Hoofdlocatie cliënt': client ? `Locatie ${c % 40}` : '',
      'Gestart op': start, 'Geactiveerd op': act, 'Bron': 'Synthetisch'};
    lines.push(REQUIRED_HEADERS.map(k => row[k]));
  }
  window.__rows = normalizeRows(lines, 0);
  const s = window.__rows;
  return {rows: s.length,
    employees: new Set(s.map(r => r.employeeNumber)).size,
    clients: new Set(s.filter(r => r.targetType === 'Cliënt').map(r => r.targetId)).size};
}"""

WRAP = """() => {
  window.__t = {};
  for (const name of ['renderOverview', 'renderTables', 'renderTime', 'renderDeepDive',
      'renderAuditLogic', 'renderSettings', 'renderEvidenceLinks']) {
    const orig = window[name];
    window[name] = function (...args) {
      const t0 = performance.now();
      try { return orig.apply(this, args); }
      finally { window.__t[name] = (window.__t[name] || 0) + performance.now() - t0; }
    };
  }
}"""

RUN = """() => {
  window.__t = {};
  const t0 = performance.now();
  state.result = analyze(window.__rows, {...DEFAULT_SETTINGS});
  const t1 = performance.now();
  render();
  const t2 = performance.now();
  return {analyze: t1 - t0, render: t2 - t1, ...window.__t};
}"""


def measure(html: Path, runs: int) -> dict:
    """Open the webui in Chromium and measure the given number of runs."""
    sys.path.insert(0, str(ROOT / "tests"))
    from playwright.sync_api import sync_playwright
    from test_report_layout import launch_browser

    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(html.as_uri())
        shape = page.evaluate(BUILD)
        page.evaluate(WRAP)
        results = [page.evaluate(RUN) for _ in range(runs)]
        version = page.evaluate("APP_VERSION")
        browser.close()
    median = {k: round(statistics.median(r[k] for r in results)) for k in results[0]}
    return {
        "html": str(html),
        "version": version,
        "shape": shape,
        "runs": [{k: round(v) for k, v in r.items()} for r in results],
        "median_ms": median,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Meet analyze()- en render()-tijden van de webui op een grote synthetische set."
    )
    parser.add_argument("--html", type=Path, default=ROOT / "escalatielog-audit-webui.html")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs moet minimaal 1 zijn.")
    report = measure(args.html.resolve(), args.runs)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
