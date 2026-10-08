"""Gedeelde tijdsuitleg en echte analysegrenzen met synthetische bronregels."""

import pytest
from playwright.sync_api import expect, sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        yield page
        browser.close()


@pytest.mark.parametrize("threshold,enabled", [(2, True), (0, True), (2, False)])
def test_activation_boundaries_match_explanation(page, threshold, enabled):
    result = page.evaluate(
        """([threshold,enabled]) => {
          const start=Date.UTC(2026,0,1,8),seconds=threshold*60;
          const activations=[seconds,seconds+1,-1,'','onleesbaar','Niet geactiveerd'];
          const matrix=[REQUIRED_HEADERS,...activations.map((value,i)=>{
            const record={'Gebruiker':'Fictief '+i,'Medewerkernummer':String(i),
              'Gebruikersnaam':'fictief'+i,'Medewerkersteam':'Test',
              'Deskundigheid medewerker':'Test','Escalatie reden':'Controle',
              'Tijdsduur (min.)':'600','Escalatiedoel type':'Cliënt',
              'Escalatiedoel naam':'Fictief '+i,'Escalatiedoel identificatienummer':String(i),
              'Hoofdlocatie cliënt':'Test','Bron':'-',
              'Gestart op':new Date(start).toISOString().slice(0,19),
              'Geactiveerd op':typeof value==='number'
                ?new Date(start+value*1000).toISOString().slice(0,19):value};
            return REQUIRED_HEADERS.map(h=>record[h]);
          })];
          state.rawRows=normalizeRows(matrix,0);
          state.result=analyze(state.rawRows,{...DEFAULT_SETTINGS,
            activationDelayThresholdMinutes:threshold,signalActivationDelay:enabled});
          render();
          return {signals:state.result.auditRows.map(r=>r.signals),
            delays:state.result.auditRows.map(r=>r.activationDelay),
            reconciled:state.result.allRows.length===state.result.systemRows.length+
              state.result.duplicateRows.length+state.result.auditRows.length};
        }""",
        [threshold, enabled],
    )
    assert result["reconciled"]
    assert ["LATE_ACTIVATIE" in signals for signals in result["signals"]] == [
        False,
        enabled,
        False,
        False,
        False,
        False,
    ]
    assert all("ONGELDIGE_ACTIVATIE" in result["signals"][i] for i in (2, 3, 4))
    assert "NIET_GEACTIVEERD" in result["signals"][5]
    assert result["delays"][:2] == [threshold, round(threshold + 1 / 60, 2)]
    guidance = page.locator("#activationGuidance")
    expect(guidance.locator("h3")).to_have_text(
        "Alleen ná de grens een signaal" if enabled else "Activatievertraging · signaal uit"
    )
    assert guidance.locator(".row-names strong").all_text_contents() == [
        f"{threshold * 60} s",
        f"{threshold * 60 + 1} s",
    ]
    assert guidance.locator(".outcome.flagged").count() == int(enabled)
    assert "Niet geactiveerd" in guidance.text_content()
    if threshold == 0:
        assert guidance.locator("svg circle").first.get_attribute("cx") == "280"


@pytest.mark.parametrize(
    "start,end,enabled,selected",
    [
        (23, 6, True, [0, 1, 2, 3, 4, 5, 23]),
        (8, 17, True, list(range(8, 17))),
        (6, 6, True, []),
        (23, 6, False, [0, 1, 2, 3, 4, 5, 23]),
    ],
)
def test_night_boundaries_and_disabled_volume(page, start, end, enabled, selected):
    result = page.evaluate(
        """([start,end,enabled]) => {
          const matrix=[REQUIRED_HEADERS,...Array.from({length:25},(_,i)=>{
            const record={'Gebruiker':'Fictief '+i,'Medewerkernummer':String(i),
              'Gebruikersnaam':'fictief'+i,'Medewerkersteam':'Test',
              'Deskundigheid medewerker':'Test','Escalatie reden':'Controle',
              'Tijdsduur (min.)':'600','Escalatiedoel type':'Cliënt',
              'Escalatiedoel naam':'Fictief '+i,'Escalatiedoel identificatienummer':String(i),
              'Hoofdlocatie cliënt':'Test','Bron':'-', 'Geactiveerd op':'Niet geactiveerd',
              'Gestart op':i===24?'onleesbaar':`2026-01-01T${String(i).padStart(2,'0')}:00:00`};
            return REQUIRED_HEADERS.map(h=>record[h]);
          })];
          state.rawRows=normalizeRows(matrix,0);
          state.result=analyze(state.rawRows,{...DEFAULT_SETTINGS,
            nightStartHour:start,nightEndHour:end,signalNight:enabled});render();
          return {night:state.result.auditRows.filter(r=>r.signals.includes('NACHT'))
              .map(r=>r.started.hour),
            volume:state.result.employees.reduce((a,r)=>a+r.Nacht,0),
            hourTotal:state.result.time.hours.reduce((a,r)=>a+r.Escalaties,0),
            missing:state.result.time.missingStart};
        }""",
        [start, end, enabled],
    )
    assert result["night"] == (selected if enabled else [])
    assert result["volume"] == len(selected)
    assert result["hourTotal"] == 24
    assert result["missing"] == 1
    guidance = page.locator(".night-guidance")
    assert "1 auditregel zonder geldige starttijd" in guidance.text_content()
    if not selected:
        assert guidance.locator(".segment").count() == 0
        assert "Leeg nachtvenster" in guidance.text_content()
    if not enabled:
        assert "nachtvolumes blijven beschikbaar" in guidance.text_content()


def test_reanalysis_report_and_responsive_guidance(page, tmp_path):
    errors, requests = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: requests.append(request.url))
    page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
    page.locator("#analyzeBtn").click()
    page.locator("#workspace.show").wait_for()
    page.locator('.tab[data-view="attention"]').click()
    original_csv = page.evaluate("toCsv(attentionRows(state.result.attention))")
    page.evaluate("state.settings.activationDelayThresholdMinutes=99;renderTables(state.result)")
    expect(page.locator("#activationGuidance .setting-line")).to_have_text("2 min · signaal aan")
    assert page.evaluate("toCsv(attentionRows(state.result.attention))") == original_csv
    page.locator("#activationGuidance summary").focus()
    page.keyboard.press("Enter")
    assert page.locator("#activationGuidance details").get_attribute("open") is not None
    for width in (1280, 800, 390):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.body.scrollWidth<=innerWidth")
        assert page.locator(".compact-timeline").evaluate("el=>el.scrollWidth<=el.clientWidth")
        page.locator('.tab[data-view="time"]').click()
        assert page.locator(".night-guidance").evaluate("el=>el.scrollWidth<=el.clientWidth")
        page.locator('.tab[data-view="attention"]').click()
    page.locator('.tab[data-view="settings"]').click()
    page.locator("#set-activationDelayThresholdMinutes").fill("0")
    page.locator("#set-signalActivationDelay").uncheck()
    page.locator("#set-nightStartHour").fill("6")
    page.locator("#set-nightEndHour").fill("6")
    page.locator("#set-signalNight").uncheck()
    page.locator("#rerunBtn").click()
    expect(page.locator("#activationGuidance .setting-line")).to_have_text("0 min · signaal uit")
    assert "Leeg nachtvenster" in page.locator(".night-guidance").text_content()
    report = tmp_path / "rapport.html"
    with page.expect_download() as download:
        page.locator("#reportBtn").click()
    download.value.save_as(report)
    page.goto(report.as_uri())
    section = page.locator("#s-signalen")
    section.evaluate("el=>el.open=false")
    section.locator(":scope > summary").focus()
    page.keyboard.press("Enter")
    expect(section.locator(".delay-guidance")).to_be_visible()
    expect(section.locator(".delay-guidance h3")).to_have_text("Activatievertraging · signaal uit")
    page.keyboard.press("Enter")
    expect(section.locator(".delay-guidance")).not_to_be_visible()
    for width in (1280, 800, 390):
        page.set_viewport_size({"width": width, "height": 900})
        page.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)")
        assert page.evaluate("document.body.scrollWidth<=innerWidth")
        assert page.locator(".compact-timeline").evaluate("el=>el.scrollWidth<=el.clientWidth")
    page.evaluate("document.querySelectorAll('details').forEach(d=>d.open=false)")
    page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
    assert page.locator("details:not([open])").count() == 0
    page.pdf(path=tmp_path / "rapport.pdf", format="A4")
    assert (tmp_path / "rapport.pdf").stat().st_size > 1000
    context = page.context.browser.new_context(java_script_enabled=False)
    static = context.new_page()
    static.goto(report.as_uri())
    expect(static.locator("#s-signalen .delay-guidance")).to_be_visible()
    assert static.locator(".delay-guidance").is_visible()
    assert "0 min · signaal uit" in static.locator(".delay-guidance").text_content()
    expect(static.locator(".delay-guidance h3")).to_have_text("Activatievertraging · signaal uit")
    assert "Leeg nachtvenster" in static.locator("#s-tijd").text_content()
    context.close()
    assert not errors
    assert not [url for url in requests if url.startswith(("http:", "https:"))]
