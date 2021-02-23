import os
import logging
from datetime import timedelta
from os.path import join
from time import time

from kivy.loader import Loader
from kivymd.app import MDApp
from kivymd.uix.slider import MDSlider
from kivymd.uix.button import MDIconButton
from kivymd.uix.list import OneLineIconListItem
from kivymd.uix.list import MDList
from kivymd.theming import ThemableBehavior
from kivymd.uix.list import BaseListItem, ContainerSupport
from kivymd.toast import toast
from kivy.factory import Factory
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivy.properties import (BooleanProperty, NumericProperty,
                             ObjectProperty, StringProperty)
from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.logger import Logger, LOG_LEVELS
from kivy.utils import platform
from kivy.metrics import dp

from api import API
from db import Database


my_logger = logging.getLogger('gtplayer')
my_logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
my_logger.addHandler(ch)


def get_open_port():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        return s.getsockname()[1]


class ServerSong():

    def __init__(self, app, pos_callback, state_callback, port):
        from oscpy.server import OSCThreadServer
        self.app = app
        self.pos_callback = pos_callback
        self.state_callback = state_callback
        self.state = 'stop'
        self.length = 30
        self.is_complete = False
        self.song_object = None

        self.osc = OSCThreadServer()
        self.osc.listen(port=port, default=True)
        self.osc.bind(b'/pos', self._get_pos)
        self.osc.bind(b'/set_state', self.set_state)
        self.osc.bind(b'/set_length', self.set_length)
        self.osc.bind(b'/set_complete', self.set_complete)
        self.osc.bind(b'/playing', self.playing)
        self.osc.bind(b'/update_playlist', self.update_playlist)

    def playing(self, id, pos):
        Logger.debug('ACTIVITY: Playing.')
        self.state = 'play'
        self.last_pos = pos
        song = self.app.playlist.get_track(id=id)
        play_button = self.app.play_button
        if self.song_object != song:
            play_button.load_song(song, playing=True)
        play_button.update_track_current(current=pos)
        if play_button.event:
            play_button.event.cancel()
        play_button.event = Clock.schedule_interval(play_button.update_track_current, 1)

    def set_state(self, value):
        Logger.debug('ACTIVITY: State %s', value)
        self.state = value.decode()

    def set_length(self, value):
        Logger.debug('ACTIVITY: Length %s', value)
        self.length = value

    def set_complete(self, value):
        Logger.debug('ACTIVITY: Song is_complete=%s', value)
        self.is_complete = value

    def set_volume(self, value):
        Logger.debug('ACTIVITY -> Service: Set volume %s', value)
        self.osc.send_message(b'/set_volume', [value], *self.server_address)

    def getaddress(self):
        return self.osc.getaddress()

    def load(self, song):
        Logger.debug('ACTIVITY -> SERVER: /load')
        self.osc.send_message(b'/load', [song.id], *self.server_address)

    def unload(self):
        Logger.debug('ACTIVITY -> SERVER: /unload')
        self.osc.send_message(b'/unload', [], *self.server_address)

    def play(self, seek, volume):
        Logger.debug('ACTIVITY -> SERVER: /play pos %s vol %s', seek, volume)
        self.osc.send_message(b'/play', [seek, volume], *self.server_address)

    def play_new_playlist(self):
        Logger.debug('ACTIVITY -> SERVER: /play_new_playlist')
        self.osc.send_message(b'/play_new_playlist', [], *self.server_address)

    def load_play(self, song, volume):
        Logger.debug('ACTIVITY -> SERVER: /load_play %s vol %s', song.id, volume)
        self.osc.send_message(b'/load_play',
                              [song.id, volume],
                              *self.server_address)

    def stop(self):
        Logger.debug('ACTIVITY -> SERVER: /stop')
        self.osc.send_message(b'/stop', [], *self.server_address)

    def seek(self, position):
        Logger.debug('ACTIVITY -> SERVER: /seek %s', position)
        self.osc.send_message(b'/seek', [position], *self.server_address)

    def save_pos(self, callback):
        Logger.debug('ACTIVITY -> SERVER: /get_pos')
        self.pos_callback = callback
        self.osc.send_message(b'/get_pos', [], *self.server_address)

    def get_pos(self, callback):
        Logger.debug('ACTIVITY -> SERVER: get pos and call %s', callback)
        self.pos_callback = callback
        self.osc.send_message(b'/get_pos', [], *self.server_address)

    def _get_pos(self, value):
        Logger.debug('ACTIVITY: pos received %s', value)
        self.pos_callback(value)

    def update_playlist(self):
        self.app.playlist = self.app.db.get_playlist()
        Logger.debug('ACTIVITY: Updated playlist.')


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
        # self.bind(value=self.on_value)
        # TODO: by using these, slider value won't update automatically
        # how do I set it myself?
        # self.bind(on_touch_down=self.stop_slider_update)
        # self.bind(on_touch_up=self.seek)
        self.bind(value=self.seek)

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

    def seek(self, slider, touch, *args):
        if abs(slider.value - app.song.last_pos) > 1.5:
            play_button = app.play_button
            app.song.last_pos = value = self.value
            play_button.update_track_current(current=value)
            if app.song.state == 'play':
                Logger.info('SEEK: %s', value)
                app.song.seek(value)

class VolumeSlider(MDSlider):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_value = 0
        self.bind(value=self.set_volume)

    def set_volume(self, slider, value):
        value = slider.value
        if value != 0:
            self.last_value = value
        app.volume = slider.value_normalized
        app.song.set_volume(app.volume)

class PlayButton(ButtonBehavior, Image):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(on_release=lambda instance: self.control(instance))
        self.event = None
        self.snackbar = None
        app.play_button = self

    def load_song(self, song, playing=False):
        Logger.debug('load_song: %s', song.preview_file)
        app.song.song_object = song
        app.song.is_complete = False
        app.song.last_pos = 0
        if playing:
            app.song.state = 'play'
        app.main_page.edit_ui_for_song(song, playing=playing)
        app.playlist.set_current(song)

    def play_track(self, song, seek=0):
        self.update_track_current(current=seek)
        if self.event:
            self.event.cancel()
        if app.song is None or app.song.song_object != song:
            self.load_song(song)
            app.song.load_play(song, app.volume)
            Logger.info('SONG: Playing new song.')
        else:
            Logger.info('SONG: resume.')
            app.song.play(seek, app.volume)
        # app.song.song_object = song
        # app.playlist.set_current(song)
        app.song.state = 'play'
        self.source = f'images/stop_{app.theme_cls.theme_style.lower()}.png'

        Logger.info('play_track: playing %s | seek: %s', song.name, seek)

    def control(self, instance, **kwargs):
        play_next = kwargs.get('play_next')
        Logger.debug('control: current: %s, play_next: %s | song_state: %s',
                     app.playlist.current_track,
                     play_next,
                     app.song.state)

        if play_next or app.song is None or app.song.state == 'stop':
            if (play_next and app.playlist.is_last) or app.playlist.tracks == []:
                app.song.play_new_playlist()
            elif play_next or app.song is None:
                song = app.playlist.next()
                Logger.debug('playing %s', song.name)
                self.play_track(song)
            else:
                Logger.debug('control: resuming song %s', app.song.last_pos)
                self.play_track(app.song.song_object, seek=app.song.last_pos)
        else:
            def save_pos(pos):
                app.song.last_pos = pos
                self.update_track_current(current=pos)
            app.song.save_pos(callback=save_pos)
            app.song.stop()
            app.song.state = 'stop'
            Logger.debug('control: stopped at %s (state: %s)',
                         app.song.last_pos, app.song.state)
            self.source = f'images/play_{app.theme_cls.theme_style.lower()}.png'
            if self.event:
                self.event.cancel()

    def play_previous(self, instance):
        Logger.debug(
            'play_previous: PLAYLIST: current: %s | is_first: %s',
            app.playlist.current_track,
            app.playlist.is_first
        )
        if not app.playlist.is_first:
            song = app.playlist.previous()
            self.play_track(song)

    def play_next(self, instance):
        Logger.debug(
            'play_next: PLAYLIST: current: %s | is_last: %s',
            app.playlist.current_track,
            app.playlist.is_first
        )
        if self.event:
            self.event.cancel()
        if app.playlist.is_last:
            app.song.play_new_playlist()
        else:
            song = app.playlist.next()
            self.play_track(song)

    def stop_song(self, release=False):
        if app.song.state == 'play':
            app.song.stop()
            if platform == 'android' and release:
                app.song.unload()
            else:
                Logger.debug('SONG UNLOAD: Skipped because of ffpyplayer crash.')

    def update_track_current(self, *args, **kwargs):
        track_current = app.main_page.ids.track_current
        slider = app.main_page.ids.playback_slider
        current = kwargs.get('current')
        if current is None:
            new_value = slider.value + 1
            if new_value >= 5:
                app.main_page.download_next_coverart()
            if new_value <= slider.max:
                slider.value = new_value
                app.song.last_pos = new_value
        else:
            slider.value = current
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
            app.song.song_object.date_favorited = time()
            self.favorited = True
            app.favorites.append(app.song.song_object)
            app.db.add_favorites_track(app.song.song_object)
        else:
            app.song.song_object.date_favorited = None
            self.favorited = False
            app.favorites.remove(app.song.song_object)
            app.db.remove_favorites_track(app.song.song_object)


class MyBaseListItem(ContainerSupport, BaseListItem):
    _txt_left_pad = NumericProperty("10dp")
    _txt_top_pad = NumericProperty("20dp")
    _txt_bot_pad = NumericProperty("10dp")  # dp(24) - dp(5)
    _height = NumericProperty()
    _num_lines = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.height = dp(56) if not self._height else self._height


class PlaylistSongItem(MyBaseListItem):
    # dp(40) = dp(16) + dp(24):
    _txt_right_pad = NumericProperty("40dp")

    def __init__(self, **kwargs):
        import kivymd.material_resources as m_res
        super().__init__(**kwargs)
        self._txt_right_pad = dp(40) + m_res.HORIZ_MARGINS


def is_removable(song):
    return True if not app.song or song.name != app.song.song_object.name else False


class MainPage(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        global app
        app = MDApp.get_running_app()
        self.app = app
        self.song = self.app.song
        self.playlist_menu = None

    def edit_ui_for_song(self, song=None, playing=False):
        if app.song:
            self.ids.track_length.text = str(timedelta(
                seconds=app.song.length)
            )[3:7]
            self.ids.playback_slider.max = app.song.length
        # app.play_button.update_track_current(current=0)
        if playing:
            theme = app.theme_cls.theme_style.lower()
            app.play_button.source = f'images/stop_{theme}.png'
        if song in app.favorites:
            self.favorite_button.favorited = True
        else:
            self.favorite_button.favorited = False
        if song != self.song:
            self.update_playlist_menu(song=song)
            self.update_cover_art(song)
            self.update_song_info(song)
            self.update_download_button(song)
            self.song = song

    def update_download_button(self, song):
        if song.download_url or song.isrc:
            Logger.debug('DOWNLOAD: Available.')
            self.download_button.text_color = app.theme_cls.text_color
        else:
            Logger.debug('DOWNLOAD: Unavailable.')
            self.download_button.text_color = app.theme_cls.disabled_hint_text_color

    def update_playlist_menu(self, *args, song=None):
        from kivymd.uix.bottomsheet import MDCustomBottomSheet
        self.app.playlist = self.app.db.get_playlist()
        self.playlist_menu = MDCustomBottomSheet(
            screen=Factory.PlaylistLayout(height=dp(65 * len(app.playlist.tracks))),
        )
        for i in app.playlist.tracks:
            item = PlaylistSongItem(
                text=i.name,
                secondary_text=i.artist,
                on_release=lambda *args, song=i: self.play_from_playlist(song),
            )
            item.song = i
            item.open_song_menu = self.open_song_menu
            removable = (
                is_removable(i)
                or i != app.playlist.current_track
                or (song is not None and i != song)
            )
            # different background for current song
            if not removable:
                item.bg_color = app.theme_cls.primary_color  # rgba('#cbcbcb')
                item.theme_text_color = 'Custom'
                item.text_color = (1, 1, 1, 1)
            self.playlist_menu.screen.songs_grid.add_widget(item)

    def open_song_menu(self, i):
        # adding right-side icons
        from kivymd.uix.bottomsheet import MDListBottomSheet
        song_menu = MDListBottomSheet(radius_from='top')
        if i.download_file:
            song_menu.add_item(
                text="Song Downloaded",
                callback=lambda *args: None,
                icon='check')
        elif i.download_url or i.isrc:
            song_menu.add_item(
                text="Download Full Song",
                callback=lambda *args, song=i: self.download_song(
                    song, show_progress=False),
                icon='download')
        # Spotify
        if i.id_spotify:
            from utils import spotify_installed
            msg = "Spotify isn't installed on your device."
            song_menu.add_item(
                text="Listen on Spotify",
                callback=lambda x, song=i: (self.open_spotify(i)
                                            if spotify_installed()
                                            else toast(msg)),
                icon="spotify")

        # Favorited
        favorited = i in app.favorites
        song_menu.add_item(
            text="Favorite" if not favorited else "Unfavorite",
            callback=lambda *args, song=i: app.main_page.favorite_playlist_item(
                self, song),
            icon='heart' if favorited else 'heart-outline')

        # Remove
        removable = (
            is_removable(i)
            or i != app.playlist.current_track
        )
        if removable:
            song_menu.add_item(
                text="Remove from playlist",
                callback=lambda *args, song=i: app.main_page.remove_playlist_item(
                    self, song),
                icon='close')
        song_menu.open()

    def open_spotify(self, song):
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        mActivity = autoclass('org.kivy.android.PythonActivity').mActivity

        intent = Intent(Intent.ACTION_VIEW)
        intent.setData(Uri.parse(f"spotify:track:{song.id_spotify}"))
        intent.putExtra(
            Intent.EXTRA_REFERRER,
            Uri.parse("android-app://org.allerter.geniustmusicplayer").toString()
        )
        self.app.play_button.stop_song(release=True)
        mActivity.startActivity(intent)

    def play_from_playlist(self, track):
        # track = app.playlist.get_track(name=selected_item.text)
        if track == app.playlist.current_track:  # track is already playing
            return
        self.playlist_menu.dismiss()
        app.play_button.play_track(track)

    def remove_playlist_item(self, instance, song):
        self.playlist_menu.screen.songs_grid.remove_widget(instance.parent.parent)
        app.playlist.remove(song)
        app.db.remove_playlist_track(song)
        self.playlist_menu.dismiss()
        toast('Removed from playlist')

    def favorite_playlist_item(self, instance, song):
        if song in app.favorites:
            favorited = False
            song.date_favorited = None
            app.favorites.remove(song)
            app.db.remove_favorites_track(song)
            msg = 'Song unfavorited'
        else:
            favorited = True
            song.date_favorited = time()
            app.favorites.append(song)
            app.db.add_favorites_track(song)
            msg = 'Song favorited'

        # Correct main favorite button if user (un)favorited item == current song
        if app.song.song_object == song:
            app.main_page.favorite_button.favorited = favorited

        self.playlist_menu.dismiss()
        toast(msg)

    def _get_cover_art_path(self, song):
        filename = str(song.id) + ".png"
        return os.path.join(self.app.images_path, filename)

    def _get_cover_art(self, song):
        cover_art = self._get_cover_art_path(song)
        if not os.path.isfile(cover_art):
            if song.cover_art is not None:
                cover_art = song.cover_art
            else:
                cover_art = 'images/empty_coverart.png'
        return cover_art

    def update_cover_art(self, song):
        cover_art = self._get_cover_art(song)
        self.ids.cover_art.source = cover_art

    def save_cover_art(self, image):
        if (image.texture != Loader.loading_image.texture
                and image.source != 'images/empty_coverart'):
            cover_art = self._get_cover_art_path(self.app.song.song_object)
            if not os.path.isfile(cover_art):
                image.texture.save(cover_art, flipped=False)
                Logger.debug('CACHE: Saved %s', cover_art)

    def download_next_coverart(self):
        song = self.app.playlist.preview_next()
        if song.cover_art and not os.path.isfile(self._get_cover_art_path(song)):
            image = Loader.image(song.cover_art)
            image.source = None
            image.bind(on_load=self.save_cover_art)

    def update_song_info(self, song):
        self.ids.title.text = song.name
        self.ids.artist.text = song.artist

    def check_permission(self, permissions, grant_results):
        for result in grant_results:
            if result is False:
                return
        self.app.storage_permission = True
        self.download_song(self.to_be_downloaded, self.show_progress)

    def download_song(self, song, show_progress=True):
        import threading
        import requests
        from io import BytesIO
        from kivymd.uix.progressbar import MDProgressBar
        from jnius import autoclass, PythonJavaClass, java_method
        from android.storage import primary_external_storage_path
        from get_song_file import get_download_info, get_file_from_encrypted
        from utils import save_song

        def get_song(self, song, storage_path, progress_bar=None):
            Logger.debug("DOWNLOAD: Thread started.")
            if song.download_url:
                url = song.download_url
                encrypted = False
            else:
                Logger.debug("DOWNLOAD: Getting song info.")
                data = get_download_info(song.isrc)
                url = data['url']
                encrypted = True
            Logger.debug("DOWNLOAD: Downloading chunks...")
            req = requests.get(url, stream=True)
            song_bytes = b''
            chunk_size = 500000
            num_chunks = int(req.headers['Content-Length']) // chunk_size
            chunk_progress = 100 // num_chunks
            try:
                for i, chunk in enumerate(req.iter_content(chunk_size)):
                    song_bytes += chunk
                    if progress_bar:
                        progress_bar.value += chunk_progress
                    Logger.debug('DOWNLOAD: Received chunk %s/%s', i, num_chunks)
            except Exception as e:
                Logger.error(e)
                if progress_bar:
                    toast('Download failed.')
                song.download_file = None
                return
            bio = BytesIO(song_bytes)
            if encrypted:
                bio = get_file_from_encrypted(bio, data, BytesIO())
            filename = save_song(
                storage_path,
                song,
                bio.getbuffer(),
                preview=False
            )
            song.download_file = filename
            Logger.debug("DOWNLOAD: Saved file.")

            class OnScanCompletedListener(PythonJavaClass):
                __javainterfaces__ = ["android/media/MediaScannerConnection"
                                      "$OnScanCompletedListener"]
                __javacontext__ = "app"

                def __init__(self, **kwargs):
                    super().__init__(**kwargs)

                @java_method("(Ljava/lang/String;Landroid/net/Uri;)V")
                def onScanCompleted(self, path, uri):
                    Logger.debug("DOWNLOAD: Scan completed.")

            MediaScannerConnection = autoclass("android.media.MediaScannerConnection")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            mActivity = PythonActivity.mActivity
            listener = OnScanCompletedListener()
            MediaScannerConnection.scanFile(
                mActivity.getApplicationContext(),
                [filename],
                ["audio/mp3"],
                listener
            )

            if progress_bar:
                toast(f'Downloaded to {filename}')
                self.remove_widget(progress_bar)
            Logger.debug("DOWNLOAD: Thread finished.")

        if song.download_file == 'downloading':
            if show_progress:
                toast('Download in progress...')
            return

        if not self.app.storage_permission:
            from android.permissions import request_permissions, Permission
            self.to_be_downloaded = song
            self.show_progress = show_progress
            request_permissions(
                [
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                ],
                callback=self.check_permission)
            return

        primary_ext_storage = primary_external_storage_path()
        if os.path.exists(os.path.join(primary_ext_storage, "Music")):
            storage_path = os.path.join(primary_ext_storage, "Music")
        elif os.path.exists(os.path.join(primary_ext_storage, "Download")):
            storage_path = os.path.join(primary_ext_storage, "Download")
        else:
            storage_path = primary_ext_storage
        Logger.debug("DOWNLOAD: Storage path: %s", storage_path)
        if show_progress:
            progress_bar = MDProgressBar()
            progress_bar.pos = progress_bar.pos[0], self.ids.cover_art.pos[1] + dp(5)
            self.add_widget(progress_bar)
            toast('Download started.')
        else:
            progress_bar = None
        song.download_file = 'downloading'
        t = threading.Thread(
            target=get_song,
            args=(self, song, storage_path, progress_bar),
        )
        t.daemon = True
        t.start()


# -------------------- App --------------------


class ItemDrawer(OneLineIconListItem):
    icon = StringProperty()


class ContentNavigationDrawer(BoxLayout):
    screen_manager = ObjectProperty()
    nav_drawer = ObjectProperty()


class DrawerList(ThemableBehavior, MDList):
    def set_color_item(self, instance_item):
        '''Called when tap on a menu item.'''

        # Set the color of the icon and text for the menu item.
        dark_mode = True if self.theme_cls.theme_style == 'Dark' else False
        selected_colors = (self.theme_cls.primary_color, self.theme_cls.primary_light)
        for item in self.children:
            if item.text_color in selected_colors:
                item.text_color = (
                    self.theme_cls.text_color
                    if not dark_mode
                    else (1, 1, 1, 0.87))
                break
        instance_item.text_color = (
            self.theme_cls.primary_color
            if not dark_mode
            else self.theme_cls.primary_light
        )


class LoadingPage(Screen):
    def __init__(self, **kwargs):
        from kivymd.uix.label import MDLabel
        super().__init__(**kwargs)
        logo = Image(source="images/icon.png", pos=(800, 800))
        label = MDLabel(
            text='Loading...',
            pos=(logo.pos[0] + logo.size[0] + 5, logo.pos[1]))
        self.add_widget(logo)
        self.add_widget(label)
        # animation = Animation(x=0, y=0, d=2)
        # animation.start(logo)


def start_service(args):
    from jnius import autoclass
    service = autoclass('org.allerter.geniustmusicplayer.ServiceGtplayer')
    mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
    service.start(mActivity, args)


def remove_splash_screen(*args):
    from jnius import autoclass
    activity = autoclass('org.kivy.android.PythonActivity').mActivity
    activity.removeLoadingScreen()


class MainApp(MDApp):
    artists = []
    genres = []
    db = Database()
    song = None
    main_page = None
    volume = 0.5
    api = API()
    storage_permission = False

    def build(self):
        Logger.setLevel(LOG_LEVELS['debug'])
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.accent_palette = "Amber"
        Loader.loading_image = 'images/empty_coverart.png'

        self.nav_layout = Factory.NavLayout()
        self.screen_manager = self.nav_layout.screen_manager
        self.nav_drawer = self.nav_layout.nav_drawer
        self.nav_drawer_list = self.nav_drawer.children[0].ids.nav_drawer_list
        if platform == 'android':
            from android.storage import app_storage_path
            storage_path = app_storage_path()
        else:
            from kivy.core.window import Window
            storage_path = ''
            Window.size = (330, 650)

        songs_path = join(storage_path, 'songs')
        if not os.path.isdir(songs_path):
            os.mkdir(songs_path)
            Logger.info('DIR: created songs directory')
        self.songs_path = songs_path
        images_path = join(storage_path, 'temp')
        if not os.path.isdir(images_path):
            os.mkdir(images_path)
            Logger.info('DIR: created images temp directory')
        self.images_path = images_path

        self.load_first_page()
        Logger.debug('DISPLAY: Loaded first page.')
        if platform == 'android':
            Clock.schedule_once(remove_splash_screen, .1)
        return self.nav_layout

    def complete_ui(self):
        from kivy.lang import Builder
        import settings_page
        import favorites_page
        Builder.load_file("kv/favorites_page.kv")
        favorites_screen = Screen(name='favorites_page')
        app.favorites_page = favorites_page.FavoritesPage()
        favorites_screen.add_widget(app.favorites_page)
        self.screen_manager.add_widget(favorites_screen)

        Builder.load_file("kv/settings_page.kv")
        settings_screen = Screen(name='settings_page')
        app.settings_page = settings_page.SettingsPage()
        settings_screen.add_widget(app.settings_page)
        self.screen_manager.add_widget(settings_screen)

    def load_first_page(self, *args):
        if user := self.db.get_user():
            self.main_page = page = MainPage()
            self.nav_drawer.type = 'modal'

            self.playlist = self.db.get_playlist()
            self.favorites = self.db.get_favorites()
            if user['dark_mode']:
                self.theme_cls.theme_style = "Dark"
            else:
                self.theme_cls.theme_style = "Light"
            self.genres = user['genres']
            self.artists = user['artists']
            self.volume = user['volume']
            self.play_mode = user['play_mode']

            # load song
            song = self.playlist.current_track
            self.main_page.edit_ui_for_song(song)

            # adding screens
            main_screen = Screen(name='main_page')
            main_screen.add_widget(page)
            self.screen_manager.add_widget(main_screen)
            self.screen_manager.switch_to(main_screen)

            def set_pos(value):
                Logger.debug('SONG: pos %s', value)
                app.song.last_pos = value

            def set_state(value):
                Logger.debug('SONG: state %s', value)
                app.main_page.play_button.check_end()

            # Activity OSC Server
            try:
                activity_port = get_open_port()
            except Exception as e:
                Logger.error(
                    ("OSC: Couldn't get open port for activity."
                     "Setting 4999 instead. %s"),
                    e)
                activity_port = 4999
            Logger.debug('ACTIVITY PORT: %s', activity_port)
            self.song = ServerSong(self, pos_callback=set_pos,
                                   state_callback=set_state,
                                   port=activity_port)

            # Start service
            try:
                service_port = get_open_port()
            except Exception as e:
                Logger.error(
                    ("OSC: Couldn't get open port for service."
                     "Setting 5000 instead. %s"),
                    e)
                service_port = 5000
            Logger.debug('SERVICE PORT: %s', service_port)
            if platform == 'android':
                Logger.debug('ACTIVITY: Starting service.')
                args = [str(x) for x in self.song.getaddress()]
                args.append(str(service_port))
                argument = ",".join(args)
                start_service(argument)
                Logger.debug('ACTIVITY: Service started.')
            else:
                from threading import Thread
                from time import sleep
                from service import start_debug_server
                t = Thread(target=start_debug_server,
                           args=(self.song.getaddress(), service_port,))
                t.daemon = True
                t.start()
                sleep(1)  # allow debug server to finish setting up
            self.song.server_address = [self.song.getaddress()[0], service_port]

            # Update UI
            self.play_button.load_song(song)
            self.song.last_pos = user['last_pos']
            slider = self.main_page.ids.playback_slider
            slider.value = self.song.last_pos
            self.main_page.ids.track_current.text = str(timedelta(
                seconds=slider.value
            ))[3:7]

            volume_slider = self.main_page.ids.volume_slider
            volume_slider.value = volume_slider.last_value = self.volume * 100

            Clock.schedule_once(lambda *args, song=song: self.complete_ui())
        else:
            from kivy.lang import Builder
            import start_page
            self.nav_drawer.type = 'standard'
            Builder.load_file("kv/start_page.kv")
            start_screen = Screen(name='start_page')
            app.start_page = start_page.StartPage()
            start_screen.add_widget(app.start_page)
            self.screen_manager.add_widget(start_screen)

    def on_pause(self):
        self.on_stop()
        return True

    def on_stop(self):
        if app.song and self.db.get_user():
            song_pos = self.main_page.playback_slider.value
            self.db.update_last_pos(song_pos)
            self.db.update_volume(self.volume)
            # Clean up cached cover arts
            images = [f
                      for f in os.listdir(self.images_path)
                      if os.path.isfile(os.path.join(self.images_path, f))]
            cached = [song.id for song in self.playlist.tracks]
            cached.extend([song.id for song in self.favorites])
            for image in images:
                id = int(image[:-4])
                if id not in cached:
                    os.remove(os.path.join(self.images_path, image))
                    Logger.debug('CACHE: Removed %s', image)

    def on_resume(self):
        # update playback slider
        if app.song and self.db.get_user():
            self.playlist = self.db.get_playlist()
            self.play_button.load_song(self.playlist.current_track)


if __name__ == '__main__':
    app = MainApp()
    app.run()
