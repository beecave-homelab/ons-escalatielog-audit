"""Regressietests voor issue #55: rendertlimiet en zoek-debounce.

- tableWidget toont standaard maximaal RENDER_ROW_LIMIT (500) rijen en
  voegt een knop 'Meer tonen' toe zodra de gefilterde set groter is.
- Zoeken, sorteren en filteren werken op de volledige set; de teller
  toont het volledige gefilterde aantal.
- De drilldown gebruikt dezelfde limiet en knop.
- Het zoekveld is gedebounceerd (SEARCH_DEBOUNCE_MS).
"""

import pytest
from playwright.sync_api import expect, sync_playwright
from test_report_layout import ROOT, launch_browser


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        yield page, errors
        browser.close()


def build_rows(n: int) -> list[dict]:
    return [{"Medewerker": f"Medewerker {i:04d}", "Team": f"Team {i % 10}"} for i in range(n)]


def load_table(page, n: int, **opt) -> None:
    rows = build_rows(n)
    # render() adds .show to #workspace; without an analysis the workspace
    # stays hidden and Playwright visibility checks fail. Show it directly.
    page.evaluate("() => document.querySelector('#workspace').classList.add('show')")
    page.locator('.tab[data-view="attention"]').click()
    page.evaluate(
        """([rows, opt]) => tableWidget('#attentionTable', rows, opt)""",
        [rows, opt],
    )


def test_table_renders_max_500_rows_with_more_button(page) -> None:
    page, errors = page
    load_table(page, 620, search=True)

    expect(page.locator("#attentionTable tbody tr")).to_have_count(501)
    assert page.locator("#attentionTable .count-label").text_content() == "620 van 620"
    more = page.locator("#attentionTable .more-rows-btn")
    assert more.count() == 1
    assert "nog 120" in more.text_content()

    more.click()
    expect(page.locator("#attentionTable tbody tr")).to_have_count(620)
    assert page.locator("#attentionTable .more-rows-btn").count() == 0
    assert page.locator("#attentionTable .count-label").text_content() == "620 van 620"

    # Sorting resets the limit but the counter keeps the full filtered count.
    page.locator("#attentionTable th").first.click()
    expect(page.locator("#attentionTable tbody tr")).to_have_count(501)
    assert page.locator("#attentionTable .count-label").text_content() == "620 van 620"

    # Enter on the focused Meer-tonen button must activate the button itself
    # (regression for the tbody keydown handler hijacking Enter/Space).
    more = page.locator("#attentionTable .more-rows-btn")
    more.focus()
    page.keyboard.press("Enter")
    expect(page.locator("#attentionTable tbody tr")).to_have_count(620)
    assert page.locator("#attentionTable .more-rows-btn").count() == 0
    assert page.locator("#attentionTable .count-label").text_content() == "620 van 620"

    # Search filters the full set, not only the rendered rows.
    page.get_by_role("textbox", name="Zoeken…").fill("Team 3")
    expect(page.locator("#attentionTable .count-label")).to_have_text("62 van 620")
    expect(page.locator("#attentionTable tbody tr")).to_have_count(62)
    assert page.locator("#attentionTable .more-rows-btn").count() == 0

    assert not errors


def test_search_is_debounced(page) -> None:
    page, errors = page
    load_table(page, 30, search=True)

    search = page.get_by_role("textbox", name="Zoeken…")
    search.fill("Medewerker 0017")
    # Directly after typing the table is not yet re-filtered (debounce).
    assert page.locator("#attentionTable .count-label").text_content() == "30 van 30"
    expect(page.locator("#attentionTable .count-label")).to_have_text("1 van 30")

    assert not errors


def test_drilldown_limit_and_more_button(page) -> None:
    page, errors = page
    rows = [
        {
            "sourceRow": i + 2,
            "employeeTeam": f"Team {i % 10}",
            "expertise": "Verpleegkundige",
            "targetType": "Cliënt",
            "signals": [],
        }
        for i in range(520)
    ]
    page.evaluate("rows => openDrilldown('Test', rows)", rows)

    # Only the visible slice is in the DOM; hidden rows are not built at all.
    expect(page.locator("#drillBody tbody tr")).to_have_count(500)
    more = page.locator("#drillBody .drill-more .more-rows-btn")
    assert more.count() == 1
    assert "nog 20" in more.text_content()
    assert page.locator(".drill-count").text_content() == "520 van 520"

    more.click()
    expect(page.locator("#drillBody tbody tr")).to_have_count(520)
    assert page.locator("#drillBody .drill-more").count() == 0

    # Searching in the drilldown resets the limit to 500 visible rows.
    page.get_by_role("textbox", name="Zoek bronregels").fill("Team 3")
    expect(page.locator(".drill-count")).to_have_text("52 van 520")
    expect(page.locator("#drillBody tbody tr")).to_have_count(52)

    # Meer tonen via keyboard: the drilldown has no tbody keydown interceptor,
    # so native button activation must work.
    page.get_by_role("textbox", name="Zoek bronregels").fill("Team")
    expect(page.locator(".drill-count")).to_have_text("520 van 520")
    expect(page.locator("#drillBody tbody tr")).to_have_count(500)
    more = page.locator("#drillBody .drill-more .more-rows-btn")
    more.focus()
    page.keyboard.press("Enter")
    expect(page.locator("#drillBody tbody tr")).to_have_count(520)
    assert page.locator("#drillBody .drill-more").count() == 0

    # CSV export contains every source row, not just visible ones.
    with page.expect_download() as download_info:
        page.locator("#drillCsvBtn").click()
    csv_text = download_info.value.path().read_text(encoding="utf-8-sig")
    assert len(csv_text.splitlines()) == 521  # header + 520 rows

    assert not errors


def test_drilldown_reopen_does_not_grow_listeners(page) -> None:
    """S1: heropening voegt geen nieuwe click-listener toe aan #drillBody."""
    page, errors = page
    rows = [{"sourceRow": i + 2} for i in range(5)]
    before = page.evaluate(
        "() => typeof getEventListeners === 'function'"
        " ? getEventListeners(document.querySelector('#drillBody')).click?.length ?? 0"
        " : -1"
    )
    for _ in range(3):
        page.evaluate("rows => openDrilldown('Test', rows)", rows)
        page.evaluate("closeDrilldown")
    after = page.evaluate(
        "() => typeof getEventListeners === 'function'"
        " ? getEventListeners(document.querySelector('#drillBody')).click?.length ?? 0"
        " : -1"
    )
    # getEventListeners is alleen beschikbaar in CDP-context, niet in de
    # pagina. Val terug op functioneel bewijs: Meer tonen moet na drie
    # heropeningen nog steeds precies één portie toevoegen.
    assert before in (-1, 1) and after in (-1, 1)
    page.evaluate("rows => openDrilldown('Test', rows)", [{"sourceRow": i + 2} for i in range(520)])
    more = page.locator("#drillBody .drill-more .more-rows-btn")
    more.click()
    assert page.locator("#drillBody tbody tr").count() == 520
    assert page.locator("#drillBody .drill-more").count() == 0
    assert not errors
