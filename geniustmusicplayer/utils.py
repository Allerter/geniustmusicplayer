import functools
import inspect
import json
from functools import wraps
from os.path import join

from kivy.uix.screenmanager import Screen
from kivy.logger import Logger
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.button import MDFlatButton


class Song:
    def __init__(self, id, name, artist, genres=None,
                 id_spotify=None, isrc=None, cover_art=None,
                 preview_url=None, download_url=None, preview_file=None,
                 download_file=None, date_favorited=None,):
        self.id = id
        self.name = name
        self.artist = artist
        self.genres = genres if genres else []
        self.id_spotify = id_spotify
        self.isrc = isrc
        self.cover_art = (cover_art
                          if cover_art is not None
                          else 'images/empty_coverart.png'
                          )
        self.preview_url = preview_url
        self.download_url = download_url
        self.preview_file = preview_file
        self.download_file = download_file
        self.date_favorited = date_favorited

    def to_dict(self):
        return dict(
            id=self.id,
            name=self.name,
            artist=self.artist,
            id_spotify=self.id_spotify,
            isrc=self.isrc,
            cover_art=self.cover_art,
            preview_url=self.preview_url,
            download_url=self.download_url,
            preview_file=self.preview_file,
            download_file=self.download_file,
            date_favorited=self.date_favorited,
        )

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def bytes_to_song(cls, song):
        if isinstance(song, bytes):
            song = cls(**json.loads(song.decode()))
        return song

    def __eq__(self, other):
        if isinstance(other, Song) and self.id == other.id:
            return True
        else:
            return False

    def __repr__(self):
        return f'Song(artist={self.artist!r}, song={self.name!r})'


class Playlist:
    def __init__(self, tracks: list, current=-1) -> None:
        self.tracks = tracks
        self._current = current

    @property
    def track_names(self):
        return [track.name for track in self.tracks]

    @property
    def is_first(self):
        return True if self._current == 0 else False

    @property
    def is_last(self):
        return True if self._current == len(self.tracks) - 1 else False

    @property
    def current_track(self):
        if self._current == -1:
            return None
        try:
            return self.tracks[self._current]
        except IndexError:
            return None

    def preview_next(self):
        if not self.is_last:
            track = self.tracks[self._current + 1]
        else:
            track = self.tracks[self._current]

        return track

    def next(self):
        if not self.is_last:
            self._current += 1

        return self.tracks[self._current]

    def previous(self):
        if self._current == -1:
            self._current += 1
        elif not self.is_first:
            self._current -= 1

        Logger.debug(
            'PLAYLIST: current: %s | track: %s, tracks: %s',
            self._current,
            self.tracks[self._current],
            self.tracks)
        return self.tracks[self._current]

    def remove(self, track):
        self.tracks.remove(track)

    def set_current(self, track):
        self._current = self.tracks.index(track)

    def track_by_name(self, track_name):
        for track in self.tracks:
            if track.name == track_name:
                return track

    def to_dict(self):
        tracks = [track.to_dict() for track in self.tracks]
        current = self._current if self._current != -1 else 0
        return dict(tracks=tracks, current=current)

    def to_json(self):
        return json.dumps(self.to_dict())

    def __repr__(self):
        return f'Playlist({len(self.tracks)} Tracks, current={self._current})'


def create_snackbar(text, callback):
    snackbar = Snackbar(
        text=text,
        snackbar_x="10dp",
        snackbar_y="10dp",
    )
    snackbar.size_hint_x = (
        Window.width - (snackbar.snackbar_x * 2)
    ) / Window.width
    snackbar.buttons = [
        MDFlatButton(
            text="RETRY" if callback is not None else "OK",
            text_color=(1, 1, 1, 1),
            on_release=callback if callback is not None else lambda *args: None,
        ),
    ]
    return snackbar


def get_class_that_defined_method(meth):
    if isinstance(meth, functools.partial):
        return get_class_that_defined_method(meth.func)
    if (inspect.ismethod(meth)
        or (inspect.isbuiltin(meth)
            and getattr(meth, '__self__', None) is not None
            and getattr(meth.__self__, '__class__', None))):
        for cls in inspect.getmro(meth.__self__.__class__):
            if meth.__name__ in cls.__dict__:
                return cls
        meth = getattr(meth, '__func__', meth)  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0],
                      None)
        if isinstance(cls, type):
            return cls
    return getattr(meth, '__objclass__', None)  # handle special descriptor objects


def log(func):
    """logs entering and exiting functions for debugging."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        cls = get_class_that_defined_method(func)
        if cls is not None:
            cls = cls.__name__
        # Logger.debug("Entering: %s.%s", cls, func.__name__)
        result = func(*args, **kwargs)
        # Logger.debug("Exiting: %s.%s (return value: %s)",
        #             cls, func.__name__, repr(result))
        return result

    return wrapper


@log
def save_favorites(favorites):
    save_keys(favorites=[song.to_dict() for song in favorites])


@log
def save_keys(**kwargs):
    app = MDApp.get_running_app()
    for key, value in kwargs.items():
        app.store['user'][key] = value
    app.store.put('user', **app.store['user'])


def save_song(songs_path, song, data, preview=True):
    song_name = clean_filename(
        f'{song.artist} - {song.name}' + ('preview' if preview else '')
    )
    filename = join(songs_path, f'{song_name}.mp3')
    with open(filename, 'wb') as f:
        f.write(data)
    return filename


def clean_filename(s):
    return "".join(
        i
        for i in s
        if i not in r"\/:*?<>|"
    )


@log
def switch_screen(page, name):
    screen = Screen(name=name)
    screen.add_widget(page)
    MDApp.get_running_app().screen_manager.switch_to(screen)
