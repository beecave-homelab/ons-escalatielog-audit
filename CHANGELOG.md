# Changelog

Alle noemenswaardige wijzigingen aan dit project worden in dit bestand vastgelegd. Versies volgen [Semantic Versioning](https://semver.org/lang/nl/).

## [Nog niet uitgebracht]

## [0.16.0] - 2026-10-16

### Toegevoegd

- Analyse-instellingen zijn vóór de eerste analyse bereikbaar via Instellingen in het uploadvak, ook zonder bestand. De eerste analyse gebruikt de ingevulde waarden. Bestandsselectie bewaart de invoer en na de analyse blijven dezelfde instellingen bereikbaar (#84).

### Onderhoud

- Werk de GitHub Actions bij naar actions/checkout 7.0.1, actions/setup-python 7.0.0, astral-sh/setup-uv 10.2.0, actions/configure-pages 6.0.0, actions/upload-pages-artifact 5.0.0 en actions/deploy-pages 5.0.1. Deze versies draaien op Node.js 24. De test van de Pages-workflow controleert alleen nog de naam van elke actie en niet de exacte commit. De verplichte pinning op een volledige commit blijft gecontroleerd in `test_workflow_hardening.py`.

## [0.15.4] - 2026-10-15

### Opgelost

- Het HTML-rapport en het overzicht schrijven niet langer wijzigingen uit oudere versies toe aan de huidige versie. De versiegeschiedenis staat alleen nog in de changelog van de release (#52).
- De XLSX-lezer leest werkbladen met een namespaceprefix, cellen en rijen zonder r-attribuut en gedeelde tekst met fonetische hulptekst correct in. Foutcellen zoals #N/A worden als lege waarde ingelezen in plaats van als de tekst NaN. In regels die geen systeemmelding zijn, verschijnen ze onder Datakwaliteit als Foutcel in bron (#53).
- Een lege of niet-numerieke tijdsduur verschijnt in Auditlogica als (leeg of ongeldig) in plaats van null minuten, achteraan de duurverdeling. De drilldowns van Duurverdeling en Systeemmeldingen openen precies de meegetelde bronregels (#54).
- Het signaalfilter bij Aandachtspunten vergelijkt hele signaalnamen, de uitleg bij ZEER_SNELLE_HERESCALATIE volgt de definitie uit de documentatie, hetzelfde bestand kan opnieuw worden gekozen, de leeswijzer in het rapport gebruikt geen Engels leenwoord meer en de drilldown ruimt zijn ResizeObserver op (#62).

### Onderhoud

- Blokkeer privacygevoelige bestanden in de hele Git-boom en niet alleen in `escalatielogs/` en `exports/`: ook `*.xlsx` buiten `tests/fixtures/` en exports die beginnen met `escalatie_log_controle_`. Paden worden hoofdletterongevoelig vergeleken. Het setupscript zet de Git-hooks in `.githooks/` aan.
- Pin alle GitHub Actions op een vaste commit, beperk de rechten van iedere workflow en bewaar geen inloggegevens na de checkout. Dependabot stelt updates van acties voor, met een wachttijd van zeven dagen.
- Gebruik één gedeelde lijst met controles (`scripts/run-checks.sh`) in CI en in `scripts/install-dependencies.sh --check`, en zet de uv-versie vast.
- Laat de SVG-tekstcontrole transforms en een viewBox met verschoven oorsprong meenemen.
- Lees en schrijf bestanden in de release- en versiescripts als UTF-8, weiger `--revision` bij `release_tools.py prepare` en controleer ook links met een titel en referentielinks.
- Leg uit waarom de versiecontrole faalt bij een push zonder vorige commit, en verwijder de versie uit de subkoppen van deze changelog.

## [0.15.3] - 2026-10-14

### Opgelost

- Het dashboard bouwt het bronregelbewijs voor klikbare onderdelen niet meer bij iedere weergave opnieuw op. `analyze()` legt de bronregels per medewerker, team, reden, cliënt, tijdvak, signaal, thema en prioriteit één keer vast; de weergave zoekt ze alleen op. Drilldowns tonen dezelfde bronregels als voorheen, maar grote exports worden merkbaar sneller weergegeven.

## [0.15.2] - 2026-10-14

### Opgelost

- **Analyse opnieuw uitvoeren** werkt de analyse nu in één keer bij. Nieuwe instellingen, het analysetijdstip en het resultaat worden pas vastgelegd als analyse en weergave slagen. Mislukt de heranalyse, dan blijven de vorige cijfers, instellingen en het analysetijdstip actief en toont de statusregel een foutmelding.

- `analyze()` wijzigt de applicatiestatus en de ingelezen bronregels niet meer. Een mislukte heranalyse kan daardoor de signalen van het getoonde resultaat niet aantasten.

- Het HTML-rapport neemt de toegepaste instellingen over uit het analyseresultaat, net als de PNG-export. Instellingen die nog niet met een heranalyse zijn toegepast, komen niet meer in het rapport terecht.

## [0.15.1] - 2026-10-14

### Opgelost

- Koppel het bronregelsbewijs bij Datakwaliteit vast in de analyse in plaats van in de weergave. `analyzeQuality` legt per bevinding de exacte bronregels vast als niet-enumerable `__rows` vanuit dezelfde groep die de telling en toelichting bepaalt. `renderEvidenceLinks` leest deze metadata alleen uit en leidt geen bewijs meer af.

- Een Exact-dubbel-drilldown toont nu uitsluitend de regels met identieke `exactRowKey` (alle 14 bronvelden), niet meer regels die toevallig overeenkomen op medewerkernummer, starttijd, reden en doelnaam. Een bijna-duplicaat dat afwijkt in bijvoorbeeld duur of doel-ID verschijnt niet langer in de drilldown.

- Identifierconflicten houden de sleutelruimte gescheiden: een conflict op medewerkernummer brengt alleen regels met dat nummer mee, een conflict op gebruikersnaam alleen regels met die naam. De eerdere OR-voorwaarde (`employeeNumber===key||loginName===key`) is verwijderd.

- Ontbrekend/ongeldig veld, Redenvariant en Identifierconflict dragen nu ook `__rows` bewijs vanaf de analyse, op dezelfde manier als Tijd/duur al deed.

## [0.15.0] - 2026-10-12

### Toegevoegd

- Zoek en filter per tabel in het zelfstandige HTML-rapport, met compacte kolomkoppen, een regelteller en een wisknop. Schermlezers krijgen tabelcontext bij de teller en een gekoppelde lege-resultaatmelding. Afdrukken toont alle opgenomen regels en herstelt daarna de schermselectie. Zonder JavaScript blijven de tabellen leesbaar.

- Download alle visuals van Overzicht als losse PNG-bestanden in één lokaal gemaakte ZIP, met herkenbare namen, brongegevens en context per afbeelding.

## [0.14.0] - 2026-10-10

### Toegevoegd

- Publiceer de Pages-showcase vanaf main na de volledige CI op dezelfde commit, met uitsluitend de ongewijzigde webui in het publicatieartefact.
- Onderscheid in de README de online showcase met synthetisch voorbeeldbestand en een lokale, hash-gecontroleerde releasekopie voor analyses.

### Onderhoud

- Weiger verouderde Pages-commits bij de start en vlak vóór publicatie; laat deployments op elkaar wachten zonder lopende of wachtende runs te annuleren.
- Leg PyYAML expliciet vast als ontwikkelafhankelijkheid voor de workflowtests.

## [0.13.1] - 2026-10-09

### Onderhoud

- Behoud in de README uitsluitend gebruikersinformatie; releasebeheer hoort bij het beheerproces.

- Herstel het hervatten van conceptreleases: vind bestaande concepten via de releaselijst en ruim lege restanten van mislukte uploads pas na alle conflictcontroles op.

- Controleer alle opmaak-, lint-, versie- en synthetische regressietests in CI; de versiecontrole heeft een expliciete release-modus die ongepubliceerde wijzigingen blokkeert.

- Bereid handmatig een conceptrelease voor met een vaste main-commit, gecontroleerde hervatting en uitsluitend de toegestane downloadbestanden. Publicatie blijft handmatig.

- Voeg een release-downloadlink en uitleg over downloaden en uitpakken toe aan de README.

- Beperk `docs/` op `main` tot de berekeningsdocumentatie en zes gebruikte SVG-diagrammen. Ontwikkelhandleidingen, mock-ups, ontwerpbesluiten en controlebewijs horen op `dev` of lokaal.

- Controleer de volledige productiedocumentatie met een vaste toelatingslijst in pull requests naar `main`, de merge queue en pushes op `main`.

## [0.13.0] - 2026-10-09

### Toegevoegd

- Exporteer alle dashboardvisuals na analyse als één lokale PNG met vaste indeling en dubbele resolutie, inclusief volledige labels, heatmapwaarden, leeswijzers en toegepaste instellingen.
- Vermeld bronbestand, waargenomen datumbereik, analysetijdstip, applicatieversie en de triagewaarschuwing in de afbeelding. De PNG kan persoonsgegevens bevatten; bewaar en deel volgens interne afspraken.
- Meld mislukte of te grote PNG-exports zonder analyse of dashboard te veranderen en bevestig een geslaagde herkansing.
- Gebruik gedeelde analysegegevens voor webui en PNG; wijzigingen in de gerenderde pagina beïnvloeden de exportwaarden niet.

## [0.12.0] - 2026-10-08

### Toegevoegd

- Toon bij Aandachtspunten twee fictieve activatietijdlijnen: exact op de ingestelde grens en één seconde later, met de toestand van het signaal en een aangepaste kop wanneer het signaal uitstaat.
- Toon boven het uurpatroon een gearceerde 24-uursband voor het toegepaste nachtvenster, inclusief lege vensters en uitgeschakelde signalen.
- Neem dezelfde uitleg op binnen Signalen en Tijdpatronen in het HTML-rapport; berekening en uitzonderingen klappen open bij afdrukken.

## [0.11.2] - 2026-10-06

### Opgelost

- Benoem bij een afgekeurde XLSX-export de ontbrekende kolommen, het best passende werkblad en het Excel-rijnummer van de mogelijke kopregel.
- Vermeld het aantal herkende vereiste kolommen in de best passende rij.
- Koppel de release-uitleg in het HTML-rapport aan de juiste versie: uitlijning bij 0.11.1 en importdiagnostiek bij 0.11.2.
- Vermeld het aantal leesbare werkbladen en de controlegrens van tien rijen; leid het aantal vereiste kolommen af van de kolommenlijst.
- Toon de importdiagnose op afzonderlijke regels en laat lange werkbladnamen binnen het invoervak afbreken.

## [0.11.1] - 2026-09-22

### Opgelost

- Lijn toelichtingen, grafieken en tabellen binnen het HTML-rapport gelijk uit en voorkom een dubbele inspringing van de tijdmatrix.
- Geef bij brede rapporttabellen aan dat de overige kolommen horizontaal bereikbaar zijn.

## [0.11.0] - 2026-09-21

### Toegevoegd

- Filter bronregels in het detailvenster op team, deskundigheid, doeltype en auditcontext, samen met het zoekveld en een zichtbare regelteller.

### Gewijzigd

- Verduidelijk dat Bronregels CSV ook bij actieve detailfilters de volledige geopende selectie exporteert.

## [0.10.0] - 2026-09-21

### Toegevoegd

- Toon de prioriteitsroute en de meetellende thema’s bij aandachtspunten; groepeer de drie prioriteitstabellen onder één uitlegblok in het rapport.
- Toon de gekoppelde eerdere activatie en her-escalatie als tijdlijn in het bronregeldetail; geef in het rapport een expliciet fictief voorbeeld met de toegepaste toegangstermijn.
- Leg burst- en cliëntclustervensters uit, met exacte verstreken seconden, drempels en selectiereden; toon het werkelijke venster bij de bronregels.
- Voeg een neutrale ratioschaal en de concrete oorzaak van ontbrekende peer-ratio’s toe.
- Toon top-3-concentratie als balk met exacte teller/noemer, resterende registraties en uitleg bij 100% of een lege noemer.

### Gewijzigd

- Maak nulwaarden in de rapporttijdmatrix expliciet, voeg de thematabel toe en deel de cliëntselectie tussen overzicht en rapport. De cliënttabel volgt dezelfde sortering als de grafiek.
- Behoud de bestaande signalen, reconciliatie en beide CSV-schema’s; de analyseresultaten krijgen aanvullende uitlegvelden en exacte tellers.

## [0.9.0] - 2026-09-20

### Toegevoegd

- Voeg de auditflow als verdelingstabel toe aan het HTML-rapport: bronbestand = systeemmeldingen + duplicaatkopieën + auditpopulatie, met aandachtspunten als selectie binnen de auditpopulatie.
- Toon unieke regels per controlethema als balken in het rapport, met de uitleg dat één regel met meerdere thema's in elk thema meetelt.
- Voeg een tijdpatronen-sectie toe met een weekdag/uur-matrix in twee blokken van twaalf uur, inclusief het aantal auditregels zonder geldige starttijd en de somcontrole tegen de auditpopulatie.
- Plaats de topgrafieken voor medewerkers en cliënten in het rapport bij hun tabellen, met een leeswijzer over de topselectie en de sortering bij gelijke standen.

### Gewijzigd

- Bereken de weekdag/uur-telling en de thematellingen in het analyseresultaat, zodat webui en rapport dezelfde waarden gebruiken in plaats van ze afzonderlijk in de renderlaag te bepalen.
- Verwijder de losse topgrafieken uit de rapportsamenvatting; de grafieken staan voortaan binnen de bijbehorende inklapbare secties.
- Werk de gebruikersuitleg in de README en de functionele documentatie bij.

## [0.8.0] - 2026-09-19

### Toegevoegd

- Leg in de webui en binnen de inklapbare peeranalyse van het HTML-rapport uit hoe de vier ratio's worden berekend en geïnterpreteerd.
- Toon een rekenvoorbeeld en maak zichtbaar wat ratio's van 0,50, 1,00 en 2,00 betekenen.
- Voeg een installatiescript toe voor reproduceerbare Codex Cloud-omgevingen met uv, de vastgezette ontwikkelafhankelijkheden en Chromium.

### Gewijzigd

- Benoem het doorklikvenster van de peeranalyse als bronregels achter de vergelijking, zodat duidelijk is dat het geen nadere ratio-uitleg bevat.
- Presenteer de beperkingen van de peervergelijking nadrukkelijk als context en niet als risico- of werklastcorrectie.
- Laat de Playwright-regressietest naast Chrome en Edge ook een systeembrede of reeds door Playwright geïnstalleerde Chromium gebruiken.

### Opgelost

- Accepteer een gevonden browser pas nadat de executable met `--version` succesvol is uitgevoerd, zodat een Ubuntu snap-placeholder de installatie niet voortijdig stopt.

## [0.7.0] - 2026-09-19

### Toegevoegd

- Voeg aan het HTML-rapport een inhoudsopgave met regeltellingen en directe links naar elke sectie toe.
- Voeg een vaste teruglink naar de inhoudsopgave toe.

### Gewijzigd

- Groepeer de rapporttabellen in inklapbare secties; tabellen met weinig regels staan open en uitgebreide tabellen zijn dichtgeklapt.
- Splits de aandachtspunten in het rapport per controleprioriteit en orden de secties van bevindingen naar referentiemateriaal.
- Open alle rapportsecties automatisch bij afdrukken.

## [0.6.1] - 2026-09-18

### Toegevoegd

- Voeg reproduceerbare ontwikkeltooling toe met uv, mdformat, djLint, Ruff, pytest en pytest-cov.
- Voeg pyproject-regels toe voor consistente HTML-opmaak zonder de ingebedde CSS en JavaScript te herschrijven.
- Voeg een gegevensvrije Playwright-regressietest toe voor de scherm- en printopmaak van rapporttabellen.
- Voeg een reproduceerbare generator en een standaard synthetische testexport met 2.000 regels toe.
- Stel minimaal 85% branch-aware dekking verplicht voor de Python-testcode en meet Playwright-greenlets mee.
- Leg de ontwikkelafhankelijkheden vast in `uv.lock` zonder runtime-afhankelijkheden aan de webui toe te voegen.

### Opgelost

- Voorkom dat brede tabellen het geëxporteerde HTML-rapport buiten de paginabreedte trekken.
- Houd brede tabellen op het scherm binnen een eigen horizontaal schuifgebied.
- Laat rapporttabellen bij afdrukken binnen de beschikbare breedte vallen en lange inhoud veilig afbreken.

## [0.6.0] - 2026-09-18

### Toegevoegd

- Maak KPI's, grafieken, signalen en kwaliteitscontroles aanklikbaar, zodat gebruikers de onderliggende bronregels kunnen bekijken.
- Toon bij her-escalaties ook de eerdere activatie waarop het signaal is gebaseerd.
- Voeg een kwaliteitscontrole toe voor activaties die vóór de geregistreerde starttijd liggen.
- Beschrijf in de webui de gebruikte definities, aannames en beperkingen van de analyses.
- Maak zichtbaar dat peervergelijkingen niet corrigeren voor FTE, diensten, caseload of andere verschillen in werklast.

### Gewijzigd

- Vergelijk medewerkers alleen met andere medewerkers binnen een stabiele team- en functiecontext.
- Sluit de onderzochte medewerker uit van de mediaan waarmee de eigen waarde wordt vergeleken.
- Laat de peer-ratio leeg wanneer geen betrouwbare vergelijkingsgroep kan worden gevormd.
- Selecteer cliëntclusters wanneer de drempel voor medewerkers of teams wordt overschreden en toon vervolgens het sterkste gevonden tijdvenster.
- Baseer de controleprioriteit op afzonderlijke thema's en her-escalaties, met correctie voor signalen die inhoudelijk overlappen.
- Presenteer de controleprioriteit nadrukkelijk als hulpmiddel voor triage en niet als gevalideerde risicoscore.
- Maak duidelijk onderscheid tussen een escalatiepoging, een geactiveerde escalatie en daadwerkelijke dossierinzage.
- Verduidelijk dat dossierinzage alleen kan worden vastgesteld met aanvullende logging.
- Stem de teksten en toelichtingen af op gebruik door FAB, CISO en Privacy Officer.

### Opgelost

- Voorkom dat resultaten van eerdere analyses blijven meetellen wanneer hetzelfde bestand opnieuw wordt geanalyseerd.
- Bereken her-escalaties opnieuw op basis van een eerdere geldige activatie die op het nieuwe startmoment al heeft plaatsgevonden.
- Corrigeer de berekening en presentatie van exacte duplicaten in de donutgrafiek.
- Corrigeer de selectie van cliëntclusters die eerder konden worden gemist wanneer slechts één van de ingestelde drempels werd overschreden.
- Voorkom dat overlappende signalen de controleprioriteit onterecht meerdere keren verhogen.
- Herken tijdsinconsistenties waarbij een activatie vóór de start van de escalatie is geregistreerd.

## [0.5.0] - 2026-09-17

### Toegevoegd

- Voeg peervergelijkingen toe waarmee medewerkers kunnen worden vergeleken met collega's binnen hetzelfde team, dezelfde deskundigheid en dezelfde team-deskundigheidscombinatie.
- Voeg burst-detectie toe om veel handmatige escalaties van één medewerker binnen een kort tijdvenster zichtbaar te maken.
- Voeg cliëntclusters toe om cliënten te herkennen die binnen een kort tijdvenster door meerdere medewerkers of teams worden benaderd.
- Voeg een concentratieanalyse toe om onderscheid te maken tussen escalaties naar een kleine vaste groep doelen en een brede spreiding over veel doelen.
- Voeg analyses toe voor afwijkend gebruik van escalatieredenen per medewerker en team.
- Voeg aparte analyses toe voor deskundigheden en locaties.
- Voeg een overzicht `Auditlogica` toe voor controle van duurverdelingen, systeemfilters, doeltypen en bronwaarden.
- Toon expliciet de aanbevolen vervolgroute voor audits: eerst planning en rooster, daarna dossierlogging en vervolgens teamcontext of toelichting.

### Gewijzigd

- Gebruik de escalatielog nadrukkelijk als selectielaag voor nader onderzoek en niet als zelfstandig bewijs van onrechtmatige dossierinzage.
- Breid de analyse uit van losse tellingen naar verbanden tussen medewerker, cliënt, team, deskundigheid, reden en tijd.
- Houd analyses die meerdere maanden historie of aanvullende organisatiedata vereisen buiten de automatische signalering.
- Laat exacte dubbele logregels wel terugkomen als datakwaliteitsbevinding, maar tel alleen de eerste registratie mee in de inhoudelijke analyses.

## [0.4.0] - 2026-09-17

### Toegevoegd

- Maak analyse-uitkomsten doorklikbaar naar de onderliggende regels uit het oorspronkelijke Excel-bestand.
- Toon in de detailweergave het oorspronkelijke Excel-rijnummer en alle 14 bronvelden.
- Toon per bronregel de bijbehorende auditcontext en auditsignalen.
- Voeg de mogelijkheid toe om de bronregels van een geselecteerde analyse afzonderlijk als CSV te downloaden.
- Voeg bronregel-drilldown toe voor medewerkers, cliënten, teams, escalatieredenen, aandachtspunten en systeemmeldingen.

### Gewijzigd

- Maak duidelijk zichtbaar welke bronregels bijdragen aan een geaggregeerde analyse-uitkomst.
- Behoud systeemmeldingen in een aparte drilldown zonder ze mee te nemen in de inhoudelijke auditpopulatie.

## [0.3.0] - 2026-09-17

### Toegevoegd

- Voeg een visuele auditcockpit toe met kern-KPI's, auditflow en controlefocus.
- Visualiseer de verhouding tussen bronbestand, systeemmeldingen, auditpopulatie en aandachtspunten.
- Groepeer auditsignalen visueel naar toegang en activatie, volume en spreiding, tijdpatronen en datakwaliteit.
- Voeg een heatmap toe voor escalaties per weekdag en uur.
- Voeg een medewerkerdiagram toe waarin escalatievolume wordt afgezet tegen het aantal unieke cliënten.
- Voeg een overzicht toe van cliënten die via relatief veel verschillende medewerkers worden benaderd.
- Voeg visuele topoverzichten toe voor medewerkers, teams en escalatieredenen.
- Voeg controleprioriteiten `Hoog`, `Midden` en `Basis` toe voor het ordenen van aandachtspunten.
- Breid het geëxporteerde HTML-rapport uit met KPI's, controleprioriteiten en visuele overzichten.

### Gewijzigd

- Presenteer auditsignalen als hulpmiddel voor snelle triage zonder detailgegevens uit de controletabellen te verwijderen.
- Maak expliciet dat controleprioriteit alleen de werkvolgorde ondersteunt en geen oordeel over rechtmatigheid vormt.

## [0.2.0] - 2026-09-16

### Toegevoegd

- Neem de uitvoerdatum en het uitvoertijdstip automatisch op in de namen van geëxporteerde bestanden.
- Leid de analyseperiode automatisch af uit de ingelezen escalatielog.
- Neem de analyseperiode ook op in de naam van CSV- en HTML-exports.
- Toon de gebruikte analyseperiode in het geëxporteerde HTML-rapport.

### Gewijzigd

- Gebruik herleidbare bestandsnamen voor interne verspreiding van auditresultaten.
- Geef CSV- en HTML-exports een herkenbaar onderscheid in de bestandsnaam.

## [0.1.0] - 2026-09-16

### Toegevoegd

- Introduceer een zelfstandige webui voor het lokaal analyseren van escalatielogs uit `.xlsx`-bestanden.
- Verwerk het Excel-bestand volledig lokaal in de browser zonder backend, externe API of opslag in browseropslag.
- Valideer bij het inlezen of alle 14 verwachte kolommen aanwezig zijn.
- Scheid systeemmeldingen vooraf van de handmatige auditpopulatie.
- Herken systeemmeldingen aan bekende systeemredenen en de 30-minutenregistraties uit de onderzochte export.
- Voeg analyses toe per medewerker, cliënt, team, escalatiereden en tijdstip.
- Voeg datakwaliteitscontroles toe voor ontbrekende velden, identifierconflicten, schrijfvarianten en exacte dubbele regels.
- Voeg instelbare auditsignalen toe voor nachtelijke escalaties, niet-geactiveerde escalaties, hoog dagvolume, cliëntspreiding, activatievertraging en zeldzame redenen.
- Voeg `HERESCALATIE_TIJDENS_ACTIEVE_TOEGANG` toe voor een nieuwe handmatige escalatie naar dezelfde cliënt terwijl eerdere succesvolle toegang nog geldig is.
- Voeg `ZEER_SNELLE_HERESCALATIE` toe als aanvullend signaal voor her-escalaties binnen een kort tijdvenster.
- Maak de geldigheidsduur van een succesvolle escalatie instelbaar, standaard op 840 minuten of 14 uur.
- Voeg een apart overzicht toe voor uitgesloten systeemmeldingen.
- Voeg zoeken, filteren en sorteren toe aan de analyseresultaten.
- Voeg export van aandachtspunten naar CSV toe.
- Voeg export van een zelfstandig HTML-auditrapport toe.

### Gewijzigd

- Gebruik alleen handmatige escalaties voor inhoudelijke auditcontroles en aggregaties.
- Presenteer auditsignalen als selectiecriteria voor menselijke beoordeling en niet als vaststelling van onrechtmatige inzage.
