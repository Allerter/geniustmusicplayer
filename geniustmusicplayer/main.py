from datetime import timedelta
from math import ceil, floor
import os
from os.path import join

# os.environ['KIVY_AUDIO'] = 'android'
os.environ['KIVY_IMAGE'] = 'pil,sdl2,gif'

from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.slider import MDSlider
from kivymd.uix.menu import MDDropdownMenu, RightContent
from kivymd.uix.button import MDIconButton
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ListProperty, BooleanProperty, NumericProperty
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.storage.jsonstore import JsonStore
from kivy.core.audio import SoundLoader
from kivy.logger import Logger, LOG_LEVELS
from kivy.utils import platform
from kivy.loader import Loader
from kivy.utils import get_color_from_hex

import start_page
from utils import log, switch_screen, create_snackbar
from api import API, Song

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
    storage_path = ''
    Window.size = (330, 650)

songs_path = join(storage_path, 'songs')
if not os.path.isdir(songs_path):
    Logger.info('created songs directory')
    os.mkdir(songs_path)


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

    def __repr__(self):
        return f'Playlist({len(self.tracks)} Tracks, current={self._current})'


@log
def save_keys(**kwargs):
    for key, value in kwargs.items():
        app.store['user'][key] = value
    app.store.put('user', **app.store['user'])


def save_song(song, data):
    song_name = "".join(
        i
        for i in f'{song.artist} - {song.name} preview'
        if i not in r"\/:*?<>|"
    )
    filename = join(songs_path, f'{song_name}.mp3')
    with open(filename, 'wb') as f:
        f.write(data)
    return filename


def remove_songs(files):
    for file in files:
        if os.path.isfile(file) or os.path.islink(file):
            try:
                os.unlink(file)
                Logger.debug('FILE: Removed "%s"', file)
            except Exception as e:
                Logger.error('FILE: Failed to delete "%s". Reason: %s', file, e)

# -------------------- Main Page --------------------
class PlaybackSlider(MDSlider):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(value=self.on_value)
        # TODO: by using these, slider value won't update automatically
        # how do I set it myself?
        # self.bind(on_touch_down=self.stop_slider_update)
        #  self.bind(on_touch_up=self.start_slider_update)

    def stop_slider_update(self, slider, motion, *args):
        touch = motion.pos
        play_button = app.play_button

        if slider.collide_point(*touch):
            if app.song and app.song.state == 'stop':
                app.song.last_pos = slider.value
            elif app.song:
                play_button.event.cancel()
            return True
        return False

    def start_slider_update(self, slider, motion, *args):
        touch = motion.pos
        play_button = app.play_button

        if slider.collide_point(*touch):
            if app.song and app.song.state == 'stop':
                app.song.last_pos = slider.value
            elif app.song:
                play_button.event = Clock.schedule_interval(
                    play_button.update_track_current, 1
                )
            return True
        return False

    def on_value(self, instance, value):
        play_button = app.main_page.ids.play_button
        app.song.last_pos = self.value
        song_pos = app.song.get_pos()
        if abs(value - song_pos) > 1:
            app.song.seek(value)
            play_button.update_track_current(value)
        elif app.song.length - song_pos < 20:
            def save_preview(*args):
                if req.status_code == 200:
                    next_song.preview_file = save_song(next_song, req.response)
                    Logger.debug('SONG PRELOAD: download successful')
                else:
                    next_song.preview_file = None
                    Logger.debug('SONG PRELOAD: download failed')
            # pre-download next song
            next_song = app.playlist.preview_next()
            if next_song.preview_file is None:
                next_song.preview_file = 'downloading'
                Logger.info('SONG PRELOAD: downloading next song')
                trigger = Clock.create_trigger(save_preview)
                req = app.api.download_preview(next_song, trigger=trigger)


class VolumeSlider(MDSlider):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_value = 0
        self.bind(value=self.on_value)

    @log
    def on_value(self, instance, value):
        self.last_value = app.volume
        app.volume = instance.value_normalized
        if app.song:
            app.song.volume = app.volume


class PlayButton(MDIconButton):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(on_release=lambda instance: self.control(instance))
        self.event = None
        self.snackbar = None
        app.play_button = self

    @log
    def check_end(self, *args):
        if app.song.length - app.song.get_pos() < 0.2:
            self.play_next(self)

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
            song.preview_file = save_song(song, data)

        Logger.debug('load_song: %s', song.preview_file)
        app.song = SoundLoader.load(song.preview_file)
        app.song.bind(state=self.check_end)
        app.song.song_object = song
        app.song.name = song.name
        app.song.artist = song.artist
        app.song.volume = app.volume
        if song in app.favorites:
            app.main_page.favorite_button.favorited = True
        else:
            app.main_page.favorite_button.favorited = False
        app.song.cover_art = song.cover_art
        app.song.last_pos = 0
        app.main_page.edit_ui_for_song()
        app.playlist.set_current(song)

    @log
    def play_track(self, song, seek=0):
        if app.song:
            self.stop_song()

        if app.song is None or app.song.song_object != song:
            def call_load_song(*args):
                if self.snackbar:
                    self.snackbar.dismiss()
                if res.status_code == 200:
                    self.load_song(song, res.response)
                    self.play_track(song)
                else:
                    song.preview_file = None
                    msg = 'Dowloading Song Failed. Retrying...'
                    self.snackbar = create_snackbar(
                        msg,
                        lambda *args: self.play_track(song)
                    )
                    Clock.schedule_once(lambda *args: self.play_track(song), 1)
                    self.snackbar.open()

            if song.preview_file and song.preview_file != 'downloading':
                self.load_song(song)
            else:
                Logger.debug('play_track: downloading preview')
                app.main_page.ids.cover_art.source = 'images/loading_coverart.gif'
                trigger = Clock.create_trigger(call_load_song)
                res = app.api.download_preview(song, trigger=trigger)
                return

        app.song.play()
        app.song.seek(seek)
        app.song.volume = app.volume
        Logger.info('VOLUME %s', app.song.volume)
        self.source = 'images/stop2.png'
        self.icon = 'pause'
        if self.event:
            self.event.cancel()
        self.event = Clock.schedule_interval(self.update_track_current, 1)
        Logger.info('play_track: playing %s', song.name)

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
                        remove_songs(
                            [song.preview_file
                             for song in app.playlist.tracks
                             if song not in app.favorites and song.preview_file]
                        )
                        tracks = req.response
                        app.playlist = Playlist(tracks)
                        save_keys(playlist=app.playlist.to_dict())
                        self.control(instance, play_next=True)
                    else:
                        msg = "Failed to get playlist.\nRetrying in 3 seconds."
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
            self.icon = 'play'
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

            # if app.song.song_object not in app.history:
            #    app.history.append(app.song.song_object)

    def update_track_current(self, *args):
        track_current = app.main_page.ids.track_current
        slider = app.main_page.ids.playback_slider

        if app.song:
            slider.value = app.song.get_pos()
            track_current.text = str(timedelta(
                seconds=slider.value
            ))[3:7]


class FavoriteButton(MDIconButton):
    favorited = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(on_release=self.favorite)
        self.icon = "heart-outline"

    def on_favorited(self, *args):
        if self.favorited:
            self.icon = 'heart'
        else:
            self.icon = 'heart-outline'

    def favorite(self, *args):
        if not self.favorited:
            self.favorited = True
            app.favorites.append(app.song.song_object)
        else:
            self.favorited = False
            app.favorites.remove(app.song.song_object)
        save_keys(favorites=[song.to_dict() for song in app.favorites])


class RightContentCls(RightContent):
    def __init__(self, **kwargs):
        song = kwargs.pop('song')
        super().__init__(**kwargs)
        if song.id_spotify:
            spotify_button = MDIconButton(
                icon='spotify',
                user_font_size="20sp",
                pos_hint={"center_y": .5},
                theme_text_color="Custom",
                text_color=get_color_from_hex("#1DB954"),
                on_release=lambda *args: create_snackbar(
                    'Spotify',
                    lambda *args: None).open(),
            )
            self.add_widget(spotify_button)


def is_removable(song):
    return True if not app.song or song.name != app.song.name else False

class MainPage(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        global app
        app = MDApp.get_running_app()
        self.song = app.song
        self.playlist_menu = None
        # menu_items = [
        #    {"right_content_cls": RightContentCls(song=i),
        #     "text": i.name,
        #     "song": i
        #     } for i in app.playlist.tracks
        # ]
        # self.playlist_menu = MDDropdownMenu(
        #    caller=self.ids.playlist_button, items=menu_items, width_mult=4
        # )
        # self.playlist_menu.bind(on_release=self.play_from_playlist)

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
            {"right_content_cls": RightContentCls(song=i) if is_removable(i) else None,
             "text": i.name,
             "song": i,
             "icon": 'play-outline' if i == app.song.song_object else None
             } for i in app.playlist.tracks
        ]
        if self.playlist_menu:
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

# -------------------- App --------------------


class LoadingPage(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logo = Image(source="images/icon.png", pos=(800, 800))
        label = MDLabel(
            text='Loading...',
            pos=(logo.pos[0] + logo.size[0] + 5, logo.pos[1]))
        self.add_widget(logo)
        self.add_widget(label)
        # animation = Animation(x=0, y=0, d=2)
        # animation.start(logo)


class MainApp(MDApp):
    artists = ListProperty([])
    genres = ListProperty([])
    playlist = Playlist([])
    store = JsonStore('preferences.json')
    favorites = ([Song(**x) for x in store['user']['favorites']]
                 if store.exists('user') else [])
    volume = store['user']['volume'] if store.exists('user') else 50
    song = None
    main_page = None
    api = API()

    @log
    def build(self):
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.accent_palette = "Amber"
        self.theme_cls.theme_style = "Light"
        Loader.loading_image = 'images/loading_coverart.gif'

        self.screen_manager = ScreenManager()
        switch_screen(LoadingPage(), 'loading_page')
        self.load_first_page()
        return self.screen_manager

    @log
    def load_first_page(self, *args):
        if 'user' in self.store and self.store['user'].get('genres'):
            page = MainPage()
            page_name = 'main_page'
            app.main_page = page
            user = self.store['user']
            app.genres = user['genres']
            app.artists = user['artists']
            app.volume = user['volume']
            app.main_page.ids.volume_slider.value = app.volume * 100
            # get playlist
            playlist = Playlist(
                [Song(**x) for x in user['playlist']['tracks']],
                current=user['playlist']['current']
            )
            app.playlist = playlist
            # load song
            song = self.playlist.current_track
            if song.preview_file is None:
                res = self.api.download_preview(song, async_request=False)
                self.play_button.load_song(song, res.response)
            else:
                self.play_button.load_song(song)
            app.song.last_pos = user['playlist'].get('last_pos', 0)
            # update track current
            slider = app.main_page.ids.playback_slider
            slider.value = app.song.last_pos
            app.main_page.ids.track_current.text = str(timedelta(
                seconds=slider.value
            ))[3:7]
        else:
            page = start_page.StartPage()
            page_name = 'start_page'
        switch_screen(page, page_name)

    def on_volume(self, *args):
        if app.song:
            app.song.volume = app.volume

    def on_stop(self):
        song_pos = app.song.get_pos()
        playlist = app.playlist.to_dict()
        playlist.update({'last_pos': song_pos})
        save_keys(playlist=playlist, volume=app.volume)


if __name__ == '__main__':
    app = MainApp()
    app.run()
