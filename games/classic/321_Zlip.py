# -*- coding: utf-8 -*-
# Game by poilou
#######
from include import cplayer
from include import cgame
import random

### TROPHEES
from include import ctrophies


# VAR
WinTotal = 321
LOGO = '321_Zlip.png'
HEADERS = ['D1', 'D2', 'D3', '', '', '', '']
OPTIONS = {'theme': 'default', 'max_round': 10, 'advanced': True, 'master': False}
NB_DARTS = 3  # How many darts the player is allowed to throw
GAME_RECORDS = {'Zlips': 'DESC', 'Zlipped': 'ASC', 'Points Per Round': 'DESC'}
VERSION = '1.00'

def check_players_allowed(nb_players):
    """
    Check if number of players is ok according to options
    """
    return nb_players >= 2 and nb_players <= 12, VERSION, 12
    
# Extend the basic player
class CPlayerExtended(cplayer.Player):
    def __init__(self, ident, nb_columns, interior=False):
        super().__init__(ident, nb_columns, interior)
        self.havezapped = 0
        self.ident = ident
        self.nbzapped = 0
        # Init Player Records to zero
        for record in GAME_RECORDS:
            self.stats[record] = '0'

    def zap(self, display_zip=False):
        self.havezapped += 1
        if display_zip:
            self.columns[6] = ['321Zap_zlip', 'image']

    def get_zap(self):
        return self.havezapped

    def set_zapped(self):
        self.nbzapped += 1

    def get_zapped(self):
        return self.nbzapped

class Game(cgame.Game):
    def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
        super(Game, self).__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)
        self.nb_darts = NB_DARTS  # Total darts the player has to play
        self.game_records = GAME_RECORDS
        self.logo = LOGO
        self.headers = HEADERS
        self.score_map.update({'SB': 50})
        self.options = options

        #  Get the maxiumum round number
        self.max_round = int(self.options['max_round'])
        # For Raspberry
        self.rpi = rpi
    
        self.advanced = options['advanced']
        self.master = options['master']
    #
    # Post Darts Launch Checks
    #
    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):

        # Init
        handler = self.init_handler()
        check = None
        score = int(self.score_map.get(hit))
        self.infos = "Score before playing {players[actual_player].score}"

        # Whatever you played, we keep it in the display table
        players[actual_player].columns[player_launch - 1] = (f'{score}', 'str')
        self.infos = "Player has played {score}"
        
        ### TROPHEES
        ctrophies.process_single_dart(players[actual_player], hit)
        
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        #if player_launch == 3:
        #    round_darts = players[actual_player].darts[-3:]
        #    ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)
        

        # Case : the player goes over 321
        if players[actual_player].score + score > WinTotal:
            self.infos += "/!\\ Going over {}, too much !\n".format(WinTotal)
            delete = players[actual_player].score + score - WinTotal
            players[actual_player].set_score(WinTotal - delete)
            player_launch = self.nb_darts
            handler['return_code'] = 1
            handler['sound'] = 'toohigh'
            handler['message'] = 'Damn, you get too high !'

        # The player reach exactly 321 points
        elif players[actual_player].score + score == WinTotal:
            players[actual_player].increment_hits(hit)
            # The player did not zlip anyone and "master" is enabled. master has got a priority on advanced
            if players[actual_player].get_zap() == 0 and self.master:
                players[actual_player].set_score(0)
                self.infos += "/!\\ Game in master mode - You never zlipped, so back to Zero !\n"
                player_launch = self.nb_darts
                handler['return_code'] = 1
                handler['sound'] = 'whatamess'
                handler['message'] = 'Ho Dear ! You have to Zlip first !'
            # The player did not zlip anyone and "advanced" is enabled
            elif players[actual_player].get_zap() == 0 and self.advanced:
                players[actual_player].set_score(0)
                self.infos += "/!\\Game in advanced mode - You did not Zlip, so you won a Zlip !\n"
                player_launch = self.nb_darts
                players[actual_player].zap(True)
                handler['return_code'] = 1
                handler['sound'] = 'zapdamn'  # If its a valid hit, play sound
                handler['message'] = 'Gosh ! You picked up a free Zlip !'
            # The player zapped at least once or none of the advanced nor master is true - Victoire
            elif players[actual_player].get_zap() > 0 or (self.master and not self.advanced):
                self.infos += "/!\\Player {} wins !\n".format(players[actual_player].ident)
                self.winner = players[actual_player].ident
                
                ### TROPHEES DE VICTOIRE ---
                winning_player = players[self.winner]
                

                # enregistres les donnees du jeu highscorepour stats
                ctrophies.check_game_end_stats(players, winning_player, "321 Zlip")
                
                
                players[actual_player].add_score(score)
                players[actual_player].increment_hits(hit)
                handler['sound'] = 'zapdamn'  # If its a valid hit, play sound
                handler['return_code'] = 3
                handler['message'] = f'{players[actual_player].name} won with {players[actual_player].get_zap()} zap !'

        # Standard Case - score is incremented
        else:
            handler['show'] = (players[actual_player].darts, hit, True)
            handler['sound'] = hit
            players[actual_player].points += score
            players[actual_player].increment_hits(hit)
            players[actual_player].add_score(score)

        check = False
        # Case : if the player Zlip another player
        for player in players:
            if player.score == players[actual_player].score and player.ident != players[actual_player].ident and players[
                actual_player].score > 0:
                self.infos += "The player {} has been zlipped !\n".format(player.ident)
                player.set_score(0)
                if self.master or self.advanced:
                    players[actual_player].zap(True)
                else:
                    players[actual_player].zap()
                player.set_zapped()
                handler['sound'] = 'zapdamn'  # If its a valid hit, play sound
                handler['message'] = 'zapped!'
                check = True

        players[actual_player].add_dart(actual_round, player_launch, hit, score=score, check=check)
        
        # TROPHEES
        # On vérifie les trophées de volée uniquement à la 3ème fléchette
        if player_launch == 3:
            round_darts = players[actual_player].darts[-3:]
            ctrophies.check_and_unlock_trophies(players[actual_player], round_darts)

        # You may want to count darts played
        players[actual_player].darts_thrown += 1
        # players[actual_player].points = players[actual_player].score

        # It is recommanded to update stats evry dart thrown
        self.refresh_stats(players, actual_round)

        #### Display and return code only behond this point

        # Round log
        self.infos += "Score after playing {players[actual_player].score}"
        self.infos += "Player  {} - dart {} - Zlips : {} - Zlipped : {}\n {}".format(actual_player, player_launch,
                                                                                        players[
                                                                                            actual_player].havezapped,
                                                                                        players[actual_player].nbzapped,
                                                                                        self.infos)
        self.infos += "Touche {}\n".format(hit)
        self.infos += "Fleches lancees : {}\n".format(str(player_launch))
        self.infos += "Total des touches : {}\n".format(players[actual_player].get_total_hit())

        # If its the last launch of last round
        if actual_round >= self.max_round and actual_player == self.nb_players - 1 and player_launch == self.nb_darts:
            self.infos += "/!\\Last round reached ({})\n".format(actual_round)
            handler['return_code'] = 2

        # Time for shot or video ?
        handler['take_shot'] = self.time_to_take_shot_or_video(hit)

        # Print debug
        self.logs.debug(self.infos)
        return handler

    #####
    # Method called before each dart launch
    #####
    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        # Keep player_launch in current object
        self.player_launch = player_launch

        if player_launch == 1:
            players[actual_player].reset_darts()
            if actual_round == 1 and actual_player == 0:
                for player in players:
                    player.reset_rounds(self.max_round)

        # Clean table for current player (only next launch)
        for i in range(player_launch, 4):
            players[actual_player].columns[i - 1] = ('', 'str')

        score_to_zap = -1
        diff_score = -1
        targets_to_zap = []
        zap_list = []

        all_targets_to_zap = []
        # For all other players
        player_iterator = 0
        for player in players:
            if player_launch == 1 or player.ident != actual_player:
                # clean table for all players
                player.columns[0] = ['', 'str']
                player.columns[1] = ['', 'str']
                player.columns[2] = ['', 'str']
            # Si c est un joueur qui a plus de points on affiche le nombre de points pour le zapper
            if player.score > players[actual_player].score and player.ident != actual_player:
                diff_score = player.score - players[actual_player].score
                # Possibilities = self.SearchPossibleLaunch(diff_score)
                zap_list = self.SearchZap(diff_score)
                if len(zap_list) >= 1:
                    player.columns[0] = (str(zap_list[0]), 'str', 'game-green')
                    if score_to_zap == - 1 or score_to_zap > diff_score:
                        score_to_zap = diff_score
                        targets_to_zap = zap_list

                if len(zap_list) >= 2: player.columns[1] = (str(zap_list[1]), 'str', 'game-green')
                if len(zap_list) >= 3: player.columns[2] = (str(zap_list[2]), 'str', 'game-green')
                if len(zap_list) > 0 and actual_player != player_iterator:
                    for key in zap_list:
                        all_targets_to_zap.append(f'{key}#{player.color}')

            # Sinon on cherche un possible zap en arriere
            elif player.ident != actual_player:
                score_up = WinTotal - players[actual_player].score
                score_down = WinTotal - player.score
                zap_list = self.SearchZap(score_up, score_down)
                if len(zap_list) >= 1:
                    player.columns[0] = (zap_list[0], 'str', 'game-purple')
                    if score_to_zap == - 1 or score_to_zap > diff_score:
                        score_to_zap=diff_score
                        targets_to_zap=zap_list
                if len(zap_list) >= 2: player.columns[1] = (zap_list[1], 'str', 'game-purple')
                if len(zap_list) >= 3: player.columns[2] = (zap_list[2], 'str', 'game-purple')
                if len(zap_list) > 0 and actual_player != player_iterator:
                    for key in zap_list:
                        all_targets_to_zap.append(f'{key}#{self.colors[0]}')

            # Pour nous on affiche le nombre de points vers la victoire (si ZAP OK et Option master ou advanced)
            if players[actual_player].get_zap() > 0 or (
                    not self.master and not self.advanced):
                diff_score = WinTotal - players[actual_player].score

                zap_list = self.SearchZap(diff_score)
                if len(zap_list) >= 1:
                    players[actual_player].columns[player_launch - 1] = (zap_list[0], 'str', 'game-red')
                if len(zap_list) >= 2:
                    players[actual_player].columns[player_launch] = (zap_list[1], 'str', 'game-red')
                if len(zap_list) >= 3:
                    players[actual_player].columns[player_launch + 1] = (zap_list[2], 'str', 'game-red')

                if len(zap_list) > 0 and actual_player != player_iterator:
                    for key in zap_list:
                        all_targets_to_zap.append(f'{key}#{self.colors[1]}')

            player_iterator += 1
        self.rpi.set_target_leds('|'.join(all_targets_to_zap))
        return 0

    def pnj_score(self, players, actual_player, computerLevel, player_launch):
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende : [MISS, Taux tactique, Triples, Doubles, Bull, Voisins, Constance]
        # - Plus forte (plus précise) : Diminuer le MISS (1ère val), augmenter Triples/Doubles/Bull (val 3, 4, 5).
        # - Plus "humaine" / brouillonne : Augmenter le MISS (1ère val), diminuer les triples et le bull.
        # - Plus agressive (stratège) : Augmenter le taux tactique (2e val).
        # =========================================================================
        levels = [
                 [70, 15, 2,  5,  10, 45, 60],  # 1 : Noob 
                 [55, 30, 4,  8,  20, 52, 68],  # 2 : Débutant
                 [25, 55, 12, 14, 50, 65, 78],  # 3 : Intermédiaire 
                 [15, 70, 20, 16, 70, 78, 88],  # 4 : Pro 
                 [8,  90, 40, 25, 88, 92, 98]   # 5 : Expert 
                ]

        lvl_idx = max(0, min(computerLevel - 1, len(levels) - 1))
        tire_rate = levels[lvl_idx][0]
        tactik_rate = levels[lvl_idx][1]

        # 1. Gestion du tir raté (MISS) selon le niveau
        if random.randrange(100) < tire_rate:
            players[actual_player].columns[player_launch - 1] = ('MISS', 'str')
            self.display.play_sound('miss')
            players[actual_player].darts_thrown += 1
            return 'MISS'

        zap_list = []
        current_score = players[actual_player].score
        has_already_zapped = players[actual_player].get_zap() > 0
        distance_to_321 = WinTotal - current_score

        # 2. Stratégie de l'IA
        # Si elle n'a PAS ENCORE zlippé OU SI elle est proche de la fin (<= 60 points de 321) 
        # et qu'elle veut tenter un coup de Trafalgar de dernière minute :
        should_look_for_zlip = not has_already_zapped or (distance_to_321 <= 60 and random.randrange(100) < 60)

        if should_look_for_zlip and random.randrange(100) < tactik_rate:
            for player in players:
                if player.ident != actual_player and player.score > current_score:
                    diff_score = player.score - current_score
                    zap_list = self.SearchZap(diff_score)
                    if zap_list:
                        break  # Trouvé une cible pour zlipper un adversaire en chemin !

        # 3. Si pas de zlip visé (ou si elle est en mode route directe vers 321), on vise 321
        if not zap_list:
            zap_list = self.SearchZap(distance_to_321)

        # 4. Sélection finale du coup
        if not zap_list:
            remaining = WinTotal - current_score
            possible_hits = [hit for hit, val in self.score_map.items() if val <= remaining]
            if possible_hits and remaining > 0:
                hit_target = random.choice(possible_hits)
            else:
                number = random.randint(1, 20)
                mult = random.choice(['S', 'S', 'S', 'D'])
                hit_target = f'{mult}{number}'
        else:
            target_index = player_launch - 1
            if target_index < len(zap_list):
                hit_target = zap_list[target_index]
            else:
                hit_target = zap_list[0]

        return hit_target
    # Search any possible ZAP (Normal and back zap)
    #
    def SearchZap(self, score_up, score_down=0):
        # /!\return value must be iterable and must have at least 3 values
        # print LSTChiffres
        return_value = []
        total = score_up + score_down
        # 1 dart possibility
        for hit, key in self.score_map.items():
            if total == key:
                return_value = [hit.upper()]
                return return_value
                break
        # 2 darts possibilities - Player must have at least two darts left
        if self.player_launch == 2 or self.player_launch == 1:
            for hit, key in self.score_map.items():
                if total > key and key < score_up:
                    firstrest = total - key
                    for hit2, key2 in self.score_map.items():
                        if firstrest == key2:
                            return_value = [hit.upper(), hit2.upper()]
                            return return_value
        # 3 darts possibilities - Player must have at least 3 darts left
        if self.player_launch == 1:
            for hit, key in self.score_map.items():
                if total > key and key < score_up:
                    firstrest = total - key
                    for hit3, key3 in self.score_map.items():
                        if firstrest > key3 and key + key3 < score_up:
                            secondrest = firstrest - key3
                            for hit4, key4 in self.score_map.items():
                                if secondrest == key4:
                                    return_value = [hit.upper(), hit3.upper(), hit4.upper()]
                                    return return_value
        return return_value

    def miss_button(self, players, actual_player, actual_round, player_launch):
        '''
        Miss button
        '''
        print('miss')
        #players[actual_player].columns[6] = (self.moyenne, 'int')
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

    ###############
    # Method to frefresh player.stat - Adapt to the stats you want.
    # They represent mathematical formulas used to calculate stats. Refreshed after every launch
    def refresh_stats(self, players, actual_round):
        for player in players:
            player.stats['Zlips'] = player.havezapped
            player.stats['Zlipped'] = player.nbzapped
            player.stats['Points Per Round'] = player.avg(actual_round)
