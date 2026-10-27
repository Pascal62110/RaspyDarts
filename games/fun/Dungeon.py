# -*- coding: utf-8 -*-
# ==============================================================================
# JEU : DUNGEON DARTS (Mode Coop/Boss - Joueurs 1/5 plus petits)
# ==============================================================================

from include import cplayer
from include import cgame
import random
import time
import os
#### TROPHEES
from include import ctrophies


VERSION = '1.17'
DEBUG = {'debug-extra_info': False}

OPTIONS = {
    'theme': 'default', 
    'nb_boss': '7', 
    'number_of_lives': '15', 
    'number_of_targets': '5',
    'vie_premier_boss' : '10',
    'palier_pv_boss' : '2',
    'target_jaune': True,
}

LOGO = 'dungeon/bk_dungeon.png' 
HEADERS = [ 'D1', 'D2', 'D3', '', 'Hit', '', 'PPR']
NB_DARTS = 3
GAME_RECORDS = {'Points Per Round': 'DESC'}

def check_players_allowed(nb_players):
   return 0 < nb_players <= 4, VERSION, 4

class CPlayerExtended(cplayer.Player):
   def __init__(self, ident, nb_columns, interior=False):
      super().__init__(ident, nb_columns, interior)

      self.character = 0
      self.targets = []
      self.segments = ['--', '--', '--']
      self.action_state = '-1' 
      self.lives = 15
      self.max_lives = 15
      self.alive = True
      
      self.classe_nom = 'Guerrier'
      self.pouvoir_desc = 'S et T + 1'
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
      self.max_round = int(self.options['nb_boss'])
      self.game_records = GAME_RECORDS
      
      self.debuglevel = int(config.get_value('SectionGlobals', 'debuglevel', 0))
      if self.debuglevel == 2:
          self.debug_info = options['debug-extra_info']
      
      self.index_joueur_actif = 0    
      self.derniere_initialisation_round = -1
      self.players_G = []
      self.classes_disponibles = []
      self.bosses_tues = [] 
      self.last_boss_killer = -1 
      
      # Dictionnaire pour suivre les dégâts infligés par chaque joueur au boss actuel
      self.boss_damage = {}
      
      # Limité à 5 cibles max
      nb_targets_config = int(self.options.get('number_of_targets', 3))
      if nb_targets_config > 5:
            nb_targets_config = 5
      elif nb_targets_config < 3:
            nb_targets_config = 3
      
      # Récupération de la vie du premier boss depuis les options
      vie_base = int(self.options.get('vie_premier_boss', 10))
      
      # Palier PV boss en plus
      palier = int(self.options.get('palier_pv_boss', 3))
      
      self.pv_par_etage = {}
      for etage in range(1, 8):
            if etage == 1:
                self.pv_par_etage[etage] = vie_base
            else:
                self.pv_par_etage[etage] = vie_base + ((etage - 1) * palier)
        
      # Initialisation du boss au premier étage
      self.boss_lives = self.pv_par_etage[1]
      
      self.derniere_initialisation_round = -1
      
      self.target_jaune = bool(self.options.get('target_jaune', True))

   def get_player_image_name(self, p, suffix):
      p_name = p.name if hasattr(p, 'name') and p.name else f"j{p.ident+1}"
      test_img = f'dungeon/{p_name}{suffix}'
      full_path = self.display.file_class.get_full_filename(test_img, 'images')
      if full_path and os.path.exists(full_path):
          return test_img
      else:
          class_fallback = p.classe_nom.lower() if hasattr(p, 'classe_nom') else 'guerrier'
          return f'dungeon/{class_fallback}{suffix}'

   def pnj_score(self, players, actual_player, computer_level, player_launch):
        """
        Compute PNJ Score for Boss / RPG game (e.g., Boss Fight mechanics):
        - Handles class-specific behavior (e.g., Mage healing/targeting).
        - Manages boss targets, health checks, and geographic neighbor deviations.
        """
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende des niveaux : [miss_chance, p_simple, p_double]
        #   * miss_chance : Probabilité de rater la cible et de dévier vers un voisin géographique (%)
        #   * p_simple    : Probabilité d'obtenir un score simple (ou taux de réussite de base) (%)
        #   * p_double    : Probabilité d'obtenir un score double (%)
        # - Plus fort / précis : Diminuer miss_chance, augmenter p_double.
        # - Plus humain / brouillon : Augmenter miss_chance, diminuer p_double.
        # =========================================================================
        
        current_player = players[actual_player]
        
        geo_neighbors = {
            1: [20, 18, 4], 2: [17, 15, 10], 3: [19, 17, 2], 4: [18, 13, 1], 
            5: [20, 12, 9], 6: [10, 13, 15], 7: [19, 16, 8], 8: [16, 11, 7], 
            9: [14, 12, 5], 10: [15, 6, 2], 11: [14, 8, 16], 12: [9, 5, 20], 
            13: [6, 4, 11], 14: [9, 11, 16], 15: [10, 2, 6], 16: [7, 8, 11], 
            17: [2, 3, 15], 18: [4, 1, 20], 19: [7, 3, 2], 20: [1, 5, 12]
        }

        # Niveaux de difficulté [Chance d'erreur/raté, Chance simple, Chance double]
        levels = [
            [50, 75, 5],  # Niveau 1
            [40, 72, 8],  # Niveau 2
            [30, 75, 15], # Niveau 3
            [10, 65, 22], # Niveau 4
            [0, 55, 25]   # Niveau 5
        ]
        
        lvl_idx = max(0, min(computer_level - 1, len(levels) - 1))
        miss_chance = levels[lvl_idx][0]
        p_simple = levels[lvl_idx][1]
        p_double = levels[lvl_idx][2]

        boss_targets = current_player.targets if current_player.targets else (self.boss_targets if hasattr(self, 'boss_targets') else [20])
        players_missing_life = [p for p in players if p.lives < p.max_lives]
        is_mage = (current_player.classe_nom == 'Mage')

        target_chosen = None
        is_bull = False
        is_mage_double_target = False

        if is_mage and players_missing_life:
            target_chosen = random.randint(1, 20)
            is_mage_double_target = True
        elif current_player.lives < current_player.max_lives and random.randrange(100) < 50:
            target_chosen = 'DB' if random.randrange(100) < 30 else 'SB'
            is_bull = True
        else:
            target_chosen = random.choice(boss_targets) if boss_targets else 20

        if is_bull:
            if random.randrange(100) < miss_chance:
                current_player.darts_thrown += 1
                fallback = random.choice([20, 5, 1, 12])
                return f'S{fallback}'
            return target_chosen

        if random.randrange(100) < miss_chance:
            current_player.darts_thrown += 1
            if target_chosen in geo_neighbors:
                target_chosen = random.choice(geo_neighbors[target_chosen])
            return f'S{target_chosen}'

        if is_mage_double_target:
            rand_val = random.randrange(100)
            if rand_val < p_double:
                return f'D{target_chosen}'
            else:
                return f'S{target_chosen}'

        rand_val = random.randrange(100)
        if rand_val < p_simple:
            multi = 'S'
        elif rand_val < p_simple + p_double:
            multi = 'D'
        else:
            multi = 'T'

        return f'{multi}{target_chosen}'
   
   def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        self.show_hit = True
        self.players_G = players

        if not players[actual_player].alive:
            return 4

        if self.derniere_initialisation_round != actual_round and player_launch == 1 and actual_player == 0:
            self.derniere_initialisation_round = actual_round

            if actual_round == 1:
                classes_fixes = [
                    ("Guerrier", "S et T + 1"),
                    ("Mage", "D et T Soin de groupe"),
                    ("Voleur", "40% Esquive"),
                    ("Alchimiste", "T + 1 + 2pts")
                ]
                
                classes_attribuees = list(classes_fixes)
                random.shuffle(classes_attribuees)

                for i, player in enumerate(players):
                    player.action_state = '-1'
                    player.pouvoir_actif_tour = False
                    
                    idx = i % len(classes_attribuees)
                    player.classe_nom = classes_attribuees[idx][0]
                    player.pouvoir_desc = classes_attribuees[idx][1]

                    max_pv_init = int(self.options['number_of_lives'])
                    player.lives = max_pv_init
                    player.max_lives = max_pv_init
                    player.alive = True
                    player.score = 0

                self.bosses_tues.clear() 
                self.last_boss_killer = -1 

            self.display.display_background('dungeon/bk_dungeon')

        boss_id = min(len(self.bosses_tues) + 1, self.max_round)
        if not hasattr(self, 'boss_lives') or self.boss_lives <= 0:
            self.boss_lives = self.pv_par_etage.get(boss_id, 10)
            # Réinitialisation du dictionnaire des dégâts pour le nouveau boss
            self.boss_damage = {p.ident: 0 for p in players}
            
        if player_launch == 1:
            if players[actual_player].alive:
                players[actual_player].action_state = '-1'
                players[actual_player].segments = ['--', '--', '--']
                
                nb_targets_config = int(self.options.get('number_of_targets', 3))
                if nb_targets_config > 5:
                   nb_targets_config = 5
                elif nb_targets_config < 3:
                   nb_targets_config = 3
                   
                self.boss_targets = []
                boss_hits = list(range(1, 21))
                for _ in range(0, nb_targets_config):
                    if len(boss_hits) == 0:
                        break
                    b_header = random.randint(0, len(boss_hits) - 1)
                    self.boss_targets.append(boss_hits[b_header])
                    boss_hits.pop(b_header)

                players[actual_player].targets = list(self.boss_targets)
                players[actual_player].round_points = 0
                self.save_turn(players)
                players[actual_player].pre_play_score = players[actual_player].score

        if not hasattr(self, 'boss_targets') or not self.boss_targets:
            nb_targets_config = int(self.options.get('number_of_targets', 3))
            if nb_targets_config > 5:
               nb_targets_config = 5
            elif nb_targets_config < 3:
                nb_targets_config = 3
                
            self.boss_targets = []
            boss_hits = list(range(1, 21))
            for _ in range(0, nb_targets_config):
                if len(boss_hits) == 0:
                    break
                b_header = random.randint(0, len(boss_hits) - 1)
                self.boss_targets.append(boss_hits[b_header])
                boss_hits.pop(b_header)

        players[actual_player].pouvoir_actif_tour = False
        segments = {}

        if self.boss_lives > 0:
            if hasattr(self, 'boss_targets'):
                for header in self.boss_targets:
                    segments[f'S{header}'] = 'red'
                    segments[f'D{header}'] = 'red'
                    segments[f'T{header}'] = 'red'

            if self.target_jaune:
                for player in players:
                    if player.ident == actual_player and player.alive:
                        classe = player.classe_nom
                        if classe == 'Guerrier':
                            for header in self.boss_targets:
                                segments[f'S{header}'] = 'yellow'
                                segments[f'T{header}'] = 'yellow'
                        elif classe == 'Mage':
                            for i in range(1, 21):
                                segments[f'D{i}'] = 'yellow'
                                segments[f'T{i}'] = 'yellow'
                        elif classe == 'Alchimiste':
                            for header in self.boss_targets:
                                segments[f'T{header}'] = 'yellow'
                        elif classe == 'Voleur':
                            boss_set = set(self.boss_targets)
                            for i in range(1, 21):
                                if i not in boss_set:
                                    segments[f'S{i}'] = 'yellow'
                                    segments[f'D{i}'] = 'yellow'
                                    segments[f'T{i}'] = 'yellow'
                                    segments[f'E{i}'] = 'yellow'

            segments['SB'] = 'green'
            segments['DB'] = 'green'
            
            segmentsAsStr = "|".join("{}#{}".format(*s) for s in segments.items())
            self.rpi.set_target_leds(segmentsAsStr)
            
        return 0

   def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        handler = self.init_handler()
        return_code = 0 
        current_player = players[actual_player]
        self.players_G = players

        current_player.action_state = '-1'
        

        
        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)

        if self.boss_lives <= 0 or not current_player.alive:
            winner = self.check_winner(players, actual_round, player_launch, actual_player)
            if winner > -1 or len([p for p in players if p.alive]) == 0:
                self.winner = winner
                # Si tous les joueurs sont morts, on force l'affichage de la victoire du boss
                if len([p for p in players if p.alive]) == 0:
                    self.display.screen.fill((0, 0, 0))
                    self.display.display_background('dungeon/bk_dungeon')
                    # Force l'affichage du boss en mode vainqueur (ex: bossX-6)
                    boss_id = min(len(self.bosses_tues) + 1, self.max_round)
                    boss_scalex = 540 * self.display.res['x'] / 1920
                    boss_scaley = 547 * self.display.res['y'] / 1080
                    boss_x = (self.display.res['x'] - boss_scalex) / 2
                    boss_y = 140 * self.display.res['y'] / 1080
                    boss_img = f'dungeon/boss{boss_id}-6'
                    self.display.display_image(self.display.file_class.get_full_filename(boss_img, 'images'), boss_x, boss_y, boss_scalex, boss_scaley, True, False, False)
                    self.affichage_players(players, actual_player, actual_round, self.max_round, True)
                    self.display.update_screen()
                    self.display.play_sound('dungeon_ko')
                    time.sleep(2.0)
                return 3
            handler['return_code'] = return_code
            return handler

        current_player.darts_thrown += self.score_map[hit]
        current_player.columns[player_launch - 1] = (hit[1:], 'int')
        current_player.segments[player_launch - 1] = hit

        multi = self.get_hit_unit(hit) 
        multi_char = hit[0] if len(hit) > 0 else 'S'
        boss_id = min(len(self.bosses_tues) + 1, self.max_round)

        target_hit = int(hit[1:]) if hit not in ['SB', 'DB'] and len(hit) > 1 and hit[1:].isdigit() else -1
        est_cible_valide = (target_hit in current_player.targets) or (hit in ['SB', 'DB'])

        current_player.pouvoir_actif_tour = False

        if current_player.classe_nom == 'Mage' and (multi_char == 'D' or multi_char == 'T') and hit not in ['SB', 'DB']:
            current_player.pouvoir_actif_tour = True
            for p in players:
                if p.alive:
                    if multi_char == 'D':
                        p.lives += 1
                    elif multi_char == 'T':
                        p.lives += 2
						
                    if p.lives > p.max_lives:
                        p.lives = p.max_lives
            self.animation_soin(actual_player, boss_id, soin_global=True)

        if est_cible_valide:
            if current_player.classe_nom == 'Guerrier' and multi in [1, 3]:
                multi += 1  
                current_player.pouvoir_actif_tour = True

            elif current_player.classe_nom == 'Alchimiste' and multi == 3:
                multi += 1  
                current_player.score += 2  
                current_player.pouvoir_actif_tour = True

        if hit == 'SB' or hit == 'DB':
            #handler['sound'] = 'dungeon_crit'
            degats_bull = 1 if hit == 'SB' else 2
            
            if current_player.ident not in self.boss_damage:
                self.boss_damage[current_player.ident] = 0
            self.boss_damage[current_player.ident] += degats_bull

            current_player.lives += degats_bull
            if current_player.lives > current_player.max_lives:
                current_player.lives = current_player.max_lives

            current_player.score += degats_bull * 5
            self.show_hit = False
            self.animation_soin(actual_player, boss_id, soin_global=False)
				
        else:
            if est_cible_valide:
                #handler['sound'] = 'dungeon_hit'
                current_player.score += multi
                
                if current_player.ident not in self.boss_damage:
                    self.boss_damage[current_player.ident] = 0
                self.boss_damage[current_player.ident] += multi

                self.boss_lives -= multi
                if self.boss_lives < 0:
                    self.boss_lives = 0

                boss_vient_de_mourir = False

                if self.boss_lives <= 0 and boss_id not in self.bosses_tues:
                    self.bosses_tues.append(boss_id)
                    boss_vient_de_mourir = True
                    self.last_boss_killer = actual_player 
                    
                    total_degats_recueillis = sum(self.boss_damage.values())
                    pool_points = 50  
                    
                    for p in players:
                        degats_p = self.boss_damage.get(p.ident, 0)
                        if total_degats_recueillis > 0 and degats_p > 0:
                            points_gagnes = int((degats_p / total_degats_recueillis) * pool_points)
                            p.score += points_gagnes

                    self.display.screen.fill((0, 0, 0))
                    self.display.display_background('dungeon/bk_dungeon')
                    self.affichage_players(players, actual_player, actual_round, self.max_round, False)
                    self.display.update_screen()
    
                    self.display.play_sound('dungeon_win_stage')
                    time.sleep(1.0)
                            
                    next_boss_id = len(self.bosses_tues) + 1
                    if next_boss_id <= self.max_round:
                        self.boss_lives = self.pv_par_etage.get(next_boss_id, 45)
                        self.boss_damage = {p.ident: 0 for p in players} 
                        self.last_boss_killer = -1 

                current_player.increment_hits(hit)
                self.show_hit = False
                
                coup_anim = min(max(multi, 1), 3)
                if self.boss_lives > 0 and not boss_vient_de_mourir:
                    self.animation_combat(coup_anim, actual_player, boss_id)

            else:
                #handler['sound'] = 'dungeon_trap'
                esquive = False
                if current_player.classe_nom == 'Voleur' and random.randrange(100) < 40:  #% esquive voleur
                    esquive = True
                
                if multi_char == 'D':
                    degats_piege = 2
                elif multi_char == 'T':
                    degats_piege = 3
                else:
                    degats_piege = 1
                
                if esquive:
                    #self.display.play_sound('dungeon_dodge')
                    current_player.pouvoir_actif_tour = True 
                    self.animation_combat(degats_piege, actual_player, boss_id, is_defense=True, esquive=True)
                else:
                    current_player.lives -= degats_piege
                    if current_player.lives <= 0:
                        current_player.lives = 0
                        current_player.alive = False 
                        #handler['sound'] = 'dungeon_ko' 
                
                    self.show_hit = False
                    self.animation_combat(degats_piege, actual_player, boss_id, is_defense=True)

        # TROPHEES
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)

        winner = self.check_winner(players, actual_round, player_launch, actual_player)
        if winner > -1 or len([p for p in players if p.alive]) == 0:
            self.winner = winner
            winning_player = players[self.winner].name if self.winner > -1 else "BOSS"
            ctrophies.check_game_end_stats(players, winning_player, "DUNGEON")
            
            if len([p for p in players if p.alive]) == 0:
                self.display.screen.fill((0, 0, 0))
                self.display.display_background('dungeon/bk_dungeon')
                boss_id = min(len(self.bosses_tues) + 1, self.max_round)
                boss_scalex = 540 * self.display.res['x'] / 1920
                boss_scaley = 547 * self.display.res['y'] / 1080
                boss_x = (self.display.res['x'] - boss_scalex) / 2
                boss_y = 140 * self.display.res['y'] / 1080
                boss_img = f'dungeon/boss{boss_id}-6'
                self.display.display_image(self.display.file_class.get_full_filename(boss_img, 'images'), boss_x, boss_y, boss_scalex, boss_scaley, True, False, False)
                self.affichage_players(players, actual_player, actual_round, self.max_round, True)
                self.display.update_screen()
                self.display.play_sound('dungeon_ko')
                time.sleep(2.0)
            return 3
        
        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        handler['return_code'] = return_code
        return handler

   def post_round_check(self, players, actual_round, actual_player):
        check_winner = self.check_winner(players, actual_round, 3, actual_player)
        if check_winner >= 0:
            return check_winner
        if len(self.bosses_tues) < self.max_round:
            return -2
        else:
            return -1

 
   def check_winner(self, players, actual_round, player_launch, actual_player):
        alive_players = [p for p in players if p.alive]
        
        # Si tous les joueurs sont morts, le boss gagne (GAGNANT EST ENNEMI  -> return -1)
        if len(alive_players) == 0:
            return -1

        # Si tous les étages/boss ont été vaincus, on cherche le meilleur score parmi les survivants
        if len(self.bosses_tues) >= self.max_round:
            bestscoreid = -1
            bestscore = -1
            for player in players:
                if player.alive and player.score > bestscore:
                    bestscore = player.score
                    bestscoreid = player.ident
            return bestscoreid
            
        return -1
 
 
   '''
   def check_winner(self, players, actual_round, player_launch, actual_player):
        alive_players = [p for p in players if p.alive]
        
        
        if len(alive_players) == 0:
            bestscoreid = -1
            bestscore = -1
            for player in players:
                if player.score > bestscore:
                    bestscore = player.score
                    bestscoreid = player.ident
                elif player.score == bestscore:
                    bestscoreid = -1
            return bestscoreid

        if len(self.bosses_tues) >= self.max_round:
            bestscoreid = -1
            bestscore = -1
            for player in players:
                if player.alive and player.score > bestscore:
                    bestscore = player.score
                    bestscoreid = player.ident
            return bestscoreid
            
        return -1
   '''
   
   
   
   def refresh_stats(self, players, actual_round):
      for player in players:
         player.stats['Points Per Round'] = player.show_ppr()

   def display_segment(self):
        return self.show_hit

   def refresh_game_screen(self, players, actual_round, max_round, RemDarts, nb_darts, logo, headers, actual_player, TxtOnlogo=False, Wait=False, OnScreenButtons=None, showScores=True, end_of_game=False, endOfSet=None, Set=None, MaxSet=None):
      ClickZones = {}
      self.display.screen.fill((0, 0, 0))
      self.display.display_background('dungeon/bk_dungeon')
      self.affichage_players(players, actual_player, actual_round, max_round, end_of_game)
      
      if end_of_game :
          ClickZones = self.display.end_of_game_menu(logo, stat_button=False)

      self.display.update_screen()
      return ClickZones
     
   def early_player_button(self, players, actual_round, actual_player):
        win = self.check_winner(players, actual_round, self.nb_darts, actual_player)
        if win != -1:
            self.winner = win
            ###trophee
            winning_player = players[self.winner].name if self.winner > -1 else "BOSS"
            ctrophies.check_game_end_stats(players, winning_player, "DUNGEON")
            return 3
        return 1

   def miss_button(self, players, actual_player, actual_round, player_launch):
        current_player = players[actual_player]
        
        if current_player.alive:
            current_player.segments[player_launch - 1] = 'MISS'    
            self.display.play_sound('miss')   
            
            boss_id = min(len(self.bosses_tues) + 1, self.max_round)
            degats_piege = 1
            
            esquive = False
            if current_player.classe_nom == 'Voleur' and random.randrange(100) < 40:  #% d esquive
                esquive = True
            
            if esquive:
                #self.display.play_sound('dungeon_dodge')
                current_player.pouvoir_actif_tour = True 
                self.animation_combat(degats_piege, actual_player, boss_id, is_defense=False, esquive=True)
            else:
                current_player.lives -= degats_piege
                if current_player.lives <= 0:
                    current_player.lives = 0
                    current_player.alive = False 
                    sound_handler = 'dungeon_ko' 
                else:
                    sound_handler = 'dungeon_trap'
                
                self.display.play_sound(sound_handler)
                self.show_hit = False
                self.animation_combat(degats_piege, actual_player, boss_id, is_defense=True)

        # Vérification si tous les joueurs sont morts suite à ce miss
        if len([p for p in players if p.alive]) == 0:
            self.display.screen.fill((0, 0, 0))
            self.display.display_background('dungeon/bk_dungeon')
            boss_scalex = 540 * self.display.res['x'] / 1920
            boss_scaley = 547 * self.display.res['y'] / 1080
            boss_x = (self.display.res['x'] - boss_scalex) / 2
            boss_y = 140 * self.display.res['y'] / 1080
            boss_img = f'dungeon/boss{boss_id}-6'
            self.display.display_image(self.display.file_class.get_full_filename(boss_img, 'images'), boss_x, boss_y, boss_scalex, boss_scaley, True, False, False)
            self.affichage_players(players, actual_player, actual_round, self.max_round, True)
            self.display.update_screen()
            self.display.play_sound('dungeon_ko')
            time.sleep(2.0)
            return 3

        return 0

   def animation_soin(self, actual_player_idx, boss_id, soin_global=False):
        self.display.play_sound('dungeon_crit')
        if soin_global:
            indices_soignes = [i for i, p in enumerate(self.players_G) if p.alive]
        else:
            indices_soignes = [actual_player_idx]

        for frame in range(2): 
            self.display.screen.fill((0, 0, 0))
            self.display.display_background('dungeon/bk_dungeon')
            self.affichage_players(
                self.players_G, 
                actual_player_idx, 
                min(boss_id, self.max_round), 
                self.max_round, 
                False, 
                force_vie1_indices=indices_soignes
            )
            self.display.update_screen()
            time.sleep(0.4)
            
            
   def affichage_players(self, players, actual_player, actual_round, max_round, fin, skip_active_player_anim=False, force_vie1_indices=None):
     screen_w = self.display.res['x']
     screen_h = self.display.res['y']
     
     boss_scalex = 540 * screen_w / 1920
     boss_scaley = 547 * screen_h / 1080
     boss_x = (screen_w - boss_scalex) / 2
     boss_y = 140 * screen_h / 1080
     
     if self.boss_lives <= 0 and len(self.bosses_tues) > 0:
         boss_id = self.bosses_tues[-1]
     else:
         boss_id = min(len(self.bosses_tues) + 1, self.max_round)
     
     if self.winner >= 0:
         boss_img = f'dungeon/boss{boss_id}-6'
     elif self.boss_lives <= 0:
         boss_img = f'dungeon/boss{boss_id}-6'
     else:
         pv_max = self.pv_par_etage.get(boss_id, int(self.options['number_of_lives']))
         degats_boss = pv_max - self.boss_lives
         palier = pv_max / 5.0 if pv_max > 5 else 1.0
         niveau_degat_boss = min(int(degats_boss // palier), 4)
         niveau_degat_boss = max(0, niveau_degat_boss)
         boss_img = f'dungeon/boss{boss_id}-{niveau_degat_boss + 1}'

     self.display.display_image(self.display.file_class.get_full_filename(boss_img, 'images'), boss_x, boss_y, boss_scalex, boss_scaley, True, False, False)

     active_p = players[actual_player]
     if self.boss_lives > 0 and active_p.alive:
         nb_targets = len(active_p.targets)
         if nb_targets > 0:
             target_size = 90 * screen_w / 1920    
             boss_center_x = boss_x + (boss_scalex / 2)
             boss_center_y = boss_y + (boss_scaley / 3)  

             if nb_targets == 3:
                 offsets = [
                     (-260 * screen_w / 1920, -70 * screen_h / 1080),    
                     (0, -170 * screen_h / 1080),                      
                     (260 * screen_w / 1920, -70 * screen_h / 1080)    
                 ]
             elif nb_targets == 4:
                 offsets = [
                     (-280 * screen_w / 1920, -60 * screen_h / 1080),  
                     (-125 * screen_w / 1920, -165 * screen_h / 1080),  
                     (125 * screen_w / 1920, -165 * screen_h / 1080),   
                     (280 * screen_w / 1920, -60 * screen_h / 1080)    
                 ]
             elif nb_targets == 5:
                 offsets = [
                     (-280 * screen_w / 1920, -50 * screen_h / 1080),                         
                     (-180 * screen_w / 1920, -130 * screen_h / 1080),    
                     (0, -180 * screen_h / 1080),                                        
                     (180 * screen_w / 1920, -130 * screen_h / 1080),     
                     (280 * screen_w / 1920, -50 * screen_h / 1080)                           
                 ]
             else:
                 spacing = 15 * screen_w / 1920         
                 total_width_targets = nb_targets * target_size + (nb_targets - 1) * spacing
                 start_target_x = boss_x + (boss_scalex - total_width_targets) / 2
                 offsets = [(start_target_x + i * (target_size + spacing) - boss_center_x, -100 * screen_h / 1080) for i in range(nb_targets)]

             for idx_t, target_val in enumerate(active_p.targets):
                 if idx_t < len(offsets):
                     off_x, off_y = offsets[idx_t]
                     offset_x = boss_center_x + off_x - (target_size / 2)
                     offset_y = boss_center_y + off_y - (target_size / 2)

                     self.display.display_image(self.display.file_class.get_full_filename('dungeon/hit_target', 'images'), offset_x, offset_y, target_size, target_size, True, False, False)
                     self.display.blit_text(str(target_val), offset_x, offset_y, target_size, target_size, color=(255, 255, 255))

# --- SECTION POUVOIR ADAPTATIVE ---
     box_x = 40 * screen_w / 1920
     box_y = (screen_h / 3 - 30) * screen_h / 1080
     box_w, box_h = 360 * screen_w / 1920, 220 * screen_h / 1080

     if active_p.alive:
         box_w = 400 * screen_w / 1920
         box_h = 265 * screen_h / 1080
 
         self.display.blit_rect(box_x, box_y, box_w, box_h, (20, 20, 20), Alpha=170)
         
         # Redimensionnement proportionnel des polices selon la largeur de l'écran
         fs_titre = int(40 * screen_w / 1920)
         fs_classe = int(42 * screen_w / 1920)
         fs_desc = int(45 * screen_w / 1920)

         self.display.blit_text("POUVOIR", box_x, box_y + (10 * screen_h / 1080), box_w, fs_titre, color=(0, 255, 255))
         self.display.blit_text(f"{active_p.classe_nom}", box_x, box_y + (50 * screen_h / 1080), box_w, fs_classe, color=(255, 255, 0))
         
         if active_p.classe_nom == 'Guerrier':
             self.display.blit_text("Simple - Double", box_x + (10 * screen_w / 1920), box_y + (100 * screen_h / 1080), box_w - (20 * screen_w / 1920), fs_desc, color=(200, 200, 200))
             self.display.blit_text("Attaque +1", box_x + (10 * screen_w / 1920), box_y + (130 * screen_h / 1080), box_w - (20 * screen_w / 1920), fs_desc, color=(200, 200, 200))
             
         elif active_p.classe_nom == 'Mage':
             self.display.blit_text("Double +1 - Triple +2", box_x + (10 * screen_w / 1920), box_y + (100 * screen_h / 1080), box_w - (20 * screen_w / 1920), fs_desc, color=(200, 200, 200))
             self.display.blit_text("Soin collectif", box_x + (10 * screen_w / 1920), box_y + (130 * screen_h / 1080), box_w - (20 * screen_w / 1920), fs_desc, color=(200, 200, 200))
             
         elif active_p.classe_nom == 'Voleur':
             self.display.blit_text("40% d'esquive", box_x + (10 * screen_w / 1920), box_y + (115 * screen_h / 1080), box_w - (20 * screen_w / 1920), fs_desc, color=(200, 200, 200))
             
         elif active_p.classe_nom == 'Alchimiste':
             self.display.blit_text("Triple", box_x + (10 * screen_w / 1920), box_y + (90 * screen_h / 1080), box_w - (20 * screen_w / 1920), fs_desc, color=(200, 200, 200))
             self.display.blit_text("Attaque +1", box_x + (10 * screen_w / 1920), box_y + (130 * screen_h / 1080), box_w - (20 * screen_w / 1920), fs_desc, color=(200, 200, 200))
             self.display.blit_text("Score +2", box_x + (10 * screen_w / 1920), box_y + (155 * screen_h / 1080), box_w - (20 * screen_w / 1920), fs_desc, color=(200, 200, 200))
             
     center_y_bloc_gauche = box_y + (box_h / 2)
     zone_w = 420 * screen_w / 1920
     zone_x = screen_w - zone_w - (30 * screen_w / 1920)
     icon_size = 95 * screen_w / 1920
     espacement = 15 * screen_w / 1920
     hauteur_bloc_boss = (2 * icon_size) + 40 
     start_y = center_y_bloc_gauche - (hauteur_bloc_boss / 2)
     
     lignes = [4, 3] 
     b_idx = 1
     
     for l_idx, nb_items in enumerate(lignes):
         y_pos = start_y + (l_idx * (icon_size + 40)) 
         largeur_ligne = nb_items * icon_size + (nb_items - 1) * espacement
         start_x = zone_x + (zone_w - largeur_ligne) / 2
         
         for item_idx in range(nb_items):
             if b_idx > self.max_round: break
             x_pos = start_x + item_idx * (icon_size + espacement)
             boss_thumb = f'dungeon/boss{b_idx}'
             self.display.display_image(self.display.file_class.get_full_filename(boss_thumb, 'images'), x_pos, y_pos, icon_size, icon_size, True, False, False)
             
             if b_idx in self.bosses_tues:
                 self.display.display_image(self.display.file_class.get_full_filename('dungeon/cross_mark', 'images'), x_pos, y_pos, icon_size, icon_size, True, False, False)
             b_idx += 1

     p_scalex = (320 * screen_w / 1920) * 0.8
     p_scaley = (500 * screen_h / 1080) * 0.8
     p_y = screen_h - p_scaley - 20
     
     for i, p in enumerate(players):
         if skip_active_player_anim and i == actual_player:
             continue 

         if i < 2:
             marge_gauche = (screen_w / 2) - (2 * p_scalex)
             espacement_gauche = marge_gauche / 3
             x = espacement_gauche + i * (p_scalex + espacement_gauche)
         else:
             marge_droite = (screen_w / 2) - (2 * p_scalex)
             espacement_droite = marge_droite / 3
             x = (screen_w / 2) + espacement_droite + (i - 2) * (p_scalex + espacement_droite)
             
             
             

 # --- MODIFICATION ICI : Priorité au soin forcé si l'index est concerné ---
         if force_vie1_indices and i in force_vie1_indices and p.alive:
             p_img = self.get_player_image_name(p, '-vie1')
         elif not p.alive:
             p_img = self.get_player_image_name(p, '-6')
         elif self.winner >= 0 and self.winner == i:
             p_img = self.get_player_image_name(p, '-win')
         elif self.boss_lives <= 0 and self.last_boss_killer == i:
             p_img = self.get_player_image_name(p, '-win') 
         else:
             degats_perdus = p.max_lives - p.lives
             niveau_degat = min(max(degats_perdus // 3, 0), 4)
             p_img = self.get_player_image_name(p, f'-{niveau_degat + 1}') 

         self.display.display_image(self.display.file_class.get_full_filename(p_img, 'images'), x, p_y, p_scalex, p_scaley, True, False, False)

         
         if i == actual_player:
             couleur_nom = (255, 255, 0)  
             name_h = 35                  
             name_y = p_y - 35            
         else:
             couleur_nom = (255, 0, 0)    
             name_h = 25                  
             name_y = p_y - 30

         self.display.blit_text(f"{p.name} ({p.classe_nom})", x, name_y, p_scalex, name_h, color=couleur_nom)

         couleur_pv = (255, 0, 0) if p.lives <= 5 else (255, 255, 255)
         self.display.blit_text(str(p.lives), x + p_scalex / 5, p_y + p_scaley - p_scalex / 4, p_scalex / 3, p_scalex / 4, color=couleur_pv)
         self.display.blit_text(str(p.score), x + p_scalex - p_scalex / 3, p_y + p_scaley - p_scalex / 4, p_scalex / 3, p_scalex / 4, color=(200, 200, 200))
         
     active_p = players[actual_player]
     etat_pouvoir = getattr(active_p, 'pouvoir_actif_tour', False)
     
     if active_p.alive and etat_pouvoir:
         marge_gauche = (screen_w / 2) - (2 * p_scalex)
         espacement_gauche = marge_gauche / 3
         x_p2_fin = (espacement_gauche + 1 * (p_scalex + espacement_gauche)) + p_scalex
         
         marge_droite = (screen_w / 2) - (2 * p_scalex)
         espacement_droite = marge_droite / 3
         x_p3_debut = (screen_w / 2) + espacement_droite + (2 - 2) * (p_scalex + espacement_droite)
         
         mid_space_center_x = (x_p2_fin + x_p3_debut) / 2
         
         icon_w = 185 * screen_w / 1920
         ratio_hauteur_largeur = 674 / 370  
         icon_h = icon_w * ratio_hauteur_largeur
         icon_y_pos = p_y + (p_scaley / 2) - (icon_h / 2)
         
         classe_val = getattr(active_p, 'classe_nom', 'guerrier')
         nom_classe = str(classe_val).lower().strip()
         remplacements = {'é': 'e', 'è': 'e', 'ê': 'e', 'à': 'a', 'ù': 'u', 'û': 'u', 'î': 'i', 'ï': 'i', 'ô': 'o'}
         for accent, sans_accent in remplacements.items():
             nom_classe = nom_classe.replace(accent, sans_accent)
         
         logo_pouvoir = f'dungeon/icon_{nom_classe}'
         full_path = self.display.file_class.get_full_filename(logo_pouvoir, 'images')
         
         if full_path and os.path.exists(full_path):
             self.display.display_image(
                 full_path, 
                 mid_space_center_x - (icon_w / 2), 
                 icon_y_pos, 
                 icon_w, 
                 icon_h, 
                 True, False, False
             )
         else:
             print(f"[AVERTISSEMENT] Impossible de trouver l'icône de pouvoir : {logo_pouvoir}")
             
     header_w = 500 * screen_w / 1920
     header_x = (screen_w - header_w) / 2
     header_y = 10 * screen_h / 1080
     
     self.display.blit_rect(header_x, header_y, header_w, 60 * screen_h / 1080, (0, 0, 0), Alpha=180)
     current_stage_display = min(len(self.bosses_tues) + 1, self.max_round)
     self.display.blit_text(f"ETAGE {current_stage_display} / {max_round}  -  PV BOSS: {self.boss_lives}", 
                            header_x, header_y, header_w, 55, color=(255,255,255))

     seg_w = 300 * screen_w / 1920
     seg_h = 70 * screen_h / 1080
     seg_x = screen_w - seg_w - (20 * screen_w / 1920)
     seg_y = 20 * screen_h / 1080

     self.display.blit_rect(seg_x, seg_y, seg_w, seg_h, (0, 0, 0), Alpha=180)
     # Affichage au format --/--/--
     self.display.blit_text("/".join(players[actual_player].segments), 
                            seg_x, seg_y + 10, seg_w, 75, color=(200,200,200))

   def animation_combat(self, nb_coups, actual_player_idx, boss_id, is_defense=False, esquive=False):
        coups = 0
        screen_w = self.display.res['x']
        screen_h = self.display.res['y']
        
        boss_scalex = 540 * screen_w / 1920
        boss_scaley = 547 * screen_h / 1080
        boss_x = (screen_w - boss_scalex) / 2
        boss_y = 140 * screen_h / 1080 

        p_scalex = (320 * screen_w / 1920) * 0.8
        p_scaley = (500 * screen_h / 1080) * 0.8
        p_y = screen_h - p_scaley - 20

        if actual_player_idx < 2:
            marge_gauche = (screen_w / 2) - (2 * p_scalex)
            espacement_gauche = marge_gauche / 3
            p_x = espacement_gauche + actual_player_idx * (p_scalex + espacement_gauche)
        else:
            marge_droite = (screen_w / 2) - (2 * p_scalex)
            espacement_droite = marge_droite / 3
            p_x = (screen_w / 2) + espacement_droite + (actual_player_idx - 2) * (p_scalex + espacement_droite)

        p = self.players_G[actual_player_idx]

        while coups < max(1, nb_coups):
            coups += 1
            
            self.display.screen.fill((0, 0, 0))
            self.display.display_background('dungeon/bk_dungeon')
            self.affichage_players(self.players_G, actual_player_idx, min(boss_id, self.max_round), self.max_round, False, skip_active_player_anim=True)

            if esquive:
                boss_image_name = f'boss{boss_id}' 
                if coups == 1:
                    self.display.play_sound('dungeon_esquive')
                p_image_suffix = f'-esquive{coups}'  
            elif is_defense:
                boss_image_name = f'boss{boss_id}-hit{coups}'
                self.display.play_sound('dungeon_trap_sound')
                p_image_suffix = f'-touche{coups}'
            else:
                boss_image_name = f'boss{boss_id}-touche{coups}'
                self.display.play_sound('dungeon_hit_sound')
                p_image_suffix = f'-hit{coups}'

            boss_img_path = f'dungeon/{boss_image_name}'
            self.display.display_image(self.display.file_class.get_full_filename(boss_img_path, 'images'), boss_x, boss_y, boss_scalex, boss_scaley, True, False, False)
            
            p_img_path = self.get_player_image_name(p, p_image_suffix)
            self.display.display_image(self.display.file_class.get_full_filename(p_img_path, 'images'), p_x, p_y, p_scalex, p_scaley, True, False, False)

            if esquive:
                self.display.blit_text("ESQUIVE !", screen_w / 2 - 150, screen_h / 2 - 40, 300, 80, color=(0, 255, 255))

            self.display.update_screen()
            time.sleep(0.35)
