# -*- coding: utf-8 -*-
# Game: Shoot Out & Super Shoot Out
########
import random
from include import cplayer
from include import cgame

### TROPHEES
from include import ctrophies
#

############
# Game Variables
############
OPTIONS = {'theme': 'default', 'simple50': False, 'super_shoot_out': False, 'segment': False}
GAME_RECORDS = {'Points Per Round': 'DESC', 'Points Per Dart': 'DESC'}
NB_DARTS = 3  # Total darts the player has to play
LOGO = 'Shoot-Out.png'
HEADERS = ['D1', 'D2', 'D3', '', 'Rnd', 'Mlt1', 'Mlt2'] # Columns headers
VERSION = '1.00'

def check_players_allowed(nb_players):
    """
    Check if number of players is ok according to options
    """
    return nb_players >= 1 and nb_players <= 12, VERSION, 12 
    
class CPlayerExtended(cplayer.Player):
    """
    Extended player class for Shoot Out
    """
    def __init__(self, ident, config):
        super(CPlayerExtended, self).__init__(ident, config)
        for record in GAME_RECORDS:
            self.stats[record] = '0'
        self.multiplicateur = 1
        self.super_multiplicateur = 1

class Game(cgame.Game):
    """
    Shoot Out game class
    """
    def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
        super().__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)
        self.game_records = GAME_RECORDS
        self.nb_darts = NB_DARTS
        self.logo = LOGO
        self.headers = HEADERS
        self.options = options
        self.simple = options['simple50']
        self.shoot_out = True
        
        self.super_shoot_out = options['super_shoot_out']
        self.segment = options['segment'] # Option segment réintégrée ici
        
        self.max_round = 8

        if self.simple:
            self.score_map.update({'SB': 50})
        else:
            self.score_map.update({'SB': 25})

        self.winner = None
        self.video_player = video_player

        self.multiplicateur = 1
        self.super_multiplicateur = 1
        self.leds = True
        self.calcul = False
        self.game_ended = False  # Verrou pour empêcher le double comptage des stats/victoires

        if self.shoot_out and not self.super_shoot_out:
            self.headers[5] = '--'
            self.headers[6] = 'Mlti'
        elif self.super_shoot_out:
            self.headers[5] = 'Mlt1'
            self.headers[6] = 'Mlt2'
            self.shoot_out = True


    def pnj_score(self, players, actual_player, computer_level, player_launch):
        """
        Intelligence Artificielle (PNJ) pour le jeu Shoot Out / Super Shoot Out :
        - Vise les segments de la cible selon la précision du niveau.
        - Gère la dispersion géographique (voisins) en cas de raté.
        - Intègre la logique spécifique du tour 8 ou du multiplicateur max où le Bull devient accessible.
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

        player = players[actual_player]

        # Vérifie si le Bull est disponible (Tour 8 ou multiplicateur atteint à 20)
        # On regarde si l'attribut global ou le joueur permet de viser le bull
        is_bull_allowed = False
        # On peut inspecter les cibles actuelles du joueur ou l'état de la partie
        if any('SB' in str(t) for t in player.targets):
            is_bull_allowed = True

        # Si le Bull est autorisé, l'IA a une chance de tenter le coup (surtout aux niveaux élevés)
        if is_bull_allowed and random.randrange(100) < (comp_lvl * 5):
            return 'DB' if (comp_lvl >= 4 and random.randrange(100) < 40) else 'SB'

        # Sélection de la cible normale (on privilégie les grands secteurs ou aléatoire sur 1-20)
        target_value = random.choice([20, 19, 18, 20, 16, 15, 17, 13])
        
        # Choix du multiplicateur selon le niveau de l'IA (les niveaux faibles font surtout des Simples)
        rand_multi = random.randrange(100)
        if comp_lvl >= 4 and rand_multi < 25:
            multi = 'T'
        elif comp_lvl >= 2 and rand_multi < 55:
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
            neighbor_multi = 'S' if random.randrange(100) < 70 else multi
            return f"{neighbor_multi}{neighbor_num}"
        else:
            # Raté complet (MISS)
            return 'MISS'



    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        """
        Actions done before each dart throw
        """
        return_code = 0

        # AJOUTE LE BULLS DANS LA LISTE TARGETS AU 8ÈME TOUR
        if actual_round == 8 and player_launch == 1 or self.multiplicateur == 20:
            for player in players:
                Sbull = [f'SB#{self.colors[0]}']
                Dbull = [f'DB#{self.colors[0]}']
                self.rpi.set_target_leds('|'.join(Sbull + Dbull))
                player.targets = player.targets + Sbull + Dbull

        # INITIALISE LES LEDS POUR CHAQUE JOUEUR
        if self.leds:
            for player in players:
                hitsS = [f'S{number}#{self.colors[0]}' for number in range(1, 21)]
                hitss = [f's{number}#{self.colors[0]}' for number in range(1, 21)]
                hitsD = [f'D{number}#{self.colors[0]}' for number in range(1, 21)]
                hitsT = [f'T{number}#{self.colors[0]}' for number in range(1, 21)]
                self.rpi.set_target_leds('|'.join(hitsS + hitsD + hitsT + hitss))
                player.targets = hitsS + hitsD + hitsT + hitss
                self.leds = False

        if player_launch == 1:
            players[actual_player].reset_darts()

        if not players[actual_player].alive:
            return 4

        # Set score at startup
        if actual_round == 1 and player_launch == 1 and actual_player == 0:
            for player in players:
                player.score = 0
                player.alive = True

        # Each new player
        if player_launch == 1:
            players[actual_player].round_points = 0
            players[actual_player].pre_play_score = players[actual_player].score

            # Affiche les targets du joueur
            self.rpi.set_target_leds('')
            self.rpi.set_target_leds('|'.join(players[actual_player].targets))
            players[actual_player].columns[5] = (players[actual_player].multiplicateur, 'int')

            # Reset display Table
            players[actual_player].columns = []
            for i in range(0, 7):
                players[actual_player].columns.append(['', 'int'])
            if actual_round == 1 and actual_player == 0:
                for player in players:
                    player.reset_rounds(self.max_round)

            if not self.super_shoot_out:
                players[actual_player].columns[6] = (players[actual_player].multiplicateur, 'int')
            else:
                players[actual_player].columns[5] = (players[actual_player].multiplicateur, 'int')
                players[actual_player].columns[6] = (players[actual_player].super_multiplicateur, 'int')

        # Clean next boxes
        for i in range(player_launch - 1, self.nb_darts):
            players[actual_player].columns[i] = ('', 'int')

        self.logs.debug(self.infos)
        return return_code



    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        """
        Function run after each dart throw
        """
        handler = self.init_handler()
        handler['show'] = (players[actual_player].darts, hit, True)
        handler['sound'] = hit
        
        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)
        


        # SI ON TOUCHE SB OU DB AU 8ème TOUR
        if (hit == 'SB' or hit == 'DB') and (actual_round == 8 or self.multiplicateur == 20):
            self.multiplicateur = players[actual_player].multiplicateur
            players[actual_player].multiplicateur += 1
            if self.super_shoot_out:
                self.super_multiplicateur = players[actual_player].super_multiplicateur
                players[actual_player].super_multiplicateur += 1
            self.calcul = True

        # QUAND ON TOUCHE UN SEGMENT ALLUMÉ (prend en compte l'option self.segment)
        if hit + '#green' in players[actual_player].targets:
            try:
                while True:
                    if self.segment:
                        players[actual_player].targets.remove(hit + '#green')
                    else:
                        players[actual_player].targets.remove('s' + hit[1:] + '#green')
                        players[actual_player].targets.remove('S' + hit[1:] + '#green')
                        players[actual_player].targets.remove('D' + hit[1:] + '#green')
                        players[actual_player].targets.remove('T' + hit[1:] + '#green')

                    self.multiplicateur = players[actual_player].multiplicateur
                    players[actual_player].multiplicateur += 1
                    if self.super_shoot_out:
                        self.super_multiplicateur = players[actual_player].super_multiplicateur
                        players[actual_player].super_multiplicateur += 1

                    self.calcul = True
            except:
                pass

            self.rpi.set_target_leds('')
            self.rpi.set_target_leds('|'.join(players[actual_player].targets))

        elif not (hit + '#green') in players[actual_player].targets:
            players[actual_player].darts_thrown += 1
            if self.super_shoot_out:
                self.super_multiplicateur = 1
                players[actual_player].super_multiplicateur = 1

        # CALCUL DU SCORE
        if self.calcul:
            if self.super_shoot_out:
                score = self.score_map[hit] * self.multiplicateur * self.super_multiplicateur
                self.calcul = False
            else:
                score = self.score_map[hit] * self.multiplicateur
                self.calcul = False
        else:
            score = self.score_map[hit] * 0

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

        if not self.super_shoot_out:
            players[actual_player].columns[6] = (players[actual_player].multiplicateur, 'int')
        else:
            players[actual_player].columns[5] = (players[actual_player].multiplicateur, 'int')
            players[actual_player].columns[6] = (players[actual_player].super_multiplicateur, 'int')

        players[actual_player].darts_thrown += 1
        players[actual_player].increment_hits(hit)

        if player_launch == self.nb_darts and actual_round >= self.max_round \
                and actual_player == len(players) - 1:
            self.winner = self.check_winner(players)
            if self.winner is not None:
                if not self.game_ended:
                    self.game_ended = True
                    winning_player = players[self.winner]
                    ctrophies.check_game_end_stats(players, winning_player, "SHOOT-OUT")
                
                handler['return_code'] = 3
            else:
                handler['return_code'] = 2

        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        return handler

    def post_round_check(self, players, actual_round, actual_player):
        handler = self.init_handler()
        handler['return_code'] = -2
        if actual_round >= self.max_round and actual_player == len(players) - 1:
            winner_idx = self.check_winner(players)
            if winner_idx is not None:
                if not self.game_ended:
                    self.game_ended = True
                    winning_player = players[winner_idx]
                    ctrophies.check_game_end_stats(players, winning_player, "SHOOT-OUT")
                handler['return_code'] = winner_idx
            else:
                handler['return_code'] = winner_idx
        return handler

    def get_score(self, player):
        return player.score

    def miss_button(self, players, actual_player, actual_round, player_launch):
        print('miss')
        players[actual_player].columns[player_launch - 1] = ('MISS', 'str')
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
        
        self.super_multiplicateur = 1
        players[actual_player].super_multiplicateur = 1
        if self.super_shoot_out:
            players[actual_player].columns[6] = (players[actual_player].super_multiplicateur, 'int')

    def next_set_order(self, players):
        players.sort(key=self.get_score)
