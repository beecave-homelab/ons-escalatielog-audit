"""Instellingen importeren en exporteren als lokaal JSON-bestand (issue #87)."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser

SETTINGS_FILE_NAME = "escalatielog-audit-instellingen.json"


def open_settings(page) -> None:
    """Open het Instellingen-tabblad via de knop in het uploadvak."""
    page.get_by_role("button", name="Instellingen", exact=True).filter(visible=True).click()
    expect(page.locator("#settingsGrid")).to_be_visible()


def _valid_payload(overrides: dict | None = None) -> dict:
    payload = {
        "format": "escalatielog-audit-instellingen",
        "schemaVersion": 1,
        "settings": {
            "activeAccessMinutes": 120,
            "veryFastRepeatMinutes": 3,
            "nightStartHour": 22,
            "nightEndHour": 7,
            "employeeDailyVolumeThreshold": 20,
            "employeeUniqueClientsThreshold": 40,
            "clientUniqueEmployeesThreshold": 5,
            "clientUniqueTeamsThreshold": 4,
            "activationDelayThresholdMinutes": 1,
            "rareReasonMaxCount": 3,
            "excludeDuration30": True,
            "peerGroupMinSize": 4,
            "burstWindowMinutes": 30,
            "burstThreshold": 3,
            "clientClusterWindowMinutes": 90,
            "clientClusterEmployeeThreshold": 2,
            "clientClusterTeamThreshold": 1,
            "reasonConcentrationMinCount": 5,
            "signalNight": False,
            "signalWeekend": True,
            "signalNotActivated": False,
            "signalRareReason": True,
            "signalActivationDelay": False,
            "signalReEscalationActiveAccess": False,
            "signalVeryFastRepeat": False,
            "signalDataQuality": False,
            "signalEmployeeDailyVolume": False,
            "signalEmployeeUniqueClients": False,
            "signalClientUniqueEmployees": False,
            "signalClientUniqueTeams": False,
        },
    }
    if overrides:
        payload["settings"].update(overrides)
    return payload


def _write_settings_json(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "instellingen.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_export_import_roundtrip_before_analysis(tmp_path: Path) -> None:
    """Exporteren en importeren herstelt dezelfde formulierwaarden zonder bestand."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(accept_downloads=True)
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        open_settings(page)
        page.locator("#set-activeAccessMinutes").fill("60")
        page.locator("#set-signalNight").uncheck()
        page.locator("#set-nightStartHour").fill("22")
        page.locator("#set-nightEndHour").fill("7")
        with page.expect_download() as dl:
            page.locator("#exportSettingsBtn").click()
        download = dl.value
        assert download.suggested_filename == SETTINGS_FILE_NAME
        saved = tmp_path / SETTINGS_FILE_NAME
        download.save_as(saved)
        payload = json.loads(saved.read_text(encoding="utf-8"))
        assert payload["format"] == "escalatielog-audit-instellingen"
        assert payload["schemaVersion"] == 1
        assert payload["settings"]["activeAccessMinutes"] == 60
        assert payload["settings"]["signalNight"] is False
        assert payload["settings"]["nightStartHour"] == 22
        assert payload["settings"]["nightEndHour"] == 7
        page.locator("#set-activeAccessMinutes").fill("840")
        page.locator("#set-signalNight").check()
        page.locator("#set-nightStartHour").fill("23")
        page.locator("#set-nightEndHour").fill("6")
        page.locator("#settingsFileInput").set_input_files(saved)
        expect(page.locator("#set-activeAccessMinutes")).to_have_value("60")
        expect(page.locator("#set-signalNight")).not_to_be_checked()
        expect(page.locator("#set-nightStartHour")).to_have_value("22")
        expect(page.locator("#set-nightEndHour")).to_have_value("7")
        expect(page.locator("#status")).to_contain_text("Instellingen geïmporteerd")
        assert page.evaluate("state.result===null")
        assert page.evaluate("state.settings.activeAccessMinutes===840")
        browser.close()


def test_export_import_roundtrip_after_analysis(tmp_path: Path) -> None:
    """Exporteren en importeren werken na een uitgevoerde analyse."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(accept_downloads=True)
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
        page.locator("#analyzeBtn").click()
        page.locator("#workspace.show").wait_for(timeout=30_000)
        page.locator('.tab[data-view="settings"]').click()
        expect(page.locator("#rerunBtn")).to_have_text("Analyse opnieuw uitvoeren")
        page.locator("#set-activeAccessMinutes").fill("120")
        page.locator("#set-signalWeekend").check()
        with page.expect_download() as dl:
            page.locator("#exportSettingsBtn").click()
        saved = tmp_path / SETTINGS_FILE_NAME
        dl.value.save_as(saved)
        payload = json.loads(saved.read_text(encoding="utf-8"))
        assert payload["settings"]["activeAccessMinutes"] == 120
        assert payload["settings"]["signalWeekend"] is True
        applied_before = page.evaluate("state.settings.activeAccessMinutes")
        assert applied_before == 840
        weekend_before = page.evaluate("state.settings.signalWeekend")
        assert weekend_before is False
        page.locator("#set-activeAccessMinutes").fill("840")
        page.locator("#set-signalWeekend").uncheck()
        page.locator("#settingsFileInput").set_input_files(saved)
        expect(page.locator("#set-activeAccessMinutes")).to_have_value("120")
        expect(page.locator("#set-signalWeekend")).to_be_checked()
        expect(page.locator("#status")).to_contain_text("Analyse opnieuw uitvoeren")
        assert page.evaluate("state.settings.activeAccessMinutes===840")
        assert page.evaluate("state.settings.signalWeekend===false")
        assert page.evaluate("state.result!==null")
        browser.close()


def test_export_blocked_by_invalid_input(tmp_path: Path) -> None:
    """Ongeldige formulierwaarden blokkeren export met een zichtbare foutmelding."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(accept_downloads=True)
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        open_settings(page)
        page.locator("#set-activeAccessMinutes").fill("0")
        # De luisteraar moet actief zijn vóór de klik, anders vangt hij de
        # download van diezelfde klik nooit (zie de ronde-trip-tests hierboven).
        try:
            with page.expect_download(timeout=2_000) as download_info:
                page.locator("#exportSettingsBtn").click()
            raise AssertionError(
                "Export should not have produced a download, got "
                f"{download_info.value.suggested_filename!r}"
            )
        except PlaywrightTimeout:
            pass
        expect(page.locator("#status")).to_have_class("status error")
        expect(page.locator("#status")).to_contain_text("Exporteren mislukt")
        browser.close()


def test_import_rejects_invalid_json(tmp_path: Path) -> None:
    """Ongeldige JSON wordt afgewezen zonder gedeeltelijke wijzigingen."""
    bad = tmp_path / "bad.json"
    bad.write_text("not valid json {{{", encoding="utf-8")
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        open_settings(page)
        old_val = page.locator("#set-activeAccessMinutes").input_value()
        page.locator("#settingsFileInput").set_input_files(bad)
        expect(page.locator("#status")).to_have_class("status error")
        expect(page.locator("#set-activeAccessMinutes")).to_have_value(old_val)
        browser.close()


def test_import_rejects_unknown_schema_version(tmp_path: Path) -> None:
    """Een niet-ondersteunde formaatversie wordt afgewezen."""
    payload = _valid_payload()
    payload["schemaVersion"] = 99
    f = _write_settings_json(tmp_path, payload)
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        open_settings(page)
        page.locator("#settingsFileInput").set_input_files(f)
        expect(page.locator("#status")).to_have_class("status error")
        expect(page.locator("#status")).to_contain_text("Niet-ondersteunde formaatversie")
        browser.close()


def test_import_rejects_unknown_key(tmp_path: Path) -> None:
    """Onbekende instellingen worden afgewezen."""
    payload = _valid_payload()
    payload["settings"]["nonExistentSetting"] = 42
    f = _write_settings_json(tmp_path, payload)
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        open_settings(page)
        page.locator("#settingsFileInput").set_input_files(f)
        expect(page.locator("#status")).to_have_class("status error")
        expect(page.locator("#status")).to_contain_text("Onbekende instellingen")
        browser.close()


def test_import_rejects_missing_key(tmp_path: Path) -> None:
    """Ontbrekende instellingen worden afgewezen."""
    payload = _valid_payload()
    del payload["settings"]["activeAccessMinutes"]
    f = _write_settings_json(tmp_path, payload)
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        open_settings(page)
        page.locator("#settingsFileInput").set_input_files(f)
        expect(page.locator("#status")).to_have_class("status error")
        expect(page.locator("#status")).to_contain_text("Ontbrekende instellingen")
        browser.close()


def test_import_rejects_wrong_type(tmp_path: Path) -> None:
    """Verkeerde typen worden afgewezen."""
    payload = _valid_payload()
    payload["settings"]["signalNight"] = "yes"
    f = _write_settings_json(tmp_path, payload)
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        open_settings(page)
        page.locator("#settingsFileInput").set_input_files(f)
        expect(page.locator("#status")).to_have_class("status error")
        expect(page.locator("#status")).to_contain_text("booleaanse waarde")
        browser.close()


def test_import_rejects_out_of_range(tmp_path: Path) -> None:
    """Waarden buiten het toegestane bereik worden afgewezen."""
    payload = _valid_payload()
    payload["settings"]["nightStartHour"] = 25
    f = _write_settings_json(tmp_path, payload)
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        open_settings(page)
        page.locator("#settingsFileInput").set_input_files(f)
        expect(page.locator("#status")).to_have_class("status error")
        expect(page.locator("#status")).to_contain_text("buiten het toegestane bereik")
        browser.close()


def test_import_rejects_wrong_format_name(tmp_path: Path) -> None:
    """Onbekende formaatnaam wordt afgewezen."""
    payload = _valid_payload()
    payload["format"] = "something-else"
    f = _write_settings_json(tmp_path, payload)
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        open_settings(page)
        page.locator("#settingsFileInput").set_input_files(f)
        expect(page.locator("#status")).to_have_class("status error")
        expect(page.locator("#status")).to_contain_text("Onbekende bestandsindeling")
        browser.close()


def test_import_does_not_modify_analysis(tmp_path: Path) -> None:
    """Import wijzigt geen bestaand analyseresultaat of toegepaste instellingen."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(accept_downloads=True)
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
        page.locator("#analyzeBtn").click()
        page.locator("#workspace.show").wait_for(timeout=30_000)
        applied_access = page.evaluate("state.settings.activeAccessMinutes")
        page.locator('.tab[data-view="settings"]').click()
        payload = _valid_payload({"activeAccessMinutes": 1})
        f = _write_settings_json(tmp_path, payload)
        page.locator("#settingsFileInput").set_input_files(f)
        expect(page.locator("#set-activeAccessMinutes")).to_have_value("1")
        expect(page.locator("#status")).to_contain_text("Analyse opnieuw uitvoeren")
        assert page.evaluate("state.result!==null")
        assert page.evaluate("state.settings.activeAccessMinutes") == applied_access
        browser.close()


def test_import_then_rerun_applies_settings(tmp_path: Path) -> None:
    """Na import en heranalyse zijn de geïmporteerde waarden toegepast."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(accept_downloads=True)
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
        page.locator("#analyzeBtn").click()
        page.locator("#workspace.show").wait_for(timeout=30_000)
        page.locator('.tab[data-view="settings"]').click()
        night_before = page.evaluate(
            "state.result.attention.filter(r=>r.signals.includes('NACHT')).length"
        )
        assert night_before == 544
        payload = _valid_payload({"signalNight": False})
        f = _write_settings_json(tmp_path, payload)
        page.locator("#settingsFileInput").set_input_files(f)
        expect(page.locator("#set-signalNight")).not_to_be_checked()
        page.locator("#rerunBtn").click()
        expect(page.locator("#status")).to_contain_text(
            "Analyse opnieuw uitgevoerd", timeout=30_000
        )
        assert page.evaluate("state.settings.signalNight===false")
        night_after = page.evaluate(
            "state.result.attention.filter(r=>r.signals.includes('NACHT')).length"
        )
        assert night_after == 0
        browser.close()
