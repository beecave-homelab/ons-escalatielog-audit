"""Controleer de echte lokale dashboard-PNG met uitsluitend synthetische gegevens."""

import struct
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        yield page
        assert not errors
        browser.close()


def load_analysis(page):
    page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
    page.locator("#analyzeBtn").click()
    page.locator("#workspace.show").wait_for(timeout=30_000)


def download_png(page, path: Path):
    with page.expect_download() as pending:
        page.locator("#pngBtn").click()
    download = pending.value
    download.save_as(path)
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    assert width == 2400
    assert 5000 < height <= 16384
    assert len(data) > 50_000
    assert download.suggested_filename.endswith("_dashboard.png")
    assert "(01-05-2026_31-05-2026)" in download.suggested_filename
    return data


def test_png_complete_offline_and_viewport_independent(page, tmp_path):
    expect(page.locator("#pngBtn")).to_be_disabled()
    load_analysis(page)
    page.context.set_offline(True)
    requests = []
    page.on("request", lambda request: requests.append(request.url))
    # Observe actual drawing, not just an export manifest: every text line must fit the canvas.
    drawing = page.evaluate(
        """() => {
          const model=dashboardPngModel(), lines=[];
          const original=CanvasRenderingContext2D.prototype.fillText;
          CanvasRenderingContext2D.prototype.fillText=function(value,x,y){
            lines.push({value:String(value),x,y,width:this.measureText(value).width,
              size:Number(this.font.match(/([\\d.]+)px/)[1])});
            return original.call(this,value,x,y);
          };
          let canvas;try{canvas=drawDashboardPng(model)}
          finally{CanvasRenderingContext2D.prototype.fillText=original}
          return {model,lines,width:canvas.width/2,height:canvas.height/2,
            ids:[...document.querySelectorAll('#view-overview [id]')].map(x=>x.id),
            pixel:[...canvas.getContext('2d').getImageData(0,0,1,1).data]};
        }"""
    )
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
    model = drawing["model"]
    # DOM changes must never change exported audit findings.
    assert page.evaluate(
        """() => {const before=JSON.stringify(dashboardPngModel());
          const root=$('#view-overview'),html=root.innerHTML;
          root.innerHTML='<div>Gewijzigde dashboardwaarden: 999.999</div>';
          const unchanged=JSON.stringify(dashboardPngModel())===before;
          root.innerHTML=html;render();return unchanged}"""
    )
    assert set(drawing["ids"]) - {"analysisBanner", "signalTotalBadge"} == set(model["sections"])
    assert len(model["kpis"]) == 6
    assert len(model["reviews"]) == 3
    assert len(model["flow"]) == 5
    assert len(model["priority"]) == 3
    assert len(model["donuts"]) == 2
    assert len(model["employees"]) == 250
    assert len(model["charts"]) == 4
    assert len(model["route"]) == 3
    assert model["version"] == "0.14.0"
    text = " ".join(line["value"] for line in drawing["lines"])
    for expected in [
        "1.802",
        "1.790",
        "Tijdheatmap",
        "Medewerkerprofiel",
        "Controlefocus",
        "Signalen in aandachtspunten",
        "Toegepaste instellingen",
        "01-05-2026",
        "31-05-2026",
        "0.14.0",
        "geen bewijs van dossierinzage",
        "persoonsgegevens",
    ]:
        assert expected in text
    assert model["notice"] in text
    for chart in model["charts"]:
        assert chart["title"] in text
        for row in chart["rows"]:
            assert row["label"] in text
            assert row["value"] in text
    for signal in model["signals"]:
        assert signal["title"] in text
        assert signal["note"] in text
    for line in drawing["lines"]:
        assert 0 <= line["x"] <= drawing["width"] - line["width"]
        assert 0 <= line["y"] <= drawing["height"] - line["size"] * 1.4
        assert line["size"] >= 13
    assert drawing["pixel"] == [245, 246, 248, 255]
    before = page.evaluate(
        "({result:state.result.attention.length,html:$('#view-overview').innerHTML})"
    )
    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate("window.scrollTo(0,document.body.scrollHeight)")
    small = download_png(page, tmp_path / "dashboard-small.png")
    page.set_viewport_size({"width": 1440, "height": 900})
    page.locator('.tab[data-view="employees"]').click()
    page.evaluate(
        "openDrilldown('Synthetische drilldown', 'Geen exportonderdeel',"
        "state.result.auditRows.slice(0,2))"
    )
    # Export from another tab with an open drilldown through the same action function.
    with page.expect_download() as pending:
        page.evaluate("exportDashboardPng()")
    pending.value.save_as(tmp_path / "dashboard-wide.png")
    assert (tmp_path / "dashboard-wide.png").read_bytes() == small
    after = page.evaluate(
        "({result:state.result.attention.length,html:$('#view-overview').innerHTML})"
    )
    assert before == after
    assert not requests
    assert "connect-src 'none'" in page.locator(
        'meta[http-equiv="Content-Security-Policy"]'
    ).get_attribute("content")


def test_png_reanalysis_empty_and_failures(page, tmp_path):
    load_analysis(page)
    first = download_png(page, tmp_path / "first.png")
    page.locator('.tab[data-view="settings"]').click()
    page.locator("#set-signalNight").uncheck()
    assert page.evaluate("dashboardPngModel().settings.signalNight") is True
    page.locator("#rerunBtn").click()
    expect(page.locator("#status")).to_contain_text("Analyse opnieuw uitgevoerd")
    assert page.evaluate("dashboardPngModel().settings.signalNight") is False
    assert download_png(page, tmp_path / "rerun.png") != first
    page.evaluate("state.rawRows=[];state.result=analyze([],state.settings);render()")
    with page.expect_download() as pending:
        page.evaluate("exportDashboardPng()")
    pending.value.save_as(tmp_path / "empty.png")
    assert (tmp_path / "empty.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert page.evaluate("dashboardPngModel().signals.length") == 0
    page.evaluate(
        """() => {window.originalToBlob=HTMLCanvasElement.prototype.toBlob;
          HTMLCanvasElement.prototype.toBlob=function(cb){cb(null)}}"""
    )
    page.evaluate("exportDashboardPng()")
    expect(page.locator("#status")).to_contain_text("Dashboard als PNG is mislukt")
    expect(page.locator("#pngBtn")).to_be_enabled()
    page.evaluate("() => {HTMLCanvasElement.prototype.toBlob=window.originalToBlob}")
    with page.expect_download():
        page.evaluate("exportDashboardPng()")
    expect(page.locator("#status")).to_have_text("Dashboard als PNG gedownload.")
    # Long words are wrapped, not ellipsized; oversized images fail explicitly.
    page.evaluate("$('#chartReasons .empty').textContent='Geen gegevens.'")
    assert page.evaluate(
        """() => {const m=dashboardPngModel();
          m.charts[3].rows=[{label:'L'.repeat(1000),value:'1',amount:1}];
          return drawDashboardPng(m).height>0}"""
    )
    assert page.evaluate(
        """() => {const m=dashboardPngModel();m.file='L'.repeat(200000);
          try{drawDashboardPng(m);return false}catch(e){return e.message.includes('te groot')}}"""
    )
    downloads = []
    page.on("download", lambda download: downloads.append(download.suggested_filename))
    page.evaluate(
        """async () => {
          HTMLCanvasElement.prototype.toBlob=function(cb){
            window.originalToBlob.call(this,blob=>setTimeout(()=>cb(blob),50),'image/png');
          };
          const pending=exportDashboardPng();exportDashboardPng();
          state.result=analyze([],state.settings);render();await pending;
          HTMLCanvasElement.prototype.toBlob=window.originalToBlob;
        }"""
    )
    assert not downloads
    expect(page.locator("#status")).to_contain_text("De analyse is intussen gewijzigd")
    page.locator("#fileInput").set_input_files(
        {
            "name": "nieuw.xlsx",
            "mimeType": "application/octet-stream",
            "buffer": STANDARD_FIXTURE.read_bytes(),
        }
    )
    expect(page.locator("#pngBtn")).to_be_disabled()
    page.locator("#analyzeBtn").click()
    page.locator("#workspace.show").wait_for(timeout=30_000)
    assert page.evaluate("dashboardPngModel().file") == "nieuw.xlsx"


def test_overview_visuals_zip_individual_and_offline(page, tmp_path):
    import io
    import zipfile

    expect(page.locator("#visualsZipBtn")).to_be_disabled()
    load_analysis(page)
    # A separator at the 100-character cutoff must not remain before .png.
    assert (
        page.evaluate("visualPngName('base',{title:'A'.repeat(99)+' B'},0)")
        == "base_overzicht_01_" + "a" * 99 + ".png"
    )
    assert (
        page.evaluate("visualPngName('base',{title:' --Cliënten / teams-- '},1)")
        == "base_overzicht_02_clienten-teams.png"
    )
    requests = []
    page.on("request", lambda request: requests.append(request.url))
    drawings = page.evaluate(
        """() => {const model=dashboardPngModel();return overviewPngVisuals(model).map((v,i)=>{
          const lines=[],original=CanvasRenderingContext2D.prototype.fillText;
          CanvasRenderingContext2D.prototype.fillText=function(value,x,y){
            lines.push({value:String(value),x,y,width:this.measureText(value).width,
              size:Number(this.font.match(/([\\d.]+)px/)[1])});
            return original.call(this,value,x,y);
          };
          let c;try{c=drawDashboardPng(v.model,v)}
          finally{CanvasRenderingContext2D.prototype.fillText=original}
          const drawing={name:visualPngName(exportBaseName(),v,i),title:v.title,
            lines,width:c.width,height:c.height};c.width=0;c.height=0;return drawing;
        })}"""
    )
    assert len(drawings) == page.evaluate("22 + dashboardPngModel().signals.length")
    for drawing in drawings:
        text = " ".join(line["value"] for line in drawing["lines"])
        assert drawing["title"] in text
        assert "01-05-2026" in text
        assert "31-05-2026" in text
        assert "geen bewijs van dossierinzage" in text
        assert "persoonsgegevens" in text
        assert drawing["width"] == 1200
        assert 300 < drawing["height"] < 2000
        for line in drawing["lines"]:
            assert 0 <= line["x"] <= drawing["width"] - line["width"]
            assert 0 <= line["y"] <= drawing["height"] - line["size"] * 1.4
    page.set_viewport_size({"width": 390, "height": 844})
    with page.expect_download(timeout=60_000) as pending:
        page.locator("#visualsZipBtn").click()
    path = tmp_path / "visuals.zip"
    pending.value.save_as(path)
    assert pending.value.suggested_filename.endswith("_overzicht_visuals.zip")
    with zipfile.ZipFile(io.BytesIO(path.read_bytes())) as archive:
        assert archive.testzip() is None
        assert archive.namelist() == [drawing["name"] for drawing in drawings]
        for drawing in drawings:
            data = archive.read(drawing["name"])
            assert data[:8] == b"\x89PNG\r\n\x1a\n"
            assert struct.unpack(">II", data[16:24]) == (drawing["width"], drawing["height"])
            assert "/" not in drawing["name"]
            assert "_overzicht_" in drawing["name"]
    assert not requests
    expect(page.locator("#status")).to_contain_text("losse visuals als ZIP gedownload")
    expect(page.locator("#pngBtn")).to_be_enabled()
    expect(page.locator("#visualsZipBtn")).to_be_enabled()
    # Keep a synthetic representative image for visual inspection outside the repo.
    with zipfile.ZipFile(path) as archive:
        heat = next(name for name in archive.namelist() if "tijdheatmap" in name)
        (tmp_path / "heatmap.png").write_bytes(archive.read(heat))


def test_visuals_zip_errors_stale_analysis_and_empty(page):
    load_analysis(page)
    downloads = []
    page.on("download", lambda download: downloads.append(download.suggested_filename))
    page.evaluate(
        """async () => {const original=HTMLCanvasElement.prototype.toBlob;
          HTMLCanvasElement.prototype.toBlob=function(cb){cb(null)};
          await exportOverviewVisualsZip();HTMLCanvasElement.prototype.toBlob=original;
        }"""
    )
    assert not downloads
    expect(page.locator("#status")).to_contain_text("Losse visuals als ZIP is mislukt")
    expect(page.locator("#visualsZipBtn")).to_be_enabled()
    page.evaluate(
        """async () => {const original=HTMLCanvasElement.prototype.toBlob;
          HTMLCanvasElement.prototype.toBlob=function(cb){
            original.call(this,blob=>setTimeout(()=>cb(blob),50),'image/png');
          };
          const pending=exportOverviewVisualsZip();exportOverviewVisualsZip();exportDashboardPng();
          state.result=analyze([],state.settings);render();await pending;
          HTMLCanvasElement.prototype.toBlob=original;
        }"""
    )
    assert not downloads
    expect(page.locator("#status")).to_contain_text("De analyse is intussen gewijzigd")
    with page.expect_download():
        page.evaluate("exportOverviewVisualsZip()")
    expect(page.locator("#status")).to_contain_text("23 losse visuals als ZIP gedownload")
    page.locator("#fileInput").set_input_files(
        {
            "name": "nieuwe-visuals.xlsx",
            "mimeType": "application/octet-stream",
            "buffer": STANDARD_FIXTURE.read_bytes(),
        }
    )
    expect(page.locator("#visualsZipBtn")).to_be_disabled()
