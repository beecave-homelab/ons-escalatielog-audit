"""Regression tests for issue #53: XLSX reader variants and error cells.

The tests use only synthetic, data-free worksheets.
"""

from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest
from generate_synthetic_escalatielog import HEADERS, column_name, workbook_files
from playwright.sync_api import sync_playwright
from test_report_layout import ROOT, launch_browser

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_RELS_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WORKSHEET_REL = f"{OFFICE_RELS_NS}/worksheet"

BASE_VALUES = dict(
    zip(
        HEADERS,
        [
            "Test Medewerker",
            "M001",
            "Team A",
            "Verpleegkundige",
            "tmed",
            "Werkoverleg",
            "15",
            "Cliënt",
            "Cliënt X",
            "C100",
            "Locatie 1",
            "01-05-2026, 09:30:00",
            "01-05-2026, 09:32:00",
            "Synthetische test",
        ],
        strict=True,
    )
)


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


def write_xlsx(path: Path, files: dict[str, str], compression=ZIP_DEFLATED) -> None:
    with ZipFile(path, "w", compression=compression) as workbook:
        for name, content in files.items():
            workbook.writestr(name, content)


def inline_cell(ref: str, value: str) -> str:
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'


def row_xml(row_index: int, cells: dict[int, str], prefix: str = "") -> str:
    p = f"{prefix}:" if prefix else ""
    content = "".join(
        cell.replace("<c ", f"<{p}c ").replace("</c>", f"</{p}c>")
        for index, cell in sorted(cells.items())
    )
    return f'<{p}row r="{row_index}">{content}</{p}row>'


def test_error_cell_reads_empty_and_reports_foutcel(page, tmp_path):
    """An error cell reads empty and appears as Foutcel in bron under Datakwaliteit."""
    page, errors = page
    workbook = tmp_path / "foutcel.xlsx"

    header_cells = {
        index: inline_cell(f"{column_name(index)}1", header)
        for index, header in enumerate(HEADERS, 1)
    }
    values = [BASE_VALUES[h] for h in HEADERS]
    error_cells = {
        index: inline_cell(f"{column_name(index)}2", value) for index, value in enumerate(values, 1)
    }
    error_cells[2] = '<c r="B2" t="e"><v>#N/A</v></c>'
    empty_values = {**BASE_VALUES, "Gestart op": "01-05-2026, 09:45:00"}
    empty_cells = {
        index: inline_cell(f"{column_name(index)}3", empty_values[h])
        for index, h in enumerate(HEADERS, 1)
        if index != 2  # Medewerkernummer is genuinely missing
    }
    files = workbook_files([])
    files["xl/worksheets/sheet1.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{MAIN_NS}"><sheetData>'
        f"{row_xml(1, header_cells)}{row_xml(2, error_cells)}{row_xml(3, empty_cells)}"
        "</sheetData></worksheet>"
    )
    write_xlsx(workbook, files)

    page.locator("#fileInput").set_input_files(workbook)
    result = page.evaluate(
        """async () => {
          const parsed = await readXlsx(state.file);
          const rows = normalizeRows(parsed.matrix, parsed.headerRow);
          const nanFree = !rows.some(r => Object.values(r).some(v =>
            (typeof v === 'number' && !Number.isFinite(v)) || String(v) === 'NaN'));
          state.result = analyze(rows, state.settings);
          render();
          const fout = state.result.quality.filter(
            i => i['Type issue'] === 'Foutcel in bron');
          const miss = state.result.quality.filter(
            i => i['Type issue'] === 'Ontbrekend/ongeldig veld'
              && i.Sleutel === 'Medewerkernummer');
          return {
            nanFree,
            errorFields: rows.map(r => r.errorFields),
            fout: fout.map(i => ({
              sleutel: i.Sleutel, aantal: i.Aantal,
              rows: i.__rows.map(r => r.sourceRow),
              nonEnum: !Object.keys(i).includes('__rows'),
            })),
            missRows: miss.flatMap(i => i.__rows.map(r => r.sourceRow)),
          };
        }"""
    )

    assert result["nanFree"], "Geen NaN-waarde mag in de genormaliseerde regels staan"
    assert result["errorFields"] == [["Medewerkernummer"], []]
    assert result["fout"] == [
        {
            "sleutel": "Medewerkernummer",
            "aantal": 1,
            "rows": [2],
            "nonEnum": True,
        }
    ]
    assert 3 in result["missRows"], "De echt lege cel blijft onder Ontbrekend/ongeldig veld"
    assert "NaN" not in page.locator("#qualityTable").text_content()

    page.locator("#tabs").get_by_role("tab", name="Datakwaliteit", exact=True).click()
    page.locator("#qualityTable tbody tr").filter(has_text="Foutcel in bron").click()
    assert page.locator("#drillBody tbody tr").count() == 1
    assert page.evaluate("state.drilldown.rows.map(r => r['Excel-rij'])") == [2]
    page.locator("#drillCloseBtn").click()
    assert not errors


@pytest.mark.parametrize("compression", [ZIP_STORED, ZIP_DEFLATED])
def test_namespaced_workbook_parses_like_unprefixed(page, tmp_path, compression):
    """x: prefixes on all SpreadsheetML and package elements read in identically."""
    page, errors = page
    strings = HEADERS + [BASE_VALUES[h] for h in HEADERS]
    matrix_rows = [list(range(14)), list(range(14, 28))]

    def sheet_xml(prefix: str) -> str:
        p = f"{prefix}:" if prefix else ""
        ns = f'xmlns:{prefix}="{MAIN_NS}"' if prefix else f'xmlns="{MAIN_NS}"'
        rows = "".join(
            f'<{p}row r="{r}">'
            + "".join(
                f'<{p}c r="{column_name(c)}{r}" t="s"><{p}v>{i}</{p}v></{p}c>'
                for c, i in enumerate(row, 1)
            )
            + f"</{p}row>"
            for r, row in enumerate(matrix_rows, 1)
        )
        return f"<{p}worksheet {ns}><{p}sheetData>{rows}</{p}sheetData></{p}worksheet>"

    def sst_xml(prefix: str) -> str:
        p = f"{prefix}:" if prefix else ""
        ns = f'xmlns:{prefix}="{MAIN_NS}"' if prefix else f'xmlns="{MAIN_NS}"'
        items = "".join(f"<{p}si><{p}t>{escape(s)}</{p}t></{p}si>" for s in strings)
        return f'<{p}sst {ns} count="{len(strings)}" uniqueCount="{len(strings)}">{items}</{p}sst>'

    def files(prefix: str) -> dict[str, str]:
        p = f"{prefix}:" if prefix else ""
        book_ns = f'xmlns:{prefix}="{MAIN_NS}"' if prefix else f'xmlns="{MAIN_NS}"'
        rel_ns = f'xmlns:{prefix}="{RELS_NS}"' if prefix else f'xmlns="{RELS_NS}"'
        result = workbook_files([])
        result.pop("xl/worksheets/sheet1.xml")
        result["xl/workbook.xml"] = (
            f'<{p}workbook {book_ns} xmlns:r="{OFFICE_RELS_NS}"><{p}sheets>'
            f'<{p}sheet name="Export" sheetId="1" r:id="rId1"/></{p}sheets></{p}workbook>'
        )
        result["xl/_rels/workbook.xml.rels"] = (
            f"<{p}Relationships {rel_ns}>"
            f'<{p}Relationship Id="rId1" Type="{WORKSHEET_REL}" '
            f'Target="worksheets/sheet1.xml"/></{p}Relationships>'
        )
        result["xl/sharedStrings.xml"] = sst_xml(prefix)
        result["xl/worksheets/sheet1.xml"] = sheet_xml(prefix)
        return result

    normal = tmp_path / "normaal.xlsx"
    prefixed = tmp_path / "geprefixed.xlsx"
    write_xlsx(normal, files(""))
    write_xlsx(prefixed, files("x"), compression=compression)

    matrices = []
    for path in (normal, prefixed):
        page.locator("#fileInput").set_input_files(path)
        matrices.append(
            page.evaluate(
                """async () => {
                  const parsed = await readXlsx(state.file);
                  return {sheet: parsed.sheet, matrix: parsed.matrix};
                }"""
            )
        )
    assert matrices[0]["sheet"] == matrices[1]["sheet"]
    assert matrices[0]["matrix"] == matrices[1]["matrix"]
    assert matrices[0]["matrix"][0] == HEADERS
    assert matrices[0]["matrix"][1] == [BASE_VALUES[h] for h in HEADERS]
    assert not errors


def test_cells_and_rows_without_r_attribute(page):
    """Cells without r follow the previous cell; rows without r the previous row."""
    page, errors = page
    sheet = (
        f'<worksheet xmlns="{MAIN_NS}"><sheetData>'
        '<row><c t="inlineStr"><is><t>a</t></is></c>'
        '<c t="inlineStr"><is><t>b</t></is></c></row>'
        '<row r="4"><c t="inlineStr"><is><t>c</t></is></c></row>'
        '<row><c r="C5" t="inlineStr"><is><t>d</t></is></c>'
        '<c t="inlineStr"><is><t>e</t></is></c></row>'
        "</sheetData></worksheet>"
    )
    matrix = page.evaluate(
        "(text) => parseWorksheet(xml(text), [])",
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>{sheet}',
    )
    assert matrix[0] == ["a", "b"]
    assert matrix[3] == ["c"]
    assert matrix[4] == [None, None, "d", "e"]
    assert not errors


def test_shared_strings_skip_phonetic_and_keep_rich_runs(page):
    """rPh text does not count; rich-text runs are concatenated."""
    page, errors = page
    shared_doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="{MAIN_NS}" count="2" uniqueCount="2">'
        '<si><rPh sb="0" eb="1"><t>NEGEER</t></rPh><t>Houd mij</t></si>'
        "<si><r><t>deel 1</t></r><r><t>deel 2</t></r></si>"
        "</sst>"
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{MAIN_NS}"><sheetData><row r="1">'
        '<c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c>'
        "</row></sheetData></worksheet>"
    )
    matrix = page.evaluate(
        """([sstText, sheetText]) => {
          const sdoc = xml(sstText);
          const shared = [...sdoc.getElementsByTagNameNS('*', 'si')]
            .map(si => sharedText(si));
          return parseWorksheet(xml(sheetText), shared);
        }""",
        [shared_doc, sheet],
    )
    assert matrix[0] == ["Houd mij", "deel 1deel 2"]
    assert not errors
