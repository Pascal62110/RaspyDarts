# -*- coding: utf-8 -*-
# Game by Cory Baumgart!
'''
Bermuda triangle game
'''

######
import collections
import random
from include import cplayer
from include import cgame

LOGO = 'Bermuda_Triangle.png'
HEADERS = ['12', '-', '-', '-', '-', '-', '-']
OPTIONS = {'theme': 'default'}
NB_DARTS = 3
GAME_RECORDS = {'Points Per Round':'DESC', 'Points Per Dart':'DESC'}
VERSION = '1.00'

def check_players_allowed(nb_players):
    """
    Check if number of players is ok according to options
    """
    return nb_players >= 1 and nb_players <= 12, VERSION, 12
    
class CPlayerExtended(cplayer.Player):
    '''
    Extended player class
    '''
    def __init__(self, ident, nb_columns, interior=False):
        super().__init__(ident, nb_columns, interior)
        self.pre_play_score = None
        # Init Player Records to zero
        for record in GAME_RECORDS:
            self.stats[record]='0'

class Game(cgame.Game):
    '''
    Bermuda triange game class
    '''
    def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
        super().__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)
        # game_records is the dictionnary of stats (see above)
        # For Raspberry
        self.raspberry = rpi
        self.game_records = GAME_RECORDS
        self.logo = LOGO
        self.headers = HEADERS
        self.nb_darts = NB_DARTS # Total darts the player has to play
        self.options = options

        # Number of round is ruled (fixé à 12 tours max)
        self.max_round = 12
        self.doublebull = True

        self.infos = ''
        self.winner = None

    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        '''
        Actions done before each dart throw - for example, check if the player is allowed to play
        '''
        return_code = 0

        if player_launch == 1:
            players[actual_player].reset_darts()

        # Each new player
        if player_launch == 1:
            players[actual_player].round_points = 0
            self.save_turn(players)
            players[actual_player].pre_play_score = players[actual_player].score

            # Reset display Table
            players[actual_player].columns = []
            # Clean all next boxes
            for _ in range(0, 7):
                players[actual_player].columns.append(['', 'int'])
            if actual_round == 1 and actual_player == 0:
                for player in players:
                    player.reset_rounds(self.max_round)

        # Display headers depending of round (12 tours au total)
        if actual_round == 1:
            self.headers[0] = '12'
        elif actual_round == 2:
            self.headers[0] = '13'
        elif actual_round == 3:
            self.headers[0] = '14'
        elif actual_round == 4:
            self.headers[0] = 'DBL'
        elif actual_round == 5:
            self.headers[0] = '15'
        elif actual_round == 6:
            self.headers[0] = '16'
        elif actual_round == 7:
            self.headers[0] = '17'
        elif actual_round == 8:
            self.headers[0] = 'TPL'
        elif actual_round == 9:
            self.headers[0] = '18'
        elif actual_round == 10:
            self.headers[0] = '19'
        elif actual_round == 11:
            self.headers[0] = '20'
        elif actual_round == 12:
            self.headers[0] = 'BULL'

        self.headers[1] = self.headers[0]
        self.headers[2] = self.headers[0]

        if self.headers[0] == 'DBL':
            targ = [f'D{num}' for num in range(1, 21)]
        elif self.headers[0] == 'TPL':
            targ = [f'T{num}' for num in range(1, 21)]
        elif self.headers[0] == 'BULL':
            targ = ['SB', 'DB']
        else:
            targ = [f'{mult}{self.headers[0]}' for mult in ['S', 'D', 'T']]

        self.raspberry.set_target_leds('|'.join([f'{key}#{self.colors[0]}' for key in targ]))

        # Print debug output
        self.logs.debug(self.infos)
        return return_code

    def pnj_score(self, players, actual_player, computerLevel, player_launch):
        '''
        IA équilibrée et réaliste pour le Bermuda Triangle : scores modérés, vrais ratés possibles.
        '''
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende : [Taux de miss pur (%), Taux de glissement / déviation (%)]
        # - Plus fort / précis : Diminuer le MISS et le taux de glissement.
        # - Plus humain / brouillon : Augmenter le MISS et le taux de glissement.
        # =========================================================================
        geo_neighbors = {
            1: [20, 18, 4], 2: [17, 15, 10], 3: [19, 17, 2], 4: [18, 13, 1], 
            5: [20, 12, 9], 6: [10, 13, 15], 7: [19, 16, 8], 8: [16, 11, 7], 
            9: [14, 12, 5], 10: [15, 6, 2], 11: [14, 8, 16], 12: [9, 5, 20], 
            13: [6, 4, 11], 14: [9, 11, 16], 15: [10, 2, 6], 16: [7, 8, 11], 
            17: [2, 3, 15], 18: [4, 1, 20], 19: [7, 3, 2], 20: [1, 5, 12]
        }

        # Niveaux : [Taux de miss pur, Taux de glissement]
        levels = [
                 [45, 80],  # 1 : Noob 
                 [30, 70],  # 2 : Débutant
                 [18, 60],  # 3 : Intermédiaire
                 [6, 25],   # 4 : Pro 
                 [2, 8]     # 5 : Expert 
                ]

        lvl_idx = max(0, min(computerLevel - 1, len(levels) - 1))
        miss_rate = levels[lvl_idx][0]
        slip_rate = levels[lvl_idx][1]

        if random.randrange(100) < miss_rate:
            players[actual_player].columns[player_launch - 1] = ('MISS', 'str')
            self.display.play_sound('miss')
            players[actual_player].darts_thrown += 1
            return 'MISSDART'

        current_target_type = self.headers[0]
        target_num = None
        mult = 'S'

        if current_target_type in ['12', '13', '14', '15', '16', '17', '18', '19', '20']:
            target_num = int(current_target_type)
            mult = random.choices(['S', 'D', 'T'], weights=[97, 2, 1], k=1)[0]
        elif current_target_type == 'DBL':
            target_num = random.randint(1, 20)
            mult = 'D'
        elif current_target_type == 'TPL':
            target_num = random.choice([15, 16, 17, 18, 19, 20])
            mult = 'T'
        elif current_target_type == 'BULL':
            return random.choices(['SB', 'DB', 'MISS'], weights=[30, 5, 65], k=1)[0]

        hit_target = f'{mult}{target_num}'

        if random.randrange(100) < slip_rate:
            if current_target_type in ['DBL', 'TPL']:
                if target_num in geo_neighbors:
                    target_num = random.choice(geo_neighbors[target_num])
                mult = 'S'
            else:
                if random.randrange(100) < 50 and target_num in geo_neighbors:
                    target_num = random.choice(geo_neighbors[target_num])
                    mult = 'S'
                else:
                    players[actual_player].columns[player_launch - 1] = ('MISS', 'str')
                    self.display.play_sound('miss')
                    players[actual_player].darts_thrown += 1
                    return 'MISSDART'

            hit_target = f'{mult}{target_num}'

        return hit_target

    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        '''
        Function run after each dart throw - for example, add points to player
        '''

        self.infos = ""
        handler = self.init_handler()
        score = 0
        is_valid = False
        
        if actual_round == 1 and hit[1:] == '12': is_valid = True
        elif actual_round == 2 and hit[1:] == '13': is_valid = True
        elif actual_round == 3 and hit[1:] == '14': is_valid = True
        elif actual_round == 4 and hit[:1] == 'D': is_valid = True
        elif actual_round == 5 and hit[1:] == '15': is_valid = True
        elif actual_round == 6 and hit[1:] == '16': is_valid = True
        elif actual_round == 7 and hit[1:] == '17': is_valid = True
        elif actual_round == 8 and hit[:1] == 'T': is_valid = True
        elif actual_round == 9 and hit[1:] == '18': is_valid = True
        elif actual_round == 10 and hit[1:] == '19': is_valid = True
        elif actual_round == 11 and hit[1:] == '20': is_valid = True
        elif actual_round == 12 and hit in ('SB', 'DB'): is_valid = True  # Le 12ème tour valide à la fois SB et DB

        if is_valid:
            score = self.score_map[hit]
            check = True
            players[actual_player].columns[player_launch - 1] = ('check-mark', 'image')
        else:
            check = False
            return_code = -1
            players[actual_player].columns[player_launch - 1] = ('cross-mark', 'image')

        if score > 0:
            handler['show'] = (players[actual_player].darts, hit, False)
            handler['sound'] = hit 
            players[actual_player].score += score 
            players[actual_player].round_points += score 
            players[actual_player].points += score   
        elif players[actual_player].round_points == 0 and player_launch == 3:
            self.infos += "Dividing score by half!\n"
            handler['return_code'] = 1 
            players[actual_player].score = int(players[actual_player].score / 2)
            handler['sound'] = 'whatamess'

        # Check last round (fixé à 12 tours)
        if actual_round >= self.max_round and actual_player == self.nb_players - 1 \
                and player_launch == int(self.nb_darts):
            self.infos += f"Last round reached ({actual_round})\n"
            self.winner = self.check_winner(players)
            if self.winner is not None:
                self.infos += f"Player {self.winner} wins !\n"
                handler['return_code'] = 3
            else:
                handler['return_code'] = 2

        players[actual_player].add_dart(actual_round, player_launch, hit, score=score, check=check)
        players[actual_player].increment_hits(hit)
        players[actual_player].darts_thrown += 1

        self.refresh_stats(players, actual_round)
        self.logs.debug(self.infos)

        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        return handler

    def early_player_button(self, players, actual_player, actual_round):
        '''
        Function launched if the player hit the player button before having
        thrown all his darts (Pneu)
        '''
        self.infos += f"EarlyPlayer function. Actual player marked {players[actual_player].round_points}\n"
        self.display.play_sound('whatamess')
        return_code = 1

        if actual_round == self.max_round and actual_player == self.nb_players - 1:
            return_code = 2
            self.winner = self.check_winner(players)
            if self.winner is not None:
                self.infos += f'Player {self.winner} wins !\n'
                return_code = 3

        return return_code

    def refresh_stats(self, players, actual_round):
        '''
        Method to frefresh player.stat
        '''
        for player in players:
            player.stats['Points Per Round'] = player.show_ppr()
            player.stats['Points Per Dart'] = player.show_ppd()

    def miss_button(self, players, actual_player, actual_round, player_launch):
        '''
        To avoid Ouin ouin
        '''
        players[actual_player].columns[player_launch-1] = ('MISS', 'str')
        self.display.play_sound('miss')
        players[actual_player].darts_thrown += 1
        check = False
        players[actual_player].columns[player_launch - 1] = ('cross-mark', 'image')
        players[actual_player].round_points += 0 
        
        if player_launch == 3 and players[actual_player].round_points == 0:
            self.infos += 'Dividing score by half! And early !\n'
            players[actual_player].score = int(players[actual_player].score / 2)
            self.display.play_sound('whatamess')


    def post_round_check(self, players, actual_round, actual_player):
        """
        Vérifie si la partie est terminée à la fin du dernier tour.
        """
        if actual_round >= self.max_round and actual_player == self.nb_players - 1:
            self.infos += f"Last round reached ({actual_round})\n"
            self.winner = self.check_winner(players)
            return self.winner
        else:
            return -2

    def check_winner(self, players):
        """
        Détermine le joueur ayant le score le plus élevé.
        """
        best_score = -1
        best_player = -1
        for player in players:
            if player.score > best_score:
                best_score = player.score
                best_player = player.ident
        return best_player
        
    def next_game_order(self, players):
        '''
        Define the next game players order, depending of previous games' score
        '''
        scores = {}
        for player in players:
            scores[player.name] = player.score
        new_order = collections.OrderedDict(sorted(scores.items(), key=lambda t: t[1],
            reverse=True))
        return list(new_order.keys())
