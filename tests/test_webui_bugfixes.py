"""Regressietests voor issues #54 en #62.

- Lege en niet-numerieke duur vormen één categorie '(leeg of ongeldig)'
  met een drilldown die precies de meegetelde bronregels opent (#54).
- Kleine webui-fixes: signaalfilter op hele namen, herselectie van
  hetzelfde bestand en opruiming van de drilldown-ResizeObserver (#62).
"""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser


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


def load_duration_rows(page) -> None:
    """Dubieuze duurwaarden via normalizeRows -> analyze -> render."""
    page.evaluate(
        """() => {
          const base = [
            'Test Medewerker', 'M001', 'Team A', 'Verpleegkundige', 'tmed'];
          const mk = (reason, duration, started) => [
            ...base, reason, duration, 'Cliënt', 'Cliënt X', 'C100',
            'Locatie 1', started, '01-05-2026, 09:32:00', 'Synthetische test'];
          const matrix = [
            REQUIRED_HEADERS,
            mk('Werkoverleg', '', '01-05-2026, 09:30:00'),
            mk('Werkoverleg', 'abc', '01-05-2026, 09:45:00'),
            mk('cliënt gekoppeld aan item in ons ketenverkeer', '',
               '01-05-2026, 10:00:00'),
            mk('Werkoverleg', '15', '01-05-2026, 10:15:00'),
            mk('Werkoverleg', '45', '01-05-2026, 10:30:00'),
          ];
          state.result = analyze(normalizeRows(matrix, 0), state.settings);
          render();
        }"""
    )


def test_empty_and_invalid_duration_form_one_bucket(page, tmp_path: Path) -> None:
    page, errors = page
    load_duration_rows(page)

    logic = page.evaluate(
        """() => {
          const issues = state.result.logic.issues.filter(
            i => i.Controlepunt === 'Duurverdeling');
          return {
            waardes: issues.map(i => i.Waarde),
            aantallen: issues.map(i => i.Aantal),
            rows: issues.map(i => i.__rows.map(r => r.sourceRow)),
            anyNull: state.result.logic.issues.some(
              i => Object.values(i).some(v => String(v).includes('null'))),
          };
        }"""
    )
    assert logic["waardes"] == ["15 minuten", "45 minuten", "(leeg of ongeldig)"]
    assert logic["aantallen"] == [1, 1, 3]
    assert logic["rows"][2] == [2, 3, 4]
    assert not logic["anyNull"]

    logic_table = page.locator("#logicTable").text_content()
    assert "(leeg of ongeldig)" in logic_table
    assert "null" not in logic_table
    assert "null" not in page.locator("#systemTable").text_content()

    attention_csv = page.evaluate("toCsv(attentionRows(state.result.attention))")
    assert "null" not in attention_csv

    with page.expect_download() as download_info:
        page.locator("#reportBtn").click()
    report = tmp_path / "rapport.html"
    download_info.value.save_as(report)
    report_html = report.read_text(encoding="utf-8")
    assert "null minuten" not in report_html
    assert "(leeg of ongeldig)" in report_html

    # De duurcategorie opent precies de drie meegetelde bronregels.
    page.locator('.tab[data-view="logic"]').click()
    page.locator("#logicTable tbody tr").filter(has_text="(leeg of ongeldig)").click()
    assert page.locator("#drillBody tbody tr").count() == 3
    assert page.evaluate("state.drilldown.rows.map(r => r['Excel-rij'])") == [
        2,
        3,
        4,
    ]
    page.locator("#drillCloseBtn").click()

    # De systeemcategorie met lege duur opent de ene meegetelde regel.
    page.locator('.tab[data-view="system"]').click()
    system_row = page.locator("#systemTable tbody tr").filter(has_text="cliënt gekoppeld")
    assert system_row.count() == 1
    assert system_row.locator("td").nth(2).text_content() == "1"
    system_row.click()
    assert page.locator("#drillBody tbody tr").count() == 1
    assert page.evaluate("state.drilldown.rows.map(r => r['Excel-rij'])") == [4]
    page.locator("#drillCloseBtn").click()
    assert not errors


def test_signal_filter_matches_whole_signal_names(page) -> None:
    page, errors = page
    page.evaluate(
        """() => tableWidget('#attentionTable', [
          {Medewerker: 'A', Signalen: 'NACHT_EXTRA'},
          {Medewerker: 'B', Signalen: 'NACHT'},
          {Medewerker: 'C', Signalen: 'NACHT; NACHT_EXTRA'},
        ], {search: true, signalFilter: true})"""
    )
    page.evaluate(
        """() => {
          const select = document.querySelector('#attentionTable .signal-filter');
          select.value = 'NACHT';
          select.dispatchEvent(new Event('change', {bubbles: true}));
        }"""
    )
    assert page.locator("#attentionTable tbody tr").count() == 2
    assert page.locator("#attentionTable .count-label").text_content() == "2 van 3"
    texts = page.locator("#attentionTable tbody tr").all_inner_texts()
    assert texts[0].startswith("B")
    assert texts[1].startswith("C")

    signal_text = page.evaluate("SIGNAL_META.ZEER_SNELLE_HERESCALATIE")
    assert "vorige handmatige escalatie" not in signal_text
    assert signal_text == (
        "Her-escalatie die binnen de ingestelde grens start na de eerdere "
        "geactiveerde escalatie waarop de her-escalatie steunt."
    )
    assert not errors


def test_same_file_can_be_selected_twice(page) -> None:
    page, errors = page
    page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
    assert page.evaluate("document.getElementById('fileInput').value") == ""
    assert page.locator("#fileName").text_content() == "synthetic-escalatielog.xlsx"
    page.evaluate("document.getElementById('fileName').textContent = 'Overschreven'")
    page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
    assert page.locator("#fileName").text_content() == "synthetic-escalatielog.xlsx"
    assert not errors


def test_drilldown_disconnects_resize_observer() -> None:
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        page.evaluate(
            """() => {
              window.__roDisconnects = 0;
              const orig = ResizeObserver.prototype.disconnect;
              ResizeObserver.prototype.disconnect = function () {
                window.__roDisconnects++;
                return orig.call(this);
              };
            }"""
        )
        page.evaluate("openDrilldown('Eén', [{sourceRow: 2}])")
        assert page.evaluate("window.__roDisconnects") == 0
        assert page.evaluate("state.drillResizeObserver !== null")
        page.evaluate("openDrilldown('Twee', [{sourceRow: 3}])")
        assert page.evaluate("window.__roDisconnects") == 1
        page.evaluate("closeDrilldown()")
        assert page.evaluate("state.drillResizeObserver === null")
        assert page.evaluate("window.__roDisconnects") == 2
        assert not errors
        browser.close()
