# -*- coding: utf-8 -*-
# Game: High Score
########
import random
from include import cplayer
from include import cgame
### TROPHEES
from include import ctrophies
from include import cpaths
import json
import os

############
# Game Variables
############
OPTIONS = {'theme': 'default', 'max_round': 10, 'simple50': False, 'suddendeath': False, 'lives': 2, 'multix123': False}
GAME_RECORDS = {'Points Per Round': 'DESC', 'Points Per Dart': 'DESC'}
NB_DARTS = 3  # Total darts the player has to play
LOGO = 'High_Score.png'
HEADERS = ['D1', 'D2', 'D3', '', 'Rnd', 'PPD', 'PPR'] # Columns headers
VERSION = '1.00'




def enregistrer_fin_de_partie(nom_du_jeu, players_list, winner_name):
    data_file = cpaths.trophies_file()
    
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    nom_jeu_clean = nom_du_jeu.strip().lower().replace(" ", "_")

    for player in players_list:
        p_key = player.strip()
        if p_key not in data:
            data[p_key] = {"trophies": [], "stats": {}}
            
        stats = data[p_key].setdefault("stats", {})
        
        # Incrémentation des parties jouées
        stats["total_parties_jouees"] = stats.get("total_parties_jouees", 0) + 1
        stat_jeu_partie = f"parties_jouees_{nom_jeu_clean}"
        stats[stat_jeu_partie] = stats.get(stat_jeu_partie, 0) + 1
        
        # Boucle conditionnelle Victoire / Défaite
        if p_key.lower() == winner_name.strip().lower():
            stats["wins"] = stats.get("wins", 0) + 1
            stat_jeu_win = f"victoire_{nom_jeu_clean}"
            stats[stat_jeu_win] = stats.get(stat_jeu_win, 0) + 1
        else:
            stat_jeu_loss = f"defaite_{nom_jeu_clean}"
            stats[stat_jeu_loss] = stats.get(stat_jeu_loss, 0) + 1

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)






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
        self.simple = options['simple50']
        self.sudden_death = options['suddendeath']
        self.lives = int(options['lives'])
        self.multix123 = options['multix123']
        self.max_round = int(options['max_round'])
        
        # In order to display dead players at bottom of score's table
        self.position = nb_players
        if nb_players == 1:
            self.sudden_death = False
            
        if self.sudden_death:
            self.headers[3] = 'Vies'

        if self.simple:
            self.score_map.update({'SB': 50})
        else:
            self.score_map.update({'SB': 25})

        self.winner = None
        self.video_player = video_player
        self.calcul = False
        self.game_ended = False  # Verrou pour empêcher le double comptage des stats/victoires





    def compute_position(self, players, dead=None):
        if dead is None:
            index = 1
            for player in players:
                player.position = index
                index += 1
        else:
            for player in players:
                if player.position == dead:
                    player.position = self.position
                    self.position -= 1
                elif player.alive and player.position > dead:
                    player.position -= 1

    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        """
        Actions done before each dart throw
        """
        return_code = 0

        if player_launch == 1:
            players[actual_player].reset_darts()

        if not players[actual_player].alive:
            return 4

        # Set score at startup
        if actual_round == 1 and player_launch == 1 and actual_player == 0:
            self.compute_position(players)
            try:
                self.check_handicap(players)
            except Exception as exception:
                self.logs.error(f"Handicap failed : {exception}")

            for player in players:
                player.score = 0
                player.lives = self.lives
                player.alive = True

        # Each new player
        if player_launch == 1:
            players[actual_player].round_points = 0
            players[actual_player].pre_play_score = players[actual_player].score
            self.rpi.set_target_leds('')

            # Reset display Table
            players[actual_player].columns = []
            for i in range(0, 7):
                players[actual_player].columns.append(['', 'int'])
            if actual_round == 1 and actual_player == 0:
                for player in players:
                    player.reset_rounds(self.max_round)

        # Display avg or multix123 columns
        if actual_round == 1 and player_launch == 1:
            if not self.multix123:
                players[actual_player].columns[5] = (0.0, 'int')
                players[actual_player].columns[6] = (0.0, 'int')
            else:
                players[actual_player].columns[5] = (players[actual_player].show_ppd(), 'int')
                players[actual_player].columns[6] = (players[actual_player].show_ppr(), 'int')

        # Clean next boxes
        for i in range(player_launch - 1, self.nb_darts):
            players[actual_player].columns[i] = ('', 'int')

        if self.multix123:
            self.headers[0] = 'X1'
            self.headers[1] = 'X2'
            self.headers[2] = 'X3'
        else:
            self.headers[0] = 'D1'
            self.headers[1] = 'D2'
            self.headers[2] = 'D3'

        if self.sudden_death:
            players[actual_player].columns[3] = (players[actual_player].lives, 'int')

        self.logs.debug(self.infos)
        return return_code


    def pnj_score(self, players, actual_player, computer_level, player_launch):
        """
        Intelligence Artificielle (PNJ) pour le jeu High Score :
        - Vise les segments de la cible selon la précision du niveau.
        - Gère la dispersion géographique (voisins) en cas de raté.
        - Intègre la probabilité de viser le Bull (SB ou DB) selon les niveaux et l'option simple50.
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

        # Niveaux de précision [Chance réussite exacte, Chance voisin/alternatif, Chance raté]
        levels = [
            [20, 45, 35],  # Niveau 1 : Noob (20% exact, 45% voisin, 35% miss)
            [35, 45, 20],  # Niveau 2 : Débutant (35% exact, 45% voisin, 20% miss)
            [55, 35, 10],  # Niveau 3 : Intermédiaire (55% exact, 35% voisin, 10% miss)
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

        # Étant sur "High Score", l'IA cherche à faire un maximum de points, donc vise souvent les Triples (surtout le 20 ou le 19)
        # Chance de tenter le Bull pour les niveaux moyens/élevés
        if comp_lvl >= 3 and random.randrange(100) < (comp_lvl * 4):
            if comp_lvl >= 4 and random.randrange(100) < 50:
                return 'DB'
            return 'SB'

        # Sélection de la cible (les experts visent en priorité le 20 ou le 19)
        target_value = random.choice([20, 20, 19, 18, 20]) if comp_lvl >= 3 else random.choice([20, 19, 18, 16, 15])
        
        # Choix du multiplicateur : les IA plus fortes favorisent les Triples
        rand_multi = random.randrange(100)
        if comp_lvl >= 4 and rand_multi < 45:
            multi = 'T'
        elif comp_lvl >= 2 and rand_multi < 30:
            multi = 'D'
        else:
            multi = 'S'

        rand_val = random.randrange(100)

        if rand_val < p_exact:
            # Touche exactement ce qu'il visait
            return f"{multi}{target_value}"
        elif rand_val < p_exact + p_neighbor:
            # Raté partiel : touche un chiffre voisin sur la cible
            if target_value in dartboard_order:
                idx = dartboard_order.index(target_value)
                neighbor_num = dartboard_order[(idx + random.choice([-1, 1])) % len(dartboard_order)]
            else:
                neighbor_num = random.randint(1, 20)
            neighbor_multi = 'S' if random.randrange(100) < 60 else multi
            return f"{neighbor_multi}{neighbor_num}"
        else:
            # Raté complet (MISS) sous forme de chaîne vide (géré par miss_button ou absence de score)
            return 'MISS'


    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        """
        Function run after each dart throw
        """
        handler = self.init_handler()
        
        # À la ligne 300, remplacez print(vars(players)) par :
        print('AFFICHAGE DES RECORD DU JOUEUR')
        for player in players:
            print(f"\nJoueur : {player.name}")
            
            # Boucle sur chaque record/statistique configuré pour le jeu
            for record in self.game_records:
                # Vérifie si le record existe dans le dictionnaire stats du joueur pour éviter une erreur
                if record in player.stats:
                    print(f"  - {record} : {player.stats[record]}")
                else:
                    print(f"  - {record} : Non disponible")
                    

        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)
        
               
        
        
        handler['show'] = (players[actual_player].darts, hit, True)
        handler['sound'] = hit
        

        if hit == 'SB' or hit == 'DB' and self.multix123:
            score = self.score_map[hit]
            self.calcul = True

        if self.multix123:
            score = self.score_map[hit]
            if player_launch == 1:
                score = self.score_map[hit]
            elif player_launch == 2:
                score = self.score_map[hit] * 2
            elif player_launch == 3:
                score = self.score_map[hit] * 3
        else:
            score = self.score_map[hit]

        players[actual_player].add_dart(actual_round, player_launch, hit, score=score)
        
        # TROPHEES
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)

        players[actual_player].score += score
        players[actual_player].round_points += score
        players[actual_player].points += score

        # Store what he played in the table
        players[actual_player].columns[player_launch - 1] = (score, 'int')
        players[actual_player].columns[4] = (players[actual_player].round_points, 'int')
        
        players[actual_player].columns[5] = (players[actual_player].show_ppd(), 'int')
        players[actual_player].columns[6] = (players[actual_player].show_ppr(), 'int')

        players[actual_player].darts_thrown += 1
        players[actual_player].increment_hits(hit)
        self.refresh_stats(players, actual_round)

        # Check for end of game
        if player_launch == self.nb_darts and actual_round >= self.max_round \
                and actual_player == len(players) - 1:
            self.winner = self.check_winner(players)
            if self.winner is not None:
                if not self.game_ended:
                    self.game_ended = True
                    winning_player = players[self.winner]
                    ctrophies.check_game_end_stats(players, winning_player.name, "HIGHSCORE")
                
                handler['return_code'] = 3
            else:
                handler['return_code'] = 2

        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        return handler

    def post_round_check(self, players, actual_round, actual_player):
        handler = self.init_handler()
        handler['return_code'] = -2
        if self.sudden_death:
            dead = self.find_deads(players)
            if dead is not None:
                players[dead].alive = False
                self.compute_position(players, players[dead].position)

                winner = self.get_winner(players)
                if winner is not None:
                    self.winner = winner
                    if not self.game_ended:
                        self.game_ended = True
                        winning_player = players[self.winner]
                        ctrophies.check_game_end_stats(players, winning_player.name, "HIGHSCORE")
                    
                    handler['return_code'] = winner
                else:
                    handler['announcement'] = f'{players[dead].name} est éliminé'
        elif actual_round >= self.max_round and actual_player == len(players) - 1:
            winner_idx = self.check_winner(players)
            if winner_idx is not None:
                if not self.game_ended:
                    self.game_ended = True
                    winning_player = players[winner_idx]
                    ctrophies.check_game_end_stats(players, winning_player.name, "HIGHSCORE")
                handler['return_code'] = winner_idx
            else:
                handler['return_code'] = winner_idx
        return handler

    def find_deads(self, players):
        min_score = None
        nb_min = 0
        for i in range(0, len(players)):
            if not players[i].alive:
                continue

            if min_score is None:
                min_score = players[i].score
                dead = i
                nb_min = 1
            elif players[i].score == min_score:
                nb_min += 1
            elif players[i].score < min_score:
                min_score = players[i].score
                dead = i
                nb_min = 1

        if nb_min == 1:
            players[dead].lives -= 1
            players[dead].columns[3] = (players[dead].lives, 'int')
            if players[dead].lives < 1:
                return dead
            return None
        return None

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

    def miss_button(self, players, actual_player, actual_round, player_launch):
        print('miss')
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
            
        ###ctrophies.process_single_dart(players[actual_player], hit)

    def next_set_order(self, players):
        players.sort(key=self.get_score)

    def refresh_stats(self, players, actual_round):
        for player in players:
            player.stats['Points Per Round'] = player.avg(actual_round)
            player.stats['Points Per Dart'] = player.show_ppd()
