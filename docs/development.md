# Ontwikkelen

Deze pagina is bedoeld voor mensen die aan Ons Escalatielog Audit bijdragen. De
webui zelf heeft geen buildstap of runtime-afhankelijkheden. De
ontwikkelcontroles gebruiken [uv](https://docs.astral.sh/uv/), Python 3.10 of
nieuwer en een lokale installatie van Chrome, Edge of Chromium.

## Ontwikkelomgeving inrichten

Installeer de vastgezette ontwikkelafhankelijkheden vanuit de hoofdmap van de
repository:

```bash
uv sync --locked
```

## Controles uitvoeren

Voer vóór het indienen van een wijziging deze controles uit:

```bash
uv run mdformat --check README.md CHANGELOG.md AGENTS.md docs
uv run djlint . --check
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run pytest --cov=tests --cov-report=term-missing:skip-covered
```

Formatteer gewijzigde HTML met `uv run djlint . --reformat`. djLint formatteert
de HTML-structuur, maar laat de compacte CSS en JavaScript in de ingebedde
`<style>`- en `<script>`-blokken ongemoeid.

De coverage-controle volgt ook de greenlets van Playwright en faalt onder 85%.
Deze dekking meet alleen de Python-testcode en zegt niets over de JavaScript-code
van de webui.

## Synthetische testdata

De repository bevat een standaard testexport met 2.000 verzonnen regels. Maak
deze met dezelfde seed opnieuw via:

```bash
uv run python tests/generate_synthetic_escalatielog.py \
  --output tests/fixtures/synthetic-escalatielog.xlsx \
  --rows 2000 \
  --seed 20260918
```

Dezelfde seed levert byte-voor-byte hetzelfde bestand op. De pytest-suite
controleert dit bestand in de echte webui en maakt daarnaast tijdelijk een
kleiner rapport om de tabelopmaak op scherm- en printbreedte te controleren.

## Bescherming tegen datalekken via Git

Bestanden onder `escalatielogs/` en `exports/` kunnen persoonsgegevens bevatten
en mogen daarom nooit door Git worden gevolgd. Alleen `.gitkeep` is daar
toegestaan. Synthetische testbestanden horen onder `tests/fixtures/`.

Activeer na het klonen eenmalig de meegeleverde lokale Git-hooks:

```bash
git config core.hooksPath .githooks
```

De pre-commit-hook controleert de Git-index. De pre-push-hook controleert iedere
te pushen commit, dus ook een bestand dat in een latere commit alweer is
verwijderd. GitHub Actions voert dezelfde controle opnieuw uit voor pushes en
pull requests. Controleer de huidige index ook handmatig met:

```bash
scripts/check-sensitive-paths.sh --index
```

Deze controles zijn een aanvullende beveiliging. Ze vervangen niet de
verplichte controle van staged bestanden vóór iedere commit en van de volledige
wijzigingsreeks vóór iedere push.
