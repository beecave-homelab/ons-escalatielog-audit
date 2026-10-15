#!/bin/bash
set -euo pipefail

# Script Description: Block tracked files in privacy-sensitive locations.
# Author: beecave-homelab
# Version: 0.2.0
# License: MIT
# Creation Date: 20/09/2026
# Last Modified: 15/10/2026
# Usage: scripts/check-sensitive-paths.sh [--index | --range REVISION_RANGE]

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
mode="index"
revision_range=""

show_help() {
  cat <<EOF
Gebruik: ${0} [OPTIE]

Controleer de hele Git-boom op privacygevoelige paden. Verboden zijn:
  - alles onder escalatielogs/ of exports/ behalve .gitkeep,
  - elk *.xlsx-bestand buiten tests/fixtures/,
  - elk bestand waarvan de naam begint met escalatie_log_controle_.
De vergelijking is hoofdletterongevoelig.

Opties:
  --index                   Controleer de huidige Git-index (standaard).
  --range REVISION_RANGE   Controleer elke commit in een Git-revisiebereik.
  -h, --help                Toon deze hulptekst.

Voorbeelden:
  ${0}
  ${0} --range origin/main..HEAD
EOF
}

log() {
  printf '[privacycontrole] %s\n' "$*"
}

error_exit() {
  printf '[privacycontrole] Fout: %s\n' "$*" >&2
  exit 1
}

shopt -s nocasematch

forbidden_reason() {
  local path="$1"
  case "${path}" in
    escalatielogs/*|exports/*)
      printf 'pad onder escalatielogs/ of exports/'
      ;;
    *.xlsx)
      printf 'xlsx-export buiten tests/fixtures/'
      ;;
    *)
      printf 'bestandsnaam begint met escalatie_log_controle_'
      ;;
  esac
}

is_forbidden_path() {
  local path="$1"
  local base="${path##*/}"

  case "${path}" in
    escalatielogs/.gitkeep|exports/.gitkeep)
      return 1
      ;;
    escalatielogs/*|exports/*)
      return 0
      ;;
  esac

  case "${path}" in
    *.xlsx)
      case "${path}" in
        tests/fixtures/*.xlsx)
          case "${path#tests/fixtures/}" in
            */*)
              return 0
              ;;
          esac
          return 1
          ;;
      esac
      return 0
      ;;
  esac

  case "${base}" in
    escalatie_log_controle_*)
      return 0
      ;;
  esac

  return 1
}

check_index() {
  local path
  local found=false

  while IFS= read -r -d '' path; do
    if is_forbidden_path "${path}"; then
      printf '[privacycontrole] Verboden gevolgd pad: %s (%s)\n' \
        "${path}" "$(forbidden_reason "${path}")" >&2
      found=true
    fi
  done < <(git ls-files -z)

  if [[ "${found}" == true ]]; then
    error_exit "verwijder deze paden uit de Git-index; lokale bestanden mogen blijven staan."
  fi

  log "Git-index bevat geen verboden bestanden."
}

check_commit() {
  local commit="$1"
  local path
  local found=false

  while IFS= read -r -d '' path; do
    if is_forbidden_path "${path}"; then
      printf '[privacycontrole] Commit %s bevat verboden pad: %s (%s)\n' \
        "${commit}" "${path}" "$(forbidden_reason "${path}")" >&2
      found=true
    fi
  done < <(git ls-tree -rz --name-only "${commit}")

  [[ "${found}" == false ]]
}

check_range() {
  local range="$1"
  local commit
  local found=false

  git rev-list "${range}" >/dev/null 2>&1 \
    || error_exit "ongeldig revisiebereik: ${range}"

  while IFS= read -r commit; do
    if ! check_commit "${commit}"; then
      found=true
    fi
  done < <(git rev-list "${range}")

  if [[ "${found}" == true ]]; then
    error_exit "het revisiebereik bevat privacygevoelige paden en mag niet worden gepusht."
  fi

  log "Revisiebereik ${range} bevat geen verboden bestanden."
}

parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --index)
        mode="index"
        shift
        ;;
      --range)
        [[ $# -ge 2 ]] || error_exit "--range vereist een revisiebereik."
        mode="range"
        revision_range="$2"
        shift 2
        ;;
      -h|--help)
        show_help
        exit 0
        ;;
      *)
        error_exit "onbekende optie: $1"
        ;;
    esac
  done
}

main() {
  parse_arguments "$@"
  cd "${REPO_ROOT}"
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    || error_exit "dit script moet in een Git-repository staan."

  if [[ "${mode}" == "range" ]]; then
    check_range "${revision_range}"
  else
    check_index
  fi
}

main "$@"
