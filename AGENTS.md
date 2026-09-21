# AGENTS.md

Guidance for coding agents working in this repository. Read this first; then `README.md` and `docs/berekeningen-en-patroonherkenning.md` for the functional definitions.

## What this is

A **single-file, offline web app** (`escalatielog-audit-webui.html`) that audits Nedap Ons *escalatielog* exports (`.xlsx`). A functioneel beheerder opens the file in a browser, drops in the export, and gets counts, signals ("aandachtspunten"), drilldowns, a CSV export and a standalone HTML report. Language of UI, docs and commit messages is **Dutch**.

The webui has no build step, server, framework or runtime dependency. Everything is inline HTML/CSS/JS (~820 lines, long lines, dense style). Development-only checks use Python, uv, mdformat, Ruff, pytest and Playwright.

## Repository layout

| Path | Purpose |
| -- | -- |
| `escalatielog-audit-webui.html` | The entire application. Version constant `APP_VERSION` near the top of the `<script>`. |
| `README.md` | User-facing intro, usage, required input columns, privacy. Contains the version badge. |
| `docs/development.md` | Human developer setup, quality checks, synthetic test data and Git privacy safeguards. |
| `CHANGELOG.md` | Release history with user-visible changes grouped by SemVer version. |
| `pyproject.toml` / `.mdformat.toml` | Development dependencies and configuration for djLint, Ruff, pytest, coverage and mdformat. |
| `uv.lock` | Reproducible lockfile for development-only Python tooling. |
| `tests/generate_synthetic_escalatielog.py` | Seeded CLI generator for deterministic, data-free XLSX exports. |
| `tests/fixtures/synthetic-escalatielog.xlsx` | Standard synthetic export: 2,000 rows generated with seed `20260918`; safe to commit. |
| `tests/test_report_layout.py` | Synthetic Playwright regression test for exported report tables; contains no personal data. |
| `docs/berekeningen-en-patroonherkenning.md` | Authoritative functional/technical reference (16 sections): populations, signals, thresholds, tie-breaks, defaults (§14), reference results (§15). Has frontmatter with `updated:` date. |
| `docs/assets/` | SVG diagrams used by README/docs. |
| `escalatielogs/` | Local test exports (**gitignored**, contain personal data; never commit). The historically used May export `Escalatielogs 01-05-2026 tot 31-05-2026.xlsx` lives here; it is not a documentation reference — docs §15 points at the committed synthetic fixture. |
| `exports/` | Output written during manual testing (**gitignored**; contains personal data — never commit). |
| `to-do/` | Gitignored local scratch/todo directory; not used by the webui. |
| `project-overview.md` | Gitignored; not present in this repo. |

## Architecture of the HTML file

Sections, in file order:

1. `<head>`: strict CSP (`default-src 'none'; connect-src 'none'`, inline style/script only). **Do not relax it** and do not add `fetch`/XHR/storage APIs — "geen netwerkverkeer, geen browseropslag" is a documented product guarantee.
2. `<style>`: all CSS.
3. `<body>`: upload card, tab bar, tab panels (Overzicht, Aandachtspunten, Medewerkers/Cliënten/Teams/…, Verdieping, Auditlogica, Systeem, Datakwaliteit, Instellingen), drilldown overlay, footer. Elements with class `app-version` are filled from `APP_VERSION` at startup.
4. `<script>`:
   - **Constants**: `APP_VERSION`, `REQUIRED_HEADERS` (14 columns), `SYSTEM_REASONS`, `SIGNAL_META`, `DEFAULT_SETTINGS`, `SETTINGS_SCHEMA`, `SOURCE_COLUMNS`.
   - **XLSX reader**: hand-written ZIP (local-file headers, stored + deflate via `DecompressionStream('deflate-raw')`), shared strings, `parseWorksheet`, sheet selection = first sheet whose first 10 rows contain all required headers. No ZIP64, no error cells, no merging of sheets.
   - **Normalisation**: `parseDate` (Excel serial 1900-system, `dd-mm-yyyy, hh:mm[:ss]`, ISO with `T`; date-only text is rejected), `normalizeRows`, `isSystemEvent`, `exactRowKey`/`deduplicateManualRows`.
   - **Analysis**: `analyze()` builds the populations `allRows → systemRows / manualRows → duplicateRows / auditRows → attention`, computes signals, then `peerAnalysis`, `burstAnalysis`, `clientClusterAnalysis`, `concentrationAnalysis`, `reasonUseAnalysis`, `auditLogicAnalysis`, `aggregate*`, `analyzeQuality`. All findings that end up in exports must be produced here, **not in render functions**.
   - **Rendering**: `render()` → `renderOverview`, `renderTables`, `renderDeepDive`, `renderAuditLogic`, `renderTime`, `tableWidget` (search/sort/filter are view-only), `openDrilldown` (rows carry non-enumerable `__rows`/`previousSourceRow` metadata).
   - **Exports**: `toCsv` (`;` separator, BOM, CRLF, formula-injection guard for `=`, `+`, `@`, `-…` but not bare `-` or plain numbers), `exportAttentionCsv`, `exportDrilldownCsv`, `exportReport` (self-contained HTML string template; tables render as collapsible `<details>` sections grouped under an anchor TOC, and a `beforeprint` handler opens all sections for printing). File names via `exportBaseName`. Both the CSVs and the HTML report contain personal data; treat them with the same care as the source export.
   - **Settings**: `renderSettings`/`readSettings`; integers only, hours 0–23, activation delay may be 0, other thresholds ≥1; invalid input is rejected without applying.

Always HTML-escape with `esc()` before inserting data into the DOM or the report.

## Invariants to keep

- Reconciliation: `allRows = systemRows + duplicateRows + auditRows`. The optional 30-minute exclusion is applied inside `isSystemEvent`, so excluded rows count as `systemRows` and the identity always holds. Datakwaliteit uses `manualRows`; Auditlogica uses `allRows`.
- Signal semantics documented in docs §7–§11: inclusive re-escalation window, tie-break on lower Excel row, activation delay strictly `>` threshold, night window wrap-around (start inclusive, end exclusive), theme-based priority, dedup on all 14 trimmed source fields (first copy kept).
- A row can carry several signals but counts **once** as an aandachtspunt.
- Wording: signals are triage indicators, never proof of unlawful access or dossier viewing. Keep such disclaimers in UI, report and docs.
- **Docs follow code**: the docs state that the implementation wins on conflict and must be updated. Any behavioural change ⇒ update the relevant section in `docs/berekeningen-en-patroonherkenning.md` (and its `updated:` date) and, if user-visible, `README.md`.
- **Version**: semver only (`0.6.0` style). Keep `APP_VERSION` in the HTML, `project.version` in `pyproject.toml` and the badge in `README.md` equal, and record each release in `CHANGELOG.md`. Never write `v6`, `v6.0`, etc.

## Verifying changes

Run `scripts/install-dependencies.sh --check` to prepare and validate a fresh Linux Codex Cloud environment. The script installs uv when needed, synchronizes the lockfile and prefers a distribution-provided Chromium so setup does not depend on the Playwright browser download.

Run the development checks with `uv sync --locked`, `uv run mdformat --check README.md CHANGELOG.md AGENTS.md docs`, `uv run djlint . --check`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` and `uv run pytest --cov=tests --cov-report=term-missing:skip-covered`. Coverage follows Playwright greenlets and must remain at or above 85%. The pytest suite verifies the committed standard synthetic export, builds a temporary layout-focused XLSX file and checks exported report tables in a locally installed Chrome, Edge or Chromium browser; it must not use files from `escalatielogs/`.

For the full analysis regression, re-run the synthetic reference file `tests/fixtures/synthetic-escalatielog.xlsx` with default settings and compare to docs §15. Key figures:

| Controle | Uitkomst |
| -- | -: |
| Bronregels / systeemregels / duplicaten / auditregels | 2000 / 156 / 42 / 1802 |
| Medewerkers / cliënten / locatiedoelen | 250 / 558 / 40 |
| Niet geactiveerd / nacht / late activatie / ongeldige activatie | 310 / 544 / 1391 / 66 |
| Her-escalaties / zeer snel | 0 / 0 |
| Unieke aandachtspunten | 1790 (99,3 %) |
| Bursts / cliëntclusters | 0 / 5 |

For the manual reference check, open the HTML in Chromium/Chrome (needs `DecompressionStream`; Edge/Chrome 80+, Firefox 113+, Safari 16.4+). Check the console for errors, verify the figures above, exercise one drilldown, one CSV export and the HTML report. If figures change intentionally, update docs §15 in the same change.

For synthetic edge cases, call `analyze()`/`analyzeQuality()` directly in the page context with hand-built row objects.

## Conventions

- Keep the single-file architecture; do not split into modules or introduce a bundler.
- Format HTML markup with `uv run djlint . --reformat`. The configured formatter leaves embedded CSS and JavaScript compact; keep their one-line functions, `const` maps and minimal comments, and don't reformat unrelated lines.
- Commit messages follow `type emoji: Dutch imperative summary`, e.g. `docs 📝: Voeg uitleg over de analyseketen toe aan de README`, `chore 📦: …`.
- Never commit anything from `escalatielogs/` or `exports/`; both contain real personal data.
- Do not create commits or PRs unless explicitly asked.

## Issues and pull requests

- Apply the repository's existing labels to every issue and pull request. Inspect the available labels first and select only labels that describe the primary type and relevant cross-cutting concerns; do not invent near-duplicate labels without explicit approval.
- Every pull request must link the issue or issues it addresses. Use a GitHub closing keyword such as `Closes #123` only when merging the PR fully resolves that issue; otherwise use a non-closing reference such as `Relates to #123` and state what remains.
- Attach a screenshot or short video only when an issue or pull request concerns visual changes in the webui. Prefer a clear before/after pair. Skip visual evidence for all other changes, including analysis logic, scripts, CI, tests and documentation.
- When visual evidence is required, upload it to the pull request so reviewers can view it directly; a local filesystem path is not sufficient.
- Screenshots and videos must use synthetic or otherwise non-personal data. Never attach source files or generated exports from `escalatielogs/` or `exports/` to an issue or pull request.
- Do not open a pull request while its required issue link or labels are missing. For visual webui changes, also require the visual evidence; if it cannot be produced, stop and ask the user how to proceed.
