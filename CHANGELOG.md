# Changelog

Alle noemenswaardige wijzigingen aan dit project worden in dit bestand vastgelegd. Versies volgen [Semantic Versioning](https://semver.org/lang/nl/).

## [0.8.0] - 2026-09-19

### Toegevoegd in v0.8.0

- Leg in de webui en binnen de inklapbare peeranalyse van het HTML-rapport uit hoe de vier ratio's worden berekend en geïnterpreteerd.
- Toon een rekenvoorbeeld en maak zichtbaar wat ratio's van 0,50, 1,00 en 2,00 betekenen.
- Voeg een installatiescript toe voor reproduceerbare Codex Cloud-omgevingen met uv, de vastgezette ontwikkelafhankelijkheden en Chromium.

### Gewijzigd in v0.8.0

- Benoem het doorklikvenster van de peeranalyse als bronregels achter de vergelijking, zodat duidelijk is dat het geen nadere ratio-uitleg bevat.
- Presenteer de beperkingen van de peervergelijking nadrukkelijk als context en niet als risico- of werklastcorrectie.
- Laat de Playwright-regressietest naast Chrome en Edge ook een systeembrede of reeds door Playwright geïnstalleerde Chromium gebruiken.

## [0.7.0] - 2026-09-19

### Toegevoegd in v0.7.0

- Voeg aan het HTML-rapport een inhoudsopgave met regeltellingen en directe links naar elke sectie toe.
- Voeg een vaste teruglink naar de inhoudsopgave toe.

### Gewijzigd in v0.7.0

- Groepeer de rapporttabellen in inklapbare secties; tabellen met weinig regels staan open en uitgebreide tabellen zijn dichtgeklapt.
- Splits de aandachtspunten in het rapport per controleprioriteit en orden de secties van bevindingen naar referentiemateriaal.
- Open alle rapportsecties automatisch bij afdrukken.

## [0.6.1] - 2026-09-18

### Toegevoegd in v0.6.1

- Voeg reproduceerbare ontwikkeltooling toe met uv, mdformat, djLint, Ruff, pytest en pytest-cov.
- Voeg pyproject-regels toe voor consistente HTML-opmaak zonder de ingebedde CSS en JavaScript te herschrijven.
- Voeg een gegevensvrije Playwright-regressietest toe voor de scherm- en printopmaak van rapporttabellen.
- Voeg een reproduceerbare generator en een standaard synthetische testexport met 2.000 regels toe.
- Stel minimaal 85% branch-aware dekking verplicht voor de Python-testcode en meet Playwright-greenlets mee.
- Leg de ontwikkelafhankelijkheden vast in `uv.lock` zonder runtime-afhankelijkheden aan de webui toe te voegen.

### Opgelost in v0.6.1

- Voorkom dat brede tabellen het geëxporteerde HTML-rapport buiten de paginabreedte trekken.
- Houd brede tabellen op het scherm binnen een eigen horizontaal schuifgebied.
- Laat rapporttabellen bij afdrukken binnen de beschikbare breedte vallen en lange inhoud veilig afbreken.

## [0.6.0] - 2026-09-18

### Toegevoegd in v0.6.0

- Maak KPI's, grafieken, signalen en kwaliteitscontroles aanklikbaar, zodat gebruikers de onderliggende bronregels kunnen bekijken.
- Toon bij her-escalaties ook de eerdere activatie waarop het signaal is gebaseerd.
- Voeg een kwaliteitscontrole toe voor activaties die vóór de geregistreerde starttijd liggen.
- Beschrijf in de webui de gebruikte definities, aannames en beperkingen van de analyses.
- Maak zichtbaar dat peervergelijkingen niet corrigeren voor FTE, diensten, caseload of andere verschillen in werklast.

### Gewijzigd in v0.6.0

- Vergelijk medewerkers alleen met andere medewerkers binnen een stabiele team- en functiecontext.
- Sluit de onderzochte medewerker uit van de mediaan waarmee de eigen waarde wordt vergeleken.
- Laat de peer-ratio leeg wanneer geen betrouwbare vergelijkingsgroep kan worden gevormd.
- Selecteer cliëntclusters wanneer de drempel voor medewerkers of teams wordt overschreden en toon vervolgens het sterkste gevonden tijdvenster.
- Baseer de controleprioriteit op afzonderlijke thema's en her-escalaties, met correctie voor signalen die inhoudelijk overlappen.
- Presenteer de controleprioriteit nadrukkelijk als hulpmiddel voor triage en niet als gevalideerde risicoscore.
- Maak duidelijk onderscheid tussen een escalatiepoging, een geactiveerde escalatie en daadwerkelijke dossierinzage.
- Verduidelijk dat dossierinzage alleen kan worden vastgesteld met aanvullende logging.
- Stem de teksten en toelichtingen af op gebruik door FAB, CISO en Privacy Officer.

### Opgelost in v0.6.0

- Voorkom dat resultaten van eerdere analyses blijven meetellen wanneer hetzelfde bestand opnieuw wordt geanalyseerd.
- Bereken her-escalaties opnieuw op basis van een eerdere geldige activatie die op het nieuwe startmoment al heeft plaatsgevonden.
- Corrigeer de berekening en presentatie van exacte duplicaten in de donutgrafiek.
- Corrigeer de selectie van cliëntclusters die eerder konden worden gemist wanneer slechts één van de ingestelde drempels werd overschreden.
- Voorkom dat overlappende signalen de controleprioriteit onterecht meerdere keren verhogen.
- Herken tijdsinconsistenties waarbij een activatie vóór de start van de escalatie is geregistreerd.

## [0.5.0] - 2026-09-17

### Toegevoegd in v0.5.0

- Voeg peervergelijkingen toe waarmee medewerkers kunnen worden vergeleken met collega's binnen hetzelfde team, dezelfde deskundigheid en dezelfde team-deskundigheidscombinatie.
- Voeg burst-detectie toe om veel handmatige escalaties van één medewerker binnen een kort tijdvenster zichtbaar te maken.
- Voeg cliëntclusters toe om cliënten te herkennen die binnen een kort tijdvenster door meerdere medewerkers of teams worden benaderd.
- Voeg een concentratieanalyse toe om onderscheid te maken tussen escalaties naar een kleine vaste groep doelen en een brede spreiding over veel doelen.
- Voeg analyses toe voor afwijkend gebruik van escalatieredenen per medewerker en team.
- Voeg aparte analyses toe voor deskundigheden en locaties.
- Voeg een overzicht `Auditlogica` toe voor controle van duurverdelingen, systeemfilters, doeltypen en bronwaarden.
- Toon expliciet de aanbevolen vervolgroute voor audits: eerst planning en rooster, daarna dossierlogging en vervolgens teamcontext of toelichting.

### Gewijzigd in v0.5.0

- Gebruik de escalatielog nadrukkelijk als selectielaag voor nader onderzoek en niet als zelfstandig bewijs van onrechtmatige dossierinzage.
- Breid de analyse uit van losse tellingen naar verbanden tussen medewerker, cliënt, team, deskundigheid, reden en tijd.
- Houd analyses die meerdere maanden historie of aanvullende organisatiedata vereisen buiten de automatische signalering.
- Laat exacte dubbele logregels wel terugkomen als datakwaliteitsbevinding, maar tel alleen de eerste registratie mee in de inhoudelijke analyses.

## [0.4.0] - 2026-09-17

### Toegevoegd in v0.4.0

- Maak analyse-uitkomsten doorklikbaar naar de onderliggende regels uit het oorspronkelijke Excel-bestand.
- Toon in de detailweergave het oorspronkelijke Excel-rijnummer en alle 14 bronvelden.
- Toon per bronregel de bijbehorende auditcontext en auditsignalen.
- Voeg de mogelijkheid toe om de bronregels van een geselecteerde analyse afzonderlijk als CSV te downloaden.
- Voeg bronregel-drilldown toe voor medewerkers, cliënten, teams, escalatieredenen, aandachtspunten en systeemmeldingen.

### Gewijzigd in v0.4.0

- Maak duidelijk zichtbaar welke bronregels bijdragen aan een geaggregeerde analyse-uitkomst.
- Behoud systeemmeldingen in een aparte drilldown zonder ze mee te nemen in de inhoudelijke auditpopulatie.

## [0.3.0] - 2026-09-17

### Toegevoegd in v0.3.0

- Voeg een visuele auditcockpit toe met kern-KPI's, auditflow en controlefocus.
- Visualiseer de verhouding tussen bronbestand, systeemmeldingen, auditpopulatie en aandachtspunten.
- Groepeer auditsignalen visueel naar toegang en activatie, volume en spreiding, tijdpatronen en datakwaliteit.
- Voeg een heatmap toe voor escalaties per weekdag en uur.
- Voeg een medewerkerdiagram toe waarin escalatievolume wordt afgezet tegen het aantal unieke cliënten.
- Voeg een overzicht toe van cliënten die via relatief veel verschillende medewerkers worden benaderd.
- Voeg visuele topoverzichten toe voor medewerkers, teams en escalatieredenen.
- Voeg controleprioriteiten `Hoog`, `Midden` en `Basis` toe voor het ordenen van aandachtspunten.
- Breid het geëxporteerde HTML-rapport uit met KPI's, controleprioriteiten en visuele overzichten.

### Gewijzigd in v0.3.0

- Presenteer auditsignalen als hulpmiddel voor snelle triage zonder detailgegevens uit de controletabellen te verwijderen.
- Maak expliciet dat controleprioriteit alleen de werkvolgorde ondersteunt en geen oordeel over rechtmatigheid vormt.

## [0.2.0] - 2026-09-16

### Toegevoegd in v0.2.0

- Neem de uitvoerdatum en het uitvoertijdstip automatisch op in de namen van geëxporteerde bestanden.
- Leid de analyseperiode automatisch af uit de ingelezen escalatielog.
- Neem de analyseperiode ook op in de naam van CSV- en HTML-exports.
- Toon de gebruikte analyseperiode in het geëxporteerde HTML-rapport.

### Gewijzigd in v0.2.0

- Gebruik herleidbare bestandsnamen voor interne verspreiding van auditresultaten.
- Geef CSV- en HTML-exports een herkenbaar onderscheid in de bestandsnaam.

## [0.1.0] - 2026-09-16

### Toegevoegd in v0.1.0

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

### Gewijzigd in v0.1.0

- Gebruik alleen handmatige escalaties voor inhoudelijke auditcontroles en aggregaties.
- Presenteer auditsignalen als selectiecriteria voor menselijke beoordeling en niet als vaststelling van onrechtmatige inzage.
