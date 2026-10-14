# -*- coding: utf-8 -*-
# ==============================================================================
# JEU : SOS INCENDIE (Mode Coopératif / Pydarts)
# ==============================================================================

from include import cplayer
from include import cgame
import random
import time
import os
import pygame
#### TROPHEES
from include import ctrophies


VERSION = '1.0'
DEBUG = {'debug-extra_info': False}

OPTIONS = {
    'theme': 'default', 
    'number_of_lives': '35',       # PV collectifs initiaux de la structure
    'nb_feux_depart': '4',         # Nombre de feux jaunes au départ de la partie
    'target_jaune': True,
}

LOGO = 'incendie/bk_incendie.png' 
HEADERS = [ 'D1', 'D2', 'D3', '', 'Hit', '', 'PPR']
NB_DARTS = 3
GAME_RECORDS = {'Points Per Round': 'DESC'}

# Dimensions et coordonnées des fenêtres du bâtiment (Grille 5x4)
LARGEUR_VITRE = 175
HAUTEUR_VITRE = 119

EMPLACEMENTS_FENETRES = [
    # Ligne 1 (Haut)
    (530, 114), (784, 114), (1042, 114), (1297, 114),
    # Ligne 2
    (530, 294), (784, 294), (1042, 294), (1297, 294),
    # Ligne 3
    (530, 469), (784, 469), (1042, 469), (1297, 469),
    # Ligne 4
    (530, 645), (784, 645), (1042, 645), (1297, 645),
    # Ligne 5 (Bas)
    (530, 823), (784, 823), (1042, 823), (1297, 823),
]

def check_players_allowed(nb_players):
   return 0 < nb_players <= 4, VERSION, 4

class CPlayerExtended(cplayer.Player):
   def __init__(self, ident, nb_columns, interior=False):
      super().__init__(ident, nb_columns, interior)

      self.character = 0
      self.targets = []
      self.segments = ['--', '--', '--']
      self.action_state = 'repos'  # Par défaut en attente (-repos)
      self.lives = 50
      self.max_lives = 50
      self.alive = True
      
      self.classe_nom = 'specialiste'
      self.pouvoir_desc = 'Dégâts massifs (-2 niveaux)'
      self.pouvoir_actif_tour = False 
      
      for record in GAME_RECORDS:
         self.stats[record] = '0'

class Game(cgame.Game):
   def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
      super().__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)
      self.rpi = rpi
      self.logo = LOGO
      self.headers = HEADERS
      self.nb_darts = NB_DARTS
      self.nb_players = nb_players
      self.debug_info = False
      self.options = options
      self.game_records = GAME_RECORDS
      
      self.debuglevel = int(config.get_value('SectionGlobals', 'debuglevel', 0))
      if self.debuglevel == 2:
          self.debug_info = options['debug-extra_info']
      
      self.index_joueur_actif = 0    
      self.derniere_initialisation_round = -1
      self.players_G = []
      
      max_pv_init = int(self.options.get('number_of_lives', 50))
      self.structure_pv = max_pv_init
      self.max_structure_pv = max_pv_init
      self.feu_intensite = 0.0  
      self.foyers = {}            
      self.round_number = 1
      self.game_over = False
      self.victory = False
      self.feux_initialises = False
      self.secteur_vers_fenetre = {} # Grille de positionnement aléatoire des fenêtres
      
      self.target_jaune = bool(self.options.get('target_jaune', True))

      self.texture_feu = None
      try:
          full_path_feu = self.display.file_class.get_full_filename('incendie/flamme2', 'images')
          if full_path_feu and os.path.exists(full_path_feu):
              self.texture_feu = pygame.image.load(full_path_feu).convert_alpha()
      except Exception as e:
          print(f"[SOS INCENDIE] ERREUR chargement flamme2 : {e}")

      if self.texture_feu is None:
          try:
              if os.path.exists("flamme2.png"):
                  self.texture_feu = pygame.image.load("flamme2.png").convert_alpha()
          except Exception as e:
              print(f"[SOS INCENDIE] ERREUR alternative flamme2 : {e}")

      # Chargement de la texture de la vague d'eau pour le Bull
      self.texture_vague = None
      try:
          full_path_vague = self.display.file_class.get_full_filename('incendie/vague eau', 'images')
          if full_path_vague and os.path.exists(full_path_vague):
              self.texture_vague = pygame.image.load(full_path_vague).convert_alpha()
      except Exception as e:
          print(f"[SOS INCENDIE] ERREUR chargement vague eau : {e}")

      if self.texture_vague is None:
          try:
              if os.path.exists("vague eau.png"):
                  self.texture_vague = pygame.image.load("vague eau.png").convert_alpha()
          except Exception as e:
              print(f"[SOS INCENDIE] ERREUR alternative vague eau : {e}")

   def get_player_image_name(self, p, suffix):
      role_fallback = p.classe_nom.lower() if hasattr(p, 'classe_nom') and p.classe_nom else 'specialiste'
      test_img = f'incendie/{role_fallback}{suffix}'
      full_path = self.display.file_class.get_full_filename(test_img, 'images')
      
      if full_path and os.path.exists(full_path):
          return test_img
      else:
          return f'incendie/specialiste{suffix}'

   def pnj_score(self, players, actual_player, computer_level, player_launch):
        """
        Compute PNJ Score for cooperative firefighting game (e.g., SOS Incendie):
        - Manages targeted foyers (fires), structure health, and firefighter roles/classes.
        - Includes precision bounds, miss chances, and sequential dartboard ring offsets.
        """
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende des niveaux : [miss_chance, p_simple, p_double]
        #   * miss_chance : Probabilité de rater la cible et de dévier vers un secteur voisin (%)
        #   * p_simple    : Probabilité d'atteindre la cible en score simple (%)
        #   * p_double    : Probabilité d'atteindre la cible en score double (%)
        # - Plus fort / précis : Diminuer miss_chance, augmenter p_simple / p_double.
        # - Plus humain / brouillon : Augmenter miss_chance, diminuer p_simple / p_double.
        # =========================================================================
        
        current_player = players[actual_player]
        levels = [
            [50, 40, 8],   # Niveau 1
            [40, 45, 10],  # Niveau 2
            [30, 50, 10],  # Niveau 3
            [15, 60, 20],  # Niveau 4
            [0, 65, 25]    # Niveau 5
        ]
        
        lvl_idx = max(0, min(computer_level - 1, len(levels) - 1))
        miss_chance = levels[lvl_idx][0]
        p_simple = levels[lvl_idx][1]
        p_double = levels[lvl_idx][2]

        if self.foyers:
            target_chosen = random.choice(list(self.foyers.keys()))
        else:
            target_chosen = random.randint(1, 20)

        # Ordre physique des segments sur la cible de fléchettes (sens horaire standard)
        ordre_cible = [
            20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5
        ]

        rand_val = random.randrange(100)
        
        if rand_val < miss_chance:
            if self.foyers:
                CibleRatee = random.choice(list(self.foyers.keys()))
            else:
                CibleRatee = random.randint(1, 20)
                
            if CibleRatee in ordre_cible:
                idx_voisin = ordre_cible.index(CibleRatee)
                decalage = random.choice([-1, 1])
                chiffre_deporte = ordre_cible[(idx_voisin + decalage) % len(ordre_cible)]
            else:
                chiffre_deporte = random.randint(1, 20)
                
            return f'S{chiffre_deporte}'

        is_bull = (self.structure_pv < self.max_structure_pv * 0.7 and random.randrange(100) < 40) or not self.foyers
        if is_bull and random.randrange(100) < 30:
            return 'DB' if random.randrange(100) < 30 else 'SB'

        role = current_player.classe_nom.lower() if hasattr(current_player, 'classe_nom') else 'specialiste'
        
        if role in ['logisticien', 'specialiste', 'voltigeur'] and random.randrange(100) < 35:
            return f'T{target_chosen}'
        elif role == 'pompier' and random.randrange(100) < 45:
            return f'D{target_chosen}'
            
        elif rand_val < miss_chance + p_simple:
            return f'S{target_chosen}'
        elif rand_val < miss_chance + p_simple + p_double:
            return f'D{target_chosen}'
        else:
            return f'T{target_chosen}'
   
   def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        self.show_hit = True
        self.players_G = players

        # Calcul direct de la vie du bâtiment basé sur la charge actuelle des feux (Max 50 PV)
        if self.foyers:
            total_poids_feux = sum(int(etat) for etat in self.foyers.values())
            max_pv_init = int(self.options.get('number_of_lives', 50))
            self.structure_pv = max(0, max_pv_init - total_poids_feux)
            self.feu_intensite = min(100.0, (total_poids_feux / max_pv_init) * 100.0)
        else:
            self.feu_intensite = 0.0
            self.structure_pv = int(self.options.get('number_of_lives', 50))

        if self.structure_pv <= 0:
            self.structure_pv = 0
            self.game_over = True
        
        if self.game_over or self.victory:
            # --- AJOUT TROPHEES ---
            winning_player = players[self.winner].name if getattr(self, 'winner', -1) > -1 else "BOSS"
            ctrophies.check_game_end_stats(players, winning_player, "INCENDIE")
            return 3

        if actual_round == 1 and actual_player == 0 and player_launch == 1 and self.derniere_initialisation_round != 1:
            self.derniere_initialisation_round = 1
            
            # --- MÉLANGE ALÉATOIRE DES FENÊTRES SUR LE BÂTIMENT ---
            indices_fenetres = list(range(len(EMPLACEMENTS_FENETRES)))
            random.shuffle(indices_fenetres)
            self.secteur_vers_fenetre = {secteur: indices_fenetres[i] for i, secteur in enumerate(range(1, 21))}
            # ---------------------------------------------------

            roles_fixes = [
                ("Specialiste", "Dégâts massifs -- Simple = 3 hits"),
                ("Voltigeur", "Splash -- -1 sur foyer voisin"),
                ("Logisticien", "Simple = Jaune /  Orange -- Triple = Splash -1"),
                ("Pompier", "Débit Massif -- Simple = 2 hits")
            ]
            roles_attribues = list(roles_fixes)
            random.shuffle(roles_attribues)

            for i, player in enumerate(players):
                player.action_state = 'repos'  
                player.pouvoir_actif_tour = False
                idx = i % len(roles_attribues)
                player.classe_nom = roles_attribues[idx][0]
                player.pouvoir_desc = roles_attribues[idx][1]

                max_pv_init = int(self.options.get('number_of_lives', 50))
                player.lives = max_pv_init
                player.max_lives = max_pv_init
                player.alive = True
                player.score = 0

            self.foyers.clear()
            self.feu_intensite = 0.0
            self.structure_pv = max_pv_init
            self.feux_initialises = False
            self.display.display_background('incendie/bk_incendie')

        if player_launch == 1:
            self.round_number = actual_round
            if players[actual_player].alive:
                players[actual_player].action_state = 'repos'  
                players[actual_player].segments = ['--', '--', '--']
                
                if actual_round == 1 and actual_player == 0 and not self.feux_initialises:
                    disponibles = [s for s in range(1, 21) if s not in self.foyers]
                    if disponibles:
                        nb_depart = int(self.options.get('nb_feux_depart', 4))
                        nb_a_prendre = min(nb_depart, len(disponibles))
                        random.shuffle(disponibles) # Mélange strict
                        choix_init = disponibles[:nb_a_prendre]
                        for sec in choix_init:
                            self.foyers[sec] = 1
                    self.feux_initialises = True
                else:
                    for s in list(self.foyers.keys()):
                        self.foyers[s] = min(3, int(self.foyers[s]) + 1)

                    red_fires = [s for s, etat in self.foyers.items() if int(etat) == 3]
                    
                    if red_fires and random.choice([True, False]):
                        feu_source = random.choice(red_fires)
                        if feu_source in self.secteur_vers_fenetre:
                            idx_fenetre = self.secteur_vers_fenetre[feu_source]
                            r, c = idx_fenetre // 4, idx_fenetre % 4
                            voisins_potentiels = []
                            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                                nr, nc = r + dr, c + dc
                                if 0 <= nr < 5 and 0 <= nc < 4:
                                    idx_v = nr * 4 + nc
                                    for sec, p_idx in self.secteur_vers_fenetre.items():
                                        if p_idx == idx_v and sec not in self.foyers:
                                            voisins_potentiels.append(sec)
                            if voisins_potentiels:
                                ns_propagne = random.choice(voisins_potentiels)
                                self.foyers[ns_propagne] = 1
                    else:
                        disponibles = [s for s in range(1, 21) if s not in self.foyers]
                        if disponibles:
                            random.shuffle(disponibles) # Mélange les fenêtres libres
                            sec_jaune = disponibles[0]
                            self.foyers[sec_jaune] = 1

                if self.foyers:
                    self.feux_initialises = True

                if self.foyers:
                    self.feu_intensite = min(100.0, (len(self.foyers) / 20.0) * 100.0)
                else:
                    self.feu_intensite = 0.0

                players[actual_player].round_points = 0
                self.save_turn(players)
                players[actual_player].pre_play_score = players[actual_player].score

        players[actual_player].pouvoir_actif_tour = False
        segments = {}
        
        if self.foyers:
            total_poids_feux = sum(int(etat) for etat in self.foyers.values())
            max_pv_init = int(self.options.get('number_of_lives', 50))
            self.structure_pv = max(0, max_pv_init - total_poids_feux)
            self.feu_intensite = min(100.0, (total_poids_feux / max_pv_init) * 100.0)
        else:
            self.feu_intensite = 0.0
            self.structure_pv = int(self.options.get('number_of_lives', 50))

        if self.structure_pv <= 0:
            self.structure_pv = 0
            self.game_over = True
            
        if self.game_over or self.victory:
            return 3    

        if not self.game_over and not self.victory:
            for header, etat in self.foyers.items():
                e_val = int(etat)
                color_led = 'red' if e_val >= 3 else ('orange' if e_val == 2 else 'yellow')
                segments[f'S{header}'] = color_led
                segments[f'D{header}'] = color_led
                segments[f'T{header}'] = color_led

            segments['SB'] = 'blue'
            segments['DB'] = 'blue'
            
            segmentsAsStr = "|".join("{}#{}".format(*s) for s in segments.items())
            self.rpi.set_target_leds(segmentsAsStr)
            
        return 0
   
   def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        handler = self.init_handler()
        return_code = 0 
        current_player = players[actual_player]
        self.players_G = players

        if self.game_over or self.victory:
            return 3

        current_player.darts_thrown += self.score_map[hit]
        current_player.columns[player_launch - 1] = (hit[1:], 'int')
        current_player.segments[player_launch - 1] = hit
        
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)
        
        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)

        multi = self.get_hit_unit(hit) 
        multi_char = hit[0] if len(hit) > 0 else 'S'
        target_hit = int(hit[1:]) if hit not in ['SB', 'DB'] and len(hit) > 1 and hit[1:].isdigit() else -1
        role = current_player.classe_nom.lower()

        current_player.pouvoir_actif_tour = False

# --- CAS 1 : BULL'S EYE (SB ou DB) ---
        if hit in ['SB', 'DB']:
            self.display.play_sound('incendie_eau_crit')    
            current_player.pouvoir_actif_tour = True
            current_player.action_state = 'action'  
            self.show_hit = False

            red_fires = [s for s, etat in self.foyers.items() if int(etat) >= 3]

            if hit == 'SB':
                if red_fires:
                    cible = random.choice(red_fires)
                elif self.foyers:
                    cible = random.choice(list(self.foyers.keys()))
                else:
                    cible = None

                if cible and cible in self.foyers:
                    etat_cible = int(self.foyers[cible])
                    if etat_cible >= 3:
                        current_player.score += 30  
                    elif etat_cible == 2:
                        current_player.score += 20  
                    else:
                        current_player.score += 10  
                    del self.foyers[cible]

            elif hit == 'DB':
                cibles_possibles = red_fires[:]
                if len(cibles_possibles) < 2:
                    autres = [s for s in self.foyers.keys() if s not in cibles_possibles]
                    cibles_possibles.extend(random.sample(autres, min(2 - len(cibles_possibles), len(autres))))
                
                cibles = random.sample(cibles_possibles, min(2, len(cibles_possibles)))
                for cible in cibles:
                    if cible in self.foyers:
                        etat_cible = int(self.foyers[cible])
                        if etat_cible >= 3:
                            current_player.score += 30
                        elif etat_cible == 2:
                            current_player.score += 20
                        else:
                            current_player.score += 10
                        del self.foyers[cible]

            if not self.foyers:
                self.feu_intensite = 0.0
            else:
                self.feu_intensite = min(100.0, (len(self.foyers) / 20.0) * 100.0)

            self.animation_bull_vague(actual_player)
            current_player.action_state = 'repos'

# --- CAS 2 : INTERVENTION SUR UN FOYER (Secteurs 1 à 20) ---
        elif target_hit in range(1, 21):
            if target_hit in self.foyers:
                current_player.action_state = 'action'  
                
                effective_multi = multi
                
                if role == 'specialiste':
                    effective_multi = multi + 2
                    current_player.pouvoir_actif_tour = True
                elif role == 'pompier':
                    effective_multi = max(2, multi)
                    current_player.pouvoir_actif_tour = True
                elif role == 'logisticien':
                    etat_actuel = int(self.foyers[target_hit])
                    if etat_actuel <= 2:
                        effective_multi = 3 
                        current_player.pouvoir_actif_tour = True
                    
                    if multi_char == 'T':
                        current_player.pouvoir_actif_tour = True
                        # SPLASH LOGISTICICIEN BASÉ SUR LA GRILLE VISUELLE
                        if target_hit in self.secteur_vers_fenetre:
                            idx_f_cible = self.secteur_vers_fenetre[target_hit]
                            r, c = idx_f_cible // 4, idx_f_cible % 4
                            voisins_actifs = []
                            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                                nr, nc = r + dr, c + dc
                                if 0 <= nr < 5 and 0 <= nc < 4:
                                    idx_v = nr * 4 + nc
                                    for sec, p_idx in self.secteur_vers_fenetre.items():
                                        if p_idx == idx_v and sec in self.foyers and sec != target_hit:
                                            voisins_actifs.append(sec)
                            if voisins_actifs:
                                voisin_touche = random.choice(voisins_actifs)
                                self.foyers[voisin_touche] = int(self.foyers[voisin_touche]) - 1
                                if self.foyers[voisin_touche] <= 0:
                                    del self.foyers[voisin_touche]

                etat_initial = int(self.foyers[target_hit])

                if etat_initial >= 3:
                    current_player.score += 25  
                elif etat_initial == 2:
                    current_player.score += 15  
                else:
                    current_player.score += 5   

                if role == 'voltigeur':
                    # SPLASH VOLTIGEUR BASÉ SUR LA GRILLE VISUELLE
                    if target_hit in self.secteur_vers_fenetre:
                        idx_f_cible = self.secteur_vers_fenetre[target_hit]
                        r, c = idx_f_cible // 4, idx_f_cible % 4
                        voisins_actifs = []
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < 5 and 0 <= nc < 4:
                                idx_v = nr * 4 + nc
                                for sec, p_idx in self.secteur_vers_fenetre.items():
                                    if p_idx == idx_v and sec in self.foyers and sec != target_hit:
                                        voisins_actifs.append(sec)
                        if voisins_actifs:
                            voisin_touche = random.choice(voisins_actifs)
                            self.foyers[voisin_touche] = int(self.foyers[voisin_touche]) - 1
                            if self.foyers[voisin_touche] <= 0:
                                if voisin_touche in self.foyers:
                                    del self.foyers[voisin_touche]
                        current_player.pouvoir_actif_tour = True

                self.show_hd = False 
                self.show_hit = False

                coup_anim = min(max(effective_multi, 1), etat_initial)
                self.animation_combat(coup_anim, actual_player, target_hit=target_hit)    

                if not self.foyers:
                    self.feu_intensite = 0.0
                    
                current_player.action_state = 'repos'

            else:
                self.animation_rate(actual_player, multi_char=multi_char)
                current_player.score += 1
                self.show_hit = False
                

        if self.structure_pv <= 0:
            self.structure_pv = 0
            self.game_over = True

        if self.game_over or self.victory:
			
            return 3
        
        winner = self.check_winner(players, actual_round, player_launch, actual_player)
        if winner > -1:
            #trophee
            winning_player = players[winner].name if winner > -1 else "BOSS"
            ctrophies.check_game_end_stats(players, winning_player, "INCENDIE")
            return 3
        
        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        handler['return_code'] = return_code
        return handler

   def post_round_check(self, players, actual_round, actual_player):
        # 1. Propagation des feux pour le tour suivant de manière aléatoire
        if self.foyers:
            for s in list(self.foyers.keys()):
                self.foyers[s] = min(3, int(self.foyers[s]) + 1)

            red_fires = [s for s, etat in self.foyers.items() if int(etat) == 3]
            
            if red_fires and random.choice([True, False]):
                feu_source = random.choice(red_fires)
                idx = feu_source - 1
                r, c = idx // 4, idx % 4
                voisins_potentiels = []
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < 5 and 0 <= nc < 4:
                        ns = nr * 4 + nc + 1
                        if ns not in self.foyers:
                            voisins_potentiels.append(ns)
                if voisins_potentiels:
                    ns_propagne = random.choice(voisins_potentiels)
                    self.foyers[ns_propagne] = 1
            else:
                disponibles = [s for s in range(1, 21) if s not in self.foyers]
                if disponibles:
                    random.shuffle(disponibles) # Mélange pour un choix aléatoire (ex: 10, 15, 1, 12...)
                    sec_jaune = disponibles[0]
                    self.foyers[sec_jaune] = 1

        # 2. Recalcul immédiat des PV et de l'intensité après propagation
        if self.foyers:
            total_poids_feux = sum(int(etat) for etat in self.foyers.values())
            max_pv_init = int(self.options.get('number_of_lives', 50))
            self.structure_pv = max(0, max_pv_init - total_poids_feux)
            self.feu_intensite = min(100.0, (total_poids_feux / max_pv_init) * 100.0)
        else:
            self.feu_intensite = 0.0
            self.structure_pv = int(self.options.get('number_of_lives', 50))

        # 3. Si le bâtiment est détruit, on déclenche le Game Over instantané (intercepté par Pydarts)
        if self.structure_pv <= 0:
            self.structure_pv = 0
            self.game_over = True
            # --- AJOUT TROPHEES ---
            winning_player = players[self.winner].name if getattr(self, 'winner', -1) > -1 else "BOSS"
            ctrophies.check_game_end_stats(players, winning_player, "INCENDIE")
            return 3

        if not self.foyers:
            self.feu_intensite = 0.0
            winner = self.check_winner(players, actual_round, 3, actual_player)
            if winner > -1 or self.victory:
                # --- AJOUT TROPHEES ---
                winning_player = players[winner].name if winner > -1 else "BOSS"
                ctrophies.check_game_end_stats(players, winning_player, "INCENDIE")
                return 3

        if self.game_over or self.victory:
            # --- AJOUT TROPHEES ---
            winning_player = players[self.winner].name if getattr(self, 'winner', -1) > -1 else "BOSS"
            ctrophies.check_game_end_stats(players, winning_player, "INCENDIE")
            return 3
            
        return -2
        
   def check_winner(self, players, actual_round, player_launch, actual_player):
        if self.structure_pv <= 0:
            self.game_over = True

        partie_finie = False
        
        if getattr(self, 'feux_initialises', False):
            if len(self.foyers) == 0:
                self.victory = True
                partie_finie = True
            elif self.game_over:
                partie_finie = True

        if partie_finie:
            bestscoreid = -1
            bestscore = -1
            for player in players:
                if player.score > bestscore:
                    bestscore = player.score
                    bestscoreid = player.ident   
            
            self.winner = bestscoreid
            return bestscoreid
            
        return -1

   def refresh_stats(self, players, actual_round):
      for player in players:
         player.stats['Points Per Round'] = player.avg(actual_round)

   def display_segment(self):
        return self.show_hit

   def refresh_game_screen(self, players, actual_round, max_round, RemDarts, nb_darts, logo, headers, actual_player, TxtOnlogo=False, Wait=False, OnScreenButtons=None, showScores=True, end_of_game=False, endOfSet=None, Set=None, MaxSet=None):
      ClickZones = {}
      self.display.screen.fill((0, 0, 0))
      self.display.display_background('incendie/bk_incendie')
      self.affichage_players(players, actual_player, actual_round, max_round, end_of_game)
      
      if end_of_game :
          ClickZones = self.display.end_of_game_menu(logo, stat_button=False)

      self.display.update_screen()
      return ClickZones
     
   def early_player_button(self, players, actual_player, actual_round):
        if self.game_over or self.victory:
            ### trophee
            winning_player = players[self.winner].name if getattr(self, 'winner', -1) > -1 else "BOSS"
            ctrophies.check_game_end_stats(players, winning_player, "INCENDIE")
            return 3
        return 1

   def miss_button(self, players, actual_player, actual_round, player_launch):
        current_player = players[actual_player]
        
        if current_player.alive:
            current_player.segments[player_launch - 1] = 'MISS'
            self.animation_rate(actual_player, multi_char='S')
            self.show_hit = False

        return 0

   def animation_bull_vague(self, actual_player_idx):
        if not self.texture_vague:
            return

        screen_w = self.display.res['x']
        screen_h = self.display.res['y']

        bat_x = 510 * screen_w / 1920
        bat_y = 100 * screen_h / 1080
        bat_w = 980 * screen_w / 1920
        bat_h = 860 * screen_h / 1080

        nb_steps = 8
        total_height = bat_h + (200 * screen_h / 1080)
        step_distance = total_height / nb_steps

        for step in range(nb_steps):
            current_y = bat_y - (200 * screen_h / 1080) + (step * step_distance)
            
            vague_w = int(bat_w)
            vague_h = int(180 * screen_h / 1080)
            scaled_vague = pygame.transform.smoothscale(self.texture_vague, (vague_w, vague_h))

            self.display.screen.fill((0, 0, 0))
            self.display.display_background('incendie/bk_incendie')
            self.affichage_players(self.players_G, actual_player_idx, self.round_number, 5, False, skip_active_player_anim=False)

            self.display.screen.blit(scaled_vague, (bat_x, current_y))
            self.display.update_screen()
            time.sleep(0.015)

   def affichage_players(self, players, actual_player, actual_round, max_round, fin, skip_active_player_anim=False, force_vie1_indices=None):
        active_p = players[actual_player]
        
        if self.game_over:
            suffix = "-ko"
        elif self.victory or fin:
            suffix = "-win"
        elif not skip_active_player_anim:
            if hasattr(active_p, 'action_state') and active_p.action_state:
                suffix = f"-{active_p.action_state}"
            else:
                suffix = "-repos"
        else:
            suffix = ""
            
        screen_w = self.display.res['x']
        screen_h = self.display.res['y']
        
        bat_scalex = 1920 * screen_w / 1920
        bat_scaley = 1080 * screen_h / 1080
        bat_x = 0
        bat_y = 0
        
        if self.game_over:
            bat_img = 'incendie/batiment_detruit'
        elif self.feu_intensite >= 75:
            bat_img = 'incendie/batiment_critique'
        elif self.feu_intensite >= 50:
            bat_img = 'incendie/batiment_moyen'
        else:
            bat_img = 'incendie/batiment_sain'

        # --- UTILISATION DE LA GRILLE MÉLANGÉE ---
        secteur_vers_index = getattr(self, 'secteur_vers_fenetre', {})
        if not secteur_vers_index:
            indices_fenetres = list(range(len(EMPLACEMENTS_FENETRES)))
            random.shuffle(indices_fenetres)
            secteur_vers_index = {secteur: indices_fenetres[i] for i, secteur in enumerate(range(1, 21))}
            self.secteur_vers_fenetre = secteur_vers_index
        # ------------------------------------------

        for numero, etat in self.foyers.items():
            if numero in secteur_vers_index:
                idx_pos = secteur_vers_index[numero]
                if idx_pos < len(EMPLACEMENTS_FENETRES):
                    pos = EMPLACEMENTS_FENETRES[idx_pos]
                    pos_x = pos[0] * screen_w / 1920
                    pos_y = pos[1] * screen_h / 1080
                    w_vitre = LARGEUR_VITRE * screen_w / 1920
                    h_vitre = HAUTEUR_VITRE * screen_h / 1080

                    if self.texture_feu:
                        scaled_feu = pygame.transform.smoothscale(self.texture_feu, (int(w_vitre), int(h_vitre)))
                        self.display.screen.blit(scaled_feu, (pos_x, pos_y))
                        
                        e_val = int(etat)
                        overlay = pygame.Surface((int(w_vitre), int(h_vitre)), pygame.SRCALPHA)
                        if e_val >= 3:
                            overlay.fill((255, 0, 0, 120))    
                        elif e_val == 2:
                            overlay.fill((255, 140, 0, 120))  
                        elif e_val == 1:
                            overlay.fill((255, 255, 0, 120))  
                            
                        self.display.screen.blit(overlay, (pos_x, pos_y))

        bat_path = self.display.file_class.get_full_filename(bat_img, 'images')
        if bat_path and os.path.exists(bat_path):
            self.display.display_image(bat_path, bat_x, bat_y, bat_scalex, bat_scaley, True, False, False)

        for numero, etat in self.foyers.items():
            if numero in secteur_vers_index:
                idx_pos = secteur_vers_index[numero]
                if idx_pos < len(EMPLACEMENTS_FENETRES):
                    pos = EMPLACEMENTS_FENETRES[idx_pos]
                    pos_x = pos[0] * screen_w / 1920
                    pos_y = pos[1] * screen_h / 1080
                    w_vitre = LARGEUR_VITRE * screen_w / 1920
                    h_vitre = HAUTEUR_VITRE * screen_h / 1080
                    
                    self.display.blit_text(str(numero), pos_x, pos_y, w_vitre, h_vitre, color=(255, 255, 255))

        p_x = (20 + 45) * screen_w / 1920
        p_scalex = 536 * screen_w / 1920
        p_scaley = 464 * screen_h / 1080
        img_y = 10 * screen_h / 1080

        img_name = self.get_player_image_name(active_p, suffix)
        img_path = self.display.file_class.get_full_filename(img_name, 'images')
        
        if img_path and os.path.exists(img_path):
            self.display.display_image(img_path, p_x, img_y, p_scalex, p_scaley, True, False, False)

        list_start_y = img_y + p_scaley + 15 * screen_h / 1080
        bloc_w = 260 * screen_w / 1920
        hauteur_ligne_joueur = 140 * screen_h / 1080  

        for i, p in enumerate(players):
            ligne_y = list_start_y + (i * hauteur_ligne_joueur)

            if i == actual_player:
                couleur_nom = (255, 255, 0)  
                font_h = int(60 * screen_h / 1080)          
                font_role = int(48 * screen_h / 1080)       
                font_score = int(42 * screen_h / 1080)                       
                decalage_role = int(38 * screen_h / 1080)   
                decalage_score = int(66 * screen_h / 1080)  
            else:
                couleur_nom = (200, 200, 200) 
                font_h = int(42 * screen_h / 1080)          
                font_role = int(32 * screen_h / 1080)       
                font_score = int(30 * screen_h / 1080)                              
                decalage_role = int(30 * screen_h / 1080)   
                decalage_score = int(52 * screen_h / 1080)   

            self.display.blit_text(p.name, p_x, ligne_y, bloc_w, font_h, color=couleur_nom)
            self.display.blit_text(f"({p.classe_nom})", p_x, ligne_y + decalage_role, bloc_w, font_role, color=couleur_nom)
            self.display.blit_text(f"SC: {p.score}", p_x, ligne_y + decalage_score, bloc_w, font_score, color=(255, 255, 255))
            
        box_w, box_h = 300 * screen_w / 1920, 180 * screen_h / 1080  
        box_x = screen_w - box_w - int(10 * screen_w / 1920)
        box_y = screen_h - box_h - int(120 * screen_h / 1080)

        if active_p.alive:
            self.display.blit_rect(box_x, box_y, box_w, box_h, (20, 20, 20), Alpha=200)
            self.display.blit_text("STATUT POMPIER", box_x + int(10 * screen_w / 1920), box_y + int(10 * screen_h / 1080), box_w - int(20 * screen_w / 1920), int(40 * screen_h / 1080), color=(0, 255, 255))
            self.display.blit_text(f"Role : {active_p.classe_nom}", box_x + int(10 * screen_w / 1920), box_y + int(35 * screen_h / 1080), box_w - int(20 * screen_w / 1920), int(40 * screen_h / 1080), color=(255, 255, 0))
            
            desc = active_p.pouvoir_desc
            p1, p2 = desc, "" 

            if " -- " in desc:
                p1, p2 = desc.split(" -- ", 1)

            self.display.blit_text(p1, box_x + int(10 * screen_w / 1920), box_y + int(65 * screen_h / 1080), box_w - int(20 * screen_w / 1920), int(40 * screen_h / 1080), color=(255, 255, 255))
            if p2:
                self.display.blit_text(p2, box_x + int(10 * screen_w / 1920), box_y + int(95 * screen_h / 1080), box_w - int(20 * screen_w / 1920), int(40 * screen_h / 1080), color=(255, 255, 255))
        
        header_w = 600 * screen_w / 1920
        header_x = (screen_w - header_w) / 2
        header_y = 10 * screen_h / 1080
        
        self.display.blit_rect(header_x, header_y, header_w, 60 * screen_h / 1080, (0, 0, 0), Alpha=180)
        self.display.blit_text(f"STRUCTURE: {self.structure_pv}/{self.max_structure_pv}  -    FEU: {int(self.feu_intensite)}%", 
                               header_x, header_y, header_w, int(55 * screen_h / 1080), color=(255,255,255))

        seg_w = 300 * screen_w / 1920
        seg_h = 100 * screen_h / 1080
        seg_x = screen_w - seg_w - (20 * screen_w / 1920)
        seg_y = 20 * screen_h / 1080

        self.display.blit_rect(seg_x, seg_y, seg_w, seg_h, (0, 0, 0), Alpha=180)
        self.display.blit_text("/".join(players[actual_player].segments), 
                               seg_x, seg_y + (5 * screen_h / 1080), seg_w, int(75 * screen_h / 1080), color=(200,200,200))
                               
   def animation_combat(self, nb_coups, actual_player_idx, target_hit=None):
        current_player = self.players_G[actual_player_idx]
        
        for _ in range(max(1, nb_coups)):
            self.display.play_sound('incendie_jet_eau')
            
            if target_hit and target_hit in self.foyers:
                self.foyers[target_hit] = int(self.foyers[target_hit]) - 1

            current_player.action_state = 'action'
            self.display.screen.fill((0, 0, 0))
            self.display.display_background('incendie/bk_incendie')
            self.affichage_players(self.players_G, actual_player_idx, self.round_number, 5, False, skip_active_player_anim=False)
            self.display.update_screen()
            time.sleep(0.30)
            
            current_player.action_state = 'repos'
            self.display.screen.fill((0, 0, 0))
            self.display.display_background('incendie/bk_incendie')
            self.affichage_players(self.players_G, actual_player_idx, self.round_number, 5, False, skip_active_player_anim=False)
            self.display.update_screen()
            time.sleep(0.30)
        
        if target_hit and target_hit in self.foyers and self.foyers[target_hit] <= 0:
            del self.foyers[target_hit]
            current_player.score += 5  
            
        current_player.action_state = 'repos'

   def animation_rate(self, actual_player_idx, multi_char='S'):
        current_player = self.players_G[actual_player_idx]
        
        if multi_char == 'T':
            nb_fois = 3
        elif multi_char == 'D':
            nb_fois = 2
        else:
            nb_fois = 1
        
        for _ in range(nb_fois):  
            self.display.play_sound('incendie_erreur')
            current_player.action_state = 'rate'
            self.display.screen.fill((0, 0, 0))
            self.display.display_background('incendie/bk_incendie')
            self.affichage_players(self.players_G, actual_player_idx, self.round_number, 5, False, skip_active_player_anim=False)
            self.display.update_screen()
            time.sleep(0.25)
            
            current_player.action_state = 'repos'
            self.display.screen.fill((0, 0, 0))
            self.display.display_background('incendie/bk_incendie')
            self.affichage_players(self.players_G, actual_player_idx, self.round_number, 5, False, skip_active_player_anim=False)
            self.display.update_screen()
            time.sleep(0.25)
            
        current_player.action_state = 'repos'
