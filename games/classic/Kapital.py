# -*- coding: utf-8 -*-
'''
game by diego aimabouer : Kapital
'''
#######
import time
import random
from include import cplayer
from include import cgame

LOGO = 'Kapital.png' # Background image
HEADERS = ['!', 'D1', 'D2', 'D3', '', '', ''] # Columns headers - Must be a string
OPTIONS = {'theme': 'default'} # Dictionnay of options in string format
NB_DARTS = 3
GAME_RECORDS = {'Score': 'DESC'}

#1 = White
#2 = Red
#3 = Blue
COLORS = {
            'SB' : 3, 'DB': 2,

            's20': 3, 'S20': 3, 'D20': 1, 'T20': 1,
            's18': 3, 'S18': 3, 'D18': 1, 'T18': 1,
            's14': 3, 'S14': 3, 'D14': 1, 'T14': 1,
            's13': 3, 'S13': 3, 'D13': 1, 'T13': 1,
            's12': 3, 'S12': 3, 'D12': 1, 'T12': 1,
            's10': 3, 'S10': 3, 'D10': 1, 'T10': 1,
            's8': 3, 'S8' : 3, 'D8' : 1, 'T8' : 1,
            's7': 3, 'S7' : 3, 'D7' : 1, 'T7' : 1,
            's3': 3, 'S3' : 3, 'D3' : 1, 'T3' : 1,
            's2': 3, 'S2' : 3, 'D2' : 1, 'T2' : 1,

            's19': 1, 'S19': 1, 'D19': 2, 'T19': 2,
            's17': 1, 'S17': 1, 'D17': 2, 'T17': 2,
            's16': 1, 'S16': 1, 'D16': 2, 'T16': 2,
            's15': 1, 'S15': 1, 'D15': 2, 'T15': 2,
            's11': 1, 'S11': 1, 'D11': 2, 'T11': 2,
            's9': 1, 'S9' : 1, 'D9' : 2, 'T9' : 2,
            's6': 1, 'S6' : 1, 'D6' : 2, 'T6' : 2,
            's5': 1, 'S5' : 1, 'D5' : 2, 'T5' : 2,
            's4': 1, 'S4' : 1, 'D4' : 2, 'T4' : 2,
            's1': 1, 'S1' : 1, 'D1' : 2, 'T1' : 2
            }

TARGETS = ['20', '1', '18', '4', '13', '6', '10', '15', '2', '17', '3', \
        '19', '7', '16', '8', '11', '14', '9', '12', '5']

VERSION = '1.00'

def check_players_allowed(nb_players):
    """
    Check if number of players is ok according to options
    """
    return nb_players >= 1 and nb_players <= 12, VERSION, 12
    
class CPlayerExtended(cplayer.Player):
    '''
    Extend the basic player
    '''
    def __init__(self, ident, nb_columns, interior=False):
        super().__init__(ident, nb_columns, interior)
        # Init Player Records to zero
        for record in GAME_RECORDS:
            self.stats[record] = '0'

        self.contrat_done = False

class Game(cgame.Game):
    '''
    Kapital class game
    '''
    def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
        super().__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)
        self.logo = LOGO
        self.headers = HEADERS
        self.nb_darts = NB_DARTS # Total darts the player has to play
        self.options = options
        self.game_records = GAME_RECORDS
        # For rpi
        self.rpi = rpi

        self.winner = None
        self.infos = ''
        self.jackpot = 0
        self.suite = []
        self.contract_colors = []
        self.max_round = 15
        self.kot_kot = None

    def pnj_score(self, players, actual_player, computerLevel, player_launch):
        '''
        IA réaliste pour Kapital avec gestion intelligente du tour 57 et de la matrice.
        '''
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende : [Taux de miss pur (%), Taux de glissement/déviation sur la matrice (%)]
        # - Plus fort / précis : Diminuer le miss_rate et le slip_rate.
        # - Plus humain / brouillon : Augmenter le miss_rate et le slip_rate.
        # =========================================================================
        geo_neighbors = {
            1: [20, 18, 4], 2: [17, 15, 10], 3: [19, 17, 2], 4: [18, 13, 1], 
            5: [20, 12, 9], 6: [10, 13, 15], 7: [19, 16, 8], 8: [16, 11, 7], 
            9: [14, 12, 5], 10: [15, 6, 2], 11: [14, 8, 16], 12: [9, 5, 20], 
            13: [6, 4, 11], 14: [9, 11, 16], 15: [10, 2, 6], 16: [7, 8, 11], 
            17: [2, 3, 15], 18: [4, 1, 20], 19: [7, 3, 2], 20: [1, 5, 12]
        }

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

        # 1. Test du MISS pur
        if random.randrange(100) < miss_rate:
            players[actual_player].columns[player_launch] = ('MISS', 'str')
            self.display.play_sound('miss')
            players[actual_player].darts_thrown += 1
            return 'MISSDART'

        actual_round = getattr(self, 'actual_round', 1)
        target_num = 20
        mult = 'S'

        # 2. Détermination de l'intention selon le tour
        if actual_round in [2, 4, 6, 8, 10, 12, 14]: # Chiffres simples
            targets_map = {2: 20, 4: 19, 6: 18, 8: 17, 10: 16, 12: 15, 14: 14}
            target_num = targets_map.get(actual_round, 20)
            mult = random.choices(['S', 'D', 'T'], weights=[80, 15, 5], k=1)[0]
            
        elif actual_round == 1: # K de départ
            target_num = random.choice([20, 19, 18, 15])
            mult = random.choices(['T', 'D', 'S'], weights=[30, 30, 40], k=1)[0]
            
        elif actual_round == 3: # TRIPLES
            target_num = random.choice([20, 19, 18, 17, 16])
            mult = 'T'
            
        elif actual_round == 5: # DOUBLES
            target_num = random.randint(1, 20)
            mult = 'D'
            
        elif actual_round == 7: # KOLR
            target_num = random.randint(1, 20)
            mult = 'S'
            
        elif actual_round == 9: # 57 : Logique intelligente basée sur le score restant
            if player_launch == 1:
                mult = 'T'
                target_num = 19
            else:
                rem = 57 - players[actual_player].score_contrat
                possible_launch = self.search_possible_launch(rem, player_launch)
                if possible_launch:
                    chosen = random.choice(list(possible_launch))
                    if isinstance(chosen, str) and chosen.startswith(('S', 'D', 'T')):
                        mult = chosen[0]
                        target_num = int(chosen[1:])
                    else:
                        mult = 'S'
                        try:
                            target_num = int(chosen)
                        except ValueError:
                            target_num = 6
                else:
                    mult = 'S'
                    target_num = 6
                    
        elif actual_round == 11: # SUITE
            target_num = random.randint(5, 16)
            mult = 'S'
            
        elif actual_round == 13: # KKOT
            if getattr(self, 'possibilities', None):
                target_num = random.choice(list(self.possibilities))
            else:
                target_num = random.randint(1, 20)
            mult = 'S'
            
        elif actual_round == 15: # Bull
            return random.choices(['SB', 'DB', 'MISSDART'], weights=[50, 20, 30], k=1)[0]

        # 3. Simulation de la déviation réaliste sur la matrice
        if random.randrange(100) < slip_rate:
            if mult in ['D', 'T']:
                if random.randrange(100) < 60:
                    mult = 'S'
                else:
                    mult = 'S'
                    if target_num in geo_neighbors:
                        target_num = random.choice(geo_neighbors[target_num])
            else:
                if target_num in geo_neighbors:
                    target_num = random.choice(geo_neighbors[target_num])
                mult = 'S'

        return f'{mult}{target_num}'


    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        '''
        Actions done before each dart throw - for example, check if the player is allowed to play
        '''
        self.actual_round = actual_round
        return_code = 0
        self.infos += ""
        self.rpi.set_target_leds('')
        text = ''
        
        # Init
        if player_launch == 1:
            self.possibilities = None
            players[actual_player].contrat_done = False
            self.jackpot = 0
            self.save_turn(players)
            players[actual_player].score_contrat = 0
            players[actual_player].reset_darts()
            # Clear table for current player
            for i in range(1, 4):
                players[actual_player].columns[i] = ('', 'txt', 'game-grey')
            if actual_round == 1:
                players[actual_player].reset_rounds(self.max_round)

        leds = ''
        # Display du contrat
        if actual_round == 1:
            text = 'K'
        elif actual_round == 2:
            text = '20'
            leds = f'S20#{self.colors[0]}|D20#{self.colors[0]}|T20#{self.colors[0]}'

        elif actual_round == 3:
            text = 'Trpl'
            leds = '|'.join(f'T{number}#{self.colors[0]}' for number in range(1, 21))

        elif actual_round == 4:
            text = '19'
            leds = f'S19#{self.colors[0]}|D19#{self.colors[0]}|T19#{self.colors[0]}'

        elif actual_round == 5:
            text = 'Dble'
            leds = '|'.join(f'D{number}#{self.colors[0]}' for number in range(1, 21))

        elif actual_round == 6:
            text = '18'
            leds = f'S18#{self.colors[0]}|D18#{self.colors[0]}|T18#{self.colors[0]}'

        elif actual_round == 7:
            text = 'Kolr'
            segments = []

            if player_launch > 1:
                for segment, color in COLORS.items():
                    if (player_launch == 2 and color != self.contract_colors[0] ) or \
                        (player_launch == 3 and color not in (self.contract_colors[0], self.contract_colors[1])):
                        segments.append(segment)
                leds = '|'.join([f'{segment}#{self.colors[0]}' for segment in segments])

        elif actual_round == 8:
            leds = f'S17#{self.colors[0]}|D17#{self.colors[0]}|T17#{self.colors[0]}'
            text = '17'

        elif actual_round == 9:
            text = '57'
            if player_launch == 1:
                leds = f'T19#{self.colors[0]}'
            else:
                possible_launch = self.search_possible_launch(57 - players[actual_player].score_contrat, player_launch)

                if possible_launch is not None:
                    leds = '|'.join([f'{key}#{self.colors[0]}' for key in possible_launch] \
                            + [f'SB#{self.colors[0]}'])
                else:
                    return 4

        elif actual_round == 10:
            leds = f'S16#{self.colors[0]}|D16#{self.colors[0]}|T16#{self.colors[0]}'
            text = '16'

        elif actual_round == 11:
            text = 'Suite'
            # Sécurité : initialiser self.suite par défaut si elle est vide ou absente
            if not hasattr(self, 'suite') or not self.suite:
                self.suite = [1]

            has_second_element = len(self.suite) > 1
            is_25 = has_second_element and str(self.suite[1]) == '25'

            if player_launch == 2 or (player_launch == 3 and is_25):
                leds = '|'.join(\
                    [f'{mult}{self.suite[0] + add}#{self.colors[0]}' for mult in ['S', 'D', 'T'] \
                        for add in [-2, -1, 1, 2] if 1 <= self.suite[0] + add <= 20] \
                    + [f'SB#{self.colors[0]}'])

            elif player_launch == 3:
                if has_second_element and self.suite[0] + 1 == self.suite[1]:
                    if self.suite[0] == 19:
                        # 19-20, only 18 and SB available
                        leds = '|'.join(\
                            [f'{mult}18#{self.colors[0]}' for mult in ['S', 'D', 'T']] \
                            + [f'SB#{self.colors[0]}'])
                    elif self.suite[0] == 1:
                        # 1-2, only 3 and SB available
                        leds = '|'.join(\
                            [f'{mult}3#{self.colors[0]}' for mult in ['S', 'D', 'T']] \
                            + [f'SB#{self.colors[0]}'])
                    else:
                        # 12 and 13, possibilities 11, 14 and SB/DB
                        leds = '|'.join(\
                            [f'{mult}{self.suite[0] + add}#{self.colors[0]}' for mult in ['S', 'D', 'T'] \
                                for add in [-1, 2]] \
                            + [f'SB#{self.colors[0]}'])
                else:
                    # 12 and 14 for example : only one possibility : 13 -and SB/DB)
                     leds = '|'.join([f'{mult}{self.suite[0] + 1}#{self.colors[0]}' for mult in ['S', 'D', 'T']] \
                           + [f'SB#{self.colors[0]}'])

        elif actual_round == 12:
            leds = f'S15#{self.colors[0]}|D15#{self.colors[0]}|T15#{self.colors[0]}'
            text = '15'

        elif actual_round == 13:
            text = 'Kkot'
            if self.possibilities is not None:
                leds = '|'.join([f'{mult}{num}#{self.colors[0]}' for mult in ['S', 'D', 'T'] \
                    for num in self.possibilities] + ['SB#green|DB#green'])

        elif actual_round == 14:
            leds = f'S14#{self.colors[0]}|D14#{self.colors[0]}|T14#{self.colors[0]}'
            text = '14'

        elif actual_round == 15:
            leds = f'SB#{self.colors[0]}|DB#{self.colors[0]}'
            text = 'B'

        if player_launch == 1:
            for player in players:
                player.columns[0] = (text, 'txt', 'game-text')

        self.rpi.set_target_leds(leds)
        return return_code


    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        '''
        Is the contract done ?
        '''

        handler = self.init_handler()
        dart_valid = False

        self.infos = ""
        if player_launch == 1:
            self.jackpot = 0

        multiplier, value = self.split_key(hit)
        score = self.score_map.get(hit)

        if multiplier == 'D':
            led_color = self.colors[0]
        elif multiplier == 'T':
            led_color = self.colors[1]
        else:
            led_color = self.colors[2]

        players[actual_player].columns[player_launch] = (str(hit), 'txt', f'game-{led_color}')
        play_sound = True
        if player_launch == 1:
            players[actual_player].contrat_done = False

        # Round 1 : Max points
        if actual_round == 1:
            players[actual_player].contrat_done = True
            dart_valid = True
            play_sound = False

        # Round 2 : 20
        elif actual_round == 2 and value == '20':
            players[actual_player].contrat_done = True
            dart_valid = True

        # Round 3 : Triple
        elif actual_round == 3 and multiplier == 'T':
            players[actual_player].contrat_done = True
            dart_valid = True

        # Round 4 : 19
        elif actual_round == 4 and value == '19':
            players[actual_player].contrat_done = True
            dart_valid = True

        # Round 5 : double
        elif actual_round == 5 and multiplier == 'D':
            players[actual_player].contrat_done = True
            dart_valid = True

        # Round 6 : 18
        elif actual_round == 6 and value == '18':
            players[actual_player].contrat_done = True
            dart_valid = True

        # Round 7 : Color
        elif actual_round == 7:
            players[actual_player].score_contrat += self.score_map.get(hit)
            play_sound = False
            if player_launch == 1:
                self.contract_colors = []
            self.contract_colors.append(COLORS[hit])
            if len(self.contract_colors) == 2 and player_launch == 2:
                if self.contract_colors[0] != self.contract_colors[1]:
                    handler['sound'] = 'kapitalpressure'
            elif len(self.contract_colors) == 3:
                if self.contract_colors[0] not in \
                        (0, self.contract_colors[1], self.contract_colors[2]) \
                    and self.contract_colors[2] != self.contract_colors[1]:
                    self.infos += "Hehe ! Good Job !\n"
                    players[actual_player].contrat_done = True
                    handler['sound'] = 'kapitalhardcontrat'
                    players[actual_player].add_score(players[actual_player].score_contrat)
                    
        # Round 8 : 17
        elif actual_round == 8 and value == '17':
            players[actual_player].contrat_done = True
            dart_valid = True

        # Round 9 : 57
        elif actual_round == 9:
            play_sound = False
            players[actual_player].score_contrat += self.score_map.get(hit)
            if players[actual_player].score_contrat == 57:
                players[actual_player].contrat_done = True
                handler['return_code'] = 1
                handler['sound'] = 'kapitalhardcontrat'
                players[actual_player].add_score(players[actual_player].score_contrat)

        # Round 10 : 16
        elif actual_round == 10 and value == '16':
            players[actual_player].contrat_done = True
            dart_valid = True

        # Round 11 : Suite
        elif actual_round == 11:
            play_sound = False
            players[actual_player].score_contrat += self.score_map.get(hit)
            if player_launch == 1:
                self.suite = []

            if value == 'B':
                self.suite.append(25)
            else:
                self.suite.append(int(value))
            self.suite.sort()
            
            if len(self.suite) == 2:
                if self.suite[1] - self.suite[0] in (1, 2) or 25 in self.suite:
                    handler['sound'] = 'kapitalpressure'
                else:
                    handler['sound'] = 'chaussette'
                    handler['return_code'] = 1

            elif len(self.suite) == 3:
                if (self.suite[0] + 1 == self.suite[1] and self.suite[1] + 1 == self.suite[2]) \
                        or (self.suite[2] == 25 and self.suite[0] + 1 == self.suite[1]) \
                        or (self.suite[2] == 25 and self.suite[0] + 2 == self.suite[1]):
                    players[actual_player].contrat_done = True
                    handler['sound'] = 'kapitalhardcontrat'
                    self.infos += "Suite done !\n"
                    players[actual_player].add_score(players[actual_player].score_contrat)
                else:
                    self.infos += "Looser !\n"

        # Round 12 : 15
        elif actual_round == 12 and value == '15':
            players[actual_player].contrat_done = True
            dart_valid = True

        # Round 13 : Kot Kot
        elif actual_round == 13:
            play_sound = False
            players[actual_player].score_contrat += self.score_map.get(hit)
            self.infos += rf"Votre cote-cote en est ici : {self.kot_kot}\n"
            self.infos += rf"Il vous rapporte actuellement {players[actual_player].score_contrat} points\n"
            self.infos += f'possibilities = {self.possibilities}'

            if player_launch == 3 and (self.possibilities is None or value in self.possibilities \
                    or value == 'B'):
                players[actual_player].contrat_done = True
            elif value == 'B':
                pass
            elif self.possibilities is None:
                temp = TARGETS.index(value)
                self.possibilities = []
                self.possibilities.append(TARGETS[(temp + len(TARGETS) + 1) % len(TARGETS)])
                self.possibilities.append(TARGETS[(temp + len(TARGETS) - 1) % len(TARGETS)])
                self.kot_kot = temp
                if actual_round == 1:
                    self.possibilities.append(TARGETS[(temp + len(TARGETS) + 2) % len(TARGETS)])
                    self.possibilities.append(TARGETS[(temp + len(TARGETS) - 2) % len(TARGETS)])
            else:
                if value in self.possibilities:
                    temp = TARGETS.index(value)
                    min_hit = min(temp, self.kot_kot)
                    max_hit = max(temp, self.kot_kot)
                    self.possibilities = []
                    if max_hit - min_hit in (1, 19):
                        self.possibilities.append(TARGETS[(max_hit + len(TARGETS) + 1) % len(TARGETS)])
                        self.possibilities.append(TARGETS[(min_hit + len(TARGETS) - 1) % len(TARGETS)])
                    elif max_hit - min_hit in (2, 18):
                        self.possibilities.append(TARGETS[(max_hit + len(TARGETS) - 1) % len(TARGETS)])

            if players[actual_player].contrat_done:
                handler['sound'] = 'kapitalhardcontrat'
                self.infos += "Kotkot réussi !!! Good Job mate !\n"
                players[actual_player].add_score(players[actual_player].score_contrat)
            elif actual_round == 3:
                self.infos += "Looser.\n"

        # Round 14 : 14
        elif actual_round == 14 and value == '14':
            players[actual_player].contrat_done = True
            dart_valid = True

        # Round 15 : Bull
        elif actual_round == 15 and value == 'B':
            play_sound = False
            players[actual_player].contrat_done = True
            dart_valid = True
            handler['sound'] = 'kapitalhardcontrat'

        if player_launch == 3 and not players[actual_player].contrat_done:
            handler['sound'] = 'kapitaldivision'
            players[actual_player].set_score(int(players[actual_player].score / 2))

        players[actual_player].increment_hits(hit)
        players[actual_player].darts_thrown += 1

        self.refresh_stats(players, actual_round)

        if players[actual_player].contrat_done and dart_valid:
            self.jackpot += 1
            self.infos += f"Bien joué Calhagan ! {self.jackpot} touches !\n"
            score = self.score_map.get(hit)
            players[actual_player].add_dart(actual_round, player_launch, hit, score=score, check=False)
            players[actual_player].score_contrat += score
            players[actual_player].add_score(score)

            if play_sound:
                if self.jackpot == 3:
                    handler['sound'] = 'kapital3goodhits'
                else:
                    handler['sound'] = 'kapitalcontratok'
        else:
            players[actual_player].add_dart(actual_round, player_launch, hit, score=0, check=False)
            handler['sound'] = hit

        if actual_round == 15 and player_launch == 3:
            self.winner = self.check_winner(players)
            if actual_player == self.nb_players - 1 and player_launch == int(self.nb_darts):
                self.infos += f"Last round reached ({actual_round})\n"
                handler['return_code'] = 2
                if self.winner is not None:
                    handler['return_code'] = 3

        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        self.logs.debug(self.infos)
        return handler

    def early_player_button(self, players, actual_player, actual_round):
        '''
        Function launched when the player put player button before having launched all his darts
        '''
        self.infos = "Pneu (or early player buttton) function\n"
        if actual_round == 15:
            self.winner = self.check_winner(players)
            if self.winner is not None:
                self.infos += f"Current winner is Player {self.winner}\n"
            if actual_player == self.nb_players - 1:
                self.infos += f"Last round reached ({actual_round})\n"
                if self.winner is not None:
                    return 3
                return 2

        self.logs.debug(self.infos)
        return 1

    def search_possible_launch(self, score, player_launch):
        '''
        Is there a combination to win ?
        '''
        for hit, key in self.score_map.items():
            if score == key:
                return [hit.upper()]

        if player_launch == 2:
            for hit, key in self.score_map.items():
                if score > key:
                    rest = score - key
                    for hit2, key2 in self.score_map.items():
                        if rest == key2:
                            return [hit2.upper(), hit.upper()]

        return None

    def miss_button(self, players, actual_player, actual_round, player_launch):
        '''
        Miss button
        '''
        print('miss')
        players[actual_player].columns[player_launch] = ('MISS', 'str')
        self.display.play_sound('miss')
        players[actual_player].darts_thrown += 1
        if not players[actual_player].contrat_done and player_launch == 3:
            self.display.play_sound('kapitaldivision')
            players[actual_player].score = int(players[actual_player].score / 2)
