# -*- coding: utf-8 -*-
'''
Game by ... David ! Low Score
'''
########
from include import cplayer
from include import cgame
import random
#### TROPHEES
from include import ctrophies

############
# Game Variables
############
OPTIONS = {'theme': 'default', 'max_round': 10, 'penality': 50}
GAME_RECORDS = {'Points Per Round': 'ASC', 'Points Per Dart': 'ASC'}
NB_DARTS = 3
LOGO = 'Low_Score.png'
HEADERS = ['D1', 'D2', 'D3', '', 'Rnd', 'PPD', 'PPR']
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
        # Extend the basic players property with your own here
        # Init Player Records to zero
        for record in GAME_RECORDS:
            self.stats[record] = '0'
        self.darts_thrown = 0

class Game(cgame.Game):
    '''
    Low score class game
    '''
    # Like player_launch but not visible inside method early_player_button
    def __init__(self ,display, game, nb_players, options, config, logs, rpi, dmd, video_player):
        super().__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)

        ##############
        # VAR
        ##############
        # Dictionary of options in STRING format.
        # You can use any numeric value or 'True' or 'False', but in string format.
        # Don't put more than 10 options per game or you will experience display issues
        self.options = options
        # Dictionary of stats and display order (For example : Points Per Darts and avg
        # are displayed in descending order)
        self.game_records = GAME_RECORDS
        # How many darts per player and per round ? Yes ! this is a feature :)
        self.nb_darts = NB_DARTS  # Total darts the player has to play
        # Background image - relative to images folder - Name it like the game itself
        self.logo = LOGO
        # Columns headers - Better as a string
        self.headers = HEADERS
        # self.score_map.update({'SB':50})
        #  Get the maximum round number
        self.max_round = int(options['max_round'])
        #  Penality points for a missing dart
        self.penality = int(options['penality'])

        self.winner = None

    def pnj_score(self, players, actual_player, computerLevel, player_launch):
        '''
        IA réaliste pour Low Score : cherche à faire un minimum de points.
        Le PNJ privilégie les zones à très faible valeur (simples 1, 5, 20, etc.) 
        et évite les gros triples ou doubles, tout en gérant le taux de raté.
        '''
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende : [Taux de miss pur (miss_rate, %), Taux de glissement/déviation sur la matrice (slip_rate, %)]
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

        # 1. Test du MISS pur : On retourne simplement 'MISSDART' pour laisser 
        # le système principal gérer la pénalité une seule et unique fois.
        if random.randrange(100) < miss_rate:
            players[actual_player].columns[player_launch - 1] = ('MISS', 'str')
            self.display.play_sound('miss')
            self.display.play_sound('penality')
            players[actual_player].darts_thrown += 1
            return 'MISS'

        # Stratégie Low Score : viser volontairement de petits chiffres simples
        low_value_targets = [1, 5, 2, 3, 4, 9, 12]
        target_num = random.choice(low_value_targets)
        mult = 'S'

        # 2. Simulation de la déviation / glissement de la matrice physique
        if random.randrange(100) < slip_rate:
            if target_num in geo_neighbors:
                target_num = random.choice(geo_neighbors[target_num])
            mult = 'S'

        return f'{mult}{target_num}'


    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        '''
        Actions done before each dart throw - for example, check if the player is allowed to play
        '''
        return_code = 0
        self.actual_round = actual_round
        
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
            players[actual_player].darts_thrown = 0

            players[actual_player].round_points = 0
            self.save_turn(players)
            players[actual_player].pre_play_score = players[actual_player].score

            #Reset display Table
            players[actual_player].columns = []

            # Clean all next boxes
            for _ in range(0, 7):
                players[actual_player].columns.append(['','int'])

        # Display stats
        if actual_round == 1 and player_launch == 1:
            players[actual_player].columns[5] = (0.0,'int')
            players[actual_player].columns[6] = (0.0,'int')
        else:
            players[actual_player].columns[5] = (players[actual_player].show_ppd(),'int')
            players[actual_player].columns[6] = (players[actual_player].show_ppr(),'int')

        # Print debug output
        self.logs.debug(self.infos)
        return return_code

    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        '''
        Function run after each dart throw - for example, add points to player
        '''
        handler = self.init_handler()

        players[actual_player].darts_thrown = player_launch

        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)

        
        handler['show'] = (players[actual_player].darts, hit, True)
        handler['sound'] = hit

        # test SB ou DB
        if hit in ('SB', 'DB'):
            score = -self.score_map[hit]
        else:
            score = self.score_map[hit]

        players[actual_player].score += score
        players[actual_player].round_points += score
        players[actual_player].points += score
        players[actual_player].columns[player_launch - 1] = (score, 'int')

        players[actual_player].add_dart(actual_round, player_launch, hit, score=score)
        
        # TROPHEES
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)

        # Record total dart thrown, total hits (S=1, D=2, T=3) and refresh players stats
        players[actual_player].increment_hits(hit)

        # Refresh stats
        players[actual_player].columns[5] = (players[actual_player].show_ppd(), 'int')
        players[actual_player].columns[6] = (players[actual_player].show_ppr(), 'int')
        self.refresh_stats(players,actual_round)

        # Check for end of game (no more rounds to play)
        if player_launch == self.nb_darts and actual_round >= self.max_round \
                and actual_player == len(players) - 1:
            
            self.winner = self.check_winner(players, high=False)
           
            if self.winner is not None:
                winning_player = players[self.winner].name
                
                print('winner lowscore')
                print(winning_player)
                
                # On enregistre les stats uniquement si on a un vrai gagnant
                ctrophies.check_game_end_stats(players, winning_player, "low_score")
                
                handler['return_code'] = 3
            else:
                # No winner : last round reached
                ctrophies.check_game_end_stats(players, None, "low_score")
                handler['return_code'] = 2

        # Time for shot or video ?
        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        
        return handler

    def miss_button(self, players, actual_player, actual_round, player_launch):
        '''
        Miss button
        '''
        players[actual_player].score += self.penality
        players[actual_player].columns[player_launch-1] = ('MISS', 'str')
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
        
        # play penality sound
        self.display.play_sound('penality')
        # Refresh stats
        players[actual_player].columns[5] = (players[actual_player].show_ppd(), 'int')
        players[actual_player].columns[6] = (players[actual_player].show_ppr(), 'int')
        self.refresh_stats(players, actual_round)

    def early_player_button(self, players, actual_player, actual_round):
        '''
        Function launched when the  put player button before having launched all his darts
        '''
        # Jump to next player by default
        return_code = 1

        # darts_thrown for missing target
        players[actual_player].darts_thrown += (self.nb_darts - players[actual_player].darts_thrown)

        # Check missing darts
        penality = (self.nb_darts - players[actual_player].darts_thrown) * self.penality

        if penality > 0:
            # add penality points
            players[actual_player].score += penality
            players[actual_player].round_points += penality # Keep total for this round
            players[actual_player].points += penality #for ppd,ppr

            # Refresh stats
            players[actual_player].columns[5] = (players[actual_player].show_ppd(),'int')
            players[actual_player].columns[6] = (players[actual_player].show_ppr(),'int')
            self.refresh_stats(players,actual_round)

            # play penality sound
            self.display.playSound('penality')

            # anim leds for the penality
            #Event.Publish('penalty')

        if actual_round >= self.max_round and actual_player == self.nb_players - 1:
            bestscoreid = -1
            bestscore = 10000
            for player in players:
                if player.score < bestscore:
                    bestscore = player.score
                    bestscoreid = player.ident
            self.winner = bestscoreid
            return_code = 3

        return return_code

    def refresh_stats(self, players, actual_round):
        '''
        Method to refresh player.stat - Adapt to the stats you want.
        They represent mathematical formulas used to calculate stats. Refreshed after every launch
        '''
        for player in players:
            player.stats['Points Per Round'] = player.show_ppr()
            player.stats['Points Per Dart'] = player.show_ppd()
