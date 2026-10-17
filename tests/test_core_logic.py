"""Gerichte randgevallen en een tweede synthetische referentie voor issue #59."""

from collections.abc import Iterator
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest
from generate_synthetic_escalatielog import create_workbook, main, synthetic_rows
from playwright.sync_api import Page, sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser

# Handmatig afgeleid uit de zeven auditregels, niet uit analyze()-uitvoer.
EXPECTED_SIGNALS = {
    "NIET_GEACTIVEERD": 0,
    "NACHT": 0,
    "WEEKEND": 0,
    "HOOG_DAGVOLUME": 0,
    "VEEL_UNIEKE_CLIENTEN_MEDEWERKER": 0,
    "VEEL_MEDEWERKERS_CLIENT": 0,
    "VEEL_TEAMS_CLIENT": 5,
    "HERESCALATIE_TIJDENS_ACTIEVE_TOEGANG": 2,
    "ZEER_SNELLE_HERESCALATIE": 1,
    "LATE_ACTIVATIE": 0,
    "ZELDZAME_REDEN": 0,
    "ONGELDIGE_STARTDATUM": 0,
    "ONGELDIGE_ACTIVATIE": 0,
    "ONGELDIGE_DUUR": 0,
    "ONTBREKENDE_KERNVELDEN": 0,
    "ONVOLLEDIG_CLIENTDOEL": 0,
}


@pytest.fixture(scope="module")
def browser():
    """Hergebruik één browser; ieder geval krijgt een lege pagina."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        yield browser
        browser.close()


@pytest.fixture
def page(browser) -> Iterator[Page]:
    """Start de echte applicatie zonder bronbestanden met persoonsgegevens."""
    page = browser.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
    yield page
    page.close()
    assert not errors


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (46143.5, "01-05-2026, 12:00:00"),
        (46143 + 1 / 86400, "01-05-2026, 00:00:01"),
        ("31-12-2025, 23:59:59", "31-12-2025, 23:59:59"),
        ("01-01-2026 00:00", "01-01-2026, 00:00:00"),
        ("2024-02-29T12:34:56", "29-02-2024, 12:34:56"),
        ("2026-01-01T00:00", "01-01-2026, 00:00:00"),
        ("31-02-2026, 12:00", None),
        ("29-02-2025, 12:00", None),
        ("2026-04-31T12:00", None),
        ("01-05-2026, 24:00", None),
        ("01-05-2026, 12:60", None),
        ("01-05-2026", None),
        ("2026-05-01", None),
        ("31-12-1899, 23:59", None),
        ("01-01-10000, 00:00", None),
        ("Niet geactiveerd", None),
        ("-", None),
        ("", None),
        (None, None),
        (0, None),
    ],
)
def test_parse_date_boundaries(page: Page, value, expected) -> None:
    """Kalendercontrole, tijdfractie en jaarovergang houden vaste betekenis."""
    actual = page.evaluate("value => parseDate(value)?.display ?? null", value)
    assert actual == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("=1+1", "'=1+1"),
        (" +SUM(A1)", "' +SUM(A1)"),
        ("@naam", "'@naam"),
        ("-cmd", "'-cmd"),
        ("\t=1", "'\t=1"),
        ("-", "-"),
        ("-12", "-12"),
        ("-12.5", "-12.5"),
        ("-12,5", "-12,5"),
        (-12, "-12"),
        ("77600-1", "77600-1"),
    ],
)
def test_csv_formula_guard(page: Page, value, expected: str) -> None:
    """Formules krijgen een apostrof; gewone negatieve getallen blijven getallen."""
    assert page.evaluate("value => toCsv([{Waarde:value}])", value) == (
        f'\ufeff"Waarde"\r\n"{expected}"'
    )


def test_csv_format_and_escaping(page: Page) -> None:
    """BOM, puntkomma, CRLF, quotes en meerregelige cellen blijven exact behouden."""
    actual = page.evaluate(
        "rows => toCsv(rows)",
        [{"Tekst": 'a;"b"\r\nc', "Leeg": None}, {"Tekst": "einde", "Leeg": ""}],
    )
    assert actual == '\ufeff"Tekst";"Leeg"\r\n"a;""b""\r\nc";""\r\n"einde";""'
    assert page.evaluate("toCsv([])") == ""


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("activeAccessMinutes", ""),
        ("activeAccessMinutes", "1.5"),
        ("activeAccessMinutes", "-1"),
        ("activeAccessMinutes", "0"),
        ("nightStartHour", "24"),
        ("nightEndHour", "-1"),
        ("activationDelayThresholdMinutes", "-1"),
    ],
)
def test_read_settings_rejects_invalid_values(page: Page, key: str, value: str) -> None:
    """De formulierlezer weigert ongeldige waarden zonder instellingen toe te passen."""
    actual = page.evaluate(
        """({key,value}) => {
            renderSettings();
            const before=JSON.stringify(state.settings);
            document.getElementById('set-'+key).value=value;
            let error=null;
            try { readSettings(); } catch(e) { error=e.message; }
            return {error, unchanged:JSON.stringify(state.settings)===before};
        }""",
        {"key": key, "value": value},
    )
    assert actual == {"error": f"Ongeldige instelling: {key}", "unchanged": True}


def test_read_settings_accepts_zero_delay_and_hour_limits(page: Page) -> None:
    """Vertraging nul en beide uurgrenzen zijn geldig; lezen past niets toe."""
    assert page.evaluate(
        """() => {
            renderSettings();
            document.getElementById('set-activationDelayThresholdMinutes').value='0';
            document.getElementById('set-nightStartHour').value='0';
            document.getElementById('set-nightEndHour').value='23';
            const next=readSettings();
            return [next.activationDelayThresholdMinutes,next.nightStartHour,
                next.nightEndHour,state.settings.activationDelayThresholdMinutes];
        }"""
    ) == [0, 0, 23, 2]


@pytest.mark.parametrize("exclude", [False, True])
def test_duration_exclusion_reconciles_before_dedup(page: Page, exclude: bool) -> None:
    """Twee gelijke 30-minutenregels verhuizen samen naar de systeemgroep."""
    matrix = synthetic_rows(9, 20260918, "signals")
    matrix[1][6] = matrix[-1][6] = "30"
    actual = page.evaluate(
        """({matrix,exclude}) => {
            const settings={...DEFAULT_SETTINGS,excludeDuration30:exclude};
            const r=analyze(normalizeRows(matrix,0),settings);
            return {all:r.allRows.length,system:r.systemRows.length,
                duplicates:r.duplicateRows.length,audit:r.auditRows.length,
                systemRows:r.systemRows.map(x=>x.sourceRow),
                duplicateRows:r.duplicateRows.map(x=>x.sourceRow)};
        }""",
        {"matrix": matrix, "exclude": exclude},
    )
    assert actual == {
        "all": 9,
        "system": 3 if exclude else 1,
        "duplicates": 0 if exclude else 1,
        "audit": 6 if exclude else 7,
        "systemRows": [2, 9, 10] if exclude else [9],
        "duplicateRows": [] if exclude else [10],
    }
    assert actual["all"] == actual["system"] + actual["duplicates"] + actual["audit"]


@pytest.mark.parametrize("shared", [False, True])
@pytest.mark.parametrize("numeric", [False, True])
@pytest.mark.parametrize("stored", [False, True])
def test_signal_profile_roundtrip(
    page: Page, tmp_path: Path, shared: bool, numeric: bool, stored: bool
) -> None:
    """Alle acht XLSX-varianten leveren dezelfde vaste signalen en bronrelaties."""
    workbook = tmp_path / "signalen.xlsx"
    options = {"shared_strings": shared, "numeric_dates": numeric, "stored": stored}
    digest = create_workbook(workbook, 9, 20260918, "signals", **options)
    assert digest == create_workbook(tmp_path / "kopie.xlsx", 9, 20260918, "signals", **options)
    with ZipFile(workbook) as archive:
        assert all(
            i.compress_type == (ZIP_STORED if stored else ZIP_DEFLATED) for i in archive.infolist()
        )
        sheet = archive.read("xl/worksheets/sheet1.xml").decode()
        assert ('t="s"' in sheet) is shared
        assert ('<c r="L2"><v>46146.375</v></c>' in sheet) is numeric
        assert ("xl/sharedStrings.xml" in archive.namelist()) is shared
    page.locator("#fileInput").set_input_files(workbook)
    actual = page.evaluate(
        """async () => {
            const parsed=await readXlsx(state.file);
            const r=analyze(normalizeRows(parsed.matrix,parsed.headerRow),{...DEFAULT_SETTINGS});
            return {signals:Object.fromEntries(Object.keys(SIGNAL_META)
                    .map(k=>[k,r.signalCounts.get(k)||0])),
                populations:[r.allRows.length,r.systemRows.length,r.duplicateRows.length,r.auditRows.length],
                attention:r.attention.length,
                repeats:r.auditRows.filter(x=>x.reEscalationMinutes!==null)
                    .map(x=>[x.sourceRow,x.previousSourceRow,x.reEscalationMinutes,x.veryFastMinutes]),
                bursts:r.bursts.map(x=>[x['Max escalaties in venster'],
                    x.__rows.map(r=>r.sourceRow)]),
                clusters:r.clientClusters.map(x=>[x['Unieke medewerkers'],x['Unieke teams'],
                    x.__rows.map(r=>r.sourceRow)]),
                start:r.auditRows[0].started.display,
                duration:r.auditRows[0].durationMinutes};
        }"""
    )
    assert actual == {
        "signals": EXPECTED_SIGNALS,
        "populations": [9, 1, 1, 7],
        "attention": 5,
        "repeats": [[3, 2, 4, 4], [4, 3, 6, None]],
        "bursts": [[5, [2, 3, 4, 5, 6]]],
        "clusters": [[3, 3, [2, 3, 4, 7, 8]]],
        "start": "04-05-2026, 09:00:00",
        "duration": 15,
    }


def test_generator_cli_and_standard_fixture_unchanged(tmp_path: Path, monkeypatch) -> None:
    """CLI-opties werken en de bestaande §15-fixture blijft byte-identiek."""
    standard = tmp_path / "standaard.xlsx"
    create_workbook(standard, 2000, 20260918)
    assert standard.read_bytes() == STANDARD_FIXTURE.read_bytes()
    output = tmp_path / "signalen.xlsx"
    monkeypatch.setattr(
        "sys.argv",
        [
            "generator",
            "--output",
            str(output),
            "--rows",
            "9",
            "--profile",
            "signals",
            "--shared-strings",
            "--numeric-dates",
            "--stored",
        ],
    )
    main()
    with ZipFile(output) as archive:
        assert "xl/sharedStrings.xml" in archive.namelist()
        assert all(i.compress_type == ZIP_STORED for i in archive.infolist())
        assert '<c r="L2"><v>46146.375</v></c>' in archive.read("xl/worksheets/sheet1.xml").decode()
    with pytest.raises(ValueError, match="precies 9"):
        synthetic_rows(10, 1, "signals")
    with pytest.raises(ValueError, match="Onbekend profiel"):
        synthetic_rows(9, 1, "onbekend")


def test_quality_and_system_drilldowns_keep_exact_source_rows(page: Page) -> None:
    """De duplicaatgroep en systeemgroep openen uitsluitend hun eigen bronregels."""
    page.evaluate(
        """matrix => {
            state.result=analyze(normalizeRows(matrix,0),{...DEFAULT_SETTINGS});
            render();
        }""",
        synthetic_rows(9, 20260918, "signals"),
    )
    page.locator('.tab[data-view="quality"]').click()
    page.locator("#qualityTable tbody tr").filter(has_text="Exact dubbel").click()
    assert page.evaluate("state.drilldown.rows.map(r=>r['Excel-rij'])") == [2, 10]
    assert page.locator("#drillBody tbody tr").count() == 2
    page.locator("#drillCloseBtn").click()
    page.locator('.tab[data-view="system"]').click()
    page.locator("#systemTable tbody tr").filter(has_text="cliënt gekoppeld").click()
    assert page.evaluate("state.drilldown.rows.map(r=>r['Excel-rij'])") == [9]
    assert page.locator("#drillBody tbody tr").count() == 1
