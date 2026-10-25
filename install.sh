#!/bin/bash
# ==============================================================================
# RaspyDarts - Installation depuis GitHub sur un Raspberry Pi neuf
# ==============================================================================
#
# Sur Raspberry Pi OS 13 (Trixie) avec bureau, depuis le compte qui fera tourner
# RaspyDarts (pas root) :
#
#   curl -fsSL https://raw.githubusercontent.com/rmdelcelier/RaspyDarts/main/install.sh | sudo bash
#
# Options (apres "sudo bash -s --") :
#   --version <ref>   branche, etiquette ou commit a installer (defaut : main)
#   --sans-exemple    ne pas installer la configuration d'exemple (~/.raspydarts)
#   --oui             repondre oui aux confirmations
#
#   curl -fsSL https://raw.githubusercontent.com/rmdelcelier/RaspyDarts/main/install.sh | sudo bash -s -- --oui
#
# Telecharge le code (environ 1 Go) et la configuration d'exemple de la release
# "exemple" (environ 400 Mo), puis lance scripts/install_on_pi.sh, le meme script
# que l'installation depuis le poste de developpement (install_raspydarts.ps1).
# ==============================================================================

set -u

REPO="rmdelcelier/RaspyDarts"
REF="main"
WITH_EXAMPLE=1
ASSUME_YES=0
EXAMPLE_URL="https://github.com/$REPO/releases/download/exemple/raspydarts_example.zip"
WORK_DIR=/var/tmp/raspydarts-install    # pas /tmp : un tmpfs trop petit pour le code
# Code + exemple telecharges, plus les 4 Go demandes par install_on_pi.sh
MIN_FREE_KB=5600000

die() { printf '\n  \033[31m[ERREUR]\033[0m %s\n\n' "$1"; exit 1; }
ok()  { printf '  \033[32m[+]\033[0m %s\n' "$1"; }

while [ $# -gt 0 ]; do
    case "$1" in
        --version)      [ $# -ge 2 ] || die "--version : indiquez une branche, une etiquette ou un commit."
                        REF="$2"; shift ;;
        --sans-exemple) WITH_EXAMPLE=0 ;;
        --oui)          ASSUME_YES=1 ;;
        *)              die "Option inconnue : $1" ;;
    esac
    shift
done

printf '\n  \033[36m========================================================\n'
printf '    RaspyDarts - Telechargement depuis GitHub (%s)\n' "$REF"
printf '  ========================================================\033[0m\n\n'

[ "$(id -u)" -eq 0 ] || die "A lancer avec sudo : curl -fsSL ... | sudo bash"
[ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ] \
    || die "A lancer avec sudo depuis le compte qui fera tourner RaspyDarts, pas en root."
command -v curl >/dev/null || die "curl absent."

mkdir -p "$WORK_DIR" || die "Impossible de creer $WORK_DIR"
FREE_KB=$(df --output=avail -k "$WORK_DIR" | tail -1 | tr -d ' ')
[ "$FREE_KB" -ge "$MIN_FREE_KB" ] \
    || die "Espace libre insuffisant : $((FREE_KB / 1024)) Mo ($((MIN_FREE_KB / 1024)) Mo necessaires)."
trap 'rm -rf "$WORK_DIR"' EXIT

CODE="$WORK_DIR/raspydarts.tar.gz"
printf '  Code de RaspyDarts (environ 1 Go)...\n'
curl -fL --retry 3 -o "$CODE" "https://codeload.github.com/$REPO/tar.gz/$REF" \
    || die "Telechargement du code echoue ($REF existe-t-il ?)."
ok "Code telecharge ($(( $(stat -c %s "$CODE") / 1048576 )) Mo)"

# Le script d'installation du Pi, pris dans le code telecharge (meme version)
tar -xzf "$CODE" -C "$WORK_DIR" --wildcards --strip-components=2 '*/scripts/install_on_pi.sh' \
    && [ -f "$WORK_DIR/install_on_pi.sh" ] || die "scripts/install_on_pi.sh absent du code ($REF)."

HOME_ARCHIVE="-"
if [ "$WITH_EXAMPLE" = "1" ]; then
    HOME_ARCHIVE="$WORK_DIR/raspydarts_example.zip"
    printf '\n  Configuration d exemple (environ 400 Mo)...\n'
    curl -fL --retry 3 -o "$HOME_ARCHIVE" "$EXAMPLE_URL" || die "Telechargement de l'exemple echoue."
    ok "Exemple telecharge ($(( $(stat -c %s "$HOME_ARCHIVE") / 1048576 )) Mo)"
fi

YES=""
[ "$ASSUME_YES" = "1" ] && YES="--yes"
# Les questions se lisent au clavier : l'entree de ce script est le tuyau de curl
if [ -z "$YES" ] && [ -r /dev/tty ] && : < /dev/tty 2>/dev/null; then
    bash "$WORK_DIR/install_on_pi.sh" "$CODE" "$HOME_ARCHIVE" < /dev/tty
else
    [ -n "$YES" ] || printf '  (pas de clavier : reponses oui)\n'
    bash "$WORK_DIR/install_on_pi.sh" "$CODE" "$HOME_ARCHIVE" --yes
fi
