# -*- coding: utf-8 -*-
'''
Game by Diego : Killer
'''

import random
import time
from include import cplayer
from include import cgame

LOGO = 'Killer.png'
HEADERS = ['Hom', 'Hit', 'Kil', '-', 'D1', 'D2', 'D3']
OPTIONS = {'theme': 'default', 'max_round': 100, 'vie': 0, 'killer': 5, 'bulls': False, 'max': False, 'random': True, 'suicide': False}
NB_DARTS = 3
GAME_RECORDS = {'Score': 'DESC', 'Points Per Round': 'DESC', 'Points de Hit': 'DESC'}
VERSION = '1.00'

def check_players_allowed(nb_players):
    """
    Check if number of players is ok according to options
    """
    return nb_players >= 2 and nb_players <= 12, VERSION, 12
    
class CPlayerExtended(cplayer.Player):
    '''
    Extended player class
    '''
    def __init__(self, ident, nb_columns, interior=False):
        super().__init__(ident, nb_columns, interior)
        self.target = 21
        self.killer = False
        #self.score = int(options['vie'])
        self.alive = True
        # Init Player Records to zero
        for record in GAME_RECORDS:
            self.stats[record] = '0'

class Game(cgame.Game):
    '''
    Killer game class
    '''
    def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
        super().__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)
        # For rpi
        self.rpi = rpi
        self.logo = LOGO
        self.headers = HEADERS
        self.nb_darts = NB_DARTS
        self.options = options
        self.nb_players = nb_players
        # records is the dictionnary of stats (see above)
        self.game_records = GAME_RECORDS
        #  Get the maxiumum round number
        self.max_round = int(options['max_round'])
        self.random = options['random']
        
        self.vies = int(options['vie'])
        self.killer = int(options['killer'])
        self.bulls = options['bulls']
        self.max = options['max']
        # Lose points on a wrong hit (own segment as killer, opponent's segment otherwise)
        self.suicide = options.get('suicide', False)

        self.infos = ''
        self.winner = None
        
        self.hit = 0

    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        '''
        Post dart method
        '''
        self.infos = ""
        handler = self.init_handler()

        to_add, value = self.split_key(hit, True)
        to_play = None

        index = 0
        for player in players:
            # Un joueur est touché
            #if not self.bulls :
            if str(value) == player.target and player.alive :

                if index == actual_player:
                    if player.killer:
                        if self.suicide:
                            player.score -= to_add
                    else:
                        player.score += to_add
                        if self.max :
                            if player.score >= int(self.killer) :
                                player.score = int(self.killer)
                        to_play = hit
                elif players[actual_player].killer:
                    player.score -= to_add
                    to_play = 'gunshotsimple'
                    self.hit = int(to_add)
                    players[actual_player].hit += self.hit
                    players[actual_player].columns[1] = (players[actual_player].hit , 'int')
                    players[actual_player].columns[player_launch +3] = (f'{hit}', 'str')
                elif to_play is None:
                    to_play = 'whatamess'
                    if self.suicide:
                        players[actual_player].score -= to_add
                
            index += 1
        
        index = 0
        for player in players:   
            if self.bulls :
                if str(value) == 'B' and player.alive :
                    if index == actual_player:
                        player.score += to_add
                        if self.max :
                            if player.score >= int(self.killer) :
                                player.score = int(self.killer)
                        to_play = hit
                    elif players[actual_player].killer:
                        player.score -= to_add
                        to_play = 'gunshotsimple'
                        self.hit = int(to_add)
                        players[actual_player].hit += self.hit
                        players[actual_player].columns[1] = (players[actual_player].hit , 'int')
                        players[actual_player].columns[player_launch +3] = (f'{hit}', 'str')
                index += 1
  
        index = 0
        for player in players:
            if player.score >= self.killer and not player.killer:
                if index == actual_player:
                    to_play = 'yiha'
            elif player.score < 0 and player.alive:
                if to_play == 'gunshotsimple':
                    self.display.play_sound('gunshotsimple')
                to_play = 'harmonica'
            elif player.killer and player.score < self.killer:
                to_play = 'gunshotsimple'  ###'divise2categories'

            if player.score >= self.killer:
                player.killer = True
                player.columns[2] = ('killer_santiag', 'image')
            elif player.score < 0:
                player.killer = False
                player.alive = False
                player.columns[2] = ('killer_skull', 'image')
            else:
                player.killer = False
                player.alive = True
                player.columns[2] = ('', 'txt')
                players[actual_player].columns[player_launch +3] = (f'{hit}', 'str')

            index += 1

        if to_play == hit:
            handler['sound'] = hit
        else:
            handler['sound'] = to_play

        # Check if there is a winner (last player alive)
        self.winner = self.check_winner(players, self.nb_players)
        if self.winner is not None:
            # If the function check_winner returns the id of a winner
            self.display.play_sound('harmonica')
            handler['return_code'] = 3 # Tell the main loop there is a winner
        elif not any(player.alive for player in players):
            # Everybody is dead : nobody can play anymore
            self.infos += f"Nobody left alive{self.lf}"
            handler['return_code'] = 2

        # Check last round
        if actual_round >= self.max_round and actual_player == self.nb_players - 1 \
                and (player_launch == int(self.nb_darts) or handler['return_code'] == 1):
            self.infos += f"Last round reached ({actual_round}){self.lf}"
            handler['return_code'] = 2

        # Refresh stats - in any case, points equals to "score"
        players[actual_player].points = players[actual_player].score
        self.refresh_stats(players, actual_round)

        self.logs.debug(self.infos)

        # Time for shot or video ?
        handler['take_shot'] = self.time_to_take_shot_or_video(hit)

        return handler


    def pnj_score(self, players, actual_player, computerLevel, player_launch):
        '''
        IA réaliste pour Killer : gère intelligemment la cible du joueur (si non Killer) 
        ou la cible des adversaires (si Killer), tout en respectant la matrice et le niveau.
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

        # 1. Test du MISS pur
        if random.randrange(100) < miss_rate:
            players[actual_player].columns[player_launch + 3] = ('MISS', 'str')
            self.display.play_sound('miss')
            players[actual_player].darts_thrown += 1
            return 'MISSDART'

        current_player_obj = players[actual_player]
        target_num = 20
        mult = 'S'

        # 2. Détermination de la cible selon l'état du PNJ (Killer ou non)
        if not current_player_obj.killer:
            # Pas encore Killer : il vise en priorité son propre nombre pour marquer des points
            try:
                target_num = int(current_player_obj.target)
            except (ValueError, TypeError):
                target_num = 20
            # S'il cherche à monter ses points, il peut viser des Simples, ou tenter quelques Doubles/Triples selon son niveau
            mult = random.choices(['S', 'D', 'T'], weights=[70, 20, 10], k=1)[0]
        else:
            # Déjà Killer : il choisit de viser un adversaire encore en vie pour lui baisser son score
            alive_adversaries = [p for i, p in enumerate(players) if p.alive and i != actual_player]
            if alive_adversaries:
                target_adv = random.choice(alive_adversaries)
                try:
                    target_num = int(target_adv.target)
                except (ValueError, TypeError):
                    target_num = 20
                # En tant que Killer, il cherche à faire mal (préfère les Simples solides ou Doubles)
                mult = random.choices(['S', 'D'], weights=[60, 40], k=1)[0]
            else:
                try:
                    target_num = int(current_player_obj.target)
                except (ValueError, TypeError):
                    target_num = 20
                mult = 'S'

        # 3. Simulation de la déviation réaliste basée sur la matrice physique
        if random.randrange(100) < slip_rate:
            if mult in ['D', 'T']:
                if random.randrange(100) < 60:
                    mult = 'S'  # Glisse du double/triple vers le simple du même numéro
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
        Executed before every dart throw
        '''

        # If player is dead - he can't play
        if not players[actual_player].alive:
            self.rpi.set_target_leds('')
            return 4

        # First launch - Display Go msg and save backupturn
        if player_launch == 1:
            #backup score each round
            self.save_turn(players)
        #on affiche les cases au 1er tour
        if player_launch == 1 and actual_player == 0 and actual_round == 1:
            for player in players:
                player.hit = 0
                player.score = self.vies
                
            if not self.random_from_net:
                self.set_target(players, self.nb_players)

            #time.sleep(7)
            couleur = 0
            for player in players:
                player.columns[0] = (player.target, 'int', 'game-red')
                player.columns[1] = (self.hit, 'int')
                couleur += 1 
        
        ### if player_launch
        if player_launch == 1 :
            players[actual_player].columns[4] = ('', 'str')
            players[actual_player].columns[5] = ('', 'str')
            players[actual_player].columns[6] = ('', 'str')
                
        ### pour option random
        if player_launch == 1 and self.random :
            targets = []
            index2 = random.randint(1, 20)
            for index in range(0, self.nb_players):
                while index2 in targets:
                    index2 = random.randint(1, 20)
                targets.append(index2)

            targets = sorted(targets)
            for index in range(0, self.nb_players):
                players[index].target = str(targets[index])
                self.infos += f"Goal for player {index} is {players[index].target}{self.lf}"
            
            for player in players:
                player.columns[0] = (player.target, 'int', 'game-red')
                
        leds = []
        if not players[actual_player].killer:
            # Segment to touch
            index = 0
            for player in players:
                if not player.alive:
                    pass
                elif index == actual_player:
                    leds.extend([f'{mult}{player.target}#{self.colors[0]}' for mult in ['S', 'D', 'T']])
                else:
                    leds.extend([f'{mult}{player.target}#{self.colors[1]}' for mult in ['S', 'D', 'T']])
                index += 1
        else:
            # Segment to avoid
            index = 0
            for player in players:
                if not player.alive:
                    pass
                elif index == actual_player:
                    leds.extend([f'{mult}{player.target}#{self.colors[1]}' for mult in ['S', 'D', 'T']])
                else:
                    leds.extend([f'{mult}{player.target}#{self.colors[0]}' for mult in ['S', 'D', 'T']])
                index += 1
        

        self.rpi.set_target_leds('|'.join(leds))
        
        # Check if there is a winner (only on last dart thrown, except if winner is current player)
        self.winner = self.check_winner(players, self.nb_players)
        
        return 0

    def set_target(self, players, nb_players):
        '''
        Randomize goal for players
        '''
        targets = []
        index2 = random.randint(1, 20)
        for index in range(0, nb_players):
            while index2 in targets:
                index2 = random.randint(1, 20)
            targets.append(index2)

        targets = sorted(targets)
        for index in range(0, nb_players):
            players[index].target = str(targets[index])
            self.infos += f"Goal for player {index} is {players[index].target}{self.lf}"

    def check_winner(self, players, nb_players):
        '''
        Check if there is a winner
        '''
        # The winner is the last player alive, killer or not (the others may have killed themselves)
        alive = [player.ident for player in players if player.alive]
        winner = alive[0] if len(alive) == 1 else None

        if winner is not None:
            self.infos += f"Player {winner} wins !{self.lf}"
            return winner
        else:
            self.infos += "Still no winner ...\n"
            return None

    def refresh_stats(self, players, actual_round):
        '''
        Method to frefresh player.stat - Adapt to the stats you want.
        They represent mathematical formulas used to calculate stats. Refreshed after every launch
        '''
        for player in players:
            player.stats['Score'] = player.score
            player.stats['Points Per Round'] = player.show_ppr()
            player.stats['Points de HIT'] = player.hit

    def get_random(self, players, actual_round, actual_player, player_launch):
        '''
        Returns and Random things, to send to clients in case of a network game
        '''
        if actual_round == 1 and actual_player == 0 and player_launch == 1:
            myrand = []
            for player in players:
                myrand.append(player.camembert)
        else:
            myrand = None # Means that there is no random
        return myrand

    def miss_button(self, players, actual_player, actual_round, player_launch):
        '''
        Miss button
        '''
        print('miss')
        #players[actual_player].columns[6] = (self.moyenne, 'int')
        players[actual_player].columns[player_launch+3] = ('MISS', 'str')
        self.display.play_sound('miss')
        players[actual_player].darts_thrown += 1

    def set_random(self, players, actual_round, actual_player, player_launch, data):
        '''
        Set Random things, while received by master in case of a network game
        '''
        if actual_round == 1 and actual_player == 0 and player_launch == 1 and data is not None:
            for player in players:
                player.target = str(data[player.ident])
        self.random_from_net = True
