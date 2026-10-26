"""Exercise the generated training file through real controls, entirely offline."""

import importlib.util
import re
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


def assert_controls_reachable(page, modal: bool = False, active: bool = True) -> None:
    """Check complete button bounds and hit-test all edges without scrolling them into view."""
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    selectors = ["#tourResume"]
    if active:
        selectors.append(".tour-footer button:not([hidden])")
    if modal:
        selectors.extend(["#drillCloseBtn", "#drillCsvBtn"])
    failures = page.evaluate(
        """selectors => {
          const banner=document.querySelector('#tourBanner').getBoundingClientRect();
          return selectors.flatMap(selector=>[...document.querySelectorAll(selector)])
            .filter(el=>el.getClientRects().length).flatMap(el=>{
              const r=el.getBoundingClientRect();
              const inside=r.left>=0 && r.right<=innerWidth && r.top>=0 && r.bottom<=innerHeight;
              const points=[[r.left+r.width/2,r.top+2],[r.left+r.width/2,r.bottom-2],
                [r.left+2,r.top+r.height/2],[r.right-2,r.top+r.height/2],
                [r.left+r.width/2,r.top+r.height/2]];
              const hit=points.every(([x,y])=>el.contains(document.elementFromPoint(x,y)));
              const belowBanner=el.id==='tourResume'||r.top>=banner.bottom;
              return inside&&hit&&belowBanner?[]:[{id:el.id,inside,hit,belowBanner,
                top:r.top,bottom:r.bottom,viewport:innerHeight,banner:banner.bottom}];
            });
        }""",
        selectors,
    )
    assert not failures, f"Knoppen zijn afgedekt, afgeknipt of buiten beeld: {failures}"


def click_visible_example(page, selector: str) -> None:
    """Click a visible part of wide table rows, whose geometric center can be offscreen."""
    target = page.locator(selector).first
    if "tbody" not in selector:
        target.click()
        return
    target.evaluate(
        """el => {
          const wrap=el.closest('.table-wrap');
          if(wrap){wrap.scrollTop=0;wrap.scrollIntoView({block:'start',inline:'nearest'});}
        }"""
    )
    point = target.evaluate(
        """el => {
          const r=el.getBoundingClientRect();
          const banner=document.querySelector('#tourBanner').getBoundingClientRect();
          const top=Math.max(r.top,banner.bottom);
          const bottom=Math.min(r.bottom,innerWidth<=1100?
            document.querySelector('#tourPanel').getBoundingClientRect().top:innerHeight,
            innerHeight);
          for(let y=top+6;y<bottom-3;y+=12)
            for(let x=Math.max(6,r.left+6);x<Math.min(r.right,innerWidth)-3;x+=24)
              if(el.contains(document.elementFromPoint(x,y)))return {x,y};
          return null;
        }"""
    )
    assert point, f"Geen zichtbaar aanklikbaar deel van de tabelregel: {selector}"
    page.mouse.click(point["x"], point["y"])


@pytest.mark.parametrize(
    "width,height",
    [
        (1440, 1000),
        (1440, 780),
        (1280, 720),
        (1024, 768),
        (768, 800),
        (494, 779),
        (375, 667),
        (320, 568),
        (844, 390),
    ],
)
def test_tour__complete_route_and_keyboard_controls(tour_page, width: int, height: int) -> None:
    """Every real target remains usable at desktop, tablet and narrow mobile widths."""
    page, errors, requests, downloads = tour_page
    page.set_viewport_size({"width": width, "height": height})
    assert reference_counts(page) == [2000, 156, 42, 1802, 1790]
    steps = page.evaluate("tourSteps.length")
    for index in range(steps):
        expect(page.locator("#tourProgress")).to_have_text(f"Stap {index + 1} van {steps}")
        expect(page.locator("#tourTitle")).to_be_focused()
        expect(page.locator("#tourMarker"), f"Markering bij stap {index + 1}").to_be_visible()
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
        assert_controls_reachable(page)
        if index not in (0, 3, 10):
            assert page.evaluate(
                """() => {
                  const tabs=document.querySelector('#tabs'), active=tabs.querySelector('.active');
                  const r=(active||tabs).getBoundingClientRect();
                  const banner=document.querySelector('#tourBanner').getBoundingClientRect();
                  return r.top>=banner.bottom && r.bottom<=innerHeight && r.left>=0 &&
                    r.right<=innerWidth && tabs.contains(document.elementFromPoint(
                      r.left+r.width/2,r.top+r.height/2)) &&
                    (!active||getComputedStyle(active).backgroundColor==='rgb(160, 42, 133)');
                }"""
            ), "Het actieve tabblad moet zichtbaar, aanklikbaar en gemarkeerd blijven."
        examples = {
            1: "#kpis .kpi",
            2: "#findingList [data-finding]",
            4: "#attentionTable tbody tr[data-row-index]",
            5: "#employeesTable tbody tr[data-row-index]",
            6: "#clientsTable tbody tr[data-row-index]",
            7: "#teamsTable tbody tr[data-row-index]",
            8: "#timeCards .bar-row",
            9: "#qualityTable tbody tr[data-row-index]",
        }
        if index in examples:
            click_visible_example(page, examples[index])
            expect(
                page.locator("#drillOverlay"), f"Bronregels vanuit stap {index + 1}"
            ).to_have_class("drill-overlay show")
            expect(page.locator("#tourHint")).to_contain_text("Bronregels zijn geopend")
            expect(page.locator("#tourMarker")).to_be_hidden()
            assert_controls_reachable(page, modal=True)
            page.evaluate("document.querySelector('#drillBody').scrollTop=500")
            assert_controls_reachable(page, modal=True)
            page.locator("#drillCloseBtn").click()
            expect(page.locator("#drillOverlay")).not_to_have_class("drill-overlay show")
            if index == 1:
                page.locator(examples[index]).first.click()
                expect(page.locator("#tourRestore")).to_be_visible()
                assert_controls_reachable(page, modal=True)
                page.locator("#tourRestore").click()
                expect(page.locator("#drillOverlay")).not_to_have_class("drill-overlay show")
        if index == 3:
            assert_controls_reachable(page, modal=True)
            expect(page.locator("#drillOverlay")).to_have_class("drill-overlay show")
            page.locator("#drillCloseBtn").click()
            expect(page.locator("#tourRestore")).to_be_visible()
            page.locator("#tourRestore").click()
            expect(page.locator("#drillOverlay")).to_have_class("drill-overlay show")
            # Guidance controls participate in the existing dialog keyboard scope.
            assert_controls_reachable(page, modal=True)
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
        if index in (5, 6, 7):
            page.locator("#tourRelated").click()
            expect(page.locator("#view-deepdive")).to_be_visible()
            expect(page.locator("#tourRestore")).to_be_visible()
            assert_controls_reachable(page)
            page.locator("#tourRestore").click()
        # Long explanations scroll independently from the permanent navigation.
        page.locator(".tour-content").evaluate("el => el.scrollTop=el.scrollHeight")
        assert_controls_reachable(page, modal=index == 3)
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
    page.locator("#kpis .kpi").first.click()
    assert_controls_reachable(page, modal=True, active=False)
    page.locator("#drillCloseBtn").click()
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


def test_tour__open_dialog_follows_window_resize_and_stopped_keyboard_scope(tour_page) -> None:
    """Resize an already open dialog and keep hidden guidance outside its focus cycle."""
    page, errors, requests, downloads = tour_page
    page.locator("#tourNext").click()
    page.locator("#kpis .kpi").first.click()
    for width, height in [(1440, 780), (375, 667), (844, 390), (320, 568), (1280, 720)]:
        page.set_viewport_size({"width": width, "height": height})
        assert_controls_reachable(page, modal=True)
    page.locator("#tourStop").click()
    page.locator("#kpis .kpi").first.click()
    assert_controls_reachable(page, modal=True, active=False)
    assert page.locator("#drillOverlay #tourPanel").count() == 0
    page.locator("#drillBody .more-rows-btn").focus()
    page.keyboard.press("Tab")
    expect(page.locator("#drillCsvBtn")).to_be_focused()
    page.locator("#drillCloseBtn").click()
    assert not errors and not requests and not downloads


@pytest.mark.parametrize("change", ["name", "target", "unknown"])
def test_generator__rejects_broken_control_reference(change: str) -> None:
    """An authored reference cannot silently drift away from its real control."""
    html = '<button id="csvBtn">Aandachtspunten CSV</button>'
    refs = {"csv": {"label": "Aandachtspunten CSV", "selector": "#csvBtn"}}
    script = 'text:"[[csv]]"'
    if change == "name":
        html = html.replace("Aandachtspunten CSV", "Andere naam")
    elif change == "target":
        refs["csv"]["selector"] = "#missing"
    else:
        script = 'text:"[[unknown]]"'
    with pytest.raises(ValueError, match=r"knopnaam of doel gewijzigd|onbekende knopverwijzing"):
        generate_tour.validate_references(html, script, refs)


def assert_pointer_reachable(page, selector: str) -> None:
    """The entire real control must be exposed; panel controls stay inside the panel."""
    target = page.locator(selector)
    expect(target).to_have_class(re.compile(r"\btour-pointed\b"))
    if target.is_enabled():
        expect(target).to_be_focused()
    assert target.evaluate(
        """el => {
          const r=el.getBoundingClientRect(),panel=tourPanel.getBoundingClientRect();
          const inside=tourPanel.contains(el);
          const separate=r.bottom<=panel.top || r.top>=panel.bottom ||
            r.right<=panel.left || r.left>=panel.right;
          return r.top>=0 && r.bottom<=innerHeight && r.left>=0 && r.right<=innerWidth &&
            (inside||separate) && [[r.left+r.width/2,r.top+2],[r.left+r.width/2,r.bottom-2],
              [r.left+2,r.top+r.height/2],[r.right-2,r.top+r.height/2]].every(([x,y])=>
                el.contains(document.elementFromPoint(x,y)));
        }"""
    ), f"De volledige aangewezen knop moet zichtbaar blijven: {selector}"


@pytest.mark.parametrize("width,height", [(1440, 1000), (375, 667), (320, 568)])
def test_tour__references_point_without_executing_and_survive_resize(
    tour_page, width: int, height: int
) -> None:
    """Every authored reference exposes its target without activating any app action."""
    page, errors, requests, downloads = tour_page
    page.set_viewport_size({"width": width, "height": height})
    page.evaluate("window.pointerOriginalResult=state.result")
    for index in range(page.evaluate("tourSteps.length")):
        page.evaluate("index => tourShow(index)", index)
        references = page.locator(".tour-reference").evaluate_all(
            "nodes => nodes.map(el=>el.dataset.reference)"
        )
        for key in references:
            reference = page.locator(f'.tour-reference[data-reference="{key}"]')
            selector = page.evaluate("key => tourReferences[key].selector", key)
            target = page.locator(selector)
            available = target.count() and target.is_visible()
            reference.focus()
            page.keyboard.press("Enter")
            if available:
                expect(page.locator("#tourPointerStatus")).to_contain_text("is aangewezen")
                assert_pointer_reachable(page, selector)
                # Resize with this exact mark active, including a desktop/mobile transition.
                other = (
                    {"width": 320, "height": 568} if width != 320 else {"width": 375, "height": 667}
                )
                page.set_viewport_size(other)
                assert_pointer_reachable(page, selector)
                page.set_viewport_size({"width": width, "height": height})
                assert_pointer_reachable(page, selector)
            else:
                expect(page.locator("#tourPointerStatus")).to_contain_text("niet beschikbaar")
                assert page.locator(".tour-pointed").count() == 0
            assert page.evaluate("tour.index") == index, "Aanwijzen mag geen tourstap uitvoeren."
            assert page.evaluate("state.result===window.pointerOriginalResult")
            assert reference_counts(page) == [2000, 156, 42, 1802, 1790]
            assert not downloads, "Een verwijzing mag geen download uitvoeren."
        page.locator("#tourNext").focus()
        page.keyboard.press("Enter")
        assert page.locator(".tour-pointed").count() == 0
    assert not errors and not requests and not downloads


def test_tour__pointer_keyboard_cycle_hidden_target_and_escape(tour_page) -> None:
    """Pointer tabstops participate in the modal cycle and never leave stale success."""
    page, errors, requests, downloads = tour_page
    page.evaluate("tourShow(3)")
    page.locator("#tourTitle").focus()
    page.keyboard.press("Tab")
    expect(page.locator('.tour-reference[data-reference="close"]')).to_be_focused()
    page.keyboard.press("Tab")
    expect(page.locator('.tour-reference[data-reference="restore"]')).to_be_focused()
    page.keyboard.press("Tab")
    expect(page.locator('.tour-reference[data-reference="next"]')).to_be_focused()
    page.locator("#tourReset").focus()
    page.keyboard.press("Tab")
    expect(page.locator("#drillCsvBtn")).to_be_focused()
    page.keyboard.press("Shift+Tab")
    expect(page.locator("#tourReset")).to_be_focused()
    page.locator('.tour-reference[data-reference="close"]').click()
    assert_pointer_reachable(page, "#drillCloseBtn")
    page.locator("#drillCloseBtn").click()
    expect(page.locator("#tourPointerStatus")).to_contain_text("niet zichtbaar")
    assert page.locator(".tour-pointed").count() == 0
    page.evaluate("tourShow(11)")
    page.locator('.tour-reference[data-reference="csv"]').click()
    assert_pointer_reachable(page, "#csvBtn")
    page.keyboard.press("Escape")
    expect(page.locator("#tourPanel")).to_be_hidden()
    assert page.locator(".tour-pointed").count() == 0
    assert not errors and not requests and not downloads


def test_tour__disabled_file_control_is_highlighted_without_opening_picker(tour_page) -> None:
    """Pointing identifies a disabled import control without enabling or focusing it."""
    page, errors, requests, downloads = tour_page
    file_choosers = []
    page.on("filechooser", lambda chooser: file_choosers.append(chooser))
    reference = page.locator('.tour-reference[data-reference="choose"]')
    reference.focus()
    page.keyboard.press("Enter")
    for width, height in [(1440, 1000), (375, 667), (320, 568)]:
        page.set_viewport_size({"width": width, "height": height})
        expect(page.locator("#chooseBtn")).to_be_disabled()
        assert_pointer_reachable(page, "#chooseBtn")
        expect(reference).to_be_focused()
        expect(page.locator("#tourPointerStatus")).to_contain_text("is aangewezen")
        expect(page.locator("#tourPointerStatus")).to_contain_text("knop is uitgeschakeld")
    page.keyboard.press("Escape")
    assert page.locator(".tour-pointed").count() == 0
    expect(page.locator("#chooseBtn")).to_be_disabled()
    assert reference_counts(page) == [2000, 156, 42, 1802, 1790]
    assert not file_choosers and not errors and not requests and not downloads
