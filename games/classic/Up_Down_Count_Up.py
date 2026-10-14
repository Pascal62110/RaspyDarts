# -*- coding: utf-8 -*-
"""
Game by ... David !
"""

from include import cplayer
from include import cgame
import random

### TROPHEES
from include import ctrophies

OPTIONS = {'theme': 'default', 'max_round': 10, 'penalty': 50, 'start_negative': False}
GAME_RECORDS = {'Points Per Round': 'DESC', 'Points Per Dart': 'DESC'}
NB_DARTS = 3
LOGO = 'Up_Down_Count_Up.png'
HEADERS = ['D1', 'D2', 'D3', '+/-', '', 'PPD', 'PPR']
VERSION = '1.00'

def check_players_allowed(nb_players):
    """
    Check if number of players is ok according to options
    """
    return nb_players >= 1 and nb_players <= 12, VERSION, 12
    
class CPlayerExtended(cplayer.Player):
    """
    Extend the basic player
    """
    def __init__(self, ident, nb_columns, interior=False):
        super().__init__(ident, nb_columns, interior)
        # Extend the basic players property with your own here
        # Init Player Records to zero
        for record in GAME_RECORDS:
            self.stats[record] = '0'

class Game(cgame.Game):
    """
    Up Down class game
    """
    # Like player_launch but not visible inside method early_player_button
    nb_darts_hit_in_turn = 0

    def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
        super().__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)

        # Dictionary of stats and display order
        self.game_records = GAME_RECORDS
        self.nb_darts = NB_DARTS  # Total darts the player has to play
        self.logo = LOGO
        self.headers = HEADERS

        self.options = options
        #  Get the maximum round number
        self.max_round = int(options['max_round'])
        #  penalty points for a missing dart
        self.penalty = int(options['penalty'])
        # start the game with a negative round
        self.negative = options['start_negative']

        self.actual_round = 1
        self.winner = None
        self.rate = 0

    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        """
        Actions done before each dart throw - for example, check if the player is allowed to play
        """
        self.actual_round = actual_round
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
                player.reset_rounds(self.max_round)

        # Each new player
        if player_launch == 1:
            self.nb_darts_hit_in_turn = 0

            players[actual_player].round_points = 0
            self.save_turn(players)
            players[actual_player].pre_play_score = players[actual_player].score

            #Reset display Table
            players[actual_player].columns = []
            # Clean all next boxes
            for _ in range(0, 7):
                players[actual_player].columns.append(['', 'int'])

            # show the type of actual Round
            if self.is_positive_round(actual_round):
                self.display.message([self.display.lang.translate('UDCP-tourpos')], \
                        3000, 'blue', 'middle', 'huge')
                players[actual_player].columns[3] = ('+', 'string')
            else:
                self.display.message([self.display.lang.translate('UDCP-tourneg')], \
                        3000, 'red', 'middle', 'huge')
                players[actual_player].columns[3] = ('-', 'string')

        # Display stats
        if actual_round == 1 and player_launch == 1:
            players[actual_player].columns[5] = (0.0, 'int')
            players[actual_player].columns[6] = (0.0, 'int')
        else:
            players[actual_player].columns[5] = (players[actual_player].show_ppd(), 'int')
            players[actual_player].columns[6] = (players[actual_player].avg(actual_round), 'int')

        # Print debug output
        self.logs.debug(self.infos)
        return return_code

    def pnj_score(self, players, actual_player, computer_level, player_launch):
        """
        Compute PNJ Score for Up Down game using matrix neighbors and round direction.
        """
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende des niveaux : [miss_chance, exact_target_chance, neighbor_chance, double_chance, triple_chance]
        #   * miss_chance         : Taux de raté pur (miss, 'MISSDART', %)
        #   * exact_target_chance : Précision / probabilité de toucher exactement la cible choisie (%)
        #   * neighbor_chance     : Taux de glissement vers un voisin géographique sur la matrice (%)
        #   * double_chance       : Probabilité ou seuil de réussite pour les doubles (%)
        #   * triple_chance       : Probabilité ou seuil de réussite pour les triples (%)
        # - Plus fort / précis : Diminuer le miss_chance, augmenter exact_target_chance et neighbor_chance.
        # - Plus humain / brouillon : Augmenter le miss_chance.
        # =========================================================================
        geo_neighbors = {
            1: [20, 18, 4], 2: [17, 15, 10], 3: [19, 17, 2], 4: [18, 13, 1], 
            5: [20, 12, 9], 6: [10, 13, 15], 7: [19, 16, 8], 8: [16, 11, 7], 
            9: [14, 12, 5], 10: [15, 6, 2], 11: [14, 8, 16], 12: [9, 5, 20], 
            13: [6, 4, 11], 14: [9, 11, 16], 15: [10, 2, 6], 16: [7, 8, 11], 
            17: [2, 3, 15], 18: [4, 1, 20], 19: [7, 3, 2], 20: [1, 5, 12]
        }

        # [miss_chance, exact_target_chance, neighbor_chance, double_chance, triple_chance]
        levels = [
            [35, 10, 30, 10, 10],  # 1 : Noob
            [20, 25, 40, 15, 15],  # 2 : Débutant
            [ 5, 50, 60, 25, 30],  # 3 : Intermédiaire
            [ 1, 80, 80, 40, 50],  # 4 : Pro
            [ 0, 95, 90, 60, 70]   # 5 : Expert
        ]

        lvl_idx = max(0, min(computer_level - 1, len(levels) - 1))

        if random.randrange(100) < levels[lvl_idx][0]:
            players[actual_player].darts_thrown += 1
            self.rate += 1
            return 'MISS'

        is_pos = self.is_positive_round(self.actual_round)

        # Choix de la cible privilégiée selon le tour (positif = gros chiffres, négatif = petits chiffres)
        if is_pos:
            preferred_targets = [20, 19, 18, 17, 16]
        else:
            preferred_targets = [1, 2, 3, 4, 5, 20]

        base_target = random.choice(preferred_targets)

        # Utilisation de la matrice de voisinage
        rand_val = random.randrange(100)
        if rand_val < levels[lvl_idx][1]:
            segment = base_target
        elif base_target in geo_neighbors and rand_val < levels[lvl_idx][1] + levels[lvl_idx][2]:
            segment = random.choice(geo_neighbors[base_target])
        else:
            segment = random.randint(1, 20)

        if segment > 20:
            segment = 20

        # Gestion des multiplicateurs
        mult_rand = random.randrange(100)
        if is_pos:
            if mult_rand < levels[lvl_idx][3]:
                mult = 'D'
            elif mult_rand < levels[lvl_idx][3] + levels[lvl_idx][4]:
                mult = 'T'
            else:
                mult = 'S'
        else:
            # En tour négatif, le PNJ privilégie les simples pour limiter les dégâts, avec un risque mesuré de double/triple
            if mult_rand < levels[lvl_idx][3] // 2:
                mult = 'D'
            elif mult_rand < (levels[lvl_idx][3] // 2) + (levels[lvl_idx][4] // 2):
                mult = 'T'
            else:
                mult = 'S'

        return f'{mult}{segment}'

    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        """
        Function run after each dart throw - for example, add points to player
        """
        handler = self.init_handler()

        self.nb_darts_hit_in_turn = player_launch
        
        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)
        


        # factor to add or substract points by the round type
        factor = -1
        if self.is_positive_round(actual_round):
            factor = 1
        score = self.score_map[hit] * factor

        players[actual_player].score += score
        # Keep total for this round
        players[actual_player].round_points += score
        players[actual_player].points += score

        # Record total dart thrown, total hits (S=1, D=2, T=3) and refresh players stats
        players[actual_player].darts_thrown += 1
        players[actual_player].increment_hits(hit)

        # Historize
        players[actual_player].add_dart(actual_round, player_launch, hit, score=score)
        
        # TROPHEES
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)

        # Refresh stats
        players[actual_player].columns[5] = (players[actual_player].show_ppd(), 'int')
        players[actual_player].columns[6] = (players[actual_player].avg(actual_round), 'int')

        # Store what he played in the table
        players[actual_player].columns[player_launch - 1] = (score,'int')

        self.refresh_stats(players, actual_round)

        # Check for end of game (no more rounds to play)
        if player_launch == self.nb_darts and actual_round >= self.max_round \
                and actual_player == len(players) - 1:
            bestscoreid = -1
            bestscore = -10000
            for player in players:
                if player.score > bestscore:
                    bestscore = player.score
                    bestscoreid = player.ident
            self.winner = bestscoreid
            
            winning_player = players[self.winner]
                
            ctrophies.check_game_end_stats(players, winning_player, "UP AND DOWN")
            
            
            handler['return_code'] = 3
        else:
            handler['show'] = (players[actual_player].darts, hit, True)
            handler['sound'] = hit

        # Time for shot or video ?
        handler['take_shot'] = self.time_to_take_shot_or_video(hit)

        return handler

    def early_player_button(self, players, actual_player, actual_round):
        """
        Function launched when the  put player button before having launched all his darts
        """
        return_code = 1

        players[actual_player].darts_thrown += (self.nb_darts - self.nb_darts_hit_in_turn)

        # Refresh stats
        players[actual_player].columns[5] = (players[actual_player].show_ppd(), 'int')
        players[actual_player].columns[6] = (players[actual_player].avg(actual_round), 'int')
        self.refresh_stats(players, actual_round)

        self.display.play_sound('penality')

        if actual_round >= self.max_round and actual_player == self.nb_players - 1:
            bestscoreid = -1
            bestscore = -10000
            for player in players:
                if player.score > bestscore:
                    bestscore = player.score
                    bestscoreid = player.ident
            self.winner = bestscoreid
            return_code = 3

        return return_code

    def miss_button(self, players, actual_player, actual_round, player_launch):
        """
        Miss button
        """
        players[actual_player].columns[player_launch - 1] = ('MISS', 'str')
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
        
        # Appliquer la pénalité uniquement si le tour est négatif
        if not self.is_positive_round(actual_round):
            score_penalty = self.penalty
            if score_penalty > 0:
                players[actual_player].score -= score_penalty
                players[actual_player].round_points -= score_penalty
                players[actual_player].points -= score_penalty
            self.display.play_sound('penality')

        players[actual_player].columns[5] = (players[actual_player].show_ppd(), 'int')
        players[actual_player].columns[6] = (players[actual_player].avg(actual_round), 'int')
        self.refresh_stats(players, actual_round)

    def refresh_stats(self, players, actual_round):
        """
        Method to refresh player.stat
        """
        for player in players:
            player.stats['Points Per Round'] = player.avg(actual_round)
            player.stats['Points Per Dart'] = player.show_ppd()

    def is_positive_round(self, actual_round):
        """
        detect the type of round (negative or positive)
        """
        return (actual_round % 2 == 1 and not self.negative) \
                or (actual_round % 2 == 0 and self.negative)
