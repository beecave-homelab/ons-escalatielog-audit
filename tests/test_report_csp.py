"""The exported report runs only its own filter script under a hash CSP (#65)."""

import base64
import hashlib
import re
from pathlib import Path

from playwright.sync_api import sync_playwright
from test_report_filters import export_report
from test_report_layout import launch_browser

HASH_SOURCE = re.compile(r"'sha256-[A-Za-z0-9+/]+={0,2}'")
EXPECTED_DIRECTIVES = {
    "default-src": "'none'",
    "style-src": "'unsafe-inline'",
    "connect-src": "'none'",
    "img-src": "data:",
    "base-uri": "'none'",
    "form-action": "'none'",
}
GIF_1X1 = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
INJECTED = (
    "<script>document.documentElement.dataset.injected='1'</script>"
    f'<img alt="" src="{GIF_1X1}" '
    "onload=\"document.documentElement.dataset.handler='1'\">"
)


def csp_directives(html: str) -> dict[str, list[str]]:
    match = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', html)
    assert match, "Het rapport bevat geen CSP-meta-tag"
    directives = {}
    for directive in match.group(1).split(";"):
        name, *tokens = directive.split()
        directives[name] = tokens
    return directives


def test_report_csp_allows_only_the_hashed_filter_script(tmp_path: Path) -> None:
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(accept_downloads=True)
        report = tmp_path / "rapport.html"
        export_report(page, report)
        browser.close()

    html = report.read_text(encoding="utf-8")
    directives = csp_directives(html)
    script_src = directives.pop("script-src")
    assert len(script_src) == 1, "script-src mag precies één bron bevatten"
    assert HASH_SOURCE.fullmatch(script_src[0]), (
        f"script-src moet een sha256-hash zijn, geen {script_src[0]}"
    )
    assert "'unsafe-inline'" not in script_src[0]
    assert directives == {name: [value] for name, value in EXPECTED_DIRECTIVES.items()}

    scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    assert len(scripts) == 1, "Het rapport bevat precies één scriptelement"
    digest = base64.b64encode(hashlib.sha256(scripts[0].encode("utf-8")).digest()).decode("ascii")
    assert script_src[0] == f"'sha256-{digest}'", (
        "De CSP-hash moet overeenkomen met de inhoud van het scriptelement"
    )


def test_report_filters_run_under_the_hash_csp(tmp_path: Path) -> None:
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(accept_downloads=True)
        errors = []
        csp_messages = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "console",
            lambda message: (
                csp_messages.append(message.text)
                if "Content Security Policy" in message.text
                else None
            ),
        )
        export_report(page, tmp_path / "rapport.html")

        filters = page.locator(".report-filters")
        tables = page.locator(".report-table")
        assert tables.count() > 0, "Het rapport bevat geen analysetabellen"
        assert filters.count() == tables.count(), (
            "Het gebundelde script moet boven iedere tabel filters bouwen"
        )
        section = page.locator("#s-hoog")
        count = section.locator(".report-count-value")
        assert count.text_content() == "4 van 4"
        section.get_by_role("searchbox").fill("ALPHA")
        assert count.text_content() == "1 van 4"
        assert not errors
        assert not csp_messages, (
            f"Het gebundelde script mag niet door de CSP worden geblokkeerd: {csp_messages}"
        )
        browser.close()


def test_report_csp_blocks_injected_script_and_handlers(tmp_path: Path) -> None:
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(accept_downloads=True)
        report = tmp_path / "rapport.html"
        export_report(page, report)
        html = report.read_text(encoding="utf-8")

        injected = tmp_path / "rapport-geinjecteerd.html"
        injected.write_text(html.replace("</body>", f"{INJECTED}</body>"), encoding="utf-8")
        blocked = browser.new_page()
        blocked.goto(injected.as_uri())
        blocked.wait_for_selector(".report-filters")
        blocked.wait_for_timeout(300)
        assert blocked.evaluate("document.documentElement.dataset.injected") is None
        assert blocked.evaluate("document.documentElement.dataset.handler") is None
        blocked.close()

        control_html = HASH_SOURCE.sub("'unsafe-inline'", html, count=1)
        assert "'sha256-" not in csp_directives(control_html)["script-src"][0]
        control = tmp_path / "rapport-controle.html"
        control.write_text(control_html.replace("</body>", f"{INJECTED}</body>"), encoding="utf-8")
        allowed = browser.new_page()
        allowed.goto(control.as_uri())
        allowed.wait_for_function("document.documentElement.dataset.injected === '1'")
        allowed.wait_for_function("document.documentElement.dataset.handler === '1'")
        allowed.close()
        browser.close()
