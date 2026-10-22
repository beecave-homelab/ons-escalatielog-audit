# AGENTS.md

Richtlijnen voor codeeragents in deze repository. Lees dit bestand eerst en daarna `README.md` en `docs/berekeningen-en-patroonherkenning.md` voor de functionele definities.

## Wat dit is

Een **offline webapp in één bestand** (`escalatielog-audit-webui.html`) die *escalatielog*-exports (`.xlsx`) uit Nedap Ons controleert. Een functioneel beheerder opent het bestand in een browser, sleept de export erin en krijgt tellingen, signalen ("aandachtspunten"), drilldowns, een CSV-export en een zelfstandig HTML-rapport. De repository is Nederlandstalig, behalve de code zelf; zie [Taal](#taal).

De webui heeft geen buildstap, server, framework of runtime-afhankelijkheid. Alles staat inline in HTML, CSS en JavaScript (ongeveer 1400 regels, lange regels, compacte stijl). Alleen de ontwikkelcontroles gebruiken Python, uv, mdformat, Ruff, pytest en Playwright.

## Taal

Tekst die mensen lezen schrijf je in het Nederlands. Code en codecommentaar schrijf je in het Engels.

In het Nederlands:

- alle tekst in de webui: labels, knoppen, hulpteksten, meldingen en foutmeldingen, het HTML-rapport en de kolomkoppen van CSV-exports;
- `README.md`, `CHANGELOG.md`, `AGENTS.md` en alles onder `docs/`, ook de tekst in de SVG-diagrammen;
- hulpteksten, uitvoer en foutmeldingen van scripts en tests, zoals `--help`, `[controles] Fout: …` en de tekst van exceptions en assertions;
- namen van GitHub Actions-workflows, -jobs en -stappen (`name:`). Hernoem een verplichte status zoals **Versiecontrole** of **Productiedocumentatie** niet zonder de branchbescherming van `main` aan te passen;
- de `description` in `pyproject.toml`;
- commitberichten, issues, pull requests en reviewreacties.

In het Engels:

- de code zelf: functie-, variabele- en klassenamen, testnamen en bestandsnamen van code, zoals `analyze`, `renderOverview` en `test_search_is_debounced`;
- commentaar en docstrings in code-, script- en configuratiebestanden, ook in de inline JavaScript en CSS van de HTML;
- de vaste header van Bash-scripts (`Script Description`, `Author`, `Version`, `License`, `Creation Date`, `Last Modified`, `Usage`), inclusief de beschrijving.

Deze vaste termen blijven zoals ze zijn, ongeacht de taal eromheen:

- de kolomnamen van de Nedap Ons-export in `REQUIRED_HEADERS`, letterlijk zoals de bron ze levert (bijvoorbeeld `Escalatie reden`);
- signaalcodes en andere bestaande domeintermen in de code, zoals `NIET_GEACTIVEERD`;
- het type en de emoji vooraan in een commitbericht (`docs 📝:`) en GitHub-trefwoorden zoals `Closes #123` en `Relates to #123`;
- productnamen.

## Indeling van de repository

| Pad | Doel |
| -- | -- |
| `escalatielog-audit-webui.html` | De volledige applicatie. De versieconstante `APP_VERSION` staat bovenaan de `<script>`. |
| `README.md` | Introductie voor gebruikers, gebruik, verplichte invoerkolommen en privacy. Bevat de versiebadge. |
| `CHANGELOG.md` | Releasegeschiedenis met zichtbare wijzigingen, gegroepeerd per SemVer-versie. |
| `pyproject.toml` / `.mdformat.toml` | Ontwikkelafhankelijkheden en configuratie voor djLint, Ruff, pytest, coverage en mdformat. |
| `uv.lock` | Reproduceerbaar lockbestand voor de Python-hulpmiddelen die alleen bij ontwikkeling nodig zijn. |
| `tests/generate_synthetic_escalatielog.py` | CLI-generator met vaste seed voor deterministische XLSX-exports zonder echte gegevens. |
| `tests/fixtures/synthetic-escalatielog.xlsx` | Synthetische standaardexport: 2.000 regels, gegenereerd met seed `20260918`. Mag worden gecommit. |
| `tests/test_report_layout.py` | Synthetische Playwright-regressietest voor de tabellen in het geëxporteerde rapport. Bevat geen persoonsgegevens. |
| `docs/berekeningen-en-patroonherkenning.md` | Gezaghebbende functionele en technische referentie (19 secties): populaties, signalen, drempels, tie-breaks, standaardinstellingen (§14) en referentie-uitkomsten (§15). Heeft frontmatter met een `updated:`-datum. |
| `docs/assets/` | SVG-diagrammen voor README en docs. Alle tekst moet binnen de viewBox blijven; `scripts/check-svg-text-bounds.sh` en CI controleren dat. |
| `escalatielogs/` | Lokale testexports (**gitignored**, bevatten persoonsgegevens; nooit committen). Hier staat de eerder gebruikte meiexport `Escalatielogs 01-05-2026 tot 31-05-2026.xlsx`. Die is geen referentie voor de documentatie; docs §15 verwijst naar de gecommitte synthetische fixture. |
| `exports/` | Uitvoer van handmatige tests (**gitignored**, bevat persoonsgegevens; nooit committen). |
| `to-do/` | Gitignored lokale werkmap voor kladwerk en takenlijsten. De webui gebruikt deze map niet. |
| `project-overview.md` | Gitignored en niet aanwezig in deze repository. |

## Opbouw van het HTML-bestand

De onderdelen in volgorde van het bestand:

1. `<head>`: strikte CSP (`default-src 'none'; connect-src 'none'`, alleen inline style en script). **Versoepel die niet** en voeg geen `fetch`, XHR of opslag-API's toe. "Geen netwerkverkeer, geen browseropslag" is een gedocumenteerde productbelofte.
2. `<style>`: alle CSS.
3. `<body>`: uploadkaart, tabbalk, tabpanelen (Overzicht, Aandachtspunten, Medewerkers/Cliënten/Teams/…, Verdieping, Auditlogica, Systeem, Datakwaliteit, Instellingen), drilldown-overlay en footer. Bij het opstarten krijgen elementen met de klasse `app-version` de waarde van `APP_VERSION`.
4. `<script>`:
   - **Constanten**: `APP_VERSION`, `REQUIRED_HEADERS` (14 kolommen), `SYSTEM_REASONS`, `SIGNAL_META`, `DEFAULT_SETTINGS`, `SETTINGS_SCHEMA`, `SOURCE_COLUMNS`.
   - **XLSX-lezer**: zelfgeschreven ZIP-lezer (local-file headers, stored en deflate via `DecompressionStream('deflate-raw')`), shared strings en `parseWorksheet`. De lezer kiest het eerste werkblad waarvan de eerste 10 rijen alle verplichte kolomkoppen bevatten. Elementen worden op lokale naam gezocht (`getElementsByTagNameNS('*', …)`), zodat namespace-prefixen werken. Cellen en rijen zonder `r`-attribuut krijgen de vorige index + 1. Fonetische runs (`rPh`) in shared en inline strings worden genegeerd. Foutcellen (`t="e"`) worden `''` en worden per rij vastgelegd als niet-enumereerbare `__errorCols` → `errorFields` → Datakwaliteit *Foutcel in bron*. Dat gebeurt alleen voor manualRows, dus foutcellen in systeemregels worden niet gemeld. Geen ZIP64 en geen samenvoeging van werkbladen. `MAX_ZIP_ENTRY_BYTES` (512 MB) begrenst de uitgepakte grootte per ZIP-onderdeel en een uitgepakte grootte die afwijkt van de central directory wordt afgewezen.
   - **Normalisatie**: `parseDate` (Excel-serienummer in het 1900-systeem, `dd-mm-yyyy, hh:mm[:ss]`, ISO met `T`; tekst met alleen een datum wordt afgewezen), `normalizeRows`, `isSystemEvent`, `exactRowKey`/`deduplicateManualRows`.
   - **Analyse**: `analyze()` bouwt de populaties `allRows → systemRows / manualRows → duplicateRows / auditRows → attention` op, berekent de signalen en roept daarna `peerAnalysis`, `burstAnalysis`, `clientClusterAnalysis`, `concentrationAnalysis`, `reasonUseAnalysis`, `auditLogicAnalysis`, `aggregate*` en `analyzeQuality` aan. Alle bevindingen die in exports terechtkomen, moeten hier ontstaan en **niet in renderfuncties**.
   - **Weergave**: `render()` → `renderOverview`, `renderTables`, `renderDeepDive`, `renderAuditLogic`, `renderTime`, `tableWidget` (zoeken, sorteren en filteren veranderen alleen de weergave) en `openDrilldown` (rijen dragen niet-enumereerbare metadata `__rows`/`previousSourceRow`).
   - **Exports**: `toCsv` (scheidingsteken `;`, BOM, CRLF, beveiliging tegen formule-injectie voor `=`, `+`, `@` en `-…`, maar niet voor een losse `-` of gewone getallen), `exportAttentionCsv`, `exportDrilldownCsv` en `exportReport`. Dat laatste is een zelfstandig HTML-sjabloon als string; `exportReport` is `async` omdat de rapport-CSP het enige script toelaat via `script-src 'sha256-…'` over het `reportTableFilters`-script, zonder `'unsafe-inline'` voor scripts. Tabellen staan daarin als inklapbare `<details>`-secties onder een inhoudsopgave met ankers, en een `beforeprint`-handler klapt alle secties open voor afdrukken. Bestandsnamen komen uit `exportBaseName`. De CSV's en het HTML-rapport bevatten persoonsgegevens; behandel ze net zo zorgvuldig als de bronexport.
   - **Instellingen**: `renderSettings`/`readSettings`. Alleen gehele getallen; uren 0–23, de activatievertraging mag 0 zijn en andere drempels zijn ≥1. Ongeldige invoer wordt afgewezen en niet toegepast.

Escape gegevens altijd met `esc()` voordat je ze in de DOM of het rapport zet.

## Vaste regels

- Reconciliatie: `allRows = systemRows + duplicateRows + auditRows`. De optionele uitsluiting van 30-minutenregels gebeurt in `isSystemEvent`. Uitgesloten regels tellen daardoor als `systemRows` en de gelijkheid klopt altijd. Datakwaliteit gebruikt `manualRows`; Auditlogica gebruikt `allRows`.
- De signaalbetekenis staat in docs §7–§11: het venster voor her-escalaties is inclusief, een gelijke stand wordt beslist op de laagste Excelrij, de activatievertraging moet strikt `>` de drempel zijn, het nachtvenster loopt door over middernacht (begin inclusief, eind exclusief), de prioriteit volgt het thema en ontdubbeling gebeurt op alle 14 getrimde bronvelden (de eerste kopie blijft staan).
- Een regel kan meerdere signalen hebben, maar telt **één keer** als aandachtspunt.
- Formulering: signalen zijn triage-indicatoren en nooit bewijs van onrechtmatige toegang of het inzien van een dossier. Houd die disclaimers in de UI, het rapport en de docs.
- **Docs volgen de code**: volgens de docs wint de implementatie bij een tegenstrijdigheid en moeten de docs worden bijgewerkt. Werk bij elke gedragswijziging de betreffende sectie in `docs/berekeningen-en-patroonherkenning.md` bij, inclusief de `updated:`-datum, en ook `README.md` als de wijziging zichtbaar is voor gebruikers.
- **Versie**: alleen SemVer (in de vorm `0.6.0`). Houd `APP_VERSION` in de HTML, `project.version` in `pyproject.toml` en de badge in `README.md` gelijk en leg elke release vast in `CHANGELOG.md`. Schrijf nooit `v6`, `v6.0` en dergelijke.

## Versiebeleid vóór merge naar main

- Iedere wijziging aan `escalatielog-audit-webui.html` naar `main` bevat in dezelfde PR een hogere SemVer en een nieuwe of bijgewerkte gedateerde changelogsectie voor die versie. Nieuwe functionaliteit verhoogt minor; bugfixes verhogen patch. Beoordeel breaking changes bewust volgens SemVer, met aandacht voor de pre-1.0-status. CI controleert dat de versie stijgt, maar bepaalt niet het wijzigingstype.
- Houd `APP_VERSION`, `project.version`, de README-badge en de projectversie in `uv.lock` gelijk. Bij productwijzigingen naar `main` is *Nog niet uitgebracht* leeg. Op `dev` mogen wijzigingen daar worden verzameld.
- Wijzigingen uitsluitend aan documentatie, tests, scripts of CI vereisen geen productbump. Leg ze wel vast onder *Nog niet uitgebracht* → `### Onderhoud` in `CHANGELOG.md`, zodat ze niet uit beeld raken. De eerstvolgende productwijziging naar `main` verplaatst die regels naar de sectie van de nieuwe versie; de versiecontrole en `check_release_version.py --release` weigeren een release zolang *Nog niet uitgebracht* gevuld is. De single-file HTML is de volledige runtime; ook HTML-opmaakwijzigingen tellen conservatief als productwijziging. Analyse en visuele veranderingen blijven onder de bestaande documentatie- en bewijsregels vallen.
- Controleer de gecommitteerde wijziging lokaal met `uv run python scripts/check_main_version.py --base origin/main --head HEAD` na het ophalen van de actuele doelbranch. De controle vergelijkt Git-commits, niet ongecommitteerde bestanden.
- Een push die `main` aanmaakt of herstelt heeft de null-SHA als basis; de versiecontrole faalt dan bewust met de uitleg dat handmatig met de laatst uitgebrachte versie moet worden vergeleken.
- De bestaande verplichte CI-status **Versiecontrole** controleert de doelbranch-SHA voor PR's naar `main`, de merge queue en pushes op `main`, zonder padfilter. Ontbrekende refs zijn een fout. Publiceren blijft een afzonderlijke handmatige stap via de bestaande releaseworkflow; een merge publiceert geen release automatisch.

## Wijzigingen controleren

Voer `scripts/install-dependencies.sh --check` uit om een nieuwe Linux-omgeving in Codex Cloud voor te bereiden en te controleren. Het script installeert zo nodig de vastgezette uv-versie, synchroniseert het lockbestand en activeert de Git-hooks in `.githooks/` (`git config core.hooksPath .githooks`). Het geeft de voorkeur aan een Chromium uit de distributie, zodat de installatie niet afhangt van de browserdownload van Playwright.

Voer de ontwikkelcontroles uit met `uv sync --locked` en daarna `scripts/run-checks.sh`. Dat is de ene lijst die CI en `--check` delen: versie, privacypaden, productiedocumentatie, mdformat, djLint, Ruff, SVG-tekstgrenzen en pytest. De bestaande coverage met `--cov=tests` volgt Playwright-greenlets en meet de Python-test- en hulpcode onder `tests/`, niet de JavaScript van de app en niet `scripts/`. Deze poort voor Python-testcode moet op 85% of hoger blijven.

`tests/test_app_coverage.py` meet daarnaast via Chromium CDP welk deel van de door V8 gemelde benoemde functies in het inline appscript wordt aangeroepen in één synthetisch referentiescenario (laden, analyse, navigatie, drilldown, CSV- en HTML-export). `tests/conftest.py` toont dit rapport in de pytest-samenvatting, lokaal en in CI, inclusief de namen van functies die niet zijn aangeroepen. Het is alleen een rapportage zonder JavaScript-drempel. Het is geen regel- of branchcoverage en ook geen coverage over de hele testsuite; een aangeroepen functie kan nog ongeteste paden bevatten. De pytest-suite controleert de gecommitte synthetische standaardexport, bouwt een tijdelijk XLSX-bestand voor de opmaak en controleert de geëxporteerde rapporttabellen in een lokaal geïnstalleerde Chrome, Edge of Chromium. De suite mag geen bestanden uit `escalatielogs/` gebruiken.

Voor de volledige analyseregressie draai je het synthetische referentiebestand `tests/fixtures/synthetic-escalatielog.xlsx` opnieuw met de standaardinstellingen en vergelijk je de uitkomst met docs §15. De belangrijkste cijfers:

| Controle | Uitkomst |
| -- | -: |
| Bronregels / systeemregels / duplicaten / auditregels | 2000 / 156 / 42 / 1802 |
| Medewerkers / cliënten / locatiedoelen | 250 / 558 / 40 |
| Niet geactiveerd / nacht / late activatie / ongeldige activatie | 310 / 544 / 1391 / 66 |
| Her-escalaties / zeer snel | 0 / 0 |
| Unieke aandachtspunten | 1790 (99,3 %) |
| Bursts / cliëntclusters | 0 / 5 |

Open voor de handmatige referentiecontrole de HTML in Chromium of Chrome. De app heeft `DecompressionStream` nodig (Edge/Chrome 80+, Firefox 113+, Safari 16.4+). Controleer de console op fouten, controleer de cijfers hierboven en probeer één drilldown, één CSV-export en het HTML-rapport. Veranderen de cijfers bewust, werk dan docs §15 in dezelfde wijziging bij.

Voor synthetische randgevallen roep je `analyze()`/`analyzeQuality()` direct aan in de paginacontext, met zelf opgebouwde rijobjecten.

Bij prestatiewijzigingen voer je `uv run python scripts/measure_render_performance.py [--html PATH] [--runs N]` uit vóór en na de wijziging en zet je beide uitvoeren in de PR. Het script bouwt in de pagina een deterministische synthetische set van 50.000 regels, 3.000 medewerkers en 20.000 cliënten. Het print JSON met de duur per run en de mediaan van `analyze()`, `render()` en elke `render*`-substap. Gebruik minstens 3 runs, meet de baseline op een kopie van de HTML van de basisbranch (`--html`) en laat andere browsers en testruns tijdens het meten stilstaan.

## Taak afronden

Een taak is pas klaar als je al het tijdelijke werk hebt opgeruimd dat je voor die taak hebt aangemaakt. Denk aan bestanden en mappen in `/tmp` of elders buiten de repository, tijdelijke kopieën van de HTML (zoals de baseline voor `measure_render_performance.py`), tijdelijke testbestanden en scripts, testexports in `exports/` en servers of browserprocessen die je hebt gestart. Ruim alleen op wat je zelf hebt aangemaakt; verwijder geen bestaande bestanden van de gebruiker. Lukt opruimen niet, meld dan welke paden of processen zijn achtergebleven.

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

## Schrijfstijl documentatie

Dit geldt voor `README.md`, `CHANGELOG.md` en `docs/berekeningen-en-patroonherkenning.md`.

- Groepeer samenhangende zinnen in een alinea met één herkenbaar onderwerp. Een reeks alinea's van één zin is alleen terecht als iedere zin een eigen onderwerp heeft.
- Beschrijf eerst de hoofdregel, dan de voorwaarden en uitzonderingen en daarna het gevolg. Houd een voorbeeld of referentiegetal bij de regel die het toelicht.
- Schrijf natuurlijk Nederlands en wissel korte en iets langere zinnen af. Vervang losse zinnen niet door lange zinnen die de lezer twee keer moet lezen.
- Gebruik een opsomming voor echte verzamelingen, voorwaarden of stappen, niet als vervanging van lopende uitleg.
- Zet technische implementatiedetails in een eigen alinea als ze de uitleg over het gebruik onderbreken.
- Behoud bij herschrijven definities, identifiers, getallen, grenswaarden, tellers en noemers, uitzonderingen en waarschuwingen. Een kortere tekst is geen reden om nuance te schrappen.

## Afspraken

- Houd de architectuur van één bestand aan. Splits niet op in modules en voeg geen bundler toe.
- Formatteer de HTML-opmaak met `uv run djlint . --reformat`. De geconfigureerde formatter laat de ingesloten CSS en JavaScript compact. Houd daar de functies van één regel, de `const`-maps en het minimale commentaar aan en herformatteer geen regels die niets met de wijziging te maken hebben.
- Commitberichten volgen `type emoji: Nederlandse samenvatting in de gebiedende wijs`, bijvoorbeeld `docs 📝: Voeg uitleg over de analyseketen toe aan de README` of `chore 📦: …`.
- Commit nooit iets uit `escalatielogs/` of `exports/`; beide bevatten echte persoonsgegevens. `scripts/check-sensitive-paths.sh` blokkeert (hoofdletterongevoelig) alles in die mappen behalve `.gitkeep`, elk `*.xlsx`-bestand buiten `tests/fixtures/` en elk bestand waarvan de naam begint met `escalatie_log_controle_`. De pre-commit- en pre-push-hooks in `.githooks/` voeren dezelfde controle uit; `scripts/install-dependencies.sh` activeert ze met `git config core.hooksPath .githooks`.
- Maak geen commits of PR's tenzij daar expliciet om wordt gevraagd.

## Issues en pull requests

- Geef elke issue en pull request de bestaande labels van de repository. Bekijk eerst welke labels er zijn en kies alleen labels die het hoofdtype en relevante overkoepelende aandachtspunten beschrijven. Maak zonder expliciete toestemming geen labels aan die bijna gelijk zijn aan bestaande.
- Elke pull request moet verwijzen naar de issue of issues die hij oplost. Gebruik een GitHub-sluitwoord zoals `Closes #123` alleen als de merge van de PR die issue volledig oplost. Gebruik anders een verwijzing die de issue niet sluit, zoals `Relates to #123`, en vermeld wat er nog openstaat.
- Voeg alleen een screenshot of korte video toe als een issue of pull request over visuele wijzigingen in de webui gaat. Een duidelijk voor-en-napaar heeft de voorkeur. Laat visueel bewijs weg bij alle andere wijzigingen, zoals analyselogica, scripts, CI, tests en documentatie.
- Upload visueel bewijs dat nodig is naar de issue of pull request, zodat reviewers het daar direct kunnen bekijken. Een lokaal bestandspad is niet genoeg.
- Neem bij het omzetten van browserfeedback naar een issue de relevante annotaties en bijbehorende screenshots mee. Koppel elk beeld aan de betreffende bevinding. Voor een issue over de huidige webui volstaan de geannoteerde screenshots van die situatie; een voor-en-napaar hoort bij de implementatie-PR.
- Controleer of originele screenshots daadwerkelijk kunnen worden opgehaald en geüpload; zichtbaarheid in de chat bewijst dat niet. Lukt overnemen niet, vermeld die beperking dan expliciet in de issue en de terugkoppeling. Neem de geselecteerde tekst en voldoende schermcontext op om de plek te herkennen. Benoem een vervangend synthetisch screenshot als reproductie, niet als oorspronkelijke annotatie.
- Lees vóór afronding de aangemaakte issue terug. Controleer of die zonder de chat begrijpelijk is, alle relevante bevindingen bevat en de afbeeldingen voor reviewers laden. Alleen Markdown-links toevoegen is geen bewijs dat screenshots zijn bijgevoegd of gecontroleerd. Meld ontbrekende of niet-verifieerbare afbeeldingen expliciet.
- Screenshots en video's moeten synthetische of andere niet-persoonlijke gegevens gebruiken. Voeg nooit bronbestanden of gegenereerde exports uit `escalatielogs/` of `exports/` toe aan een issue of pull request.
- Open geen pull request zolang de verplichte issueverwijzing of labels ontbreken. Bij visuele webuiwijzigingen is ook het visuele bewijs verplicht. Kun je dat niet maken, stop dan en vraag de gebruiker hoe je verder moet.
