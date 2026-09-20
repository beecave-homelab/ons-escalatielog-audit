#!/bin/bash
set -euo pipefail

# Script Description: Prepare a Codex Cloud environment for this repository.
# Author: beecave-homelab
# Version: 0.1.0
# License: MIT
# Creation Date: 20/09/2026
# Last Modified: 20/09/2026
# Usage: scripts/setup-codex-cloud.sh [OPTIONS]

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

skip_browser=false
run_checks=false

print_ascii_art() {
  cat <<'EOF'
╔═╗ ╔═╗ ╔╦╗ ╔═╗ ═╗ ╦
║   ║ ║  ║║ ║╣  ╔╩╦╝
╚═╝ ╚═╝ ═╩╝ ╚═╝ ╩ ╚═
        CLOUD SETUP
EOF
}

show_help() {
  cat <<EOF
Gebruik: ${0} [OPTIES]

Richt een Linux Codex Cloud-omgeving in voor deze repository. Het script
installeert uv wanneer dat ontbreekt, synchroniseert uv.lock en zorgt dat de
Playwright-tests een Chromium-browser kunnen starten.

Opties:
  --check          Voer na installatie alle repositorycontroles uit.
  --skip-browser   Sla installatie van een browser over.
  -h, --help       Toon deze hulptekst.

Voorbeelden:
  ${0}
  ${0} --check
  ${0} --skip-browser --check
EOF
}

log() {
  printf '[setup] %s\n' "$*"
}

error_exit() {
  printf '[setup] Fout: %s\n' "$*" >&2
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

run_as_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  elif command_exists sudo; then
    sudo "$@"
  else
    error_exit "Rootrechten of sudo zijn nodig om systeempakketten te installeren."
  fi
}

install_uv() {
  if command_exists uv; then
    log "uv is al beschikbaar: $(uv --version)"
    return
  fi

  command_exists curl || error_exit "curl ontbreekt; installeer curl en probeer opnieuw."
  log "Installeer uv via het officiële installatiescript."
  curl -LsSf https://astral.sh/uv/install.sh | sh

  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  command_exists uv || error_exit "uv is geïnstalleerd, maar niet vindbaar via PATH."
}

browser_available() {
  local browser
  for browser in google-chrome google-chrome-stable microsoft-edge \
    microsoft-edge-stable chromium chromium-browser; do
    if command_exists "${browser}"; then
      log "Browser gevonden: $(command -v "${browser}")"
      return 0
    fi
  done
  return 1
}

install_browser() {
  if browser_available; then
    return
  fi

  if command_exists apt-get; then
    log "Installeer Chromium en benodigde bibliotheken via apt."
    run_as_root apt-get update
    if run_as_root apt-get install -y chromium; then
      browser_available || error_exit "Chromium is geïnstalleerd maar niet vindbaar."
      return
    fi
    log "Het apt-pakket chromium was niet beschikbaar; probeer chromium-browser."
    run_as_root apt-get install -y chromium-browser
    browser_available || error_exit "Geen bruikbare Chromium-installatie gevonden."
    return
  fi

  log "Geen apt gevonden; probeer de Playwright-browser te installeren."
  uv run playwright install chromium
}

sync_dependencies() {
  log "Synchroniseer de vastgezette ontwikkelafhankelijkheden."
  uv sync --locked
}

run_repository_checks() {
  log "Voer documentatie-, lint- en regressiecontroles uit."
  uv run mdformat --check README.md CHANGELOG.md AGENTS.md docs
  uv run djlint . --check
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest --cov=tests --cov-report=term-missing:skip-covered
}

parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --check)
        run_checks=true
        shift
        ;;
      --skip-browser)
        skip_browser=true
        shift
        ;;
      -h|--help)
        show_help
        exit 0
        ;;
      *)
        error_exit "Onbekende optie: $1"
        ;;
    esac
  done
}

main() {
  parse_arguments "$@"
  print_ascii_art

  cd "${REPO_ROOT}"
  install_uv
  sync_dependencies

  if [[ "${skip_browser}" == false ]]; then
    install_browser
  else
    log "Browserinstallatie overgeslagen."
  fi

  if [[ "${run_checks}" == true ]]; then
    run_repository_checks
  fi

  log "Codex Cloud-omgeving is gereed."
}

main "$@"
