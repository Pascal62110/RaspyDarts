# -*- coding: utf-8 -*-
# Game by ... LaDite - 
########
import random
from include import cplayer
from include import cgame
##### TROPHEES
from include import ctrophies

############
# Game Variables
############

OPTIONS = {'theme': 'default', 'max_round': 8, 'winscore': 10, 'simple50' : False}
GAME_RECORDS = {'Points Per Round': 'DESC', 'Points Per Dart': 'DESC'}
NB_DARTS = 3  # Total darts the player has to play
LOGO = 'Target.png'
HEADERS = ['D1', 'D2', 'D3', '', 'Round', '', 'Target'] # Columns headers - Must be a string
VERSION = '1.05'

def check_players_allowed(nb_players):
    """
    Check if number of players is ok according to options
    """
    return nb_players >= 1 and nb_players <= 12, VERSION, 12
    
class CPlayerExtended(cplayer.Player):
    '''
    Extended player class
    '''
    def __init__(self, ident, config):
        super(CPlayerExtended, self).__init__(ident, config)
        for record in GAME_RECORDS:
            self.stats[record] = '0'

class Game(cgame.Game):
    '''
    Target game class
    '''
    def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
        super().__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)
        self.game_records = GAME_RECORDS
        self.nb_darts = NB_DARTS
        self.logo = LOGO
        self.headers = HEADERS
        self.options = options
        self.max_round = int(options['max_round'])
        if self.max_round > 15 :
                self.max_round = 15
        
        self.simple = options['simple50']

        if self.simple:
            self.score_map.update({'SB': 50})
        else:
            self.score_map.update({'SB': 25})

        self.winner = None
        self.dart = 0
        self.translate = self.display.lang.translate
        self.winscore = int(options['winscore'])
        self.target = [30,32,33,34,36,38,39,40,42,45,48,51,54,57,60,50]
        self.cible = random.shuffle(self.target)
        self.test = 0
        self.game_ended = False
         
    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        return_code = 0

        if player_launch == 1:
            players[actual_player].reset_darts()

        if actual_round == 1 and player_launch == 1 and actual_player == 0:
            try:
                self.check_handicap(players)
            except Exception as exception:
                self.logs.error(f'Handicap failed : {exception}')

            for player in players:
                player.score = 0
                player.reset_rounds(self.max_round)    

        if player_launch == 1:
            players[actual_player].round_points = 0
            players[actual_player].pre_play_score = players[actual_player].score
            players[actual_player].columns = []
            for i in range(0, 7):
                players[actual_player].columns.append(['', 'int'])
              
            if actual_player == 0:
                self.cible = self.target[-1]     
                self.target.pop()

            players[actual_player].columns[6] = (self.cible, 'int')
                
        for i in range(player_launch - 1, self.nb_darts):
            players[actual_player].columns[i] = ('', 'int')
            
        reste = self.cible - players[actual_player].round_points
        self.possible_hits = self.search_possibilities(reste, player_launch)

        if len(self.possible_hits) >= 1:
            players[actual_player].columns[player_launch - 1] = (self.possible_hits[0], 'str', 'game-silver')
        if len(self.possible_hits) >= 2:
            players[actual_player].columns[player_launch] = (self.possible_hits[1], 'str', 'game-silver')
        if len(self.possible_hits) >= 3:
            players[actual_player].columns[player_launch + 1] = (self.possible_hits[2], 'str', 'game-silver')

        self.rpi.set_target_leds('|'.join([f'{key}#{self.colors[0]}' for key in self.possible_hits]))
        players[actual_player].columns[6] = (self.cible, 'int')
        
        self.logs.debug(self.infos)
        return return_code

    def pnj_score(self, players, actual_player, level, player_launch):
        levels = [
            [15, 45, 40], [30, 50, 20], [40, 35, 15], [72, 23,  5], [90, 10,  0]
        ]

        try:
            comp_lvl = int(level)
        except (ValueError, TypeError):
            comp_lvl = 3

        lvl_idx = max(0, min(comp_lvl - 1, len(levels) - 1))
        p_exact = levels[lvl_idx][0]
        p_neighbor = levels[lvl_idx][1]

        target_hit = None
        if hasattr(self, 'possible_hits') and self.possible_hits:
            target_hit = self.possible_hits[0]
        
        if not target_hit:
            reste = self.cible - players[actual_player].round_points
            if 0 < reste <= 20:
                target_hit = f"S{reste}"
            else:
                target_hit = random.choice(['S20', 'S19', 'S18', 'S16'])

        mult = target_hit[0] if target_hit[:1] in ['S', 'D', 'T'] else 'S'
        try:
            val_str = target_hit[1:] if mult in ['S', 'D', 'T'] else target_hit
            if val_str in ['SB', 'DB', 'B']:
                base_val = val_str
            else:
                base_val = int(val_str)
        except ValueError:
            base_val = 20
            mult = 'S'

        if comp_lvl <= 2 and mult in ['T', 'D'] and random.randint(1, 100) <= 75:
            mult = 'S' 
        elif comp_lvl == 3 and mult == 'T' and random.randint(1, 100) <= 45:
            mult = 'S' 

        if base_val in ['SB', 'DB', 'B']:
            roll = random.randint(1, 100)
            if roll <= p_exact:
                return 'DB' if comp_lvl >= 4 and base_val == 'DB' else 'SB'
            elif roll <= p_exact + p_neighbor:
                return 'SB' if base_val == 'DB' else 'MISS'
            else:
                return 'MISS'

        dartboard_neighbors = {
            20: [1, 5],   1: [20, 18], 18: [1, 4],   4: [18, 13], 13: [4, 6],
            6: [13, 10], 10: [6, 15],  15: [10, 2],  2: [15, 17], 17: [2, 3],
            3: [17, 19], 19: [3, 7],   7: [19, 16], 16: [7, 8],   8: [16, 11],
            11: [8, 14], 14: [11, 9],  9: [14, 12], 12: [9, 5],   5: [12, 20]
        }

        roll = random.randint(1, 100)
        if roll <= p_exact:
            return f"{mult}{base_val}"
        elif roll <= p_exact + p_neighbor:
            neighbors = dartboard_neighbors.get(base_val, [1, 5])
            hit_val = random.choice(neighbors)
            if mult in ['D', 'T']:
                mult = 'S'
            return f"{mult}{hit_val}"
        else:
            return 'MISS'

    def check_winner(self, players):
        """
        Check if a player has won the game based on winscore
        """
        for player in players:
            if player.score >= self.winscore:
                return player.ident
        return None

    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        handler = self.init_handler()
        handler['show'] = (players[actual_player].darts, hit, True)
        handler['sound'] = hit

        score = self.score_map[hit]
        
        while len(players[actual_player].rounds) < actual_round:
            players[actual_player].rounds.append([''] * (self.nb_darts + 1))
        while len(players[actual_player].scores) < actual_round:
            players[actual_player].scores.append([0] * (self.nb_darts + 1))

        players[actual_player].add_dart(actual_round, player_launch, hit, score=score)
        players[actual_player].round_points += score
        
        # TROPHEES
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)
        
        ctrophies.process_single_dart(players[actual_player], hit)
        
        if player_launch == 1 :
                if players[actual_player].round_points == self.cible :
                        players[actual_player].score += 3
                        handler['sound'] = 'target_hit'
                        handler['return_code'] = 1
                elif players[actual_player].round_points > self.cible and actual_round <= self.max_round and actual_player != self.nb_players - 1 :
                        handler['sound'] = 'target_toohigh'
                        handler['return_code'] = 1
                elif players[actual_player].round_points > self.cible and actual_round == self.max_round and actual_player == self.nb_players - 1 :
                        handler['sound'] = 'target_toohigh'
                        handler['return_code'] = 3
        elif player_launch == 2 :
                if players[actual_player].round_points == self.cible :
                        players[actual_player].score += 2
                        handler['sound'] = 'target_hit'
                        handler['return_code'] = 1
                elif players[actual_player].round_points > self.cible and actual_round <= self.max_round and actual_player != self.nb_players - 1 :
                        handler['sound'] = 'target_toohigh'
                        handler['return_code'] = 1
                elif players[actual_player].round_points > self.cible and actual_round == self.max_round and actual_player == self.nb_players - 1 :
                        handler['sound'] = 'target_toohigh'
                        handler['return_code'] = 3        
        elif player_launch == 3 :
                if players[actual_player].round_points == self.cible :
                        players[actual_player].score += 1
                        handler['sound'] = 'target_hit'
                        handler['return_code'] = 1
                elif players[actual_player].round_points > self.cible :
                        handler['sound'] = 'target_toohigh'
                        handler['return_code'] = 1  
                elif players[actual_player].round_points < self.cible :
                        handler['sound'] = 'target_rate'
                        handler['return_code'] = 1  

        players[actual_player].columns[4] = (players[actual_player].round_points, 'int')
        players[actual_player].columns[player_launch - 1] = (score, 'int')

        if players[actual_player].round_points > self.cible :
                players[actual_player].columns[6] = ('cross-mark', 'image')
        elif players[actual_player].round_points == self.cible :
                players[actual_player].columns[6] = ('check-mark', 'image')
        elif players[actual_player].round_points < self.cible and player_launch == 3 :
                players[actual_player].columns[6] = ('cross-mark', 'image')
        
        players[actual_player].darts_thrown += 1
        players[actual_player].increment_hits(hit)
        self.refresh_stats(players, actual_round)

        # Check last round reached
        is_last_player_last_round = (actual_round >= self.max_round and actual_player == self.nb_players - 1)
        if is_last_player_last_round and (player_launch == int(self.nb_darts) or players[actual_player].round_points >= self.cible):
            self.infos += f"Last round reached ({actual_round}){self.lf}"
            best_id = self.best_score(players)
            self.winner = best_id
            if not self.game_ended:
                self.game_ended = True
                winning_player = players[best_id] if isinstance(best_id, int) and 0 <= best_id < len(players) else players[0]
                ctrophies.check_game_end_stats(players, winning_player, "TARGET")
            handler['return_code'] = 3
            return handler

        # Check winner using check_winner method (like By_Fives)
        self.winner = self.check_winner(players)
        if self.winner is not None:
            if not self.game_ended:
                self.game_ended = True
                winning_player = players[self.winner] if isinstance(self.winner, int) and 0 <= self.winner < len(players) else players[0]
                ctrophies.check_game_end_stats(players, winning_player, "TARGET")
            handler['return_code'] = 3
            return handler
       
        reste = self.cible - players[actual_player].round_points
        self.possible_titles = self.search_possibilities(reste, player_launch + 1)
        self.possible_hits = self.possible_titles
        if len(self.possible_hits) <= 0 and handler['return_code'] != 2 and handler['return_code'] != 3:
            handler['return_code'] = 1

        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        return handler

    def miss_button(self, players, actual_player, actual_round, player_launch):
        return_code = 0
        self.winner = self.check_winner(players)
        if self.winner is not None:
            if not self.game_ended:
                self.game_ended = True
                winning_player = players[self.winner] if isinstance(self.winner, int) and 0 <= self.winner < len(players) else players[0]
                ctrophies.check_game_end_stats(players, winning_player, "TARGET")
            return 3
        elif actual_round >= self.max_round and actual_player == self.nb_players - 1 \
                and player_launch == int(self.nb_darts):
            self.infos += f"Last round reached ({actual_round}){self.lf}"
            best_id = self.best_score(players)
            self.winner = best_id
            if not self.game_ended:
                self.game_ended = True
                winning_player = players[best_id] if isinstance(best_id, int) and 0 <= best_id < len(players) else players[0]
                ctrophies.check_game_end_stats(players, winning_player, "TARGET")
            return 3
        elif players[actual_player].round_points < self.cible :
            self.display.play_sound('target_rate')
            players[actual_player].columns[player_launch-1] = ('MISS', 'str')
            players[actual_player].darts_thrown += 1
            self.display.message(['Fléchette suivante'], None, None, 'middle', 'big')
        
        hit = 'MISS'
        ctrophies.process_single_dart(players[actual_player], hit)
        
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)
        
        return return_code

    def early_player_button(self, players, actual_player, actual_round):
        return 0

    def post_round_check(self, players, actual_round, actual_player):
        self.winner = self.check_winner(players)
        if self.winner is not None:
            player_obj = players[self.winner] if isinstance(self.winner, int) and 0 <= self.winner < len(players) else players[0]
            if not self.game_ended:
                self.game_ended = True
                ctrophies.check_game_end_stats(players, player_obj, "TARGET")
            return self.winner

        if actual_round >= self.max_round:
            best_id = self.best_score(players)
            self.winner = best_id
            if not self.game_ended:
                self.game_ended = True
                winning_player = players[best_id] if isinstance(best_id, int) and 0 <= best_id < len(players) else players[0]
                ctrophies.check_game_end_stats(players, winning_player, "TARGET")
            return self.winner
        return -2

    def get_score(self, player):
        return player.score

    def best_score(self, players):
        best_player = None
        best_score = -1
        for player in players:
            if player.score > best_score:
                best_score = player.score
                best_player = player.ident
        return best_player

    def next_set_order(self, players, actual_player):
        players.sort(key=self.get_score, reverse=True)

    def refresh_stats(self, players, actual_round):
        for player in players:
            player.stats['Points Per Round'] = player.show_ppr()
            player.stats['Points Per Dart'] = player.show_ppd()
            
    def search_possibilities(self, score, player_launch):
        '''
        The same suggestions as always, in the same order : the dart reaching the score is
        looked up in a table (all the turns of 3 darts were tried : 0.2 s on a Pi 3)
        '''
        first_hit = {}
        for hit, key in self.score_map.items():
            first_hit.setdefault(key, hit)
        for hit, key in self.score_map.items():
            if score == key:
                return [hit.upper()]
        finishes = [(hit, key) for hit, key in self.score_map.items() if score > key and hit[:1] in ('D', 'T')]
        if player_launch in (1, 2):
            for hit, key in finishes:
                if score - key in first_hit:
                    return [first_hit[score - key].upper(), hit.upper()]
        if player_launch == 1:
            for hit, key in finishes:
                firstrest = score - key
                for hit3, key3 in self.score_map.items():
                    if firstrest > key3 and firstrest - key3 in first_hit:
                        return [hit3.upper(), first_hit[firstrest - key3].upper(), hit.upper()]
        return []
