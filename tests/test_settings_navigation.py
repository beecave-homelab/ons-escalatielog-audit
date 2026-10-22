"""Settings panel navigation via the upload button and aligned panel actions (#113, #115)."""

import os
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_report_layout import ROOT, STANDARD_FIXTURE, launch_browser

WEBUI = Path(os.environ.get("AUDIT_WEBUI_HTML", ROOT / "escalatielog-audit-webui.html"))

ACTIONS = ["#rerunBtn", "#exportSettingsBtn", "#importSettingsBtn"]


def analyze(page) -> None:
    """Run the standard analysis through the normal upload flow."""
    page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
    page.locator("#analyzeBtn").click()
    page.locator("#workspace.show").wait_for(timeout=30_000)


def action_boxes(page) -> list:
    """Return the geometry of the three settings actions in DOM order."""
    return page.evaluate(
        """selectors => selectors.map(sel => {
          const el = document.querySelector(sel), r = el.getBoundingClientRect();
          return {id: sel, top: r.top, left: r.left, right: r.right, height: r.height,
                  scrollWidth: el.scrollWidth, clientWidth: el.clientWidth};
        })""",
        ACTIONS,
    )


def assert_aligned_row(page) -> None:
    """The three actions form one row with shared top, height and gaps."""
    boxes = action_boxes(page)
    tops = [box["top"] for box in boxes]
    assert max(tops) - min(tops) <= 1, f"De instellingsknoppen staan niet op één lijn: {tops}"
    choose_height = page.evaluate(
        "document.querySelector('#chooseBtn').getBoundingClientRect().height"
    )
    assert all(abs(box["height"] - choose_height) <= 1 for box in boxes), (
        "Een instellingsknop is hoger dan een gewone knopregel."
    )
    lefts = [box["left"] for box in boxes]
    assert lefts == sorted(lefts), "De knopvolgorde is niet links naar rechts."
    gaps = [
        boxes[1]["left"] - boxes[0]["right"],
        boxes[2]["left"] - boxes[1]["right"],
    ]
    assert abs(gaps[0] - gaps[1]) <= 1, f"De tussenruimtes tussen de knoppen lopen uiteen: {gaps}"


def assert_contained_actions(page) -> None:
    """The actions sit inside the card below the text without overflow or overlap."""
    metrics = page.evaluate(
        """selectors => {
          const boxes = selectors.map(sel => {
            const el = document.querySelector(sel), r = el.getBoundingClientRect();
            return {id: sel, top: r.top, left: r.left, right: r.right, bottom: r.bottom,
                    scrollWidth: el.scrollWidth, clientWidth: el.clientWidth};
          });
          const card = document.querySelector('#view-settings .section-card')
            .getBoundingClientRect();
          const text = document.querySelector('.settings-head > div:first-child')
            .getBoundingClientRect();
          return {boxes, card: {left: card.left, right: card.right, top: card.top,
                                bottom: card.bottom},
                  textBottom: text.bottom,
                  pageOverflow: document.documentElement.scrollWidth > innerWidth};
        }""",
        ACTIONS,
    )
    assert metrics["pageOverflow"] is False, "De pagina heeft horizontale overflow."
    card = metrics["card"]
    boxes = metrics["boxes"]
    for box in boxes:
        assert box["scrollWidth"] <= box["clientWidth"], f"De tekst van {box['id']} wordt afgekapt."
        assert card["left"] - 1 <= box["left"] and box["right"] <= card["right"] + 1, (
            f"{box['id']} valt buiten de instellingenkaart."
        )
        for other in boxes:
            if other is box:
                continue
            overlap = not (
                box["right"] <= other["left"] + 1
                or other["right"] <= box["left"] + 1
                or box["bottom"] <= other["top"] + 1
                or other["bottom"] <= box["top"] + 1
            )
            assert not overlap, f"{box['id']} overlapt met {other['id']}."
    first_top = min(box["top"] for box in boxes)
    assert first_top >= metrics["textBottom"] - 1, "De knoppen staan niet onder de uitlegtekst."


@pytest.mark.parametrize(
    "viewport", [{"width": 1440, "height": 900}, {"width": 390, "height": 844}]
)
def test_main_tablist_has_no_settings_tab(viewport) -> None:
    """The Hoofdtabbladen tablist has no Instellingen tab before or after analysis."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport=viewport)
        page.goto(WEBUI.as_uri())
        tabs = page.get_by_role("tablist", name="Hoofdtabbladen")
        expect(tabs.get_by_role("tab", name="Instellingen", exact=True)).to_have_count(0)
        assert page.locator('.tab[data-view="settings"]').count() == 0, (
            "Het tabblad Instellingen bestaat nog vóór de analyse."
        )
        analyze(page)
        expect(tabs.get_by_role("tab", name="Instellingen", exact=True)).to_have_count(0)
        assert page.locator('.tab[data-view="settings"]').count() == 0, (
            "Het tabblad Instellingen bestaat nog na de analyse."
        )
        browser.close()


def test_settings_button_opens_panel_before_analysis() -> None:
    """#settingsBtn opens the panel, focuses the title and stays open on a second click."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        page.goto(WEBUI.as_uri())
        page.locator("#settingsBtn").click()
        expect(page.locator("#settingsGrid")).to_be_visible()
        expect(page.locator("#settingsBtn")).to_have_attribute("aria-expanded", "true")
        expect(page.locator("#settingsTitle")).to_be_focused()
        page.locator("#settingsBtn").click()
        expect(page.locator("#settingsGrid")).to_be_visible()
        expect(page.locator("#settingsBtn")).to_have_attribute("aria-expanded", "true")
        browser.close()


def test_settings_panel_replaces_and_restores_analysis_panels() -> None:
    """Opening settings hides every tab panel; any tab choice returns to the analysis."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        page.goto(WEBUI.as_uri())
        analyze(page)
        page.locator('.tab[data-view="teams"]').click()
        page.locator("#settingsBtn").click()
        expect(page.locator("#view-settings")).to_be_visible()
        assert page.evaluate(
            "[...document.querySelectorAll('#workspace .view')].every(p=>p.hidden)"
        ), "Niet alle analysespanelen zijn verborgen terwijl Instellingen open is."
        assert page.locator('#tabs [role="tab"][aria-selected="true"]').count() == 0, (
            "Er is nog een tabblad geselecteerd terwijl Instellingen open is."
        )
        assert (
            page.evaluate(
                "[...document.querySelectorAll('#tabs [role=tab]')]"
                ".filter(t=>t.tabIndex===0).length"
            )
            == 1
        ), "Er moet precies één tab-stop in de tabbalk overblijven."
        assert page.evaluate("document.querySelector('#actionStatus').hidden") is True
        page.locator('.tab[data-view="attention"]').click()
        expect(page.locator("#view-settings")).to_be_hidden()
        expect(page.locator("#settingsBtn")).to_have_attribute("aria-expanded", "false")
        expect(page.locator("#view-attention")).to_be_visible()
        assert page.evaluate("document.querySelector('#actionStatus').hidden") is False
        page.locator("#settingsBtn").click()
        page.locator('#tabs [role="tab"][tabindex="0"]').focus()
        page.keyboard.press("ArrowRight")
        expect(page.locator("#view-settings")).to_be_hidden()
        expect(page.locator('.tab[data-view="employees"]')).to_have_attribute(
            "aria-selected", "true"
        )
        expect(page.locator("#view-employees")).to_be_visible()
        browser.close()


def test_invalid_settings_reopen_panel_after_analysis() -> None:
    """Rejected input reopens the settings panel with the field focused and marked."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        page.goto(WEBUI.as_uri())
        analyze(page)
        page.locator("#settingsBtn").click()
        field = page.locator("#set-activeAccessMinutes")
        field.fill("0")
        page.locator('.tab[data-view="overview"]').click()
        expect(page.locator("#view-settings")).to_be_hidden()
        page.locator("#analyzeBtn").click()
        expect(page.locator("#view-settings")).to_be_visible()
        expect(field).to_be_focused()
        expect(field).to_have_attribute("aria-invalid", "true")
        browser.close()


@pytest.mark.parametrize("width", [1440, 1100])
def test_settings_actions_align_at_wide_viewport(width) -> None:
    """The actions share one aligned row before and after analysis at wide viewports."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.goto(WEBUI.as_uri())
        page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
        page.locator("#settingsBtn").click()
        expect(page.locator("#rerunBtn")).to_have_text("Analyse uitvoeren")
        assert_aligned_row(page)
        page.locator("#analyzeBtn").click()
        page.locator("#workspace.show").wait_for(timeout=30_000)
        page.locator("#settingsBtn").click()
        expect(page.locator("#rerunBtn")).to_have_text("Analyse opnieuw uitvoeren")
        assert_aligned_row(page)
        browser.close()


@pytest.mark.parametrize("width", [800, 390])
def test_settings_actions_stack_at_narrow_viewport(width) -> None:
    """The actions sit below the text without overflow or overlap at narrow viewports."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": width, "height": 844})
        page.goto(WEBUI.as_uri())
        page.locator("#fileInput").set_input_files(STANDARD_FIXTURE)
        page.locator("#settingsBtn").click()
        assert_contained_actions(page)
        page.locator("#analyzeBtn").click()
        page.locator("#workspace.show").wait_for(timeout=30_000)
        page.locator("#settingsBtn").click()
        expect(page.locator("#rerunBtn")).to_have_text("Analyse opnieuw uitvoeren")
        assert_contained_actions(page)
        browser.close()
