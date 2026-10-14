
"""
Where RaspyDarts is installed and where the user keeps his configuration

Nothing is hard coded any more :
- the game works from the folder where it is installed (/raspydarts, formerly /pydarts)
- the user's folder is ~/.raspydarts ; installations made before the renaming keep
  their ~/.pydarts, which is used as it is
- the configuration file is raspydarts.cfg ; a pydarts.cfg is converted
"""

import os
import shutil

# Folder of the game : the one which contains include/
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

USER_DIR_NAME = '.raspydarts'
OLD_USER_DIR_NAME = '.pydarts'
CONFIG_NAME = 'raspydarts.cfg'
TROPHIES_NAME = 'players_data.json'
OLD_CONFIG_NAME = 'pydarts.cfg'

def user_home():
    """
    Home of the user who runs the game, even when launched with sudo
    """
    return os.path.expanduser('~' + os.environ.get('SUDO_USER', ''))

def user_dir():
    """
    Folder of the user's configuration, themes and scores
    """
    new_dir = os.path.join(user_home(), USER_DIR_NAME)
    old_dir = os.path.join(user_home(), OLD_USER_DIR_NAME)
    if not os.path.isdir(new_dir) and os.path.isdir(old_dir):
        return old_dir
    return new_dir

def trophies_file():
    """
    Trophies and statistics of the players : in the user's folder, with the scores and the
    configuration (kept by updates and backups). A file left in the folder of the game by a
    previous version is moved there.
    """
    new_file = os.path.join(user_dir(), TROPHIES_NAME)
    old_file = os.path.join(ROOT_DIR, TROPHIES_NAME)
    if not os.path.exists(new_file) and os.path.exists(old_file):
        try:
            os.makedirs(user_dir(), exist_ok=True)
            shutil.move(old_file, new_file)
        except OSError:
            return old_file
    return new_file

def config_file():
    """
    Configuration file. A pydarts.cfg is renamed raspydarts.cfg when it is the only one,
    or the most recent (a configuration dropped by the user replaces the current one)
    """
    new_file = os.path.join(user_dir(), CONFIG_NAME)
    old_file = os.path.join(user_dir(), OLD_CONFIG_NAME)
    if os.path.isfile(old_file):
        if not os.path.isfile(new_file) or os.path.getmtime(old_file) > os.path.getmtime(new_file):
            try:
                os.replace(old_file, new_file)
            except OSError:
                return old_file
    return new_file

def usable_dir(path, default):
    """
    Return path if it can be used, else default : a configuration made for another
    user (/home/pi/Pictures) must go on working after a reinstallation
    """
    path = str(path)
    if os.path.isdir(path) or os.access(os.path.dirname(path.rstrip('/')), os.W_OK):
        return path
    return default

def relocate(path):
    """
    Return where a file is in this installation when it was saved with the absolute
    path of another one (/home/pi/.pydarts/themes/x/font/y.ttf, /pydarts/fonts/z.ttf)
    """
    path = str(path)
    if os.path.exists(path):
        return path
    for marker, base in ((f'/{OLD_USER_DIR_NAME}/', user_dir()), (f'/{USER_DIR_NAME}/', user_dir()),
                         ('/pydarts/', ROOT_DIR), ('/raspydarts/', ROOT_DIR)):
        if marker in path:
            candidate = os.path.join(base, path.split(marker, 1)[1])
            if os.path.exists(candidate):
                return candidate
    return path
