"""Regression tests for issue #49: datakwaliteit evidence binding.

Verifies that analyzeQuality binds __rows evidence at creation time,
that the drilldown matches Aantal, and that renderEvidenceLinks does
not infer or mutate quality findings.
"""

from pathlib import Path

from playwright.sync_api import sync_playwright
from test_report_layout import launch_browser

ROOT = Path(__file__).resolve().parents[1]


def _make_near_duplicate_rows():
    """Three manual rows: two exact duplicates, one near-duplicate.

    The near-duplicate differs in Tijdsduur (min.) and
    Escalatiedoel identificatienummer, so its exactRowKey differs.
    """
    base = {
        "userName": "Test Medewerker",
        "employeeNumber": "M001",
        "employeeTeam": "Team A",
        "expertise": "Verpleegkundige",
        "loginName": "tmedew",
        "reason": "Werkoverleg",
        "reasonNorm": "werkoverleg",
        "durationRaw": "15",
        "durationMinutes": 15,
        "targetType": "Cli\u00ebnt",
        "targetName": "Cli\u00ebnt X",
        "targetId": "C100",
        "clientLocation": "Locatie 1",
        "startedRaw": "01-05-2026, 09:30:00",
        "activatedRaw": "01-05-2026, 09:32:00",
        "source": "Synthetische generator",
        "notActivated": False,
        "signals": [],
    }
    started = {
        "epoch": 1777627800000,
        "dateKey": "2026-05-01",
        "hour": 9,
        "weekday": 5,
        "display": "01-05-2026, 09:30:00",
        "day": 1,
        "month": 5,
        "year": 2026,
    }
    activated = {
        "epoch": 1777627920000,
        "display": "01-05-2026, 09:32:00",
    }

    def row(source_row, **overrides):
        r = {**base, "sourceRow": source_row, "started": started, "activated": activated}
        r.update(overrides)
        return r

    # Two exact duplicates (all 14 source fields identical)
    r1 = row(2)
    r2 = row(3)
    # Near-duplicate: differs in duration and targetId
    r3 = row(4, durationRaw="30", durationMinutes=30, targetId="C200")

    return [r1, r2, r3]


def _make_namespace_collision_rows():
    """Rows where employeeNumber of one person equals loginName of another.

    Identifier conflict on employeeNumber M002 should only bring rows
    with employeeNumber M002, not rows where loginName happens to be M002.
    """
    started = {
        "epoch": 1777627800000,
        "dateKey": "2026-05-01",
        "hour": 9,
        "weekday": 5,
        "display": "01-05-2026, 09:30:00",
        "day": 1,
        "month": 5,
        "year": 2026,
    }
    base = {
        "employeeTeam": "Team A",
        "expertise": "Verpleegkundige",
        "reason": "Werkoverleg",
        "reasonNorm": "werkoverleg",
        "durationRaw": "15",
        "durationMinutes": 15,
        "targetType": "Cli\u00ebnt",
        "targetName": "Cli\u00ebnt X",
        "targetId": "C100",
        "clientLocation": "Locatie 1",
        "startedRaw": "01-05-2026, 09:30:00",
        "activatedRaw": "01-05-2026, 09:32:00",
        "source": "Synthetische generator",
        "notActivated": False,
        "signals": [],
        "started": started,
        "activated": {"epoch": 1777627920000, "display": "01-05-2026, 09:32:00"},
    }

    # Person A: employeeNumber M002, loginName userA, userName "Alice"
    # Person B: employeeNumber M999, loginName M002, userName "Bob"
    # The loginName "M002" of Bob equals employeeNumber "M002" of Alice.
    # Identifier conflict on M002 (employeeNumber) should only bring Alice's rows.
    r1 = {
        **base,
        "sourceRow": 2,
        "userName": "Alice",
        "employeeNumber": "M002",
        "loginName": "userA",
    }
    r2 = {
        **base,
        "sourceRow": 3,
        "userName": "Alice2",
        "employeeNumber": "M002",
        "loginName": "userA2",
    }
    r3 = {**base, "sourceRow": 4, "userName": "Bob", "employeeNumber": "M999", "loginName": "M002"}

    return [r1, r2, r3]


def _make_separate_exact_groups_rows():
    """Two distinct exact-duplicate groups that share summary fields.

    Both groups have the same employeeNumber/startedRaw and reason/targetName
    but differ in another field (e.g. targetId), so they are separate groups.
    """
    started = {
        "epoch": 1777627800000,
        "dateKey": "2026-05-01",
        "hour": 9,
        "weekday": 5,
        "display": "01-05-2026, 09:30:00",
        "day": 1,
        "month": 5,
        "year": 2026,
    }
    base = {
        "userName": "Test Medewerker",
        "employeeNumber": "M001",
        "employeeTeam": "Team A",
        "expertise": "Verpleegkundige",
        "loginName": "tmedew",
        "reason": "Werkoverleg",
        "reasonNorm": "werkoverleg",
        "durationRaw": "15",
        "durationMinutes": 15,
        "targetType": "Cli\u00ebnt",
        "targetName": "Cli\u00ebnt X",
        "startedRaw": "01-05-2026, 09:30:00",
        "activatedRaw": "01-05-2026, 09:32:00",
        "source": "Synthetische generator",
        "notActivated": False,
        "signals": [],
        "started": started,
        "activated": {"epoch": 1777627920000, "display": "01-05-2026, 09:32:00"},
    }

    # Group 1: targetId C100
    r1 = {**base, "sourceRow": 2, "targetId": "C100", "clientLocation": "Loc 1"}
    r2 = {**base, "sourceRow": 3, "targetId": "C100", "clientLocation": "Loc 1"}
    # Group 2: targetId C200 (same summary fields, different exactRowKey)
    r3 = {**base, "sourceRow": 4, "targetId": "C200", "clientLocation": "Loc 2"}
    r4 = {**base, "sourceRow": 5, "targetId": "C200", "clientLocation": "Loc 2"}

    return [r1, r2, r3, r4]


def test_quality_evidence_near_duplicate_excluded(tmp_path: Path) -> None:
    """Two exact duplicates + one near-duplicate: Aantal=2, drilldown=2 rows."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())

        rows = _make_near_duplicate_rows()
        result = page.evaluate(
            """(rows) => {
              const issues = analyzeQuality(rows);
              const exact = issues.find(i => i['Type issue'] === 'Exact dubbel');
              return {
                totalIssues: issues.length,
                exactAantal: exact ? exact.Aantal : null,
                exactRowsLength: exact ? exact.__rows.length : null,
                exactSourceRows: exact ? exact.__rows.map(r => r.sourceRow) : null,
                nonEnumerable: exact
                  ? !Object.keys(exact).includes('__rows')
                  : null,
              };
            }""",
            rows,
        )

        assert result["exactAantal"] == 2, (
            f"Expected Aantal=2 for exact duplicate group, got {result['exactAantal']}"
        )
        assert result["exactRowsLength"] == 2, (
            f"Expected 2 evidence rows, got {result['exactRowsLength']}"
        )
        assert sorted(result["exactSourceRows"]) == [2, 3], (
            f"Evidence should be rows 2 and 3, got {result['exactSourceRows']}"
        )
        assert result["nonEnumerable"] is True, "__rows must be non-enumerable"
        page.evaluate(
            """(rows) => {
          state.result = analyze(rows, state.settings);
          render();
        }""",
            rows,
        )
        page.locator("#tabs").get_by_role("button", name="Datakwaliteit", exact=True).click()
        page.locator("#qualityTable tbody tr").filter(has_text="Exact dubbel").click()
        assert page.locator("#drillBody tbody tr").count() == 2
        assert page.evaluate("state.drilldown.rows.map(r => r['Excel-rij'])") == [2, 3]
        assert not errors
        browser.close()


def test_quality_evidence_separate_exact_groups(tmp_path: Path) -> None:
    """Two distinct exact groups sharing summary fields must not collapse."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())

        rows = _make_separate_exact_groups_rows()
        result = page.evaluate(
            """(rows) => {
              const issues = analyzeQuality(rows);
              const exactIssues = issues.filter(i => i['Type issue'] === 'Exact dubbel');
              return {
                exactCount: exactIssues.length,
                groups: exactIssues.map(i => ({
                  aantal: i.Aantal,
                  rows: i.__rows.map(r => r.sourceRow),
                })),
              };
            }""",
            rows,
        )

        assert result["exactCount"] == 2, (
            f"Expected 2 separate Exact dubbel issues, got {result['exactCount']}"
        )
        groups = sorted(result["groups"], key=lambda g: g["rows"][0])
        assert groups[0]["aantal"] == 2
        assert sorted(groups[0]["rows"]) == [2, 3]
        assert groups[1]["aantal"] == 2
        assert sorted(groups[1]["rows"]) == [4, 5]
        assert not errors
        browser.close()


def test_quality_evidence_identifier_namespace_separation(tmp_path: Path) -> None:
    """Identifier conflict on employeeNumber must not match loginName."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())

        rows = _make_namespace_collision_rows()
        result = page.evaluate(
            """(rows) => {
              const issues = analyzeQuality(rows);
              const conflicts = issues.filter(i => i['Type issue'] === 'Identifierconflict');
              return conflicts.map(i => ({
                sleutel: i.Sleutel,
                aantal: i.Aantal,
                details: i.Details,
                rows: i.__rows.map(r => r.sourceRow),
              }));
            }""",
            rows,
        )

        # There should be a conflict on employeeNumber M002 (Alice has two names)
        emp_conflicts = [c for c in result if c["sleutel"] == "M002" and "Alice" in c["details"]]
        assert len(emp_conflicts) >= 1, (
            f"Expected identifier conflict on M002 with Alice names, got: {result}"
        )
        emp_conflict = emp_conflicts[0]
        assert emp_conflict["aantal"] == 2
        assert sorted(emp_conflict["rows"]) == [2, 3], (
            f"Conflict on M002 should only include rows 2 and 3, got {emp_conflict['rows']}"
        )
        # Row 4 (Bob, loginName=M002) must NOT appear in the employeeNumber conflict
        assert 4 not in emp_conflict["rows"], (
            "Row 4 with loginName=M002 must not appear in employeeNumber=M002 conflict"
        )
        assert not errors
        browser.close()


def test_quality_evidence_all_categories_have_rows(tmp_path: Path) -> None:
    """Every quality issue must have __rows bound, for all categories."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())

        rows = _make_near_duplicate_rows()
        # Add a row with missing field to trigger Ontbrekend/ongeldig veld
        rows.append(
            {
                "sourceRow": 5,
                "userName": "",
                "employeeNumber": "",
                "employeeTeam": "",
                "expertise": "Verpleegkundige",
                "loginName": "tmedew",
                "reason": "",
                "reasonNorm": "",
                "durationRaw": "15",
                "durationMinutes": 15,
                "targetType": "Cli\u00ebnt",
                "targetName": "Cli\u00ebnt X",
                "targetId": "C100",
                "clientLocation": "Locatie 1",
                "startedRaw": "01-05-2026, 09:30:00",
                "started": {
                    "epoch": 1777627800000,
                    "dateKey": "2026-05-01",
                    "hour": 9,
                    "weekday": 5,
                    "display": "01-05-2026, 09:30:00",
                    "day": 1,
                    "month": 5,
                    "year": 2026,
                },
                "activatedRaw": "01-05-2026, 09:32:00",
                "activated": {"epoch": 1777627920000, "display": "01-05-2026, 09:32:00"},
                "source": "Synthetische generator",
                "notActivated": False,
                "signals": [],
            }
        )
        for index, row in enumerate(_make_namespace_collision_rows(), start=6):
            rows.append({**row, "sourceRow": index})
        rows.append({**rows[0], "sourceRow": 9, "reason": "WERKOVERLEG"})
        rows.append(
            {
                **rows[0],
                "sourceRow": 10,
                "started": None,
                "startedRaw": "ongeldig",
                "activated": None,
                "durationMinutes": None,
            }
        )

        result = page.evaluate(
            """(rows) => {
              const issues = analyzeQuality(rows);
              return issues.map(i => {
                const field = i['Type issue'] === 'Redenvariant' ? 'reason'
                  : i.Toelichting.includes('meerdere namen') ? 'userName'
                  : i.Toelichting.startsWith('Eén gebruikersnaam')
                    ? 'employeeNumber' : 'loginName';
                return {
                  type: i['Type issue'], sleutel: i.Sleutel, aantal: i.Aantal,
                  hasRows: !!i.__rows, rowsCount: i.__rows ? i.__rows.length : 0,
                  distinctCount: i.__rows
                    ? new Set(i.__rows.map(x => x[field]).filter(hasValue)).size : 0,
                  nonEnumerable: !Object.keys(i).includes('__rows'),
                };
              });
            }""",
            rows,
        )

        assert {issue["type"] for issue in result} == {
            "Ontbrekend/ongeldig veld",
            "Identifierconflict",
            "Redenvariant",
            "Exact dubbel",
            "Tijd/duur",
        }
        for issue in result:
            assert issue["hasRows"], f"Issue {issue['type']}/{issue['sleutel']} has no __rows"
            assert issue["nonEnumerable"], (
                f"Issue {issue['type']}/{issue['sleutel']} __rows is enumerable"
            )
            if issue["type"] in {"Identifierconflict", "Redenvariant"}:
                assert issue["distinctCount"] == issue["aantal"]
                assert issue["rowsCount"] >= issue["aantal"]
            else:
                assert issue["rowsCount"] == issue["aantal"], (
                    f"Issue {issue['type']}/{issue['sleutel']}: "
                    f"rowsCount={issue['rowsCount']} != Aantal={issue['aantal']}"
                )
        assert not errors
        browser.close()


def test_quality_evidence_survives_repeated_rendering(tmp_path: Path) -> None:
    """Evidence must be stable before rendering and after repeated rendering."""
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "escalatielog-audit-webui.html").as_uri())

        rows = _make_near_duplicate_rows()

        # Check evidence before rendering
        before = page.evaluate(
            """(rows) => {
              const issues = analyzeQuality(rows);
              const exact = issues.find(i => i['Type issue'] === 'Exact dubbel');
              return {
                aantal: exact.Aantal,
                rowsCount: exact.__rows.length,
                sourceRows: exact.__rows.map(r => r.sourceRow),
              };
            }""",
            rows,
        )

        # Simulate renderEvidenceLinks by calling it with a mock result
        # that has the quality issues
        after = page.evaluate(
            """(rows) => {
              const quality = analyzeQuality(rows);
              const mockResult = {
                quality, manualRows: rows, overview: {blocks:[],notice:''},
                allRows: rows, systemRows: [], duplicateRows: [], auditRows: rows,
                attention: [], signalCounts: new Map(),
                logic: {unexpected30:[],knownNon30:[]}, employees: [], clients: [],
                clientsByBreadth: [], teams: [], reasons: [],
                time: {dates:[],hours:[],weekdays:[]}, themeCounts: {}
              };
              // Call renderEvidenceLinks which now just sets up tableWidget
              // without re-deriving __rows
              renderEvidenceLinks(mockResult);
              // Check the quality issues are unchanged
              const exact = quality.find(i => i['Type issue'] === 'Exact dubbel');
              return {
                aantal: exact.Aantal,
                rowsCount: exact.__rows.length,
                sourceRows: exact.__rows.map(r => r.sourceRow),
              };
            }""",
            rows,
        )

        assert before["aantal"] == 2
        assert before["rowsCount"] == 2
        assert sorted(before["sourceRows"]) == [2, 3]

        assert after["aantal"] == before["aantal"]
        assert after["rowsCount"] == before["rowsCount"]
        assert sorted(after["sourceRows"]) == sorted(before["sourceRows"])
        assert not errors
        browser.close()
