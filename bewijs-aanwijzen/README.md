# Aanwijzen in PR #123

Synthetische browserreproductie van 26 oktober 2026. Alleen bewijsbeelden; deze branch wordt niet naar main gemerged.

- `voor-mobiel.png`: oorspronkelijke PoC variant 4, commit aeef658c, 375×667. Na aanwijzen staat de CSV-knop op y=375..427 achter het tourpaneel op y=352..659 (100% overlap).
- `na-mobiel.png`: implementatie in PR #123, 375×667. De knop staat op y=135..187, het paneel begint op y=352. Geen overlap.
- `na-desktop.png`: dezelfde actieve aanwijzing na vergroten naar 1440×1000.

Alle beelden gebruiken uitsluitend de synthetische referentiefixture. De PR-comment vermeldt de productcommit en de testresultaten.
