# Mock-ups voor issue #17

De gebruiker selecteerde op 08-10-2026 **activatievertraging** en **nachtvenster** uit de [fase-2-beoordeling](../../fase-2-visuele-uitleg.md). Deze mock-ups maken het ontwerp concreet vóór productie-implementatie. Alle gegevens zijn fictief; de productie-webui is ongewijzigd.

## Bekijken en beslissen

- [Webui-voorstel](index.html): beide uitlegblokken met keuzelijsten voor grenswaarden en signaalschakelaars.
- [Rapportvoorstel](rapport.html): dezelfde uitleg binnen Signalen en Tijdpatronen; uitleg en tabel klappen samen in. Het rapport is ook zonder JavaScript leesbaar.
- [Afdrukvoorbeeld](rapport-print.pdf): A4, inclusief een afzonderlijke ontwerpreviewbijlage met grensgevallen. Die bijlage is geen voorgestelde productie-rapportsectie.

**Ontwerp goedgekeurd op 08-10-2026.** De gebruiker heeft de compacte tijdlijnen en het nachtvenster akkoord bevonden en gevraagd dit voorstel als PR in te dienen. Productie-implementatie is de volgende stap; deze wijziging bevat uitsluitend beoordeling en mock-ups.

## Ontwerpkeuzes

Behoud van het bestaande paars `#A02A85`, cyaan `#007F9F`, donkergrijs `#333333`, lichtgrijs `#F6F7F9` en wit. Segoe UI/Arial sluit aan bij de toepassing. Links uitgelijnde uitleg staat boven de relevante tabel. De activatievoorbeelden zijn twee compacte tijdlijnen met één gedeelde grensmarkering; start en grens staan elk één keer boven de figuur. Een cirkel op de grens en een ruit er voorbij tonen het verschil zonder alleen kleur te gebruiken. De tijdas heeft een zichtbare onderbreking; de schematische afstanden zijn als niet-op-schaal gemarkeerd. De nachtband gebruikt een vaste as 00:00–24:00 en arcering plus exacte tekstintervallen; kleur draagt de betekenis niet alleen. De hoofdboodschap staat in één korte zin. Berekening, uitzonderingen en beperkingen staan in een uitklapper, die bij afdrukken wordt geopend. Geen animatie, externe bronnen of browseropslag.

De mock-ups veranderen geen analyse. De webui-keuzelijsten zijn uitsluitend reviewbediening. In productie volgt de uitleg de instellingen van de uitgevoerde analyse.

| Onderwerp | Webui | Rapport |
| -- | -- | -- |
| Activatievertraging | Onder de bestaande prioriteitsuitleg bij Aandachtspunten; fictieve grensvoorbeelden vóór de tabel | Binnen Signalen, vóór de signaaltabel; dezelfde grensregel en voorbeeldwaarden |
| Nachtvenster | Bij Tijdpatroon, vóór de uurweergave | Binnen Tijdpatronen, vóór de bestaande heatmap |

De kleine fictieve tabellen tonen de relatie met bronwaarden en uurvolume. Ze vervangen de productietabellen/heatmap niet en zijn geen analyse van het standaardfixture. `LATE_ACTIVATIE` en `NACHT` blijven triage-indicatoren, geen bewijs van onrechtmatige toegang of dossierinzage.

## Zelf controleren

1. Open het webui-voorstel en vergelijk 120 en 121 seconden bij de standaardgrens van 2 minuten.
2. Kies grens 0: precies 0 seconden geeft geen signaal, 1 seconde wel. Schakel het signaal uit: beide voorbeelden krijgen geen signaal.
3. Kies achtereenvolgens nachtvenster 23:00–06:00, 08:00–17:00 en 06:00–06:00. Het laatste venster heeft geen geselecteerd uur.
4. Schakel NACHT uit. De uitleg onderscheidt het uitgeschakelde signaal van de nog beschikbare nachtvolumes.
5. Open het rapport; klap Signalen en Tijdpatronen met Enter in en uit. Uitleg en tabel verdwijnen samen.
6. Bekijk de PDF. De reviewbijlage bevat nulgrens, leeg venster en uitgeschakelde signalen; deze voorbeelden zijn niet allemaal tegelijk toegepaste analyse-instellingen.

## Validatie en grenzen

[qa.json](qa.json) bevat de gerichte browserchecks: grens- en uitgeschakelde scenario's, middernacht, hetzelfde-dagvenster, leeg venster, toetsenbordfocus, inklappen met Enter, containment op 1280/800/390 px, printopening van alle secties en een leesbaar rapport met JavaScript uit. Geen ongehanteerde JavaScriptfouten of HTTP(S)-requests waargenomen.

De screenshots en een gerenderde PDF-pagina zijn visueel gecontroleerd. Er is geen volledige toegankelijkheidsaudit uitgevoerd. Native selectbediening met alle platformtoetsen is niet bewezen; focus en rapportbediening met Enter zijn gecontroleerd. Deze checks bewijzen de mock-ups, niet een toekomstige productie-implementatie. Productieregressies, actuele analyse-instellingen, CSV-pariteit en versie/documentatie-updates volgen bij productie-implementatie.

## Herziening na ontwerpreview

Op 08-10-2026 wees de gebruiker erop dat het eerste voorstel nog vooral tekst was. De activatie-uitleg is daarom vervangen door een tijdlijnpaar; de nachtvenster-uitleg is verkort tot band plus kernzin. Webui en statisch rapport gebruiken dezelfde herziene inhoud. De screenshots en PDF zijn opnieuw gegenereerd en gecontroleerd.

De compacte herziening gebruikt de skill `diagram-design`: tijdlijnlayout in fit-formaat, gedeelde as, minder herhaalde labels en een zichtbare tijdasonderbreking. De bestaande projecttokens blijven leidend: papier `#F6F7F9`, inkt `#333333`, accent `#A02A85`, lijnkleur `#007F9F` en lokale Segoe UI/Arial. Er zijn geen externe fonts toegevoegd en geen gedeelde skillprofielen aangepast. De toegankelijke SVG wordt ook afzonderlijk met de self-check van de skill gecontroleerd.
