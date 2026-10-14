# -*- coding: utf-8 -*-
"""
Game by David !
"""
######
import random
import subprocess
import math
import pygame
from copy import deepcopy
from include import cplayer
from include import cgame
### TROPHEES
from include import ctrophies


# Dictionnay of options - Text format only
OPTIONS = {'theme': 'default', 'max_round': 20, 'max_territory': 7}
# background image - relative to images folder - Name it like the game itself
LOGO = 'Conquer.png'  # background image
# Columns headers - Better as a string
HEADERS = ['#', 'PTS']  # Columns headers - Must be a string
# How many darts per player and per round ? Yes ! this is a feature :)
NB_DARTS = 3  # How many darts per player and per round
# Dictionary of stats and display order (For example : Points Per Darts and avg are displayed in ascending order)
GAME_RECORDS = {'Points Per Round': 'DESC'}
VERSION = '1.00'

def check_players_allowed(nb_players):
    """
    Check if number of players is ok according to options
    """
    return nb_players >= 2 and nb_players <= 4, VERSION , 4

class CPlayerExtended(cplayer.Player):
    """
    Extend the basic player
    """

    def __init__(self, ident, nb_columns, interior=False):
        super().__init__(ident, nb_columns, interior)
        self.segments = []
        # Init Player Records to zero
        for record in GAME_RECORDS:
            self.stats[record] = '0'

class Game(cgame.Game):
    """
    Conquer class game
    """

    def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
        super().__init__(display, game, nb_players,
                         options, config, logs, rpi, dmd, video_player)
        # For rpi
        self.rpi = rpi
        self.logo = LOGO
        self.headers = HEADERS
        self.nb_darts = NB_DARTS
        self.nb_players = nb_players
        self.options = options
        self.maxSrength = 3

        # couleurs segment des joueurs (Noms et Equivalents RGB pour Pygame)
        self.colors = ['green', 'blue', 'red', 'yellow']
        self.rgb_colors = {
            'green': (46, 204, 113),
            'blue': (52, 152, 219),
            'red': (231, 76, 60),
            'yellow': (241, 196, 15),
            'neutral': (150, 150, 150),   # Couleur de fond neutre alignée
            'border': (0, 0, 0)           # Contour noir net
        }

        # records is the dictionnary of stats (see above)
        self.game_records = GAME_RECORDS

        self.max_round = int(options['max_round'])
        self.max_territory = int(options['max_territory'])

# init Hex - Rayon exact pour un collage parfait des polygones
        self.scale = self.display.res['x'] / 1920
        self.hex_radius = 100 * self.scale  # Ajuste cette valeur si tu veux grossir/réduire globalement

        # Constantes mathématiques du pavage hexagonal
        dx = self.hex_radius * math.sqrt(3)
        dy = self.hex_radius * 1.5

        # Centre de référence global ( Bull 'B' / index 20 )
        cx = 1255 * self.scale
        cy = 565 * self.scale

        # Positions calculées mathématiquement, conservant l'ordre exact de tes indices (0 à 20)
        self.pos = [
            (cx, cy - 3 * dy),                     # 0
            (cx - 1.5 * dx, cy - 2 * dy),          # 1
            (cx - 0.5 * dx, cy - 2 * dy),          # 2
            (cx + 0.5 * dx, cy - 2 * dy),          # 3
            (cx + 1.5 * dx, cy - 2 * dy),          # 4
            (cx - 2 * dx, cy - dy),                # 5
            (cx - dx, cy - dy),                    # 6
            (cx + dx, cy - dy),                    # 7
            (cx + 2 * dx, cy - dy),                # 8
            (cx - 2.5 * dx, cy),                   # 9
            (cx - 1.5 * dx, cy),                   # 10
            (cx + 1.5 * dx, cy),                   # 11
            (cx + 2.5 * dx, cy),                   # 12
            (cx - 2 * dx, cy + dy),                # 13
            (cx - dx, cy + dy),                    # 14
            (cx, cy + dy),                         # 15
            (cx + dx, cy + dy),                    # 16
            (cx + 2 * dx, cy + dy),                # 17
            (cx - 0.5 * dx, cy + 2 * dy),          # 18
            (cx + 0.5 * dx, cy + 2 * dy),          # 19
            (cx, cy)                               # 20 (Bull - Centre exact)
        ]
        
        # hex links
        self.link = {
            '1': ('3', '4'),
            '2': ('3', '6', '7'),
            '3': ('1', '2', '4', '7', 'B'),
            '4': ('1', '3', '5', '8', 'B'),
            '5': ('4', '8', '9'),
            '6': ('2', '7', '10', '11'),
            '7': ('2', '3', 'B', '6', '11'),
            '8': ('4', '5', 'B', '9', '12'),
            '9': ('5', '8', '12', '13'),
            '10': ('6', '11', '14'),
            '11': ('6', '7', '10', 'B', '14', '15'),
            '12': ('8', '9', 'B', '13', '17', '18'),
            '13': ('9', '12', '18'),
            '14': ('10', '11', '15'),
            '15': ('11', 'B', '14', '16', '19'),
            '16': ('B', '15', '17', '19', '20'),
            '17': ('B', '12', '16', '18', '20'),
            '18': ('12', '13', '17'),
            '19': ('15', '16', '20'),
            '20': ('16', '17', '19'),
            'B': ('3', '4', '7', '8', '11', '12', '15', '16', '17')
        }

        self.grid = []  # list of (segment, player, strengh)

        # random hex
        hits = [x for x in range(1, 21)]
        for i in range(0, 20):
            h = random.randint(0, len(hits) - 1)
            self.grid.append((str(hits[h]), -1, -1))
            hits.pop(h)

        # add extra hex for bull
        self.grid.append(('B', -1, 0))  # segment, player, strengh

        self.show_segment = False
        self.backups = []
        self.backups_grid = []

    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        if actual_round == 1 and player_launch == 1 and actual_player == 0:
            try:
                LST = self.check_handicap(players)
            except Exception as e:
                self.logs.error("Handicap failed : {}".format(e))
            for Player in players:
                Player.score = 0

            self.display.specialbg = 'bg_conquer'
            self.display.display_background(image='bg_conquer.jpg')

        if player_launch == 1:
            players[actual_player].segments = ['', '', '']
            players[actual_player].round_points = 0
            self.save_turn(players)
            players[actual_player].pre_play_score = players[actual_player].score
            players[actual_player].columns = []
            for i in range(0, 2):
                players[actual_player].columns.append(['', 'int'])

        light_segments = []
        strobe_segments = []

        neighbors = self.find_neighbors(actual_player)
        for segment in neighbors:
            if neighbors[segment] == 1:
                light_segments.append(segment)
            else:
                strobe_segments.append(segment)

        self.rpi.set_target_leds('|'.join(f"{mult}{segment}#{self.colors[actual_player]}" for mult in (
            'S', 'D', 'T') for segment in light_segments))
        self.rpi.set_target_leds_blink('|'.join(f"{mult}{segment}#{self.colors[actual_player]}" for mult in (
            'S', 'D', 'T') for segment in strobe_segments))

        return 0

    def pnj_score(self, players, actual_player, level, player_launch):
        """
        Compute PNJ Score for grid-based game (e.g., Dungeon Darts),
        handling grid ownership, cell links, bull attacks, and difficulty levels.
        """
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende des niveaux : [p_success, p_neighbor, p_miss]
        #   * p_success  : Probabilité de toucher exactement la cible choisie (%)
        #   * p_neighbor : Probabilité de dévier vers un secteur voisin via la matrice (%)
        #   * p_miss     : Probabilité de rater complètement et d'atteindre un secteur aléatoire (%)
        # - Plus fort / précis : Augmenter p_success, diminuer p_miss et p_neighbor.
        # - Plus humain / brouillon : Augmenter p_miss et p_neighbor, diminuer p_success.
        # =========================================================================
        
        dartboard_neighbors = {
            1: (20, 18), 2: (15, 17), 3: (17, 19), 4: (18, 13), 5: (12, 20),
            6: (13, 10), 7: (19, 16), 8: (16, 11), 9: (14, 12), 10: (6, 15),
            11: (8, 14), 12: (9, 5), 13: (4, 6), 14: (11, 9), 15: (10, 2),
            16: (7, 8), 17: (2, 3), 18: (1, 4), 19: (3, 7), 20: (5, 1)
        }

        # Niveaux de précision [Chance réussite, Chance voisin, Chance raté]
        levels = [
            [15, 35, 50],  # Niveau 1
            [30, 40, 30],  # Niveau 2
            [50, 35, 15],  # Niveau 3
            [70, 20, 10],  # Niveau 4
            [85, 10, 5]    # Niveau 5
        ]
        
        lvl_idx = max(0, min(level - 1, len(levels) - 1))
        p_success = levels[lvl_idx][0]
        p_neighbor = levels[lvl_idx][1]

        rand_val = random.randrange(100)
        my_segments = [v[0] for v in self.grid if v[1] == actual_player]
        target_seg = None
        target_type = 'S'

        bull_data = self.grid[20]
        bull_owner = bull_data[1]
        bull_strength = bull_data[2]

        bull_neighbors_cases = self.link['B'] 
        bull_neighbor_segs = [self.grid[20 if k == 'B' else int(k)-1][0] for k in bull_neighbors_cases]
        pnj_is_adjacent_to_bull = any(seg in my_segments for seg in bull_neighbor_segs)

        if bull_owner == actual_player:
            if bull_strength < 3 and (not my_segments or pnj_is_adjacent_to_bull or level >= 2):
                target_seg = 'B'
                target_type = 'T' if level >= 3 else 'D'
        elif bull_owner == -1:
            if not my_segments or pnj_is_adjacent_to_bull or level >= 2:
                target_seg = 'B'
                target_type = 'D' if level >= 3 else 'S'
        else:
            if pnj_is_adjacent_to_bull and level >= 2:
                target_seg = 'B'
                if bull_strength <= 1 and level >= 3:
                    target_type = 'T'
                else:
                    target_type = random.choice(['D', 'T'])

        if not target_seg:
            if not my_segments:
                neutrals = [v[0] for v in self.grid if v[1] == -1 and v[0] != 'B']
                target_seg = random.choice(neutrals) if neutrals else 'B'
                target_type = 'S'
            else:
                candidates = []
                for seg in my_segments:
                    case_idx = self.getCaseFromSegment(seg)
                    linked_keys = self.link['B' if case_idx == 21 else str(case_idx)]
                    for l in linked_keys:
                        nbr_seg = 'B' if l == 'B' else self.grid[int(l)-1][0]
                        nbr_player = self.grid[20 if l == 'B' else int(l)-1][1]
                        nbr_strength = self.grid[20 if l == 'B' else int(l)-1][2]
                        if nbr_player != actual_player:
                            candidates.append((nbr_seg, nbr_player, nbr_strength))

                if candidates:
                    neutral_candidates = [c for c in candidates if c[1] == -1]
                    enemy_candidates = [c for c in candidates if c[1] != -1]

                    if neutral_candidates and (not enemy_candidates or random.random() < 0.6):
                        chosen = random.choice(neutral_candidates)
                        target_seg = chosen[0]
                        target_type = random.choice(['D', 'T']) if level >= 3 and random.random() < 0.5 else 'S'
                    elif enemy_candidates:
                        chosen = random.choice(enemy_candidates)
                        target_seg = chosen[0]
                        target_type = 'T' if chosen[2] <= 1 and level >= 3 else 'D'
                    else:
                        target_seg = random.choice([v[0] for v in self.grid if v[1] == -1]) if any(v[1] == -1 for v in self.grid) else random.choice(my_segments)
                        target_type = 'S'
                else:
                    target_seg = random.choice([v[0] for v in self.grid if v[1] == -1]) if any(v[1] == -1 for v in self.grid) else random.choice(my_segments)
                    target_type = 'S'

        if target_seg == 'B':
            if rand_val < p_success:
                return 'SB' if target_type == 'S' else ('DB' if target_type == 'D' else 'TB' if target_type == 'T' and 'TB' in self.score_map else 'DB')
            elif rand_val < p_success + p_neighbor:
                neigh = random.choice([20, 19, 6])
                return f"{target_type if target_type != 'TB' else 'D'}{neigh}"
            else:
                return f"S{random.randint(1, 20)}"
        else:
            try:
                target_num = int(target_seg)
            except ValueError:
                target_num = 20

            if rand_val < p_success:
                return f"{target_type}{target_num}"
            elif rand_val < p_success + p_neighbor:
                neighbor = random.choice(dartboard_neighbors.get(target_num, (20, 18)))
                return f"{target_type}{neighbor}"
            else:
                return f"S{random.randint(1, 20)}"

    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        handler = self.init_handler()
        curr_player = players[actual_player]
        curr_player.darts_thrown += 1
        curr_player.segments[player_launch-1] = hit


        
        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)
        # ---------------------------------------------

        multi = 1
        if hit[:1] == 'D':
            multi = 2
        if hit[:1] == 'T':
            multi = 3

        for k, v in enumerate(self.grid):
            if v[0] == hit[1:]:
                if v[1] < 0:
                    self.grid[k] = (v[0], actual_player, multi - 1)
                    handler['sound'] = 'conquer_first'
                elif v[1] != actual_player:
                    niv = v[2] - multi
                    if niv < 0:
                        self.grid[k] = (v[0], actual_player, -niv - 1)
                        handler['sound'] = 'conquer_fight'
                    else:
                        self.grid[k] = (v[0], v[1], niv)
                        handler['sound'] = 'conquer_down'
                else:
                    niv = v[2] + multi
                    if niv > self.maxSrength:
                        niv = self.maxSrength
                    self.grid[k] = (v[0], v[1], niv)
                    handler['sound'] = 'conquer_up'

                self.blink_box(k)
                self.draw_box(k, refresh=True)

                if hit[1:] == 'B':
                    handler['video'] = 'conquer/conquer_bull'

                kingdom = self.findLink(actual_player, hit[1:], [hit[1:]], [])
                if self.grid[k][1] == actual_player and len(kingdom[0]) >= self.max_territory:
                    self.winner = players[actual_player].ident
                    kingdoms = [0, 0, 0, 0]
                    for c in self.grid:
                        if c[1] >= 0:
                            kingdoms[c[1]] = kingdoms[c[1]] + 1000 + c[2]

                    for player in players:
                        player.score = kingdoms[player.ident]

                    bestscore = kingdoms[actual_player]
                    handler['return_code'] = 3
                else:
                    if actual_round >= self.max_round and actual_player == self.nb_players - 1:
                        kingdoms = [0, 0, 0, 0]
                        for c in self.grid:
                            if c[1] >= 0:
                                kingdoms[c[1]] = kingdoms[c[1]] + 1000 + c[2]

                        bestscore = 0
                        for player in players:
                            player.score = kingdoms[player.ident]
                            if kingdoms[player.ident] > bestscore:
                                bestscore = kingdoms[player.ident]
                                bestscoreid = player.ident
                        self.winner = bestscoreid
                        handler['return_code'] = 3
                        
         # TROPHEES
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)

        # --- VÉRIFICATION DES TROPHÉES DE FIN DE PARTIE ---
        if handler.get('return_code') == 3 and self.winner is not None:
            winning_player = players[self.winner]
            ctrophies.check_game_end_stats(players, winning_player, "CONQUER")
        # --------------------------------------------------

        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        return handler

    def find_neighbors(self, actual_player):
        player_segments = [
            f'{element[0]}' for element in self.grid if element[1] == actual_player]
        neighbors = {}
        for segment in player_segments:
            case = self.getCaseFromSegment(segment)
            if case == 21:
                cases_voisines = self.link['B']
            else:
                cases_voisines = self.link[f'{case}']
            for neighbor in [self.grid[20 if case == 'B' else int(case) - 1][0] for case in cases_voisines]:
                if self.getCaseFromSegment(neighbor) == 'B':
                    index = 20
                else:
                    index = int(self.getCaseFromSegment(neighbor)) - 1

                if self.grid[index][1] != actual_player and self.grid[index][1] > -1:
                    neighbors[neighbor] = 3
                elif segment not in neighbors and neighbor in neighbors:
                    neighbors[neighbor] = 2
                elif neighbor not in neighbors:
                    neighbors[neighbor] = 1
        return neighbors

    def findLink(self, actual_player, segment, linkedHex, linkedHexTotal):
        for k in self.link['B' if segment == 'B' else str(self.getCaseFromSegment(segment))]:
            seg = 'B' if k == 'B' else self.grid[int(k)-1][0]
            if seg not in linkedHex and self.grid[20 if k == 'B' else int(k) - 1][1] == actual_player:
                linkedHex.append(seg)
                linkedHex2 = self.findLink(
                    actual_player, seg, linkedHex, linkedHexTotal)
                for i in linkedHex2[0]:
                    if i not in linkedHex:
                        linkedHex.append(i)
            if seg not in linkedHexTotal:
                linkedHexTotal.append(seg)

        return (linkedHex, linkedHexTotal)

    def findPlayerNeighbor(self, player_id):
        maxZone = ([], [])
        allSeg = []
        for k, v in enumerate(self.grid):
            if v[0] not in allSeg and v[1] == player_id:
                zone = self.findLink(player_id, v[0], [v[0]], [])
                if len(zone[0]) > len(maxZone[0]):
                    maxZone = zone
                for seg in zone[0]:
                    if seg not in allSeg:
                        allSeg.append(seg)

        neighbor = []
        for v in maxZone[1]:
            if v not in maxZone[0]:
                neighbor.append(v)
        return neighbor

    def getCaseFromSegment(self, segment):
        for k, v in enumerate(self.grid):
            if segment == v[0]:
                return k + 1

    def display_segment(self):
        return False

    def get_hexagon_points(self, center, radius):
        """Calcule les 6 sommets d'un hexagone orienté angle -30"""
        points = []
        for i in range(6):
            angle_deg = 60 * i - 30
            angle_rad = math.radians(angle_deg)
            x = center[0] + radius * math.cos(angle_rad)
            y = center[1] + radius * math.sin(angle_rad)
            points.append((x, y))
        return points

    def draw_hexagon(self, surface, center, radius, color, border_color=None):
        points = self.get_hexagon_points(center, radius)
        pygame.draw.polygon(surface, color, points)
        if border_color:
            pygame.draw.polygon(surface, border_color, points, 4)

    def draw_bull_block(self, surface, center, radius, color):
        """
        Dessine le bloc unifié du Bull en compensant le décalage visuel 
        pour qu'il s'emboîte parfaitement au centre de la grille.
        """
        h_spacing = radius * math.sqrt(3)
        v_spacing = radius * 1.5

        # Décalage de compensation pour centrer le bloc unifié sur le point de grille
        bull_center_y = center[1] - (v_spacing * 0.33)  
        shift_x = 0  

        offsets = [
            (shift_x, -v_spacing * 0.65),             # Haut
            (shift_x - h_spacing / 2, v_spacing / 3), # Bas-gauche
            (shift_x + h_spacing / 2, v_spacing / 3)  # Bas-droite
        ]
        
        for dx_off, dy_off in offsets:
            sub_c = (center[0] + dx_off, bull_center_y + dy_off)
            points = self.get_hexagon_points(sub_c, radius)
            pygame.draw.polygon(surface, color, points)

        # Renvoie le centre corrigé pour bien placer le texte 'B' et les boucliers au milieu
        return (center[0] + shift_x, bull_center_y + (v_spacing * 0.1))

    def draw_shields(self, surface, center, count, base_y):
        """
        Dessine et centre horizontalement les losanges (boucliers) de force
        """
        if count <= 0:
            return
        size = 22 * self.scale
        stepx = 35 * self.scale
        total_width = (count - 1) * stepx + size
        start_x = center[0] - (total_width / 2)

        for i in range(count):
            bx = start_x + (i * stepx)
            by = base_y
            shield_points = [
                (bx + size / 2, by),             # Sommet haut
                (bx + size, by + size / 2),      # Sommet droit
                (bx + size / 2, by + size),      # Sommet bas
                (bx, by + size / 2)              # Sommet gauche
            ]
            pygame.draw.polygon(surface, (230, 230, 230), shield_points)
            pygame.draw.polygon(surface, self.rgb_colors['border'], shield_points, 2)

    def refresh_game_screen(self, Players, actual_round, max_round, RemDarts, nb_darts, logo, headers, actual_player, TxtOnLogo=False, Wait=False, OnScreenButtons=None, showScores=True, end_of_game=False, endOfSet=None, Set=None, MaxSet=None):
        ClickZones = {}
        sx = 43 * self.scale

        self.display.screen.fill((0, 0, 0))
        self.display.display_image(self.display.file_class.get_full_filename(
            'conquer/conquer_back.png', 'images'), 0, 0, self.display.res['x'], self.display.res['y'], True, False, False)

        yp1 = 180 * self.scale
        stepy = 182 * self.scale
        for player in Players:
            self.display.display_image(self.display.file_class.get_full_filename(
                f'conquer/conquer_j{player.ident + 1}.png', 'images'), sx, yp1+player.ident*stepy, 525 * self.scale, 105 * self.scale, True, False, False)
            self.display.blit_text(player.name, sx, yp1+player.ident*stepy+5 * self.scale, 525 * self.scale,
                                   100 * self.scale, color=(255, 255, 255) if actual_player == player.ident else (0, 0, 0))

        self.display.blit_text(f"{self.display.lang.translate('round')} {actual_round} / {max_round}",
                               200 * self.scale, 975 * self.scale, 223 * self.scale, 60 * self.scale, color=(255, 255, 255))

        self.display.blit_text("-".join(Players[actual_player].segments), 700 * self.scale,
                               975 * self.scale, 223 * self.scale, 60 * self.scale, color=(255, 255, 255))

         #1. dessine en premier le bull
        if len(self.grid) > 20:
            self.draw_box(20)

        # 2. Dessiner ensuite tous les autres numéros (indices 0 à 19) par-dessus
        for k in range(20):
            if k < len(self.grid):
                self.draw_box(k)
                
       # for k, v in enumerate(self.grid):
       #     self.draw_box(k)

        if end_of_game:
            ClickZones = self.display.end_of_game_menu(logo, stat_button=False)
            return ClickZones

        self.display.update_screen()
        return [ClickZones]

    def blink_box(self, case):
        """
        Fait clignoter la case touchée à travers les 4 couleurs des joueurs 
        avant de se stabiliser sur sa vraie couleur.
        """
        pos_x = self.pos[case][0] - 250 * self.scale
        pos_y = self.pos[case][1] - 250 * self.scale
        width = 500 * self.scale
        height = 500 * self.scale

        for color_name in self.colors:
            forced_color = self.rgb_colors[color_name]
            self.draw_box(case, refresh=False, forced_color=forced_color)
            self.display.update_screen((pos_x, pos_y, width, height))
            pygame.time.delay(100)

    def draw_box(self, case, refresh=False, forced_color=None):
        """
        Draw each territory (avec support d'une couleur temporaire pour le clignotement)
        """
        v = self.grid[case]
        center = self.pos[case]
        radius = self.hex_radius  

        if forced_color is not None:
            fill_color = forced_color
        elif v[1] > -1 and v[1] < len(self.colors):
            player_color_name = self.colors[v[1]]
            fill_color = self.rgb_colors.get(player_color_name, (255, 255, 255))
        else:
            fill_color = self.rgb_colors['neutral']

        border_color = self.rgb_colors['border']

        if case == 20:
            # Récupère le centre réel des 3 hexagones du bull
            bull_real_center = self.draw_bull_block(self.display.screen, center, radius, fill_color)
            
            # --- CENTRAGE PARFAIT DU TEXTE 'B' SUR LE VRAI CENTRE DU BULL ---
            text_x = bull_real_center[0] - (40 * self.scale)
            text_y = bull_real_center[1] - (40 * self.scale)
            self.display.blit_text('B', text_x, text_y, 80 * self.scale, 80 * self.scale, color=(255, 255, 255))
            
            # Affichage des boucliers centrés sur le vrai centre du Bull (légèrement décalés vers le bas en Y)
            self.draw_shields(self.display.screen, bull_real_center, v[2], bull_real_center[1] + 25 * self.scale)
        else:
            # Hexagone standard
            self.draw_hexagon(self.display.screen, center, radius, fill_color, border_color)

            # Affichage des boucliers centrés horizontalement pour les chiffres 1 à 20
            self.draw_shields(self.display.screen, center, v[2], self.pos[case][1] + 15 * self.scale)

            # Affichage du texte (numéro pour les hexagones 1 à 20)
            self.display.blit_text(str(v[0]), self.pos[case][0] - 40 * self.scale, self.pos[case][1] - 40 * self.scale, 80 * self.scale, 80 * self.scale, color=(255, 255, 255))

        if refresh:
            pos_x = self.pos[case][0] - 250 * self.scale
            pos_y = self.pos[case][1] - 250 * self.scale
            width = 500 * self.scale
            height = 500 * self.scale
            self.display.update_screen((pos_x, pos_y, width, height))

    def backup_round(self, players, actual_round):
        if len(self.backups) < actual_round:
            self.backups.append(deepcopy(players))
            self.backups_grid.append(deepcopy(self.grid))
        else:
            self.backups[actual_round - 1] = deepcopy(players)
            self.backups_grid[actual_round - 1] = deepcopy(self.grid)

    def restore_round(self, roundtorestore):
        try:
            self.grid = self.backups_grid[roundtorestore - 1]
            return self.backups[roundtorestore - 1]
        except:
            try:
                self.grid = self.backups_grid[roundtorestore]
                return self.backups[roundtorestore]
            except:
                try:
                    self.grid = self.backups_grid[roundtorestore + 1]
                    return self.backups[roundtorestore + 1]
                except:
                    return None

    def miss_button(self, players, actual_player, actual_round, player_launch):
        players[actual_player].segments[player_launch-1] = 'MISS'
        self.display.play_sound('miss')
        players[actual_player].darts_thrown += 1
        
        players[actual_player].darts_thrown += 1
        
        hit = 'MISS'
        print('CONTENU DE HIT  DEF MISS')
        print(hit)
        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)
        
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)
