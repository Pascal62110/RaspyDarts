# -*- coding: utf-8 -*-
'''
Game by LB : Shangau
'''

from copy import deepcopy# For backupTurn
from include import cplayer
from include import cgame
from include import ctrophies
import random

#
LOGO = 'Shanghai.png'
HEADERS = ['HIT', 'MAX', '-', 'D1', 'D2', 'D3', '-']
OPTIONS = {'theme': 'default', 'max_round': 7, 'maitre': False, 'Points': True,'colorised': False}
NB_DARTS = 3
GAME_RECORDS = {'Score': 'DESC', 'Reached Score': 'DESC', 'Hits': 'DESC'}
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
        #The score the player has to hit
        self.actual_hit = 1 
        self.targets_list = []
        # Init Player Records to zero
        for game_record in GAME_RECORDS:
            self.stats[game_record] = '0'
            
class Game(cgame.Game):
    '''
    Shangai game class
    '''
    def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
        super().__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)
        self.logo = LOGO
        self.headers = HEADERS
        self.game_records = GAME_RECORDS
        self.nb_darts = NB_DARTS # Total darts the player has to play
        #  Get the maxiumum round number
        self.max_round = int(options['max_round'])
        # For Raspberry
        self.rpi = rpi
        self.options = options
        self.master = options['maitre']
        self.points = options['Points']
        self.game_is_ok_for_color = options['colorised']

        self.m_list = []

        self.infos = ''
        self.winner = None

    def save_turn(self, players):
        '''
        Create Backup Properies Array
        '''
        try:
            self.previous_backup = deepcopy(self.backup)
        except: # pylint: disable=bare-except
            self.infos += "No previous turn to backup."
            self.infos += "You cannot use BackUpTurn since you threw no darts"
        self.backup = deepcopy(players)
        self.infos += "Score Backup."

    def check_shangai(self, darts):
        '''
        Check Shangai
        D'après la regle faire un S T D dans n'importe quelle ordre
        sachant que lorsque l'on touche le segment allumé, le segment change à la flechette suivante
        On ne peut donc faire qu'une suite ex S1 T2 D3 mais S1 D1 T1 est impossible
        '''
        # Sécurité : vérifier qu'on a bien 3 lancements valides et non-nuls
        if not darts or len(darts) < 3:
            return False
            
        for d in darts:
            if d is None or not isinstance(d, str) or len(d) < 2:
                return False

        if self.master:
            return [darts[0][0], darts[1][0], darts[2][0]] == ['S', 'D', 'T'] \
                and darts[0][1:] < darts[1][1:] \
                and darts[1][1:] < darts[2][1:]
        else:
            return sorted([darts[0][0], darts[1][0], darts[2][0]]) == ['D', 'S', 'T'] \
                and darts[0][1:] < darts[1][1:] \
                and darts[1][1:] < darts[2][1:]

    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        '''
        Post dart check
        '''

        check = False
        score = 0

        handler = self.init_handler()

        if hit in self.targets_list:
            check = True
            score = self.score_map.get(hit)
            players[actual_player].increment_hits(hit)
            self.infos += f"Player {actual_player} :{self.lf}"
            self.infos += f"    your score was {players[actual_player].score}{self.lf}"
            players[actual_player].score += score
            self.infos += f"    hit a {hit}{self.lf}"
            self.infos += f"    your score is now {players[actual_player].score}"
            self.infos += f"    you have now to hit {players[actual_player].actual_hit}{self.lf}"
            # Now update hit for next dart
            players[actual_player].actual_hit += 1

        elif self.master:
            # Missed and ( master or not points )
            # => next player
            handler['return_code'] = 1
        
        
        players[actual_player].columns[player_launch+2] = (hit, 'txt')
        
        
        players[actual_player].add_dart(actual_round, player_launch, hit, check=check, score=score)

        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)
        
        
        # TROPHEES
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)

        if players[actual_player].actual_hit == 21:
            players[actual_player].actual_hit = 'B'
        self.infos += f"now {players[actual_player].actual_hit}"

        # Update Score, darts count and Max score possible
        max_score = self.check_max(player_launch + 1, actual_round, \
                players[actual_player].actual_hit, players[actual_player].score)
        if players[actual_player].actual_hit == 'B':
            players[actual_player].columns[0] = (players[actual_player].actual_hit, 'str')
        else:    
            players[actual_player].columns[0] = (players[actual_player].actual_hit, 'int')
        players[actual_player].columns[1] = (max_score, 'int', 'game-green')
        

        if player_launch == 3 and self.check_shangai(players[actual_player].darts):
            self.infos += f"Victory of player {players[actual_player].ident} !{self.lf}"
            self.winner = players[actual_player].ident
            handler['return_code'] = 3
        elif player_launch == 3:
            # Check actual winnner
            self.winner = -1
            if actual_round == self.max_round and actual_player == self.nb_players - 1:
                self.winner = self.check_winner(players)

            if self.winner == -1 and self.play_show(players[actual_player].darts, hit):
                if check:
                    handler['sound'] = hit
                else:
                    handler['sound'] = 'plouf'
        else:
            self.winner = -1
            if check:
                handler['sound'] = hit
            else:
                handler['sound'] = 'plouf'

        self.infos += f"self.winner={self.winner}{self.lf}"
        self.infos += f"player_launch={player_launch}{self.lf}"

        if self.winner != -1:
            self.infos += f"Current winner is Player {self.winner}{self.lf}"

        # Last round
        if actual_round >= self.max_round and actual_player == self.nb_players - 1 \
                and player_launch == int(self.nb_darts) and handler['return_code'] == 0:
            self.infos += f"Last round reached ({actual_round}){self.lf}"
            if self.winner != -1 and self.points:
                self.infos += "Here is a winner"
                handler['return_code'] = 3
            else:
                self.infos += "No winner"
                handler['return_code'] = 2

        # --- VÉRIFICATION DES TROPHÉES DE FIN DE PARTIE ---
        if handler.get('return_code') == 3 and self.winner is not None and self.winner != -1:
            winning_player = players[self.winner]
            ctrophies.check_game_end_stats(players, winning_player, "SHANGHAI")
        # --------------------------------------------------

        # You may want to count darts played
        players[actual_player].darts_thrown += 1

        # It is recommanded to update stats every dart thrown
        self.refresh_stats(players, actual_round)

        # Update hit
        if player_launch != 3:
            if players[actual_player].actual_hit == 'B':
                players[actual_player].columns[0] = (players[actual_player].actual_hit, 'str')
            else:
                players[actual_player].columns[0] = (players[actual_player].actual_hit, 'int')

        # Print debug infos
        self.logs.debug(self.infos)

        # Time for shot or video ?
        handler['take_shot'] = self.time_to_take_shot_or_video(hit)

        return handler

    def pnj_score(self, players, actual_player, computer_level, player_launch):
        '''
        Compute PNJ Score for Shanghai with active Shanghai attempt strategy.
        '''
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende des niveaux : [miss_rate, accuracy_rate, double_rate, triple_rate, slip_rate]
        #   * miss_rate     : Taux de raté pur (miss, 'MISSDART', %)
        #   * accuracy_rate : Précision à viser la cible actuelle (%)
        #   * double_rate   : Probabilité ou seuil de réussite pour les doubles (%)
        #   * triple_rate   : Probabilité ou seuil de réussite pour les triples (%)
        #   * slip_rate     : Taux de glissement vers un voisin géographique sur la matrice (%)
        # - Plus fort / précis : Diminuer le miss_rate et le slip_rate, augmenter l'accuracy_rate.
        # - Plus humain / brouillon : Augmenter le miss_rate et le slip_rate.
        # =========================================================================
        levels = [
            [25, 15, 12, 16, 50],  # 1 : Noob
            [15, 25, 12, 16, 50],  # 2 : Débutant
            [ 1, 55, 30, 40, 80],  # 3 : Intermédiaire
            [ 0, 99, 30, 98, 99],  # 4 : Pro
            [ 0, 99, 30, 98, 99]   # 5 : Expert
        ]

        geo_neighbors = {
            1: [20, 18, 4], 2: [17, 15, 10], 3: [19, 17, 2], 4: [18, 13, 1], 
            5: [20, 12, 9], 6: [10, 13, 15], 7: [19, 16, 8], 8: [16, 11, 7], 
            9: [14, 12, 5], 10: [15, 6, 2], 11: [14, 8, 16], 12: [9, 5, 20], 
            13: [6, 4, 11], 14: [9, 11, 16], 15: [10, 2, 6], 16: [7, 8, 11], 
            17: [2, 3, 15], 18: [4, 1, 20], 19: [7, 3, 2], 20: [1, 5, 12]
        }


        lvl_idx = max(0, min(computer_level - 1, len(levels) - 1))

        # 1. Test du MISS pur
        if random.randrange(100) < levels[lvl_idx][0]:
            players[actual_player].columns[player_launch + 2] = ('MISS', 'str')
            self.display.play_sound('miss')
            players[actual_player].darts_thrown += 1
            return 'MISS'

        current_target = players[actual_player].actual_hit

        # 2. Détermination du segment visé
        if random.randrange(100) < levels[lvl_idx][1]:
            segment = current_target
        elif current_target != 'B' and current_target in geo_neighbors and random.randrange(100) < levels[lvl_idx][4]:
            segment = random.choice(geo_neighbors[current_target])
        else:
            segment = random.randint(1, 20) if current_target != 'B' else 25

        # 3. Stratégie active pour tenter le Shanghai selon le numéro de la fléchette (player_launch)
        allowed_mults = self.m_list if self.m_list else ['S', 'D', 'T']
        mult_rand = random.randrange(100)

        # Si on vise le Bull, pas de triple/double complexe
        if segment == 25 or current_target == 'B':
            score_str = 'DB' if mult_rand < levels[lvl_idx][3] else 'SB'
        else:
            target_mult = None
            
            if computer_level >= 3:
                # Sécurisation : on filtre les éléments pour éviter le NoneType is not subscriptable
                previous_darts = players[actual_player].darts[:player_launch - 1]
                hit_types = [d[0] for d in previous_darts if d is not None]
                
                # S'il manque un Triple et qu'il est autorisé
                if 'T' not in hit_types and 'T' in allowed_mults and mult_rand < levels[lvl_idx][3]:
                    target_mult = 'T'
                # S'il manque un Double et qu'il est autorisé
                elif 'D' not in hit_types and 'D' in allowed_mults and mult_rand < levels[lvl_idx][2]:
                    target_mult = 'D'
                # Sinon un Simple si autorisé
                elif 'S' in allowed_mults:
                    target_mult = 'S'

            # Fallback sur la sélection classique si pas de ciblage spécifique de Shanghai
            if not target_mult:
                if 'T' in allowed_mults and mult_rand < levels[lvl_idx][3]:
                    target_mult = 'T'
                elif 'D' in allowed_mults and mult_rand < levels[lvl_idx][2]:
                    target_mult = 'D'
                elif 'S' in allowed_mults:
                    target_mult = 'S'
                else:
                    target_mult = allowed_mults[0]

            score_str = f'{target_mult}{segment}'

        return score_str



    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        '''
        Before each throw - update screen, display score, etc...
        '''
        self.infos = ''

        if player_launch == 1:
            players[actual_player].reset_darts()
            
            for dart_col in range(3, 6):
                players[actual_player].columns[dart_col] = ('', 'str') 
            # Update Score
            if players[actual_player].actual_hit == 'B':
                players[actual_player].columns[0] = (players[actual_player].actual_hit, 'str')
            else:
                players[actual_player].columns[0] = (players[actual_player].actual_hit, 'int')
            players[actual_player].reset_rounds(self.max_round)
            self.save_turn(players)

            if self.master:
                self.m_list = ['S']
            else:
                self.m_list = ['S', 'D', 'T']
        elif player_launch == 2 and self.master:
            self.m_list = ['D']
        elif player_launch == 3 and self.master:
            self.m_list = ['T']
        else:
            try:
                self.m_list.remove(players[actual_player].darts[-1][0])
            except: # pylint: disable=bare-except
                self.logs.debug("already hit")

        # Compte S18, D18
        self.targets_list = [f'{mult}{players[actual_player].actual_hit}' for mult in self.m_list]

        max_score = self.check_max(player_launch, actual_round, \
                players[actual_player].actual_hit, players[actual_player].score)
        players[actual_player].columns[1] = (max_score, 'int', 'game-green')
        self.rpi.set_target_leds('|'.join([f'{key}#{self.colors[0]}' \
                for key in self.targets_list]))


        # For further code cleaning
        # Return 18$|D18$
        return (self.targets_list, None, None)
    
    def refresh_game_screen(self, players, actual_round, max_round, rem_darts, nb_darts, logo, headers, actual_player, TxtOnLogo=False, Wait=False, OnScreenButtons=None, showScores=True, end_of_game=False, endOfSet=None, Set=None, MaxSet=None):
        
        result = self.display.refresh_game_screen(players, actual_round, max_round, rem_darts, \
                          nb_darts, logo, headers, actual_player, TxtOnLogo, Wait, OnScreenButtons, \
                          showScores, end_of_game, endOfSet, Set, MaxSet)
        self.display.update_screen()

        return result
    
    def check_max(self, player_launch, actual_round, actual_hit, actual_score):
        '''
        Search MAX possible score for this player
        '''
        max_score = actual_score
        darts_left =  (self.nb_darts - (player_launch-1))
        # Bull special case
        if actual_hit == 'B':
            actual_hit = 21
        for i in range(0, darts_left):
            if actual_hit  == 21:
                max_score += 50
            else:
                max_score += (actual_hit + i) * 3 
        return max_score

    def early_player_button(self, players, actual_player, actual_round):
        '''
        Pushed Player Early
        '''
        if actual_round == self.max_round and actual_player == self.nb_players - 1:
            self.winner = self.check_winner(players)
            if self.winner != -1:
                self.infos += f"Current winner is Player {self.winner}"
                winning_player = players[self.winner]
                ctrophies.check_game_end_stats(players, winning_player, "SHANGHAI")
                return 3
            return 2
        return 1

    def miss_button(self, players, actual_player, actual_round, player_launch):
        '''
        Miss button
        '''
        print('miss')
        #players[actual_player].columns[6] = (self.moyenne, 'int')
        players[actual_player].columns[player_launch+2] = ('MISS', 'str')
        self.display.play_sound('miss')
        players[actual_player].darts_thrown += 1
        
        hit = 'MISS'

        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)
        
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)
                    
        # play penality sound
        self.display.play_sound('penality')

    def refresh_stats(self, players, actual_round):
        '''
        Method to frefresh player.stat - Adapt to the stats you want.
        They represent mathematical formulas used to calculate stats. Refreshed after every launch
        '''
        for player in players:
            player.stats['Score'] = player.score
            player.stats['Reached Score'] = player.actual_hit
            player.stats['Hits'] = player.get_total_hit()
