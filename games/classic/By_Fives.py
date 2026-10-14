# -*- coding: utf-8 -*-
# Game by ... poilou !
"""
Game by Poilou : By Five
"""
import collections
import random

from include import cplayer
from include import cgame

LOGO = 'By_Fives.png'
HEADERS = ['D1', 'D2', 'D3', 'Check', '', '', 'Rnd']
OPTIONS = {'theme': 'default', 'winscore': 5, 'score51': False, 'max_round': 20}
NB_DARTS = 3
GAME_RECORDS = {'Score': 'DESC'}
VERSION = '1.01'

def check_players_allowed(nb_players):
    """
    Check if number of players is ok according to options
    """
    return nb_players >= 1 and nb_players <= 12, VERSION, 12
    
class CPlayerExtended(cplayer.Player):
    """
    Extended player class
    """
    def __init__(self, ident, nb_columns, interior=False):
        super().__init__(ident , nb_columns, interior)
        self.pre_play_score = None
        # Init Player Records to zero
        for record in GAME_RECORDS:
            self.stats[record] = '0'

class Game(cgame.Game):
    """
    By Five game class
    """
    def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
        super().__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)
        self.logo = LOGO
        self.headers = HEADERS
        self.nb_darts = NB_DARTS # Total darts the player has to play
        self.options = options
        self.max_round = int(options['max_round'])
        # GameRecords is the dictionnary of stats (see above)
        self.game_records = GAME_RECORDS
        # For rpi
        self.rpi = rpi

        self.infos = ''
        self.winner = None
        self.winscore = int(options['winscore'])
        if options['score51']:
            self.score51 = True
            self.winscore = 51
        else:
            self.score51 = False
        self.valid = True

    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        """
        Actions done before each dart throw - for example, check if the player is allowed to play
        """
        return_code = 0

        if player_launch == 1:
            players[actual_player].reset_darts()
            self.valid = True

        # Set score at startup
        if actual_round == 1 and player_launch == 1 and actual_player == 0:
            for player in players:
                # Init score
                player.score = 0

        # Each new player
        if player_launch == 1:
            players[actual_player].round_points = 0
            self.save_turn(players)
            players[actual_player].pre_play_score = players[actual_player].score

            #Reset display Table
            players[actual_player].columns = []
            # Clean all next boxes
            for _ in range(0, 7):
                players[actual_player].columns.append(['', 'int'])
            if actual_round == 1 and actual_player == 0:
                for player in players:
                    player.reset_rounds(self.max_round)

        if player_launch == 3:
            targ = []
            for mult in ['S', 'D', 'T']:
                if mult == 'S':
                    multiplier = 1
                elif mult == 'D':
                    multiplier = 2
                else:
                    multiplier = 3

                for number in range(1,22):
                    if number == 21:
                        if multiplier == 3:
                            continue
                        number = 25

                    if self.mod_by_5(players[actual_player].round_points + number * multiplier):
                        if number == 25:
                            number = 'B'
                        targ.append(f'{mult}{number}#{self.colors[0]}')
            self.rpi.set_target_leds('|'.join(targ))
        else :
            self.rpi.set_target_leds('')

        # Print debug output
        self.logs.debug(self.infos)
        return return_code

    def pnj_score(self, players, actual_player, level, player_launch):
        """
        Compute pnj score with exact finish calculation for 51 points option
        """
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende : [Taux de miss (%), Taux de réussite/précision du 3e tir (%)]
        # - Plus fort / précis : Diminuer le MISS et augmenter le taux de réussite.
        # - Plus humain / brouillon : Augmenter le MISS et baisser le taux de réussite.
        # =========================================================================
        levels = [
            [25, 15],  # 1 : Noob
            [21, 30],  # 2 : Débutant
            [17, 45],  # 3 : Intermédiaire
            [13, 60],  # 4 : Pro
            [2,  75]   # 5 : Expert
        ]

        lvl_idx = max(0, min(level - 1, len(levels) - 1))
        miss_chance = levels[lvl_idx][0]
        success_probability = levels[lvl_idx][1]

        target_scores = []
        winning_scores = []
        current_points = players[actual_player].round_points
        player_score = players[actual_player].score
        
        # Gestion de la probabilité de faire un pneu (MISSDART) selon le niveau
        if random.randint(1, 100) < miss_chance:
            return 'MISSDART'

        # Au 3ème tir, le PNJ analyse ses options de fin de partie ou de score sécurisé
        if player_launch == 3:
            for val in range(1, 21):
                for mult_val, mult_str in [(1, 'S'), (2, 'D'), (3, 'T')]:
                    dart_score = val * mult_val
                    total_round = current_points + dart_score
                    if total_round % 5 == 0:
                        gained = total_round // 5
                        if self.score51:
                            new_total_score = player_score + gained
                            if new_total_score == 51:
                                winning_scores.append(f"{mult_str}{val}")
                            elif new_total_score < 51:
                                target_scores.append(f"{mult_str}{val}")
                        else:
                            target_scores.append(f"{mult_str}{val}")
                            
            # Vérification pour le Bull
            for bull_val, bull_str in [(25, 'SB'), (50, 'DB')]:
                total_round = current_points + bull_val
                if total_round % 5 == 0:
                    gained = total_round // 5
                    if self.score51:
                        new_total_score = player_score + gained
                        if new_total_score == 51:
                            winning_scores.append(bull_str)
                        elif new_total_score < 51:
                            target_scores.append(bull_str)
                    else:
                        target_scores.append(bull_str)
            
            # Priorité absolue : si un coup lui permet de gagner exactement à 51, il le tente
            if winning_scores and random.randint(1, 100) <= success_probability:
                return random.choice(winning_scores)
                
            # Sinon, s'il y a des cibles valides qui ne font pas dépasser 51
            if target_scores and random.randint(1, 100) <= success_probability:
                return random.choice(target_scores)

        # Comportement standard / tirs 1 et 2
        letters = 'SDT'
        value = random.randint(1, 20)
        multi = ''.join(random.choice(letters) for _ in range(1))
        bull = random.randint(0, 100)
        
        if 85 < bull <= 95:
            return 'SB'
        if bull > 95:
            return 'DB'
            
        return f'{multi}{value}'

    def check_winner(self, players):
        """
        Check if a player has won the game according to options
        """
        for player in players:
            if self.score51:
                if player.score == 51:
                    return player.ident
            else:
                if player.score >= self.winscore:
                    return player.ident
        return None

    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        """
        Function run after each dart throw - for example, add points to player
        """

        handler = self.init_handler()
        check = False
        
        # Gestion du pneu (MISSDART)
        if hit == 'MISSDART':
            score = 0
            players[actual_player].columns[player_launch - 1] = ('MISS', 'str')
            self.display.play_sound('miss')
        else:
            score = self.score_map[hit]
            players[actual_player].columns[player_launch - 1] = (score, 'int')
            self.display.play_sound(hit)

        players[actual_player].round_points += score

        if player_launch == 3:
            # Règle du pneu à la dernière flèche : si la 3ème est un miss, le tour est invalidé
            if hit == 'MISSDART':
                players[actual_player].round_points = 0
                checkpoints = False
            else:
                checkpoints = self.mod_by_5(players[actual_player].round_points)

            if checkpoints:
                if self.score51:
                    points_gagnes = players[actual_player].round_points / 5
                    new_score = players[actual_player].score + points_gagnes
                    
                    if new_score == 51:
                        players[actual_player].score = 51
                        score = points_gagnes
                        check = True
                    elif new_score < 51:
                        players[actual_player].score = new_score
                        score = points_gagnes
                        check = True
                    else:
                        score = 0
                        self.display.message(['Score too high !!'], None, None, 'middle', 'big')
                else:
                    check = True
                    players[actual_player].score += 1
                    score = 1
                players[actual_player].columns[3] = ('check-mark', 'image')
            else:
                players[actual_player].columns[3] = ('cross-mark', 'image')
                if hit == 'MISSDART':
                    score = 0

        players[actual_player].add_dart(actual_round, player_launch, hit, check=check, score=score)

        # Change table displayed
        players[actual_player].columns[6] = (players[actual_player].round_points, 'int')

        players[actual_player].increment_hits(hit)
        players[actual_player].darts_thrown += 1
        self.refresh_stats(players, actual_round)

        # Check last round
        if actual_round >= self.max_round and actual_player == self.nb_players - 1 \
                and player_launch == int(self.nb_darts):
            self.infos += f"Last round reached ({actual_round}){self.lf}"
            handler['return_code'] = 2

        # Check if there is a winner using our custom method
        self.winner = self.check_winner(players)
        if self.winner is not None:
            self.infos += f"player {self.winner} wins !{self.lf}"
            handler['return_code'] = 3
        else:
            handler['show'] = (players[actual_player].darts, hit, False)
            handler['sound'] = hit

        # Time for shot or video ?
        handler['take_shot'] = self.time_to_take_shot_or_video(hit)

        return handler

    def miss_button(self, players, actual_player, actual_round, player_launch):
        """
        In case of miss dart
        """
        print('miss')
        
        players[actual_player].columns[player_launch-1] = ('MISS', 'str')
        self.display.play_sound('miss')
        players[actual_player].darts_thrown += 1       
        
        # Si on fait un miss à la dernière flèche, on invalide le tour
        if player_launch == 3:
            players[actual_player].round_points = 0
            players[actual_player].columns[3] = ('cross-mark', 'image')
            return 1

    def mod_by_5(self,score):
        """
        Return True if score is divisible by 5
        """
        return score % 5 == 0
