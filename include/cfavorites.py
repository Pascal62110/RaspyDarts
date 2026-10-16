"""
Favorites (docs/menu/menus.md, section 13), kept in ~/.raspydarts/favorites.yaml :
- the options of the favorite games (screen Jeux favoris) : such a game starts without its
  screen of options ;
- the buttons fav1, fav2... of the main menu : a game, its options, the number of players
  planned and how the players are chosen. The files of menus only place them (action
  favorite:fav1)
"""

import os

from include import cpaths
from include import cmenus

try:
    import yaml
    LOADER = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
    DUMPER = getattr(yaml, 'CSafeDumper', yaml.SafeDumper)
except ImportError:
    yaml = None

FILE_NAME = 'favorites.yaml'
# Favorites which can be saved : fav1 to fav9 (F1 to F9 in the screen which saves them)
SLOTS = 9
# Key of the file holding the options of the favorite games (not a button fav1...)
GAMES = 'games'
# How the players of a favorite are chosen (ask : in the screen of the players, at its launch)
MODES = ('choose', 'generic', 'last', 'ask')


class Favorites:
    '''
    The favorites saved
    '''

    def __init__(self, logs):
        self.logs = logs
        self.path = os.path.join(cpaths.user_dir(), FILE_NAME)

    def read(self):
        '''
        All the favorites of the file : {name : favorite}
        '''
        if yaml is None or not os.path.isfile(self.path):
            return {}
        try:
            with open(self.path, encoding='utf-8') as file:
                data = yaml.load(file, Loader=LOADER) or {}
        except Exception as error:    # pylint: disable=broad-except
            self.logs.warning(f"Favorites : {self.path} not read ({error})")
            return {}
        return data if isinstance(data, dict) else {}

    def get(self, name):
        '''
        A favorite whose game still exists, None if it is empty (or its game unknown)
        '''
        favorite = self.read().get(str(name))
        if not isinstance(favorite, dict):
            return None
        game = str(favorite.get('game') or '')
        if cmenus.game_category(game) is None:
            if game:
                self.logs.warning(f"Favorites : unknown game '{game}' in {name}")
            return None
        mode = str(favorite.get('mode') or 'last')
        try:
            players = max(1, int(favorite.get('players') or 1))
        except (TypeError, ValueError):
            players = 1
        names = [str(player) for player in cmenus.as_list(favorite.get('names'))]
        return {'game': game, 'category': cmenus.game_category(game), 'options': dict(favorite.get('options') or {}),
                'players': players, 'mode': mode if mode in MODES else 'last', 'names': names}

    def save(self, name, game, options, players, mode, names):
        '''
        Saves a favorite (the others are kept)
        '''
        data = self.read()
        data[str(name)] = {'game': str(game).replace(' ', '_'), 'options': dict(options), 'players': int(players),
                           'mode': mode, 'names': [str(player) for player in names] if mode == 'choose' else []}
        self.write(data)
        self.logs.info(f"Favorites : {name} saved ({game}, {players} players, {mode})")

    def game_options(self, game):
        '''
        Options defined for a favorite game (screen Jeux favoris), None if none
        '''
        games = self.read().get(GAMES)
        options = games.get(str(game).replace(' ', '_')) if isinstance(games, dict) else None
        return dict(options) if isinstance(options, dict) else None

    def set_games_options(self, changes):
        '''
        Options of favorite games : {game : options, or None to remove them}
        '''
        data = self.read()
        games = data.get(GAMES) if isinstance(data.get(GAMES), dict) else {}
        for game, options in changes.items():
            key = str(game).replace(' ', '_')
            if options is None:
                games.pop(key, None)
            else:
                games[key] = dict(options)
        data[GAMES] = games
        self.write(data)
        self.logs.info(f"Favorites : options of favorite games {sorted(changes)} saved")

    def write(self, data):
        '''
        The file written whole (the options of the games first, then fav1, fav2...)
        '''
        if yaml is None:
            raise RuntimeError('PyYAML is missing')
        ordered = {key: data[key] for key in sorted(data, key=lambda key: (key != GAMES, len(key), key))}
        temporary = f'{self.path}.tmp'
        with open(temporary, 'w', encoding='utf-8') as file:
            yaml.dump(ordered, file, Dumper=DUMPER, allow_unicode=True, sort_keys=False, default_flow_style=False)
        os.replace(temporary, self.path)

    @staticmethod
    def players_for(favorite, last_players, generic_name):
        '''
        Players of a favorite : (players, warning) ; warning : 'too-many' or 'too-few' when
        the last players do not match the number planned (mode last). Players None : chosen
        in the screen of the players (mode ask)
        '''
        count = favorite['players']
        if favorite['mode'] == 'ask':
            return None, None
        if favorite['mode'] == 'choose' and favorite['names']:
            return favorite['names'][:], None
        if favorite['mode'] == 'generic' or not last_players:
            return [f"{generic_name} {index}" for index in range(1, count + 1)], None
        last = list(last_players)
        if len(last) > count:
            return last[:count], 'too-many'
        if len(last) < count:
            return last, 'too-few'
        return last, None
