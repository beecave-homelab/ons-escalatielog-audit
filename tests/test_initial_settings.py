"""Settings are reachable before the first analysis and are applied."""

from playwright.sync_api import expect, sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser


def test_initial_settings_survive_file_selection_and_apply() -> None:
    """A first analysis uses the pre-filled thresholds and toggles."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        page.get_by_role("button", name="Instellingen", exact=True).filter(visible=True).click()
        expect(page.locator("#settingsGrid")).to_be_visible()
        expect(page.locator("#rerunBtn")).to_be_disabled()
        page.locator("#set-signalNight").uncheck()
        page.locator("#set-activationDelayThresholdMinutes").fill("0")
        page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
        expect(page.locator("#settingsGrid")).to_be_visible()
        expect(page.locator("#set-signalNight")).not_to_be_checked()
        expect(page.locator("#set-activationDelayThresholdMinutes")).to_have_value("0")
        expect(page.locator("#rerunBtn")).to_be_enabled()
        page.locator("#rerunBtn").click()
        expect(page.locator("#workspace")).to_have_class("workspace show", timeout=30_000)
        assert page.evaluate("state.result.explanations.settings.signalNight") is False
        assert (
            page.evaluate("state.result.explanations.settings.activationDelayThresholdMinutes") == 0
        )
        assert page.evaluate("state.result.attention.some(r=>r.signals.includes('NACHT'))") is False
        page.locator("#settingsBtn").click()
        expect(page.locator("#settingsGrid")).to_be_visible()
        expect(page.locator("#rerunBtn")).to_have_text("Analyse opnieuw uitvoeren")
        page.locator("#set-signalNight").check()
        page.locator("#rerunBtn").click()
        expect(page.locator("#status")).to_contain_text("Analyse opnieuw uitgevoerd")
        assert (
            page.evaluate("state.result.attention.filter(r=>r.signals.includes('NACHT')).length")
            == 544
        )
        browser.close()


def test_invalid_initial_settings_block_analysis_and_allow_retry() -> None:
    """Invalid input starts no analysis and stays available for correction."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
        page.get_by_role("button", name="Instellingen", exact=True).filter(visible=True).click()
        page.locator("#set-activeAccessMinutes").fill("0")
        page.locator("#analyzeBtn").click()
        expect(page.locator("#status")).to_have_class("status error")
        assert page.evaluate("state.result===null && state.settings.activeAccessMinutes===840")
        expect(page.locator("#workspace")).not_to_be_visible()
        expect(page.locator("#settingsGrid")).to_be_visible()
        page.locator("#set-activeAccessMinutes").fill("60")
        page.locator("#analyzeBtn").click()
        expect(page.locator("#workspace")).to_be_visible(timeout=30_000)
        assert page.evaluate("state.result.explanations.settings.activeAccessMinutes") == 60
        page.locator("#settingsBtn").click()
        page.locator("#set-activeAccessMinutes").fill("120")
        page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
        expect(page.locator("#settingsGrid")).to_be_visible()
        expect(page.locator("#set-activeAccessMinutes")).to_have_value("120")
        expect(page.locator("#rerunBtn")).to_have_text("Analyse uitvoeren")
        page.locator("#rerunBtn").click()
        expect(page.locator("#workspace")).to_be_visible(timeout=30_000)
        assert page.evaluate("state.result.explanations.settings.activeAccessMinutes") == 120
        browser.close()
