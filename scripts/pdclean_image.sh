#!/usr/bin/env bash
#
# pdclean_image.sh
#
# A executer sur le Raspberry Pi AVANT de creer une image a diffuser.
#
# Efface :
#   - les credentials / jetons Google Drive de RaspyDarts (credentials.json, token.json)
#   - les cookies et donnees d'identification de Chromium (connexion Google Cloud, etc.)
#   - les photos et videos capturees par la camera
#   - la base de scores / joueurs (optionnel)
#   - diverses donnees systeme sensibles : historiques, cles SSH d'hote,
#     identifiants Wi-Fi, machine-id... (optionnel)
#
# Usage :
#   sudo ./pdclean_image.sh [--user UTILISATEUR] [--yes] [--keep-scores]
#                           [--system] [--wifi] [--dry-run]
#
#   --user UTILISATEUR  Compte cible (defaut : pi, ou l'utilisateur sudo appelant)
#   --yes               Ne pas demander de confirmation
#   --keep-scores       Conserver la base de scores ~/.pydarts/scores.db
#   --system            Effacer aussi les donnees systeme sensibles
#                       (historiques, cles SSH d'hote, machine-id, journaux)
#   --wifi              Effacer aussi les identifiants Wi-Fi.
#                       ATTENTION : la connexion ACTIVE n'est pas coupee, mais
#                       le Pi ne se reconnectera plus au Wi-Fi apres reboot.
#                       A eviter si vous administrez ce Pi en SSH par Wi-Fi.
#   --dry-run           Afficher ce qui serait supprime sans rien effacer
#
set -u

# ----------------------------------------------------------------------------
# Parametres par defaut
# ----------------------------------------------------------------------------
TARGET_USER="${SUDO_USER:-pi}"
ASSUME_YES=0
KEEP_SCORES=0
CLEAN_SYSTEM=0
CLEAN_WIFI=0
DRY_RUN=0
MACHINE_ID_RESET=0

while [ $# -gt 0 ]; do
    case "$1" in
        --user)        TARGET_USER="$2"; shift 2 ;;
        --user=*)      TARGET_USER="${1#*=}"; shift ;;
        --yes|-y)      ASSUME_YES=1; shift ;;
        --keep-scores) KEEP_SCORES=1; shift ;;
        --system)      CLEAN_SYSTEM=1; shift ;;
        --wifi)        CLEAN_WIFI=1; shift ;;
        --dry-run)     DRY_RUN=1; shift ;;
        -h|--help)
            sed -n '2,28p' "$0"; exit 0 ;;
        *)
            echo "Option inconnue : $1" >&2; exit 1 ;;
    esac
done

# ----------------------------------------------------------------------------
# Verifications de base
# ----------------------------------------------------------------------------
if ! id "$TARGET_USER" >/dev/null 2>&1; then
    echo "ERREUR : l'utilisateur '$TARGET_USER' n'existe pas." >&2
    exit 1
fi

USER_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
if [ -z "$USER_HOME" ] || [ ! -d "$USER_HOME" ]; then
    echo "ERREUR : repertoire personnel introuvable pour '$TARGET_USER'." >&2
    exit 1
fi

PYDARTS_DIR="$USER_HOME/.pydarts"
CONFIG_FILE="$PYDARTS_DIR/pydarts.cfg"

# Le nettoyage systeme / Wi-Fi exige les droits root
if { [ "$CLEAN_SYSTEM" -eq 1 ] || [ "$CLEAN_WIFI" -eq 1 ]; } && [ "$(id -u)" -ne 0 ]; then
    echo "ERREUR : --system / --wifi necessitent les droits root (relancez avec sudo)." >&2
    exit 1
fi

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
# Lit une valeur depuis la section [Camera] du fichier de config INI.
read_cfg() {
    # $1 = cle
    [ -f "$CONFIG_FILE" ] || return 0
    awk -F= -v key="$1" '
        /^\[/{ section=$0 }
        section=="[Camera]" && $1 ~ "^[ \t]*"key"[ \t]*$" {
            sub(/^[ \t]+/, "", $2); sub(/[ \t]+$/, "", $2); print $2; exit
        }' "$CONFIG_FILE"
}

# Supprime un fichier ou repertoire en respectant --dry-run.
remove_path() {
    # $1 = chemin
    local p="$1"
    [ -z "$p" ] && return 0
    if [ -e "$p" ] || [ -L "$p" ]; then
        if [ "$DRY_RUN" -eq 1 ]; then
            echo "  [dry-run] supprimerait : $p"
        else
            rm -rf -- "$p" && echo "  supprime : $p"
        fi
    fi
}

# Vide le contenu d'un repertoire sans supprimer le repertoire lui-meme.
empty_dir() {
    # $1 = repertoire
    local d="$1"
    [ -z "$d" ] && return 0
    [ -d "$d" ] || return 0
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "  [dry-run] viderait le contenu de : $d"
        find "$d" -mindepth 1 -maxdepth 1 -printf '    [dry-run] -> %p\n' 2>/dev/null
    else
        find "$d" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + \
            && echo "  contenu vide : $d"
    fi
}

# ----------------------------------------------------------------------------
# Recapitulatif et confirmation
# ----------------------------------------------------------------------------
PICTURE_PATH="$(read_cfg picture_path)"; PICTURE_PATH="${PICTURE_PATH:-/home/pi/Pictures}"
VIDEO_PATH="$(read_cfg video_path)";     VIDEO_PATH="${VIDEO_PATH:-/home/pi/Videos}"

echo "============================================================"
echo " RaspyDarts - Nettoyage avant creation d'image"
echo "============================================================"
echo " Utilisateur cible : $TARGET_USER ($USER_HOME)"
echo " Photos            : $PICTURE_PATH"
echo " Videos            : $VIDEO_PATH"
echo " Conserver scores  : $([ "$KEEP_SCORES" -eq 1 ] && echo oui || echo NON)"
echo " Nettoyage systeme : $([ "$CLEAN_SYSTEM" -eq 1 ] && echo oui || echo non)"
echo " Effacer Wi-Fi     : $([ "$CLEAN_WIFI" -eq 1 ] && echo 'OUI (pas de reconnexion apres reboot)' || echo non)"
echo " Mode simulation   : $([ "$DRY_RUN" -eq 1 ] && echo oui || echo non)"
echo "============================================================"

if [ "$ASSUME_YES" -ne 1 ] && [ "$DRY_RUN" -ne 1 ]; then
    printf "Ces donnees seront DEFINITIVEMENT effacees. Continuer ? [oui/NON] "
    read -r answer
    case "$answer" in
        oui|OUI|o|O|y|Y|yes) ;;
        *) echo "Annule."; exit 0 ;;
    esac
fi

# ----------------------------------------------------------------------------
# 1. Credentials / jetons Google Drive de RaspyDarts
# ----------------------------------------------------------------------------
echo
echo "[1/6] Credentials Google Drive (RaspyDarts)"
remove_path "$PYDARTS_DIR/credentials.json"
remove_path "$PYDARTS_DIR/token.json"

# ----------------------------------------------------------------------------
# 2. Cookies et donnees d'identification Chromium (connexion Google Cloud...)
# ----------------------------------------------------------------------------
echo
echo "[2/6] Donnees d'identification, cookies, favoris et historique Chromium"

# IMPORTANT : si Chromium tourne, il reecrit ses fichiers (cookies, favoris,
# historique...) depuis la memoire en quittant. On le ferme donc d'abord,
# sinon la suppression est annulee au prochain arret du navigateur.
if [ "$DRY_RUN" -eq 1 ]; then
    if pgrep -u "$TARGET_USER" -x chromium >/dev/null 2>&1 \
       || pgrep -u "$TARGET_USER" -x chromium-browser >/dev/null 2>&1; then
        echo "  [dry-run] fermerait Chromium (en cours d'execution)"
    fi
else
    for proc in chromium chromium-browser chrome google-chrome; do
        pkill -u "$TARGET_USER" -x "$proc" 2>/dev/null
    done
    # On laisse le temps aux processus de se terminer proprement.
    sleep 2
fi

for chromedir in \
    "$USER_HOME/.config/chromium" \
    "$USER_HOME/.config/chromium-browser" \
    "$USER_HOME/.config/google-chrome" \
    "$USER_HOME/snap/chromium/common/chromium"
do
    [ -d "$chromedir" ] || continue
    # On efface les fichiers porteurs d'identite / cookies / favoris /
    # historique / cache dans chaque profil (Default, Profile 1, ...)
    # ainsi qu'au niveau racine.
    for sub in \
        "Cookies" "Cookies-journal" \
        "Login Data" "Login Data-journal" "Login Data For Account" \
        "Web Data" "Web Data-journal" \
        "History" "History-journal" "History Provider Cache" "Visited Links" \
        "Bookmarks" "Bookmarks.bak" \
        "Top Sites" "Top Sites-journal" "Shortcuts" "Shortcuts-journal" \
        "Favicons" "Favicons-journal" \
        "Last Session" "Last Tabs" "Current Session" "Current Tabs" \
        "Network/Cookies" "Network/Cookies-journal" \
        "Network/Trust Tokens" "Network/Network Persistent State" \
        "Sessions" "Session Storage" "Local Storage" "IndexedDB" \
        "Service Worker" "Sync Data" "AutofillStrikeDatabase" \
        "Token Service" "Affiliation Database"
    do
        remove_path "$chromedir/$sub"
        for prof in "$chromedir"/Default "$chromedir"/Profile*; do
            [ -d "$prof" ] && remove_path "$prof/$sub"
        done
    done
    # Caches navigateur
    empty_dir "$chromedir/Default/Cache"
    remove_path "$chromedir/Local State"   # contient des cles de chiffrement
done

# ----------------------------------------------------------------------------
# 3. Photos et videos capturees
# ----------------------------------------------------------------------------
echo
echo "[3/6] Photos et videos"
empty_dir "$PICTURE_PATH"
empty_dir "$VIDEO_PATH"

# ----------------------------------------------------------------------------
# 4. Base de scores / joueurs et logs eventuels
# ----------------------------------------------------------------------------
echo
echo "[4/6] Base de scores et donnees de jeu"
if [ "$KEEP_SCORES" -eq 1 ]; then
    echo "  (conservee a la demande : --keep-scores)"
else
    remove_path "$PYDARTS_DIR/scores.db"
fi

# ----------------------------------------------------------------------------
# 5. Donnees systeme sensibles (optionnel : --system)
# ----------------------------------------------------------------------------
echo
echo "[5/6] Donnees systeme sensibles"
if [ "$CLEAN_SYSTEM" -ne 1 ]; then
    echo "  (ignore : ajoutez --system pour l'activer)"
else
    # Historiques shell (commandes tapees dans LXTerminal = historique bash)
    # et autres traces d'utilisation, pour l'utilisateur cible et root.
    for h in \
        ".bash_history" ".zsh_history" ".sh_history" ".ash_history" \
        ".python_history" ".lesshst" ".wget-hsts" ".viminfo" \
        ".local/share/recently-used.xbel" ".local/share/nano/search_history"
    do
        remove_path "$USER_HOME/$h"
        remove_path "/root/$h"
    done

    # Cles SSH d'hote : seront regenerees au prochain demarrage
    # (chaque Pi doit avoir des cles uniques).
    # NB : ne coupe pas la session SSH en cours.
    for k in /etc/ssh/ssh_host_*; do
        [ -e "$k" ] && remove_path "$k"
    done

    # Identite unique de la machine.
    # On vide /etc/machine-id (systemd en regenere un unique au prochain boot)
    # et on pointe le machine-id de dbus dessus via un lien symbolique, comme
    # sur une installation standard. ATTENTION : tant que le Pi n'a pas
    # redemarre, D-Bus est inutilisable (machine-id vide) -> ne pas relancer
    # d'application, seulement eteindre pour capturer l'image.
    if [ "$DRY_RUN" -ne 1 ]; then
        : > /etc/machine-id 2>/dev/null && echo "  vide : /etc/machine-id"
        rm -f /var/lib/dbus/machine-id
        ln -sf /etc/machine-id /var/lib/dbus/machine-id \
            && echo "  lien : /var/lib/dbus/machine-id -> /etc/machine-id"
        MACHINE_ID_RESET=1
    else
        echo "  [dry-run] viderait : /etc/machine-id (reboot requis ensuite)"
    fi

    # Journaux systeme
    empty_dir "/var/log/journal"
    if [ "$DRY_RUN" -ne 1 ]; then
        find /var/log -type f -name '*.log' -exec truncate -s 0 {} + 2>/dev/null
        echo "  journaux /var/log/*.log vides"
    else
        echo "  [dry-run] viderait les journaux /var/log/*.log"
    fi
fi

# ----------------------------------------------------------------------------
# 6. Identifiants Wi-Fi (optionnel : --wifi)
# ----------------------------------------------------------------------------
echo
echo "[6/6] Identifiants Wi-Fi"
if [ "$CLEAN_WIFI" -ne 1 ]; then
    echo "  (ignore : ajoutez --wifi pour l'activer)"
    echo "  -> conserve : la connexion Wi-Fi reste fonctionnelle apres reboot."
else
    echo "  ATTENTION : la connexion ACTIVE n'est pas coupee maintenant,"
    echo "  mais le Pi ne se reconnectera PLUS au Wi-Fi apres reboot."
    remove_path "/etc/wpa_supplicant/wpa_supplicant.conf"
    remove_path "/boot/wpa_supplicant.conf"
    remove_path "/boot/firmware/wpa_supplicant.conf"
    empty_dir   "/etc/NetworkManager/system-connections"
fi

echo
echo "============================================================"
if [ "$DRY_RUN" -eq 1 ]; then
    echo " Simulation terminee (aucune donnee effacee)."
else
    echo " Nettoyage termine. L'image peut etre creee."
fi
echo "============================================================"

if [ "$MACHINE_ID_RESET" -eq 1 ]; then
    echo
    echo "************************************************************"
    echo " IMPORTANT : machine-id reinitialise."
    echo " D-Bus est inutilisable dans cette session (machine-id vide)."
    echo " NE RELANCEZ PAS RaspyDarts maintenant."
    echo " Eteignez le Pi pour capturer l'image :"
    echo "     sudo poweroff"
    echo " Un nouvel identifiant unique sera genere au prochain demarrage."
    echo "************************************************************"
fi
