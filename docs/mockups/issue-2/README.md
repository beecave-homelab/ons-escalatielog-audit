# Mock-ups voor issue #2

Ontwerpvoorstel van 20-09-2026, zelf uitgewerkt zonder subagents. Geen productiecode gewijzigd. De HTML-bestanden zijn zelfstandig, gebruiken geen externe bronnen of browseropslag en bevatten uitsluitend fictieve gegevens.

## Bekijken

- [Webui-mock-ups](index.html): zes webui-schermen voor alle vijf kandidaten uit fase 1. Bursts en cliëntclusters hebben elk een scherm.
- [HTML-exportmock-up](rapport.html): dezelfde onderwerpen als inklapbare rapportsecties.
- [Afdrukvoorbeeld](rapport-print.pdf): afdrukvoorbeeld op A4.
- `webui-*.png` en `rapport-overzicht.png`: screenshots van de voorstellen.
- `nulmeting-aandachtspunten.png`: verse nulmeting vanuit de ongewijzigde webui met `tests/fixtures/synthetic-escalatielog.xlsx`.
- `qa.json`: uitgevoerde browsercontroles en nulmetingcijfers.

De voorgestelde voorbeeldgegevens zijn bewust klein en op de uitleg afgestemd. Het zijn geen analyseresultaten van de standaardfixture. De nulmeting is wel met die fixture berekend.

## Ontwerpkeuzes

Behoud van het bestaande paars (#A02A85), cyaan (#007F9F), donkergrijs (#333333), lichtgrijs (#F6F7F9) en wit. Segoe UI/Arial sluit aan bij de bestaande toepassing. Links uitgelijnde uitleg boven de relevante tabel; tijdlijnen en beslisroutes verduidelijken de analyse. Geen nieuwe dashboardstijl of externe grafiekbibliotheek.

| Kandidaat | Voorstel | Status |
| -- | -- | -- |
| Controleprioriteit | Beslisroute met zes bedienbare uitzonderingsvoorbeelden; kolom Waarom bij aandachtspunten | Voorgesteld als eerste selectie |
| Her-escalatie | Tijdlijn bij gekoppelde bronregels; binnen/op/buiten-grensvoorbeelden; fictief voorbeeld in export | Voorgesteld als eerste selectie |
| Bursts en cliëntclusters | Algemeen schema boven de tabel, werkelijke voorbeeldtijden na openen van het geselecteerde venster; drempels zichtbaar | Voorgesteld als eerste selectie |
| Peer-ratio | Neutrale schaal met referentiepunten en 13 / 6 = 2,17; bestaande definities behouden | Aanvullend voorstel |
| Top-3-concentratie | Teller/noemer naast de balk; doelen en cliënten gescheiden; 100% en lege noemer getoond | Aanvullend voorstel |

Alle voorstellen wachten op inhoudelijke beoordeling. Geen kandidaat is hiermee automatisch goedgekeurd voor productie; fase 2 van het issue is niet uitgewerkt.

## Verschillen tussen webui en rapport

De webui heeft bedienbare uitlegvoorbeelden. Dit is reviewbediening: de uiteindelijke toepassing zou werkelijke analyseresultaten tonen. De vensterknoppen demonstreren de geselecteerde detailinformatie inline; de productieversie heeft al een bronregeldialoog waarin deze uitleg kan worden geplaatst.

Het rapport toont statische uitleg en tabellen samen in een `details.rep`-sectie. Controleprioriteit krijgt één overkoepelend blok met de drie bestaande prioriteitsgroepen daarbinnen. Dit vermijdt drie identieke beslisroutes. De drie groepen blijven afzonderlijk inklapbaar.

De her-escalatiesectie is een expliciet fictief rekenvoorbeeld, met een bijbehorende voorbeeldtabel; geen volledige nieuwe export van alle bronregels. Het is een voorgestelde extra uitlegsectie. De visuele schaal is schematisch en zegt dat expliciet. De tijdgrens is inclusief en begint bij activatie, niet bij de 30-minutencontrole voor systeemuitsluiting.

Voor bursts en clusters bevat het rapport algemene schema's en de geselecteerde aggregaties. Het kopieert geen interactieve bronregeldialogen. De cluster haalt alleen de teamdrempel en maakt zo de OF-voorwaarde zichtbaar.

## Nog te beoordelen vóór implementatie

1. De eerste selectie en of peers/concentratie tegelijk mee moeten.
2. Het overkoepelende prioriteitsblok en de kolom Waarom.
3. De aparte fictieve her-escalatie-uitlegsectie in de export.
4. De extra kolommen voor verstreken tijd, drempels en selectiereden.

Daarna pas integratie met `analyze()`, gedeelde inhoudshelpers, aanvullende analysevelden en productieregressietests. CSV-schema's blijven buiten dit voorstel.

## Controle en grenzen

Chrome/Playwright: alle zes webui-schermen en het rapport gecontroleerd op 1280, 800 en 390 px zonder documentbrede overflow. Prioriteitsscenario's, grensscenario's, vensterbediening met muis/toetsenbord, samen inklappen van peeruitleg/tabel en echt `beforeprint`-gedrag gecontroleerd. Geen JavaScript-fouten. Desktopvoorbeelden en een gerenderde printpagina visueel bekeken.

Geen volledige toegankelijkheidsaudit of productieanalyse-regressietest: dit zijn losstaande ontwerpmock-ups met vaste voorbeeldwaarden. De browserchecks bewijzen niet de toekomstige implementatie. Het PDF-bestand is visueel bewijs; de HTML-tabellen bevatten de semantische structuur.

Dit voorstel staat onder `docs/mockups/issue-2/` en hoort bij issue #2. Productie-implementatie volgt pas na ontwerpbeoordeling. De volledige gegenereerde nulmetingexport blijft lokaal; de screenshot en controlecijfers zijn hier opgenomen.

## Zelf beoordelen

Open `index.html` rechtstreeks in Chrome/Edge, of serveer vanuit de repository:

```bash
python3 -m http.server 8872 --bind 127.0.0.1 --directory docs/mockups/issue-2
```

Open vervolgens `http://127.0.0.1:8872/index.html`.

1. Wissel tussen de zes onderwerpen. Bij Controleprioriteit staan zes voorbeelden in de keuzelijst.
2. Kies bij Her-escalatie achtereenvolgens binnen, exact op en buiten de grens. Tijdlijn, bronregelvoorbeeld en toelichting moeten samen veranderen.
3. Open bij Bursts en Cliëntclusters het geselecteerde venster, ook met Enter en spatie.
4. Open de HTML-export. Klap Peeranalyse open en dicht: uitleg en tabel verdwijnen samen.
5. Druk het rapport af. Alle secties, inclusief de toelichting in geneste uitklappers, moeten zichtbaar zijn.

De screenshots tonen de standaardweergave. De kleine voorbeeldtabellen zijn geen volledige productie-export en de keuzelijsten zijn ontwerpbediening.
