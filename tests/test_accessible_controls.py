"""Keyboard navigation, sorting and status/field feedback (#56, #61)."""

import re

import pytest
from playwright.sync_api import expect, sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(accept_downloads=True, viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())
        yield page
        browser.close()
        assert not errors


def analyze(page) -> None:
    """Use the shared synthetic reference through the normal upload flow."""
    page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
    page.locator("#analyzeBtn").click()
    page.wait_for_selector("#workspace.show")


def test_tabs__keyboard_wraps_selects_and_links_visible_panels(page) -> None:
    """Both tab bars have one tab stop, appropriate roles and linked panels."""
    analyze(page)
    tabs = page.get_by_role("tablist", name="Hoofdtabbladen")
    first = tabs.get_by_role("tab", name="Overzicht", exact=True)
    first.focus()
    first.press("ArrowRight")
    attention = tabs.get_by_role("tab", name="Aandachtspunten", exact=True)
    expect(attention).to_be_focused()
    expect(attention).to_have_attribute("aria-selected", "true")
    expect(page.locator("#view-attention")).to_be_visible()
    expect(first).to_have_attribute("tabindex", "-1")
    attention.press("End")
    last = tabs.get_by_role("tab", name="Datakwaliteit", exact=True)
    expect(last).to_be_focused()
    last.press("ArrowRight")
    expect(first).to_be_focused()
    first.press("ArrowLeft")
    expect(last).to_be_focused()
    last.press("Home")
    expect(first).to_be_focused()
    tabs.get_by_role("tab", name="Verdieping", exact=True).click()
    deep = page.get_by_role("tablist", name="Verdieping", exact=True)
    peers = deep.get_by_role("tab", name="Peers", exact=True)
    peers.focus()
    peers.press("ArrowRight")
    bursts = deep.get_by_role("tab", name="Bursts", exact=True)
    expect(bursts).to_be_focused()
    expect(page.locator("#deep-bursts")).to_be_visible()
    bursts.press("End")
    expect(deep.get_by_role("tab", name="Redengebruik")).to_be_focused()
    deep.get_by_role("tab", name="Redengebruik").press("Home")
    expect(peers).to_be_focused()
    assert page.evaluate(
        """() => [...document.querySelectorAll('[role=tablist]')].every(list=>{
          const tabs=[...list.querySelectorAll('[role=tab]')];
          return tabs.filter(t=>t.tabIndex===0).length===1&&tabs.every(t=>{
            const panel=document.getElementById(t.getAttribute('aria-controls'));
            return panel.getAttribute('role')==='tabpanel'&&
              panel.getAttribute('aria-labelledby')===t.id&&
              panel.hidden===(t.getAttribute('aria-selected')!=='true');
          });
        })"""
    )


def test_table__sorts_complete_data_via_enter_and_space_and_labels_search(page) -> None:
    """A native header button sorts both directions without losing keyboard focus."""
    analyze(page)
    page.get_by_role("tab", name="Medewerkers", exact=True).click()
    table = page.locator("#employeesTable")
    expect(table.locator(".table-search")).to_have_attribute(
        "aria-label", "Zoek in tabel Medewerkers"
    )
    button = table.get_by_role("button", name="Sorteer op Escalaties", exact=True)
    header = table.locator('th[data-col="Escalaties"]')
    button.focus()
    button.press("Enter")
    expect(header).to_have_attribute("aria-sort", "ascending")
    expect(button).to_be_focused()
    expect(header.locator(".sort-indicator")).to_have_text("↑")
    index = table.locator("th").all_text_contents().index("Escalaties↑")
    values = table.locator(f"tbody tr td:nth-child({index + 1})").all_text_contents()
    numbers = [int(value.replace(".", "")) for value in values]
    assert numbers == sorted(numbers)
    button.press("Space")
    expect(header).to_have_attribute("aria-sort", "descending")
    expect(button).to_be_focused()
    values = table.locator(f"tbody tr td:nth-child({index + 1})").all_text_contents()
    numbers = [int(value.replace(".", "")) for value in values]
    assert numbers == sorted(numbers, reverse=True)
    table.get_by_role("button", name="Sorteer op Medewerker", exact=True).click()
    expect(header).to_have_attribute("aria-sort", "none")
    expect(header.locator(".sort-indicator")).to_have_text("↕")


def test_status__announces_once_and_shows_success_next_to_export(page) -> None:
    """A real PNG download yields text, success styling and one shared live region."""
    analyze(page)
    with page.expect_download():
        page.locator("#pngBtn").click()
    expect(page.locator("#status")).to_have_text("Dashboard als PNG gedownload.")
    expect(page.locator("#status")).to_have_attribute("role", "status")
    expect(page.locator("#status")).to_have_attribute("aria-live", "polite")
    for selector in ("#status", "#actionStatus", "#settingsStatus"):
        expect(page.locator(selector)).to_have_class(re.compile(r"\bok\b"))
    expect(page.locator("#actionStatus")).to_be_visible()
    expect(page.locator("#actionStatus")).to_have_text("Dashboard als PNG gedownload.")
    assert page.locator("#status").evaluate("el=>getComputedStyle(el).color") == "rgb(22, 121, 76)"
    for selector in ("#actionStatus", "#settingsStatus"):
        expect(page.locator(selector)).to_have_attribute("aria-hidden", "true")
        assert page.locator(selector).get_attribute("aria-live") is None
        assert page.locator(selector).get_attribute("role") is None


@pytest.mark.parametrize(
    ("key", "bad", "good", "bound"),
    [
        ("activeAccessMinutes", "0", "1", "minimaal 1"),
        ("nightStartHour", "24", "23", "0 tot en met 23"),
        ("activationDelayThresholdMinutes", "-1", "0", "minimaal 0"),
    ],
)
def test_settings__names_bounds_focuses_error_and_clears_on_recovery(
    page, key, bad, good, bound
) -> None:
    """Invalid input does not change the analysis and recovered input loses the error marking."""
    analyze(page)
    page.locator("#settingsBtn").click()
    before = page.evaluate("JSON.stringify(state.settings)")
    field = page.locator(f"#set-{key}")
    label = page.locator(f'label[for="set-{key}"]').text_content()
    field.fill(bad)
    page.locator("#rerunBtn").click()
    expect(field).to_be_focused()
    expect(field).to_have_attribute("aria-invalid", "true")
    expect(page.locator("#settingsStatus")).to_contain_text(label)
    expect(page.locator("#settingsStatus")).to_contain_text(bound)
    assert page.evaluate("JSON.stringify(state.settings)") == before
    field.fill(good)
    assert field.get_attribute("aria-invalid") is None
    expect(page.locator("#settingsStatus")).to_contain_text("Instelling hersteld")
