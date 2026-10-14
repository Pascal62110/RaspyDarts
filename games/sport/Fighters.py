# -*- coding: utf-8 -*-
# Game by David !
######

# Versions
# 1.00

from include import cplayer
from include import cgame
import random
##### TROPHEES
from include import ctrophies


VERSION = '1.00'
DEBUG = {'debug-extra_info': True} #je le force  à True pour le moment
# Dictionnay of options - Text format only
OPTIONS = {'theme': 'default', 'max_round': 20, 'number_of_lives': 15, 'points':False, 'colorised': False}
# background image - relative to images folder - Name it like the game itself
LOGO = 'Fighters.png' # background image
# Columns headers - Better as a string
HEADERS = ['D1', 'D2', 'D3', '', 'Hit', '', 'PPR']
# How many darts per player and per round ? Yes ! this is a feature :)
NB_DARTS = 3
# Dictionary of stats and display order (For example : Points Per Darts and avg are displayed in ascending order)
GAME_RECORDS = {'Points Per Round': 'DESC'}

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

      self.character = 0
      self.targets = []
      self.lives = 0
      self.segments = []
      self.alive = True
      # Init Player Records to zero
      for record in GAME_RECORDS:
         self.stats[record]='0'

class Game(cgame.Game):
   """
   Class of the real game
   """
   def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
      super().__init__(display, game, nb_players, options, config, logs,rpi, dmd, video_player)
      # For rpi
      self.rpi = rpi
      self.logo = LOGO
      self.headers = HEADERS
      self.nb_darts = NB_DARTS
      self.nb_players = nb_players

      self.game_is_ok_for_color = options['colorised']
      self.debug_info = False 
      self.options = options
      self.points = options['points']
      #  Get the maximum round number
      self.max_round = int(options['max_round'])
      # GameRecords is the dictionnary of stats (see above)
      self.game_records = GAME_RECORDS
      #  Get the maxiumum round number
      self.lives = int(options['number_of_lives'])
      self.game_ended = False  # Verrou pour empêcher le double comptage des stats/victoires

      # DEBUG dictionnary special for developer
      self.debuglevel = int(config.get_value('SectionGlobals', 'debuglevel', 0))
      if self.debuglevel == 2: #Ajouter les options du dictionnaire DEBUG
          #on charge les options (le dictionnaire DEBUG est inclus dans OPTIONS lorsque l'on est en debuglevel 2
          self.debug_info = options['debug-extra_info']
          #overwrite max_round to 2 for my test
          self.max_round = 2

   def pnj_score(self, players, actual_player, computer_level, player_launch):
        """
        Intelligence Artificielle (PNJ) pour le jeu Fighters :
        - Stratégie avancée : gestion des points de vie (danger, soins), opportunités de K.O. sur les adversaires vulnérables, et tirs tactiques sur le Bull.
        - Gère les 5 niveaux de difficulté avec taux de raté, déviation sur voisins géographiques et multiplicateurs (S, D, T).
        """
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende du format par niveau [miss_chance, simple_chance, double_chance] :
        #   * miss_chance   : Probabilité de rater la cible visée et de dévier vers un voisin (%)
        #   * simple_chance : Probabilité d'obtenir un Simple (S) si la cible est touchée (%)
        #   * double_chance : Probabilité d'obtenir un Double (D) (%)
        #   * Triple résiduel : Le reste est attribué au Triple (T)
        # - Statistiques additionnelles par niveau :
        #   * ko_chance     : Probabilité de tenter un K.O. ciblé [25%, 40%, 55%, 75%, 90%]
        #   * bull_chance   : Probabilité de viser le Bull [1%, 3%, 10%, 15%, 20%]
        # - Ajustement : Pour renforcer l'IA, réduis miss_chance et augmente les multiplicateurs.
        # =========================================================================

        current_player = players[actual_player]

        # Matrice géographique des voisins sur une cible de fléchettes standard
        geo_neighbors = {
            1: [20, 18, 4], 2: [17, 15, 10], 3: [19, 17, 2], 4: [18, 13, 1], 
            5: [20, 12, 9], 6: [10, 13, 15], 7: [19, 16, 8], 8: [16, 11, 7], 
            9: [14, 12, 5], 10: [15, 6, 2], 11: [14, 8, 16], 12: [9, 5, 20], 
            13: [6, 4, 11], 14: [9, 11, 16], 15: [10, 2, 6], 16: [7, 8, 11], 
            17: [2, 3, 15], 18: [4, 1, 20], 19: [7, 3, 2], 20: [1, 5, 12]
        }

        # Table de précision par niveau : [miss_chance, simple_chance, double_chance]
        levels = [
            [50, 75,  5],  # Niveau 1 (Noob) : 50% raté, 75% simple, 5% double
            [40, 72,  8],  # Niveau 2 (Débutant) : 40% raté, 72% simple, 8% double
            [30, 75, 15],  # Niveau 3 (Intermédiaire) : 30% raté, 75% simple, 15% double
            [10, 65, 22],  # Niveau 4 (Pro) : 10% raté, 65% simple, 22% double
            [ 0, 55, 25]   # Niveau 5 (Expert) : 0% raté, 55% simple, 25% double
        ]
        
        try:
            comp_lvl = int(computer_level)
        except (ValueError, TypeError):
            comp_lvl = 3

        lvl_idx = max(0, min(comp_lvl - 1, len(levels) - 1))
        miss_chance = levels[lvl_idx][0]
        p_simple = levels[lvl_idx][1]
        p_double = levels[lvl_idx][2]

        ko_probabilities = [25, 40, 55, 75, 90]
        ko_chance = ko_probabilities[lvl_idx]

        bull_probabilities = [1, 3, 10, 15, 20]
        bull_chance = bull_probabilities[lvl_idx]

        max_lives_ref = 300 if self.points else int(self.options['number_of_lives'])
        is_in_danger = current_player.lives < (max_lives_ref * 0.5)

        medic_target = current_player.targets[0] if current_player.targets else 20
        alive_opponents = [p for p in players if p.ident != actual_player and p.alive]

        target_chosen = None
        is_bull = False

        ko_target = None
        if self.points:
            for opp in alive_opponents:
                if opp.lives <= 3: 
                    for t in opp.targets:
                        ko_target = t
                        break
                if ko_target:
                    break

            if ko_target and random.randrange(100) < ko_chance:
                target_chosen = ko_target

        if not target_chosen and is_in_danger and medic_target:
            if self.points:
                if medic_target >= 10:
                    target_chosen = medic_target
            else:
                target_chosen = medic_target

        elif not target_chosen and len(alive_opponents) >= 2 and random.randrange(100) < bull_chance:
            is_bull = True
            db_chance = 0 if comp_lvl < 4 else (20 if comp_lvl == 4 else 40)
            return 'DB' if random.randrange(100) < db_chance else 'SB'

        elif not target_chosen:
            target_scores = {}
            for opp in alive_opponents:
                for t in opp.targets:
                    if t not in target_scores:
                        target_scores[t] = 0
                    target_scores[t] += t * (10 + opp.score)

            if target_scores:
                target_chosen = max(target_scores, key=target_scores.get)
            elif medic_target:
                target_chosen = medic_target
            else:
                target_chosen = 20

        if not is_bull:
            if random.randrange(100) < miss_chance:
                current_player.darts_thrown += 1
                if target_chosen in geo_neighbors:
                    target_chosen = random.choice(geo_neighbors[target_chosen])
                else:
                    target_chosen = random.randint(1, 20)
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
        """
        Actions done before each dart throw - for example, check if the player is allowed to play
        """
        if self.debug_info:
            info1=f"pre_dart_check players: actual_round, actual_player, player_launch"
            info2=f"pre_dart_check players: {actual_round: ^12}, {actual_player: ^13}, {player_launch: ^13}"
            self.affiche_info(info1, info2)
            
        return_code = 0

        self.show_hit = True

        if actual_round == 1 and player_launch == 1 and actual_player == 0:
            try:
                LST = self.check_handicap(players)
            except Exception as e:
                self.logs.error(f"Handicap failed : {e}")
            for player in players:
                player.score = 0

                if self.points :
                    self.lives = 300
                else :
                    self.lives = int(self.options['number_of_lives'])
                player.lives = self.lives
                player.alive = True
            self.display.display_background('bg_fighters')

            characters = []
            for player in players:
                if self.display.file_class.get_full_filename(f'fighters/{player.name}-1', 'images') is not None:
                    player.character = player.name
                else :
                    character = random.randint(1, 8)
                    while character in characters :
                        character = random.randint(1, 8)
                    player.character = f'j{character}'
                    characters.append(character)

        if player_launch == 1:
            players[actual_player].segments = ['__','__','__']
            players[actual_player].round_points = 0
            self.save_turn(players)
            players[actual_player].pre_play_score = players[actual_player].score

            medic = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
            for player in players:
                player.targets.clear()
                if actual_player != player.ident and player.lives > 0:
                    hits = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
                    for _ in range (0, 3) :
                        header = random.randint(0, len(hits) - 1)
                        player.targets.append(hits[header])
                        if hits[header] in medic :
                            medic.remove(hits[header])
                        hits.pop(header)

            h = random.randint(0, len(medic) - 1)
            players[actual_player].targets.append(medic[h])

        if not players[actual_player].alive :
            return_code  = 4
        else :
            segments = {}
            blinks = {}
            for player in players:
                if player.ident == actual_player:
                    color = 'green'
                    segments[f'S{player.targets[0]}'] = str(color)
                    segments[f'D{player.targets[0]}'] = str(color)
                    segments[f'T{player.targets[0]}'] = str(color)
                    segments[f'E{player.targets[0]}'] = str(color)
                else:
                    for header in player.targets:
                        color = 'red'
                        if segments.get(f'S{header}', None) is not None \
                                or blinks.get(f'S{header}', None) is not None:
                            blinks[f'S{header}'] = str(color)
                            blinks[f'D{header}'] = str(color)
                            blinks[f'T{header}'] = str(color)
                            blinks[f'E{header}'] = str(color)
                            if segments.get(f'S{header}', None) is not None:
                                segments.pop(f'S{header}')
                                segments.pop(f'D{header}')
                                segments.pop(f'T{header}')
                                segments.pop(f'E{header}')
                        else:
                            segments[f'S{header}'] = str(color)
                            segments[f'D{header}'] = str(color)
                            segments[f'T{header}'] = str(color)
                            segments[f'E{header}'] = str(color)

            segmentsAsStr = "|".join("{}#{}".format(*s) for s in segments.items())
            self.rpi.set_target_leds(segmentsAsStr)
            self.rpi.set_target_leds_blink("|".join("{}#{}".format(*s) for s in blinks.items()))

        return return_code

   def post_dart_check(self,hit,players,actual_round,actual_player,player_launch):
        """
        Post dart actions
        """
        handler = self.init_handler()
        
        if self.debug_info:
            info1=f"post_dart_check : hit, players, actual_round, actual_player, player_launch"
            info2=f"post_dart_check : {hit: ^3}, players, {actual_round: ^12}, {actual_player: ^13}, {player_launch: ^13}"
            self.affiche_info(info1, info2)
                  
        return_code = 0
         
        
        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)
        
        
                
        players[actual_player].darts_thrown += 1
        players[actual_player].columns[player_launch - 1] = (hit[1:], 'int')
        players[actual_player].segments[player_launch - 1] = hit

        # TROPHEES
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)
        


        multi = self.get_hit_unit(hit)

        if hit == 'SB' or hit == 'DB' :
            for player in players :
                if player.ident != actual_player and player.lives > 0:
                    if self.points :
                         player.lives -= self.score_map[hit]
                    else: 
                         player.lives -= multi
            if self.points :
                players[actual_player].score += self.score_map[hit]
            else: 
                players[actual_player].score+=(len(players))* multi
                
            handler['video'] = 'fighters/fighters_bull'
            self.show_hit = False
            
        else :
            if int(hit[1:]) in players[actual_player].targets :
                if self.points :
                    players[actual_player].lives += self.score_map[hit]
                else: 
                    players[actual_player].lives += multi
                    
                if players[actual_player].lives > self.lives :
                     players[actual_player].lives = self.lives
                handler['sound'] = 'fighters_medic'
                handler['video'] = 'fighters/fighters_medic'
                self.show_hit = False

            playerHitted = False
            for index, player in enumerate(players):
                if index != actual_player and int(hit[1:]) in player.targets :
                    if self.points :
                        players[actual_player].score += self.score_map[hit]
                        player.lives -= self.score_map[hit]
                    else: 
                        players[actual_player].score += multi
                        player.lives -= multi
                    players[actual_player].score += multi
                    players[actual_player].increment_hits(hit)
                    playerHitted = True
                    self.show_hit = False
                    
            if playerHitted :
                handler['video'] = 'fighters/fighters_hit'+str(multi)
            else:
                self.display.sound_for_touch(hit)

        for player in players:
            if player.lives <= 0 and player.alive:
                player.alive = False
                player.targets.clear()
                if self.points :
                         players[actual_player].lives += 30
                else: 
                         players[actual_player].score += 5
                handler['video'] = 'fighters/fighters_ko'

        winner = self.check_winner(players, actual_round, player_launch, actual_player)
        if winner > -1:
            handler['video'] = 'fighters/fighters_victory'
            self.winner = winner
            
            if not self.game_ended:
                self.game_ended = True
                winning_player = players[self.winner]
                ctrophies.check_game_end_stats(players, winning_player, "FIGHTERS")
            return 3
        
        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        handler['return_code'] = return_code
        return handler

   def post_round_check(self, players, actual_round, actual_player):
        if self.debug_info:
            info1=f"Post_round_check : players, actual_round, actual_player"
            info2=f"Post_round_check : players, {actual_round: ^12}, {actual_player: ^13}"
            self.affiche_info(info1, info2)
            
        check_winner = self.check_winner(players, actual_round, 3, actual_player)
        if check_winner >= 0:
            if not self.game_ended:
                self.game_ended = True
                winning_player = players[check_winner] if isinstance(check_winner, int) and 0 <= check_winner < len(players) else players[0]
                ctrophies.check_game_end_stats(players, winning_player, "FIGHTERS")
            return check_winner
        if actual_round < self.max_round:
            return -2
        else:
            best_id = self.check_winner(players, actual_round, 3, actual_player)
            if best_id >= 0 and not self.game_ended:
                self.game_ended = True
                winning_player = players[best_id] if isinstance(best_id, int) and 0 <= best_id < len(players) else players[0]
                ctrophies.check_game_end_stats(players, winning_player, "FIGHTERS")
            return best_id

   def check_winner(self, players, actual_round, player_launch, actual_player):
        if self.debug_info:
            info1=f"check_winner : players, actual_round, player_launch, actual_player"
            info2=f"check_winner : players, {actual_round: ^12}, {player_launch: ^13}, {actual_player: ^13}"
            self.affiche_info(info1, info2)
            
        alive_players = []
        for player in players :
            if player.alive :
                alive_players.append(player.ident)

        if len(alive_players) == 1 :
            self.winner =  alive_players[0]
            players[self.winner].score += 100
            return self.winner

        elif len(alive_players) == 0 or (player_launch == self.nb_darts and \
                actual_round >= self.max_round and actual_player == self.nb_players - 1):
            bestscoreid = -1
            bestscore = 0
            for player in players:
                if player.score >= bestscore:
                    if player.score != bestscore:
                        bestscore = player.score
                        bestscoreid = player.ident
                    else:
                        bestscoreid =  -1
            return bestscoreid
        return -1

   def refresh_stats(self, players, actual_round):
      """
      Method to frefresh player.stat - Adapt to the stats you want. They represent mathematical formulas used to calculate stats. Refreshed after every launch
      """
      for player in players:
         player.stats['Points Per Round'] = player.avg(actual_round)

   def display_segment(self):
       """
       Set if a message is shown to indicate the segment hitted !
       """
       return self.show_hit

   def refresh_game_screen(self, players, actual_round, max_round, RemDarts, nb_darts, logo, headers, actual_player,TxtOnlogo=False, Wait=False, OnScreenButtons=None, showScores=True, end_of_game=False, endOfSet=None, Set=None, MaxSet=None):
      """
      Refresh In-game screen
      """
      if self.debug_info:
          info1 = f"refresh_game_screen : players, actual_round, max_round, RemDarts, nb_darts, logo, headers, actual_player,TxtOnlogo=False, Wait=False, OnScreenButtons=None, showScores=True, end_of_game=False, endOfSet=None, Set=None, MaxSet=None"
          info2 = f"refresh_game_screen : players, {actual_round: ^12}, {max_round: ^9}, {RemDarts: ^8}, {nb_darts: ^8}, logo, headers, {actual_player: ^13}, {TxtOnlogo: ^15}, {Wait: ^10}, {str(OnScreenButtons): ^20}, {showScores: ^15}, {end_of_game: ^17}, {str(endOfSet): ^13}, {str(Set): ^8}, {str(MaxSet): ^11}"
          self.affiche_info(info1, info2, 110)
      ClickZones = {}

      self.display.screen.fill( (0, 0, 0) )
      self.display.display_background('bg_fighters')
      
      self.affichage_players(players, actual_player, actual_round, max_round, end_of_game)

      if end_of_game :
          ClickZones = self.display.end_of_game_menu(logo, stat_button=False)

      self.display.update_screen()

      return ClickZones
      
   def early_player_button(self, players, actual_player, actual_round):
       """
       Run when player push PLAYERBUTTON before last dart
       """
       if self.debug_info:
           info1=f"early_player_button : players, actual_player, actual_round"
           info2=f"early_player_button : players, {actual_player: ^13}, {actual_round: ^12}"
           self.affiche_info(info1, info2)
           
       return_code = 1
       win = self.check_winner(players, actual_round, self.nb_darts, actual_player)
       if win != -1:
           self.winner = win
           if not self.game_ended:
               self.game_ended = True
               winning_player = players[self.winner] if isinstance(self.winner, int) and 0 <= self.winner < len(players) else players[0]
               ctrophies.check_game_end_stats(players, winning_player, "FIGHTERS")
           return_code = 3
       else :
           last_player = False
           if actual_player == self.nb_players - 1:
               last_player = True
           else:
               k = self.nb_players - 1
               while k > actual_player:
                   if not players[k].alive :
                       last_player = True
                   else:
                       last_player = False
                   k -=1
                   
           if (actual_round >= self.max_round and last_player):            
               return_code = 2
       return return_code
    
   def miss_button(self, players, actual_player, actual_round, player_launch):
       """
       MISSED BUTTON
       """
       if self.debug_info:
           info1="miss_button : players, actual_player, actual_round, player_launch"
           info2=f"miss_button : players, {actual_player: ^13}, {actual_round: ^12}, {player_launch: ^13}"
           self.affiche_info(info1, info2)
           
       players[actual_player].segments[player_launch - 1] = ('MISS') 
       self.display.play_sound('miss')   
       return_code = 0
       return return_code

   def affichage_players(self, players, actual_player, actual_round, max_round, fin):
      if self.debug_info:
          info1=f"affichage_players : players, actual_player, actual_round, max_round, fin"
          info2=f"affichage_players : players, {actual_player: ^13}, {actual_round: ^12}, {max_round: ^9}, {fin: ^3}"
          self.affiche_info(info1, info2)
      colorset = self.display.colorset
      scalex = 368 * self.display.res['x'] / 1920
      scaley = 670 * self.display.res['y'] / 1080

      y = self.display.res['y'] / 2 - scaley / 2
      marge = int((self.display.res['x'] - len(players) * scalex) / (len(players) + 1))

      x = marge
      for i,p in enumerate(players):
          if actual_player == p.ident :
              level = 5
          elif p.lives > self.lives - (self.lives / 4) :
              level = 1
          else :
              level = int(5 - ((p.lives // (self.lives / 5)) + 1))

          self.display.display_image(self.display.file_class.get_full_filename(f'fighters/{p.character}-{level}', 'images'),x, y, scalex, scaley, True, False, False)
          self.logs.debug(f"character img loaded : {p.character}-{level}.png")

          if i == actual_player :
              self.display.blit_text(p.name, x, y + scaley, scalex, scaley / 4, color=colorset['fighters-actual-player'])
              self.display.display_image(self.display.file_class.get_full_filename('fighters/fighters_medic', 'images'),x + scalex / 2 - scalex / 6, y + scaley * 2 / 3, scalex / 3, scalex / 3, False, False, False)
              self.display.blit_text(str(p.targets[0]),x + scalex / 2 - scalex / 6, y + scaley * 2 / 3 + 20, scalex / 3, scalex / 3, color=colorset['fighters-medic'])
          elif p.alive :
              self.display.blit_text(p.name, x, y + scaley, scalex ,scaley / 4, color=colorset['fighters-alive-player'])
              self.display.display_image(self.display.file_class.get_full_filename('fighters/hit', 'images'),x, y, scalex / 3, scalex / 3, True, False, False)
              self.display.blit_text(str(p.targets[0]),x, y,scalex / 3,scalex / 4, color=colorset['fighters-targets'])
              self.display.display_image(self.display.file_class.get_full_filename('fighters/hit', 'images'),x + scalex - scalex / 3, y, scalex / 3, scalex / 3, True, False, False)
              self.display.blit_text(str(p.targets[1]),x + scalex - scalex / 3, y, scalex / 3, scalex / 4, color=colorset['fighters-targets'])
              self.display.display_image(self.display.file_class.get_full_filename('fighters/hit', 'images'),x + scalex / 2 - scalex / 6, y, scalex / 3, scalex / 3, True, False, False)
              self.display.blit_text(str(p.targets[2]),x + scalex / 2 - scalex / 6, y, scalex / 3,scalex / 4, color=colorset['fighters-targets'])
          elif colorset['fighters-dead-player'] is not None:
              self.display.blit_text(p.name, x, y + scaley, scalex ,scaley / 4, color=colorset['fighters-dead-player'])

          self.display.blit_text(str(p.lives),x + scalex / 5, y + scaley - scalex / 4, scalex / 3, scalex / 4, color=colorset['fighters-scores'])
          self.display.blit_text(str(p.score),x + scalex - scalex / 3, y + scaley - scalex / 4, scalex / 3, scalex / 4, color=colorset['fighters-scores'])

          if not p.alive :
              self.display.display_image(self.display.file_class.get_full_filename('fighters/fighters_ko', 'images'),x, y, scalex, scaley, True, False, False)

          x += scalex + marge

      self.display.blit_rect(self.display.res['x']/8 - scalex/2, 0, scalex,y*2/3, (0, 0, 0), Alpha=150)
      self.display.blit_text(f"{self.display.lang.translate('round')} {actual_round} / {max_round}" ,self.display.res['x']/8 - scalex/2,0,scalex, y/3, color=colorset['fighters-round'])

      self.display.blit_text(" / ".join(players[actual_player].segments) ,self.display.res['x']/8 - scalex/2,y/3,scalex,y/3, color=colorset['fighters-darts'])

   def affiche_info(self, info1, info2, split = 0, car = ','):
       if split > 0 and len(info1) > split :
           while (info1[split] != car) and (split > 0):
               split -= 1
           split += 1
           info = info1[:split] + '\n' + info2[:split]
           info2 = info1[split:] + '\n' + info2[split:]
           info1 = info
       print(info1)
       print(info2)
