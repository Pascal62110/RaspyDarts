# -*- coding: utf-8 -*-
# Game by ... you !
########
import random
from include import cplayer
from include import cgame
#

############
# Game Variables
############
OPTIONS = {'theme': 'default', 'max_round': 10, 'simple50': False, 'segment': False, 'lives': 3}
GAME_RECORDS = {'Points Per Round': 'DESC', 'Points Per Dart': 'DESC'}
NB_DARTS = 3  # Total darts the player has to play
LOGO = 'BIG 6.png'
HEADERS = ['D1', 'D2', 'D3', '', 'Rnd', '', 'Target'] # Columns headers - Must be a string
VERSION = '1.00'

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
    High score game class
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
        
        self.sudden_death = True ###options['suddendeath']
        self.lives = int(options['lives'])

        if self.sudden_death:
            self.headers[3] = 'Vies'

        if self.simple:
            self.score_map.update({'SB': 50})
        else:
            self.score_map.update({'SB': 25})
            
        self.segment = options['segment']
            
        if self.segment :
                self.targets = ['S6#green', 'D6#green', 'T6#green']
        else :
                self.targets = ['S6#green']
        
        self.check = False
        self.miss = 1
        self.nextplayer = False
        
        self.winner = None

        self.video_player = video_player
        

            
    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        """
        Actions done before each dart throw - for example, check if the player is allowed to play
        """
        return_code = 0
        
        if player_launch == 1:
            players[actual_player].reset_darts()
            self.check = False
            self.miss = 1

        if not players[actual_player].alive:
            return 4

        # Set score at startup
        if actual_round == 1 and player_launch == 1 and actual_player == 0:
            try:
                self.check_handicap(players)
            except Exception as exception:
                self.logs.error(f"Handicap failed : {exception}")

            for player in players:
                player.score = 0
                player.lives = self.lives
                player.alive = True
                player.columns[3] = (player.lives, 'int')

        # Each new player
        if player_launch == 1:
            players[actual_player].round_points = 0
            players[actual_player].pre_play_score = players[actual_player].score

            players[actual_player].columns = []
            for i in range(0,7):
                players[actual_player].columns.append(['', 'int'])
            if actual_round == 1 and actual_player == 0:
                for player in players:
                    player.reset_rounds(self.max_round)

        self.rpi.set_target_leds ('')
        self.rpi.set_target_leds('|'.join(self.targets))
        
        for i in range(player_launch - 1,self.nb_darts):
            players[actual_player].columns[i] = ('', 'int')

        if self.sudden_death:
            players[actual_player].columns[3] = (players[actual_player].lives, 'int')

        if not self.check:
            raw_target = self.targets[0].split('#')[0] if self.targets and self.targets[0] else ''
            if self.segment and raw_target:
                current_target_display = "".join(filter(str.isdigit, raw_target))
            else:
                current_target_display = raw_target
        else:
            current_target_display = ''
        players[actual_player].columns[6] = (current_target_display, 'str')
            
        self.logs.debug(self.infos)
        
        return return_code

    def pnj_score(self, players, actual_player, computerLevel, player_launch):
        """
        IA stratégique Big 6 (Logique humaine) :
        - 1ère fléchette : Valide la cible en cours.
        - 2e fléchette : Vise un gros chiffre (points) en Simple.
        - 3e fléchette : Vise un gros chiffre et tente un Double ou Triple (Piège).
        """
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende : [Taux de miss pur (%), Taux de glissement / déviation (%)]
        # - Plus fort / précis : Diminuer le MISS et le taux de glissement.
        # - Plus humain / brouillon : Augmenter le MISS et le taux de glissement.
        # =========================================================================
        geo_neighbors = {
            1: [20, 18], 2: [15, 17], 3: [17, 19], 4: [18, 13], 
            5: [20, 12], 6: [13, 10], 7: [19, 16], 8: [16, 11], 
            9: [14, 12], 10: [6, 15], 11: [8, 14], 12: [9, 5], 
            13: [4, 6], 14: [11, 9], 15: [10, 2], 16: [7, 8], 
            17: [2, 3], 18: [1, 4], 19: [3, 7], 20: [1, 5]
        }

        # Niveaux : [Taux de miss pur, Taux de glissement]
        levels = [
                 [45, 80],  # 1 : Noob 
                 [30, 60],  # 2 : Débutant
                 [15, 35],  # 3 : Intermédiaire 
                 [8, 20],   # 4 : Pro 
                 [3, 10]    # 5 : Expert 
                ]

        lvl_idx = max(0, min(computerLevel - 1, len(levels) - 1))
        miss_rate = levels[lvl_idx][0]
        slip_rate = levels[lvl_idx][1]

        current_allowed = self.targets

        # CAS 1 : La cible actuelle n'est PAS encore validée (Fléchette 1)
        if not self.check:
            if random.randrange(100) < miss_rate:
                return 'MISSDART'
            
            target_num = 6
            target_mult = 'S'
            for t in current_allowed:
                clean_t = t.split('#')[0]
                if clean_t:
                    num_str = "".join(filter(str.isdigit, clean_t))
                    if num_str:
                        target_num = int(num_str)
                        if clean_t[0].upper() in ['S', 'D', 'T']:
                            target_mult = clean_t[0].upper()
                        break

            mult = target_mult
            if random.randrange(100) < slip_rate:
                if mult in ['D', 'T']:
                    mult = 'S'
                if target_num in geo_neighbors:
                    target_num = random.choice(geo_neighbors[target_num])
            return f'{mult}{target_num}'

        # CAS 2 : La cible est validée, l'IA joue ses fléchettes libres (2 et 3) pour marquer et poser un piège
        else:
            if random.randrange(100) < (miss_rate // 2):
                return 'MISSDART'

            # Fléchette 2 : Viser un gros chiffre pour marquer des points en Simple
            if player_launch == 2:
                val = random.choice([20, 19, 18, 15])
                mult = 'S'
            
            # Fléchette 3 : Tenter le coup dur (Double ou Triple sur un gros chiffre pour piéger le suivant)
            elif player_launch == 3:
                val = random.choice([20, 18, 12, 13, 16])
                trap_chance = computerLevel * 15 
                if computerLevel >= 2 and random.randrange(100) < trap_chance:
                    mult = random.choice(['D', 'T'])
                else:
                    mult = 'S'
            else:
                val = 20
                mult = 'S'

            hit_target = f'{mult}{val}'

            effective_slip = slip_rate
            if mult in ['D', 'T']:
                effective_slip += 25 

            if random.randrange(100) < effective_slip:
                if mult in ['D', 'T']:
                    mult = 'S' 
                if val in geo_neighbors:
                    val = random.choice(geo_neighbors[val])
                hit_target = f'{mult}{val}'

            return hit_target


    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        """
        Function run after each dart throw - for example, add points to player
        """

        handler = self.init_handler()

        if super().play_show(players[actual_player].darts, hit, play_special=True):
            handler['sound'] = hit

        score = 0
        
        # 1. Si on valide la toute première cible du jeu (ex: S6 initial)
        if (hit+'#green') in self.targets and not self.check :   
                score = self.score_map[hit]
                
                S = ['S1#green', 'S2#green', 'S3#green', 'S4#green', 'S5#green', 'S6#green', 'S7#green', 'S8#green', 'S9#green', 'S10#green', 'S11#green', 'S12#green', 'S13#green', 'S14#green', 'S15#green', 'S16#green', 'S17#green', 'S18#green', 'S19#green', 'S20#green']
                D = ['D1#green', 'D2#green', 'D3#green', 'D4#green', 'D5#green', 'D6#green', 'D7#green', 'D8#green', 'D9#green', 'D10#green', 'D11#green', 'D12#green', 'D13#green', 'D14#green', 'D15#green', 'D16#green', 'D17#green', 'D18#green', 'D19#green', 'D20#green']
                T = ['T1#green', 'T2#green', 'T3#green', 'T4#green', 'T5#green', 'T6#green', 'T7#green', 'T8#green', 'T9#green', 'T10#green', 'T11#green', 'T12#green', 'T13#green', 'T14#green', 'T15#green', 'T16#green', 'T17#green', 'T18#green', 'T19#green', 'T20#green']
                
                self.targets = S + D + T
                self.rpi.set_target_leds ('')
                self.rpi.set_target_leds('|'.join(self.targets))   
                self.check = True

        # 2. Une fois le jeu lancé, chaque touche valide devient LA cible pour le joueur suivant (peu importe la fléchette 1, 2 ou 3)
        if (hit) and self.check :
                if self.segment :
                        self.targets = ['s'+hit[1:]+'#green', 'S'+hit[1:]+'#green', 'D'+hit[1:]+'#green', 'T'+hit[1:]+'#green']
                else :
                        self.targets = [hit+'#green']
                
                self.rpi.set_target_leds ('')
                self.rpi.set_target_leds('|'.join(self.targets))   
                score = self.score_map[hit]
        
        self.rpi.set_target_leds ('')
        self.rpi.set_target_leds('|'.join(self.targets))       
               
        handler['return_code'] = 0

        # Si le joueur rate ses 3 fléchettes sans valider : il perd une vie et la cible revient à S6
        if player_launch == self.nb_darts and not self.check:
            players[actual_player].lives -= 1
            players[actual_player].columns[3] = (players[actual_player].lives, 'int')
            if self.segment:
                self.targets = ['S6#green', 'D6#green', 'T6#green']
            else:
                self.targets = ['S6#green']
            self.rpi.set_target_leds('')
            self.rpi.set_target_leds('|'.join(self.targets))

        if players[actual_player].lives == 0 :
            players[actual_player].alive = False 
            players[actual_player].columns[3] = ('big6_skull', 'image')

        players[actual_player].add_dart(actual_round, player_launch, hit, score=score)

        players[actual_player].score += score
        players[actual_player].round_points += score
        players[actual_player].points += score
        
        players[actual_player].columns[player_launch - 1] = (score, 'int')
        players[actual_player].columns[4] = (players[actual_player].round_points, 'int')

        if self.check:
            players[actual_player].columns[6] = ('', 'str')
        else:
            raw_target = self.targets[0].split('#')[0] if self.targets and self.targets[0] else ''
            if self.segment and raw_target:
                current_target_display = "".join(filter(str.isdigit, raw_target))
            else:
                current_target_display = raw_target
            players[actual_player].columns[6] = (current_target_display, 'str')
        
        players[actual_player].darts_thrown += 1
        players[actual_player].increment_hits(hit)
        self.refresh_stats(players, actual_round)

        if player_launch == self.nb_darts and actual_round >= self.max_round \
                and actual_player == len(players) - 1:
            winner = self.check_winner(players)
            if winner is not None:
                self.winner = winner
                handler['return_code'] = 3
            else:
                handler['return_code'] = 2
                
        handler['take_shot'] = self.time_to_take_shot_or_video(hit)

        return handler

    def early_player_button(self, players, actual_player, actual_round):
        pass
    
    def post_round_check(self, players, actual_round, actual_player):
        """
        Post round checks
        When PLAYER BUTTON is pressed on last round of last player
        """
        if self.sudden_death:
            if players[actual_player].lives == 0 :
                    players[actual_player].alive = False 
   
            winner = self.get_winner(players)
            if winner is not None:
                self.winner = winner
                self.logs.debug(f"winner is {winner}")
                return winner
        elif actual_round >= self.max_round and actual_player == len(players) - 1:
            return self.best_score(players)
        return -2

    
    def get_winner(self, players):
        nb_winner = 0
        for i in range(0, len(players)):
            if players[i].alive:
                winner = i
                nb_winner += 1

        if nb_winner == 1:
            return winner
        return None

    def get_score(self, player):
        return player.score

    def next_set_order(self, players):
        players.sort(key=self.get_score)

    def miss_button(self, players, actual_player, actual_round, player_launch):
        '''
        Miss button
        '''
        print('miss')
        players[actual_player].columns[player_launch-1] = ('MISS', 'str')
        players[actual_player].darts_thrown += 1
        
        # Si c'est la 3e fléchette et qu'il n'a pas validé, il perd une vie et la cible revient à S6
        if player_launch == self.nb_darts and not self.check:
            players[actual_player].lives -= 1
            players[actual_player].columns[3] = (players[actual_player].lives, 'int')
            if self.segment:
                self.targets = ['S6#green', 'D6#green', 'T6#green']
            else:
                self.targets = ['S6#green']
            self.rpi.set_target_leds('')
            self.rpi.set_target_leds('|'.join(self.targets))
            
            if players[actual_player].lives == 0:
                players[actual_player].alive = False 
                players[actual_player].columns[3] = ('big6_skull', 'image')

    def refresh_stats(self, players, actual_round):
        """
        refresh players' stats
        """
        for player in players:
            player.stats['Points Per Round'] = player.avg(actual_round)
            player.stats['Points Per Dart'] = player.show_ppd()
