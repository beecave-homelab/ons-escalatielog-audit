"""Exercise the generated training file through real controls, entirely offline."""

import importlib.util
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_report_layout import ROOT, launch_browser

SPEC = importlib.util.spec_from_file_location("generate_tour", ROOT / "scripts/generate_tour.py")
generate_tour = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_tour)


def test_generated_tour__matches_sources_and_keeps_csp() -> None:
    """Stale source, fixture or tour edits fail before shipping an obsolete artifact."""
    actual = generate_tour.OUTPUT.read_text()
    assert actual == generate_tour.build_tour(), "Genereer de rondleiding opnieuw."
    from html.parser import HTMLParser

    class CSPParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.policy = None

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy":
                self.policy = attrs["content"]

    app, tour = CSPParser(), CSPParser()
    app.feed((ROOT / "escalatielog-audit-webui.html").read_text())
    tour.feed(actual)
    assert tour.policy == app.policy, "De rondleiding mag de CSP niet versoepelen."


def test_generator__rejects_missing_anchor(tmp_path: Path, monkeypatch) -> None:
    """A renamed app anchor causes an explicit generation error, not a broken guide."""
    html = (
        (ROOT / "escalatielog-audit-webui.html")
        .read_text()
        .replace('id="kpis"', 'id="renamed-kpis"')
    )
    (tmp_path / "escalatielog-audit-webui.html").write_text(html)
    layer = tmp_path / "scripts/tour"
    layer.mkdir(parents=True)
    (layer / "tour.js").write_text((ROOT / "scripts/tour/tour.js").read_text())
    monkeypatch.setattr(generate_tour, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="DOM-anker ontbreekt: #kpis"):
        generate_tour.build_tour()


@pytest.fixture
def tour_page():
    """Use the same dedicated browser runner as the existing synthetic app tests."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        errors, requests, downloads = [], [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request", lambda req: requests.append(req.url) if req.url.startswith("http") else None
        )
        page.on("download", lambda download: downloads.append(download.suggested_filename))
        page.goto(generate_tour.OUTPUT.as_uri())
        expect(page.locator("#tourResume")).to_be_enabled()
        yield page, errors, requests, downloads
        browser.close()


def reference_counts(page) -> list[int]:
    """Read the normal app's analysis result rather than a parallel training calculation."""
    return page.evaluate(
        "[state.result.allRows.length,state.result.systemRows.length,"
        "state.result.duplicateRows.length,state.result.auditRows.length,"
        "state.result.attention.length]"
    )


@pytest.mark.parametrize("width", [1440, 768, 375])
def test_tour__complete_route_and_keyboard_controls(tour_page, width: int) -> None:
    """Every real target remains usable at desktop, tablet and narrow mobile widths."""
    page, errors, requests, downloads = tour_page
    page.set_viewport_size({"width": width, "height": 1000})
    assert reference_counts(page) == [2000, 156, 42, 1802, 1790]
    steps = page.evaluate("tourSteps.length")
    for index in range(steps):
        expect(page.locator("#tourProgress")).to_have_text(f"Stap {index + 1} van {steps}")
        expect(page.locator("#tourTitle")).to_be_focused()
        expect(page.locator("#tourMarker")).to_be_visible()
        assert page.locator("#tourHint").inner_text() == ""
        expect(page.locator("#tourRestore")).to_be_hidden()
        assert page.evaluate(
            """() => {
              const marker=tourMarker.getBoundingClientRect();
              const panel=tourPanel.getBoundingClientRect();
              return marker.width>0 && marker.height>0 && panel.left>=0 &&
                panel.right<=innerWidth && panel.bottom<=innerHeight;
            }"""
        ), "Markering en uitleg moeten binnen het venster blijven."
        if index == 3:
            expect(page.locator("#drillOverlay")).to_have_class("drill-overlay show")
            page.locator("#drillCloseBtn").click()
            expect(page.locator("#tourRestore")).to_be_visible()
            page.locator("#tourRestore").click()
            expect(page.locator("#drillOverlay")).to_have_class("drill-overlay show")
            # Guidance controls participate in the existing dialog keyboard scope.
            page.locator("#tourReset").focus()
            page.keyboard.press("Tab")
            expect(page.locator("#drillCsvBtn")).to_be_focused()
        if index == 4:
            page.locator("#attentionTable .table-search").fill("Medewerker")
            page.locator("#attentionTable .signal-filter").select_option("NACHT")
            page.locator("#attentionTable .sort-button").first.click()
            assert reference_counts(page) == [2000, 156, 42, 1802, 1790]
            page.locator("#tourPrev").click()
            page.locator("#tourNext").click()
            expect(page.locator("#attentionTable .table-search")).to_have_value("")
            expect(page.locator("#attentionTable .signal-filter")).to_have_value("")
            page.locator('[data-view="employees"]').click()
            expect(page.locator("#tourRestore")).to_be_visible()
            page.locator("#tourRestore").click()
            expect(page.locator("#view-attention")).to_be_visible()
        # Native keyboard activation of all forward navigation, including the final action.
        page.locator("#tourNext").focus()
        page.keyboard.press("Enter")
    expect(page.locator("#tourPanel")).to_be_hidden()
    expect(page.locator("#tourResume")).to_be_focused()
    page.locator("#tourResume").click()
    expect(page.locator("#tourProgress")).to_have_text(f"Stap {steps} van {steps}")
    page.keyboard.press("Escape")
    expect(page.locator("#tourPanel")).to_be_hidden()
    expect(page.locator("#tourResume")).to_be_focused()
    assert not errors and not requests and not downloads


def test_tour__reset_reload_import_guards_and_explicit_export(tour_page) -> None:
    """Reset recovers the reference result and imports cannot introduce real data."""
    page, errors, requests, downloads = tour_page
    for selector in ("#chooseBtn", "#fileInput", "#importSettingsBtn", "#settingsFileInput"):
        expect(page.locator(selector)).to_be_disabled()
    page.evaluate(
        """async () => {
          const file=new File(['Geen brongegevens'],'eigen.xlsx');
          await loadFile(file);importSettings(new File(['{}'],'eigen.json'));
          const transfer=new DataTransfer();transfer.items.add(file);
          document.querySelector('#dropzone').dispatchEvent(
            new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:transfer}));
        }"""
    )
    assert page.evaluate("state.file.name") == "synthetic-escalatielog.xlsx"
    assert reference_counts(page) == [2000, 156, 42, 1802, 1790]
    page.locator("#tourStop").click()
    page.locator("#settingsBtn").click()
    page.locator("#set-activationDelayThresholdMinutes").fill("5")
    assert page.evaluate("state.settings.activationDelayThresholdMinutes") == 2
    page.locator("#rerunBtn").click()
    expect(page.locator("#status")).to_contain_text("Analyse opnieuw uitgevoerd")
    page.locator('[data-view="overview"]').click()
    page.locator("#findingLimit").fill("3")
    page.locator("#applyFindingLimit").click()
    page.locator("#tourResume").click()
    page.locator("#tourReset").click()
    expect(page.locator("#tourReset")).to_be_enabled()
    assert page.evaluate("state.settings.activationDelayThresholdMinutes") == 2
    assert page.evaluate("state.findingLimit") == 10
    assert reference_counts(page) == [2000, 156, 42, 1802, 1790]
    page.reload()
    expect(page.locator("#tourResume")).to_be_enabled()
    expect(page.locator("#tourProgress")).to_have_text("Stap 1 van 14")
    assert reference_counts(page) == [2000, 156, 42, 1802, 1790]
    page.locator("#tourStop").click()
    with page.expect_download() as result:
        page.locator("#csvBtn").click()
    assert result.value.suggested_filename.endswith("_aandachtspunten.csv")
    content = Path(result.value.path()).read_text(encoding="utf-8-sig")
    assert "Synthetische medewerker" in content
    assert len(content.splitlines()) == 1791
    assert len(downloads) == 1 and not errors and not requests


def test_tour__missing_anchor_and_scrolled_target_recover(tour_page) -> None:
    """Missing or offscreen controls give guidance while navigation stays available."""
    page, errors, requests, downloads = tour_page
    page.evaluate("document.querySelector('#dropzone').id='renamed-dropzone'")
    expect(page.locator("#tourHint")).to_contain_text("onderdeel ontbreekt")
    page.locator("#tourNext").click()
    expect(page.locator("#tourMarker")).to_be_visible()
    page.evaluate("window.scrollTo(0,document.body.scrollHeight)")
    expect(page.locator("#tourRestore")).to_be_visible()
    page.locator("#tourRestore").click()
    expect(page.locator("#tourMarker")).to_be_visible()
    assert not errors and not requests and not downloads
