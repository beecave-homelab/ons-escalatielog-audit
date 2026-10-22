"""Measure the real inline script with CDP; report functions without a new quality gate."""

import pytest
from app_coverage import APP_COVERAGE, summarize_functions
from playwright.sync_api import sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser


def test_app_function_coverage__reports_synthetic_reference_scenario(request) -> None:
    """Measure loading, analysis, tabs, drilldown and the CSV/HTML export offline."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(accept_downloads=True)
        cdp = page.context.new_cdp_session(page)
        cdp.send("Profiler.enable")
        cdp.send("Profiler.startPreciseCoverage", {"callCount": True, "detailed": False})
        url = (ROOT / "escalatielog-audit-webui.html").as_uri()
        try:
            page.goto(url)
            page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
            page.locator("#analyzeBtn").click()
            page.wait_for_selector("#workspace.show")
            page.evaluate(
                """() => {
                  document.querySelectorAll('[data-view]').forEach(button=>button.click());
                  openDrilldown('Synthetisch voorbeeld',state.result.attention.slice(0,5));
                  closeDrilldown();
                }"""
            )
            for selector in ("#csvBtn", "#reportBtn"):
                with page.expect_download():
                    page.locator(selector).click()
            scripts = cdp.send("Profiler.takePreciseCoverage")["result"]
            report = summarize_functions(scripts, url)
            assert 0 < report["called"] <= report["total"]
            assert 0 < report["percentage"] <= 100
            # Missing output is a measurement error; the percentage is not a quality gate.
            assert any(
                script["url"] == url
                and any(function["functionName"] == "analyze" for function in script["functions"])
                for script in scripts
            )
            request.config.stash[APP_COVERAGE] = report
        finally:
            cdp.send("Profiler.stopPreciseCoverage")
            cdp.send("Profiler.disable")
            browser.close()


def test_summary__excludes_other_documents_and_uses_function_entry_count() -> None:
    """Other documents, anonymous wrappers and block counts are not app functions."""
    functions = [
        {"functionName": "", "ranges": [{"startOffset": 0, "endOffset": 90, "count": 1}]},
        {
            "functionName": "called",
            "ranges": [
                {"startOffset": 1, "endOffset": 40, "count": 2},
                {"startOffset": 10, "endOffset": 15, "count": 0},
            ],
        },
        {"functionName": "uncalled", "ranges": [{"startOffset": 41, "endOffset": 80, "count": 0}]},
        {"functionName": "noRanges", "ranges": []},
    ]
    scripts = [{"url": "app", "functions": functions}, {"url": "eval", "functions": functions}]
    assert summarize_functions(scripts, "app") == {
        "called": 1,
        "total": 2,
        "percentage": 50.0,
        "uncalled": ["uncalled"],
    }
    with pytest.raises(ValueError, match="Geen benoemde applicatiefuncties"):
        summarize_functions(scripts, "missing")


def test_terminal_report__names_measurement_scope_and_has_no_threshold() -> None:
    """The visible CI output names the scenario, the measurement and the existing Python gate."""
    from conftest import pytest_terminal_summary

    class Reporter:
        def __init__(self):
            self.lines = []

        def section(self, title):
            self.lines.append(title)

        def write_line(self, line):
            self.lines.append(line)

    class Config:
        stash = pytest.Stash()

    reporter, config = Reporter(), Config()
    pytest_terminal_summary(reporter, 0, config)
    assert not reporter.lines
    config.stash[APP_COVERAGE] = {
        "called": 1,
        "total": 2,
        "percentage": 50.0,
        "uncalled": ["uncalled"],
    }
    pytest_terminal_summary(reporter, 0, config)
    text = "\n".join(reporter.lines)
    assert "1/2" in text and "50.00%" in text and "uncalled" in text
    assert "geen regel-/branchdekking of volledige suitedekking" in text
    assert "85%-poort meet Python-testcode" in text
