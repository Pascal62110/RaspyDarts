"""
Favorites fav1, fav2... (docs/menu/menus.md, section 13) : a game, its options, the number of
players planned and how the players are chosen. Created in the game (screen of the options of
a game), kept in ~/.raspydarts/favorites.yaml ; the files of menus only place them
(action favorite:fav1)
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
# How the players of a favorite are chosen
MODES = ('choose', 'generic', 'last')


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
        if yaml is None:
            raise RuntimeError('PyYAML is missing')
        data = self.read()
        data[str(name)] = {'game': str(game).replace(' ', '_'), 'options': dict(options), 'players': int(players),
                           'mode': mode, 'names': [str(player) for player in names] if mode == 'choose' else []}
        ordered = {key: data[key] for key in sorted(data, key=lambda key: (len(key), key))}
        temporary = f'{self.path}.tmp'
        with open(temporary, 'w', encoding='utf-8') as file:
            yaml.dump(ordered, file, Dumper=DUMPER, allow_unicode=True, sort_keys=False, default_flow_style=False)
        os.replace(temporary, self.path)
        self.logs.info(f"Favorites : {name} saved ({game}, {players} players, {mode})")

    @staticmethod
    def players_for(favorite, last_players, generic_name):
        '''
        Players of a favorite : (players, warning) ; warning : 'too-many' or 'too-few' when
        the last players do not match the number planned (mode last)
        '''
        count = favorite['players']
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
