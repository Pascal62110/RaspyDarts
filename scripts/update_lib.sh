#!/bin/sh
# Paquets systeme ajoutes depuis l'installation de la borne. Lance au demarrage du jeu
# (raspydarts.py, « Install additional librairies ») : supprime s'il reussit, garde sinon (nouvel
# essai au demarrage suivant, par exemple sans Internet). Une mise a jour qui le contient le fait
# donc executer une fois par chaque borne. Rien n'est fait pour un paquet deja installe.
#
# fonts-noto-color-emoji : les emojis des textes du jeu (include/cemoji.py, coupes des trophees)
# paho-mqtt 2 (module Python) : le jeu et ses serveurs utilisent son API 2 (avant : 1.x). Lance par
# raspydarts.py AVANT la creation du client MQTT et des serveurs de LED
set -e

PAQUETS="fonts-noto-color-emoji"

for paquet in $PAQUETS; do
    if dpkg -s "$paquet" >/dev/null 2>&1; then
        continue
    fi
    # Liste des paquets d'abord : une liste ancienne ne connait pas la version disponible
    sudo DEBIAN_FRONTEND=noninteractive timeout 300 apt-get update -qq || true
    sudo DEBIAN_FRONTEND=noninteractive timeout 600 apt-get install -y -qq "$paquet"
done

# paho-mqtt 2 : seulement s'il manque ou s'il est en 1.x
if ! python3 -c "import paho.mqtt.client as m; m.CallbackAPIVersion" >/dev/null 2>&1; then
    sudo timeout 600 pip3 install --break-system-packages --root-user-action=ignore -q "paho-mqtt>=2"
fi
