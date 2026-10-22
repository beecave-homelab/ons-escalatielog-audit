"""Overview chart grid layout (#116) and the single-PNG export toggle (#114)."""

import os
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser

WEBUI = Path(os.environ.get("AUDIT_WEBUI_HTML", ROOT / "escalatielog-audit-webui.html"))

CHARTS = ["#employeeScatter", "#chartEmployees", "#chartTeams", "#clientBreadth", "#chartReasons"]
TITLES = [
    "Medewerkerprofiel: volume × cliëntspreiding",  # noqa: RUF001 -- exact h3 text
    "Meeste escalaties per medewerker",
    "Meest voorkomende teams",
    "Cliënten met veel verschillende medewerkers",
    "Meest voorkomende redenen",
]


def analyze(page) -> None:
    """Run the standard analysis through the normal upload flow."""
    page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
    page.locator("#analyzeBtn").click()
    page.locator("#workspace.show").wait_for(timeout=30_000)


def chart_card_boxes(page) -> list:
    """Return the card bounding boxes of the five overview charts in DOM order."""
    return page.evaluate(
        """selectors => selectors.map(sel => {
          const card = document.querySelector(sel).closest('.card'),
            r = card.getBoundingClientRect();
          return {id: sel, top: r.top, left: r.left, right: r.right,
                  bottom: r.bottom, width: r.width};
        })""",
        CHARTS,
    )


@pytest.mark.parametrize("width", [1440, 1100])
def test_overview_charts_three_rows_at_wide_viewport(width) -> None:
    """The scatter spans the grid; two aligned half-width rows sit below it."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.goto(WEBUI.as_uri())
        analyze(page)
        scatter, employees, teams, clients, reasons = chart_card_boxes(page)
        grid_width = page.evaluate(
            "document.querySelector('.overview-charts').getBoundingClientRect().width"
        )
        assert abs(scatter["width"] - grid_width) <= 1, (
            "De scatterkaart beslaat niet de volledige rasterbreedte."
        )
        fill = page.evaluate(
            """() => {const el=document.querySelector('#employeeScatter');
              return {w: el.getBoundingClientRect().width,
                      cw: el.closest('.card').clientWidth - 34}}"""
        )
        assert fill["w"] >= 0.9 * fill["cw"], "De scatter gebruikt de kaartbreedte niet."
        for left, right in ((employees, teams), (clients, reasons)):
            assert abs(left["top"] - right["top"]) <= 1, (
                f"{left['id']} en {right['id']} staan niet op één rij."
            )
            assert abs(left["width"] - right["width"]) <= 1, (
                f"{left['id']} en {right['id']} hebben geen gelijke breedte."
            )
            assert left["left"] < right["left"], f"{left['id']} staat niet links van {right['id']}."
        col_gap2 = teams["left"] - employees["right"]
        col_gap3 = reasons["left"] - clients["right"]
        assert abs(col_gap2 - col_gap3) <= 1, (
            f"De kolomafstand verschilt per rij: {col_gap2} versus {col_gap3}."
        )
        row_gap2 = employees["top"] - scatter["bottom"]
        row_gap3 = clients["top"] - employees["bottom"]
        assert abs(row_gap2 - row_gap3) <= 1, (
            f"De rijafstand loopt uiteen: {row_gap2} versus {row_gap3}."
        )
        assert scatter["top"] < employees["top"] < clients["top"], (
            "De drie rijen staan niet in oplopende volgorde."
        )
        assert abs(employees["left"] - clients["left"]) <= 1
        assert abs(teams["left"] - reasons["left"]) <= 1
        browser.close()


@pytest.mark.parametrize("width", [800, 390])
def test_overview_charts_stack_at_narrow_viewport(width) -> None:
    """The five cards stack in reading order without overflow or overlap."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": width, "height": 844})
        page.goto(WEBUI.as_uri())
        analyze(page)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
            "De pagina heeft horizontale overflow."
        )
        boxes = chart_card_boxes(page)
        lefts = [box["left"] for box in boxes]
        assert max(lefts) - min(lefts) <= 1, "De kaarten vormen geen enkele kolom."
        tops = [box["top"] for box in boxes]
        assert tops == sorted(set(tops)), "De kaarten stapelen niet in de beoogde volgorde."
        for index, first in enumerate(boxes):
            for second in boxes[index + 1 :]:
                overlap = not (
                    first["bottom"] <= second["top"] + 1
                    or second["bottom"] <= first["top"] + 1
                    or first["right"] <= second["left"] + 1
                    or second["right"] <= first["left"] + 1
                )
                assert not overlap, f"{first['id']} overlapt met {second['id']}."
        browser.close()


def test_overview_charts_keep_titles_data_and_drilldown() -> None:
    """Titles, counts and the bar-row drilldown are unchanged by the reorder."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(WEBUI.as_uri())
        analyze(page)
        titles = page.evaluate(
            """selectors => selectors.map(sel =>
              document.querySelector(sel).closest('.card').querySelector('h3')
                .textContent)""",
            CHARTS,
        )
        assert titles == TITLES, f"Grafiektitels wijken af: {titles}"
        assert page.locator("#employeeScatter .scatter-dot").count() == page.evaluate(
            "state.result.employees.length"
        ), "Het aantal scatterpunten wijkt af van het aantal medewerkers."
        for selector in ("#chartEmployees", "#chartTeams", "#clientBreadth", "#chartReasons"):
            assert page.locator(f"{selector} .bar-row").count() > 0, (
                f"{selector} bevat geen balken."
            )
        label = page.locator("#chartTeams .bar-row .bar-label").first.text_content()
        page.locator("#chartTeams .bar-row").first.click()
        expect(page.locator("#drillOverlay")).to_have_class(re.compile(r"\bshow\b"))
        expect(page.locator("#drillTitle")).to_have_text(label)
        browser.close()


def test_single_png_toggle_in_export_actions() -> None:
    """The toggle sits next to the ZIP action and drives the panel by click and keys."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(WEBUI.as_uri())
        analyze(page)
        toggle = page.locator("#visualExportsBtn")
        assert (
            page.evaluate("document.querySelector('#visualsZipBtn').nextElementSibling.id")
            == "visualExportsBtn"
        ), "De toggle volgt niet direct op de ZIP-knop."
        assert page.evaluate(
            "document.querySelector('#visualExportsBtn').parentElement.classList"
            ".contains('export-actions')"
        ), "De toggle staat niet in de exportacties."
        zip_top = page.evaluate(
            "document.querySelector('#visualsZipBtn').getBoundingClientRect().top"
        )
        box = toggle.bounding_box()
        assert abs(box["y"] - zip_top) <= 1, "De toggle staat niet naast de ZIP-knop."
        assert box["x"] > page.locator("#visualsZipBtn").bounding_box()["x"]
        assert page.locator("details#visualExports").count() == 0
        assert page.locator("#visualExports summary").count() == 0
        expect(page.locator("#visualExports")).to_be_hidden()
        expect(toggle).to_have_attribute("aria-expanded", "false")
        toggle.click()
        expect(page.locator("#visualExports")).to_be_visible()
        expect(toggle).to_have_attribute("aria-expanded", "true")
        expect(page.locator("#visualChoice")).to_be_visible()
        expect(page.locator("#visualChoice")).to_be_enabled()
        expect(page.locator("#visualPngBtn")).to_be_visible()
        expect(page.locator("#visualPngBtn")).to_be_enabled()
        toggle.click()
        expect(page.locator("#visualExports")).to_be_hidden()
        expect(toggle).to_have_attribute("aria-expanded", "false")
        toggle.focus()
        toggle.press("Enter")
        expect(page.locator("#visualExports")).to_be_visible()
        toggle.press("Space")
        expect(page.locator("#visualExports")).to_be_hidden()
        toggle.click()
        page.locator("#visualChoice").focus()
        page.keyboard.press("Escape")
        expect(page.locator("#visualExports")).to_be_hidden()
        expect(toggle).to_be_focused()
        browser.close()


def test_single_png_toggle_no_overflow_at_390() -> None:
    """Closed and open, the export row stays inside the viewport at 390px."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(WEBUI.as_uri())
        analyze(page)
        for _ in range(2):
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                "De pagina heeft horizontale overflow."
            )
            buttons = page.evaluate(
                """() => [...document.querySelectorAll('.export-actions .btn')]
                  .filter(b => b.getBoundingClientRect().width > 0)
                  .map(b => ({id: b.id, rect: b.getBoundingClientRect(),
                              scrollWidth: b.scrollWidth, clientWidth: b.clientWidth}))"""
            )
            for button in buttons:
                rect = button["rect"]
                assert rect["left"] >= -1 and rect["right"] <= 391, (
                    f"{button['id']} valt buiten de viewport."
                )
                assert button["scrollWidth"] <= button["clientWidth"], (
                    f"De tekst van {button['id']} wordt afgekapt."
                )
            page.locator("#visualExportsBtn").click()
        browser.close()
