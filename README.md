# PoC’s: knopnamen in de rondleiding

Vier ontwerpvoorstellen bij [PR #123](https://github.com/beecave-homelab/ons-escalatielog-audit/pull/123). De ontwerpkeuze staat nog open. Deze losse branch bevat uitsluitend proefbestanden en wordt niet naar `main` gemergd.

## Bekijken

1. Download deze branch als ZIP en pak hem volledig uit.
2. Open `pocs/index.html` rechtstreeks in je browser.
3. Kies een variant, een voorbeeldstap en eventueel de mobiele weergave. Met **Open deze PoC op volledige grootte** bekijk je de hele rondleiding.

De vier HTML-varianten werken ook afzonderlijk. Er is geen server of installatie nodig. De bestanden bevatten uitsluitend de ingebouwde synthetische gegevens.

| Variant | Werking | Afweging |
| --- | --- | --- |
| 1. Aanhalingstekens | Knopnamen krijgen aanhalingstekens, cursief en een rustige paarstint. | Rustig in lopende tekst; minder nadrukkelijk bij veel namen. |
| 2. Subtiele tekstlabels | Zachte achtergrond met een dunne onderrand. | Snel herkenbaar; kan op een bedienbare knop lijken. |
| 3. Apart actieblok | Zinnen over bediening staan apart onder “Wat je hier kunt doen”. | Meer overzicht bij veel acties; vraagt meer verticale ruimte. |
| 4. Aanwijsbare verwijzingen | Klik op een naam om de echte knop in beeld te brengen en te markeren. | Directe koppeling met de bediening; voert de actie niet uit. |

De toelichtingen zijn ontwerpafwegingen, geen resultaten van gebruikersonderzoek. Er is nog geen variant gekozen of in de productrondleiding toegepast.

## Herkomst en controle

Gemaakt op 25 oktober 2026 vanuit de lokaal geteste rondleiding van PR #123, met de correcties uit commit `bb2219292c96d573f04abb4aeef921b4b95cc64e`. De voorbeeldbeelden tonen de exportstap met synthetische gegevens.

Alle vier de varianten zijn gecontroleerd op desktop (1440 pixels) en mobiel (375 pixels). Het keuzeoverzicht is ook op 320 pixels gecontroleerd. Stapkeuze, tourknoppen en aanwijsverwijzingen zijn beproefd; de controles vonden geen JavaScript-fouten, netwerkverzoeken of automatische downloads. De varianten maken knopnamen niet vetgedrukt.

De HTML-bestanden zijn een bewaarde momentopname en worden niet automatisch bijgewerkt met de productcode. Ze horen niet in het releasepakket.
