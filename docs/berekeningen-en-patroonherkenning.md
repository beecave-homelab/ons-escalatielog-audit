---
title: Berekeningen, tellingen en patroonherkenning
applies_to: escalatielog-audit-webui.html
tags: [escalatielogs, audit, functioneel-beheer]
updated: 2026-09-17
---

## Berekeningen, tellingen en patroonherkenning

Dit document is de technische en functionele referentie voor de berekeningen in `escalatielog-audit-webui.html`. Het beschrijft per analyse welke regels worden meegenomen, hoe sleutels en unieke waarden worden bepaald, welke teller en noemer worden gebruikt en hoe grenswaarden, tijdvensters en gelijkstanden worden afgehandeld.

De HTML-code is de enige gedragsbron voor deze repository. Als dit document en de implementatie van elkaar afwijken, is de implementatie leidend en moet dit document worden bijgewerkt.

Een escalatieregel registreert een poging of gebeurtenis rond uitzonderlijke toegang. Ook een geregistreerde activatie bewijst niet dat daarna dossiergegevens zijn ingezien. Een auditsignaal selecteert een regel voor verificatie; het stelt geen onrechtmatige toegang vast.

## 1. Reikwijdte

De webui verwerkt per analyse één Excelbestand en gebruikt het eerste werkblad waarvan een van de eerste tien rijen alle vereiste kolomkoppen bevat. Werkbladen worden niet samengevoegd. Berekeningen gebruiken de ingelezen export en de instellingen die bij de laatste analyse zijn toegepast.

Zoeken, sorteren en filteren in een tabel verandert uitsluitend de zichtbare tabelweergave. Het wijzigt de analysepopulatie, aggregaties, grafieken en exports niet.

Deze referentie beschrijft het geïmplementeerde gedrag. Zij bevestigt geen leveranciersspecificaties, wettelijke verplichtingen of volledige naleving van normen. Controleer de inrichting en beschikbare logging van Nedap Ons voordat uitkomsten inhoudelijk worden beoordeeld.

## 2. Technische uitgangspunten

De populatie waarop een getal is gebaseerd, is onderdeel van de definitie:

- **Inhoudelijke analyses:** gebruiken `auditRows`, dus niet-systeemregels na exacte ontdubbeling.
- **Datakwaliteit:** gebruikt `manualRows`, dus niet-systeemregels vóór ontdubbeling. Daardoor blijven duplicaten als kwaliteitsbevinding zichtbaar.
- **Auditlogica:** gebruikt `allRows`, dus alle geïmporteerde niet-lege bronregels, inclusief later uitgesloten systeemregels en duplicaten.
- **Ontbrekende sleutels:** verwijderen een regel niet automatisch uit `auditRows`. De regel kan wel ontbreken in een aggregatie waarvoor die sleutel vereist is.
- **Signaalfrequenties:** tellen regels per signaal en mogen overlappen. Eén regel met drie signalen draagt aan drie signaalfrequenties bij.
- **Aandachtspunten:** tellen unieke auditregels met ten minste één ingeschakeld signaal. Dezelfde regel telt hier altijd eenmaal.

Tabellen met medewerkers, cliënten, locaties, teams, deskundigheden en redenen tonen aggregaties. Een klik op zo'n aggregatieregel opent alle auditregels die aan de groep bijdragen, niet uitsluitend de regels achter één gekozen kolomwaarde.

## 3. Invoervelden en hun gebruik

De webui verwacht de onderstaande 14 kolomnamen. Zij zoekt naar een passend werkblad met deze kopregel in de eerste tien rijen en gebruikt het eerste gevonden passende werkblad. Meerdere werkbladen worden niet samengevoegd.

| Kolom | Gebruik | Beperking |
| -- | -- | -- |
| `Gebruiker` | Weergavenaam en laatste terugval voor medewerkeridentificatie | Namen kunnen wijzigen of bij meerdere personen voorkomen |
| `Medewerkernummer` | Eerste keuze voor de medewerkersleutel | Niet zelf corrigeren of samenvoegen zonder verificatie |
| `Medewerkersteam` | Teamtelling en context voor peers | Is de geregistreerde teamwaarde; bewijst geen behandelrelatie |
| `Deskundigheid medewerker` | Functiegroepen en peercontext | Geen maat voor inzet, bevoegdheid of caseload |
| `Gebruikersnaam` | Tweede keuze voor medewerkeridentificatie en conflictcontrole | Eén account kan in de export aan meerdere nummers zijn gekoppeld |
| `Escalatie reden` | Systeemfilter, redenverdeling en signalen | Opgegeven tekst verklaart niet zelfstandig de noodzaak |
| `Tijdsduur (min.)` | Duurverdeling, datakwaliteit en optioneel duurfilter | Wordt niet gebruikt als toegangstermijn voor her-escalaties |
| `Escalatiedoel type` | Onderscheid tussen cliënt- en locatiedoelen | Onbekende typen vragen controle |
| `Escalatiedoel naam` | Leesbare weergave en volledigheidscontrole | Wordt niet gebruikt als cliënt- of locatiesleutel |
| `Escalatiedoel identificatienummer` | Sleutel voor cliënt- of locatieanalyse | Ontbrekend ID verhindert analyse van dat specifieke doel |
| `Hoofdlocatie cliënt` | Aanvullende context bij cliënten | Geen bewijs van de locatie tijdens de escalatie of van teamtoegang |
| `Gestart op` | Kalenderdag, uur, volgorde, bursts en her-escalaties | Tijdzone en volledigheid van de export zijn niet vastgelegd in deze velden |
| `Geactiveerd op` | Activatievertraging en eerdere activatie als her-escalatiecontext | `Niet geactiveerd`, ontbrekend en ongeldig zijn verschillende toestanden |
| `Bron` | Technische controle en bronregeldetail | In het testbestand uitsluitend `-`; geen onderscheidende analysedimensie |

### 3.1 Sleutels en normalisatie

De medewerkersleutel is de eerste beschikbare waarde uit `Medewerkernummer`, `Gebruikersnaam` en `Gebruiker`. Een lege waarde of `-` geldt hierbij als ontbrekend. Als alle drie ontbreken, blijft de regel in de auditpopulatie maar ontbreekt hij in het medewerkersoverzicht. Naamgebaseerde koppeling is minder betrouwbaar; identifierconflicten worden gemeld, niet automatisch opgelost.

Cliënten worden gegroepeerd op doel-ID, uitsluitend bij doeltype `Cliënt`. Locaties worden gegroepeerd op doel-ID bij doeltype `Locatie`. In analyses met gemengde doelen is de sleutel de combinatie van doeltype en doel-ID. Een cliënt en locatie met hetzelfde nummer zijn daardoor verschillende doelen.

Tekstwaarden worden aan begin en einde ontdaan van witruimte. Escalatieredenen worden voor groepering en systeemherkenning bovendien in kleine letters omgezet en krijgen enkele spaties. Dit voegt geen synoniemen of inhoudelijk vergelijkbare redenen samen. Team- en deskundigheidswaarden worden niet met dezelfde redennormalisatie samengevoegd; schrijfvarianten kunnen daar afzonderlijke groepen blijven.

De webui gebruikt bij samenvattingen vaak de meest voorkomende naam, teamwaarde of deskundigheid. Dit is een weergavekeuze, geen vaststelling van de actuele organisatorische indeling. Bij bursts en concentratie worden team en deskundigheid uit een eerste bijbehorende regel getoond. Controleer bij wisselende context de bronregels.

### 3.2 Ontbrekende cliëntgegevens

Een cliëntgerichte regel zonder doel-ID telt wel mee in de auditpopulatie en, waar mogelijk, in medewerker-, team-, reden- en tijdanalyses. Deze regel telt niet mee bij unieke cliënten, cliëntspecifieke signalen, cliëntclusters of her-escalaties voor dezelfde cliënt. Een ontbrekende cliëntnaam met een aanwezig ID verhindert groepering niet, maar geeft wel een volledigheidssignaal.

Het testbestand bevat 946 cliëntgerichte auditregels: 832 met herkenbaar cliënt-ID en 114 zonder cliënt-ID en cliëntnaam. Alle 114 niet-geactiveerde regels behoren tot die laatste groep. Dat verband is een bevinding uit dit bestand en geen algemene regel voor toekomstige exports.

## 4. Van bronbestand naar auditpopulatie

| Verzameling | Definitie |
| -- | -- |
| `allRows` | Niet-lege gegevensrijen onder de gevonden kopregel |
| `systemRows` | Regels die voldoen aan het toegepaste systeemfilter |
| `manualRows` | Alle overige regels, nog vóór ontdubbeling |
| `duplicateRows` | Extra exemplaren van gelijke regels binnen `manualRows` |
| `auditRows` | `manualRows` na ontdubbeling; basis voor inhoudelijke analyses |
| `attention` | Auditregels met minimaal één ingeschakeld signaal |

De naam `manualRows` betekent hier dat het systeemfilter de regel niet heeft herkend. Een onbekende nieuwe systeemreden kan dus voorlopig in deze verzameling terechtkomen.

De aantallen moeten aansluiten volgens:

```text
bronregels = systeemregels + duplicaatkopieën + auditregels
auditregels = regels met minimaal één signaal + regels zonder ingeschakeld signaal
```

Volledig lege rijen worden overgeslagen. De webui verwijdert geen willekeurige niet-lege instructie- of totaalrijen: gebruik een export met echte logregels onder de kolomkoppen.

### 4.1 Systeemfilter

Een regel wordt uitgesloten wanneer de genormaliseerde reden exact overeenkomt met een van deze teksten:

```text
Cliënt gekoppeld aan item in Ons Ketenverkeer
Systeemescalatie: sta 30 minuten toegang toe tot cliënt na aanmaken.
Toegang tot cliënt nadat deze is aangemaakt door Ons Ketenverkeer
```

Deze herkenning geldt ongeacht de duur. Daarnaast kan `excludeDuration30` alle regels met een numerieke duur van 30 minuten uitsluiten. Deze optie staat standaard **uit**. Een onbekende reden met 30 minuten blijft dus standaard in de auditpopulatie en verschijnt als controlepunt in **Auditlogica**.

Controleer na export- of applicatiewijzigingen de reden- en duurverdeling. Het testbestand bevat 237 herkende systeemregels: respectievelijk 125, 107 en 5 voor de drie bovenstaande redenen. Omdat die regels allemaal 30 minuten hebben, geeft het aan- of uitzetten van het aanvullende duurfilter voor dit bestand dezelfde selectie.

### 4.2 Duplicaten

Binnen de niet-uitgesloten regels vergelijkt de webui alle 14 bronvelden na inlezen en verwijderen van witruimte aan begin en einde. Bij gelijke waarden blijft het eerste exemplaar in de auditpopulatie; volgende exemplaren worden uitgesloten en krijgen een verwijzing naar de oorspronkelijke Excel-rij.

Dit is gelijkheid van ingelezen veldwaarden, geen vergelijking van bestandsbytes. Er is geen uniek gebeurtenis-ID waarmee twee verder identieke gebeurtenissen alsnog kunnen worden onderscheiden. De ontdubbeling is daarmee een expliciete analysekeuze die bij een afwijkende exportdefinitie opnieuw moet worden beoordeeld.

Systeemregels worden al vóór deze stap apart gezet en niet ontdubbeld. Het aantal systeemregels betreft dus het aantal uitgesloten bronregels. Bij datakwaliteit kan een duplicaatgroep drie exemplaren tellen terwijl **Duplicaten** in de auditflow twee uitgesloten kopieën telt.

### 4.3 Datakwaliteit heeft een andere basis

De inhoudelijke tellingen gebruiken `auditRows`. **Datakwaliteit** onderzoekt de niet-uitgesloten regels vóór ontdubbeling, zodat duplicaten zichtbaar blijven. **Auditlogica** controleert alle bronregels op duur, reden, doeltype en bronwaarde. Aantallen uit deze tabbladen zijn daarom niet zonder meer onderling vergelijkbaar of optelbaar.

## 5. Kerncijfers, tellers en noemers

| Maat | Berekening | Interpretatie |
| -- | -- | -- |
| Auditpopulatie | Aantal `auditRows` | Resterende unieke logregels, inclusief niet-geactiveerde pogingen |
| Auditpopulatie als percentage | `100 × auditregels / bronregels` | Houdt rekening met systeemregels én duplicaatkopieën |
| Aandachtspunten | Unieke auditregels met minimaal één ingeschakeld signaal | Eén regel telt eenmaal, ook bij meerdere signalen |
| Aandachtspunten als percentage | `100 × aandachtspunten / auditregels` | Omvang van de controleselectie, geen percentage overtredingen |
| Medewerkers | Verschillende beschikbare medewerkersleutels in de auditpopulatie | Geen personeelsbestand en geen volledige teambezetting |
| Cliënten | Verschillende herkenbare doel-ID's bij cliëntgerichte auditregels | Pogingen zonder cliënt-ID tellen niet mee |
| Niet geactiveerd | Regels met de tekst `Niet geactiveerd` in het activatieveld | Ontbrekende of ongeldige activatietekst telt hier niet automatisch mee |
| Niet geactiveerd als percentage | `100 × expliciet niet-geactiveerde auditregels / auditregels` | Het totaal omvat cliënt- en locatieregels |
| Signaalfrequentie | Aantal auditregels waarop één specifiek signaal staat | Frequenties van verschillende signalen kunnen overlappen |
| Regels per controlethema | Unieke auditregels met minimaal één signaal binnen dat thema | Binnen een thema eenmaal tellen; tussen thema's is overlap mogelijk |

De totalen voor her-escalaties en zeer snelle her-escalaties worden uit de berekende intervallen afgeleid. De bijbehorende signaalschakelaars bepalen of deze ook tot **Aandachtspunten** leiden. Uitschakelen van een signaal wist dus niet noodzakelijk het beschrijvende aantal uit een overzicht.

Percentages worden doorgaans op één decimaal weergegeven, peer-ratio's op twee decimalen. Bij een lege populatie tonen algemene percentagefuncties `0%`; lees dat als een lege basis, niet als bewijs dat een verschijnsel afwezig was. Een peer-ratio met onvoldoende vergelijkingsbasis of een mediaan van nul blijft leeg.

## 6. Basisanalyses en vergelijkbaarheid

### 6.1 Medewerkers

Per medewerkersleutel telt de webui auditregels, unieke herkenbare cliënten en locaties, redenen, actieve dagen en het hoogste dagvolume. Daarnaast toont zij niet-geactiveerde pogingen, nacht- en weekendregels, berekende her-escalaties, regels met signalen en het eerste en laatste geldige starttijdstip.

Een actieve dag is een kalenderdag met minimaal één auditregel met geldige startdatum. Het is geen gewerkte dag of dienst. Een medewerker kan in deze tabel over meerdere teams of deskundigheden zijn samengevat; de peeranalyse stelt daarom aanvullende voorwaarden.

### 6.2 Cliënten en locaties

Deze tabellen groeperen auditregels op het bijbehorende doeltype en doel-ID. Zij tonen volume en spreiding over medewerkers, teams, deskundigheden en redenen. Niet-geactiveerde pogingen met een herkenbaar doel tellen mee.

Het aantal verschillende medewerkers rond een cliënt is het aantal geregistreerde medewerkers met een escalatiepoging. Het is geen telling van medewerkers die aantoonbaar het dossier hebben ingezien. De kolom `Hoofdlocatie` bij een cliënt is context; het tabblad **Locaties** gaat over escalaties met doeltype `Locatie`.

### 6.3 Teams en deskundigheden

De toewijzing gebeurt per bronregel. Een medewerker die in verschillende teams voorkomt, kan daardoor in meerdere teamgroepen meetellen. Unieke aantallen uit verschillende groepen mogen niet worden opgeteld om een organisatietotaal te berekenen.

```text
escalaties per waargenomen medewerker =
  aantal auditregels van de groep / aantal herkenbare medewerkers in die groep
```

De noemer bevat uitsluitend medewerkers die in de auditpopulatie voorkomen. Medewerkers zonder escalaties, FTE, gewerkte uren, diensten en caseload ontbreken. De maat corrigeert dus niet voor de volledige teamomvang of werklast. Bij ontbrekende medewerkersleutels kan de teller regels bevatten waarvan de medewerker niet in de noemer zit. De implementatie gebruikt technisch minimaal 1 als deler; bij nul herkenbare medewerkers is de getoonde uitkomst niet inhoudelijk bruikbaar als gemiddelde.

Het nachtpercentage bij deskundigheden is het aantal nachtregels gedeeld door alle auditregels van die deskundigheid. Regels met een ongeldige startdatum blijven in de noemer maar kunnen niet als nacht worden herkend. Controleer daarom de datakwaliteit voordat percentages tussen groepen worden vergeleken.

### 6.4 Redenen

Redenen worden gegroepeerd na normalisatie. De tabel toont aantallen, schrijfvarianten, betrokken medewerkers, cliënten en teams, niet-geactiveerde pogingen en regels met signalen. De meest voorkomende duur is een beschrijvende waarde; er wordt geen geldigheidsduur van toegang uit afgeleid.

Ontbrekende waarden kunnen als lege categorie verschijnen. Tellingen van unieke redenen in de verschillende samenvattingen behandelen ontbrekende waarden niet overal hetzelfde. Gebruik het tabblad **Redenen** en de bronregels voor een vergelijking waarbij ontbrekende redenen relevant zijn.

### 6.5 Tijdpatronen

De webui telt geldige starttijdstippen per datum, uur en weekdag. De heatmap combineert weekdag en uur. Ongeldige startdatums blijven in de auditpopulatie maar vallen buiten tijdgebonden berekeningen.

De grafieken tonen ruwe volumes. Zij corrigeren niet voor het aantal maandagen of zondagen in het bestand, dienstbezetting of ontbrekende exportdagen. Het datumoverzicht bevat alleen datums waarop geldige auditregels voorkomen. Een ontbrekende datum bewijst geen nulactiviteit.

Het getoonde datumbereik loopt van het eerste tot het laatste gevonden geldige starttijdstip. Op het overzicht wordt dat afgeleid uit de auditpopulatie; exportnamen en het rapport gebruiken de bronpopulatie. Die bereiken kunnen verschillen als grensdagen uitsluitend systeemregels bevatten. Geen van beide bewijst dat de volledige bedoelde exportperiode aanwezig is.

## 7. Tijdstippen en toegangstermijn

De parser ondersteunt numerieke Excel-datums in het 1900-datumsysteem, datumtijdtekst zoals `01-05-2026, 09:30:00` en de ondersteunde ISO-vorm zonder tijdzone. Onmogelijke kalenderdatums en kloktijden worden afgewezen. Een bestand met het 1904-datumsysteem wordt geweigerd met een melding.

De tijdstippen worden als geëxporteerde kloktijden behandeld, onafhankelijk van de tijdzone van de browser. Er wordt geen bron-tijdzone vastgesteld of omgerekend. Tijdverschillen rond de overgang tussen zomer- en wintertijd kunnen daardoor onzeker zijn. Ook gebeurtenissen vóór het begin van de export zijn onbekend.

In het testbestand hebben 1.690 regels een duur van 600 minuten en 237 regels een duur van 30 minuten. De her-escalatiecontrole gebruikt afzonderlijk `activeAccessMinutes = 840`. Deze 14 uur is de overgenomen functionele aanname voor triage; de export bewijst die termijn niet en bevat geen informatie over tussentijdse intrekking van toegang.

Laat FAB de gebruikte toegangstermijn toetsen aan de feitelijke inrichting. Een onjuiste termijn verandert de selectie van her-escalaties. Bewaar bij een beoordeling de toegepaste instellingen.

## 8. Her-escalaties en activatievertraging

### 8.1 Her-escalatie tijdens aangenomen actieve toegang

Voor een nieuwe regel B zoekt de webui binnen de auditpopulatie naar een eerdere regel A van dezelfde medewerkersleutel en dezelfde herkenbare cliënt-ID. Beide starttijdstippen moeten geldig zijn. Regel A moet een leesbare activatie hebben die niet vóór de eigen start ligt.

De tijdsvoorwaarden zijn:

```text
start A <= start B
start A <= activatie A <= start B
0 <= start B - activatie A <= activeAccessMinutes
```

De grenzen zijn inclusief. Bij dezelfde starttijd geldt de lagere Excel-rij als eerdere regel; dit maakt de verwerking reproduceerbaar maar bewijst geen feitelijke volgorde binnen die seconde. Regel B hoeft zelf niet geactiveerd te zijn.

Van de passende eerdere regels wordt de meest recente beschikbare activatie gebruikt. Een eerdere poging die pas ná de start van B activeert, kan een reeds beschikbare activatie niet verdringen. De geselecteerde eerdere bronrij wordt bij het aandachtspunt bewaard en bij doorklikken getoond.

Een ontbrekende cliënt-ID, medewerkersleutel of startdatum verhindert deze koppeling. Een activatie vóór de eigen start is geen geldige eerdere activatie voor deze controle.

### 8.2 Zeer snelle her-escalatie

Dit is een aanvullend kenmerk van dezelfde geselecteerde relatie A/B:

```text
her-escalatie volgens paragraaf 8.1
en 0 <= start B - start A <= veryFastRepeatMinutes
```

De standaard is 5 minuten. Deze maat vergelijkt dus met de eerdere regel die voor de actieve-toegangscontrole is gekozen, niet met iedere willekeurige vorige poging. Een reeks niet-geactiveerde pogingen zonder geldige eerdere activatie krijgt op deze grond geen zeer-snel-signaal.

### 8.3 Activatievertraging

```text
activatievertraging in minuten = (activatie - start) / 60 seconden
late activatie als activatievertraging > activationDelayThresholdMinutes
```

De standaardgrens is strikt groter dan 2 minuten. De beslissing gebruikt het ongeronde tijdsverschil; de tabel toont een afgeronde waarde. Exact 2 minuten valt dus niet onder late activatie, 2 minuten en 1 seconde wel.

Een negatieve vertraging wordt als datakwaliteitssignaal behandeld. Een lege of onleesbare activatie krijgt eveneens een datakwaliteitssignaal, tenzij het veld expliciet `Niet geactiveerd` bevat. Dat laatste is een aparte geregistreerde toestand; de oorzaak kan niet uit de tekst worden afgeleid.

## 9. Auditsignalen

De onderstaande criteria gelden voor auditregels en de toegepaste instellingen. Drempels selecteren patronen; het zijn geen normen voor toelaatbaar gedrag.

| Signaal | Standaardcriterium | Welke regels krijgen het signaal? |
| -- | -- | -- |
| `NIET_GEACTIVEERD` | Aan | Regels met expliciet `Niet geactiveerd` |
| `NACHT` | Aan; 23:00 tot 06:00 | Startuur ≥ 23 of < 6; begin inclusief, einde exclusief |
| `WEEKEND` | Uit | Bij inschakelen: zaterdag of zondag |
| `HOOG_DAGVOLUME` | ≥ 15 | Alle regels van de medewerker op de betreffende kalenderdag |
| `VEEL_UNIEKE_CLIENTEN_MEDEWERKER` | ≥ 50 herkenbare cliënten | Alle auditregels van de medewerker in de export, ook diens locatieregels |
| `VEEL_MEDEWERKERS_CLIENT` | ≥ 4 herkenbare medewerkers | Alle auditregels voor die herkenbare cliënt |
| `VEEL_TEAMS_CLIENT` | ≥ 3 niet-lege teams | Alle auditregels voor die herkenbare cliënt |
| `HERESCALATIE_TIJDENS_ACTIEVE_TOEGANG` | Aan; ≤ 840 minuten | De nieuwe regel die aan paragraaf 8.1 voldoet |
| `ZEER_SNELLE_HERESCALATIE` | Aan; ≤ 5 minuten | De nieuwe regel die aan paragraaf 8.2 voldoet |
| `LATE_ACTIVATIE` | Aan; > 2 minuten | De vertraagd geactiveerde regel |
| `ZELDZAME_REDEN` | Uit; ≤ 2 keer | Bij inschakelen: regels met een reden die maximaal zo vaak in de auditpopulatie voorkomt |
| `ONGELDIGE_STARTDATUM` | Datakwaliteit aan | Start ontbreekt of kan niet worden gelezen |
| `ONTBREKENDE_KERNVELDEN` | Datakwaliteit aan | Gebruiker, medewerkernummer, team of reden ontbreekt |
| `ONVOLLEDIG_CLIENTDOEL` | Datakwaliteit aan | Cliëntdoel mist cliënt-ID of cliëntnaam |
| `ONGELDIGE_ACTIVATIE` | Datakwaliteit aan | Activatie ontbreekt, is onleesbaar of ligt vóór de start; expliciet niet-geactiveerde regels uitgezonderd |
| `ONGELDIGE_DUUR` | Datakwaliteit aan | Duur ontbreekt, is niet numeriek of is negatief |

Een groepssignaal kan op veel regels terugkomen. Zo zijn 100 regels met `HOOG_DAGVOLUME` geen 100 afzonderlijke dagen met een piek. Cliënt- en medewerkersdrempels gelden voor het gehele bestand en zijn daardoor gevoelig voor de lengte van de exportperiode.

Bij gelijke begin- en einduren is het nachtvenster leeg. De geaggregeerde nacht- en weekendtellingen blijven beschikbaar als het bijbehorende signaal is uitgeschakeld.

## 10. Controleprioriteit en overlap

De webui groepeert signalen in vier thema's:

| Thema | Signalen |
| -- | -- |
| Toegang en activatie | Her-escalatie, zeer snelle her-escalatie, niet geactiveerd, late activatie |
| Volume en spreiding | Hoog dagvolume, veel cliënten per medewerker, veel medewerkers of teams per cliënt, zeldzame reden |
| Tijdpatronen | Nacht en weekend |
| Datakwaliteit | Ontbrekende kernvelden of cliëntgegevens, ongeldige start, activatie of duur |

De controleprioriteit wordt uitsluitend voor aandachtspunten bepaald:

| Prioriteit | Regel |
| -- | -- |
| Hoog | Het ingeschakelde her-escalatiesignaal is aanwezig, of er zijn signalen uit minimaal drie thema's |
| Midden | Twee thema's, zonder de bovenstaande hoge prioriteit |
| Basis | Overige aandachtspunten |

Bij een niet-geactiveerde poging telt `ONVOLLEDIG_CLIENTDOEL` niet nogmaals mee voor het aantal prioriteitsthema's. Het signaal blijft wel zichtbaar en telt mee in de datakwaliteitsthemakaart. Daardoor kunnen de themakaarten en prioriteitsgroepen niet rechtstreeks uit elkaar worden opgeteld.

Deze indeling is een gekozen werkvolgorde. Thema's zijn niet bewezen onafhankelijk en de labels zeggen niets over de ernst of kans op een overtreding. De aandachtspuntentabel sorteert eerst op prioriteit, vervolgens op aantal signalen en daarna op starttijd.

In het testbestand overlappen `NIET_GEACTIVEERD` en `ONVOLLEDIG_CLIENTDOEL` volledig: beide komen op dezelfde 114 regels voor. Samen zijn dit 114 unieke regels, geen 228 onafhankelijke bevindingen. Ook zeer snelle her-escalatie en her-escalatie beschrijven een gedeeld patroon.

## 11. Verdiepende analyses

### 11.1 Peervergelijking

Een medewerker is vergelijkbaar wanneer alle bijbehorende auditregels precies één niet-lege teamwaarde en precies één niet-lege deskundigheid hebben. Bij wisselende of ontbrekende context krijgt die medewerker geen peer-ratio en telt die medewerker niet mee als peer van anderen.

Voor een vergelijkbare medewerker worden drie groepen andere vergelijkbare medewerkers gevormd:

1. hetzelfde team;
2. dezelfde deskundigheid;
3. hetzelfde team én dezelfde deskundigheid.

De medewerker zelf wordt uit iedere groep weggelaten. Per groep zijn standaard minimaal drie **andere** medewerkers nodig. De mediaan is het middelste persoonsaantal na sorteren, of het gemiddelde van de twee middelste waarden bij een even aantal peers.

| Getoonde ratio | Teller | Noemer |
| -- | -- | -- |
| Volume / team | Auditregels medewerker | Mediaan auditregels van andere vergelijkbare teamleden |
| Cliënten / team | Unieke herkenbare cliënten medewerker | Mediaan unieke cliënten van andere vergelijkbare teamleden |
| Volume / deskundigheid | Auditregels medewerker | Mediaan auditregels van andere vergelijkbare medewerkers met die deskundigheid |
| Volume / team+deskundigheid | Auditregels medewerker | Mediaan auditregels van andere vergelijkbare medewerkers met die combinatie |

Bij onvoldoende peers of een noemer van nul blijft de ratio leeg. Een ratio van 2 betekent tweemaal de groepsmediaan binnen deze export. Zij betekent niet tweemaal de werklast of tweemaal het risico.

Voorbeeld: medewerker A heeft 20 regels; drie andere passende medewerkers hebben 4, 10 en 16 regels. De mediaan van de peers is 10 en de ratio van A is `20 / 10 = 2,00`. Bij slechts twee passende anderen blijft de ratio met de standaardinstelling leeg.

Medewerkers zonder auditregels zijn onbekend. De vergelijking blijft geselecteerd op escalatiegebruik en corrigeert niet voor diensten, FTE, inzetduur, caseload of verschillen in autorisatie. De webui bevat hier geen peer-ratio voor nachtpercentage of cliënten per deskundigheid.

Doorklikken toont de bronregels van de medewerker én de verzameling team- en deskundigheidspeers. De combinatiegroep is hun doorsnede. De bronregeldialoog bevat hierdoor meer regels dan alleen de teller van een individuele ratio.

### 11.2 Bursts per medewerker

Een burst is een hoog aantal pogingen binnen een voortschrijdend tijdvenster van één medewerker. Alleen regels met een medewerkersleutel en geldige starttijd doen mee. Alle doeltypen kunnen bijdragen; onbekende doel-ID's tellen wel mee in het aantal pogingen maar niet in het aantal herkenbare unieke doelen.

Standaard is het venster 60 minuten en de drempel 5 regels. De tijdsgrens is inclusief. De webui toont één venster per medewerker: eerst het hoogste aantal regels, bij gelijkstand het hoogste aantal verschillende herkenbare doelen. Een verdere gelijkstand behoudt het eerst gevonden venster.

De getoonde start en einde zijn de eerste en laatste gebeurtenis binnen dat venster. Het verschil kan korter zijn dan 60 minuten. De tabel telt medewerkers met een geselecteerd venster, geen afzonderlijke incidenten of alle mogelijke bursts.

### 11.3 Cliëntclusters

Deze analyse gebruikt cliëntgerichte auditregels met een herkenbaar cliënt-ID en geldige starttijd. Per cliënt zoekt zij vensters van standaard 120 minuten. Een venster kwalificeert bij minimaal 3 herkenbare medewerkers **of** minimaal 2 niet-lege teams.

Pas na die toets kiest de webui één sterkste kwalificerend venster per cliënt: eerst de meeste medewerkers, daarna de meeste teams, daarna de meeste regels. Een verdere gelijkstand behoudt het eerst gevonden venster. Zo blijft een venster dat uitsluitend de teamdrempel haalt beschikbaar voor selectie.

Voorbeeld met een medewerkersdrempel van 4: een ochtendvenster met 3 medewerkers uit 1 team kwalificeert niet. Een middagvenster met 2 medewerkers uit 2 teams kwalificeert wel bij de teamdrempel van 2 en wordt getoond.

Dit is geen bewijs dat medewerkers buiten hun werkgebied handelden. Acute zorg, opname, overdracht en tijdelijke inzet kunnen het patroon verklaren. Ook hier wordt één geselecteerd venster getoond, niet alle clusters in het bestand.

### 11.4 Concentratie per medewerker

```text
top-3 doelaandeel =
  100 × regels naar de drie meest voorkomende herkenbare doelen
      / alle regels van de medewerker met een herkenbaar doel

top-3 cliëntaandeel =
  100 × regels naar de drie meest voorkomende herkenbare cliënten
      / alle cliëntgerichte regels van de medewerker met herkenbaar cliënt-ID
```

Gemengde doelen gebruiken doeltype plus doel-ID; het cliëntaandeel gebruikt alleen cliënt-ID's. Een lege noemer geeft een lege cel. Pogingen zonder herkenbaar doel tellen niet mee in teller of noemer, maar blijven in het totale escalatievolume staan.

Bij drie of minder herkenbare doelen is het top-3 aandeel vanzelf 100%. Beoordeel daarom altijd het totale aantal regels, unieke doelen en ontbrekende doelen naast het percentage. Concentratie kan een vaste cliëntgroep beschrijven; brede spreiding kan bij een functie passen.

### 11.5 Redengebruik

Per genormaliseerde reden toont de webui welke medewerker en welk team het grootste aantal regels met die reden hebben. Een reden wordt standaard pas getoond vanaf drie auditregels.

```text
topmedewerkeraandeel = 100 × regels van de topmedewerker met reden R / alle regels met reden R
topteamaandeel       = 100 × regels van het topteam met reden R / alle regels met reden R
```

Dit beantwoordt wie het grootste deel van een reden gebruikt. Het beantwoordt niet welk deel van het totale werk of alle escalaties van die medewerker door die reden wordt gevormd. Een hoog aandeel kan ontstaan doordat iemand sowieso veel escaleert.

Bij een gedeelde eerste plaats wordt één eerst aangetroffen medewerker of team getoond. Ontbrekende medewerkersleutels en teams kunnen in deze analyse als onbekende groep meetellen. Lees die groep niet als één geïdentificeerde persoon of werkelijk team.

## 12. Doorklikken en exports

| Weergave | Wat wordt geopend? |
| -- | -- |
| Kerncijfer of auditflowstap | Bronregels die bijdragen aan de getoonde populatie; een uniek-personencijfer opent dus meerdere regels per persoon |
| Signaal of thema | Regels met dat signaal of minimaal één signaal binnen het thema |
| Balk, heatmapcel of medewerkerpunt | De bijbehorende regels voor die categorie, tijdcombinatie of medewerker |
| Medewerker-, cliënt-, team- of andere aggregatieregel | Alle bijdragende auditregels voor die tabelregel, niet automatisch alleen de aangeklikte celmaat |
| Her-escalatie-aandachtspunt | De nieuwe regel plus de geselecteerde eerdere activatie als die is gevonden |
| Burst of cliëntcluster | Alleen de regels binnen het geselecteerde venster |
| Peerregel | Medewerker plus de gebruikte team- en deskundigheidspeers |
| Datakwaliteit of auditlogica | De bijbehorende regels volgens de populatie van die controle |

Details bevatten Excel-rijnummers, de bronvelden, auditcontext en waar van toepassing verwijzingen naar eerdere of dubbele regels. De bronwaarden worden na inlezen getoond; witruimte kan zijn verwijderd en numerieke Excel-datumwaarden blijven in bronvelden numeriek. Bewaar de originele export voor controle op de oorspronkelijke celweergave.

De scatterplot toont volume tegenover herkenbare unieke cliënten. Punten kunnen overlappen; gebruik het medewerkersoverzicht om alle personen afzonderlijk te zien. Balken in het overzicht tonen een topselectie, niet noodzakelijk alle categorieën.

**Aandachtspunten CSV** exporteert alle aandachtspunten van de analyse, niet alleen een gefilterde tabelweergave. **Bronregels CSV** exporteert alle regels van de geopende detailselectie; het zoekveld in de dialoog beperkt de export niet. Verdachte formuleprefixen krijgen bij CSV-export een voorafgaand apostrof om interpretatie als formule te beperken.

Het HTML-rapport bevat de toegepaste instellingen, definities en analysetabellen. Sommige tabellen hebben een weergavelimiet; bij afkapping staat vermeld hoeveel regels zijn getoond. Het rapport is daardoor niet altijd een volledige export van alle onderliggende bronregels.

De webui voert de analyse lokaal uit, zonder netwerkverkeer of opslag van ingelezen data in browseropslag. Sluiten of verversen wist de sessiegegevens. Gedownloade rapporten en CSV-bestanden blijven wel bestaan en kunnen persoonsgegevens bevatten. Bewaar en deel deze volgens de geldende interne afspraken.

## 13. Datakwaliteit en interpretatie

De controles omvatten ontbrekende kernvelden, onvolledige cliëntdoelen, ongeldige start- en activatietijden, ongeldige duur, identifierconflicten, redenvarianten en duplicaten. Een conflict hoeft niet fout te zijn, maar moet worden verklaard voordat het voor een persoonsgerichte conclusie wordt gebruikt.

Niet iedere kwaliteitsbevinding wordt automatisch een auditsignaal. Identifierconflicten en redenvarianten zijn bijvoorbeeld afzonderlijke controletabellen. Het aantal kwaliteitsbevindingen is geen aantal unieke probleemregels; één regel kan aan meerdere bevindingen bijdragen.

Het testbestand bevat twee activaties die één seconde vóór de start liggen. De webui markeert die als `ONGELDIGE_ACTIVATIE`. Eén van die regels had al een ander signaal; de uitbreiding voegt daarom één uniek aandachtspunt toe. Onderzoek bijvoorbeeld klokregistratie of exportvolgorde voordat hier een inhoudelijke conclusie aan wordt verbonden.

De webui stelt met alleen deze export niet vast:

- welke dossiergegevens daadwerkelijk zijn geraadpleegd, gewijzigd of gedeeld;
- of er een behandel- of werkrelatie was;
- of de medewerker ingepland was of tijdelijk elders werkte;
- of de geregistreerde reden voldoende was voor de situatie;
- of de toegang feitelijk nog actief was of tussentijds was ingetrokken;
- of een patroon afwijkt na correctie voor inzet, caseload en autorisatie;
- of de export volledig is of eerdere relevante gebeurtenissen ontbreken.

Een mogelijke beoordelingsroute is eerst planning, rooster en inzetcontext controleren, daarna relevante dossierlogging raadplegen en vervolgens zo nodig aanvullende toelichting vragen. Dit is een voorgestelde werkwijze; de volgorde moet passen bij de onderzoeksvraag. Wel of niet ingepland zijn bewijst op zichzelf geen rechtmatigheid of onrechtmatigheid. Controleer ook welke autorisatievormen daadwerkelijk in de eigen omgeving worden gebruikt.

## 14. Standaardinstellingen

Onderstaande namen komen overeen met de instellingen in de webui-code. Een export van het HTML-rapport bevat de werkelijk toegepaste waarden.

| Instelling | Standaard |
| -- | -: |
| `activeAccessMinutes` | 840 |
| `veryFastRepeatMinutes` | 5 |
| `nightStartHour` | 23 |
| `nightEndHour` | 6 |
| `employeeDailyVolumeThreshold` | 15 |
| `employeeUniqueClientsThreshold` | 50 |
| `clientUniqueEmployeesThreshold` | 4 |
| `clientUniqueTeamsThreshold` | 3 |
| `activationDelayThresholdMinutes` | 2 |
| `rareReasonMaxCount` | 2 |
| `peerGroupMinSize` | 3 |
| `burstWindowMinutes` | 60 |
| `burstThreshold` | 5 |
| `clientClusterWindowMinutes` | 120 |
| `clientClusterEmployeeThreshold` | 3 |
| `clientClusterTeamThreshold` | 2 |
| `reasonConcentrationMinCount` | 3 |

| Schakelaar | Standaard |
| -- | -- |
| `excludeDuration30` | Uit |
| `signalNight` | Aan |
| `signalWeekend` | Uit |
| `signalNotActivated` | Aan |
| `signalRareReason` | Uit |
| `signalActivationDelay` | Aan |
| `signalReEscalationActiveAccess` | Aan |
| `signalVeryFastRepeat` | Aan |
| `signalDataQuality` | Aan |
| `signalEmployeeDailyVolume` | Aan |
| `signalEmployeeUniqueClients` | Aan |
| `signalClientUniqueEmployees` | Aan |
| `signalClientUniqueTeams` | Aan |

De webui accepteert gehele getallen. Uren lopen van 0 tot en met 23; de activatievertragingsdrempel mag nul zijn; overige numerieke instellingen moeten minimaal 1 zijn. Ongeldige invoer wordt niet toegepast. Bekende systeemredenen blijven altijd uitgesloten, ongeacht de 30-minutenschakelaar.

## 15. Controle-uitkomsten voor het gebruikte testbestand

Referentiebestand: `979de7ca-57d5-468d-8596-fec9a675106e.xlsx`, met waargenomen datums van 1 tot en met 31 mei 2026. Onderstaande resultaten zijn tijdens de controle vastgesteld met de standaardinstellingen. Het zijn referentie-uitkomsten voor dit bestand, geen verwachting voor andere maanden.

| Controle | Uitkomst |
| -- | -: |
| Bronregels | 1.927 |
| Uitgesloten systeemregels | 237 |
| Uitgesloten duplicaatkopieën | 0 |
| Auditregels | 1.690 |
| Auditregels / bronregels | 87,7% |
| Herkenbare medewerkers | 235 |
| Herkenbare cliënten | 483 |
| Herkenbare locatiedoelen | 43 |
| Cliëntgerichte auditregels | 946 |
| Daarvan met herkenbaar cliënt-ID | 832 |
| Daarvan zonder herkenbaar cliënt-ID | 114 |
| Locatiegerichte auditregels | 744 |
| Niet-geactiveerde auditregels | 114 |
| Nachtregels | 91 |
| Late activaties | 13 |
| Her-escalaties binnen aangenomen actieve toegang | 44 |
| Daarvan zeer snel | 6 |
| Ongeldige activaties | 2 |
| Unieke aandachtspunten | 482 |
| Aandachtspunten / auditregels | 28,5% |
| Medewerkers met een geselecteerd burstvenster | 11 |
| Cliënten met een geselecteerd clustervenster | 11 |

De controle combineerde onafhankelijke hertelling van kerncijfers, gerichte randgevallen en browsercontroles. Geteste randgevallen omvatten opnieuw analyseren met een kortere toegangstermijn, toekomstige activatie naast reeds beschikbare toegang, een cluster dat uitsluitend de teamdrempel haalt, onmogelijke datums, negatieve activatievertraging en duplicaten. Ook doorklikdetails, instellingen, rapport- en CSV-export en desktop- en mobiele weergave zijn gecontroleerd. Dit is geen bewijs voor alle denkbare exportvarianten of autorisatie-inrichtingen.

## 16. Niet-geïmplementeerde analyses

De webui berekent geen historische norm of juridische conclusie. Voor de volgende analyses zijn aanvullende gegevens en expliciete definities nodig:

| Vervolganalyse | Benodigde aanvulling |
| -- | -- |
| Nieuwe of ongebruikelijke medewerker-cliëntrelaties | Voldoende historie en een betrouwbare definitie van nieuw of ongebruikelijk |
| Vergelijking met vorige perioden | Vergelijkbare exports en een expliciete vergelijkingsbasis |
| Werkelijk kruisende teamgrenzen | Historische teamtoewijzing, inzet-, rooster- of behandelrelaties |
| Werklastgecorrigeerde vergelijking | Volledige bezetting, FTE, gewerkte uren, diensten en eventueel caseload |
| Bewezen dossierinzage na escalatie | Passende dossierlogging en een betrouwbare koppeling op persoon, cliënt en tijd |

Voor trends tussen perioden moeten exportduur, dekking, definities, instellingen en groepsindeling vergelijkbaar zijn. Ruwe maandtotalen tonen zonder die voorwaarden geen gedragsverandering.
