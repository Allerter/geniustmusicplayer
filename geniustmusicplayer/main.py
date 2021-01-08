from datetime import timedelta
from math import ceil

import ffmpeg
import requests
from kivymd.app import MDApp
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
from utils import log, switch_screen
from api import API, Song
Logger.setLevel(LOG_LEVELS['debug'])
# os.environ['KIVY_IMAGE'] = 'sdl2,gif'
# os.environ['KIVY_AUDIO'] = 'ffpyplayer'

if platform != 'android':
    Window.size = (330, 650)

# Window.size = (350, 850)
# Window.top = 100
# Window.left = 900


class Playlist:
    def __init__(self, tracks: list) -> None:
        self.tracks = tracks
        self.current = -1

    @property
    def track_names(self):
        return [track.name for track in self.tracks]

    @property
    def is_first(self):
        return True if self.current == 0 else False

    @property
    def is_last(self):
        return True if self.current == len(self.tracks) - 1 else False

    @property
    def current_track(self):
        try:
            return self.tracks[self.current]
        except IndexError:
            return None

    def next(self):
        if not self.is_last:
            self.current += 1

        return self.tracks[self.current]

    def previous(self):
        if self.current == -1:
            self.current += 1
        elif not self.is_first:
            self.current -= 1

        Logger.debug(
            'PLAYLIST: current: %s | track: %s, tracks: %s',
            self.current,
            self.tracks[self.current],
            self.tracks)
        return self.tracks[self.current]

    def remove(self, track):
        self.tracks.remove(track)

    def set_current(self, track):
        self.current = self.tracks.index(track)

    def track_by_name(self, track_name):
        for track in self.tracks:
            if track.name == track_name:
                return track


# -------------------- Main Page --------------------
class PlaybackSlider(MDSlider):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(value=self.on_value)

    def on_value(self, instance, value):
        play_button = app.main_page.ids.play_button
        app.song.last_pos = self.value
        if app.song.state == 'stop' and ceil(app.song.get_pos()) == ceil(app.song.length):
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
    def play_track(self, song):
        Logger.debug('playing %s', song.name)
        if app.song:
            app.song.stop()
            app.history.append(app.playlist.current_track)

        if not song.filename:
            song_file = requests.get(song.preview_url)
            mp3_filename = f'songs/{song.artist} - {song.name} preview.mp3'
            ogg_filename = mp3_filename[:-4] + '.ogg'
            with open(mp3_filename, 'wb') as f:
                f.write(song_file.content)
            ffmpeg.run(
                ffmpeg.output(
                    ffmpeg.input(mp3_filename),
                    ogg_filename)
            )
            song.filename = ogg_filename
        app.song = SoundLoader.load(song.filename)
        app.song.name = song.name
        app.song.artist = song.artist
        app.song.volume = app.volume
        app.song.cover_art = (
            song.cover_art
            if song.cover_art is not None
            else 'images/empty_coverart.png'
        )
        app.song.last_pos = 0
        if app.playlist.current_track != song:
            app.playlist.set_current(song)
        app.main_page.ids.track_length.text = str(timedelta(
            seconds=app.song.length)
        )[3:7]
        app.main_page.ids.playback_slider.max = app.song.length
        app.song.play()
        app.main_page.play_button.update_track_current(0)
        self.source = "images/stop2.png"
        app.main_page.update_playlist_menu()
        app.main_page.update_cover_art()
        app.main_page.update_song_info()

        self.event = Clock.schedule_interval(self.update_track_current, 1)

    @log
    def control(self, instance, **kwargs):
        play_next = kwargs.get('play_next')
        Logger.debug('play_next: %s | song_state: %s | app.song: %s',
                     play_next,
                     app.song.state if app.song else None,
                     True if app.song else False)

        if play_next or app.song is None or app.song.state == 'stop':
            # player = MediaPlayer('song.mp3')
            # def get_frame(*args):
            #    s = player.get_pts()
            #    print('debug debug', s)
            # Clock.schedule_interval(get_frame, 1)
            # subprocess.call(['ffmpeg', '-i', 'picture%d0.png', 'output.avi'])
            # return
            if (play_next and app.playlist.is_last) or app.playlist.tracks == []:
                tracks = app.api.get_recommendations(
                    app.genres,
                    app.artists,
                    has_preview_url=True,
                    async_request=False,
                ).response
                app.playlist = Playlist(tracks)
                self.control(instance, play_next=True)
                return
            elif play_next or app.song is None:
                if app.song:
                    app.song.stop()
                    # app.song.unload()
                    # time.sleep(0.2)
                    Logger.debug('unloaded')
                song = app.playlist.next()
                app.main_page.update_playlist_menu()
                app.history.append(song)
                Logger.debug('playing %s', song.name)
                if not song.filename:
                    song_file = requests.get(song.preview_url)
                    mp3_filename = f'songs/{song.artist} - {song.name} preview.mp3'
                    ogg_filename = mp3_filename[:-4] + '.ogg'
                    with open(mp3_filename, 'wb') as f:
                        f.write(song_file.content)
                    ffmpeg.run(
                        ffmpeg.output(
                            ffmpeg.input(mp3_filename),
                            ogg_filename)
                    )
                    song.filename = ogg_filename
                app.song = SoundLoader.load(song.filename)
                app.song.name = song.name
                app.song.artist = song.artist
                app.song.cover_art = (
                    song.cover_art
                    if song.cover_art is not None
                    else 'images/empty_coverart.png'
                )
                app.song.volume = app.volume
                app.song.last_pos = 0
                self.update_track_current(0)
                app.main_page.update_song_info()
                app.main_page.update_cover_art()
                app.main_page.update_playlist_menu()
            else:
                pass

            app.song.volume = app.volume
            app.song.play()
            Logger.debug('last pos: %s', app.song.last_pos)
            app.song.seek(app.song.last_pos)
            # Update song length
            app.main_page.ids.track_length.text = str(timedelta(
                seconds=app.song.length)
            )[3:7]
            app.main_page.ids.playback_slider.max = app.song.length
            # Update current playback time
            self.source = "images/stop.png"
            self.event = Clock.schedule_interval(self.update_track_current, 1)
        else:
            app.song.last_pos = app.song.get_pos()
            Logger.debug(app.song.get_pos)
            self.source = "images/play.png"
            app.song.stop()
            self.event.cancel()

    @log
    def play_previous(self, instance):
        Logger.debug(
            'PLAYLIST: current: %s | is_first: %s',
            app.playlist.current,
            app.playlist.is_first
        )
        if not app.playlist.is_first:
            if app.song:
                app.song.stop()
                # app.song.unload()
                Logger.debug('unloaded')
            song = app.playlist.previous()
            self.play_track(song)

    @log
    def play_next(self, instance):
        if app.playlist.is_last:
            app.play_button.control(instance, play_next=True)
        else:
            if app.song:
                app.song.stop()
                # app.song.unload()
                Logger.debug('unloaded')
            song = app.playlist.next()
            app.history.append(song)
            self.play_track(song)

#    @log
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
    def remove_playlist_item(self, instance):
        items = app.main_page.playlist_menu.items
        for item in items:
            if item['right_content_cls'] == instance:
                removed_song = item['song']

        # if removed_song == app.playlist.current_track:
        #    app.song.stop()
        app.playlist.remove(removed_song)
        current_track = app.playlist.current_track
        menu_items = [
            {"right_content_cls": RightContentCls() if is_removable(i) else None,
             "text": i.name,
             "song": i,
             "icon": 'play-outline' if i == current_track else None
             } for i in app.playlist.tracks
        ]
        self.playlist_menu.dismiss()
        self.playlist_menu = MDDropdownMenu(
            caller=self.ids.playlist_button, items=menu_items, width_mult=4,
            opening_time=0,
        )
        self.playlist_menu.bind(on_release=self.update_playlist_menu)
        # self.playlist_menu.open()
        # self.playlist_menu.opening_time = 0.2

    @log
    def update_playlist_menu(self, *args):
        current_track = app.playlist.current_track
        menu_items = [
            {"right_content_cls": RightContentCls() if is_removable(i) else None,
             "text": i.name,
             "song": i,
             "icon": 'play-outline' if i == current_track else None
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
        self.add_widget(logo)
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
