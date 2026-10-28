
import sqlite3
import os

from include import cpaths
#

class Scores:
    """
    Scores' class
    """
    def __init__(self, config, logs):
        self.config = config
        self.logs = logs
        self.userpath = os.path.expanduser('~')
        self.pathdir = cpaths.user_dir()
        self.db = f'{self.pathdir}/scores.db'
        self.DBChecks()
        self.game_name = ''
        self.game_options = None
        self.nb_players = None
        self.game_id = ''

    def connect(self):
        """
        Create a database connection to the SQLite database
           specified by the db_file
           :param db_file: database file
           :return: Connection object or None
        """
        try:
            self.cx = sqlite3.connect(self.db)
        except Exception as exception:
            self.logs.error(f"{exception}")

    def DBChecks(self):
        """
        Check db
        """
        if not os.path.exists(self.pathdir):
            os.makedirs(self.pathdir)
        # Connect to db
        self.connect()
        # Purge if requested
        if self.config.get_value('SectionAdvanced', 'clear-local-db'):
            self.logs.warning(f"Squeezing any existing table in {self.db}")
            sql='DROP table scores'
            cur = self.cx.cursor()
            cur.execute(sql)
            sql='DROP table games'
            cur = self.cx.cursor()
            cur.execute(sql)
           # Create structure if needed
        sql = """
              CREATE TABLE IF NOT EXISTS scores
              (id INTEGER PRIMARY KEY AUTOINCREMENT,
              game_id INTEGER,
              scorename TEXT,
              score FLOAT,
              playername TEXT)
              """
        cur = self.cx.cursor()
        cur.execute(sql)
        self.cx.commit()


        sql = """
           CREATE TABLE IF NOT EXISTS games
           (  id INTEGER PRIMARY KEY AUTOINCREMENT,
              date DATETIME,
              gamename TEXT,
              gameoptions TEXT,
              nbplayers INT
           )
           """
        cur = self.cx.cursor()
        cur.execute(sql)
        self.cx.commit()

        if self.cx:
            self.cx.close()

    def add_game(self, data):
        """
        Add new game
        """
        self.game_name = data['game_name']
        self.game_options = data['game_options']
        self.nb_players = data['nb_players']
        self.connect()
        # Replaced CURRENT_TIMESTAMP by datetime('now','localtime'),
        sql = """
              INSERT INTO games (
              date,
              gamename,
              gameoptions,
              nbplayers)
              VALUES (
              datetime('now','localtime'),
              ?, ?, ?
              )
              """

        # Get cursor
        cur = self.cx.cursor()
        # Exsecute query (parametres lies : une apostrophe dans un nom ne casse plus la requete)
        cur.execute(sql, (str(self.game_name), str(self.game_options), self.nb_players))
        # Get last inserted id
        game_id = cur.lastrowid
        # Commit changes
        self.cx.commit()
        # Close cx if its still open
        if self.cx:
            self.cx.close()
        self.game_id = game_id
        return game_id

    def add_score(self, data):
        """
        add score
        """
        score_name = data['score_name']
        score = data['score']
        player_name = data['player_name']

        sql = """
              INSERT INTO scores (
              game_id,
              scorename,
              score,
              playername)
              VALUES (?, ?, ?, ?)
              """

        self.connect()
        # Get cursor
        cur = self.cx.cursor()
        # Exsecute query
        cur.execute(sql, (str(self.game_id), str(score_name), str(score), str(player_name)))
        # Commit changes
        self.cx.commit()
        # Close cx if its still open
        if self.cx:
            self.cx.close()

    def get_score_table(self, score_name, orderby, current=False):
        """
        return scores' table
        """
        self.connect()
        #
        # orderby ne peut pas etre un parametre SQL : on n'accepte que ASC / DESC
        orderby = str(orderby).strip().upper()
        if orderby not in ('ASC', 'DESC'):
            raise ValueError(f"orderby must be ASC or DESC, got {orderby!r}")
        params = [str(self.game_id), str(self.game_options), str(self.game_name), str(score_name)]
        if current:
            sql_this_game_only = "AND games.id=?"
            params.append(str(self.game_id))
        else:
            sql_this_game_only = ""
        #
        sql = f"""
              SELECT
                 CASE games.id
                    WHEN ? THEN 1
                    ELSE 0
                 END hiscore,
                 date,
                 playername,
                 score
              FROM scores
              LEFT JOIN games on scores.game_id=games.id
              WHERE gameoptions = ?
              AND gamename = ?
              AND scorename = ?
              {sql_this_game_only}
              ORDER BY score {orderby}
              LIMIT 12
              """

        # Get cursor
        cur = self.cx.cursor()
        # Exsecute query
        cur.execute(sql, params)
        # Get rows
        rows = cur.fetchall()

        return rows
