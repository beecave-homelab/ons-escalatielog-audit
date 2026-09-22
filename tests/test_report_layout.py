import os
import shutil
import sys
from pathlib import Path

import pytest
from generate_synthetic_escalatielog import create_workbook, main, synthetic_rows
from playwright.sync_api import Error, Playwright, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
STANDARD_FIXTURE = ROOT / "tests/fixtures/synthetic-escalatielog.xlsx"


def launch_browser(playwright: Playwright):
    failures = []
    for channel in ("chrome", "msedge"):
        try:
            return playwright.chromium.launch(channel=channel, headless=True)
        except Error as error:
            failures.append(f"{channel}: {error.message.splitlines()[0]}")

    executable_candidates = [
        os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for executable_path in filter(None, executable_candidates):
        try:
            return playwright.chromium.launch(executable_path=executable_path, headless=True)
        except Error as error:
            failures.append(f"{executable_path}: {error.message.splitlines()[0]}")

    try:
        return playwright.chromium.launch(headless=True)
    except Error as error:
        failures.append(f"playwright-chromium: {error.message.splitlines()[0]}")

    failure_details = "; ".join(failures)
    message = "Geen bruikbare Chrome-, Edge- of Chromium-installatie gevonden."
    pytest.fail(f"{message} {failure_details}")


def inspect_layout(page, width: int, media: str) -> dict:
    page.set_viewport_size({"width": width, "height": 900})
    page.emulate_media(media=media)
    page.reload(wait_until="load")
    closed_before_print = page.locator("details:not([open])").count()
    if media == "print":
        page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
    else:
        page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
    return page.evaluate(
        """closedBeforePrint => {
          const wrappers = [...document.querySelectorAll('.table-scroll')];
          const tables = [...document.querySelectorAll('table')];
          return {
            closedBeforePrint,
            allDetailsOpen: [...document.querySelectorAll('details')].every(detail => detail.open),
            bodyContained: document.body.scrollWidth <= innerWidth,
            wrapperCount: wrappers.length,
            wrappersContained: wrappers.every(
              wrapper => wrapper.getBoundingClientRect().right <= innerWidth
            ),
            malformedTables: tables.filter(
              table => [...table.tBodies[0].rows].some(
                row => [...row.cells].reduce((sum,cell) => sum + cell.colSpan,0)
                  !== table.tHead.rows[0].cells.length
              )
            ).length,
            wideTables: wrappers
              .filter(wrapper => wrapper.scrollWidth > wrapper.clientWidth)
              .map(wrapper => (
                wrapper.closest('details')?.querySelector('summary')?.textContent
                || wrapper.previousElementSibling?.textContent || ''
              ).trim()),
            printTablesFit: wrappers.every(
              wrapper => wrapper.querySelector('table').getBoundingClientRect().width
                <= wrapper.clientWidth + 1
            ),
          };
        }""",
        closed_before_print,
    )


def inspect_toc(page) -> dict:
    return page.evaluate(
        """() => {
          const links = [...document.querySelectorAll('.toc a')];
          const targets = links.map(link => document.querySelector(link.hash));
          return {
            linkCount: links.length,
            uniqueTargetCount: new Set(targets).size,
            allTargetsExist: targets.every(Boolean),
          };
        }"""
    )


def test_synthetic_export_is_reproducible(tmp_path: Path) -> None:
    first = tmp_path / "first.xlsx"
    second = tmp_path / "second.xlsx"
    different = tmp_path / "different.xlsx"

    standard = tmp_path / "standard.xlsx"
    first_digest = create_workbook(first, 200, 20260918)
    second_digest = create_workbook(second, 200, 20260918)
    different_digest = create_workbook(different, 200, 20260919)
    create_workbook(standard, 2000, 20260918)

    assert first_digest == second_digest
    assert first.read_bytes() == second.read_bytes()
    assert first_digest != different_digest
    assert standard.read_bytes() == STANDARD_FIXTURE.read_bytes()
    assert len(synthetic_rows(5, 1)) == 6
    with pytest.raises(ValueError, match="minimaal 1"):
        synthetic_rows(0, 1)


def test_generator_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    output = tmp_path / "cli.xlsx"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_synthetic_escalatielog.py",
            "--output",
            str(output),
            "--rows",
            "10",
            "--seed",
            "42",
            "--profile",
            "mixed",
        ],
    )

    main()

    result = capsys.readouterr().out
    assert output.is_file()
    assert "Regels: 10" in result
    assert "Seed: 42" in result
    assert "SHA-256:" in result


def test_drilldown_column_filters_and_full_csv(tmp_path: Path) -> None:
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(accept_downloads=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        page.evaluate(
            """() => {
              const rows = [
                {sourceRow: 2, employeeTeam: 'Team <A>', expertise: 'Verpleegkundige',
                 targetType: 'Cliënt', signals: ['Nacht']},
                {sourceRow: 3, employeeTeam: 'Team <A>', expertise: 'Arts',
                 targetType: 'Locatie', signals: []},
                {sourceRow: 4, employeeTeam: 'Team B', expertise: 'Arts',
                 targetType: 'Cliënt', signals: ['Nacht']},
              ];
              openDrilldown('Test', rows);
            }"""
        )
        filters = page.locator("#drillBody .column-filter")
        assert filters.count() == 4
        team = page.get_by_role("combobox", name="Filter op Medewerkersteam")
        assert team.locator("option").all_text_contents() == [
            "Alle medewerkersteam",
            "Team <A>",
            "Team B",
        ]
        assert page.locator("#drillBody option[value='Team <A>']").count() == 1
        assert page.locator("#drillBody option[value='Team <A>'] b").count() == 0
        assert page.locator(".drill-count").text_content() == "3 van 3"
        team.focus()
        assert team.evaluate("element => document.activeElement === element")
        team.select_option("Team B")
        assert page.locator(".drill-count").text_content() == "1 van 3"
        team.select_option("Team <A>")
        page.get_by_role("combobox", name="Filter op Deskundigheid medewerker").select_option(
            "Arts"
        )
        assert page.locator(".drill-count").text_content() == "1 van 3"
        page.get_by_role("textbox", name="Zoek bronregels").fill("Cliënt")
        assert page.locator(".drill-count").text_content() == "0 van 3"
        page.get_by_role("textbox", name="Zoek bronregels").fill("Locatie")
        assert page.locator(".drill-count").text_content() == "1 van 3"
        assert page.locator("#drillBody tbody tr:visible").count() == 1
        page.locator("#drillOverlay").screenshot(path=str(tmp_path / "drilldown-filters.png"))
        with page.expect_download() as download_info:
            page.locator("#drillCsvBtn").click()
        csv_file = tmp_path / "bronregels.csv"
        download_info.value.save_as(csv_file)
        assert len(csv_file.read_text(encoding="utf-8-sig").splitlines()) == 4
        page.locator("#drillCloseBtn").click()
        page.evaluate("openDrilldown('Leeg', [])")
        assert page.locator(".drill-count").text_content() == "0 van 0"
        assert not errors
        browser.close()


def test_drilldown_focus_trap_includes_select_filters(tmp_path: Path) -> None:
    """The four <select> column filters must be reachable by Tab/Shift+Tab."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        page.evaluate(
            """() => {
              const rows = [
                {sourceRow: 2, employeeTeam: 'Team A', expertise: 'Verpleegkundige',
                 targetType: 'Cliënt', signals: ['Nacht']},
                {sourceRow: 3, employeeTeam: 'Team B', expertise: 'Arts',
                 targetType: 'Locatie', signals: []},
              ];
              openDrilldown('Test', rows);
            }"""
        )

        # Collect focusable elements in DOM order inside the dialog.
        focusable = page.evaluate(
            """() => {
              const overlay = document.getElementById('drillOverlay');
              const sel = 'button, input, select, textarea, [tabindex="0"]';
              return [...overlay.querySelectorAll(sel)]
                .filter(el => !el.disabled)
                .map(el => ({
                  tag: el.tagName.toLowerCase(),
                  id: el.id || null,
                  label: el.getAttribute('aria-label') || null,
                  type: el.type || null,
                }));
            }"""
        )

        # The dialog must contain the close button, CSV button, search input,
        # and four <select> filters.
        tags = [el["tag"] for el in focusable]
        assert "select" in tags, f"No <select> in focusable set: {focusable}"
        select_count = tags.count("select")
        assert select_count == 4, f"Expected 4 selects in focus loop, got {select_count}"

        # Simulate Tab traversal: the focusable order is:
        #   1. drillCsvBtn (button)
        #   2. drillCloseBtn (button)
        #   3. drillExplanation (tabindex="0")
        #   4. drill-search (input)
        #   5-8. four selects
        # The last element is the 4th select (Auditcontext).

        search = page.get_by_role("textbox", name="Zoek bronregels")
        last_select = page.get_by_role("combobox", name="Filter op Auditcontext")
        csv_btn = page.locator("#drillCsvBtn")

        # Focus the search input, Tab forward, should reach the first select.
        search.focus()
        page.keyboard.press("Tab")
        active_label = page.evaluate("() => document.activeElement?.getAttribute('aria-label')")
        assert active_label == "Filter op Medewerkersteam", (
            f"Tab from search should reach first select, got: {active_label}"
        )

        # Shift+Tab from the first select should go back to search.
        page.keyboard.press("Shift+Tab")
        active_label = page.evaluate("() => document.activeElement?.getAttribute('aria-label')")
        assert active_label == "Zoek bronregels", (
            f"Shift+Tab from first select should reach search, got: {active_label}"
        )

        # Focus the last element (Auditcontext select), Tab forward should
        # wrap to the first focusable (CSV button).
        last_select.focus()
        page.keyboard.press("Tab")
        active_id = page.evaluate("() => document.activeElement?.id")
        assert active_id == "drillCsvBtn", (
            f"Tab from last element should wrap to drillCsvBtn, got: {active_id}"
        )

        # Shift+Tab from the first element (CSV button) should wrap to last.
        csv_btn.focus()
        page.keyboard.press("Shift+Tab")
        active_label = page.evaluate("() => document.activeElement?.getAttribute('aria-label')")
        assert active_label == "Filter op Auditcontext", (
            f"Shift+Tab from CSV button should wrap to last select, got: {active_label}"
        )

        assert not errors
        browser.close()


def test_drilldown_sticky_header_offset_below_filter_bar(tmp_path: Path) -> None:
    """Sticky table headers must sit below the sticky filter bar, not under it."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1280, "height": 400})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())

        # Generate enough rows to make the drilldown body scroll.
        rows = [
            {
                "sourceRow": i + 2,
                "employeeTeam": "Team A" if i % 2 == 0 else "Team B",
                "expertise": "Verpleegkundige" if i % 3 == 0 else "Arts",
                "targetType": "Cliënt" if i % 2 == 0 else "Locatie",
                "signals": ["Nacht"] if i % 5 == 0 else [],
            }
            for i in range(60)
        ]
        page.evaluate("""(rows) => openDrilldown('Scroll Test', rows)""", rows)

        # Wait for the filter bar to render and the offset to be applied.
        page.wait_for_selector("#drillBody .drill-filters")
        page.wait_for_function(
            """() => {
              const body = document.getElementById('drillBody');
              const v = body.style.getPropertyValue('--drill-filter-offset');
              return v && parseFloat(v) > 0;
            }"""
        )

        measurements = page.evaluate(
            """() => {
              const body = document.getElementById('drillBody');
              const filterBar = body.querySelector('.drill-filters');
              const th = body.querySelector('th');
              if (!filterBar || !th) return null;
              const filterRect = filterBar.getBoundingClientRect();
              const thRect = th.getBoundingClientRect();
              const thTop = parseFloat(getComputedStyle(th).top) || 0;
              return {
                filterHeight: filterRect.height,
                cssOffset: body.style.getPropertyValue('--drill-filter-offset'),
                computedThTop: thTop,
                // When scrolled, the th should stick at filterHeight (not 0).
                thRectTopAfterScroll: null, // filled after scroll
                filterRectTopAfterScroll: null,
              };
            }"""
        )
        assert measurements is not None, "Filter bar or th not found"

        # The CSS variable must match the filter bar's rendered height.
        filter_height = measurements["filterHeight"]
        css_offset_px = float(measurements["cssOffset"].replace("px", ""))
        assert abs(css_offset_px - filter_height) < 1, (
            f"CSS offset {css_offset_px} != filter bar height {filter_height}"
        )

        # The computed top of the th must equal the filter bar height, not 0.
        assert measurements["computedThTop"] > 0, (
            f"th top should be > 0 (offset below filter bar), got {measurements['computedThTop']}"
        )
        assert abs(measurements["computedThTop"] - filter_height) < 1, (
            f"th top {measurements['computedThTop']} != filter height {filter_height}"
        )

        # Scroll the drilldown body down so the header would normally stick at top:0.
        page.evaluate(
            """() => {
              document.getElementById('drillBody').scrollTop = 200;
            }"""
        )
        page.wait_for_timeout(100)

        overlap = page.evaluate(
            """() => {
              const body = document.getElementById('drillBody');
              const filterBar = body.querySelector('.drill-filters');
              const th = body.querySelector('th');
              const fr = filterBar.getBoundingClientRect();
              const tr = th.getBoundingClientRect();
              // Both are sticky inside .drill-body. Get their position relative
              // to the drill-body container.
              const bodyRect = body.getBoundingClientRect();
              return {
                filterTopRel: fr.top - bodyRect.top,
                filterBottomRel: fr.bottom - bodyRect.top,
                thTopRel: tr.top - bodyRect.top,
                thBottomRel: tr.bottom - bodyRect.top,
              };
            }"""
        )

        # The th top (relative to scroll container) should be at or below
        # the filter bar bottom, meaning the header is NOT hidden behind it.
        assert overlap["thTopRel"] >= overlap["filterBottomRel"] - 1, (
            f"th top {overlap['thTopRel']} should be >= filter bottom "
            f"{overlap['filterBottomRel']} (header hidden behind filter bar)"
        )

        assert not errors
        browser.close()


def test_exported_report_tables_stay_aligned(tmp_path: Path) -> None:
    workbook = tmp_path / "synthetisch-escalatielog.xlsx"
    report = tmp_path / "synthetisch-rapport.html"
    create_workbook(workbook, 24, 20260918, "layout")

    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        console_errors = []
        page.on(
            "console",
            lambda message: (
                console_errors.append(message.text) if message.type == "error" else None
            ),
        )
        page.on("pageerror", lambda error: console_errors.append(str(error)))
        app_url = (ROOT / "escalatielog-audit-webui.html").as_uri()
        page.goto(app_url, wait_until="load")
        page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
        page.locator("#analyzeBtn").click()
        page.locator("#workspace.show").wait_for(timeout=30_000)
        assert page.locator("#kpis .value").all_text_contents() == [
            "1.802",
            "1.790",
            "250",
            "558",
            "0",
            "310",
        ]
        assert "2.000 logregels ingelezen" in page.locator("#status").text_content()
        peer_guidance = page.locator("#peerGuidance")
        assert "waarde van de medewerker gedeeld door de mediaan" in peer_guidance.text_content()
        assert all(ratio in peer_guidance.text_content() for ratio in ("0,50", "1,00", "2,00"))
        assert peer_guidance.locator("tbody tr").count() == 4
        peer_guidance.locator("details").evaluate("detail => detail.open = true")
        assert "13 escalaties ÷ mediaan 6 = ratio 2,17" in peer_guidance.text_content()

        page.locator('.tab[data-view="deepdive"]').click()
        page.locator("#peerTable tbody tr").first.click()
        assert (
            page.locator("#drillTitle").text_content().startswith("Bronregels achter peeranalyse ·")
        )
        page.locator("#drillCloseBtn").click()

        page.goto(app_url, wait_until="load")
        page.locator("#fileInput").set_input_files(workbook)
        page.locator("#analyzeBtn").click()
        page.locator("#workspace.show").wait_for(timeout=30_000)

        assert page.locator("#kpis .value").all_text_contents() == [
            "24",
            "24",
            "12",
            "24",
            "0",
            "24",
        ]

        with page.expect_download() as download_info:
            page.locator("#reportBtn").click()
        download_info.value.save_as(report)
        page.goto(report.as_uri(), wait_until="load")

        report_guidance = page.locator(".peer-ratio-guidance")
        assert report_guidance.count() == 1
        assert report_guidance.locator("tbody tr").count() == 4
        assert "geen oordeel of risicoscore" in report_guidance.text_content()
        assert "13 escalaties ÷ mediaan 6 = ratio 2,17" in report_guidance.text_content()
        peer_section = page.locator("#s-peer")
        assert peer_section.locator(":scope > .peer-ratio-guidance").count() == 1
        assert report_guidance.evaluate("guidance => guidance.parentElement?.id") == "s-peer"
        peer_section.evaluate("section => section.open = false")
        assert not report_guidance.is_visible()
        peer_section.locator(":scope > summary").click()
        assert report_guidance.is_visible()

        auditflow_section = page.locator("#s-auditflow")
        assert auditflow_section.locator("table.flow tbody tr").count() == 5
        assert "duplicaatkopieën + auditpopulatie" in auditflow_section.text_content()
        auditflow_section.evaluate("section => section.open = false")
        assert not auditflow_section.locator("table.flow").is_visible()
        auditflow_section.locator(":scope > summary").click()
        assert auditflow_section.locator("table.flow").is_visible()

        signalen_section = page.locator("#s-signalen")
        theme_bars = signalen_section.locator(".r-bars .r-row")
        assert theme_bars.count() == 4
        assert theme_bars.first.locator("strong").text_content() == "24"
        assert "in elk daarvan eenmaal" in signalen_section.text_content()

        tijd_section = page.locator("#s-tijd")
        heat_tables = tijd_section.locator("table.heat")
        assert heat_tables.count() == 2
        heat_sum = page.evaluate(
            """() => [...document.querySelectorAll('#s-tijd table.heat td')]
              .reduce((sum, cell) => sum + (Number(cell.textContent) || 0), 0)"""
        )
        assert heat_sum == 24
        peak_cell = tijd_section.locator("td").filter(has_text="24")
        assert peak_cell.count() == 1
        assert (
            peak_cell.evaluate("cell => getComputedStyle(cell).backgroundColor")
            == "rgb(157, 47, 132)"
        )
        assert "niet alle medewerkers" in page.locator("#s-medewerkers").text_content()
        assert "niet alle cliënten" in page.locator("#s-clienten").text_content()
        assert "Som van alle cellen" in tijd_section.text_content()
        tijd_section.evaluate("section => section.open = false")
        assert not tijd_section.locator("table.heat").first.is_visible()
        tijd_section.locator(":scope > summary").click()
        assert tijd_section.locator("table.heat").first.is_visible()

        for section_id in ("#s-medewerkers", "#s-clienten"):
            section = page.locator(section_id)
            assert section.locator(".r-bars .r-row").count() > 0
            assert "Leeswijzer top" in section.text_content()

        toc_result = inspect_toc(page)
        page.locator('.toc a[href="#s-peer"]').click()
        page.wait_for_function("location.hash === '#s-peer'")
        toc_hash = page.evaluate("location.hash")
        screen_results = [inspect_layout(page, width, "screen") for width in (1280, 800)]
        print_results = [inspect_layout(page, width, "print") for width in (1280, 800)]
        browser.close()

    assert not console_errors
    assert toc_result == {
        "linkCount": 21,
        "uniqueTargetCount": 21,
        "allTargetsExist": True,
    }
    assert toc_hash == "#s-peer"
    for result in screen_results:
        assert result["bodyContained"]
        assert result["wrapperCount"] >= 8
        assert result["wrappersContained"]
        assert result["malformedTables"] == 0
        assert any(t.startswith("Aandachtspunten") for t in result["wideTables"])
        assert any(t.startswith("Peeranalyse") for t in result["wideTables"])
    for result in print_results:
        assert result["closedBeforePrint"] > 0
        assert result["allDetailsOpen"]
        assert result["bodyContained"]
        assert result["wrappersContained"]
        assert result["malformedTables"] == 0
        assert result["printTablesFit"]
