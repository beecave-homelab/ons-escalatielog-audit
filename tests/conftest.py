"""Show application function coverage even when tests pass with output capturing."""

from app_coverage import APP_COVERAGE


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """Visibly separate the synthetic JavaScript measurement from Python test coverage."""
    report = config.stash.get(APP_COVERAGE, None)
    if report is None:
        return
    terminalreporter.section("JavaScript-applicatiedekking — synthetisch referentiescenario")
    terminalreporter.write_line(
        f"Benoemde functies (V8): {report['called']}/{report['total']} "
        f"aangeroepen ({report['percentage']:.2f}%)."
    )
    terminalreporter.write_line(
        "Alleen het inline applicatiescript; geen regel-/branchdekking of volledige suitedekking."
    )
    terminalreporter.write_line("Rapportage zonder drempel; de 85%-poort meet Python-testcode.")
    terminalreporter.write_line("Niet aangeroepen functies: " + ", ".join(report["uncalled"]))
