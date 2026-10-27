# -*- coding: utf-8 -*-
# Game by ... laDite!
########
import random
from include import cplayer
from include import cgame


### TROPHEES
from include import ctrophies

############
# Game Variables
############
OPTIONS = {'theme': 'default', 'max_round': 10, 'oper1': True, 'simple50': False}
GAME_RECORDS = {'Points Per Round': 'DESC', 'Points Per Dart': 'DESC'}
NB_DARTS = 3  # Total darts the player has to play
LOGO = 'Chaos.png'
HEADERS = ['D1', 'D2', 'D3', '', 'Round', '', ''] # Columns headers - Must be a string
VERSION = '1.00'

def check_players_allowed(nb_players):
    """
    Check if number of players is ok according to options
    """
    return nb_players >= 1 and nb_players <= 12, VERSION, 12
    
class CPlayerExtended(cplayer.Player):
    """
    Exetended player class
    """
    def __init__(self, ident, config):
        super(CPlayerExtended, self).__init__(ident, config)
        # Extend the basic players property with your own here
        # Init Player Records to zero
        for record in GAME_RECORDS:
            self.stats[record] = '0'

class Game(cgame.Game):
    """
    Chaos game class
    """
    def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
        super().__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)
        self.game_records = GAME_RECORDS
        self.nb_darts = NB_DARTS
        self.logo = LOGO
        self.headers = HEADERS
        self.options = options
        #  Get the maximum round number
        self.max_round = int(options['max_round'])
        self.simple = options['simple50']

        if self.simple:
            self.score_map.update({'SB': 50})
        else:
            self.score_map.update({'SB': 25})

        self.winner = None
        self.video_player = video_player
        self.targets = ''
        self.leds = True
        #  Penality points for a missing dart
        self.penality = 0 ###int(options['penalite']) 
        self.oper1 = options['oper1']
        self.dart1 = 'plus'
        self.dart2 = 'moins'
        self.dart3 = 'fois'
        self.div0 = 0
        self.div1 = 0
        self.div2 = 0
        self.multi0 = 0
        self.multi1 = 0
        self.multi2 = 0
        self.moins0 = 0
        self.moins1 = 0
        self.moins2 = 0
        self.game_ended = False  # Verrou pour empêcher le double comptage des stats/victoires
  
    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        """
        Actions done before each dart throw - for example, check if the player is allowed to play
        """
        return_code = 0
        
        if player_launch == 1:
            players[actual_player].reset_darts()
        
        # Set score at startup
        if actual_round == 1 and player_launch == 1 and actual_player == 0:
            try:
                self.check_handicap(players)
            except Exception as exception: # pylint: disable=broad-except
                self.logs.error(f"Handicap failed : {exception}")

            for player in players:
                # Init score
                player.score = 0
        
        if player_launch == 1 and actual_player == 0:  
            ### tire au sort les headers          
            listedarts = ['plus', 'moins', 'fois', 'div']    
            
            self.headers[2] = random.choice(listedarts)
            if self.oper1 :
                listedarts.remove(self.headers[2])

            self.headers[1] = random.choice(listedarts)
            if self.oper1 :
                listedarts.remove(self.headers[1])

            self.headers[0] = random.choice(listedarts)
            if self.oper1 :
                listedarts.remove(self.headers[0])
            
            ### tire au sort le multiplicateur du headers
            if self.headers[0] == 'fois' :
                    multi = [2,3,4]
                    self.headers[0] = '* ' + str(random.choice(multi))
                    self.multi0 = int(self.headers[0][-1])
            if self.headers[1] == 'fois' :
                    multi = [2,3,4]
                    self.headers[1] = '* ' + str(random.choice(multi))
                    self.multi1 = int(self.headers[1][-1])
            if self.headers[2] == 'fois' :
                    multi = [2,3,4]
                    self.headers[2] = '* ' + str(random.choice(multi))
                    self.multi2 = int(self.headers[2][-1])
            
            ### tire au sort le diviseur du headers        
            if self.headers[0] == 'div' :
                    multi = [2,3,4]
                    self.headers[0] = '/ ' + str(random.choice(multi))
                    self.div0 = int(self.headers[0][-1])
            if self.headers[1] == 'div' :
                    multi = [2,3,4]
                    self.headers[1] = '/ ' + str(random.choice(multi))
                    self.div1 = int(self.headers[1][-1])
            if self.headers[2] == 'div' :
                    multi = [2,3,4]
                    self.headers[2] = '/ ' + str(random.choice(multi))
                    self.div2 = int(self.headers[2][-1])

            ### tire au sort le multiplicateur de "MOINS' du headers        
            if self.headers[0] == 'moins' :
                    multi = [1,1,2,3,4]
                    self.headers[0] = ' -*' + str(random.choice(multi))
                    self.moins0 = int(self.headers[0][-1]) *-1
                    if self.headers[0] == ' -*1':
                        self.headers[0] = 'Moins'
                    
            if self.headers[1] == 'moins' :
                    multi = [1,1,2,3,4]
                    self.headers[1] = ' -*' + str(random.choice(multi))
                    self.moins1 = int(self.headers[1][-1]) *-1
                    if self.headers[1] == ' -*1': 
                        self.headers[1] = 'Moins'
                        
            if self.headers[2] == 'moins' :
                    multi = [1,1,2,3,4]
                    self.headers[2] = ' -*' + str(random.choice(multi))
                    self.moins2 = int(self.headers[2][-1]) *-1
                    if self.headers[2] == ' -*1':
                        self.headers[2] = 'Moins'

        # Each new player
        if player_launch == 1:
            players[actual_player].round_points = 0
            players[actual_player].pre_play_score = players[actual_player].score

            
            # Clean all next boxes
            for i in range(0,7):
                players[actual_player].columns.append(['', 'int'])
            
            if actual_round == 1 and actual_player == 0:
                for player in players:
                    player.reset_rounds(self.max_round)
 
        # Clean next boxes
        for i in range(player_launch - 1,self.nb_darts):
            players[actual_player].columns[i] = ('', 'int')
        
        # Print debug output
        self.logs.debug(self.infos)
        
        #self.rpi.set_target_leds('|'.join(self.targets))
        
        return return_code

    def pnj_score(self, players, actual_player, level, player_launch):
        """
        Compute PNJ Score for Chaos game:
        - Adapts strategy based on the arithmetic operator of the dart (+, *, / vs -, -*, Moins).
        - Includes difficulty levels, dartboard neighbors, and misses.
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

        levels = [
            [15, 35, 50],  # Niveau 1
            [30, 40, 30],  # Niveau 2
            [40, 30, 20],  # Niveau 3
            [70, 20, 10],  # Niveau 4
            [85, 10, 5]    # Niveau 5
        ]
        
        lvl_idx = max(0, min(level - 1, len(levels) - 1))
        p_success = levels[lvl_idx][0]
        p_neighbor = levels[lvl_idx][1]

        rand_val = random.randrange(100)

        # Récupération de l'en-tête/opérateur pour la fléchette actuelle (player_launch: 1 à 3)
        header_idx = max(0, min(player_launch - 1, 2))
        current_header = str(self.headers[header_idx])

        # Détermination du mode : min de points (-, -*, Moins) ou max de points (+, *, /)
        is_min_mode = '-' in current_header or 'Moins' in current_header

        if not is_min_mode:
            # Mode MAX de points (+, *, /) : Visée agressive (T20, T19, S20)
            target_type = random.choice(['T', 'S', 'T'])
            target_num = 20 if target_type == 'T' else random.choice([20, 19, 18])
            
            if rand_val < p_success:
                return f"{target_type}{target_num}"
            elif rand_val < p_success + p_neighbor:
                neighbor = random.choice(dartboard_neighbors.get(target_num, (20, 18)))
                return f"{target_type}{neighbor}"
            else:
                return f"S{random.randint(1, 20)}"
        else:
            # Mode MIN de points (-, -*, Moins) : Visée prudente sur petits scores (S1, S5, S2...)
            low_targets = [1, 5, 2, 3, 12, 9]
            target_num = random.choice(low_targets)
            target_type = 'S'

            if rand_val < p_success:
                return f"{target_type}{target_num}"
            elif rand_val < p_success + p_neighbor:
                neighbor = random.choice(dartboard_neighbors.get(target_num, (20, 18)))
                return f"{target_type}{neighbor}"
            else:
                return f"S{random.choice([1, 20, 5])}"

    def best_score(self, players):
        """
        Find the winner
        Only one player with best score
        """
        best_player = None
        best_score = None
        best_count = 0
        for player in players:
            if best_score is None or player.score > best_score:
                best_score = player.score
                best_player = player.ident
                best_count = 1
                self.logs.debug(\
                        f"Best found : {best_score} / Count={best_count} / player = {best_player}")
            elif player.score == best_score:
                best_count += 1

        self.logs.debug(\
                f"Best score : {best_score} / Count={best_count} / Player = {best_player}")

        if best_count == 1:
            return best_player
        return -1

    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        """
        Function run after each dart throw - for example, add points to player
        """
        handler = self.init_handler()
        
        self.display.sound_for_touch(hit)

        score = 0
        
        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)
 
 
        #if (hit and actual_round < self.max_round) or (hit and actual_round == self.max_round and player_launch < 3) : 
        if (hit) :
                print('condition  1-2 fleche')
                if player_launch == 1 :
                        operat = self.headers[0][-3]
                        if operat == 'l' :
                                score = score + self.score_map[hit] 
                        elif operat == '-' or operat == 'i' :
                                score = self.score_map[hit] * self.moins0
                        elif operat == '*' :
                                score = self.score_map[hit] * self.multi0
                        elif operat == '/' :
                                score = round(self.score_map[hit] / self.div0)  
             
                if player_launch == 2 :
                        operat = self.headers[1][-3]
                        if operat == 'l' :
                                score = score + self.score_map[hit] 
                        elif operat == '-' or operat == 'i' :
                                score = self.score_map[hit] * self.moins1
                        elif operat == '*' :
                                score = self.score_map[hit] * self.multi1
                                
                        elif operat == '/' :
                                score = round(self.score_map[hit] / self.div1)     
                                
                if player_launch == 3 :
                        operat = self.headers[2][-3]
                        if operat == 'l' :
                                score = score + self.score_map[hit] 
                        elif operat == '-' or operat == 'i' :
                                score = self.score_map[hit] * self.moins2
                        elif operat == '*' :
                                score = self.score_map[hit] * self.multi2
                        elif operat == '/' :
                                score = round(self.score_map[hit] / self.div2)     

        return_code = 0

        players[actual_player].add_dart(actual_round, player_launch, hit, score=score)
        
        
        # TROPHEES
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)
        
        
        if actual_round < self.max_round and player_launch < 3 :
            players[actual_player].score += score
        else :
            players[actual_player].score += score
        players[actual_player].round_points += score
        players[actual_player].points += score

        
        # Store what he played in the table
        players[actual_player].columns[player_launch - 1] = (score, 'int', 'game-silver')
        # Store total for the round in column 6 (start from 0)
        players[actual_player].columns[4] = (players[actual_player].round_points, 'int', 'game-silver')
        
        # Record total dart thrown, total hits (S=1, D=2, T=3) and refresh players stats
        players[actual_player].darts_thrown += 1
        players[actual_player].increment_hits(hit)
        self.refresh_stats(players, actual_round)
        
        # Check last round
        if player_launch == self.nb_darts and actual_round >= self.max_round \
                and actual_player == len(players) - 1:
            self.winner = self.check_winner(players)
            self.infos += f"Last round reached ({actual_round}){self.lf}"
            return_code = 2


        if self.winner is not None:
            if not self.game_ended:
                self.game_ended = True
                winning_player = players[self.winner]
                ctrophies.check_game_end_stats(players, winning_player, "CHAOS")    
            return_code = 3

        self.logs.debug(self.infos)

        # Time for shot or video ?
        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        handler['return_code'] = return_code
        return handler

    def miss_button(self, players, actual_player, actual_round, player_launch):
        '''
        Miss button
        '''
        if player_launch == 1 :
                operat = self.headers[0][-3]
                if operat == 'l' :
                        score = 0
                elif operat == '-' or operat == 'i' :
                        score = 20 * self.moins0
                elif operat == '*' :
                        score = 0  ##1 * self.multi0
                elif operat == '/' :
                        score = 0  
             
        if player_launch == 2 :
                operat = self.headers[1][-3]
                if operat == 'l' :
                        score = 0
                elif operat == '-' or operat == 'i' :
                        score = 20 * self.moins1
                elif operat == '*' :
                        score = 0  ##1 * self.multi1
                                
                elif operat == '/' :
                        score = 0
                                
        if player_launch == 3 :
                operat = self.headers[2][-3]
                if operat == 'l' :
                        score = 0
                elif operat == '-' or operat == 'i' :
                        score = 20 * self.moins2
                elif operat == '*' :
                        score = 0  ##1 * self.multi2
                elif operat == '/' :
                        score = 0  
        
        self.penality = score
         
        players[actual_player].score += self.penality
        players[actual_player].columns[player_launch-1] = (score, 'int', 'game-red')
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
        
        self.display.message([self.display.lang.translate('Color-miss')], 1000, None, 'middle', 'big')
    
    def post_round_check(self, players, actual_round, actual_player):
        """
        Post round checks
        When PLAYER BUTTON is pressed on last round of last player
        """

        if actual_round >= self.max_round and actual_player == len(players) - 1:
            # Last round, last player
            winner = self.best_score(players)
            if winner != -1:
                if not self.game_ended:
                    self.game_ended = True
                    winning_player = next((p for p in players if p.ident == winner), players[winner] if isinstance(winner, int) and winner < len(players) else None)
                    if winning_player:
                        ctrophies.check_game_end_stats(players, winning_player, "CHAOS")
            return winner
        return -2
    
    def get_score(self, player):
        """
        Return score of player
        """
        return player.score

    def next_set_order(self, players):
        """
        Sort players for next set
        """
        players.sort(key=self.get_score)

    def refresh_stats(self, players, actual_round):
        """
        refresh players' stats
        """
        for player in players:
            player.stats['Points Per Round'] = player.show_ppr()
            player.stats['Points Per Dart'] = player.show_ppd()

    def display_segment(self):
       """
       Set if a message is shown to indicate the segment hitted !
       """
       return False
