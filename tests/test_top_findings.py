"""Mixed, traceable Top-X and a local text template with synthetic data."""

from pathlib import Path

import pytest
from playwright.sync_api import expect
from test_inline_explanations import page as page
from test_report_layout import STANDARD_FIXTURE


def load_reference(page) -> None:
    """Read the committed synthetic reference via the real upload route."""
    page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
    page.locator("#analyzeBtn").click()
    expect(page.locator("#workspace")).to_be_visible(timeout=30_000)


def open_editor(page) -> None:
    """Open only the template editor without changing the method disclosure."""
    page.get_by_text("Samenvatting maken en kopiëren", exact=True).click()


def test_mixed_findings_use_actual_windows_and_stable_order(page) -> None:
    """Each kind keeps its own criteria and source rows, also on overlap."""
    data = page.evaluate(
        """() => {
          const patches=Array.from({length:6},(_,i)=>({
            'Medewerkernummer':i<3?'E1':'E2',
            'Gebruiker':i<3?'Medewerker A':'Medewerker B',
            'Medewerkersteam':i<3?'Team A':'Team B',
            'Escalatiedoel identificatienummer':'C1',
            'Gestart op':`01-01-2026, 08:0${i}:00`}));
          const r=runRows(patches,{burstThreshold:3,clientClusterEmployeeThreshold:2});
          const f=r.findings;
          return {types:f.slice(0,6).map(x=>x.values.type),
            firstAudit:f[0].__rows[0].sourceRow,
            bursts:f.filter(x=>x.values.type==='Burst').map(x=>x.__rows.map(y=>y.sourceRow)),
            cluster:f.find(x=>x.values.type==='Cliëntcluster').__rows.map(x=>x.sourceRow),
            priorities:f.filter(x=>x.values.type!=='Auditregel').map(x=>x.values.prioriteit),
            count:r.auditRows.length,hidden:!Object.keys(f[0]).includes('__rows'),
            keys:f.map(x=>x.key),
            again:analyze(r.allRows,r.explanations.settings).findings.map(x=>x.key)};
        }"""
    )
    assert data["types"] == [
        "Auditregel",
        "Burst",
        "Cliëntcluster",
        "Auditregel",
        "Burst",
        "Auditregel",
    ]
    assert data["firstAudit"] == 2
    assert data["bursts"] == [[2, 3, 4], [5, 6, 7]]
    assert data["cluster"] == [2, 3, 4, 5, 6, 7]
    assert all(value == "Niet van toepassing" for value in data["priorities"])
    assert data["count"] == 6
    assert data["hidden"]
    assert data["keys"] == data["again"]


def test_selection_limit_and_drilldown_preserve_analysis(page) -> None:
    """The view selection only limits the Top-X and opens exactly its evidence group."""
    load_reference(page)
    before = page.evaluate(
        "JSON.stringify([[...state.result.signalCounts],attentionRows(state.result.attention)])"
    )
    expect(page.locator(".finding-item")).to_have_count(5)
    expected = page.evaluate("selectedFindings()[1].__rows.map(x=>x.sourceRow)")
    page.locator('[data-finding="1"]').click()
    assert page.evaluate("state.drilldown.rows.map(x=>x['Excel-rij'])") == sorted(expected)
    page.locator("#drillCloseBtn").click()
    page.locator("#findingLimit").fill("2")
    page.locator("#applyFindingLimit").click()
    expect(page.locator(".finding-item")).to_have_count(2)
    after = page.evaluate(
        "JSON.stringify([[...state.result.signalCounts],attentionRows(state.result.attention)])"
    )
    assert before == after
    assert page.evaluate("dashboardPngModel().findings.length") == 2
    for value in ("", "0", "51", "1.5"):
        page.locator("#findingLimit").fill(value)
        page.locator("#applyFindingLimit").click()
        expect(page.locator("#findingLimit")).to_have_attribute("aria-invalid", "true")
        expect(page.locator(".finding-item")).to_have_count(2)
    page.locator("#findingLimit").fill("50")
    page.locator("#applyFindingLimit").click()
    expect(page.locator(".finding-item")).to_have_count(50)
    expect(page.locator("#findingLimit")).not_to_have_attribute("aria-invalid", "true")


def test_summary_validation_is_literal_and_limited_to_selected_data(page) -> None:
    """Source values are not reinterpreted as template or HTML."""
    data = page.evaluate(
        """() => {
          const r=runRows([{'Gebruiker':'{positie}<img src=x onerror=alert(1)>',
            'Escalatiedoel naam':'','Escalatiedoel identificatienummer':''}]);
          const f=r.findings.slice(0,1),errors=[];
          for(const s of ['{onbekend}','{medewerker','{{positie}}','x'.repeat(4001)]){
            try{findingsSummary(f,s)}catch(e){errors.push(e.message)}
          }
          return {text:findingsSummary(f,'{positie}: {medewerker} / {client} / {bronrijen}'),
            errors,empty:findingsSummary([],'{positie}'),count:r.attention.length};
        }"""
    )
    assert data["text"].startswith(
        "1: {positie}<img src=x onerror=alert(1)> / Niet beschikbaar / 2"
    )
    assert len(data["errors"]) == 4
    assert "geen bewijs van dossierinzage" in data["text"]
    assert data["empty"] == "Geen opvallendheden in deze analyse."
    assert data["count"] == 1


def test_preview_gates_copy_and_reports_clipboard_failure(page) -> None:
    """Copying follows the viewed preview and honestly reports a refused clipboard."""
    load_reference(page)
    open_editor(page)
    page.evaluate(
        """Object.defineProperty(navigator,'clipboard',{configurable:true,
          value:{writeText:async text=>{window.copiedSummary=text}}})"""
    )
    page.locator("#findingTemplate").fill("{positie} {type}: {onderwerp}")
    expect(page.locator("#findingPreview")).to_have_value("")
    expect(page.locator("#copyFindings")).to_be_disabled()
    page.locator("#previewFindings").click()
    preview = page.locator("#findingPreview").input_value()
    page.locator("#copyFindings").click()
    expect(page.locator("#findingStatus")).to_contain_text("Samenvatting gekopieerd")
    assert page.evaluate("window.copiedSummary") == preview
    page.locator("#findingTemplate").fill("{geheim}")
    page.locator("#previewFindings").click()
    expect(page.locator("#copyFindings")).to_be_disabled()
    expect(page.locator("#findingStatus")).to_contain_text("Onbekende placeholder")
    page.locator("#resetFindingTemplate").click()
    page.evaluate("()=>{navigator.clipboard.writeText=async()=>{throw new Error('Geweigerd')}}")
    page.locator("#copyFindings").click()
    expect(page.locator("#findingStatus")).to_contain_text("Ctrl+C of Cmd+C")
    assert page.locator("#findingPreview").evaluate("el=>el.selectionEnd-el.selectionStart") > 0
    assert page.evaluate("document.activeElement.id") == "findingPreview"


def test_report_and_png_share_selection_and_exclude_template(page, tmp_path: Path) -> None:
    """Exports use the same analysis data, without free template text."""
    load_reference(page)
    page.locator("#findingLimit").fill("3")
    page.locator("#applyFindingLimit").click()
    open_editor(page)
    page.locator("#findingTemplate").fill("PRIVÉTEST {onderwerp}")
    page.locator("#previewFindings").click()
    expected = page.evaluate("findingRows()")
    assert page.evaluate("dashboardPngModel().findings") == expected
    assert "Opvallendheden om te onderzoeken" in page.evaluate(
        "overviewPngVisuals(dashboardPngModel()).map(x=>x.title)"
    )
    with page.expect_download() as pending:
        page.locator("#reportBtn").click()
    report = tmp_path / "rapport.html"
    pending.value.save_as(report)
    html = report.read_text(encoding="utf-8")
    assert "PRIVÉTEST" not in html
    page.goto(report.as_uri())
    section = page.locator("#s-opvallendheden")
    expect(section.locator("tbody tr")).to_have_count(3)
    for row in expected:
        assert row["Onderwerp"] in section.inner_text()
        assert row["Selectiereden"].strip() in section.inner_text()
    page.evaluate("dispatchEvent(new Event('beforeprint'))")
    expect(section).to_have_attribute("open", "")


def test_patterns_without_individual_signals_and_empty_analysis(page) -> None:
    """Patterns stay standalone candidates; an empty analysis is not an error."""
    values = page.evaluate(
        """() => {
          const disabled=Object.fromEntries(Object.keys(DEFAULT_SETTINGS)
            .filter(x=>x.startsWith('signal')).map(x=>[x,false]));
          const patches=Array.from({length:3},()=>({}));
          const r=runRows(patches,{...disabled,burstThreshold:2});
          const types=r.findings.map(x=>x.values.type);
          state.analysisRunAt=new Date();render();
          const preview=$('#findingPreview').value;
          state.result=analyze([],DEFAULT_SETTINGS);render();
          return {types,preview,empty:$('#findingList').textContent,
            disabled:$('#copyFindings').disabled};
        }"""
    )
    assert values["types"] == ["Burst"]
    assert "Burst" in values["preview"]
    assert "Geen auditregels" in values["empty"]
    assert values["disabled"]


@pytest.mark.parametrize("width", [390, 1440])
def test_findings_layout_and_html_escaping(page, width: int) -> None:
    """Long source values stay readable and are not executed as HTML."""
    load_reference(page)
    page.set_viewport_size({"width": width, "height": 1000})
    page.evaluate(
        """() => {state.result.findings[0].values.onderwerp='<img src=x> '+ 'Lang'.repeat(80);
          renderFindings(state.result)}"""
    )
    assert page.locator("#topFindings img").count() == 0
    assert "<img src=x>" in page.locator(".finding-item").first.inner_text()
    assert page.evaluate("document.body.scrollWidth<=innerWidth")


def test_pending_copy_identifies_old_selection_and_source_rows_are_capped(page) -> None:
    """A delayed clipboard gets an honest message; large evidence sets stay complete."""
    load_reference(page)
    open_editor(page)
    page.evaluate(
        """() => {Object.defineProperty(navigator,'clipboard',{configurable:true,
          value:{writeText:text=>{window.pendingText=text;
            return new Promise(resolve=>{window.finishCopy=resolve})}}});}
        """
    )
    page.locator("#copyFindings").click()
    page.locator("#findingLimit").fill("1")
    page.locator("#applyFindingLimit").click()
    page.evaluate("window.finishCopy()")
    expect(page.locator("#findingStatus")).to_contain_text("De vorige selectie is gekopieerd")
    assert page.evaluate("window.pendingText") != page.locator("#findingPreview").input_value()
    values = page.evaluate(
        """() => {
          const r=runRows(Array.from({length:25},()=>({})),{burstThreshold:2});
          const burst=r.findings.find(x=>x.values.type==='Burst');
          return {size:burst.__rows.length,count:burst.values.aantal_bronregels,
            numbers:burst.values.bronrijen};
        }"""
    )
    assert values["size"] == 25
    assert values["count"] == "25"
    assert values["numbers"].endswith(" … (25 totaal)")
    assert values["numbers"].split(" …")[0].count(",") == 19


@pytest.mark.parametrize("exporter", ["exportDashboardPng", "exportOverviewVisualsZip"])
def test_export_refuses_selection_changed_during_encoding(page, exporter: str) -> None:
    """A new Top-X must not produce a download of the previous selection."""
    load_reference(page)
    downloads = []
    page.on("download", lambda download: downloads.append(download.suggested_filename))
    page.evaluate(
        """async name => {
          const original=HTMLCanvasElement.prototype.toBlob;
          HTMLCanvasElement.prototype.toBlob=function(cb){
            original.call(this,blob=>setTimeout(()=>cb(blob),20),'image/png');
          };
          try{
            const pending=window[name]();
            $('#findingLimit').value='1';$('#applyFindingLimit').click();
            await pending;
          }finally{HTMLCanvasElement.prototype.toBlob=original}
        }""",
        exporter,
    )
    assert not downloads
    expect(page.locator("#status")).to_contain_text("De Top-X is intussen gewijzigd")
    expect(page.locator("#pngBtn")).to_be_enabled()
    expect(page.locator("#visualsZipBtn")).to_be_enabled()
