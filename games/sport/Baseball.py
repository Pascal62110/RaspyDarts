# -*- coding: utf-8 -*-
"""
Game by LaDite - jeu base sur le castle de david
"""


# Versions
# 1.00

from include import cplayer
from include import cgame
import random
import subprocess

VERSION = '1.00'
# Dictionnay of options - Text format only
OPTIONS = {'theme': 'default', 'max_round': 9, '7eme_manche': False, 'noequal': True, 'team': False}

# Background image - relative to images folder - Name it like the game itself
LOGO = 'Baseball.png' # Background image
# Columns headers - Better as a string

HEADERS = ['*', ' ', 'D1', 'D2', 'D3', '', 'BASE'] # Columns headers - Must be a string

NB_DARTS = 3 # How many darts per player and per round
# Dictionary of stats and display order (For example : Points Per Darts and avg are displayed in ascending order)
GAME_RECORDS = {'Points Per Round':'DESC'}

def check_players_allowed(nb_players):
    """
    Return the player number max for a game.
    """
    return nb_players >= 1 and nb_players <= 4, VERSION, 4

class CPlayerExtended(cplayer.Player):
    """
    Extend the basic player
    """
    def __init__(self, ident, nb_columns, interior=False):
      super().__init__(ident, nb_columns, interior)
      self.home = 0
      # Init Player Records to zero
      for record in GAME_RECORDS:
         self.stats[record] = '0'
      self.columns[6] = ['baseball_image0', 'image']

class Game(cgame.Game):
    """
    Class of the real game
    """
    def __init__(self, display, game, nb_players, options, config, logs, rpi, dmd, video_player):
      super().__init__(display, game, nb_players, options, config, logs, rpi, dmd, video_player)
      # For rpi
      self.rpi = rpi
      self.logo = LOGO
      self.headers = HEADERS
      self.nb_darts = NB_DARTS
      self.nb_players = nb_players
      self.options = options
      #  Get the maximum round number
      self.max_round = int(options['max_round'])
      # GameRecords is the dictionnary of stats (see above)
      self.GameRecords = GAME_RECORDS

      # gestion de l'affichage du segment
      self.show_hit = True

      self.septieme = options['7eme_manche']
      self.noequal = options['noequal']

      self.winner = None

      self.base = 0
      self.nb_touche = 0
      self.egalite = 'ko'

   # Actions done before each dart throw - for example, check if the player is allowed to play
    def pre_dart_check(self, players, actual_round, actual_player, player_launch):
        
        handler = self.init_handler()
        return_code = 0
        self.infos = ''
        # Set score at startup
        if actual_round == 1 and player_launch == 1 and actual_player == 0:
            try:
                LST = self.check_handicap(players)
            except Exception as e:
                self.logs.error("Handicap failed : {}".format(e))
            for player in players:
                # Init score
                player.score = 0
                player.base_occupee = 0

### AFFICHE LE MESSAGE AU DEBUT DU TOUR SI 7eme manche = True
        if self.septieme and actual_round == 7:
            #self.display.message([self.display.lang.translate('Baseball-septieme')], 1000, None, 'middle', 'big')
            handler['message'] = 'Baseball-septieme'

        # Determine le segment du joueur et des advs
        if player_launch == 1:
            # segment du joueur choisi au hasard à chaque fléchette
            segments = []
            for i, player in enumerate(players):
                home = random.randint(1, 20)
                while home in segments:
                    home = random.randint(1, 20)
                player.home = home
                segments.append(home)
                # affiche le chiffre a toucher dans la premiere colonne
                player.columns[0] = (player.home, 'int')

            if actual_round == 1:
                players[actual_player].base_occupee = 0

            players[actual_player].round_points = 0
            self.save_turn(players)
            players[actual_player].pre_play_score = players[actual_player].score # Backup current score

            #Reset display Table
            players[actual_player].columns = []
            # Efface les colonne 1-7
            for i in range(0, 7):
                players[actual_player].columns.append(['', 'str'])

        # Determine la couleur des segments
        segments = []
        index = 0
        for player in players:
            # J'ajoute dans le tableau les valeurs : S12#green, D12#green, T12|#green, E12#green
            # green est un exemple. player.color est la couleur du joueur
            for multiplier in ('S', 'D', 'T', 'E'):
                segments.append(f'{multiplier}{player.home}#{player.color}')

        # Ajout des SB/DB
        segments.append(f'SB#{players[actual_player].color}')
        segments.append(f'DB#{players[actual_player].color}')

        # Construction de la chaine S12#green|D12#green|T12|#green|E12#green|SB#green|DB#green
        self.rpi.set_target_leds('|'.join(segments))

        # Display stats
        players[actual_player].columns[0] = (players[actual_player].home, 'int')
        image_bb = f'baseball_image{players[actual_player].base_occupee}'
        players[actual_player].columns[6] = [image_bb, 'image']

        
        handler['return_code'] = return_code
        return handler
        #return return_code


    def pnj_score(self, players, actual_player, computer_level, player_launch):
        """
        Intelligence Artificielle (PNJ) pour le jeu Baseball :
        - Gère le HomeRun tactique sur le Bull lorsque le PNJ a 3 bases pleines.
        - Gère la stratégie d'attaque ciblée sur les adversaires selon le niveau.
        - Utilise une table de probabilités complète (ratés, précision, voisins, doubles, triples).
        """
        # =========================================================================
        # GUIDE DE RÉGLAGE DES NIVEAUX DE DIFFICULTÉ :
        # - Légende du format par niveau : [miss_chance, exact_target_chance, neighbor_chance, double_chance, triple_chance]
        #   * miss_chance         : Probabilité de rater complètement (retourne 'MISSDART') (%)
        #   * exact_target_chance : Probabilité de viser la cible exacte (%)
        #   * neighbor_chance     : Probabilité de viser un secteur voisin géométrique/physique (%)
        #   * double_chance       : Probabilité d'obtenir un Double (D) (%)
        #   * triple_chance       : Probabilité d'obtenir un Triple (T) (%)
        # - Ajustement : Pour renforcer l'IA, réduis miss_chance et augmente exact_target_chance.
        # =========================================================================

        geo_neighbors = {
            1: [20, 18, 4], 2: [17, 15, 10], 3: [19, 17, 2], 4: [18, 13, 1], 
            5: [20, 12, 9], 6: [10, 13, 15], 7: [19, 16, 8], 8: [16, 11, 7], 
            9: [14, 12, 5], 10: [15, 6, 2], 11: [14, 8, 16], 12: [9, 5, 20], 
            13: [6, 4, 11], 14: [9, 11, 16], 15: [10, 2, 6], 16: [7, 8, 11], 
            17: [2, 3, 15], 18: [4, 1, 20], 19: [7, 3, 2], 20: [1, 5, 12]
        }

        # Table de précision par niveau : [miss_chance, exact_target_chance, neighbor_chance, double_chance, triple_chance]
        levels = [
            [40, 10, 20,  4,  2],  # Niveau 1 (Noob) : 40% miss, 6% total D+T
            [25, 25, 30,  8,  5],  # Niveau 2 (Débutant) : 25% miss, 13% total D+T
            [10, 50, 40, 18, 15],  # Niveau 3 (Intermédiaire) : 10% miss, 33% total D+T (18% D + 15% T)
            [ 2, 75, 50, 24, 20],  # Niveau 4 (Pro) : 2% miss, 44% total D+T
            [ 0, 90, 60, 30, 25]   # Niveau 5 (Expert) : 0% miss, 55% total D+T
        ]

        try:
            comp_lvl = int(computer_level)
        except (ValueError, TypeError):
            comp_lvl = 3

        lvl_idx = max(0, min(comp_lvl - 1, len(levels) - 1))

        # Gestion du raté global (Miss)
        if random.randrange(100) < levels[lvl_idx][0]:
            players[actual_player].darts_thrown += 1
            return 'MISSDART'

        current_player = players[actual_player]
        bases = getattr(current_player, 'base_occupee', 0)
        home_target = getattr(current_player, 'home', random.randint(1, 20))

        # 1. Si le PNJ a 3 bases pleines, sa priorité absolue est de tenter le Bull (HomeRun)
        if bases == 3 and comp_lvl >= 3 and random.randrange(100) < (comp_lvl * 20):
            if random.randrange(100) < 40 and comp_lvl >= 4:
                return 'DB'
            else:
                return 'SB'

        # 2. Logique d'attaque tactique basée sur le score des adversaires (Niveau 3 et plus)
        opponents_with_runners = [
            p for p in players 
            if p.ident != current_player.ident and getattr(p, 'base_occupee', 0) > 0
        ]

        attack_chance = comp_lvl * 6 if comp_lvl >= 3 else 0

        target_segment = None
        if comp_lvl >= 3 and opponents_with_runners and random.randrange(100) < attack_chance:
            opponents_with_runners.sort(key=lambda p: p.score, reverse=True)
            target_opp = opponents_with_runners[0]
            target_segment = target_opp.home
        
        # 3. Si pas d'attaque, le PNJ vise sa propre cible (home)
        if target_segment is None:
            rand_val = random.randrange(100)
            if rand_val < levels[lvl_idx][1]:
                target_segment = home_target
            elif home_target in geo_neighbors and rand_val < levels[lvl_idx][1] + levels[lvl_idx][2]:
                target_segment = random.choice(geo_neighbors[home_target])
            else:
                target_segment = random.randint(1, 20)

        if target_segment > 20:
            target_segment = 20

        # Choix du multiplicateur ('S', 'D', 'T')
        mult_rand = random.randrange(100)
        if mult_rand < levels[lvl_idx][3]:
            mult = 'D'
        elif mult_rand < levels[lvl_idx][3] + levels[lvl_idx][4]:
            mult = 'T'
        else:
            mult = 'S'

        return f'{mult}{target_segment}'



    def early_player_button(self, players, actual_player, actual_round):
        return_code = 1
        # Numero de la prochaine fléchette (1 à nb_darts) : le moteur ne le transmet pas à cette méthode
        player_launch = sum(1 for dart in players[actual_player].darts if dart is not None) + 1

        if self.noequal and player_launch == self.nb_darts and actual_round >= self.max_round \
                and actual_player == len(players) - 1:

            bestscore = 2  ### JUSTE POUR TEST - modifier par le score d un joueur ou autre
            for player in players:
                ### AVEC EGALITE
                if player.score == bestscore:
                    self.infos += 'egalité - manche supplémentaire'
                    #self.egalite = 'ok'
                else:
                    ### PAS D EGALITE
                    self.infos += 'pas d egalite - fin de partie'
                    bestscoreid = -1
                    bestscore = -1
                    for player in players:
                        if player.score > bestscore:
                            bestscore = player.score
                            bestscoreid = player.ident
                    self.winner = bestscoreid
                    return_code = 3

            return return_code

### FIN DE PARTIE (ET OPTION NOEQUAL = FALSE)
        if not self.noequal and player_launch == self.nb_darts and actual_round >= self.max_round \
                and actual_player == len(players) - 1:
            self.infos += 'avec ou sans egalite - fin de partie'
            bestscoreid = -1
            bestscore = -1
            for player in players:
                if player.score > bestscore:
                    bestscore = player.score
                    bestscoreid = player.ident
            self.winner = bestscoreid
            return_code = 3

        return return_code


    def post_dart_check(self, hit, players, actual_round, actual_player, player_launch):

        return_code = 0
        handler = self.init_handler()
        self.show_hit = True

        self.display.sound_for_touch(hit) # Touched !

        # Record total dart thrown, total hits (S=1, D=2, T=3) and refresh players stats
        players[actual_player].darts_thrown += 1

        # stock the segment hitted
        #players[actual_player].columns[player_launch + 1] = (hit[1:], 'int')
        players[actual_player].columns[player_launch + 1] = [hit, 'txt']

        # test multiplicateur
        multiplier, value = self.split_key(hit, multiplier=True)

### JOUEUR TOUCHE LE BULLS (OK)
        if hit == 'SB':
            players[actual_player].increment_hits(hit)
            ### AJOUTE UN BONUS DE 1 POINT SUPPLEMENTAIRE POUR LE SUPER HOMERUN
            temporaire = players[actual_player].base_occupee + 1
            players[actual_player].score = (players[actual_player].score + temporaire)
            players[actual_player].base_occupee = 0

            self.infos += f'valeur temporaire (bull) : {temporaire}'

            self.show_hit = False
            #self.display.play_sound('baseball_homerun')
            handler['sound'] = 'baseball_homerun'

            ### 0 à 3 bases occupée(sà
            if 1 <= temporaire <= 4:
                #self.video_player.play_video(self.display.file_class.get_full_filename(f'baseball/homerun{temporaire}', 'videos'))
                handler['video'] = 'baseball/homerun'+str(temporaire)

            ### RE-INITIALISE LE NOMBRE DE BASES DU JOUEUR
            image_bb = f'baseball_image{players[actual_player].base_occupee}'
            players[actual_player].columns[6] = [image_bb, 'image']

        elif hit == 'DB':
            players[actual_player].increment_hits(hit)
            ### AJOUTE UN BONUS DE 2 POINTS SUPPLEMENTAIRES POUR LE SUPER HOMERUN
            temporaire = players[actual_player].base_occupee + 2
            players[actual_player].score = (players[actual_player].score + temporaire)
            players[actual_player].base_occupee = 0

            self.infos += f'valeur temporaire (bull) : {temporaire}'

            self.show_hit = False
            #self.display.play_sound('baseball_super_homerun')
            handler['sound'] = 'baseball_super_homerun'

            ### 0 à 3 bases occupée(sà
            if 2 <= temporaire <= 5:
                #self.video_player.play_video(self.display.file_class.get_full_filename(f'baseball/super_homerun{temporaire - 1}', 'videos'))
                handler['video'] = 'baseball/homerun'+str(temporaire)

            ### RE-INITIALISE LE NOMBRE DE BASES DU JOUEUR
            image_bb = f'baseball_image{players[actual_player].base_occupee}'
            players[actual_player].columns[6] = [image_bb, 'image']
        else:
            ### JOUEUR TOUCHE SON SEGMENT (OK)
            for i, player in enumerate(players):
                if i == actual_player and player.home == int(value):
                    players[actual_player].base_occupee += multiplier
                    self.infos += 'base occupee : {players[actual_player].base_occupee}'
                    players[actual_player].increment_hits(hit)
                    self.show_hit = False
                    #self.display.play_sound('baseball_batte')
                    handler['sound'] = 'baseball_batte'
                    #self.display.play_sound('baseball_base_acquise')
                    handler['sound'] = 'baseball_base_acquise'

                    if 1 <= players[actual_player].base_occupee <= 3:
                        #self.video_player.play_video(self.display.file_class.get_full_filename(f'baseball/base{players[actual_player].base_occupee}_acquise', 'videos'))
                        handler['video'] = 'baseball/homerun'+str(players[actual_player].base_occupee)+'_acquise'

                    elif players[actual_player].base_occupee > 3:
                        temporaire = (players[actual_player].base_occupee - 3)
                        players[actual_player].score = players[actual_player].score + temporaire
                        players[actual_player].base_occupee = players[actual_player].base_occupee - temporaire

                        self.infos += f'valeur temporaire : {temporaire}'
                        #self.display.play_sound('baseball_points_gagne')
                        handler['sound'] = 'baseball_points_gagne'

                        ### 1 POINT
                        if 1 <= temporaire <= 3:
                            #self.video_player.play_video(self.display.file_class.get_full_filename(f'baseball/score{temporaire}', 'videos'))
                            handler['video'] = 'baseball/score'+str(temporaire)

### JOUEUR TOUCHE LE SEGMENT D UN ADVS (OK)
                if i != actual_player and player.home == int(value):
                    player.base_occupee -= multiplier
                    # Pour ne pas descendre en dessous de 0
                    player.base_occupee = max(player.base_occupee, 0)

                    ### RE-INITIALISE LES BASES DE L ADVERSAIRE
                    if player.base_occupee >= 0:
                        self.show_hit = False
                        #self.display.play_sound('baseball_joueur_out')
                        handler['sound'] = 'baseball_joueur_out'
                        #self.video_player.play_video(self.display.file_class.get_full_filename('baseball/runner_out', 'videos'))
                        handler['video'] = 'baseball/runner_out'

### SEPTIEME MANCHE (si joueur ne touche pas son segment 1x sur la volee, son score est divise par 2)
                if i == actual_player and players[actual_player].home != int(value):
                    if self.septieme and actual_round == 7:

                        self.infos += f'self.septieme : {self.septieme}'
                        self.nb_touche += 1
                        self.infos += f'touche : (self.nb_touche)'
                        if self.nb_touche == 3:
                            #self.display.play_sound('baseball_balle_ratee')
                            handler['sound'] = 'baseball_balle_ratee'
                            #self.video_player.play_video(self.display.file_class.get_full_filename('baseball/strike', 'videos'))
                            handler['video'] = 'baseball/strike'
                            players[actual_player].score = int((players[actual_player].score / 2))
                            self.nb_touche = 0

                image_bb = f'baseball_image{player.base_occupee}'
                player.columns[6] = [image_bb ,'image']
                
        # Time for shot or video ?
        handler['take_shot'] = self.time_to_take_shot_or_video(hit)
        handler['return_code'] = return_code
        return handler

        self.logs.debug(self.infos)
        #return return_code

    def check_winner(self, players):
        """
        Method to identify the winner, in case
        """
        bestscore = -1
        return_code = -1
        for player in players:
            ### AVEC EGALITE
            if player.score == bestscore:
                self.winner = None
                return_code = 2
            elif player.score > bestscore:
                bestscore = player.score
                self.winner = player.ident
                return_code = 3

        return return_code

    def post_round_check(self, players, actual_round, actual_player):
        """
        In case of "Early player button" pressed on last dart of last player round of last round
        Return id of winner of -1 if None
        """
        self.logs.debug(f"Post round : actual_round={actual_round} / self.max_round={self.max_round} / actual_player={actual_player}")

        if actual_round < self.max_round:
            return -2

        winner = self.check_winner(players)
        if winner == 2:
            if self.noequal:
                self.max_round += 1
                self.display.message([self.display.lang.translate('Baseball-egalite')], 1000, None, 'middle', 'big')
                #handler['message'] = 'Baseball-egalite'
                # One more round
                return -2
            return -1

        return self.winner

    def refresh_stats(self, players, actual_round):
        """
        Method to frefresh player.stat - Adapt to the stats you want. They represent mathematical formulas used to calculate stats. Refreshed after every launch
        """
        for player in players:
            player.stats['Points Per Round'] = player.show_ppr()

    def miss_button(self, players, actual_player, actual_round, player_launch):
        '''
        Miss button
        '''
        players[actual_player].columns[player_launch+1] = ('MISS', 'str')
        self.display.play_sound('miss')
        players[actual_player].darts_thrown += 1


    def display_segment(self):
        """
        Set if a message is shown to indicate the hit segment
        """
        return self.show_hit
