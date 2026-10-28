# -*- coding: utf-8 -*-
# Game by ... LaDite
########
import random
from include import cplayer
from include import cgame
#

############
# Game Variables
############

OPTIONS = {'theme': 'default', 'max_round': 20, 'start': '10', 'double': False, 'triple': False, 'jump': False, 'master': False, 'bull': False}

GAME_RECORDS = {'Points Per Round': 'DESC', 'Points Per Dart': 'DESC'}
NB_DARTS = 3  # Total darts the player has to play
LOGO = 'Slider.png'
HEADERS = ["D1", "D2", "D3", "", "Rnd", "", "JOUE"] # Columns headers - Must be a string
VERSION = '1.00'

def check_players_allowed(nb_players):
    """
    Check if number of players is ok according to options
    """
    return nb_players >= 1 and nb_players <= 12, VERSION, 12
    
GEO_NEIGHBORS = {
    1: [20, 18, 4], 2: [17, 15, 10], 3: [19, 17, 2], 4: [18, 13, 1],
    5: [20, 12, 9], 6: [10, 13, 15], 7: [19, 16, 8], 8: [16, 11, 7],
    9: [14, 12, 5], 10: [15, 6, 2], 11: [14, 8, 16], 12: [9, 5, 20],
    13: [6, 4, 11], 14: [9, 11, 16], 15: [10, 2, 6], 16: [7, 8, 11],
    17: [2, 3, 15], 18: [4, 1, 20], 19: [7, 3, 2], 20: [1, 5, 12]
}  # Voisins géographiques sur la cible standard (comme dans Tennis.py)


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
        
        self.character = 0
        

class Game(cgame.Game):
    """
    bowling game class
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
        self.video_player = video_player
        
### declaration variable 
        self.next = 0
        self.rate = 0
        self.gagne = False
        self.player_launch = 0
        self.repetition = True
        
        self.options = options
        self.leds = str(options['start'])
        self.double = options['double']
        self.triple = options['triple']
        self.saut = options['jump']
        self.master = options['master']
        self.bull = options['bull']

        
    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        """
        Actions done before each dart throw - for example, check if the player is allowed to play
        """
        return_code = 0

        if not players[actual_player].alive:
            self.logs.debug(f'Le joueur {actual_player} est éliminé. Il passe son tour')
            return 4
            
        if player_launch == 1:
            players[actual_player].reset_darts()
            self.rate = 0
            self.repetition = True

        # Set score at startup
        if actual_round == 1 and player_launch == 1 and actual_player == 0:
            try:
                self.check_handicap(players)
            except Exception as exception: # pylint: disable=broad-except
                self.logs.error(f"Handicap failed : {exception}")

            for player in players:
                # Init score
                player.score = 0
                player.leds = self.leds
                player.lives = 0
                player.alive = True

        # Each new player
        if player_launch == 1:
       
            players[actual_player].round_points = 0
            players[actual_player].pre_play_score = players[actual_player].score

            #Reset display Table
            players[actual_player].columns = []
            
            # Clean all next boxes
            for i in range(0,7):
                players[actual_player].columns.append(['', 'int'])
                
            if actual_round == 1 and actual_player == 0:
                for player in players:
                    player.reset_rounds(self.max_round)

       # Clean next boxes
        for i in range(player_launch - 1,self.nb_darts):
            players[actual_player].columns[i] = ('', 'int')

### GESTION PLAYERS.LEDS MAX
        if int(players[actual_player].leds) >= 21 and self.bull :
                players[actual_player].columns[6] = ('B', 'txt') 
        elif int(players[actual_player].leds) >= 21 and not self.bull :
                players[actual_player].leds = 20
                players[actual_player].columns[6] = (players[actual_player].leds, 'int') 
        else :
                players[actual_player].columns[6] = (players[actual_player].leds, 'int')

### GESTION DES LEDS         
        if self.bull and int(players[actual_player].leds) == 21 :
                self.rpi.set_target_leds ('')
                leds = f'SB#green|DB#green'
                self.rpi.set_target_leds (leds)
        elif self.double and not self.triple :
                self.rpi.set_target_leds ('')
                leds = f'D{players[actual_player].leds}#green'
                self.rpi.set_target_leds(leds)
        elif self.triple and not self.double :
                self.rpi.set_target_leds ('')
                leds = f'T{players[actual_player].leds}#green'
                self.rpi.set_target_leds(leds)
        elif self.double and self.triple :
                self.rpi.set_target_leds ('')
                leds = f'D{players[actual_player].leds}#green|T{players[actual_player].leds}#green'
                self.rpi.set_target_leds(leds)
        else :
                self.rpi.set_target_leds ('')
                leds = f'S{players[actual_player].leds}#green|D{players[actual_player].leds}#green|T{players[actual_player].leds}#green'
                self.rpi.set_target_leds(leds)

        # Print debug output
        self.logs.debug(self.infos)
        return return_code

        self.player_launch = player_launch
        
    def pnj_score(self, players, actual_player, computer_level, player_launch):
        """
        Compute PNJ Score for this game according to computer level, options and current target.
        """
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende des niveaux : [miss_rate, accuracy_rate, double_rate, triple_rate, slip_rate]
        #   * miss_rate     : Taux de raté pur (miss, 'MISSDART', %)
        #   * accuracy_rate : Précision / probabilité de viser directement la cible actuelle (%)
        #   * double_rate   : Taux ou poids lié aux doubles (%)
        #   * triple_rate   : Taux ou poids lié aux triples (%)
        #   * slip_rate     : Taux de glissement vers un voisin géographique sur la matrice (%)
        # - Plus fort / précis : Diminuer le miss_rate et le slip_rate, augmenter l'accuracy_rate.
        # - Plus humain / brouillon : Augmenter le miss_rate et le slip_rate.
        # =========================================================================
        levels = [
            [35, 10, 10, 10, 30],  # 1 : Noob
            [20, 25, 15, 15, 40],  # 2 : Débutant
            [ 5, 50, 25, 30, 60],  # 3 : Intermédiaire
            [ 1, 80, 40, 50, 80],  # 4 : Pro
            [ 0, 95, 60, 70, 90]   # 5 : Expert
        ]

        lvl_idx = max(0, min(computer_level - 1, len(levels) - 1))

        if random.randrange(100) < levels[lvl_idx][0]:
            players[actual_player].darts_thrown += 1
            self.rate += 1
            if self.rate == 3:
                a = int(players[actual_player].leds)
                players[actual_player].leds = str(a - 1)
            return 'MISSDART'

        current_target = int(players[actual_player].leds) if str(players[actual_player].leds).isdigit() else 21

        if current_target >= 21 and self.bull:
            bull_rand = random.randrange(100)
            if bull_rand < levels[lvl_idx][2]:
                return 'DB'
            elif bull_rand < levels[lvl_idx][2] + levels[lvl_idx][3]:
                return 'SB'
            else:
                return f"S{random.randint(1, 20)}"

        rand_val = random.randrange(100)
        if rand_val < levels[lvl_idx][1]:
            segment = current_target
        elif current_target in GEO_NEIGHBORS and rand_val < levels[lvl_idx][1] + levels[lvl_idx][4]:
            segment = random.choice(GEO_NEIGHBORS[current_target])
        else:
            segment = random.randint(1, 20)

        if segment > 20:
            segment = 20

        # --- GESTION NATURELLE DU MULTIPLICATEUR ( COMME UN HUMAIN ) ---
        mult_rand = random.randrange(100)
        
        chance_triple = levels[lvl_idx][3] // 2  
        chance_double = levels[lvl_idx][2] // 2

        if mult_rand < chance_triple:
            mult = 'T'
        elif mult_rand < chance_triple + chance_double:
            mult = 'D'
        else:
            mult = 'S'

        return f'{mult}{segment}'
        
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

        # Play DMD animation
        if super().play_show(players[actual_player].darts, hit, play_special=True):
            handler['sound'] = hit

        score = 0
        saut = 0

### TOUCHE LE BON SEGMENT        
        if hit[1:] == 'B' and self.bull and int(players[actual_player].leds) == 21 :
                if hit == 'SB' :
                        score = 5
                elif hit == 'DB' :
                        score = 8
                        
                self.gagne = True
                
        elif (hit[1:]) == players[actual_player].leds and int(players[actual_player].leds) < 20 :
                if self.double and not self.triple :
                        if hit[:1] == 'D' :
                                score = 4
                                saut = 2 
                        else :
                                score = 0
                                saut = 0
                elif self.triple and not self.double :
                        if hit[:1] == 'T' :
                                score = 6
                                saut = 3 
                        else :
                                score = 0
                                saut = 0
                                
                elif self.double and self.triple :
                        if hit[:1] == 'D' :
                                score = 4
                                saut = 2
                        elif hit[:1] == 'T' :
                                score = 6
                                saut = 3
                        else :
                                score = 0
                                saut = 0
                                        
                elif not self.triple and not self.double :
                        if hit[:1] == 'S' :
                                score = 1
                                saut = 1
                        elif hit[:1] == 'D' :
                                score = 2
                                saut = 2
                        elif hit[:1] == 'T' :
                                score = 3  
                                saut = 3 
                        else : 
                                score = 0
                                saut = 0
                else :
                        score = 0
                        saut = 0
                        
                increment = saut if self.saut else 1
                a = int(players[actual_player].leds)
                b = a + increment 
                players[actual_player].leds = str(b) 
   
        elif (hit[1:]) == '20' and int(players[actual_player].leds) >= 20 :
                if self.double :
                        if hit[:1] == 'D' :
                                score = 4
                                saut = 2 
                        else :
                                score = 0
                                saut = 0
                elif self.triple :
                        if hit[:1] == 'T' :
                                score = 6
                                saut = 3 
                        else :
                                score = 0
                                saut = 0
                elif not self.triple and not self.double :
                        if hit[:1] == 'S' :
                                score = 1
                                saut = 1
                        elif hit[:1] == 'D' :
                                score = 2
                                saut = 2
                        elif hit[:1] == 'T' :
                                score = 3  
                                saut = 3  
                else :
                        score = 0
                        saut = 0
                
                if self.bull :
                        self.gagne = False
                else :
                        self.gagne = True
                
                increment = saut if self.saut else 1
                a = int(players[actual_player].leds)
                b = a + increment 
                players[actual_player].leds = str(b)

        else :
                score = 0
                if self.master :
                        if hit[:1] == 'S' :
                                saut = 1
                        elif hit[:1] == 'D' :
                                saut = 2
                        elif hit[:1] == 'T' :
                                saut = 3  
                        
                        a = int(players[actual_player].leds)
                        b = a - saut
                        players[actual_player].leds = str(b) 
                else :
                        self.rate += 1
                 
                if self.rate == 3 :
                        a = int(players[actual_player].leds)
                        b = a - 1 
                        players[actual_player].leds = str(b) 

        if self.bull :
                if int(players[actual_player].leds) >= 21 :
                        players[actual_player].leds = 21
                            
        handler['return_code'] = self.next
              
        players[actual_player].add_dart(actual_round, player_launch, hit, score=score)

        players[actual_player].score += score
        players[actual_player].round_points += score
        players[actual_player].points += score
        
        players[actual_player].columns[6] = (players[actual_player].leds, 'int')

        players[actual_player].columns[player_launch - 1] = (score, 'int')
        players[actual_player].columns[4] = (players[actual_player].round_points, 'int')

        players[actual_player].darts_thrown += 1
        players[actual_player].increment_hits(hit)
        self.refresh_stats(players, actual_round)
        
        if int(players[actual_player].leds) <= 0 :
                players[actual_player].alive = False
                players[actual_player].columns[5] = ('skull', 'image')

                self.winner = self.check_winner(players)
                if self.winner > -1:
                        self.infos += "Here is a winner"
                        handler['return_code'] = 3
                if len(players) == 1:
                        handler['return_code'] = 2
                
        self.player_launch = player_launch
        handler['return_code'] = self.next

        # MODIFICATION ICI : Fin immédiate de la partie dès que self.gagne est True
        if self.gagne == True:
                winner = self.best_score(players)
                if winner >= 0:
                        self.winner = winner
                        handler['return_code'] = 3
                else:
                        self.winner = actual_player
                        handler['return_code'] = 3
        elif player_launch == self.nb_darts and actual_round >= self.max_round \
                and actual_player == len(players) - 1:
                winner = self.best_score(players)
                if winner >= 0:
                        self.winner = winner
                        handler['return_code'] = 3
                else:
                        handler['return_code'] = 2

        handler['take_shot'] = self.time_to_take_shot_or_video(hit)

        return handler

    def early_player_button(self, players, actual_player, actual_round):
        
        if self.master and self.repetition :
                if self.player_launch == 0 :
                        a = int(players[actual_player].leds)
                        b = a - 3
                        players[actual_player].leds = str(b)
                        players[actual_player].columns[6] = (players[actual_player].leds, 'int') 
                        self.repetition = False
                elif self.player_launch == 1 :
                        a = int(players[actual_player].leds)
                        b = a - 2
                        players[actual_player].leds = str(b) 
                        players[actual_player].columns[6] = (players[actual_player].leds, 'int')
                        self.repetition = False
                elif self.player_launch == 2 :
                        a = int(players[actual_player].leds)
                        b = a - 1 
                        players[actual_player].leds = str(b) 
                        players[actual_player].columns[6] = (players[actual_player].leds, 'int')
                        self.repetition = False
        if not self.master and self.repetition :
                if self.rate == 2 or self.rate == 1 :
                        a = int(players[actual_player].leds)
                        b = a - 1 
                        players[actual_player].leds = str(b)
                        players[actual_player].columns[6] = (players[actual_player].leds, 'int') 
                        self.repetition = False
                
        return 1
                                
    def post_round_check(self, players, actual_round, actual_player):
        """
        Post round checks
        When PLAYER BUTTON is pressed on last round of last player
        """
        if actual_round >= int(self.max_round) and actual_player == len(players) - 1:
            return self.best_score(players)
        return -2


    def check_winner(self, players, last_round=False):
        """
        Last round (or not) : who is the winner ?
        Last alive player
        or
        best score at last round
        """
        nb_alive = 0
        last_alive = -1
        for player in players:
            if player.alive:
                nb_alive += 1
                last_alive = player.ident

        if nb_alive == 1:
            return last_alive
        if not last_round:
            return -1

        deuce = False
        best_score = -1
        best_player = -1
        for player in players:
            if player.score > best_score:
                best_score = player.score
                deuce = False 
                best_player = player.ident
            elif player.score == best_score:
                deuce = True
                best_player = -1

        return best_player

    def miss_button(self, players, actual_player, actual_round, player_launch):
        '''
        Miss button
        '''
        players[actual_player].columns[player_launch-1] = ('MISS', 'str')
        players[actual_player].darts_thrown += 1
        self.rate += 1
        if self.rate == 3 :
                a = int(players[actual_player].leds)
                b = a - 1 
                players[actual_player].leds = str(b)
                players[actual_player].columns[6] = (players[actual_player].leds, 'int')  
     
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
