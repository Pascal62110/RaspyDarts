# -*- coding: utf-8 -*-
"""
game by LaDite : Golf
"""
#######

# Versions
# 1.00

import time
import random
from include import cplayer
from include import cgame
#
#
VERSION = '1.00'
LOGO = 'Golf.png' # Background image
HEADERS = ['*', 'D1', 'D2', 'D3', '', 'MRQ', 'PAR'] # Columns headers - Must be a string
OPTIONS = {'theme': 'default', 'nine_holes': False, 'bulls': True, 'master': False}
NB_DARTS = 3
GAME_RECORDS = {'Score': 'DESC', 'Par': 'DESC'}

def check_players_allowed(nb_players):
    """
    Check if number of players is ok according to options
    """
    return nb_players <= 12, VERSION, 12
 
class CPlayerExtended(cplayer.Player):
    """
    Extend the basic player
    """
    def __init__(self, ident, nb_columns, interior=False):
        super().__init__(ident, nb_columns, interior)
        # Init Player Records to zero
        for record in GAME_RECORDS:
            self.stats[record] = '0'

        self.contrat_done = False

class Game(cgame.Game):
    """
    GOLF class game
    """
    def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
        super().__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)
        self.logo = LOGO
        self.headers = HEADERS
        self.nb_darts = NB_DARTS # Total darts the player has to play
        self.options = options
        self.game_records = GAME_RECORDS
        # For rpi
        self.rpi = rpi

        self.winner = None
        self.infos = ''

        if options['nine_holes']:
            self.max_round = 9
        else:
            self.max_round = 18

        if options['master']:
            self.master = True
            self.bulls = True
        else:
            self.master = False
            self.bulls = options['bulls']

    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        """
        Actions done before each dart throw - for example, check if the player is allowed to play
        """
        return_code = 0
        self.infos += ""
        self.rpi.set_target_leds('')
        
        # Stockage du tour actuel pour l'IA
        self.current_round = actual_round

        # Init
        if player_launch == 1:
            players[actual_player].contrat_done = False # First Dart, reset contract to NOT DONE.

            self.save_turn(players)

            # Clear table for current player
            for i in range(1, 4):
                players[actual_player].columns[i] = ('', 'txt', 'game-grey')
### Vide la colonne MARQUE en debut de tour
            players[actual_player].columns[5] = ('', 'txt', 'game-grey')

        leds = []
        tour = actual_round
        #Allume les leds correspondant au chiffre a jouer SELON la variable TOUR
        if actual_round == tour:
            self.rpi.set_target_leds('')
            text = str(tour)
            leds = f'S{tour}#{self.colors[0]}|D{tour}#{self.colors[0]}|T{tour}#{self.colors[0]}'
            if self.bulls:
                leds += f'|SB#{self.colors[0]}|DB#{self.colors[0]}'

        if player_launch == 1:
            for player in players:
                player.columns[0] = (text, 'txt', 'game-text')

        self.rpi.set_target_leds(leds)
        return return_code

    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):
        """
        Is the contract done ?
        """
        
        handler = self.init_handler()

        self.infos = ""
        if player_launch == 1:
            players[actual_player].contrat_done = False

        multiplier, value = self.split_key(hit)
        score = self.score_map.get(hit)
        hits = hit

        if multiplier == 'D':
            led_color = self.colors[0]
        elif multiplier == 'T':
            led_color = self.colors[1]
        else:
            led_color = self.colors[2]

        # affiche le chiffre a viser dans la colonne JOUEUR
        players[actual_player].columns[player_launch] = (str(hit), 'txt', f'game-{led_color}')
        play_sound = True
        players[actual_player].contrat_done = False

        # Default
        hit_type = 'double_bogey'
        points = 5

        if value == str(actual_round) and not hits in ['SB', 'DB']:
            if multiplier == 'D':
                hit_type = 'eagle'
                points = 1
            elif multiplier == 'T':
                hit_type = 'birdie'
                points = 2
            else:
                hit_type = 'bogey'
                points = 4

        elif hits in ['SB', 'DB']:
            if hits == 'DB' and (self.bulls or self.master):
                hit_type = 'condor'
                points = -1
            elif hits == 'SB' and self.bulls and not self.master:
                hit_type = 'albatros'
                points = 0
            else:
                hit_type = 'double_bogey'
                points = 5

        handler['dmd'] = 'Golf-' + hit_type
        handler['video'] = 'golf/' + hit_type
        players[actual_player].marque = points
        players[actual_player].columns[5] = [players[actual_player].marque, 'int']
        players[actual_player].contrat_done = True
        play_sound = False

        # You may want to count darts played
        players[actual_player].darts_thrown += 1

        # It is recommanded to update stats every dart thrown
        self.refresh_stats(players, actual_round)

        #Check actual winnner if last round reached
        if player_launch == self.nb_darts and actual_round >= self.max_round \
                and actual_player == len(players) - 1:
            self.winner = self.check_winner(players)
            if self.winner is not None:
                self.infos += f"Current winner is Player {self.winner}{self.lf}"
                return 3
            # Last round
            if actual_player == self.nb_players - 1 and player_launch == int(self.nb_darts):
                self.infos += f"Last round reached ({actual_round}){self.lf}"
                return 2

        if players[actual_player].contrat_done and player_launch == 3:
            players[actual_player].score += players[actual_player].marque
            players[actual_player].par = players[actual_player].score - (actual_round * 3)
            players[actual_player].columns[6] = [players[actual_player].par, 'int']

        handler['take_shot'] = self.time_to_take_shot_or_video(hit_type)
        return handler

    def check_winner(self, players):
        """
        Method to check WHO is the winnner
        """
        deuce = False
        best_score = 1000
        best_player = None
        for player in players:
            if player.score < best_score:
                best_score = player.score
                deuce = False 
                best_player = player.ident
            elif player.score == best_score:
                deuce = True
                best_player = None
        if deuce:
            self.infos += f"There is a score deuce ! Two people have {best_score}.{self.lf}"
            self.infos += f"No winner!{self.lf}"
            return None
        return best_player

    def early_player_button(self, players, actual_player, actual_round):
        """
        Function launched when the player put player button before having launched all his darts
        """
        self.infos = "Pneu (or early player buttton) function\n"
        self.logs.debug(f'actual_round={actual_round} / max_round={self.max_round} / contrat_done={players[actual_player].contrat_done}')

        if not players[actual_player].contrat_done:
            hit_type = 'double_bogey'
            self.logs.debug('contrat non reussi - appui sur next player (section early player button)')
            points = 5
            players[actual_player].marque = points
            players[actual_player].columns[5] = [players[actual_player].marque, 'int']
            players[actual_player].score += players[actual_player].marque
            players[actual_player].par = players[actual_player].score - (actual_round * 3)
            players[actual_player].columns[6] = [players[actual_player].par, 'int']

            return 4
        else:
            self.logs.debug('contrat reussi - 1 ou 2 fleches jouees')
            players[actual_player].score += players[actual_player].marque
            players[actual_player].par = players[actual_player].score - (actual_round * 3)
            players[actual_player].columns[6] = [players[actual_player].par, 'int']

        if actual_round >= self.max_round:
            self.winner = self.check_winner(players)
            if self.winner is not None:
                self.infos += f"Current winner is Player {self.winner}{self.lf}"
            if actual_player == self.nb_players - 1:
                self.infos += f"Last round reached ({actual_round}){self.lf}"
                if self.winner is not None:
                    return 3
                return 2

        self.display.message([self.display.lang.translate('Golf-save')], 1000, None, 'middle', 'big')
        self.logs.debug(self.infos)
        return 4

    def miss_button(self, players, actual_player, actual_round, player_launch):
        '''
        Miss button
        '''
        players[actual_player].columns[player_launch] = ('MISS', 'str')
        self.display.play_sound('miss')
        players[actual_player].darts_thrown += 1
        players[actual_player].marque = 5
        pass
        
    def pnj_score(self, players, actual_player, computer_level, player_launch):
        """
        Intelligence Artificielle (PNJ) pour le jeu Golf :
        - Vise le trou actuel (1 à 18).
        - Gère la stratégie de conservation ou d'amélioration des tirs précédents (Single, Double, Triple, Bull).
        - Intègre une gestion des ratés avec déviation sur les chiffres voisins physiques de la cible.
        """
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende du format par niveau [miss_chance, p_single, p_double] :
        #   * miss_chance : Probabilité de rater la cible et de dévier vers un voisin physique (%)
        #   * p_single    : Probabilité d'obtenir un Simple (S) (%)
        #   * p_double    : Probabilité d'obtenir un Double (D) (%)
        #   * Triple résiduel : Le reste (100 - p_single - p_double) est attribué au Triple (T)
        # - Paramètres stratégiques :
        #   * improve_chances  : Probabilité de tenter d'améliorer un Triple [10%, 30%, 50%, 70%] selon le niveau
        #   * bull_risk_chances: Probabilité de prendre un risque sur le Bull après un mauvais coup [10%, 25%, 50%, 70%, 85%]
        # - Ajustement : Pour renforcer l'IA, réduis miss_chance et augmente p_double ou la part des Triples.
        # =========================================================================

        current_player = players[actual_player]
        actual_round = getattr(self, 'current_round', 1)

        if actual_round > 18:
            target_number = 20
        else:
            target_number = actual_round

        # Tableau des niveaux : [Taux d'échec / Miss, % Single, % Double]
        levels = [
            [70, 60, 20],  # Niveau 1 : Noob (70% raté, 60% single, 20% double, 20% triple)
            [55, 55, 25],  # Niveau 2 : Débutant (55% raté, 55% single, 25% double, 20% triple)
            [40, 50, 30],  # Niveau 3 : Intermédiaire (40% raté, 50% single, 30% double, 20% triple)
            [20, 45, 35],  # Niveau 4 : Pro (20% raté, 45% single, 35% double, 20% triple)
            [10, 35, 40]   # Niveau 5 : Expert (10% raté, 35% single, 40% double, 25% triple)
        ]
        
        try:
            comp_lvl = int(computer_level)
        except (ValueError, TypeError):
            comp_lvl = 3

        lvl_idx = max(0, min(comp_lvl - 1, len(levels) - 1))
        miss_chance = levels[lvl_idx][0]
        p_single = levels[lvl_idx][1]
        p_double = levels[lvl_idx][2]

        # ----------------------------------------------------
        # 1. GESTION DES TIRS PRÉCÉDENTS (Garder ou Améliorer)
        # ----------------------------------------------------
        if player_launch > 1:
            best_shot = None
            best_rank = 99 # 0 = DB, 1 = SB, 2 = Double (D), 3 = Triple (T)
            
            for i in range(1, player_launch):
                prev_shot = current_player.columns[i][0]
                if not prev_shot or prev_shot == 'MISS':
                    continue
                
                mult, val = self.split_key(prev_shot)
                rank = 99
                
                if prev_shot == 'DB':
                    rank = 0
                elif prev_shot == 'SB':
                    rank = 1
                elif val == str(target_number):
                    if mult == 'D':
                        rank = 2
                    elif mult == 'T':
                        rank = 3
                    elif mult == 'S':
                        rank = 4

                if rank < best_rank:
                    best_rank = rank
                    best_shot = prev_shot

            # Si c'est un DB, SB ou un Double (D), on le garde obligatoirement à 100% jusqu'à la fin du tour
            if best_shot and best_rank <= 2:
                if hasattr(self, 'display') and self.display:
                    self.display.message([f"Je garde ce tir : {best_shot}"], 1500, None, 'middle', 'big')
                return best_shot
            
            # Si c'est un Triple (T), il peut choisir de le garder ou de tenter de faire mieux
            if best_shot and best_rank == 3:
                improve_chances = {1: 0, 2: 10, 3: 30, 4: 50, 5: 70}
                if random.randrange(100) < improve_chances.get(comp_lvl, 20):
                    if hasattr(self, 'display') and self.display:
                        self.display.message([f"Je tente de faire mieux !"], 1500, None, 'middle', 'big')
                else:
                    if hasattr(self, 'display') and self.display:
                        self.display.message([f"Je garde ce tir : {best_shot}"], 1500, None, 'middle', 'big')
                    return best_shot

        # ----------------------------------------------------
        # 2. PRISE DE RISQUE SUR LE BULL (Si mauvais coup précédent)
        # ----------------------------------------------------
        try_bull = False
        if player_launch > 1:
            prev_shot = current_player.columns[player_launch - 1][0]
            if prev_shot and prev_shot != 'MISS':
                _, val = self.split_key(prev_shot)
                if val != str(target_number) and prev_shot not in ['SB', 'DB']:
                    if getattr(self, 'bulls', False) or getattr(self, 'master', False):
                        bull_risk_chances = {1: 10, 2: 25, 3: 50, 4: 70, 5: 85}
                        if random.randrange(100) < bull_risk_chances.get(comp_lvl, 30):
                            try_bull = True

        if try_bull:
            if hasattr(self, 'display') and self.display:
                self.display.message([f"Le PNJ prend un risque et tente le Bull !"], 1500, None, 'middle', 'big')
            bull_miss_chances = [90, 80, 70, 50, 30]
            b_miss = bull_miss_chances[lvl_idx]

            if getattr(self, 'master', False):
                if random.randrange(100) < min(100, b_miss + 15):
                    return 'SB'
                return 'DB'
            else:
                if random.randrange(100) < b_miss:
                    return f"S{random.randint(1, 20)}"
                db_chance = comp_lvl * 10
                return 'DB' if random.randrange(100) < db_chance else 'SB'

        # ----------------------------------------------------
        # 3. TEST DE RATÉ (MISS) : Touche un CHIFFRE VOISIN physique
        # ----------------------------------------------------
        if random.randrange(100) < miss_chance:
            dartboard_order = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5]
            if target_number in dartboard_order:
                idx = dartboard_order.index(target_number)
                left_neighbor = dartboard_order[(idx - 1) % len(dartboard_order)]
                right_neighbor = dartboard_order[(idx + 1) % len(dartboard_order)]
                miss_target = random.choice([left_neighbor, right_neighbor])
            else:
                miss_target = random.randint(1, 20)
            return f"S{miss_target}"

        # ----------------------------------------------------
        # 4. TIR NORMAL SUR LE TROU EN COURS
        # ----------------------------------------------------
        rand_val = random.randrange(100)
        if rand_val < p_single:
            multi = 'S'
        elif rand_val < p_single + p_double:
            multi = 'D'
        else:
            multi = 'T'

        return f"{multi}{target_number}"

    def display_segment(self):
       """
       Set if a message is shown to indicate the segment hitted !
       """
       return False
