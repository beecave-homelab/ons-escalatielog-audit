# Besluiten over visuele uitleg en rapportpariteit

Uitvoering van de issuebespreking in [#2](https://github.com/beecave-homelab/ons-escalatielog-audit/issues/2) en [#3](https://github.com/beecave-homelab/ons-escalatielog-audit/issues/3), na de opdracht op 21-09-2026 om het besproken werk in productiecode uit te voeren. De mock-ups uit PR #9 waren alleen ontwerpdocumentatie; versie 0.10.0 implementeert de vijf uitgewerkte onderwerpen uit fase 1.

## Issue #2: geselecteerde productie-uitwerking

| Onderwerp | Webui | Zelfstandig rapport |
| -- | -- | -- |
| Controleprioriteit | Eén beslisroute bij Aandachtspunten; onderbouwing per rij en in bronregeldetail | Eén overkoepelende prioriteitssectie met route en drie geneste prioriteitsgroepen |
| Her-escalatie | Werkelijke gekoppelde Excel-rijen en start/activatietijden, met beide exacte tijdsafstanden | Een expliciet fictief voorbeeld op de inclusieve grens, met de toegepaste instelling en een voorbeeldtabel |
| Bursts en cliëntclusters | Algemeen schema boven tabel; werkelijk geselecteerd venster bij bronregels | Algemeen schema met exacte start, einde, verstreken seconden, maximum en drempels in de tabel |
| Peer-ratio’s | Neutrale schaal en bestaande definities; feitelijke oorzaak van ontbrekende ratio per cel | Dezelfde inhoud, geheel binnen Peeranalyse |
| Top-3-concentratie | Databalk naast exacte teller/noemer/percentage; doelen en cliënten gescheiden | Dezelfde databalk en waarden binnen Concentratie |

De nieuwe tabelkolommen zijn *Waarom deze prioriteit*, *Minimum escalaties*, *Minimum medewerkers*, *Minimum teams*, *Selectiereden*, *Verstreken (sec.)*, *Top-3 doelregistraties* en *Top-3 cliëntregistraties*. Ze horen alleen bij hun eigen analyse. De bronregels- en aandachtspunten-CSV behouden hun bestaande schema. Ratio’s en concentratiepercentages blijven numeriek sorteerbaar; opmaak vervangt de waarden niet.

Fase 2 blijft een afzonderlijke selectie zoals het issue voorschrijft. Activatievertraging, nachtvenster en redenconcentratie krijgen in deze fase geen nieuwe visual. De analysegrenzen blijven gelden; de regressies controleren ook de strikte activatievertraging. Auditflow en overlap per thema zijn reeds opgenomen via #3.

## Issue #3: beslismatrix en afronding geselecteerde secties

| Kandidaat | Besluit en controlewaarde | Populatie, tabel en plaatsing | Toegankelijkheid, print en ruimte |
| -- | -- | -- | -- |
| Auditflow | Opgenomen in 0.9.0; verklaart de reconciliatie | Alle bronregels, met afzonderlijke systeem-, duplicaat- en auditpopulatie; aandachtspunten zijn deel van audit. Eigen populatietabel | Exacte waarden en expliciete noemers, geen extra diagram nodig |
| Tijdheatmap | Opgenomen in 0.9.0; toont uur/weekdagpatronen | Auditregels met geldige starttijd; ongeldige starttijden apart. Eén gedeelde matrix | Twee tabellen van twaalf uur; vanaf 0.10.0 ook nullen expliciet als tekst |
| Controlethema’s | Opgenomen in 0.9.0; vergelijkt omvang, geen deel-van-geheel | Unieke auditregels per thema. Vanaf 0.10.0 eigen thematabel naast balken en bestaande signaaltabel in dezelfde sectie | Vier tekstwaarden blijven zonder kleur leesbaar; beperkte extra lengte |
| Topmedewerkers en cliënten | Behouden bij hun eigen tabellen | Escalatievolume respectievelijk unieke medewerkers; cliëntselectie en sortering gedeeld met de webui, tweede sleutel escalatievolume | Rapporttabel volgt dezelfde selectievolgorde; afkapping blijft vermeld, lange grafieklabels mogen afbreken |
| Medewerkerspreiding | Uitgesteld, conform bespreking | Volume × unieke cliënten per medewerker | Identificatie van overlappende punten en leesbaarheid in print vragen eerst een aparte uitwerking |
| Topteams | Uitgesteld, conform bespreking; beperkte extra waarde boven tabel | Auditvolume per team; bestaande teamtabel blijft | Geen extra rapportlengte |
| Topredenen | Uitgesteld, conform bespreking | `reasons` telt alle genormaliseerde redenen; `reasonUse` is een andere selectie met minimumaantal en concentratie | Een eventuele toekomstige visual hoort bij een volledige redenaggregatietabel, niet alleen bij Redengebruik |
| Verhoudingsdonuts | Niet opnemen | Percentages zijn al beschikbaar bij KPI’s en populatietabel | Voorkomt dubbele uitleg en ruimtebeslag |
| Beoordelingsroute | Korte tekst behouden | Bronkwaliteit, context en aanvullende logging; geen nieuwe bevinding | Controlekader en beperkingen blijven tekst, geen extra diagram |

Deze besluiten zijn geen belofte dat iedere kandidaat is gebouwd. De geselecteerde onderwerpen zijn geïmplementeerd; uitgestelde onderwerpen en fase 2 staan hierboven afzonderlijk benoemd. Het toevoegen van een nieuwe visual daarvoor vereist een inhoudelijke keuze. Deze wijziging sluit de GitHub-issues niet automatisch.

## Controlebewijs

De regressietests gebruiken alleen synthetische gegevens. Ze controleren de prioriteitsuitzondering en nul meetellende thema’s, her-escalatie exact op en buiten de grens, heranalyse met andere instellingen, uitgeschakelde signalen, beide clusterdrempels afzonderlijk, burstgrenzen, lege noemers en ontbrekende peercontext. Browsertests controleren plaatsing, toetsenbordbediening, gezamenlijk inklappen, het echte `beforeprint`-event, escaping, lege resultaten en de bestaande synthetische referentiecijfers.

Op 21-09-2026 slagen alle zeven tests met 95,10% dekking (ondergrens 85%), samen met de lockfile-, Markdown-, HTML- en Ruff-controles. De lokale referentieanalyse behoudt alle cijfers uit §15; signalen, prioriteiten en beide CSV-uitvoeren zijn gelijk aan versie 0.9.0. De browserconsole geeft geen fouten.

Met de standaard synthetische export groeit het zelfstandige HTML-rapport van 923.313 naar 1.276.547 bytes. Bij dezelfde A4-afdrukinstellingen groeit het rapport van 345 naar 393 pagina’s door de extra uitleg en tabelwaarden. Prioriteitsredenen staan daarom onder de bijbehorende rij, zonder extra smalle afdrukkolom. De tijdlijn en concentratietabel zijn ook visueel in de PDF gecontroleerd.

De oorspronkelijke mock-ups blijven bewaard als ontwerpgeschiedenis. Gebruik de productie-webui voor de actuele werking; de vaste screenshots en fictieve keuzelijsten uit de mock-ups zijn geen bewijs van de huidige analyseresultaten.
