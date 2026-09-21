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
