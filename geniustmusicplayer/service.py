from os import environ

from oscpy.server import OSCThreadServer
from kivy.core.audio import SoundLoader
from kivy.logger import Logger
from kivy.utils import platform
from kivy.clock import Clock
from kivy.app import App

from utils import Song, save_song, Playlist
from api import API
from db import Database


class OSCSever:
    def __init__(self, activity_server_address, port):
        self.osc = OSCThreadServer()
        self.osc.listen(port=port, default=True)
        self.activity_server_address = activity_server_address
        self.osc.bind(b'/get_pos', self.get_pos)
        self.osc.bind(b'/load', self.load)
        self.osc.bind(b'/play', self.play)
        self.osc.bind(b'/load_play', self.load_play)
        self.osc.bind(b'/seek', self.seek)
        self.osc.bind(b'/set_volume', self.set_volume)
        self.osc.bind(b'/stop', self.stop)
        self.osc.bind(b'/unload', self.unload)

        self.song = None
        self.api = API()
        self.db = Database()
        user = self.db.get_user()
        self.genres = user['genres']
        self.artists = user['artists']
        self.volume = user['volume']
        self.songs_path = user['songs_path']
        self.playlist = self.db.get_playlist()
        self.event = None

        self.load(self.playlist.current_track)

    def check_pos(self, *args):
        Logger.debug('SERVICE: pos check.')
        if self.song.length - self.song.get_pos() < 20:
            next_song = self.playlist.preview_next()
            if next_song is None or next_song.preview_file is None:
                if next_song is None:
                    self.playlist = self.get_new_playlist()
                    next_song = self.playlist.preview_next()
                Logger.debug('SERVICE: Preloading next song.')
                res = self.api.download_preview(next_song)
                next_song.preview_file = save_song(self.songs_path, next_song, res)
                self.db.update_track(next_song, 'preview_file', next_song.preview_file)

    def get_new_playlist(self):
        Logger.debug('SERVICE: getting new playlist.')
        req = self.api.get_recommendations(
            self.genres,
            self.artists,
            song_type='preview',
        )
        playlist = Playlist(req)
        self.db.update_playlist(playlist)
        self.osc.send_message(b'/set_playlist',
                              [playlist.to_json().encode()],
                              *self.activity_server_address)
        return playlist

    def get_pos(self, *values):
        pos = self.song.get_pos() if self.song else 0
        Logger.debug('SERVICE -> ACTIVITY: /pos %s', pos)
        self.osc.answer(b'/pos', [pos])

    def getaddress(self):
        return self.osc.getaddress()

    def load(self, song):
        Logger.debug('SERVER: Loading song.')
        song = Song.bytes_to_song(song)
        if song.preview_file is None:
            res = self.api.download_preview(song)
            song.preview_file = save_song(self.songs_path, song, res)
            self.db.update_track(song, 'preview_file', song.preview_file)
        self.song = SoundLoader.load(song.preview_file)
        self.song.song_object = song
        self.song.on_complete_callback = self.on_complete
        self.song.bind(state=self.on_state)
        self.playlist.set_current(song)
        self.db.update_current_track(song)

    def load_play(self, song, volume=None):
        Logger.debug('SERVICE: Loading and playing song.')
        self.song.stop()
        self.load(song)
        Logger.debug('SERVICE -> ACTIVITY: /playing 0.')
        values = [song.to_json().encode() if not isinstance(song, bytes) else song, 0]
        self.osc.send_message(b'/playing',
                              values,
                              *self.activity_server_address)
        self.play(0, volume if volume is not None else self.volume)

    def play(self, seek, volume):
        self.song.play()
        self.song.seek(seek)
        self.song.volume = volume
        if self.event:
            self.event.cancel()
        self.event = Clock.schedule_interval(self.check_pos, .5)
        Logger.debug('SERVICE: Playing song.')

    def stop(self, *values):
        Logger.debug('SERVICE: stopping song.')
        self.song.stop()
        if self.event:
            self.event.cancel()

    def seek(self, value):
        Logger.debug('SERVICE: seeking %s.', value)
        self.song.seek(value)

    def set_volume(self, value):
        Logger.debug('SERVER: setting song volume %s.', value)
        self.song.volume = self.volume = value

    def on_complete(self, *values):
        Logger.debug('SERVICE -> ACTIVITY: /set_complete')
        self.osc.send_message(b'/set_complete', [True], *self.activity_server_address)
        self.play_next()

    def play_next(self):
        Logger.debug('SERVICE: Playing next.')
        self.stop()
        if self.playlist.is_last:
            self.playlist = self.get_new_playlist()
        song = self.playlist.next()
        if song.preview_file is None:
            Logger.debug('SERVICE: Downloading song.')
            res = self.api.download_preview(song)
            song.preview_file = save_song(self.songs_path, song, res)
            self.db.update_track(song, 'preview_file', song.preview_file)
        self.load_play(song)

    def play_previous(self):
        Logger.debug('SERVICE: Playing previous.')
        if not self.playlist.is_first:
            self.stop()
            self.load_play(self.playlist.previous())

    def on_state(self, instance, value):
        Logger.debug('SERVICE -> ACTIVITY: /set_state %s', value)
        self.osc.send_message(
            b'/set_state',
            [value.encode()],
            *self.activity_server_address)
        if self.song.length - self.song.get_pos() < 0.2:
            self.on_complete()

    def unload(self, *values):
        pass  # self.song.unload()


class MyApp(App):
    def build(self, *args):
        if platform == 'android':
            from android_audio_player import SoundAndroidPlayer
            args = environ.get('PYTHON_SERVICE_ARGUMENT', '').split(',')
            Logger.debug('SERVICE: received args: %s', args)
            activity_address, port = args[:2], args[2]
            OSCSever(activity_address, port)
            SoundLoader.register(SoundAndroidPlayer)
        else:
            OSCSever(('127.0.0.1', 4999), 5000)
        return ""


if __name__ == '__main__':
    MyApp().run()
