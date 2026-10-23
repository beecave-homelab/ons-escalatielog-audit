"""Atomic re-analysis and analysis settings in the report (issue #50)."""

import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser


def load_fixture(page) -> None:
    page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
    page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
    page.locator("#analyzeBtn").click()
    page.locator("#workspace.show").wait_for(timeout=30_000)


def export_report(page, report: Path) -> str:
    with page.expect_download() as download_info:
        page.evaluate("exportReport()")
    download_info.value.save_as(report)
    return report.read_text(encoding="utf-8")


def settings_row(html: str, label: str) -> str:
    match = re.search(r"<td>" + re.escape(label) + r"</td><td>(.*?)</td>", html, re.DOTALL)
    assert match, f"Instellingsregel ontbreekt in rapport: {label}"
    return match.group(1)


def test_rerun_analyze_failure_keeps_previous_state(tmp_path: Path) -> None:
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        load_fixture(page)
        before = page.evaluate(
            """() => {
              window.__before=state.result;
              window.__settingsJson=JSON.stringify(state.settings);
              window.__runAt=state.analysisRunAt.getTime();
              window.__runAtObj=state.analysisRunAt;
              return {
                kpis: document.querySelector('#kpis').textContent,
                night: state.result.attention.filter(r=>r.signals.includes('NACHT')).length,
              };
            }"""
        )
        assert before["night"] == 544
        page.locator("#settingsBtn").click()
        page.locator("#set-signalNight").uncheck()
        page.locator("#set-burstWindowMinutes").fill("45")
        page.evaluate(
            "(()=>{window.__aq=analyzeQuality;"
            "analyzeQuality=()=>{throw new Error('Geforceerde testfout')}})()"
        )
        page.locator("#rerunBtn").click()
        expect(page.locator("#status")).to_have_class("status error")
        assert "Geforceerde testfout" in page.locator("#status").text_content()
        kept = page.evaluate(
            """() => ({
              sameResult: state.result===window.__before,
              settings: JSON.stringify(state.settings),
              runAt: state.analysisRunAt.getTime(),
              sameRunAtObj: state.analysisRunAt===window.__runAtObj,
              night: state.result.attention.filter(r=>r.signals.includes('NACHT')).length,
              kpis: document.querySelector('#kpis').textContent,
              loading: document.querySelector('#loading').classList.contains('show'),
            })"""
        )
        assert kept["sameResult"]
        assert kept["settings"] == before_settings(page)
        assert kept["runAt"] == page.evaluate("window.__runAt")
        assert kept["sameRunAtObj"]
        assert kept["night"] == 544
        assert kept["kpis"] == before["kpis"]
        assert not kept["loading"]
        assert not page.locator("#set-signalNight").is_checked()
        html = export_report(page, tmp_path / "rapport-mislukt.html")
        assert settings_row(html, "Burstvenster (min.)") == "60"
        assert settings_row(html, "Signaal: nacht") == "true"

        page.evaluate("(()=>{analyzeQuality=window.__aq})()")
        page.locator("#rerunBtn").click()
        expect(page.locator("#status")).to_have_class("status ok")
        assert "Analyse opnieuw uitgevoerd" in page.locator("#status").text_content()
        applied = page.evaluate(
            """() => ({
              signalNight: state.settings.signalNight,
              burstWindowMinutes: state.settings.burstWindowMinutes,
              newResult: state.result!==window.__before,
              newRunAt: state.analysisRunAt!==window.__runAtObj
                && state.analysisRunAt.getTime()!==window.__runAt,
            })"""
        )
        assert applied["signalNight"] is False
        assert applied["burstWindowMinutes"] == 45
        assert applied["newResult"]
        assert applied["newRunAt"]
        html = export_report(page, tmp_path / "rapport-geslaagd.html")
        assert settings_row(html, "Burstvenster (min.)") == "45"
        assert settings_row(html, "Signaal: nacht") == "false"
        browser.close()


def before_settings(page) -> str:
    return page.evaluate("window.__settingsJson")


def test_rerun_render_failure_rolls_back(tmp_path: Path) -> None:
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        load_fixture(page)
        before = page.evaluate(
            """() => {
              window.__before=state.result;
              window.__settingsJson=JSON.stringify(state.settings);
              window.__runAt=state.analysisRunAt.getTime();
              return document.querySelector('#kpis').textContent;
            }"""
        )
        page.locator("#settingsBtn").click()
        page.locator("#set-burstWindowMinutes").fill("45")
        page.evaluate(
            "(()=>{window.__rdd=renderDeepDive;window.__first=true;"
            "renderDeepDive=(...a)=>{if(window.__first){window.__first=false;"
            "throw new Error('Geforceerde renderfout')}return window.__rdd(...a)}})()"
        )
        page.locator("#rerunBtn").click()
        expect(page.locator("#status")).to_have_class("status error")
        assert "Geforceerde renderfout" in page.locator("#status").text_content()
        kept = page.evaluate(
            """() => ({
              sameResult: state.result===window.__before,
              settings: JSON.stringify(state.settings),
              runAt: state.analysisRunAt.getTime(),
              kpis: document.querySelector('#kpis').textContent,
              loading: document.querySelector('#loading').classList.contains('show'),
            })"""
        )
        assert kept["sameResult"]
        assert kept["settings"] == before_settings(page)
        assert kept["runAt"] == page.evaluate("window.__runAt")
        assert kept["kpis"] == before
        assert not kept["loading"]
        assert page.locator("#set-burstWindowMinutes").input_value() == "60"
        page.evaluate("(()=>{renderDeepDive=window.__rdd})()")
        browser.close()


def test_analyze_is_pure_and_report_uses_result_settings(tmp_path: Path) -> None:
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        load_fixture(page)
        purity = page.evaluate(
            """() => {
              const settings=JSON.stringify(state.settings);
              const signals=JSON.stringify(state.rawRows.map(r=>r.signals));
              const result=analyze(state.rawRows,{...DEFAULT_SETTINGS,
                signalNight:false,activeAccessMinutes:1});
              return {
                settingsKept: JSON.stringify(state.settings)===settings,
                rowsKept: JSON.stringify(state.rawRows.map(r=>r.signals))===signals,
                resultSettings: result.explanations.settings.activeAccessMinutes,
              };
            }"""
        )
        assert purity["settingsKept"]
        assert purity["rowsKept"]
        assert purity["resultSettings"] == 1
        page.evaluate(
            "(()=>{state.settings={...state.settings,"
            "burstWindowMinutes:999,activeAccessMinutes:1}})()"
        )
        html = export_report(page, tmp_path / "rapport-instellingen.html")
        assert settings_row(html, "Burstvenster (min.)") == "60"
        assert "actieve toegang 840 min." in html
        page.evaluate("render()")
        assert (
            "840 min. aangenomen toegang"
            in page.locator("#analysisBanner .meta-chip").first.text_content()
        )
        browser.close()
