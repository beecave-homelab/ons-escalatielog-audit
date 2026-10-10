"""HTTP-regressie onder het Pages-projectpad, uitsluitend met synthetische data."""

import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

from playwright.sync_api import sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser


class PagesHandler(SimpleHTTPRequestHandler):
    extensions_map: ClassVar[dict[str, str]] = {".html": "text/html; charset=utf-8"}

    def end_headers(self):
        self.send_header("Cache-Control", "max-age=600")
        super().end_headers()

    def log_message(self, *_args):
        pass


def test_http_project_path_preserves_analysis_and_local_exports(tmp_path: Path):
    app = "escalatielog-audit-webui.html"
    project = tmp_path / "ons-escalatielog-audit"
    project.mkdir()
    content = (ROOT / app).read_bytes()
    (project / app).write_bytes(content)
    handler = functools.partial(PagesHandler, directory=str(tmp_path))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}/ons-escalatielog-audit/"
            with sync_playwright() as playwright:
                browser = launch_browser(playwright)
                page = browser.new_page(accept_downloads=True)
                errors, requests = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on(
                    "console",
                    lambda message: (
                        errors.append(message.text) if message.type == "error" else None
                    ),
                )
                page.on("request", lambda request: requests.append(request.url))
                response = page.goto(base + app, wait_until="networkidle")
                assert response.status == 200
                assert response.headers["content-type"] == "text/html; charset=utf-8"
                assert response.body() == content
                page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
                page.locator("#analyzeBtn").click()
                page.locator("#workspace.show").wait_for(timeout=30_000)
                assert page.evaluate(
                    """() => {const r=state.result;return [r.allRows.length,r.systemRows.length,
                    r.duplicateRows.length,r.auditRows.length,r.employees.length,r.clients.length,
                    r.locations.length,r.auditRows.filter(x=>x.notActivated).length,
                    r.auditRows.filter(x=>x.started&&isNight(x.started.hour,23,6)).length,
                    r.signalCounts.get('LATE_ACTIVATIE'),r.signalCounts.get('ONGELDIGE_ACTIVATIE'),
                    r.auditRows.filter(x=>x.reEscalationMinutes!==null).length,
                    r.auditRows.filter(x=>x.veryFastMinutes!==null).length,
                    r.attention.length,r.bursts.length,r.clientClusters.length]}"""
                ) == [2000, 156, 42, 1802, 250, 558, 40, 310, 544, 1391, 66, 0, 0, 1790, 0, 5]
                page.evaluate("openDrilldown('HTTP-test',state.result.auditRows.slice(0,2))")
                with page.expect_download() as csv_info:
                    page.locator("#drillCsvBtn").click()
                csv_info.value.save_as(tmp_path / "synthetic.csv")
                assert len((tmp_path / "synthetic.csv").read_text().splitlines()) == 3
                page.locator("#drillCloseBtn").click()
                with page.expect_download() as report_info:
                    page.evaluate("exportReport()")
                report_info.value.save_as(tmp_path / "synthetic-report.html")
                assert "<html" in (tmp_path / "synthetic-report.html").read_text()
                assert not errors
                assert requests == [base + app]
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
