# -*- coding: utf-8 -*-
# Game by ... laDite!
########
import random
from include import cplayer
from include import cgame
#### TROPHEES
from include import ctrophies

############
# Game Variables
############
OPTIONS = {'theme': 'default', 'max_round': 10, 'winscore': 100, 'negatif_div2' : True}
GAME_RECORDS = {'Points Per Round': 'DESC', 'Points Per Dart': 'DESC'}
NB_DARTS = 3  # Total darts the player has to play
LOGO = 'Bulls.png'
HEADERS = ['D1', 'D2', 'D3', '', '', '', ''] # Columns headers - Must be a string
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
    def __init__(self, ident, config):
        super(CPlayerExtended, self).__init__(ident, config)
        # Extend the basic players property with your own here
        # Init Player Records to zero
        for record in GAME_RECORDS:
            self.stats[record] = '0'

class Game(cgame.Game):
    """
    Bulls game class
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

        self.winner = None
        self.winscore = int(options['winscore'])
        self.negatif_div2 = options['negatif_div2']
        
        self.video_player = video_player
        self.targets = ''
        self.leds = True
        #  Penality points for a missing dart
        self.penality = 20
        self.game_ended = False  # Verrou pour empêcher le double comptage des stats/victoires
        
  
    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        """
        Actions done before each dart throw - for example, check if the player is allowed to play
        """
        handler = self.init_handler()
        
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
        
        return handler

    def pnj_score(self, players, actual_player, computer_level, player_launch):
        """
        Compute PNJ Score for Bulls game (Nerfed version to prevent fast wins):
        - Lowered Bull probabilities across all levels.
        - Favors Single Bull (SB) over Double Bull (DB) to control score spikes.
        - Uses a strict dartboard neighbor matrix for realistic near-misses.
        """
        dartboard_neighbors = {
            1: (20, 18), 2: (15, 17), 3: (17, 19), 4: (18, 13), 5: (12, 20),
            6: (13, 10), 7: (19, 16), 8: (16, 11), 9: (14, 12), 10: (6, 15),
            11: (8, 14), 12: (9, 5), 13: (4, 6), 14: (11, 9), 15: (10, 2),
            16: (7, 8), 17: (2, 3), 18: (1, 4), 19: (3, 7), 20: (5, 1)
        }

        levels = [
            [2,  28, 70],  # Niveau 1
            [5,  35, 60],  # Niveau 2
            [25, 30, 45],  # Niveau 3
            [20, 40, 40],  # Niveau 4
            [35, 45, 20]   # Niveau 5
        ]
        
        lvl_idx = max(0, min(computer_level - 1, len(levels) - 1))
        p_bull = levels[lvl_idx][0]
        p_neighbor = levels[lvl_idx][1]

        rand_val = random.randrange(100)

        if rand_val < p_bull:
            return 'SB' if random.randrange(100) < 85 else 'DB'
        elif rand_val < p_bull + p_neighbor:
            target = random.randint(1, 20)
            neighbor = random.choice(dartboard_neighbors[target])
            return f"S{neighbor}"
        else:
            return f"S{random.randint(1, 20)}"

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
        
        #TROPHEES        
        ctrophies.process_single_dart(players[actual_player], hit) 

        if hit == 'SB' :   
            score = 25
        elif hit == 'DB' :
            score = 50
        else :
            if self.negatif_div2 :
                    score = round((self.score_map[hit] / 2) *-1)
            else :
                    score = self.score_map[hit] *-1

        handler['return_code'] = 0

        players[actual_player].add_dart(actual_round, player_launch, hit, score=score)
        
        # TROPHEES
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)
        

        players[actual_player].score += score
        players[actual_player].round_points += score
        players[actual_player].points += score

        players[actual_player].columns[player_launch - 1] = (score, 'int')
        players[actual_player].columns[4] = (players[actual_player].round_points, 'int')
        
        players[actual_player].darts_thrown += 1
        players[actual_player].increment_hits(hit)
        self.refresh_stats(players, actual_round)
        
        # Vérification immédiate si un joueur atteint ou dépasse winscore (100 points)
        for p in players:
            if p.score >= self.winscore:
                self.winner = p.ident
                if not self.game_ended:
                    self.game_ended = True
                    ctrophies.check_game_end_stats(players, p, "BULLS")
                handler['return_code'] = 3
                return handler

        # Check last round
        if actual_round >= self.max_round and actual_player == self.nb_players - 1 \
                and (player_launch == self.nb_darts or handler['return_code'] ==  1) :
            winner_id = self.best_score(players)
            self.winner = winner_id
            self.infos += f"Last round reached ({actual_round}){self.lf}"
            if winner_id != -1 and not self.game_ended:
                self.game_ended = True
                winning_player = next((p for p in players if p.ident == winner_id), players[0])
                ctrophies.check_game_end_stats(players, winning_player, "BULLS")
            handler['return_code'] = 2
            return handler

        self.logs.debug(self.infos)

        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        return handler

    def miss_button(self, players, actual_player, actual_round, player_launch):
        '''
        Miss button
        '''
        players[actual_player].score -= self.penality
        players[actual_player].columns[player_launch-1] = ('MISS', 'str')
        
        self.display.play_sound('miss')
        
        players[actual_player].darts_thrown += 1
        
        hit = 'MISS'
        ctrophies.process_single_dart(players[actual_player], hit)
        
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)
        
        self.display.message([self.display.lang.translate('Color-miss')], 1000, None, 'middle', 'big')

    def early_player_button(self, players, actual_player, actual_round, player_launch):
        '''
        Function launched when the put player button before having launched all his darts
        '''
        handler = self.init_handler()
        handler['return_code'] = 1
        
        penality = 0
        if player_launch == 1:
                penality = 60
        elif player_launch == 2:
                penality = 40
        elif player_launch == 3:
                penality = 20

        if penality > 0:
            players[actual_player].score -= penality
            players[actual_player].round_points -= penality 
            handler['sound'] = 'penality'
            
        return handler

    def post_round_check(self, players, actual_round, actual_player):
        """
        Post round checks
        When PLAYER BUTTON is pressed on last round of last player
        """
        for player in players:
            if player.score >= self.winscore:
                self.winner = player.ident
                if not self.game_ended:
                    self.game_ended = True
                    ctrophies.check_game_end_stats(players, player, "BULLS")
                return self.winner
       
        if actual_round >= self.max_round and actual_player == len(players) - 1:
            winner = self.best_score(players)
            if winner != -1:
                self.winner = winner
                if not self.game_ended:
                    self.game_ended = True
                    winning_player = next((p for p in players if p.ident == winner), players[0])
                    if winning_player:
                        ctrophies.check_game_end_stats(players, winning_player, "BULLS")
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
            player.stats['Points Per Round'] = player.avg(actual_round)
            player.stats['Points Per Dart'] = player.show_ppd()

    def display_segment(self):
       """
       Set if a message is shown to indicate the segment hitted !
       """
       return False
