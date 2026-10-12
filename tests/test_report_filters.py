from pathlib import Path

from playwright.sync_api import sync_playwright
from test_report_layout import ROOT, launch_browser


def export_report(page, report: Path, count: int = 4) -> None:
    page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
    page.evaluate(
        """count => {
          const examples = [
            ['Alpha <b>', 'Team <A>', 'Arts', 'Cliënt'],
            ['Beta', 'Team <A>', 'Verpleegkundige', 'Locatie'],
            ['Gamma', 'Team B', 'Arts', 'Locatie'],
            ['Delta', '', 'Arts', 'Cliënt']
          ];
          const matrix = [REQUIRED_HEADERS, ...Array.from({length:count}, (_,i) => {
            const [name,team,expertise,type] = examples[i%4];
            return [i === 500 ? 'Buiten limiet' : name, 'TEST-'+i, team, expertise,
              'login'+i, 'Synthetische testreden', '-1', type, 'Testdoel '+i,
              'DOEL-'+i, 'Testlocatie', '01-05-2026, 01:00:00',
              '01-05-2026, 01:05:00', 'Synthetisch'];
          })];
          state.settings = {...DEFAULT_SETTINGS};
          state.result = analyze(normalizeRows(matrix,0), state.settings);
          state.fileName = 'synthetisch-filters.xlsx';
          state.sheetName = 'Test';
          state.analysisRunAt = new Date('2026-05-31T12:00:00');
        }""",
        count,
    )
    with page.expect_download() as download_info:
        page.evaluate("exportReport()")
    download_info.value.save_as(report)
    page.goto(report.as_uri(), timeout=60_000)


def test_report_filters_combine_and_restore_after_print(tmp_path: Path) -> None:
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(accept_downloads=True)
        errors = []
        requests = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))
        export_report(page, tmp_path / "report.html")
        section = page.locator("#s-hoog")
        search = section.get_by_role("searchbox")
        team = section.get_by_role("combobox", name="Filter op Team", exact=True)
        expertise = section.get_by_role("combobox", name="Filter op Deskundigheid", exact=True)
        target = section.get_by_role("combobox", name="Filter op Doeltype", exact=True)
        assert team.locator("option").all_text_contents() == [
            "Alle team",
            "Team <A>",
            "Team B",
        ]
        assert section.locator(".report-count-value").text_content() == "4 van 4"
        status = section.get_by_role("status")
        assert (
            status.text_content()
            == "Zichtbare regels in Aandachtspunten · prioriteit Hoog: 4 van 4"
        )
        assert status.get_attribute("aria-atomic") == "true"
        assert search.get_attribute("aria-describedby") == section.locator(
            ".report-empty"
        ).get_attribute("id")
        assert section.locator(".data-row b").count() == 0
        assert "Alpha <b>" in " ".join(section.locator(".data-row").all_text_contents())
        unchanged = page.locator(".k, .priority, .r-bars, .toc").all_text_contents()
        team.focus()
        page.keyboard.press("Tab")
        assert expertise.evaluate("el => el === document.activeElement")
        team.select_option("Team <A>")
        assert section.locator(".report-count-value").text_content() == "2 van 4"
        expertise.select_option("Arts")
        target.select_option("Cliënt")
        search.fill("ALPHA")
        assert section.locator(".report-count-value").text_content() == "1 van 4"
        assert section.locator(".data-row:visible").count() == 1
        assert section.locator(".reason-row:visible").count() == 1
        assert page.locator("#s-medewerkers .report-count-value").text_content() == "4 van 4"
        assert page.locator(".k, .priority, .r-bars, .toc").all_text_contents() == unchanged
        search.fill("Gamma")
        assert section.locator(".report-count-value").text_content() == "0 van 4"
        assert section.locator(".report-empty").is_visible()
        assert search.get_attribute("aria-describedby") == section.locator(
            ".report-empty"
        ).get_attribute("id")
        assert status.text_content().endswith(": 0 van 4")
        assert section.locator("tbody tr:visible").count() == 0
        search.fill("alpha")
        closed = page.locator("details:not([open])").count()
        assert closed > 0
        page.emulate_media(media="print")
        page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
        page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
        assert page.locator("details:not([open])").count() == 0
        assert section.locator(".data-row:visible").count() == 4
        assert section.locator(".reason-row:visible").count() == 4
        assert not section.locator(".report-filters").is_visible()
        assert not section.locator(".report-empty").is_visible()
        page.evaluate("window.dispatchEvent(new Event('afterprint'))")
        page.emulate_media(media="screen")
        assert page.locator("details:not([open])").count() == closed
        assert search.input_value() == "alpha"
        assert team.input_value() == "Team <A>"
        assert section.locator(".data-row:visible").count() == 1
        assert section.locator(".reason-row:visible").count() == 1
        section.get_by_role("button", name="Filters wissen").click()
        assert section.locator(".report-count-value").text_content() == "4 van 4"
        assert search.evaluate("el => el === document.activeElement")
        assert team.input_value() == expertise.input_value() == target.input_value() == ""
        assert not section.locator(".report-empty").is_visible()
        for width in (1280, 800, 375):
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate("document.body.scrollWidth <= innerWidth")
            assert section.locator(".report-filters").evaluate(
                "el => el.scrollWidth <= el.clientWidth"
            )
            assert section.locator("th").first.bounding_box()["height"] < 55
        assert not errors
        assert all(url.startswith("file:") for url in requests)
        browser.close()


def test_report_limits_and_no_javascript(tmp_path: Path) -> None:
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(accept_downloads=True)
        report = tmp_path / "limited-report.html"
        export_report(page, report, 501)
        section = page.locator("#s-hoog")
        assert section.locator(".report-count-value").text_content() == "500 van 500"
        assert "Getoond: 500 van 501 regels" in section.locator(".report-limit").text_content()
        assert "alleen deze 500 opgenomen regels" in section.locator(".report-limit").text_content()
        section.get_by_role("searchbox").fill("Buiten limiet")
        assert section.locator(".report-count-value").text_content() == "0 van 500"
        section.get_by_role("button", name="Filters wissen").click()
        section.get_by_role("combobox", name="Filter op Signalen", exact=True).select_option(
            index=1
        )
        assert 0 < section.locator(".data-row:visible").count() < 500
        no_js = browser.new_context(java_script_enabled=False)
        plain = no_js.new_page()
        plain.goto(report.as_uri())
        assert plain.locator(".report-filters").count() == 0
        assert plain.locator("#s-hoog .data-row").count() == 500
        assert plain.locator("#s-hoog .data-row:visible").count() == 500
        assert plain.locator("#s-hoog .reason-row:visible").count() == 500
        plain.locator("#s-medewerkers > summary").click()
        assert plain.locator("#s-medewerkers .data-row:visible").count() == 300
        no_js.close()
        browser.close()
