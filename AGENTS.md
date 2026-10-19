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
| `CHANGELOG.md` | Release history with user-visible changes grouped by SemVer version. |
| `pyproject.toml` / `.mdformat.toml` | Development dependencies and configuration for djLint, Ruff, pytest, coverage and mdformat. |
| `uv.lock` | Reproducible lockfile for development-only Python tooling. |
| `tests/generate_synthetic_escalatielog.py` | Seeded CLI generator for deterministic, data-free XLSX exports. |
| `tests/fixtures/synthetic-escalatielog.xlsx` | Standard synthetic export: 2,000 rows generated with seed `20260918`; safe to commit. |
| `tests/test_report_layout.py` | Synthetic Playwright regression test for exported report tables; contains no personal data. |
| `docs/berekeningen-en-patroonherkenning.md` | Authoritative functional/technical reference (16 sections): populations, signals, thresholds, tie-breaks, defaults (§14), reference results (§15). Has frontmatter with `updated:` date. |
| `docs/assets/` | SVG diagrams used by README/docs. All text must stay inside the viewBox; `scripts/check-svg-text-bounds.sh` (and CI) enforce this. |
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
   - **XLSX reader**: hand-written ZIP (local-file headers, stored + deflate via `DecompressionStream('deflate-raw')`), shared strings, `parseWorksheet`, sheet selection = first sheet whose first 10 rows contain all required headers. Elements are matched by local name (`getElementsByTagNameNS('*', …)`), so namespace prefixes work; cells/rows without an `r` attribute take the previous index + 1; phonetic runs (`rPh`) in shared/inline strings are ignored. Error cells (`t="e"`) become `''` and are recorded per row as non-enumerable `__errorCols` → `errorFields` → Datakwaliteit *Foutcel in bron* (manualRows only, so error cells in system rows are not reported). No ZIP64, no merging of sheets.
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

## Versiebeleid vóór merge naar main

- Iedere wijziging aan `escalatielog-audit-webui.html` naar `main` bevat in dezelfde PR een hogere SemVer en een nieuwe of bijgewerkte gedateerde changelogsectie voor die versie. Nieuwe functionaliteit verhoogt minor; bugfixes verhogen patch. Beoordeel breaking changes bewust volgens SemVer, met aandacht voor de pre-1.0-status. CI controleert dat de versie stijgt, maar bepaalt niet het wijzigingstype.
- Houd `APP_VERSION`, `project.version`, de README-badge en de projectversie in `uv.lock` gelijk. Bij productwijzigingen naar `main` is *Nog niet uitgebracht* leeg. Op `dev` mogen wijzigingen daar worden verzameld.
- Wijzigingen uitsluitend aan documentatie, tests, scripts of CI vereisen geen productbump. Leg ze wel vast onder *Nog niet uitgebracht* → `### Onderhoud` in `CHANGELOG.md`, zodat ze niet uit beeld raken. De eerstvolgende productwijziging naar `main` verplaatst die regels naar de sectie van de nieuwe versie; de versiecontrole en `check_release_version.py --release` weigeren een release zolang *Nog niet uitgebracht* gevuld is. De single-file HTML is de volledige runtime; ook HTML-opmaakwijzigingen tellen conservatief als productwijziging. Analyse en visuele veranderingen blijven onder de bestaande documentatie- en bewijsregels vallen.
- Controleer de gecommitteerde wijziging lokaal met `uv run python scripts/check_main_version.py --base origin/main --head HEAD` na het ophalen van de actuele doelbranch. De controle vergelijkt Git-commits, niet ongecommitteerde bestanden.
- Een push die `main` aanmaakt of herstelt heeft de null-SHA als basis; de versiecontrole faalt dan bewust met de uitleg dat handmatig met de laatst uitgebrachte versie moet worden vergeleken.
- De bestaande verplichte CI-status **Versiecontrole** controleert de doelbranch-SHA voor PR's naar `main`, de merge queue en pushes op `main`, zonder padfilter. Ontbrekende refs zijn een fout. Publiceren blijft een afzonderlijke handmatige stap via de bestaande releaseworkflow; een merge publiceert geen release automatisch.

## Verifying changes

Run `scripts/install-dependencies.sh --check` to prepare and validate a fresh Linux Codex Cloud environment. The script installs the pinned uv version when needed, synchronizes the lockfile, activates the Git hooks in `.githooks/` (`git config core.hooksPath .githooks`) and prefers a distribution-provided Chromium so setup does not depend on the Playwright browser download.

Run the development checks with `uv sync --locked` followed by `scripts/run-checks.sh`: that is the single list CI and `--check` share (version, privacy paths, production docs, mdformat, djLint, Ruff, SVG text bounds and pytest). The existing `--cov=tests` coverage follows Playwright greenlets and measures Python test/support code under `tests/`, not the runtime JavaScript or `scripts/`. This Python test-code gate must remain at or above 85%. `tests/test_app_coverage.py` separately uses Chromium CDP to report the proportion of V8-reported named inline-app functions called in one synthetic reference scenario (load, analysis, navigation, drilldown, CSV and HTML export). `tests/conftest.py` prints this report in local and CI pytest summaries, including uncalled function names. It is reporting only, with no JavaScript threshold; it is not line/branch coverage or coverage aggregated over the full suite. A called function may still contain untested paths. The pytest suite verifies the committed standard synthetic export, builds a temporary layout-focused XLSX file and checks exported report tables in a locally installed Chrome, Edge or Chromium browser; it must not use files from `escalatielogs/`.

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

For performance changes, run `uv run python scripts/measure_render_performance.py [--html PATH] [--runs N]` before and after the change and record both outputs in the PR. It builds a deterministic synthetic set of 50,000 rows, 3,000 employees and 20,000 clients in the page and prints JSON with the per-run and median durations of `analyze()`, `render()` and each `render*` sub-step. Use at least 3 runs, measure the baseline from a copy of the base HTML (`--html`), and keep other browsers and test runs idle while measuring.

## Productiedocumentatie

Op `main` bevat `docs/` uitsluitend `berekeningen-en-patroonherkenning.md` en de
zes gebruikte SVG-diagrammen. `scripts/check-production-docs.py` bevat de vaste
toelatingslijst en controleert ook of toegestane bestanden ontbreken.
Mock-ups, screenshots, PDF-proefafdrukken, QA-resultaten, ontwerpbesluiten en
ontwikkelhandleidingen horen alleen op `dev` of lokaal in het gitignored
`to-do/`. Verplaats ze niet naar een andere gevolgde map op `main`.

Voer vóór een wijziging naar `main` `uv run python scripts/check-production-docs.py`
uit. GitHub Actions controleert de volledige resulterende Git-boom voor pull
requests naar `main`, de merge queue en pushes op `main`, zonder padfilter.
De status `Productiedocumentatie` moet verplicht zijn in de branchbescherming
van `main`; een falende workflow alleen blokkeert geen merge zonder die instelling.
Bij een productiewijziging vanuit `dev` moeten ontwikkelbestanden dus uit de
resulterende boom worden verwijderd. Breid de toelatingslijst alleen uit voor
actuele gebruikersdocumentatie en daadwerkelijk gebruikte diagrammen.

## Conventions

- Keep the single-file architecture; do not split into modules or introduce a bundler.
- Format HTML markup with `uv run djlint . --reformat`. The configured formatter leaves embedded CSS and JavaScript compact; keep their one-line functions, `const` maps and minimal comments, and don't reformat unrelated lines.
- Commit messages follow `type emoji: Dutch imperative summary`, e.g. `docs 📝: Voeg uitleg over de analyseketen toe aan de README`, `chore 📦: …`.
- Never commit anything from `escalatielogs/` or `exports/`; both contain real personal data. `scripts/check-sensitive-paths.sh` blocks (case-insensitive) everything under those directories except `.gitkeep`, every `*.xlsx` outside `tests/fixtures/` and every file whose name starts with `escalatie_log_controle_`. The `.githooks/` pre-commit and pre-push hooks run the same check; `scripts/install-dependencies.sh` activates them with `git config core.hooksPath .githooks`.
- Do not create commits or PRs unless explicitly asked.

## Issues and pull requests

- Apply the repository's existing labels to every issue and pull request. Inspect the available labels first and select only labels that describe the primary type and relevant cross-cutting concerns; do not invent near-duplicate labels without explicit approval.
- Every pull request must link the issue or issues it addresses. Use a GitHub closing keyword such as `Closes #123` only when merging the PR fully resolves that issue; otherwise use a non-closing reference such as `Relates to #123` and state what remains.
- Attach a screenshot or short video only when an issue or pull request concerns visual changes in the webui. Prefer a clear before/after pair. Skip visual evidence for all other changes, including analysis logic, scripts, CI, tests and documentation.
- When visual evidence is required, upload it to the pull request so reviewers can view it directly; a local filesystem path is not sufficient.
- Screenshots and videos must use synthetic or otherwise non-personal data. Never attach source files or generated exports from `escalatielogs/` or `exports/` to an issue or pull request.
- Do not open a pull request while its required issue link or labels are missing. For visual webui changes, also require the visual evidence; if it cannot be produced, stop and ask the user how to proceed.
