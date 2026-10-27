# -*- coding: utf-8 -*-
# Game by ... laDite!
########
import random
from include import cplayer
from include import cgame
#

############
# Game Variables
############
VERSION = '1.00'
OPTIONS = {'theme': 'default', 'win': 6, 'simple50': False}
GAME_RECORDS = {'Points Per Round': 'DESC', 'Points Per Dart': 'DESC'}
NB_DARTS = 3  # Total darts the player has to play
LOGO = 'Ping-Pong.png'
HEADERS = ['D1', 'D2', 'D3', '', 'Rnd', '', ''] # Columns headers - Must be a string

def check_players_allowed(nb_players):
    """
    Check if number of players is ok according to options
    """
    return nb_players >= 2 and nb_players <= 12, VERSION, 12
 

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
        #self.multiplicateur = 1 

class Game(cgame.Game):
    """
    PingPong game class
    """
    def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
        super().__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)
        self.game_records = GAME_RECORDS
        self.nb_darts = NB_DARTS
        self.logo = LOGO
        self.headers = HEADERS
        self.options = options
        #  Get the maximum round number
        self.max_round = 99
        self.simple = options['simple50']
       
        self.winscore = options['win']
        
        if self.simple:
            self.score_map.update({'SB': 50})
        else:
            self.score_map.update({'SB': 25})

        self.winner = None

        self.video_player = video_player

        self.points = 0
        self.test_win = False
  
    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        """
        Actions done before each dart throw - for example, check if the player is allowed to play
        """
        return_code = 0
                  
        if player_launch == 1:
            players[actual_player].reset_darts()
            self.points = 0
            

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
        

        # Check winner
        self.check_winner(players, actual_player)
        
        if self.winner is not None:
            return_code = 3

        # Print debug output
        self.logs.debug(self.infos)
        return return_code

    def pnj_score(self, players, actual_player, computer_level, player_launch):
        """
        Intelligence Artificielle (PNJ) pour le jeu Ping-Pong :
        - Plafonne l'ambition des scores (ex: ~60 max en intermédiaire) pour éviter des scores irréalistes.
        - Intègre la précision par niveau, les chiffres voisins, les MISS purs et l'analyse des adversaires.
        """
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende du format par niveau [p_exact, p_neighbor, p_miss] :
        #   * p_exact    : Probabilité de toucher la cible exacte (%)
        #   * p_neighbor : Probabilité de toucher un secteur voisin géométrique (%)
        #   * p_miss     : Probabilité d'un raté complet / MISS pur (%)
        # - Ajustement : Pour renforcer l'IA, augmente p_exact et réduis p_miss.
        # =========================================================================

        dartboard_order = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5]

        # 1. Analyse des scores des autres joueurs sur la volée en cours
        max_opponent_score = 0
        has_opponents_played = False
        
        for i, p in enumerate(players):
            if i != actual_player:
                try:
                    score_val = p.columns[4][0]
                    if isinstance(score_val, int):
                        has_opponents_played = True
                        if score_val > max_opponent_score:
                            max_opponent_score = score_val
                except (IndexError, TypeError, ValueError):
                    pass

        # Niveaux de difficulté : [Chance cible exacte, Chance chiffre voisin, Chance miss pur]
        levels = [
            [20, 45, 35],  # Niveau 1 : Noob (20% exact, 45% voisin, 35% miss)
            [35, 45, 20],  # Niveau 2 : Débutant (35% exact, 45% voisin, 20% miss)
            [55, 35, 10],  # Niveau 3 : Intermédiaire (55% exact, 35% voisin, 10% miss - Moyenne visée ~60 pts)
            [75, 20,  5],  # Niveau 4 : Pro (75% exact, 20% voisin, 5% miss)
            [90, 10,  0]   # Niveau 5 : Expert (90% exact, 10% voisin, 0% miss)
        ]

        try:
            comp_lvl = int(computer_level)
        except (ValueError, TypeError):
            comp_lvl = 3

        lvl_idx = max(0, min(comp_lvl - 1, len(levels) - 1))
        p_exact = levels[lvl_idx][0]
        p_neighbor = levels[lvl_idx][1]
        p_miss = levels[lvl_idx][2]

        # 2. Stratégie de ciblage équilibrée (pour tourner autour de ~60 max en Intermédiaire/Niveau 3)
        if not has_opponents_played or (player_launch == 1 and not has_opponents_played):
            # Premier joueur : cible des scores corrects sans excès
            target_value = random.choice([20, 19, 18, 16, 15])
            # Moins de triples automatiques pour modérer la moyenne
            multi = random.choice(['T', 'D', 'S', 'S']) if comp_lvl >= 4 else random.choice(['D', 'S', 'S', 'S'])
            bull_chance = 5
        else:
            high_pression = max_opponent_score >= 50
            is_under_pression = max_opponent_score >= 35

            if high_pression:
                # S'adapte si l'adversaire fait un très gros score
                target_value = random.choice([20, 19, 18, 20])
                multi = random.choice(['T', 'D', 'S']) if comp_lvl >= 3 else random.choice(['D', 'S'])
                bull_chance = 15
            elif is_under_pression:
                target_value = random.choice([20, 19, 18, 17])
                multi = random.choice(['D', 'S', 'S'])
                bull_chance = 8
            else:
                target_value = random.randint(1, 20)
                rand_multi = random.randrange(100)
                if comp_lvl >= 4 and rand_multi < 25:
                    multi = 'T'
                elif comp_lvl >= 2 and rand_multi < 60:
                    multi = 'S'
                else:
                    multi = random.choice(['S', 'D'])
                bull_chance = 3

        # Tentative de Bull modérée
        if random.randrange(100) < bull_chance:
            return 'SB' if comp_lvl < 4 or random.randrange(100) < 70 else 'DB'

        rand_val = random.randrange(100)

        # 3. Application de la précision (Cible exacte vs Voisin vs Miss pur)
        if rand_val < p_exact:
            return f"{multi}{target_value}"

        elif rand_val < p_exact + p_neighbor:
            # Raté partiel : touche un chiffre voisin sur la cible
            if target_value in dartboard_order:
                idx = dartboard_order.index(target_value)
                left_neighbor = dartboard_order[(idx - 1) % len(dartboard_order)]
                right_neighbor = dartboard_order[(idx + 1) % len(dartboard_order)]
                neighbor_num = random.choice([left_neighbor, right_neighbor])
            else:
                neighbor_num = random.randint(1, 20)
            
            # Les voisins baissent aussi le risque (majoritairement des simples)
            neighbor_multi = 'S' if random.randrange(100) < 70 else multi
            return f"{neighbor_multi}{neighbor_num}"

        else:
            # Raté complet (MISS)
            return ''

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
        
        ### dit le chiffre touche
        self.display.sound_for_touch(hit)

        score = 0

        if hit :
                score = self.score_map[hit]
                self.points += score
                players[actual_player].columns[4] = (self.points, 'int')

        
        return_code = 0
        
        players[actual_player].add_dart(actual_round, player_launch, hit, score=score)

        #players[actual_player].score += score
        players[actual_player].round_points += score
        players[actual_player].points += score
        
        

        # Store what he played in the table
        players[actual_player].columns[player_launch - 1] = (score, 'int')
        
        # Record total dart thrown, total hits (S=1, D=2, T=3) and refresh players stats
        players[actual_player].darts_thrown += 1
        players[actual_player].increment_hits(hit)
        self.refresh_stats(players, actual_round)

   
        # Check last round
        if actual_round >= self.max_round and actual_player == self.nb_players - 1 \
                and (player_launch == self.nb_darts or return_code == 1)  :
            self.infos += f"Last round reached ({actual_round}){self.lf}"
            return_code = 2
            
        # Check winner
        self.check_winner(players, actual_player)
        if self.winner is not None:
            return_code = 3

        self.logs.debug(self.infos)
        
        # Time for shot or video ?
        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        handler['return_code'] = return_code
        return handler
        
        #return return_code

       

            
    def early_player_button(self, players, actual_player, actual_round):
        print('early - nextplayer presse')
        
                
        return 1

    def post_round_check(self, players, actual_round, actual_player):
        """
        Post round checks
        When PLAYER BUTTON is pressed on last round of last player
        """
        print('post round check')
        self.calcul(players, actual_player)
        #self.check_winner(players, actual_player)      
        
        if actual_round >= self.max_round and actual_player == len(players) - 1 or self.test_win :
            # Last round, last player
            return self.best_score(players)
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
            player.stats['Points Per Round'] = player.show_ppr()
            player.stats['Points Per Dart'] = player.show_ppd()

    def miss_button(self, players, actual_player, actual_round, player_launch):
        """
        EMPTY
        """  
        print('miss boutton - pass')
        players[actual_player].columns[player_launch-1] = ('MISS', 'str')
        self.display.play_sound('miss')
        #self.points = 0
        players[actual_player].columns[4] = (self.points, 'int')
        players[actual_player].darts_thrown += 1
        pass

    def display_segment(self):
       """
       Set if a message is shown to indicate the segment hitted !
       """
       return False

    def calcul(self, players, actual_player) :
        print('def calcul')
        liste_score = []
        if players[actual_player].ident == self.nb_players -1 :
                for player in players :
                        ### creation de la liste des scores (recuperation du score dans la colonne 4 et de l ident du joueur)
                        liste_score.extend([[player.columns[4][0],player.ident]]) 

                score_trie=sorted(liste_score)
                print('liste des scores tries')
                print(score_trie)

                #### attribution des points
                ## meilleur score = 1 point (si egalite, 1 points pour chaque joueur)
                ## 2eme et reste = 0 points
                if score_trie[-1][0] == 0 :
                        points = 0
                else :
                        points = 1	
       
                score_acquis=[]
                for i in range(-1, -len(score_trie)-1, -1) :
                        if points > 0 and i < -1  and score_trie[i][0] != score_trie[i+1][0]:
                                if score_trie[i][0] == 0 :
                                        points = 0
                                else :
                                        points -= 1
                              
                        score_acquis.append((points, score_trie[i][1]))

                print('resultat points')
                print(score_acquis)

                ### ajoute les points au score des joueurs
                for i in range(self.nb_players) :
                        for k, v in enumerate(score_acquis):
                                if v[1] == i :
                                        for player in players :
                                                if player.ident == i :
                                                        player.score += v[0]    
                
                score_joueur = []
                for player in players :
                       score_joueur.append([player.score, player.ident])
                score_joueur = sorted(score_joueur)

                print('score_joueur')
                print(score_joueur)

		
                ### determine le gagnant
                if int(score_joueur[-1][0]) >= int(self.winscore) and score_joueur[-2][0] <= int(score_joueur[-1][0])-2 :
                        print('winner')
                        winner = score_joueur[-1][1]
                        print(winner)
                        self.test_win = True
                        self.winner = score_joueur[-1][1]
                        self.check_winner(players, actual_player)        
                else :
                        print('pas de gagnant, le jeu continue')

        return 1
        
    def check_winner(self, players, actual_player):
        '''
        Function to check winner
        '''
        print('dans checkwinner - winner')
        print(self.winner)
        if self.winner is not None:
            return 3
