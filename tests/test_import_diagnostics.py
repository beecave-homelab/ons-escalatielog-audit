"""Importdiagnostiek met uitsluitend synthetische XLSX-werkbladen."""

from pathlib import Path
from xml.sax.saxutils import quoteattr
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from generate_synthetic_escalatielog import HEADERS, workbook_files, worksheet_xml
from playwright.sync_api import expect, sync_playwright
from test_report_layout import ROOT, launch_browser


def write_workbook(path: Path, sheets: list[tuple[str, list[list[str]]]]) -> None:
    files = workbook_files([])
    files.pop("xl/worksheets/sheet1.xml")
    sheet_tags = []
    relationships = []
    for index, (name, rows) in enumerate(sheets, 1):
        sheet_tags.append(f'<sheet name={quoteattr(name)} sheetId="{index}" r:id="rId{index}"/>')
        relationships.append(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
        files[f"xl/worksheets/sheet{index}.xml"] = worksheet_xml(rows)
    files["xl/workbook.xml"] = (
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{''.join(sheet_tags)}</sheets></workbook>"
    )
    files["xl/_rels/workbook.xml.rels"] = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{''.join(relationships)}</Relationships>"
    )
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(2, len(sheets) + 1)
    )
    files["[Content_Types].xml"] = files["[Content_Types].xml"].replace(
        "</Types>", f"{overrides}</Types>"
    )
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as workbook:
        for name, content in files.items():
            workbook.writestr(name, content)


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        yield page
        browser.close()


def read_result(page, path: Path) -> dict:
    page.locator("#fileInput").set_input_files(path)
    return page.evaluate(
        """async () => {
          try {
            const parsed = await readXlsx(state.file);
            return {sheet:parsed.sheet,headerRow:parsed.headerRow};
          } catch(error) { return {error:error.message}; }
        }"""
    )


def test_missing_column_is_visible_and_safe(page, tmp_path):
    workbook = tmp_path / "synthetisch-ontbrekende-kolom.xlsx"
    sheet_name = '<img src=x onerror="window.injected=true"> & Test'
    write_workbook(workbook, [(sheet_name, [HEADERS[:3] + HEADERS[4:]])])
    dialogs = []
    page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
    page.locator("#fileInput").set_input_files(workbook)
    page.locator("#analyzeBtn").click()
    status = page.locator("#status.error")
    expect(status).to_contain_text("Ontbrekende kolommen: Deskundigheid medewerker")
    text = status.text_content()
    assert "14 vereiste escalatielog-kolommen" in text
    assert f"Best passend werkblad: “{sheet_name}” (rij 1)." in text
    assert "Alleen de eerste 10 rijen van elk leesbaar werkblad zijn gecontroleerd" in text
    assert status.locator("img").count() == 0
    assert page.evaluate("window.injected === undefined")
    assert not page.locator("#workspace").is_visible()
    assert dialogs == [f"Analyse mislukt: {text}"]
    for width in (1280, 800, 375):
        page.set_viewport_size({"width": width, "height": 900})
        assert status.evaluate("el => el.scrollWidth <= el.clientWidth")


def test_best_candidate_across_sheets_and_rows(page, tmp_path):
    workbook = tmp_path / "meerdere-werkbladen.xlsx"
    write_workbook(
        workbook,
        [
            ("Toelichting", [["Fictieve inleiding"], HEADERS[:4]]),
            ("Escalatielog", [["Niet opnemen in diagnose"], HEADERS[:-1]]),
            ("Andere export", [HEADERS[:-2]]),
        ],
    )
    message = read_result(page, workbook)["error"]
    assert "Best passend werkblad: “Escalatielog” (rij 2)." in message
    assert "Ontbrekende kolommen: Bron" in message
    assert "Niet opnemen in diagnose" not in message
    assert "3 leesbare werkbladen" in message


def test_ties_keep_first_sheet_and_first_row_without_combining_headers(page, tmp_path):
    workbook = tmp_path / "gelijke-kandidaten.xlsx"
    write_workbook(
        workbook,
        [("Eerste", [HEADERS[:-1], HEADERS[1:]]), ("Tweede", [HEADERS[:-1]])],
    )
    message = read_result(page, workbook)["error"]
    assert "Best passend werkblad: “Eerste” (rij 1)." in message
    assert "Ontbrekende kolommen: Bron" in message


@pytest.mark.parametrize("header_row", [1, 10, 11])
def test_header_search_boundary_and_first_valid_sheet(page, tmp_path, header_row):
    workbook = tmp_path / "rijgrens.xlsx"
    rows = [[] for _ in range(header_row - 1)] + [HEADERS]
    write_workbook(workbook, [("Onvolledig", [HEADERS[:-1]]), ("Export", rows)])
    result = read_result(page, workbook)
    if header_row <= 10:
        assert result == {"sheet": "Export", "headerRow": header_row - 1}
        workbook = tmp_path / "twee-geldige-werkbladen.xlsx"
        write_workbook(workbook, [("Export", rows), ("Later", [HEADERS])])
        assert read_result(page, workbook) == result
    else:
        assert "Best passend werkblad: “Onvolledig” (rij 1)." in result["error"]
        assert "Ontbrekende kolommen: Bron" in result["error"]


def test_empty_and_unrecognizable_sheets(page, tmp_path):
    workbook = tmp_path / "lege-werkbladen.xlsx"
    write_workbook(workbook, [("Leeg", []), ("Onbekend", [["Geen header", "Fictief"]])])
    message = read_result(page, workbook)["error"]
    assert "Geen van de gecontroleerde rijen bevat een vereiste kolomnaam." in message
    assert "Best passende werkblad" not in message
    assert f"Ontbrekende kolommen: {', '.join(HEADERS)}" in message
    assert "2 leesbare werkbladen" in message


def test_required_header_count_is_dynamic(page, tmp_path):
    extra = "Synthetisch extra veld"
    workbook = tmp_path / "extra-vereist-veld.xlsx"
    write_workbook(workbook, [("Export", [HEADERS])])
    page.evaluate("header => REQUIRED_HEADERS.push(header)", extra)
    message = read_result(page, workbook)["error"]
    assert "15 vereiste escalatielog-kolommen" in message
    assert f"Ontbrekende kolommen: {extra}" in message
