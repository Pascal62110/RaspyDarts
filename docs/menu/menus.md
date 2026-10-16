# Fichier de menus de RaspyDarts (`menus.yaml`)

> **Statut : spécification, version 1 (brouillon à valider).** Rien de ceci n'est encore
> programmé. Ce document décrit ce que le moteur de menus saura lire ; il sert de référence
> au jeu (Python), au configurateur de la page GitHub (JavaScript) et à ceux qui écrivent
> leur fichier à la main.

## 1. Ce que le fichier décrit, et ce qu'il ne décrit pas

Le fichier décrit **les menus** : menu principal, Divers, Paramètres, choix de la catégorie et
du jeu, options, joueurs, assistant, ainsi que les panneaux de favoris. Pour chacun : quels
boutons, dans quel ordre, où, avec quel aspect, quels raccourcis, et ce qu'ils déclenchent.

Il **ne décrit pas** les écrans de jeu (tableaux de scores, cibles, animations), dessinés par
chaque jeu de `games/` : ils gardent leur fonctionnement et le thème (`Colorset.cfg`).

Il **ne peut pas inventer d'action** : chaque bouton déclenche une action connue du jeu
(liste au §8). Un fichier mal écrit ne peut donc rien faire d'autre que mal afficher un menu.

## 2. Emplacements et priorité

Du plus prioritaire au moins prioritaire :

| Fichier | Rôle |
|---|---|
| `~/.raspydarts/menus.yaml` | le fichier de l'utilisateur (fait par la page GitHub, ou à la main) |
| `~/.raspydarts/themes/<thème>/menus.yaml` | le fichier fourni avec le thème choisi |
| `/raspydarts/menus/defaults.yaml` | les menus par défaut, livrés avec le jeu |

Un fichier ne contient que ce qu'il change ; le reste vient du niveau suivant. Les règles de
fusion :

- Les **dictionnaires** se fusionnent clé par clé (`defaults`, `styles`, un menu…).
- Une **liste de boutons** (`buttons:`) donnée par un fichier **remplace** celle du niveau
  suivant, en entier. Pour ne changer qu'un bouton sans réécrire la liste, utiliser
  `button_changes:` (§7.3).
- Une valeur `null` (ou `~`) efface la valeur du niveau suivant.

Un fichier se déposait déjà sur la carte SD comme `raspydarts.cfg` : le service
`raspydarts-boot` copie au démarrage le contenu d'un dossier `.raspydarts` déposé sur la
partition `bootfs` dans `~/.raspydarts`. `menus.yaml` et le thème personnel s'y déposent
donc de la même façon.

## 3. Erreurs

- **Fichier illisible** (YAML mal formé) : il est ignoré en entier, le menu s'affiche avec le
  niveau suivant, un message bref s'affiche une fois au démarrage et le journal donne le
  fichier, la ligne et la colonne.
- **Valeur invalide** (couleur inconnue, action inconnue, image absente…) : seule cette
  valeur est ignorée (valeur du niveau suivant), avec une ligne dans le journal.
- **Clé inconnue** : ignorée, avec une ligne dans le journal (une faute de frappe se voit).
- La borne reste **toujours** utilisable : `defaults.yaml` ne peut pas être remplacé en
  entier, un menu sans aucun bouton visible garde ceux du niveau suivant.

## 4. Unités et résolution

```yaml
resolution: auto          # ou [1024, 600], [1920, 1080]…
```

- `auto` : toutes les positions et tailles sont des **fractions de l'écran**, de `0` à `1`
  (`x: 0.5` = milieu, `width: 0.25` = un quart de la largeur). Le même fichier convient à
  toutes les résolutions.
- `[largeur, hauteur]` : positions et tailles en **pixels de cette résolution**. Sur un écran
  différent, elles sont mises à l'échelle (x et largeurs par le rapport des largeurs, y et
  hauteurs par celui des hauteurs). Une valeur peut quand même être donnée en fraction en
  l'écrivant en pourcentage : `x: 50%`.
- Les **tailles de texte** sont toujours des fractions de la **hauteur** de l'écran
  (`size: 0.045`) ou, avec une résolution de référence, des pixels de cette hauteur.

Résolutions de référence pour les essais : **1024×600** (Raspberry Pi de développement,
écran 7") et **1920×1080** (borne).

## 5. Valeurs communes

- **Couleur** : nom d'une couleur du thème (`menu-selected`, `menu-text`… : celles de
  `Colorset.cfg`), ou `'#RRGGBB'`, ou `'#RRGGBBAA'` (avec transparence). Les guillemets
  sont obligatoires pour `#` (sinon YAML y voit un commentaire).
- **Image** : chemin cherché, dans l'ordre, dans le dossier du thème, dans `~/.raspydarts`,
  puis dans `/raspydarts/images`. PNG ou JPG.
- **Police** : nom de fichier (`Kamikzon.ttf`) cherché dans `fonts/` du thème, dans
  `~/.raspydarts/fonts`, puis dans `/raspydarts/fonts`. Absente : la police du thème.
- **Texte affiché** :
  - une clé de traduction (`game-type-local`) : traduite dans la langue du jeu ;
  - un texte direct (`Mes parties`) : affiché tel quel si ce n'est pas une clé connue ;
  - un texte par langue : `{fr: Mes parties, en: My games, de: Meine Spiele}` (langue du
    jeu, sinon `en`, sinon la première donnée).
- **Touche** (raccourcis, navigation) : `F1`…`F12`, une lettre ou un chiffre (`'l'`,
  `'1'`), `enter`, `space`, `escape`, `backspace`, `tab`, `up`, `down`, `left`, `right`, ou
  un bouton de la borne : `btn:validate`, `btn:back`, `btn:cancel`, `btn:up`, `btn:down`,
  `btn:left`, `btn:right`, `btn:plus`, `btn:minus`, `btn:nextplayer`, `btn:game`, ou une
  fléchette : `dart:S20`, `dart:SB`, `dart:DB`… `none` : aucun. Comme raccourci, `escape`
  désigne toutes les touches `back` (§9).

## 6. Structure générale

```yaml
version: 1
resolution: auto
defaults: {…}            # réglages de tous les menus (§7.1)
styles: {…}              # styles de boutons nommés (§7.2)
navigation: {…}          # touches de navigation (§9)
encoder: {…}             # encodeur rotatif USB (§10)
virtual_keyboard: {…}    # clavier à l'écran (§11)
menus: {…}               # les menus (§7.3)
```

Toutes les sections sont facultatives.

### 6.1 Premier écran (`start`)

```yaml
start: main               # le menu principal (défaut)
```

| Valeur | Premier écran |
|---|---|
| `main` | le menu principal |
| `local_game` | le choix des joueurs d'une partie simple (comme l'option « Ne pas afficher le menu principal ») |
| `category:<nom>` | les joueurs, puis directement la liste des jeux de cette catégorie |
| `game:<Nom>` | les joueurs, puis directement les options de ce jeu |

Retour depuis les joueurs mène alors au menu principal. Les options du jeu « Ne pas afficher
le menu principal » et « Afficher uniquement les jeux favoris » (Paramètres > Personnalisation
> Général) restent prioritaires : un fichier ne peut pas les contredire.

Un bouton peut aussi sauter des écrans : `category:<nom>` et `game:<Nom>` dans le menu
principal passent par les joueurs puis vont directement à la liste ou aux options. Retour
depuis ces écrans revient aux joueurs (les écrans sautés ne sont pas réaffichés).

## 7. Aspect

### 7.1 `defaults` et cascade

L'aspect se décide à trois niveaux, chacun ne précisant que ce qui change :
**`defaults`** (tous les menus) → **le menu** → **le bouton**.

```yaml
defaults:
  background: images/background/menu.png   # fond du menu (§7.3 bis : image, couleur ou bloc)
  layout: list                             # disposition des boutons (§7.4)
  style: classic                           # style des boutons (§7.2)
  title:    {font: Kamikzon.ttf, size: 0.06, color: menu-header, position: top}
  subtitle: {size: 0.035, color: menu-text, position: below_title}
  shortcuts: {show: true, format: '{key}', color: menu-shortcut, position: left}
```

`shortcuts.show: false` n'affiche plus les F1, F2… (ils restent actifs). `format` permet
`'> '` ou `'[{key}]'` (remplace l'ancien réglage `shortcuts` de `Colorset.cfg`).

### 7.2 Styles et états

```yaml
styles:
  classic:
    shape: rounded           # rounded | rectangle | pill | none (texte seul)
    radius: 12               # arrondi (pixels de référence ou fraction de la hauteur du bouton)
    background:              # fond du bouton (§7.3 bis)
      color: menu-buttons
      image: null
    border: {width: 0, color: menu-border}
    shadow: false
    text: {font: null, size: 0.045, color: menu-text, align: center, position: center,
           offset: [0, 0], shadow: false, bold: false}
    icon: {position: left, size: 0.7, fit: contain}   # taille relative à la hauteur du bouton
    # États : chacun ne précise que ce qui change par rapport à l'état normal
    selected: {background: {color: menu-selected}, text: {color: menu-text-white}}
    disabled: {background: {color: '#808080'}, text: {color: '#C0C0C0'}}
    pressed:  {scale: 0.96}
```

- `text.position` : `center`, `top`, `bottom`, `left`, `right` (dans le bouton) ;
  `offset` : décalage `[x, y]`.
- `scale` (dans un état) : agrandit ou réduit le bouton autour de son centre.
- Un bouton ou un menu peut prendre un style nommé (`style: tile`) **et/ou** changer des
  propriétés directement (`background: {color: '#C0392B'}`, `selected: {…}`,
  `text: {size: 0.05}`).
- `color: …` seul est un raccourci de `background: {color: …}`.

### 7.3 bis Fonds (boutons et menus)

Le même bloc décrit le fond d'un bouton (dans un style, un état ou un bouton) et le fond
d'un menu (`background` d'un menu ou de `defaults`) :

```yaml
background:
  color: menu-buttons          # couleur de fond, sous l'image (null : transparent)
  image: images/buttons/tile.png
  fit: stretch                 # comment l'image remplit la place (ci-dessous)
  position: center             # center | top | bottom | left | right | top_left | top_right
                               # | bottom_left | bottom_right
  offset: [0, 0]               # décalage depuis cette position
  size: [1.0, 1.0]             # taille de l'image, en part du bouton (fit: center)
  opacity: 1.0                 # 0 (invisible) à 1
  slice: 12                    # fit: slice : largeur des bords gardés intacts
```

| `fit` | Rendu |
|---|---|
| `stretch` | l'image occupe **tout** le bouton, déformée si besoin |
| `cover` | l'image occupe tout le bouton **sans déformation**, ce qui dépasse est coupé |
| `contain` | l'image entière **sans déformation**, centrée (ou selon `position`), des bandes de `color` comblent le reste |
| `center` | l'image à la taille `size`, placée selon `position` et `offset` |
| `tile` | l'image répétée en mosaïque |
| `slice` | l'image découpée en 9 (« 9-slice ») : les coins gardent leur taille, les bords et le centre s'étirent ; pour des boutons de toutes tailles avec un cadre net |

- L'image est coupée selon la **forme** du bouton (coins arrondis, pilule).
- Écritures courtes : `background: images/x.png` (image, `fit: stretch`) ;
  `background: '#123456'` ou `background: menu-buttons` (couleur seule).
- Chaque état (`selected`, `disabled`, `pressed`) peut changer tout ou partie du fond :
  `selected: {background: {image: images/buttons/tile_on.png}}`.
- Un fond de menu se règle pareil ; `fit: cover` est conseillé (aucune déformation, quelle
  que soit la résolution).

### 7.3 Menus et boutons

```yaml
menus:
  main:
    title: game-type-menu
    subtitle: null
    background: images/background/main.png
    layout: tiles
    columns: 3
    style: tile
    buttons:
      - id: play                     # facultatif : par défaut, l'action
        action: local_game
        text: game-type-local
        icon: images/icons/target.png
        shortcut: [F1, l]
        exhibition: true             # visible en mode exposition (défaut : false)
      - action: menu:miscellaneous
        place: {x: 0.92, y: 0.04, width: 0.06, height: 0.08}   # placement libre (§7.5)
        style: classic
      - action: shutdown
        confirm: realy-stop          # demande de confirmation (texte)
        space_before: 1.5            # écart au-dessus, en hauteurs de bouton (dispositions auto)
```

Propriétés d'un menu, en plus de l'aspect : `title`, `subtitle`, `show_version` (version
en bas à droite du fond), `info` (informations écrites sur le fond : `ips`, `rpi_version`,
`version`), `remember` (`true` : le menu rouvre sur le dernier bouton choisi de sa liste).

Propriétés d'un bouton :

| Clé | Rôle |
|---|---|
| `id` | nom du bouton dans le menu (par défaut : l'action) |
| `action` | ce qu'il déclenche (§8) — **obligatoire** |
| `text`, `icon` | texte et icône (par défaut : ceux de l'action) |
| `shortcut` | touche ou liste de touches (défaut : aucun) |
| `exhibition` | visible en mode exposition (défaut `false`, sauf `local_game`, `trophies`, `gallery`) |
| `visible` | `false` le cache (il reste joignable par son raccourci) |
| `confirm` | texte d'une confirmation Oui/Non avant l'action |
| `place` | placement libre (§7.5) ; sinon placé par la disposition du menu |
| `footer` | bouton du bas de l'écran : `left`, `center` ou `right` (comme Retour, Enregistrer) |
| `logo` | image du dossier `images/logos_menu` du thème (disposition `tiles` du style `classic`) ; un dossier de ce nom contenant plusieurs images : l'une d'elles au hasard |
| `requires` | condition d'affichage : `favorite_games` (seulement s'il existe des jeux favoris) |
| `dmd` | texte envoyé sur l'afficheur DMD quand le bouton est sélectionné |
| `order` | rang dans l'ordre logique (§9), par défaut sa place dans la liste |
| `space_before` | écart au-dessus (dispositions `list` et `grid`) |
| `style`, et toute propriété de style | aspect de ce bouton seul |

Changer un bouton sans réécrire la liste (fichier de l'utilisateur ou du thème) :

```yaml
menus:
  main:
    button_changes:
      gallery: {visible: false}
      play: {text: {fr: Jouer, en: Play}, shortcut: [F1, enter]}
```

### 7.4 Dispositions automatiques

```yaml
    layout: list           # list | grid | tiles
    area: {x: 0.25, y: 0.18, width: 0.5, height: 0.75}   # zone où se placent les boutons
    columns: 1             # grid et tiles (list = 1)
    button_size: {width: 1.0, height: 0.09}   # largeur : fraction de la colonne ; hauteur : de l'écran
    gap: {x: 0.02, y: 0.015}
    align: center          # center | top (si les boutons ne remplissent pas la zone)
    overflow: pages        # pages | scroll (quand ils ne tiennent pas)
```

- **`list`** : une colonne, les boutons les uns sous les autres.
- **`grid`** : `columns` colonnes, rangées de gauche à droite puis de haut en bas ; même
  aspect que `list`.
- **`tiles`** : comme `grid`, mais boutons carrés ou rectangulaires plus grands, l'icône
  au-dessus du texte (`text.position: bottom` par défaut).

**Règle de placement** (identique dans le jeu et dans le configurateur, §12) : les boutons
non placés librement et visibles sont rangés dans l'ordre de la liste, ligne par ligne ; la
hauteur d'une ligne est `button_size.height` ; `space_before` ajoute un écart avant la ligne
de ce bouton ; l'ensemble est centré horizontalement dans `area`, et verticalement si
`align: center`. Le détail des calculs (arrondis compris) est donné au §12.

### 7.5 Placement libre

```yaml
        place: {x: 0.92, y: 0.04, width: 0.06, height: 0.08, anchor: top_left}
```

`x`, `y` : position du point d'ancrage (`top_left` par défaut, ou `center`, `top_right`,
`bottom_left`, `bottom_right`). Un bouton placé librement ne prend pas de place dans la
disposition automatique : les autres se rangent comme s'il n'existait pas.

## 8. Actions

Une action par bouton. Le jeu refuse une action inconnue (§3).

**Menu principal**

| Action | Effet (aujourd'hui) |
|---|---|
| `local_game` | partie simple (F1) |
| `network_join` | rejoindre une partie en réseau (F2) |
| `network_create` | créer une partie en réseau (F3) |
| `trophies` | trophées et progression (F5) |
| `gallery` | galerie des photos et vidéos (F6) |
| `infos` | informations (F9) |
| `restart` | relancer RaspyDarts (F11) |
| `desktop` | revenir sur le bureau (F12) |
| `shutdown` | éteindre le Raspberry Pi (Échap, avec confirmation) |

**Divers**

| Action | Effet |
|---|---|
| `favorite_players` | prénoms favoris |
| `favorite_games` | jeux favoris |
| `favorite_servers` | serveurs favoris |
| `customization` | personnalisation |
| `animations` | animations des LED |
| `players_bank` | banque de prénoms |
| `backups` | sauvegardes |
| `exhibition` | mode exposition |
| `update` | vérifier les mises à jour |

**Paramètres**

| Action | Effet |
|---|---|
| `setup_buttons` | boutons |
| `setup_pins_leds` | broches des LED |
| `setup_leds` | LED de la cible |
| `setup_segment_colors` | couleurs des segments |
| `setup_camera` | webcam |
| `setup_encoder` | encodeur (nouveau, §10) |
| `test_buttons`, `test_target`, `test_toys` | tests |
| `reset` | réinitialisation |

**Générales**

| Action | Effet |
|---|---|
| `menu:<id>` | ouvre le menu `<id>` ; un menu imbriqué s'écrit `menu:settings/display` |
| `category:<nom>` | ouvre la liste des jeux de la catégorie `classic`, `fun`, `sport`, `favorites` |
| `game:<Nom>` | partie de ce jeu : joueurs, puis directement ses options (ex. `game:Cricket`, `game:High_Score`) ; un jeu inconnu est ignoré |
| `favorite:fav<N>` | lance le favori n° N (§13) |
| `back` | revient à l'écran précédent |

Les menus livrés : `main`, `miscellaneous`, `settings`, `categories`, et les menus dont les
boutons sont fabriqués par le jeu (§7.6).

### 7.6 Menus dont le jeu fournit les boutons

`games` (liste des jeux d'une catégorie), `options` (options d'un jeu), `players` (joueurs),
`wizard` (assistant de configuration) : leurs boutons viennent du jeu, le fichier n'en règle
que l'aspect (`background`, `layout`, `columns`, `style`, `title`…), pas la liste. Un
`buttons:` y est ignoré (journal).

## 9. Navigation

```yaml
navigation:
  up: [up, btn:up]
  down: [down, btn:down]
  left: [left, btn:left]
  right: [right, btn:right]
  next: [tab]              # ordre logique (comme l'encodeur)
  previous: []
  validate: [enter, space, btn:validate]
  back: [escape, backspace, btn:back]
```

Deux logiques :

- **Flèches (haut, bas, gauche, droite) : géométrie.** On va au bouton le plus proche dans la
  direction demandée, d'après la position réelle des boutons à l'écran (placement libre
  compris). Candidats : les boutons dont le centre est du bon côté du centre du bouton
  actuel. Note de chacun : `distance selon l'axe + 2 × écart perpendiculaire` ; le plus bas
  l'emporte (égalité : le premier dans l'ordre logique). Aucun candidat : on fait le tour,
  vers le bouton le plus éloigné du côté opposé ayant le plus petit écart perpendiculaire.
- **`next` / `previous` et l'encodeur : ordre logique.** L'ordre des boutons dans le fichier
  (ou `order:`), en passant d'une ligne à la suivante, et en faisant le tour au bout.

`validate` déclenche le bouton sélectionné ; `back` revient à l'écran précédent. Un
raccourci (§7.3) déclenche son bouton directement, même s'il n'est pas sélectionné.

Avec la souris ou au doigt, un clic déclenche le bouton touché.

## 10. Encodeur rotatif

```yaml
encoder:
  device: auto             # auto = celui choisi dans Paramètres > Encodeur, ou son nom
  turn: [previous, next]   # sens de rotation : [sens inverse, sens horaire]
  press: validate
  long_press: back         # appui long (secondes : long_press_time)
  long_press_time: 0.6
```

L'encodeur USB est lu **à part** (son périphérique est réservé au jeu) : ses touches ne
passent pas par le clavier, il n'est jamais confondu avec lui, et l'appui long existe. Il
suit l'**ordre logique** (§9). L'écran Paramètres > Encodeur le détecte : « Tournez
l'encodeur ».

## 11. Clavier à l'écran

```yaml
virtual_keyboard:
  mode: touch              # touch (seulement au doigt) | always | never
  style: classic
```

`touch` : un champ de saisie touché **au doigt** ouvre un pavé numérique (broches, nombres)
ou un clavier (prénoms) ; un clic de souris ou une frappe au clavier ne l'ouvrent pas, et
taper au clavier le referme.

## 12. Règles de placement exactes

Partagées par le jeu et le configurateur, et vérifiées par un test qui compare, pour une
série de fichiers d'exemple et pour 1024×600 et 1920×1080, les rectangles des boutons
calculés des deux côtés (ils doivent être identiques au pixel).

1. Les valeurs sont converties en pixels de l'écran réel (§4), arrondies à l'entier le plus
   proche (0,5 vers le haut), **une seule fois**, au moment de la conversion.
2. Boutons de la disposition automatique : visibles, non placés librement, dans l'ordre
   logique.
3. Largeur d'une colonne : `(area.width − (columns − 1) × gap.x) / columns` ; largeur
   d'un bouton : `button_size.width × colonne`.
4. Ligne `i` : `y = area.y + Σ(hauteurs et écarts des lignes précédentes) + space_before`.
5. Bloc entier centré dans `area` (horizontalement toujours, verticalement si
   `align: center`).
6. Plus de lignes que n'en tient `area` : `overflow: pages` coupe en pages (les flèches de
   page s'affichent), `scroll` fait défiler pour garder le bouton sélectionné visible.

## 13. Favoris `fav1`, `fav2`…

Les favoris se **créent dans RaspyDarts** (écran des options d'un jeu : « Enregistrer comme
favori n° N ») ; le fichier ne fait que les placer :

```yaml
      - action: favorite:fav1        # texte et logo du jeu par défaut
        shortcut: [F7, '1']
```

Un favori mémorise : le jeu, ses options, le nombre de joueurs prévu et le choix des
joueurs :

- `choose` : les joueurs mémorisés avec le favori ;
- `generic` : Joueur 1, Joueur 2… ;
- `last` : les derniers joueurs, ajustés au nombre prévu, avec un avertissement s'il y en a
  trop (« les joueurs en trop seront retirés ») ou pas assez (« il manquera des joueurs »),
  et le choix de continuer.

Un favori vide affiche son bouton grisé (état `disabled`).

## 14. Exemple complet

```yaml
version: 1
resolution: auto

defaults:
  background: {image: images/background/menu.png, fit: cover}
  style: classic

styles:
  tile:
    shape: rounded
    radius: 18
    background: {image: images/buttons/tile.png, fit: slice, slice: 16}
    text: {size: 0.035, color: '#FFFFFF', position: bottom, shadow: true}
    selected: {background: {image: images/buttons/tile_on.png}, scale: 1.06}

menus:
  main:
    title: game-type-menu
    layout: tiles
    columns: 3
    area: {x: 0.1, y: 0.2, width: 0.8, height: 0.7}
    style: tile
    buttons:
      - action: local_game
        icon: images/icons/target.png
        shortcut: [F1, l]
        exhibition: true
      - action: favorite:fav1
        shortcut: F7
        exhibition: true
      - action: favorite:fav2
        shortcut: F8
        exhibition: true
      - action: trophies
        shortcut: F5
        exhibition: true
      - action: gallery
        shortcut: F6
        exhibition: true
      - action: network_join
        shortcut: F2
      - action: menu:miscellaneous
        icon: images/icons/gear.png
        shortcut: F4
        style: classic
        text: {size: 0}                       # icône seule
        place: {x: 0.94, y: 0.03, width: 0.05, height: 0.08}
      - action: shutdown
        shortcut: escape
        confirm: realy-stop
        visible: false                        # caché, joignable par Échap
```
