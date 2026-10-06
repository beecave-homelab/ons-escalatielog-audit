"""Voorkom dat macOS-tests persoonlijke Chrome- of Edge-apps starten."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from playwright.sync_api import Error
from test_report_layout import launch_browser


@pytest.mark.parametrize("executable", [None, "/tmp/test-chromium"])
def test_macos_uses_only_test_chromium(monkeypatch, executable):
    monkeypatch.setattr("test_report_layout.sys.platform", "darwin")
    monkeypatch.delenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE", raising=False)
    if executable:
        monkeypatch.setenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE", executable)
    launch = Mock(return_value=object())
    playwright = SimpleNamespace(chromium=SimpleNamespace(launch=launch))
    assert launch_browser(playwright) is launch.return_value
    expected = {"headless": True}
    if executable:
        expected["executable_path"] = executable
    launch.assert_called_once_with(**expected)


def test_macos_failure_does_not_fall_back_to_personal_browsers(monkeypatch):
    monkeypatch.setattr("test_report_layout.sys.platform", "darwin")
    monkeypatch.delenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE", raising=False)
    launch = Mock(side_effect=Error("Synthetisch: testbrowser ontbreekt"))
    playwright = SimpleNamespace(chromium=SimpleNamespace(launch=launch))
    with pytest.raises(pytest.fail.Exception, match="playwright install chromium --only-shell"):
        launch_browser(playwright)
    launch.assert_called_once_with(headless=True)
