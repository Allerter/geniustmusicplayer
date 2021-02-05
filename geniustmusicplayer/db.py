import sqlite3
from functools import wraps
from contextlib import closing
from typing import Any, List, TypeVar, Callable, Optional, Tuple, Union, Dict

from utils import Song, Playlist

RT = TypeVar("RT")


def get_cursor(func: Callable[..., RT]) -> Callable[..., RT]:
    """Returns a DB cursor for the wrapped functions"""

    @wraps(func)
    def wrapper(self, *args, **kwargs) -> RT:
        sqlite3.register_adapter(bool, int)
        sqlite3.register_converter("BOOLEAN", lambda v: bool(int(v)))
        con = sqlite3.connect('user.db', isolation_level=None, detect_types=sqlite3.PARSE_DECLTYPES)
        with closing(con.cursor()) as cursor:
            return func(self, *args, **kwargs, cursor=cursor)

    return wrapper


class Database:
    """Database class for all communications with the database."""

    def __init__(self):
        self.playlist_table = 'playlist'
        self.favorites_table = 'favorites'
        self.user_table = 'user'

    @get_cursor
    def insert(
        self,
        *data: Tuple[bool, str, str, Optional[str]],
        table,
        cursor: Any
    ) -> None:
        """Inserts data into database.

        Args:
            chat_id (int): Chat ID.
            data (tuple): data fields for user.
            table (str): table to insert into.
            cursor (Any): database cursor.
        """
        values = data
        if table == self.user_table:
            query = f"""INSERT INTO user VALUES (?,?,?,?,?,?,?);"""
        elif table == self.favorites_table:
            query = f"""INSERT INTO favorites VALUES (?,?,?,?,?,?,?,?,?,?,?);"""
        elif table == self.playlist_table:
            query = f"""INSERT INTO playlist VALUES (?,?,?,?,?,?,?,?,?,?,?,?);"""
        else:
            raise ValueError(f"Unknown table {table}")

        cursor.execute(query, values)

    @get_cursor
    def _update_playlist(
        self,
        column: str,
        id,
        data,
        cursor = None,
    ):
        query = f"UPDATE playlist SET {column} = ? WHERE id == {id};"
        values = (data,)
        cursor.execute(query, values)

    @get_cursor
    def _update_user(
        self,
        column: str,
        data,
        cursor = None,
    ):
        query = f"UPDATE user SET {column} = ?"
        values = (data,)
        cursor.execute(query, values)

    @get_cursor
    def _execute(self, query, cursor=None):
        cursor.execute(query)

    def update_dark_mode(self, value):
        self._update_user('dark_mode', value)

    def update_play_mode(self, value):
        self._update_user('play_mode', value)

    def update_genres(self, genres):
        self._update_user('genres', ",".join(genres))

    def update_artists(self, artists):
        self._update_user('artists', ",".join(artists))

    def update_songs_path(self, value):
        self._update_user('songs_path', value)

    def update_volume(self, value):
        self._update_user('volume', value)

    def update_last_pos(self, value):
        self._update_user('last_pos', value)

    @get_cursor
    def update_current_track(self, track, cursor=None):
        cursor.execute("""UPDATE playlist SET current = 0 WHERE current = 1;""")
        self._update_playlist('current', track.id, True)

    def _track_to_db(self, track, current=None):
        track = [
            track.id, track.name, track.artist, track.id_spotify,
            track.isrc, track.cover_art, track.preview_url,
            track.download_url, track.preview_file,
            track.download_file,
            track.date_favorited
        ]
        if current is not None:
            track.append(current)
        return track

    def _db_to_track(self, track):
        return Song(id=track[0],
                    name=track[1],
                    artist=track[2],
                    id_spotify=track[3],
                    isrc=track[4],
                    cover_art=track[5],
                    preview_url=track[6],
                    download_url=track[7],
                    preview_file=track[8],
                    download_file=track[9],
                    date_favorited=track[10],)

    @get_cursor
    def update_playlist(self, playlist, cursor=None):
        cursor.execute("""DELETE FROM playlist;""")
        query = """INSERT INTO playlist VALUES (?,?,?,?,?,?,?,?,?,?,?,?);"""
        values = [self._track_to_db(track, current=True if i == 0 else False)
                  for i, track in enumerate(playlist.tracks)]
        cursor.executemany(query, values)

    @get_cursor
    def remove_playlist_track(self, track, cursor=None):
        cursor.execute(f"""DELETE FROM playlist where id =  {track.id};""")

    @get_cursor
    def remove_favorites_track(self, track, cursor=None):
        cursor.execute(f"""DELETE FROM favorites where id = {track.id};""")

    @get_cursor
    def add_playlist_track(self, track, cursor=None):
        query = """INSERT INTO playlist VALUES (?,?,?,?,?,?,?,?,?,?,?,?);"""
        values = self._track_to_db(track, current=False)
        cursor.execute(query, values)

    @get_cursor
    def add_favorites_track(self, track, cursor=None):
        query = """INSERT INTO favorites VALUES (?,?,?,?,?,?,?,?,?,?,?);"""
        values = self._track_to_db(track, current=None)
        cursor.execute(query, values)

    @get_cursor
    def delete_user(self, cursor=None):
        for table in ('user', 'favorites', 'playlist'):
            query = f"""DROP TABLE {table};"""
            cursor.execute(query)

    @get_cursor
    def get_playlist(self, cursor=None):
        query = """SELECT * FROM playlist ORDER BY rowid"""
        cursor.execute(query)
        tracks = cursor.fetchall()
        for i, track in enumerate(tracks):
            if track[-1] is True:
                current = i
                break
        else:
            raise ValueError("Playlist didn't have current track")
        return Playlist(tracks=[self._db_to_track(track) for track in tracks],
                        current=current)

    @get_cursor
    def get_favorites(self, cursor=None):
        query = """SELECT * FROM favorites"""
        cursor.execute(query)
        tracks = cursor.fetchall()
        return [self._db_to_track(track) for track in tracks]

    @get_cursor
    def get_user(self, cursor=None):
        query = """SELECT * FROM user"""
        try:
            cursor.execute(query)
            user = cursor.fetchone()
        except sqlite3.OperationalError as e:
            # TODO: Log e
            return None
        return dict(
            genres=user[1].split(','),
            artists=user[2].split(','),
            dark_mode=user[3],
            play_mode=user[4],
            songs_path=user[5],
            volume=user[6],
            last_pos=user[7],
        )

    @get_cursor
    def get_track(self, id, cursor=None):
        values = (id,)
        query = f"SELECT * FROM playlist where id = ?;"
        cursor.execute(query, values)
        return self._db_to_track(cursor.fetchone())

    @get_cursor
    def update_track(self, track, column, value, cursor=None):
        values = (value,)
        for table in ('playlist', 'favorites'):
            query = f"UPDATE {table} SET {column} = ? WHERE id = {track.id};"
            cursor.execute(query, values)

    @get_cursor
    def initialize(self, genres, artists, songs_path, playlist, cursor=None):
        # User
        cursor.execute('''CREATE TABLE user
                     (id INTEGER primary key,
                      genres TEXT NOT NULL,
                      artists TEXT DEFAULT '',
                      dark_mode boolean DEFAULT 0,
                      play_mode TEXT DEFAULT 'any_file'
                        CHECK(play_mode in ('any_file', 'preview', 'full')),
                      songs_path TEXT,
                      volume REAL DEFAULT 0.50 CHECK(volume >= 0 AND volume <= 1),
                      last_pos INTEGER DEFAULT 0 CHECK(last_pos >= 0)
                      )
                 ''')
        user = (0, ",".join(genres), ",".join(artists), songs_path)
        query = 'INSERT INTO user (id, genres, artists, songs_path) VALUES (?,?,?,?)'
        cursor.execute(query, user)

        # Favorites
        cursor.execute('''CREATE TABLE favorites
                     (id integer UNIQUE,
                      name TEXT,
                      artist TEXT,
                      id_spotify TEXT unique,
                      isrc TEXT unique,
                      cover_art TEXT,
                      preview_url TEXT,
                     download_url TEXT,
                     preview_file TEXT,
                     download_file TEXT,
                     date_favorited real)
                 ''')

        # Playlist
        cursor.execute('''CREATE TABLE playlist
                     (id integer UNIQUE,
                      name TEXT,
                      artist TEXT,
                      id_spotify TEXT unique,
                      isrc TEXT unique,
                      cover_art TEXT,
                      preview_url TEXT,
                     download_url TEXT,
                     preview_file TEXT,
                     download_file TEXT,
                     date_favorited real,
                     current boolean DEFAULT 0
                     )
                     ''')
        self.update_playlist(playlist)
