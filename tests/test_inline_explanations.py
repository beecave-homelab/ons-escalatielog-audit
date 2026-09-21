"""Productie-uitleg bij synthetische analyse, inclusief lege en grensgevallen."""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        page.evaluate(
            """() => {
              window.makeRows = patches => normalizeRows([REQUIRED_HEADERS,
                ...patches.map((patch,i) => {
                  const row = {'Gebruiker':'Fictieve medewerker', 'Medewerkernummer':'E1',
                    'Medewerkersteam':'Team A', 'Deskundigheid medewerker':'Zorg',
                    'Gebruikersnaam':'fictief', 'Escalatie reden':'Controle',
                    'Tijdsduur (min.)':'840', 'Escalatiedoel type':'Cliënt',
                    'Escalatiedoel naam':'Fictieve cliënt',
                    'Escalatiedoel identificatienummer':'C1', 'Hoofdlocatie cliënt':'Locatie',
                    'Gestart op':`01-01-2026, 08:${String(i).padStart(2,'0')}:00`,
                    'Geactiveerd op':'niet geactiveerd', 'Bron':'Fictief', ...patch};
                  return REQUIRED_HEADERS.map(k => row[k]);
                })], 0);
              window.runRows = (patches,settings={}) => {
                state.result = analyze(makeRows(patches),{...DEFAULT_SETTINGS,...settings});
                return state.result;
              };
            }"""
        )
        yield page
        browser.close()


def test_priority_and_repeat_boundaries(page):
    result = page.evaluate(
        """() => {
          const settings = {signalEmployeeDailyVolume:false,
            signalEmployeeUniqueClients:false,signalClientUniqueEmployees:false,
            signalClientUniqueTeams:false};
          const incomplete={'Escalatiedoel naam':'','Escalatiedoel identificatienummer':''};
          const cases = [
            runRows([incomplete],settings).attention[0].__explanation.priority,
            runRows([{...incomplete,'Gestart op':'01-01-2026, 23:30:00'}],settings)
              .attention[0].__explanation.priority,
            runRows([incomplete],{...settings,signalNotActivated:false})
              .attention[0].__explanation.priority,
            runRows([{...incomplete,'Tijdsduur (min.)':'onbekend'}],settings)
              .attention[0].__explanation.priority,
            runRows([{...incomplete,'Tijdsduur (min.)':'onbekend',
              'Gestart op':'01-01-2026, 23:30:00'}],settings)
              .attention[0].__explanation.priority];
          const patches=[{'Geactiveerd op':'01-01-2026, 08:01:00'},
            {'Gestart op':'01-01-2026, 08:11:00'},
            {'Gestart op':'01-01-2026, 08:11:01'}];
          let r=runRows(patches,{...settings,activeAccessMinutes:10});
          const boundary=r.auditRows.map(x=>({previous:x.previousSourceRow,
            priority:attentionPriority(x),repeat:x.__explanation?.repeat}));
          const csvHeaders=Object.keys(attentionRows(r.attention)[0]);
          const sourceHeaders=Object.keys(sourceTableRows(r.auditRows)[0]);
          const displayHeaders=Object.keys(attentionRows(r.attention,true)[0]);
          const rows=r.allRows;
          r=analyze(rows,{...state.settings,activeAccessMinutes:1});
          const reset=r.auditRows[1].__explanation.repeat;
          r=runRows(patches,{...settings,activeAccessMinutes:10,
            signalReEscalationActiveAccess:false,signalVeryFastRepeat:false});
          const disabled=r.auditRows[1].__explanation;
          const delays=runRows([
            {'Geactiveerd op':'01-01-2026, 08:02:00'},
            {'Geactiveerd op':'01-01-2026, 08:03:01'}],settings)
            .auditRows.map(x=>x.signals.includes('LATE_ACTIVATIE'));
          return {cases,boundary,reset,disabled,csvHeaders,sourceHeaders,displayHeaders,delays};
        }"""
    )
    assert [x["level"] for x in result["cases"]] == ["Basis", "Midden", "Basis", "Midden", "Hoog"]
    assert result["cases"][2]["themes"] == []
    assert result["cases"][3]["themes"] == ["access", "data"]
    assert "Onvolledig cliëntdoel telt" in result["cases"][0]["reason"]
    boundary = result["boundary"]
    assert boundary[1]["previous"] == 2
    assert boundary[1]["priority"] == "Hoog"
    assert boundary[1]["repeat"]["sinceActivation"] == 600
    assert boundary[1]["repeat"]["sinceStart"] == 660
    assert boundary[2]["previous"] is None
    assert result["reset"] is None
    assert result["disabled"]["priority"]["level"] == "Basis"
    assert result["disabled"]["repeat"]["signal"] is False
    assert result["delays"] == [False, True]
    assert "Waarom deze prioriteit" not in result["csvHeaders"]
    assert "Waarom deze prioriteit" in result["displayHeaders"]
    assert len(result["csvHeaders"]) == 16
    assert len(result["sourceHeaders"]) == 18


def test_windows_concentration_and_peer_missing_reasons(page):
    result = page.evaluate(
        """() => {
          let r=runRows([{}, {'Gestart op':'01-01-2026, 08:05:00'},
            {'Gestart op':'01-01-2026, 08:10:00'}],{burstWindowMinutes:10,burstThreshold:3});
          const burst=r.bursts[0];
          const outside=runRows([{}, {'Gestart op':'01-01-2026, 08:05:00'},
            {'Gestart op':'01-01-2026, 08:10:01'}],
            {burstWindowMinutes:10,burstThreshold:3}).bursts.length;
          const clusters=[
            runRows([{}, {'Medewerkernummer':'E2','Medewerkersteam':'Team B'}],
              {clientClusterEmployeeThreshold:3,clientClusterTeamThreshold:2}).clientClusters[0],
            runRows([{}, {'Medewerkernummer':'E2'},{'Medewerkernummer':'E3'}],
              {clientClusterEmployeeThreshold:3,clientClusterTeamThreshold:2}).clientClusters[0]];
          const concentrations=[runRows([{}]).concentration[0],runRows(
            Array.from({length:7},(_,i)=>({'Escalatiedoel identificatienummer':`C${i}`})))
            .concentration[0],runRows([{'Escalatiedoel identificatienummer':''}])
            .concentration[0],runRows([{'Escalatiedoel type':'Locatie'}]).concentration[0]];
          const concentrationHtml=concentrations.map(x=>valueCellHtml(x,'Top-3 cliëntaandeel %'));
          const peerPatches=Array.from({length:4},(_,i)=>({'Medewerkernummer':`E${i}`,
            'Escalatiedoel type':'Locatie'}));
          r=runRows(peerPatches);
          const zero=r.peers[0].__ratioMissing['Ratio cliënten / team'];
          const renderedZero=valueCellHtml(r.peers[0],'Ratio cliënten / team');
          r=runRows([{}]);const small=r.peers[0].__ratioMissing['Ratio volume / team'];
          r=runRows([{'Medewerkersteam':''}]);
          const context=r.peers[0].__ratioMissing['Ratio volume / team'];
          return {burst,outside,clusters,concentrations,concentrationHtml,zero,small,context,
            renderedZero,ratios:[ratio(1,2),ratio(2,2),ratio(4,2),ratio(1,0)]};
        }"""
    )
    assert result["burst"]["Verstreken (sec.)"] == 600
    assert result["burst"]["Minimum escalaties"] == 3
    assert result["outside"] == 0
    assert [x["Selectiereden"] for x in result["clusters"]] == ["Teamdrempel", "Medewerkerdrempel"]
    concentrations = result["concentrations"]
    assert concentrations[0]["Top-3 cliëntaandeel %"] == 100
    assert concentrations[1]["Top-3 cliëntregistraties"] == 3
    assert concentrations[1]["Cliëntescalaties herkenbaar"] == 7
    assert concentrations[1]["Top-3 cliëntaandeel %"] == 42.9
    assert concentrations[2]["Top-3 cliëntaandeel %"] == ""
    assert concentrations[3]["Top-3 doelregistraties"] == 1
    assert concentrations[3]["Top-3 cliëntregistraties"] == 0
    assert "3 / 7 = 42,9%" in result["concentrationHtml"][1]
    assert "Niet berekenbaar" in result["concentrationHtml"][2]
    assert result["zero"] == "Mediaan is nul"
    assert result["small"] == "Te weinig peers: 0 / minimum 3"
    assert result["context"] == "Context ontbreekt of wisselt"
    assert "Mediaan is nul" in result["renderedZero"]
    assert result["ratios"] == [0.5, 1, 2, ""]


def test_explanation_interaction_and_export(page, tmp_path: Path):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "console", lambda message: errors.append(message.text) if message.type == "error" else None
    )
    page.evaluate(
        """() => {
          runRows([{'Geactiveerd op':'01-01-2026, 08:00:00'},
            {'Gestart op':'01-01-2026, 08:01:00','Medewerkersteam':'<img src=x onerror=alert(1)>'},
            {'Gestart op':'01-01-2026, 08:02:00'}],
            {activeAccessMinutes:2,burstThreshold:3,burstWindowMinutes:7,
             clientClusterTeamThreshold:2,clientClusterWindowMinutes:9});
          render();
        }"""
    )
    page.locator('.tab[data-view="attention"]').click()
    assert "Overige aandachtspunten" in page.locator("#priorityGuidance").inner_text()
    first = page.locator("#attentionTable tbody tr").first
    first.focus()
    first.press("Enter")
    assert "Werkelijke tijdstippen" in page.locator("#drillExplanation").inner_text()
    assert "Excel-rij 2" in page.locator("#drillExplanation").inner_text()
    page.locator("#drillCloseBtn").click()
    page.locator('.tab[data-view="deepdive"]').click()
    for tab, table in [("bursts", "burstTable"), ("clusters", "clusterTable")]:
        page.locator(f'[data-pane="{tab}"]').click()
        page.locator(f"#{table} tbody tr").first.focus()
        page.locator(f"#{table} tbody tr").first.press("Enter")
        assert "120 seconden" in page.locator("#drillExplanation").inner_text()
        page.locator("#drillCloseBtn").click()
    assert page.locator("img").count() == 0
    for width in (1280, 800, 390):
        page.set_viewport_size({"width": width, "height": 900})
        for tab in ("peers", "bursts", "clusters", "concentration"):
            page.locator(f'[data-pane="{tab}"]').click()
            assert page.evaluate("document.body.scrollWidth <= innerWidth")
    report = tmp_path / "rapport.html"
    with page.expect_download() as download:
        page.locator("#reportBtn").click()
    download.value.save_as(report)
    page.goto(report.as_uri())
    page.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)")
    assert "2 minuten" in page.locator("#s-herescalatie").inner_text()
    assert "7 minuten" in page.locator("#s-bursts").inner_text()
    assert "9 minuten" in page.locator("#s-clusters").inner_text()
    assert page.locator("#s-signalen table").count() == 2
    for selector, explanation in [
        ("#s-prioriteit", ".priority-guidance"),
        ("#s-herescalatie", ".repeat-guidance"),
        ("#s-bursts", ".window-guidance"),
        ("#s-clusters", ".window-guidance"),
        ("#s-peer", ".peer-ratio-guidance"),
        ("#s-concentratie", ".concentration-guidance"),
    ]:
        section = page.locator(selector)
        section.evaluate("d=>d.open=false")
        assert not section.locator(explanation).is_visible()
        assert not section.locator("table").first.is_visible()
        section.locator(":scope > summary").click()
        assert section.locator(explanation).is_visible()
        assert section.locator("table").first.is_visible()
    for width in (1280, 800, 390):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.body.scrollWidth <= innerWidth")
    page.evaluate("document.querySelectorAll('details').forEach(d=>d.open=false)")
    page.emulate_media(media="print")
    page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
    assert page.locator("details:not([open])").count() == 0
    assert page.locator(".priority-guidance").count() == 1
    assert page.locator("#s-hoog .reason-row").count() == 2
    assert "Excel-rij 3" in page.locator("#s-hoog .reason-row").first.inner_text()
    assert page.locator("img").count() == 0
    assert not errors


def test_empty_analysis_and_standard_fixture(page, tmp_path: Path):
    page.evaluate("runRows([]);render()")
    assert page.locator("#priorityGuidance").text_content()
    assert page.locator("#burstGuidance").text_content()
    assert page.evaluate("state.result.allRows.length") == 0
    report = tmp_path / "leeg.html"
    with page.expect_download() as download:
        page.locator("#reportBtn").click()
    download.value.save_as(report)
    page.goto(report.as_uri())
    assert page.locator("#s-tijd td").all_text_contents() == ["0"] * 168
    assert "Fictief" in page.locator("#s-herescalatie").text_content()
    assert "Geen gegevens" in page.locator("#s-bursts").text_content()
    assert "Geen gegevens" in page.locator("#s-concentratie").text_content()
    page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
    page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
    page.locator("#analyzeBtn").click()
    page.locator("#workspace.show").wait_for()
    assert page.locator("#kpis .value").all_text_contents() == [
        "1.802",
        "1.790",
        "250",
        "558",
        "0",
        "310",
    ]
