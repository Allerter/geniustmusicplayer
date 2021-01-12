from datetime import timedelta
from math import ceil, floor
import os
from os.path import join

os.environ['KIVY_AUDIO'] = 'android'
os.environ['KIVY_IMAGE'] = 'pil,sdl2,gif'

from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.slider import MDSlider
from kivymd.uix.menu import MDDropdownMenu, RightContent
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ListProperty
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.storage.jsonstore import JsonStore
from kivy.core.audio import SoundLoader
from kivy.logger import Logger, LOG_LEVELS
from kivy.utils import platform
from kivy.loader import Loader

import start_page
from utils import log, switch_screen, create_snackbar
from api import API

Logger.setLevel(LOG_LEVELS['debug'])
# os.environ['KIVY_IMAGE'] = 'sdl2,gif'
# os.environ['KIVY_AUDIO'] = 'ffpyplayer'

if platform == 'android':
    from android_audio_player import SoundAndroidPlayer
    # from android.storage import primary_external_storage_path
    # from android.permissions import request_permissions, Permission
    # request_permissions([Permission.WRITE_EXTERNAL_STORAGE])
    # storage_path = primary_external_storage_path()
    from android.storage import app_storage_path
    storage_path = app_storage_path()
    SoundLoader.register(SoundAndroidPlayer)
else:
    storage_path = 'songs/'
    Window.size = (330, 650)


class Playlist:
    def __init__(self, tracks: list) -> None:
        self.tracks = tracks
        self._current = -1

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

    def __repr__(self):
        return f'Playlist(tracks={self.tracks!r}, current={self._current})'


# -------------------- Main Page --------------------
class PlaybackSlider(MDSlider):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(value=self.on_value)

    def on_value(self, instance, value):
        play_button = app.main_page.ids.play_button
        app.song.last_pos = self.value
        if (app.song.state == 'stop'
                and ceil(app.song.get_pos()) == ceil(app.song.length)):
            Logger.debug('Song: song ended. playing next')
            play_button.control(play_button, play_next=True)
        else:
            if abs(value - app.song.get_pos()) > 1:
                app.song.seek(value)
                play_button.update_track_current(value)


class VolumeSlider(MDSlider):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(value=self.on_value)

    @log
    def on_value(self, instance, value):
        app.volume = instance.value_normalized
        if app.song:
            app.song.volume = app.volume


class PlayButton(ButtonBehavior, Image):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(on_release=lambda instance: self.control(instance))
        app.play_button = self

    @log
    def load_song(self, song, data=None):
        # if not song.filename:
        #    song_file = requests.get(song.preview_url)
        #    mp3_filename = f'songs/{song.artist} - {song.name} preview.mp3'
        #    ogg_filename = mp3_filename[:-4] + '.ogg'
        #    with open(mp3_filename, 'wb') as f:
        #        f.write(song_file.content)
        #    ffmpeg.run(
        #        ffmpeg.output(
        #            ffmpeg.input(mp3_filename),
        #            ogg_filename)
        #    )
        #    song.filename = ogg_filename
        if data:
            song.preview_file = join(storage_path,
                                     f'{song.artist} - {song.name} preview.mp3')
            with open(song.preview_file, 'wb') as f:
                f.write(data)
            Logger.debug('load_song: %s', song.preview_file)

        app.song = SoundLoader.load(song.preview_file)
        app.song.song_object = song
        app.song.name = song.name
        app.song.artist = song.artist
        app.song.volume = app.volume
        app.song.cover_art = song.cover_art
        app.song.last_pos = 0
        app.main_page.edit_ui_for_song()
        app.playlist.set_current(song)
        self.play_track(song)

    @log
    def play_track(self, song, seek=0):
        if app.song:
            app.song.stop()
            if app.song.song_object not in app.history:
                app.history.append(app.playlist.current_track)

        if app.song is None or app.song.song_object != song:
            def call_load_song(*args):
                self.load_song(song, res.response)

            if song.preview_file:
                self.load_song(song)
            else:
                Logger.debug('play_track: downloading preview')
                app.main_page.ids.cover_art.source = 'images/loading_coverart.gif'
                trigger = Clock.create_trigger(call_load_song)
                res = app.api.download_preview(song, trigger=trigger)
            return

        app.song.play()
        app.song.seek(seek)
        self.source = 'images/stop2.png'
        self.event = Clock.schedule_interval(self.update_track_current, 1)
        Logger.debug('play_track: playing %s', song.name)

    @log
    def control(self, instance, **kwargs):
        play_next = kwargs.get('play_next')
        Logger.debug('control: play_next: %s | song_state: %s | app.song: %s',
                     play_next,
                     app.song.state if app.song else None,
                     True if app.song else False)

        if play_next or app.song is None or app.song.state == 'stop':
            if (play_next and app.playlist.is_last) or app.playlist.tracks == []:
                def retry(*args):
                    self.snackbar.dismiss()
                    self.retry_event.cancel()
                    self.control(instance, play_next=True)

                def get_tracks(*args):
                    if req.status_code == 200:
                        tracks = req.response['tracks']
                        app.playlist = Playlist(tracks)
                        self.control(instance, play_next=True)
                    else:
                        msg = "Failed to get playlist. Retrying in 3 seconds."
                        self.snackbar = create_snackbar(msg, retry)
                        self.retry_event = Clock.schedule_once(retry, 3)
                        self.snackbar.open()

                trigger = Clock.create_trigger(get_tracks)
                req = app.api.get_recommendations(
                    app.genres,
                    app.artists,
                    has_preview_url=True,
                    trigger=trigger,
                    async_request=True,
                )
            elif play_next or app.song is None:
                self.stop_song()
                song = app.playlist.next()
                Logger.debug('playing %s', song.name)
                self.play_track(song)
            else:
                Logger.debug('control: resuming song %s', app.song.name)
                self.play_track(app.song.song_object, seek=app.song.last_pos)
        else:
            app.song.last_pos = app.song.get_pos()
            app.song.stop()
            Logger.debug('control: stopped at %s', app.song.last_pos)
            self.source = "images/play2.png"
            self.event.cancel()

    @log
    def play_previous(self, instance):
        Logger.debug(
            'play_previous: PLAYLIST: current: %s | is_first: %s',
            app.playlist.current_track,
            app.playlist.is_first
        )
        if not app.playlist.is_first:
            self.stop_song()
            song = app.playlist.previous()
            self.play_track(song)

    @log
    def play_next(self, instance):
        Logger.debug(
            'play_next: PLAYLIST: current: %s | is_last: %s',
            app.playlist.current_track,
            app.playlist.is_first
        )
        self.stop_song()
        if app.playlist.is_last:
            app.play_button.control(instance, play_next=True)
        else:
            song = app.playlist.next()
            self.play_track(song)

    @log
    def stop_song(self):
        if app.song:
            app.song.stop()
            # app.song.unload() TODO: why does it make app crash?
            if app.song.song_object not in app.history:
                app.history.append(app.song.song_object)

    def update_track_current(self, *args):
        track_current = app.main_page.ids.track_current
        slider = app.main_page.ids.playback_slider

        if app.song:
            slider.value = app.song.get_pos()
            track_current.text = str(timedelta(
                seconds=slider.value
            ))[3:7]


class RightContentCls(RightContent):
    pass


def is_removable(song):
    return True if not app.song or song.name != app.song.name else False

class MainPage(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        global app
        app = MDApp.get_running_app()
        self.song = app.song
        Logger.debug('Playlist: Tracks: %s', app.playlist.tracks)
        menu_items = [
            {"right_content_cls": RightContentCls(),  # = if is_removable(i) else None,
             "text": i.name,
             "song": i
             } for i in app.playlist.tracks
        ]
        self.playlist_menu = MDDropdownMenu(
            caller=self.ids.playlist_button, items=menu_items, width_mult=4
        )

        self.playlist_menu.bind(on_release=self.play_from_playlist)

    @log
    def edit_ui_for_song(self):
        self.ids.track_length.text = str(timedelta(
            seconds=app.song.length)
        )[3:7]
        self.ids.playback_slider.max = app.song.length
        app.play_button.update_track_current(0)
        self.update_playlist_menu()
        self.update_cover_art()
        self.update_song_info()

    @log
    def remove_playlist_item(self, instance):
        items = app.main_page.playlist_menu.items
        for item in items:
            if item['right_content_cls'] == instance:
                removed_song = item['song']

        app.playlist.remove(removed_song)
        self.update_playlist_menu()

    @log
    def update_playlist_menu(self, *args):
        menu_items = [
            {"right_content_cls": RightContentCls() if is_removable(i) else None,
             "text": i.name,
             "song": i,
             "icon": 'play-outline' if i == app.song.song_object else None
             } for i in app.playlist.tracks
        ]
        self.playlist_menu.dismiss()
        self.playlist_menu = MDDropdownMenu(
            caller=self.ids.playlist_button, items=menu_items, width_mult=4,
            opening_time=0,
        )
        self.playlist_menu.bind(on_release=self.play_from_playlist)

    @log
    def play_from_playlist(self, instance, selected_item):
        track = app.playlist.track_by_name(selected_item.text)
        if track == app.playlist.current_track:  # track is already playing
            return
        app.play_button.play_track(track)

    @log
    def update_cover_art(self):
        self.ids.cover_art.source = app.song.cover_art

    @log
    def update_song_info(self):
        self.ids.title.text = app.song.name
        self.ids.artist.text = app.song.artist

    @log
    def seek(self, slider, motion, *args):
        touch = motion.pos
        if slider.collide_point(*touch):
            if app.song.state == 'stop':
                app.song.last_pos = slider.value
            else:
                app.song.last_pos = slider.value
                app.song.seek(slider.value)
            return True
        return False
# -------------------- App --------------------


class LoadingPage(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logo = Image(source="logo.png", pos=(800, 800))
        label = MDLabel(
            text='Loading...',
            pos=(logo.pos[0] + logo.size[0] + 5, logo.pos[1]))
        self.add_widget(logo)
        self.add_widget(label)
        animation = Animation(x=0, y=0, d=2)
        animation.start(logo)


class MainApp(MDApp):
    artists = ListProperty([])
    genres = ListProperty([])
    playlist = Playlist([])
    history = []
    store = JsonStore('preferences.json')
    volume = store['user'].get('volume', 50) if store.exists('user') else 50
    song = None
    main_page = None
    api = API()

    @log
    def build(self):
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.accent_palette = "Amber"
        Loader.loading_image = 'images/loading_coverart.gif'

        self.screen_manager = ScreenManager()
        # uncomment - p4a already has splash screen!
        # switch_screen(LoadingPage(), 'loading_page')
        # Clock.schedule_once(self.load_first_page, 4)
        self.load_first_page()
        return self.screen_manager

    @log
    def load_first_page(self, *args):
        # comment
        # switch_screen(start_page.StartPage(), 'start_page')
        # return
        if 'user' in self.store and self.store['user'].get('genres'):
            page = MainPage()
            user = self.store['user']
            app.genres = user['genres']
            app.artists = user['artists']
            app.volume = user['volume']
            page_name = 'main_page'
            app.main_page = page
        else:
            page = start_page.StartPage()
            page_name = 'start_page'
        switch_screen(page, page_name)


if __name__ == '__main__':
    app = MainApp()
    app.run()
