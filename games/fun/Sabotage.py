# -*- coding: utf-8 -*-
# Game by ... LaDite - 
########
import random
from include import cplayer
from include import cgame
#### TROPHEES
from include import ctrophies

############
# Game Variables
############

OPTIONS = {'theme': 'default', 'max_round': 8, 'simple50' : False, 'alea' : False, 'flch3' : False}
GAME_RECORDS = {'Points Per Round': 'DESC', 'Points Per Dart': 'DESC'}
NB_DARTS = 3  # Total darts the player has to play
LOGO = 'Sabotage.png'
HEADERS = ['D1', 'D2', 'D3', '', 'Round', '', '-ADVS'] # Columns headers - Must be a string
VERSION = '1.00'

def check_players_allowed(nb_players):
    """
    Check if number of players is ok according to options
    """
    return nb_players >= 2 and nb_players <= 12, VERSION, 12
    
class CPlayerExtended(cplayer.Player):
    '''
    Exetended player class
    '''
    def __init__(self, ident, config):
        super(CPlayerExtended, self).__init__(ident, config)
        # Extend the basic players property with your own here
        # Init Player Records to zero
        for record in GAME_RECORDS:
            self.stats[record] = '0'

class Game(cgame.Game):
    '''
    Sabotage game class
    '''
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

        if self.simple:
            self.score_map.update({'SB': 50})
        else:
            self.score_map.update({'SB': 25})

        self.alea = options['alea']
        self.flch3 = options['flch3']
        self.winner = None
        self.dart = 0
        self.moyenne = 0
        self.translate = self.display.lang.translate
        self.game_ended = False  # Verrou pour empêcher le double comptage des stats/victoires
  
  
    ##############
    # PNJ SCORE METHOD FOR SABOTAGE
    ###############
    def pnj_score(self, players, actual_player, level, player_launch):
        """
        Intelligence Artificielle (PNJ) pour le jeu Sabotage :
        - Répartition humaine et réaliste des pourcentages pour S, D, T et Bull (SB/DB).
        - Cibles variées entre 10 et 20, avec des tentatives de Bull occasionnelles selon le niveau.
        - Gère les 5 niveaux de difficulté avec la matrice des voisins physiques et les miss.
        """
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende des niveaux : [p_exact, p_neighbor, p_miss]
        #   * p_exact    : Probabilité de toucher exactement la cible visée (%)
        #   * p_neighbor : Probabilité de dévier vers un secteur voisin physique (%)
        #   * p_miss     : Probabilité de rater complètement (retourne 'MISS') (%)
        # - Ajustement : Pour renforcer l'IA, augmente p_exact et réduis p_miss.
        # =========================================================================

        # Table de précision par niveau : [ % Exact, % Voisin, % Miss ]
        levels = [
            [15, 45, 40],  # Niveau 1 (Noob) : 15% exact, 45% voisin, 40% miss
            [30, 50, 20],  # Niveau 2 (Débutant) : 30% exact, 50% voisin, 20% miss
            [50, 40, 10],  # Niveau 3 (Intermédiaire) : 50% exact, 40% voisin, 10% miss
            [72, 23,  5],  # Niveau 4 (Pro) : 72% exact, 23% voisin, 5% miss
            [90, 10,  0]   # Niveau 5 (Expert) : 90% exact, 10% voisin, 0% miss
        ]

        try:
            comp_lvl = int(level)
        except (ValueError, TypeError):
            comp_lvl = 3

        lvl_idx = max(0, min(comp_lvl - 1, len(levels) - 1))
        p_exact = levels[lvl_idx][0]
        p_neighbor = levels[lvl_idx][1]

        # 1. Répartition réaliste des pourcentages (S, D, T, Bull) selon le niveau de l'IA
        if comp_lvl == 1:
            choice_pool = ['S', 'D']
            weights = [90, 10]
        elif comp_lvl == 2:
            choice_pool = ['S', 'D', 'T', 'BULL']
            weights = [78, 15, 5, 2]
        elif comp_lvl == 3:
            choice_pool = ['S', 'D', 'T', 'BULL']
            weights = [60, 22, 15, 3]
        elif comp_lvl == 4:
            choice_pool = ['S', 'D', 'T', 'BULL']
            weights = [40, 25, 28, 7]
        else:
            choice_pool = ['S', 'D', 'T', 'BULL']
            weights = [30, 25, 35, 10]

        target_type = random.choices(choice_pool, weights=weights, k=1)[0]

        # 2. Gestion si l'IA choisit de viser le Bull
        if target_type == 'BULL':
            intended_bull = 'DB' if comp_lvl >= 4 and random.randint(1, 100) <= 50 else 'SB'
            
            roll = random.randint(1, 100)
            if roll <= p_exact:
                return intended_bull
            elif roll <= p_exact + p_neighbor:
                return 'SB' if intended_bull == 'DB' else 'MISS'
            else:
                return 'MISS'

        # 3. Si l'IA vise un segment standard (entre 10 et 20)
        mult = target_type
        
        segments_pool = list(range(10, 21))
        if comp_lvl >= 4:
            seg_weights = [1, 1, 2, 2, 3, 3, 4, 5, 10, 15, 25]
        elif comp_lvl == 3:
            seg_weights = [2, 2, 3, 3, 4, 4, 5, 6, 8, 10, 12]
        else:
            seg_weights = [4, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8]

        base_val = random.choices(segments_pool, weights=seg_weights, k=1)[0]

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
      
    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        '''
        Actions done before each dart throw - for example, check if the player is allowed to play
        '''
        return_code = 0

        if player_launch == 1:
            players[actual_player].reset_darts()

        # Set score at startup
        if actual_round == 1 and player_launch == 1 and actual_player == 0:
            try:
                self.check_handicap(players)
            except Exception as exception:
                self.logs.error(f'Handicap failed : {exception}')

            for player in players:
                player.score = 0

        # Each new player
        if player_launch == 1:
            players[actual_player].round_points = 0
            players[actual_player].pre_play_score = players[actual_player].score

            players[actual_player].columns = []
            for i in range(0, 7):
                players[actual_player].columns.append(['', 'int'])
            if actual_round == 1 and actual_player == 0:
                for player in players:
                    player.reset_rounds(self.max_round)
            self.moyenne = 0

        for i in range(player_launch - 1, self.nb_darts):
            players[actual_player].columns[i] = ('', 'int')

        self.logs.debug(self.infos)
        return return_code

    def best_score(self, players):
        '''
        Find the winner
        Only one player with best score
        '''
        best_player = None
        best_score = None
        best_count = 0
        for player in players:
            if best_score is None or player.score > best_score:
                best_score = player.score
                best_player = player.ident
                best_count = 1
                self.logs.debug(\
                        f'Best found : {best_score} / Count={best_count} / player = {best_player}')
            elif player.score == best_score:
                best_count += 1

        self.logs.debug(\
                f'Best score : {best_score} / Count={best_count} / Player = {best_player}')

        if best_count == 1:
            return best_player
        return -1

    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        '''
        Function run after each dart throw - for example, add points to player
        '''

        handler = self.init_handler()
        handler['show'] = (players[actual_player].darts, hit, True)
        self.display.sound_for_touch(hit)

        score = self.score_map[hit]
        
        players[actual_player].add_dart(actual_round, player_launch, hit, score=score)
        
        players[actual_player].score += score
        players[actual_player].round_points += score
        players[actual_player].points += score

        # TROPHEES
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)
        
        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)


        if self.flch3 :
                self.moyenne = int(round(players[actual_player].round_points / 3))
        elif not self.flch3 :
                if player_launch == 3 :
                        self.moyenne = self.score_map[hit]
                else : 
                        self.moyenne = 0
                
        players[actual_player].columns[4] = (players[actual_player].round_points, 'int')
        players[actual_player].columns[player_launch - 1] = (score, 'int')
        players[actual_player].columns[6] = (self.moyenne, 'int')
                
        if player_launch == 3 and not self.alea :
                for player in players :
                        if player.ident != actual_player :
                                handler['sound'] = 'sabotage_hahaha'
                                player.score = player.score - self.moyenne
                                
        elif player_launch == 3 and self.alea :
                index_joueur = []
                for player in players :
                        if player.ident != players[actual_player].ident :
                                index_joueur.append(player.ident)
      
                choix_joueur = random.choice(index_joueur)  
                for player in players :
                        if player.ident == choix_joueur :
                                name = player.name
             
                for player in players :
                        if player.ident == choix_joueur :
                                player.score = player.score - self.moyenne

                self.display.message([
                    f"{name} : {self.translate('Sabotage-penalite')}"], 1000, None, 'middle', 'big') 
                handler['sound'] = 'sabotage_hahaha'

        players[actual_player].darts_thrown += 1
        players[actual_player].increment_hits(hit)
        self.refresh_stats(players, actual_round)

        # Check for end of game (no more rounds to play)
        if player_launch == self.nb_darts and actual_round >= self.max_round \
                and actual_player == len(players) - 1:
            winner = self.best_score(players)
            if winner > 0:
                self.winner = winner
                if not self.game_ended:
                    self.game_ended = True
                    winning_player = players[self.winner]
                    ctrophies.check_game_end_stats(players, winning_player, "SABOTAGE")
            
                handler['return_code'] = 3
            else:
                handler['return_code'] = 2

        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        return handler

    def miss_button(self, players, actual_player, actual_round, player_launch):
        '''
        Miss button
        '''
        print('miss')
        players[actual_player].columns[6] = (self.moyenne, 'int')
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

    def early_player_button(self, players, actual_player, actual_round):
        '''
        Function launched when the put player button before having launched all his darts
        '''
        handler = self.init_handler()
        return_code = 1

        if self.moyenne > 0:
            if not self.alea :
                for player in players :
                    if player.ident != actual_player :
                        player.score = player.score - self.moyenne
            elif self.alea :
                index_joueur = []
                for player in players :
                        if player.ident != players[actual_player].ident :
                                index_joueur.append(player.ident)
      
                choix_joueur = random.choice(index_joueur)  
                for player in players :
                        if player.ident == choix_joueur :
                                name = player.name
                                        
                for player in players :
                        if player.ident == choix_joueur :
                                player.score = player.score - self.moyenne
            
                self.display.message([
                    f"{name} : {self.translate('Sabotage-penalite')}"], 1000, None, 'middle', 'big')            
            handler['sound'] = 'sabotage_hahaha'
        return handler

    def post_round_check(self, players, actual_round, actual_player):
        '''
        Post round checks
        When PLAYER BUTTON is pressed on last round of last player
        '''
        if actual_round >= self.max_round and actual_player == len(players) - 1:
            winner = self.best_score(players)
            if winner != -1:
                self.winner = winner
                if not self.game_ended:
                    self.game_ended = True
                    winning_player = players[winner] if isinstance(winner, int) and 0 <= winner < len(players) else next((p for p in players if p.ident == winner), players[0])
                    ctrophies.check_game_end_stats(players, winning_player, "SABOTAGE")
                return self.winner
            else:
                return self.best_score(players)
        return -2

    def check_winner(self, players):
        nb_winner = 0
        winner = None
        for i in range(0, len(players)):
            if players[i].alive:
                winner = i
                nb_winner += 1

        if nb_winner == 1:
            return winner
        return None

    def get_score(self, player):
        '''
        Return score of player
        '''
        return player.score

    def next_set_order(self, players):
        '''
        Sort players for next set
        '''
        players.sort(key=self.get_score)

    def refresh_stats(self, players, actual_round):
        '''
        refresh players' stats
        '''
        for player in players:
            player.stats['Points Per Round'] = player.show_ppr()
            player.stats['Points Per Dart'] = player.show_ppd()
