<p align="center">
  <img src="images/background_clear.png" alt="RaspyDarts" width="100%">
</p>

<h1 align="center">RaspyDarts</h1>

<p align="center">
  <strong>Transformez votre cible électronique en véritable borne de fléchettes, avec un Raspberry Pi.</strong>
</p>

<p align="center">
  <a href="https://github.com/rmdelcelier/RaspyDarts/releases/latest"><img src="https://img.shields.io/github/v/release/rmdelcelier/RaspyDarts?label=version" alt="Version"></a>
  <a href="licence/glpv3.txt"><img src="https://img.shields.io/badge/licence-GPLv3-blue" alt="Licence GPLv3"></a>
  <img src="https://img.shields.io/badge/langues-FR%20%7C%20EN%20%7C%20DE%20%7C%20ES%20%7C%20IT-green" alt="Langues">
  <img src="https://img.shields.io/badge/jeux-56-orange" alt="56 jeux">
  <a href="https://raspydarts.wordpress.com/"><img src="https://img.shields.io/badge/site-raspydarts.wordpress.com-lightgrey" alt="Site officiel"></a>
</p>

---

RaspyDarts est un logiciel complet de borne de fléchettes électronique pour Raspberry Pi.
Il pilote l'affichage, le son, les rubans de LED, les jeux de lumière et le jeu en réseau,
et transforme une cible du commerce en borne digne d'une salle de jeux.

**Site officiel et documentation : [raspydarts.wordpress.com](https://raspydarts.wordpress.com/)**

## Fonctionnalités

- **56 jeux** répartis en trois familles : classiques, fun et sport
- **5 langues** : français, anglais, allemand, espagnol, italien
- **Jeu en réseau** entre plusieurs bornes, avec serveur maître et statistiques
- **Éclairage synchronisé** : rubans WS281x, cible rétroéclairée, DMX, Philips Hue, afficheur DMD
- **Effets sur événements** : 180, Hat Trick, Bull, White Horse, et bien d'autres
- **Webcam** : photo du joueur sur les événements marquants, envoi optionnel vers Google Drive
- **Thèmes personnalisables** : couleurs, polices, images, sons et vidéos
- **Écran tactile**, boutons physiques, télécommande Bluetooth
- **Scores et records** sauvegardés, joueurs virtuels (PNJ)

## Matériel

**Raspberry Pi** — du Pi Zero 2 au Pi 5.

**Cible électronique** — Décathlon ED110, VDarts, GranBoard, ou n'importe quelle autre cible
électronique. Le câblage des segments se fait via les GPIO, avec extension par MCP23017
si la cible demande plus d'entrées que le Pi n'en offre.

**En option**, selon les effets souhaités : ruban de LED WS281x, afficheur DMD MAX7219,
interface DMX, ampoules Philips Hue, webcam USB, écran tactile.

## Installation

### 1. Récupérer le code

Le jeu s'attend à être installé dans `/pydarts` (le lanceur `RaspyDarts.sh` s'y place au démarrage) :

```bash
sudo git clone https://github.com/rmdelcelier/RaspyDarts.git /pydarts
cd /pydarts
```

### 2. Installer les dépendances

```bash
sudo apt install python3-tk
pip3 install -r requirements.txt
```

### 3. Installer la configuration d'exemple

Les ressources personnalisables (thèmes, polices, images, sons, vidéos) ne sont pas
versionnées dans le dépôt : elles pèsent 387 Mo. Elles sont fournies dans la
[dernière Release](https://github.com/rmdelcelier/RaspyDarts/releases/latest) :

```bash
unzip pydarts_example.zip -d /home/pi/.pydarts
```

### 4. Lancer

```bash
./RaspyDarts.sh
```

Pour le jeu en réseau, `./pydarts_server.sh` sur chaque borne et `./MasterServer.sh`
sur la machine qui centralise les parties.

## Les jeux

<details>
<summary><strong>Classiques (21)</strong></summary>

321_Zlip · Batard · Bermuda_Triangle · Big6 · Bob27 · By_Fives · Color · Cricket ·
High_Score · Ho_One · Kapital · Killer · Kinito · Low_Score · Mickey · Practice ·
Round_the_clock · Scram_Cricket · Shanghai · Slider · Up_Down_Count_Up

</details>

<details>
<summary><strong>Fun (24)</strong></summary>

Bingo · Bulls · Castle · Challenge · Chaos · Conquer · Dragon · GameOfGoose · Hangman ·
Morpion · Othello · Puissance4 · Pursuit · Risk · Robin_Drink · Robin_Strip · Sabotage ·
Simon · Switch · Target · Tower · Treasure · Voleur · Yahtzydarts

</details>

<details>
<summary><strong>Sport (11)</strong></summary>

Balltrap · Baseball · Bowling · Fighters · Football · Golf · Horse · Pingpong ·
Punch-Out · Snooker · Tennis

</details>

## Créer son propre jeu

Un jeu tient dans un seul fichier `.py` déposé dans `games/`. La structure attendue,
les codes de retour et les méthodes à implémenter (`PreDartsChecks`, `PostDartsChecks`,
`EarlyPlayerButton`, `GameStats`, `CheckRecord`) sont documentés dans
**[games/README](games/README)**.

Le plus simple reste de partir d'un jeu existant proche de votre idée et de l'adapter.

## Contribuer

Les contributions sont les bienvenues, quel que soit votre niveau : un nouveau jeu,
une traduction, une correction de bug ou une simple remarque.

**Pour proposer du code :**

1. Forkez le dépôt
2. Créez une branche pour votre modification (`git checkout -b mon-nouveau-jeu`)
3. Committez votre travail
4. Ouvrez une Pull Request

Toute Pull Request est relue et validée avant fusion. La branche `main` est protégée :
elle n'accepte aucune modification directe.

**Pour discuter**, poser une question ou proposer une idée sans écrire de code, rendez-vous
dans l'onglet [Discussions](https://github.com/rmdelcelier/RaspyDarts/discussions).
Pour signaler un bug, ouvrez une [Issue](https://github.com/rmdelcelier/RaspyDarts/issues).

## Licence

RaspyDarts est distribué sous licence **GNU General Public License v3**.
Voir le fichier [LICENSE](LICENSE).
