"""Check the real local dashboard PNG with synthetic data only."""

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
            ids:[...document.querySelectorAll(
              '#view-overview [id]:not(#topFindings [id])')].map(x=>x.id),
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
    text = " ".join(line["value"] for line in drawing["lines"])
    assert "Ons Escalatielog Audit · Dashboard" in text
    for title in ("Activatie en herhaling", "Volume en spreiding", "Datakwaliteit"):
        assert title in text
    assert "niet optelbaar" in text
    assert "FAB" not in text and "CISO" not in text and "Privacy Officer" not in text
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
    expected_version = page.evaluate("APP_VERSION")
    assert model["version"] == expected_version
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
        expected_version,
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
    page.locator("#settingsBtn").click()
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
          const drawing={name:visualPngName('',v,i),title:v.title,
            lines,width:c.width,height:c.height};c.width=0;c.height=0;return drawing;
        })}"""
    )
    assert len(drawings) == 8
    for drawing in drawings:
        text = " ".join(line["value"] for line in drawing["lines"])
        assert drawing["title"] in text
        assert "FAB" not in text and "CISO" not in text and "Privacy Officer" not in text
        if drawing["title"] in ("Activatie en herhaling", "Volume en spreiding", "Datakwaliteit"):
            assert "niet optelbaar" in text
        assert "01-05-2026" in text
        assert "31-05-2026" in text
        assert "geen bewijs van dossierinzage" in text
        assert "persoonsgegevens" in text
        assert drawing["width"] == 1200
        assert 300 < drawing["height"] < 3500
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
            assert drawing["name"][:2].isdigit()
    assert not requests
    expect(page.locator("#status")).to_contain_text("losse visuals als ZIP gedownload")
    expect(page.locator("#pngBtn")).to_be_enabled()
    expect(page.locator("#visualsZipBtn")).to_be_enabled()
    # Keep a synthetic representative image for visual inspection outside the repo.
    with zipfile.ZipFile(path) as archive:
        heat = next(name for name in archive.namelist() if "tijdpatroon" in name)
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
    expect(page.locator("#status")).to_contain_text("als ZIP is mislukt")
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
    expect(page.locator("#status")).to_contain_text("8 losse visuals als ZIP gedownload")
    page.locator("#fileInput").set_input_files(
        {
            "name": "nieuwe-visuals.xlsx",
            "mimeType": "application/octet-stream",
            "buffer": STANDARD_FIXTURE.read_bytes(),
        }
    )
    expect(page.locator("#visualsZipBtn")).to_be_disabled()


@pytest.mark.parametrize("index", range(9))
def test_single_png_matches_bundle_or_optional_profile(page, tmp_path, index):
    """Every standard image and the optional profile has a usable individual action."""
    load_analysis(page)
    page.locator("#visualExportsBtn").click()
    page.locator("#visualChoice").select_option(str(index))
    page.context.set_offline(True)
    expected = page.evaluate(
        """i => {const v=overviewPngVisuals(dashboardPngModel(),true)[i];
          const c=drawDashboardPng(v.model,v);const url=c.toDataURL();
          c.width=0;c.height=0;return {url,name:visualPngName(exportBaseName(),v,i)}}""",
        index,
    )
    with page.expect_download() as pending:
        page.locator("#visualPngBtn").click()
    path = tmp_path / "single.png"
    pending.value.save_as(path)
    import base64

    assert path.read_bytes() == base64.b64decode(expected["url"].split(",")[1])
    assert pending.value.suggested_filename == expected["name"]
    assert index < 8 or expected["name"].endswith("09_medewerkerprofiel.png")
    expect(page.locator("#visualPngBtn")).to_be_enabled()
    expect(page.locator("#visualChoice")).to_be_enabled()


def test_curated_content_zero_counts_settings_and_full_labels(page):
    """The curated model preserves zero, disabled, threshold and population semantics."""
    load_analysis(page)
    contents = page.evaluate(
        """() => {
          const m=dashboardPngModel();
          return overviewPngVisuals(m,true).map(v=>{
            const lines=[],original=CanvasRenderingContext2D.prototype.fillText;
            CanvasRenderingContext2D.prototype.fillText=function(t,x,y){lines.push(String(t));
              return original.call(this,t,x,y)};
            try{const c=drawDashboardPng(v.model,v);c.width=0;c.height=0}
            finally{CanvasRenderingContext2D.prototype.fillText=original}
            return lines.join(' ');
          });
        }"""
    )
    summary, findings, signals, heat, clients, employees, teams, reasons, profile = contents
    for value in ("2.000", "156", "42", "1.802", "1.790", "99.3%", "250", "558"):
        assert value in summary
    for text in ("Her-escalaties", "Kerncijfers", "Auditflow", "Verhouding"):
        assert text not in summary
    assert "HERESCALATIE TIJDENS ACTIEVE TOEGANG · 0" in signals
    assert "ZEER SNELLE HERESCALATIE · 0" in signals
    assert "WEEKEND · uitgeschakeld" in signals
    assert "Strikt > 2 min." in signals
    assert "≤ 840 min." in signals
    assert "≥ 15 per medewerker per dag" in signals
    assert "niet optelbaar" in signals
    assert "1.391" in signals and "310" in signals
    assert "Geen ranglijst van ernst of unieke incidenten" in findings
    assert "zonder geldige starttijd" in heat
    assert "niet-geactiveerde" in clients
    for text in (employees, teams, profile):
        assert "geen risicoscore" in text and "caseload" in text
    assert "Genormaliseerde" in reasons
    for text in contents:
        assert text.count("geen bewijs van dossierinzage") == 1
        assert text.count("persoonsgegevens") == 1
    # Values come from the last successful analysis, not unapplied form edits.
    page.locator("#settingsBtn").click()
    page.locator("#set-activationDelayThresholdMinutes").fill("9")
    assert (
        page.evaluate("overviewPngVisuals(dashboardPngModel())[1].context.join(' ')").find(
            "> 2 min."
        )
        >= 0
    )
    page.locator("#rerunBtn").click()
    expect(page.locator("#status")).to_contain_text("Analyse opnieuw uitgevoerd")
    assert "> 9 min." in page.evaluate(
        "overviewPngVisuals(dashboardPngModel())[1].context.join(' ')"
    )


@pytest.mark.parametrize(
    ("action", "change"),
    [
        (action, change)
        for action in ["exportOverviewVisualPng", "exportOverviewVisualsZip"]
        for change in ["top", "analysis", "file", "encoding", "zip"]
        if action == "exportOverviewVisualsZip" or change != "zip"
    ],
)
def test_curated_exports_reject_changes_and_failures_without_partial_download(page, action, change):
    """Async encoding failures and state changes must yield no partial/stale export."""
    load_analysis(page)
    downloads = []
    page.on("download", lambda d: downloads.append(d.suggested_filename))
    result = page.evaluate(
        """async ({action,change}) => {
          const original=HTMLCanvasElement.prototype.toBlob,zip=storedPngZip,canvases=[];
          if(change==='zip')storedPngZip=()=>{throw new Error('Synthetische ZIP-fout')};
          HTMLCanvasElement.prototype.toBlob=function(cb){
            canvases.push(this);
            if(change==='encoding'){cb(null);return}
            original.call(this,blob=>setTimeout(()=>cb(blob),25),'image/png');
          };
          try{
            const pending=window[action]();
            const disabled=['pngBtn','visualsZipBtn','visualPngBtn','visualChoice']
              .every(id=>$('#'+id).disabled);
            exportOverviewVisualPng();exportOverviewVisualsZip();exportDashboardPng();
            if(change==='top')state.findingLimit=1;
            if(change==='analysis'){state.result=analyze([],state.settings);render()}
            if(change==='file')await loadFile(new File(['synthetisch'],'nieuw.xlsx'));
            await pending;
            return {disabled,released:canvases.every(c=>c.width===0&&c.height===0)};
          }finally{HTMLCanvasElement.prototype.toBlob=original;storedPngZip=zip}
        }""",
        {"action": action, "change": change},
    )
    assert not downloads
    expect(page.locator("#status")).to_contain_text("mislukt")
    assert result == {"disabled": True, "released": True}
    if change == "file":
        expect(page.locator("#visualPngBtn")).to_be_disabled()
    else:
        expect(page.locator("#visualPngBtn")).to_be_enabled()


def test_empty_bundle_has_fixed_eight_entries_and_empty_states(page, tmp_path):
    """Empty analyses keep the same manifest, explicit zeroes and valid PNG/ZIP bytes."""
    import zipfile

    load_analysis(page)
    page.evaluate("state.result=analyze([],state.settings);render()")
    names = page.evaluate(
        "overviewPngVisuals(dashboardPngModel()).map((v,i)=>visualPngName('',v,i))"
    )
    assert names == [
        "01_auditsamenvatting.png",
        "02_opvallendheden.png",
        "03_signalen-per-thema.png",
        "04_tijdpatroon.png",
        "05_clientspreiding.png",
        "06_medewerkers.png",
        "07_teams.png",
        "08_redenen.png",
    ]
    with page.expect_download() as pending:
        page.locator("#visualsZipBtn").click()
    path = tmp_path / "empty.zip"
    pending.value.save_as(path)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        assert archive.namelist() == names
        assert all(archive.read(n).startswith(b"\x89PNG\r\n\x1a\n") for n in names)


def test_curated_long_labels_top_fifty_and_viewport_bounds(page):
    """Large Top-X and long source labels stay complete and within canvas boundaries."""
    load_analysis(page)
    page.evaluate("state.findingLimit=50;renderFindings(state.result)")
    result = page.evaluate(
        """() => {
          const m=dashboardPngModel(),expected=findingRows(state.result);
          m.charts[0].rows=[{label:'Volledig label '+ 'L'.repeat(1200),amount:1,value:'1'}];
          const visuals=overviewPngVisuals(m),bad=[],texts=[];
          for(const v of visuals){const lines=[];
            const original=CanvasRenderingContext2D.prototype.fillText;
            CanvasRenderingContext2D.prototype.fillText=function(value,x,y){
              lines.push({text:String(value),x,y,width:this.measureText(value).width,
                height:Number(this.font.match(/([\\d.]+)px/)[1])*1.4});
              return original.call(this,value,x,y)};
            let c;try{c=drawDashboardPng(v.model,v)}
            finally{CanvasRenderingContext2D.prototype.fillText=original}
            bad.push(...lines.filter(l=>l.x<0||l.y<0||l.x+l.width>c.width||l.y+l.height>c.height));
            texts.push(lines.map(l=>l.text).join(' '));c.width=0;c.height=0;
          }
          return {bad,texts,expected,findings:m.findings};
        }"""
    )
    assert not result["bad"]
    assert result["findings"] == result["expected"]
    assert len(result["findings"]) == 50
    assert "50." in result["texts"][1]
    assert result["texts"][4].count("L") >= 1200
    page.locator("#visualExportsBtn").click()
    for width in (390, 1440):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.locator("#visualPngBtn").is_visible()
        assert page.locator("#visualChoice").is_visible()
        bounds = page.locator("#visualChoice").bounding_box()
        assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width


def test_visual_titles_and_slugs_come_from_manifest(page):
    """Titles and slugs come from the manifest, not from call order."""
    load_analysis(page)
    visuals = page.evaluate(
        "overviewPngVisuals(dashboardPngModel(),true).map(v=>({title:v.title,slug:v.slug}))"
    )
    assert [v["title"] for v in visuals] == page.evaluate("[...OVERVIEW_PNG_TITLES]")
    assert [v["slug"] for v in visuals] == [
        "auditsamenvatting",
        "opvallendheden",
        "signalen-per-thema",
        "tijdpatroon",
        "clientspreiding",
        "medewerkers",
        "teams",
        "redenen",
        "medewerkerprofiel",
    ]


def test_theme_card_values_follow_category_key_not_order(page):
    """Each theme card looks up its value by category key, not by position."""
    load_analysis(page)
    result = page.evaluate(
        """() => {
          const visual=overviewPngVisuals(dashboardPngModel(),true)
            .find(v=>v.slug==='signalen-per-thema');
          const model=visual.model;
          const counts=Object.entries(state.result.themeCounts);
          const distinct=new Set(counts.map(([,v])=>v)).size===counts.length;
          model.themes=counts.map(([key,amount],i)=>({
            label:signalCategoryLabel(key),key,
            amount:distinct?amount:1000*(i+1),
            value:fmt(distinct?amount:1000*(i+1))})).reverse();
          const lines=[],original=CanvasRenderingContext2D.prototype.fillText;
          CanvasRenderingContext2D.prototype.fillText=function(value,x,y){
            lines.push(String(value));return original.call(this,value,x,y)};
          try{const canvas=drawDashboardPng(model,visual);canvas.width=0;canvas.height=0}
          finally{CanvasRenderingContext2D.prototype.fillText=original}
          return {lines,themes:model.themes.map(t=>({key:t.key,value:t.value})),
            groups:pngSignalGroups(model.settings).map(g=>({key:g.key,title:g.title}))};
        }"""
    )
    values = {theme["key"]: theme["value"] for theme in result["themes"]}
    lines = result["lines"]
    for group in result["groups"]:
        position = lines.index(group["title"])
        assert lines[position + 1] == f"{values[group['key']]} unieke regels"
