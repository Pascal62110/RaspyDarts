# -*- coding: utf-8 -*-
"""
Game by LaDite !
Adapted with Conquer vector geometry engine.
"""
######
import re
import random
import subprocess
import math
import pygame
from copy import deepcopy
from include import cplayer
from include import cgame
#### TROPHEES
from include import ctrophies


# Dictionary of options - Text format only
OPTIONS = {'theme': 'default', 'max_round': 20, 'bouclier': 3, 'bonus': 0, 'miss': 0}
# background image - relative to images folder - Name it like the game itself
LOGO = 'Risk.png'  # background image
# Columns headers - Better as a string
HEADERS = ['#', 'PTS']  # Columns headers - Must be a string
# How many darts per player and per round ? Yes ! this is a feature :)
NB_DARTS = 3  # How many darts per player and per round
# Dictionary of stats and display order
GAME_RECORDS = {'Points Per Round': 'DESC'}
VERSION = '1.00'

def check_players_allowed(nb_players):
    """
    Return the player number max for a game.
    """
    return nb_players in (2, 3, 4, 5), VERSION, 5

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
        self.alive = True

class Game(cgame.Game):
    """
    Risk class game
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
        self.dead = 0
        self.led = ''
        self.bonus = int(options['bonus'])
        self.miss = int(options['miss'])
        
        # couleurs segment des joueurs (Ordre exact: J1=Green, J2=Blue, J3=Red, J4=Yellow, J5=Purple)
        self.colors = ['green', 'blue', 'red', 'yellow', 'purple']
        self.rgb_colors = {
            'green': (46, 204, 113),
            'blue': (52, 152, 219),
            'red': (231, 76, 60),
            'yellow': (241, 196, 15),
            'purple': (155, 89, 182),
            'neutral': (150, 150, 150),   # Couleur de fond neutre alignée
            'border': (0, 0, 0)           # Contour noir net
        }

        # records is the dictionnary of stats (see above)
        self.game_records = GAME_RECORDS

        self.max_round = int(options['max_round'])
        self.bouclier = int(options['bouclier'])
        if self.bouclier > 3:
            self.bouclier = 3

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
        
        joueur1 = []
        joueur2 = []
        joueur3 = []
        joueur4 = []
        joueur5 = []
        bull = ['SB#white', 'DB#white']
        
        # random hex
        hits = [x for x in range(1, 21)]
        
        if nb_players == 4:
            index_joueur = [0, 2, 3, 1, 2, 3, 1, 0, 3, 1, 0, 2, 3, 0, 1, 2, 1, 0, 2, 3]
        elif nb_players == 3:
            index_joueur = [0, 2, 9, 1, 2, 9, 1, 0, 9, 1, 0, 2, 9, 0, 1, 2, 1, 0, 2, 9]
        elif nb_players == 2:
            index_joueur = [0, 9, 9, 1, 9, 9, 1, 0, 9, 1, 0, 9, 9, 0, 1, 9, 1, 0, 9, 9]
        elif nb_players == 5:
            index_joueur = [0, 2, 4, 1, 2, 3, 1, 4, 3, 1, 0, 4, 3, 0, 1, 2, 3, 0, 2, 4]    
       
        random.shuffle(index_joueur)
        
        for i in range(0, 20):
            h = random.randint(0, len(hits) - 1)
            j = random.choice(index_joueur)
            
            if j != 9:
                self.grid.append((str(hits[h]), j, self.bouclier))
            elif j == 9:
                self.grid.append((str(hits[h]), -1, -1))
                
            if j == 0:
                joueur1.append('S'+str(hits[h])+'#green')
                joueur1.append('D'+str(hits[h])+'#green')
                joueur1.append('T'+str(hits[h])+'#green')
            elif j == 1:
                joueur2.append('S'+str(hits[h])+'#blue')
                joueur2.append('D'+str(hits[h])+'#blue')
                joueur2.append('T'+str(hits[h])+'#blue')
            elif j == 2:
                joueur3.append('S'+str(hits[h])+'#red')
                joueur3.append('D'+str(hits[h])+'#red')
                joueur3.append('T'+str(hits[h])+'#red') 
            elif j == 3:
                joueur4.append('S'+str(hits[h])+'#yellow')
                joueur4.append('D'+str(hits[h])+'#yellow')
                joueur4.append('T'+str(hits[h])+'#yellow')
            elif j == 4:
                joueur5.append('S'+str(hits[h])+'#purple')
                joueur5.append('D'+str(hits[h])+'#purple')
                joueur5.append('T'+str(hits[h])+'#purple')    

            hits.pop(h)
            index_joueur.remove(j)

        self.led = (joueur1 + joueur2 + joueur3 + joueur4 + joueur5 + bull)
        
        self.grid.append(('B', -1, self.bouclier))

        # gestion de l'affichage du segment
        self.show_segment = False

        self.backups = []
        self.backups_grid = []

    # --- VECTOR DRAWING ENGINE (CONQUER ARCHITECTURE) ---
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

    def blink_box(self, case):
        """
        Fait clignoter la case touchée à travers les couleurs vectorielles 
        des joueurs avant de se stabiliser sur sa vraie couleur.
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
        Draw each territory with polygon vectors and shields
        """

        v = self.grid[case]
        
        # --- GESTION DU BULL (Case 20) ---
        if case == 20:
            center = self.pos[case]
            radius = self.hex_radius
            
            # Le Bull reste blanc (sauf clignotement forcé)
            if forced_color is not None:
                fill_color = forced_color
            else:
                fill_color = (255, 255, 255)
                
            border_color = self.rgb_colors['border']
            
            # Dessine le bloc unifié du Bull et récupère le centre corrigé
            corrected_center = self.draw_bull_block(self.display.screen, center, radius, fill_color)
            
            # Dessine les boucliers sous le texte
            #self.draw_shields(self.display.screen, corrected_center, v[2], corrected_center[1] + 25 * self.scale)
            
            # Affichage de "RENFORTS" et "TERRITOIRE" enCORE PLUS GROS sur 2 lignes
            self.display.blit_text('RENFORTS', corrected_center[0] - 110 * self.scale, corrected_center[1] - 65 * self.scale, 220 * self.scale, 60 * self.scale, color=(0, 0, 0))
            self.display.blit_text('TERRITOIRE', corrected_center[0] - 110 * self.scale, corrected_center[1] - 5 * self.scale, 220 * self.scale, 60 * self.scale, color=(0, 0, 0))
            
            
            if refresh:
                pos_x = center[0] - 250 * self.scale
                pos_y = center[1] - 250 * self.scale
                width = 500 * self.scale
                height = 500 * self.scale
                self.display.update_screen((pos_x, pos_y, width, height))
            return


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

        self.draw_hexagon(self.display.screen, center, radius, fill_color, border_color)
        self.draw_shields(self.display.screen, center, v[2], self.pos[case][1] + 15 * self.scale)
        self.display.blit_text(str(v[0]), self.pos[case][0] - 40 * self.scale, self.pos[case][1] - 40 * self.scale, 80 * self.scale, 80 * self.scale, color=(255, 255, 255))

        if refresh:
            pos_x = self.pos[case][0] - 250 * self.scale
            pos_y = self.pos[case][1] - 250 * self.scale
            width = 500 * self.scale
            height = 500 * self.scale
            self.display.update_screen((pos_x, pos_y, width, height))

    # --- RISK LOGIC & GAMEPLAY METHODS (STRICTLY UNCHANGED) ---
    def pnj_score(self, players, actual_player, level, player_launch):
        """
        Intelligence Artificielle (PNJ) avec gestion des niveaux de difficulté, 
        du bouclier, de la défense du Bull et des multiplicateurs sur cible.
        """
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende des niveaux : [p_success, p_neighbor, p_miss]
        #   * p_success  : Probabilité de toucher exactement la cible visée (%)
        #   * p_neighbor : Probabilité de dévier vers un secteur voisin physique (%)
        #   * p_miss     : Probabilité de rater complètement et de toucher un secteur aléatoire (%)
        # - Plus fort / précis : Augmenter p_success, réduire p_neighbor et p_miss.
        # - Plus humain / brouillon : Augmenter p_miss et p_neighbor, réduire p_success.
        # =========================================================================

        dartboard_neighbors = {
            1: (20, 18), 2: (15, 17), 3: (17, 19), 4: (18, 13), 5: (12, 20),
            6: (13, 10), 7: (19, 16), 8: (16, 11), 9: (14, 12), 10: (6, 15),
            11: (8, 14), 12: (9, 5), 13: (4, 6), 14: (11, 9), 15: (10, 2),
            16: (7, 8), 17: (2, 3), 18: (1, 4), 19: (3, 7), 20: (5, 1)
        }

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

        weak_my_segments = [v for v in self.grid if v[1] == actual_player and v[2] < self.bouclier]
        my_territories_count = len(my_segments)

        needs_bull_defense = len(weak_my_segments) > 0 or (my_territories_count <= 2 and my_territories_count > 0)

        if needs_bull_defense and level >= 2 and random.random() < 0.70:
            if level >= 3 and random.random() < 0.5:
                return 'DB'
            else:
                return 'SB'

        player_territories_count = {}
        for p in players:
            if p.alive:
                player_territories_count[p.ident] = len([v for v in self.grid if v[1] == p.ident])

        threats_to_eliminate = []
        for pid, count in player_territories_count.items():
            if pid != actual_player and count > 0 and count <= 2:
                enemy_territories = [v for v in self.grid if v[1] == pid]
                threats_to_eliminate.extend(enemy_territories)

        if threats_to_eliminate and level >= 2:
            chosen_target = random.choice(threats_to_eliminate)
            target_seg = chosen_target[0]
            target_type = random.choice(['D', 'T']) if level >= 3 else 'S'
        else:
            enemies = [v for v in self.grid if v[1] != actual_player and v[1] != -1]
            if enemies:
                chosen = random.choice(enemies)
                target_seg = chosen[0]
                if level >= 3:
                    target_type = random.choice(['S', 'D', 'T'])
                elif level == 2:
                    target_type = random.choice(['S', 'D'])
                else:
                    target_type = 'S'
            else:
                target_seg = str(random.randint(1, 20))
                target_type = 'S'

        if target_seg == 'B':
            if rand_val < p_success:
                return 'SB' if target_type == 'S' else 'DB'
            elif rand_val < p_success + p_neighbor:
                neigh = random.choice([20, 19, 6])
                return f"{target_type if target_type != 'DB' else 'SB'}{neigh}"
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

    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        if actual_round == 1 and player_launch == 1 and actual_player == 0:
            try:
                LST = self.check_handicap(players)
            except Exception as e:
                self.logs.error("Handicap failed : {}".format(e))
            for player in players:
                player.score = 0
                player.alive = True

            self.display.specialbg = 'bg_risk'
            self.display.display_background(image='bg_risk.jpg')

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

        leds = self.led 

        self.rpi.set_target_leds('')
        self.rpi.set_target_leds('|'.join(leds))

        if not players[actual_player].alive:
            return 4

        return 0

    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        return_code = 0
        handler = self.init_handler()

        players[actual_player].darts_thrown += 1
        players[actual_player].segments[player_launch-1] = hit
        
                # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)
        
        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)

        multi = 1
        if hit[:1] == 'D':
            multi = 2
        if hit[:1] == 'T':
            multi = 3
        
        if hit == 'SB':
            liste2 = []
            for k, v in enumerate(self.grid):
                # On s'assure de ne pas prendre le Bull (indice 20) dans les territoires libres à conquérir
                if k != 20 and v[1] == -1 and v[2] < 0:
                    liste2.append(v)
            if len(liste2) > 0:
                choix = random.choice(liste2)
            else:
                choix = ['0', 0, 0]
            choix2 = choix[0]

            color_name = self.colors[players[actual_player].ident]
            handler['dmd'] = 'Renfort des troupes + 1 Territoire'
            handler['sound'] = 'risk_reinforcement'

            # 1. Le Bull clignote en premier (on appelle blink_box sur l'indice 20)
            self.blink_box(20)

            # 2. Renforts sur les territoires du joueur (en s'interdisant absolument le Bull avec k != 20)
            for k, v in enumerate(self.grid):
                if k == 20:
                    continue  # Jamais de renforts sur le Bull
                if v[1] == players[actual_player].ident and v[2] < 3:
                    territoire = v[0]   
                    bouclier = v[2] + 1
                    self.grid[k] = (territoire, actual_player, bouclier)
                    
            # 3. Attribution et clignotement du nouveau territoire conquis
            for k, v in enumerate(self.grid):    
                if v[0] == choix2 and choix2 != '0':
                    territoire = v[0]  
                    bouclier = 0 
                    self.grid[k] = (territoire, actual_player, bouclier)
                    
                    # Le chiffre gagnant clignote à son tour juste après le Bull
                    self.blink_box(k)
                    
                    self.led.append('S'+str(v[0])+'#'+color_name)
                    self.led.append('D'+str(v[0])+'#'+color_name)
                    self.led.append('T'+str(v[0])+'#'+color_name)
                    handler['sound'] = 'risk_annexed'
                    break


        if hit == 'DB':
            liste2 = []
            for k, v in enumerate(self.grid):
                # On s'assure de ne pas prendre le Bull (indice 20) dans les territoires libres
                if k != 20 and v[1] == -1 and v[2] < 0:
                    liste2.append(v)
            if len(liste2) > 0:
                choix = random.choice(liste2)
            else:
                choix = ['0', 0, 0]
            choix2 = choix[0]

            color_name = self.colors[players[actual_player].ident]
            handler['dmd'] = '1 Territoire + Renfort des troupes'
            handler['sound'] = 'risk_reinforcement'

            # 1. Le Bull clignote en premier
            self.blink_box(20)

            # 2. Renforts sur les troupes du joueur (en interdisant formellement le Bull avec k == 20)
            for k, v in enumerate(self.grid):
                if k == 20:
                    continue  # Jamais de renforts sur le Bull
                if v[1] == players[actual_player].ident and v[2] < 3:
                    territoire = v[0]   
                    bouclier = v[2] + 1
                    self.grid[k] = (territoire, actual_player, bouclier)
                    
            # 3. Attribution et clignotement du nouveau territoire conquis
            for k, v in enumerate(self.grid):         
                if v[0] == choix2 and choix2 != '0':
                    territoire = v[0]   
                    bouclier = 1 
                    self.grid[k] = (territoire, actual_player, bouclier)
                    
                    # La case gagnante clignote à son tour
                    self.blink_box(k)
                    
                    self.led.append('S'+str(v[0])+'#'+color_name)
                    self.led.append('D'+str(v[0])+'#'+color_name)
                    self.led.append('T'+str(v[0])+'#'+color_name)
                    handler['sound'] = 'risk_annexed'
                    break

        for k, v in enumerate(self.grid):
            if v[0] == hit[1:]:
                if v[2] == -1:
                    self.grid[k] = (v[0], -1, -1)
                    handler['sound'] = 'risk_miss'
                
                elif v[1] != actual_player:
                    players[actual_player].score += multi
                    niv = v[2] - multi
                    if niv >= 0:
                        handler['sound'] = 'risk_attack'
                        handler['dmd'] = 'Tirs sur l ennemi'
                    if niv < 0:
                        players[actual_player].score += self.bonus
                        self.grid[k] = (v[0], -1, -1)
                        handler['sound'] = 'risk_destroyed'
                        handler['dmd'] = 'Territoire ennemi anéanti'
                        
                        target_color = self.colors[v[1]]
                        try:
                            while True:
                                self.led.remove('S'+v[0]+'#'+target_color)
                                self.led.remove('D'+v[0]+'#'+target_color)
                                self.led.remove('T'+v[0]+'#'+target_color)
                        except:
                            pass
                    else:
                        self.grid[k] = (v[0], v[1], niv)
                        handler['sound'] = 'risk_attack'
                        handler['dmd'] = 'Territoire ennemi attaqué'
                
                elif v[1] == actual_player:
                    niv = v[2] - multi
                    if niv >= 0:
                        handler['sound'] = 'risk_allied_fire'
                        handler['dmd'] = 'Tirs Alliés'
                    if niv < 0:
                        players[actual_player].score -= self.miss
                        self.grid[k] = (v[0], -1, -1)
                        handler['sound'] = 'risk_friend_destroyed'
                        handler['dmd'] = 'Territoire allié anéanti'
                        
                        target_color = self.colors[v[1]]
                        try:
                            while True:
                                self.led.remove('S'+v[0]+'#'+target_color)
                                self.led.remove('D'+v[0]+'#'+target_color)
                                self.led.remove('T'+v[0]+'#'+target_color)
                        except:
                            pass
                    else:
                        self.grid[k] = (v[0], actual_player, niv)
                        handler['dmd'] = 'Tirs alliés'

                self.blink_box(k)
                self.draw_box(k, refresh=True)

                for player in players:
                    for k_check, v_check in enumerate(self.grid):
                        if v_check[1] == player.ident:
                            player.alive = True
                            break
                        else:
                            player.alive = False

        winner = self.check_winner(players, actual_round, player_launch, actual_player)
        if winner > -1:
            self.winner = winner
            return 3
 
        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        handler['return_code'] = return_code
        return handler

    def check_winner(self, players, actual_round, player_launch, actual_player):
        alive_players = []
        for player in players:
            if player.alive:
                alive_players.append(player.ident)

        if len(alive_players) == 1:
            self.winner = alive_players[0]
            players[self.winner].score += 100
            
            winning_player = players[self.winner].name
            
            ### Trophee pour la victoire par élimination
            ctrophies.check_game_end_stats(players, winning_player, "RISK")
            
            print('WINNING_PLAYER (Elimination)')
            print(winning_player)
            return self.winner

        elif len(alive_players) == 0 or (player_launch == self.nb_darts and \
                actual_round >= self.max_round and actual_player == self.nb_players - 1):
            bestscoreid = -1
            bestscore = -1
            
            for player in players:
                if player.score > bestscore:
                    bestscore = player.score
                    bestscoreid = player.ident
            
            if bestscoreid == -1:
                bestscoreid = 0
                
            self.winner = bestscoreid
            
            # Récupération propre du nom du vainqueur au score
            winning_player = next(p.name for p in players if p.ident == bestscoreid)
            
            ## Trophee pour la victoire au score max
            ctrophies.check_game_end_stats(players, winning_player, "RISK")
            
            print('WINNING_PLAYER (Max Round)')
            print(winning_player)
            return bestscoreid
        return -1

    def getCaseFromSegment(self, segment):
        for k, v in enumerate(self.grid):
            if segment == v[0]:
                return k + 1

    def display_segment(self):
        return False
        
    def miss_button(self, players, actual_player, actual_round, player_launch):
        players[actual_player].segments[player_launch-1] = 'MISS'
        self.display.play_sound('miss')
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
        
    def refresh_game_screen(self, Players, actual_round, max_round, RemDarts, nb_darts, logo, headers, actual_player, TxtOnLogo=False, Wait=False, OnScreenButtons=None, showScores=True, end_of_game=False, endOfSet=None, Set=None, MaxSet=None):
        ClickZones = {}
        sx = 43 * self.scale

        self.display.screen.fill((0, 0, 0))
        self.display.display_image(self.display.file_class.get_full_filename(
            'risk/risk_back.png', 'images'), 0, 0, self.display.res['x'], self.display.res['y'], True, False, False)

        yp1 = 180 * self.scale
        stepy = 152 * self.scale
        for player in Players:
            self.display.display_image(self.display.file_class.get_full_filename(
                f'risk/risk_j{player.ident + 1}.png', 'images'), sx, yp1+player.ident*stepy, 525 * self.scale, 105 * self.scale, True, False, False)
            self.display.blit_text(player.name + ' (' + str(player.score) + ')', sx, yp1+player.ident*stepy+5 * self.scale, 525 * self.scale,
                                   100 * self.scale, color=(255, 255, 255) if actual_player == player.ident else (0, 0, 0))

        self.display.blit_text(f"{self.display.lang.translate('round')} {actual_round} / {max_round}",
                               200 * self.scale, 975 * self.scale, 223 * self.scale, 60 * self.scale, color=(255, 255, 255))

        self.display.blit_text("-".join(Players[actual_player].segments), 700 * self.scale,
                               975 * self.scale, 223 * self.scale, 60 * self.scale, color=(255, 255, 255))

        if len(self.grid) > 20:
            self.draw_box(20)

        for k, v in enumerate(self.grid):
            if k != 20:
                self.draw_box(k)


        if end_of_game:
            ClickZones = self.display.end_of_game_menu(logo, stat_button=False)

        self.display.update_screen()
        return [ClickZones]

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
