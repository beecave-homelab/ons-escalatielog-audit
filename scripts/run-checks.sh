#!/bin/bash
set -euo pipefail

# Script Description: Run the shared list of development checks.
# Author: beecave-homelab
# Version: 0.1.0
# License: MIT
# Creation Date: 15/10/2026
# Last Modified: 15/10/2026
# Usage: scripts/run-checks.sh

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

show_help() {
  cat <<EOF
Gebruik: ${0}

Voer de gedeelde lijst met ontwikkelcontroles uit; dezelfde lijst draait in CI
en via scripts/install-dependencies.sh --check. Stopt bij de eerste fout.

Opties:
  -h, --help   Toon deze hulptekst.
EOF
}

step() {
  local title="$1"
  shift
  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    printf '::group::%s\n' "${title}"
  fi
  printf '[controles] %s\n' "${title}"
  "$@"
  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    printf '::endgroup::\n'
  fi
}

main() {
  case "${1:-}" in
    -h|--help)
      show_help
      exit 0
      ;;
    "")
      ;;
    *)
      printf '[controles] Fout: onbekende optie: %s\n' "$1" >&2
      exit 1
      ;;
  esac

  cd "${REPO_ROOT}"

  step "Controleer versies en changelog" \
    uv run python scripts/check_release_version.py
  step "Controleer privacygevoelige paden" \
    scripts/check-sensitive-paths.sh --index
  step "Controleer productiedocumentatie" \
    uv run python scripts/check-production-docs.py --revision HEAD
  step "Controleer Markdown-opmaak" \
    uv run mdformat --check README.md CHANGELOG.md AGENTS.md docs
  step "Controleer HTML-opmaak" \
    uv run djlint . --check
  step "Controleer Python-lint" \
    uv run ruff check .
  step "Controleer Python-opmaak" \
    uv run ruff format --check .
  step "Controleer SVG-tekst binnen viewBox" \
    uv run bash scripts/check-svg-text-bounds.sh
  step "Voer tests uit met coverage" \
    uv run pytest --cov=tests --cov-report=term-missing:skip-covered

  printf '[controles] Alle controles zijn geslaagd.\n'
}

main "$@"
