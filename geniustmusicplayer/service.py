import threading
import os
from os import environ
from time import sleep
import logging

import jnius
from oscpy.server import OSCThreadServer
from android import api_version
from android.storage import app_storage_path
from jnius import autoclass

from utils import save_song, Playlist
from api import API
from db import Database

service = autoclass('org.kivy.android.PythonService').mService
context = service.getApplication().getApplicationContext()

Context = autoclass("android.content.Context")
IconDrawable = autoclass("{}.R$drawable".format(service.getPackageName()))
icon = getattr(IconDrawable, 'icon')
RDrawable = autoclass('android.R$drawable')
NotificationCompat = autoclass("androidx.core.app.NotificationCompat")
MediaButtonReceiver = autoclass('androidx.media.session.MediaButtonReceiver')
MediaSession = autoclass('android.media.session.MediaSession')
MediaStyle = autoclass("androidx.media.app.NotificationCompat$MediaStyle")
NotificationCompatAction = autoclass("androidx.core.app.NotificationCompat$Action")
NotificationCompatBuilder = autoclass("androidx.core.app.NotificationCompat$Builder")
PlaybackStateCompat = autoclass("android.support.v4.media.session.PlaybackStateCompat")
BitmapFactory = autoclass("android.graphics.BitmapFactory")
IconDrawable = autoclass("{}.R$drawable".format("org.allerter.geniustmusicplayer"))
mediaSession = MediaSession(context, "gtplayer music notification")
controller = mediaSession.getController()
mediaMetadata = controller.getMetadata()
icon = getattr(IconDrawable, 'icon')
images_path = os.path.join(app_storage_path(), "temp")


class OSCSever:
    def __init__(self, activity_server_address, port):
        self.song = SoundAndroidPlayer(self.on_complete)
        self.osc = OSCThreadServer()
        self.osc.listen(port=port, default=True)
        self.activity_server_address = activity_server_address
        self.osc.bind(b'/get_pos', self.get_pos)
        self.osc.bind(b'/load', self.load)
        self.osc.bind(b'/play', self.play)
        self.osc.bind(b'/load_play', self.load_play)
        self.osc.bind(b'/seek', self.seek)
        self.osc.bind(b'/play_new_playlist', self.play_next)
        self.osc.bind(b'/set_volume', self.set_volume)
        self.osc.bind(b'/stop', self.pause)
        self.osc.bind(b'/unload', self.unload)

        self.api = API()
        self.db = Database()
        user = self.db.get_user()
        self.genres = user['genres']
        self.artists = user['artists']
        self.volume = user['volume']
        self.songs_path = user['songs_path']
        self.playlist = self.db.get_playlist()
        self.waiting_for_load = False
        self.seek_pos = 0
        self.downloading = None
        self.waiting_for_download = False
        self.downloads = []

    def check_pos(self, *args):
        if self.song.state == "play" and self.song.length - self.song.get_pos() < 20:
            next_song = self.playlist.preview_next()
            if next_song is None or next_song.preview_file is None:
                if next_song is None:
                    self.playlist = self.get_new_playlist()
                    next_song = self.playlist.preview_next()
                Logger.debug('SERVICE: Preloading next song.')
                self.download_song(next_song)

    def thread_download_song(self, song):
        self.downloads.append(song.id)
        try:
            res = self.api.download_preview(song)
        except Exception as e:
            Logger.error("SERVICE: Download failed. Reason: %s", e)
        else:
            song.preview_file = save_song(self.songs_path, song, res)
            self.db.update_track(song, 'preview_file', song.preview_file)
            Logger.debug('SERVICE: Downloading song finished.')
        self.downloads.remove(song.id)

    def download_song(self, song):
        if song.id not in self.downloads and song.preview_file is None:
            Logger.debug('SERVICE: Downloading %s.', song.id)
            t = threading.Thread(
                target=self.thread_download_song,
                args=(song,)
            )
            t.daemon = True
            t.start()
        else:
            Logger.debug('SERVICE: Skipped downloading %s. Already in progress.',
                         song.id)

    def get_new_playlist(self):
        Logger.debug('SERVICE: getting new playlist.')
        req = self.api.get_recommendations(
            self.genres,
            self.artists,
            song_type='preview',
        )
        playlist = Playlist(req)
        self.osc.send_message(b'/update_playlist',
                              [],
                              *self.activity_server_address)
        # clean up playlist songs
        favorites = self.db.get_favorites()
        for song in self.playlist.tracks:
            if (song.preview_file
                and song not in favorites
                    and song != self.song.song_object):
                Logger.debug("Service: Removed %s", song.id)
                os.remove(song.preview_file)
        return playlist

    def get_pos(self, *values):
        pos = self.song.get_pos() if self.song and self.song.is_prepared else 0
        Logger.debug('SERVICE -> ACTIVITY: /pos %s', pos)
        self.osc.answer(b'/pos', [pos])

    def getaddress(self):
        return self.osc.getaddress()

    def load(self, id):
        self.first_load = not getattr(self.song, "id", 0)
        self.song.id = id
        self.song.is_prepared = False
        Logger.debug('SERVICE: Loading %d.', id)
        song = self.db.get_track(id)
        if song.preview_file is None and self.downloading != song.id:
            Logger.debug('SERVICE: %d is not downloaded.', id)
            self.download_song(song)
        if song.id in self.downloads:
            Logger.debug('SERVICE: %d is downloading. Returning.', id)
            self.waiting_for_download = song.id
            return
        Logger.debug('SERVICE: %d file is available.', id)
        self.waiting_for_download = None
        if not self.first_load:
            self.song.reset()
        self.song.load(song.preview_file)
        self.song.song_object = song
        self.db.update_current_track(song)
        self.playlist = self.db.get_playlist()
        self.song.is_prepared = True
        self.update_notification()
        Logger.debug('SERVICE: Song loaded.')

    def load_play(self, id, volume=None):
        Logger.debug('SERVICE: Loading and playing %d.', id)
        self.pause()
        self.load(id)
        self.play(0, volume if volume is not None else self.volume)

    def play(self, seek, volume):
        if not self.song.is_prepared:
            song_id = getattr(self.song, "id", None)
            Logger.debug('SERVICE: %s is not prepared.', song_id if song_id else "Song")
            if not self.waiting_for_download:
                self.load(self.playlist.current_track.id)
            else:
                self.waiting_for_load = True
                self.seek_pos = seek
                self.volume = volume
                return
        else:
            self.waiting_for_load = False
            self.song.is_prepared = True
        self.song.play()
        self.song.seek(seek)
        self.song.volume = volume
        pos = self.song.get_pos()
        Logger.debug('SERVICE -> ACTIVITY: /playing %s.', pos)
        values = [self.song.song_object.id, pos]
        self.osc.send_message(b'/playing',
                              values,
                              *self.activity_server_address)
        Logger.debug('SERVICE: Playing %d.', self.song.song_object.id)
        self.update_notification()

    def stop(self, *values):
        Logger.debug('SERVICE: stopping %d.', self.song.song_object.id)
        self.waiting_for_load = False
        if self.song.is_prepared and self.song.state == 'play':
            self.song.is_prepared = False
            self.song.stop()
        self.update_notification()

    def pause(self, *values):
        Logger.debug('SERVICE: pausing Song.')
        self.waiting_for_load = False
        if self.song.is_prepared and self.song.state == 'play':
            self.song.pause()
        self.update_notification()

    def seek(self, value):
        Logger.debug('SERVICE: seeking %s.', value)
        if self.song.is_prepared:
            self.song.seek(value)

    def set_volume(self, value):
        Logger.debug('SERVICE: setting song volume %s.', value)
        self.volume = value
        if self.song.is_prepared:
            self.song.volume = value

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
        self.db.update_playlist(self.playlist)
        self.load_play(song.id)

    def play_previous(self):
        Logger.debug('SERVICE: Playing previous.')
        if not self.playlist.is_first:
            self.stop()
            self.load_play(self.playlist.previous().id)

    def on_state(self, instance, value):
        Logger.debug('SERVICE -> ACTIVITY: /set_state %s', value)
        self.osc.send_message(
            b'/set_state',
            [value.encode()],
            *self.activity_server_address)
        if self.song.is_prepared and self.song.length - self.song.get_pos() < 0.2:
            self.on_complete()

    def unload(self, *values):
        self.song.unload()

    def update_notification(self):
        notification = self.create_notification()
        notification_manager = context.getSystemService(Context.NOTIFICATION_SERVICE)
        notification_manager.notify(1, notification)

    def create_notification(self):
        song = getattr(self.song, "song_object", None)
        if api_version >= 26:
            builder = NotificationCompatBuilder(context, "gtplayer")
        else:
            builder = NotificationCompatBuilder(context)
        (
            builder
            .setContentTitle(song.name if song else "GTPlayer")
            .setContentText(song.artist if song else "GTPlayer")
            .setContentIntent(controller.getSessionActivity())
            .setDeleteIntent(MediaButtonReceiver.buildMediaButtonPendingIntent(
                context,
                PlaybackStateCompat.ACTION_STOP))
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC).setSmallIcon(icon)
        )
        style = MediaStyle().setShowActionsInCompactView(0)
        builder.setStyle(style)

        if song is not None and not self.playlist.is_first:
            previous_intent = MediaButtonReceiver.buildMediaButtonPendingIntent(
                context, PlaybackStateCompat.ACTION_SKIP_TO_PREVIOUS)
            action = NotificationCompatAction(
                RDrawable.ic_media_previous, "Previous", previous_intent)
            builder.addAction(action)

        if self.song.state == "play":
            intent = MediaButtonReceiver.buildMediaButtonPendingIntent(
                context, PlaybackStateCompat.ACTION_PAUSE)
            action = NotificationCompatAction(
                RDrawable.ic_media_pause, "Pause", intent)
        else:
            intent = MediaButtonReceiver.buildMediaButtonPendingIntent(
                context, PlaybackStateCompat.ACTION_PLAY)
            action = NotificationCompatAction(
                RDrawable.ic_media_play, "Play", intent)
        builder.addAction(action)

        coverart = None
        if song is not None:
            next_intent = MediaButtonReceiver.buildMediaButtonPendingIntent(
                context, PlaybackStateCompat.ACTION_SKIP_TO_NEXT)
            action = NotificationCompatAction(
                RDrawable.ic_media_next, "Next", next_intent)
            builder.addAction(action)

            path = os.path.join(images_path, f"{song.id}.png")
            if os.path.isfile(path):
                coverart = path

        coverart = coverart if coverart is not None else "images/empty_coverart.png"
        builder.setLargeIcon(BitmapFactory.decodeFile(coverart))

        return builder.build()


if api_version >= 26:
    NotificationChannel = autoclass('android.app.NotificationChannel')
    NotificationManager = autoclass("android.app.NotificationManager")
    channel_name = 'GTPlayer'
    channel_importance = NotificationManager.IMPORTANCE_DEFAULT
    channel = NotificationChannel("gtplayer", channel_name, channel_importance)
    channel.setDescription('GeniusT Music Player')
    notificationManager = service.getSystemService(NotificationManager)
    notificationManager.createNotificationChannel(channel)


def start_debug_server(activity_address, service_port):
    from kivy.core.audio import SoundLoader
    from kivy.logger import Logger
    from threading import Thread
    global Logger
    global SoundAndroidPlayer

    def SoundAndroidPlayer(filename, _):
        return SoundLoader.load(filename)

    def check_end(osc):
        while True:
            if song := osc.song:
                if song.length - song.get_pos() < .5 and song.state == 'stop':
                    osc.play_next()
            sleep(.1)
    osc = OSCSever(activity_address, service_port)
    t = Thread(target=check_end, args=(osc,))  # equivalent of OnCompletionListener
    t.daemon = True
    t.start()


if __name__ == '__main__':
    from jnius import autoclass
    from android_audio_player import SoundAndroidPlayer
    args = environ.get('PYTHON_SERVICE_ARGUMENT', '')
    logging.basicConfig(format="%(levelname)s - %(message)s")
    Logger = logging.getLogger('gtplayer')
    Logger.setLevel(logging.DEBUG)
    Logger.debug("ANDROID: api version %s", api_version)
    args = args.split(',') if args else []
    activity_ip, activity_port, service_port = args[0], int(args[1]), int(args[2])
    activity_address = (activity_ip, activity_port)
    osc = OSCSever(activity_address, service_port)
    osc.download_song(osc.playlist.current_track)
    osc.load(osc.playlist.current_track.id)
    Logger.debug('SERVICE: Started OSC server.')
    Logger.debug("SERVICE: Genres: %s - Artists: %s", osc.genres, osc.artists)
    service.startForeground(1, osc.create_notification())
    osc.osc.send_message(b'/ready',
                         [],
                         *osc.activity_server_address)
    while True:
        if osc.waiting_for_download:
            osc.load(osc.waiting_for_download)
        elif osc.waiting_for_load:
            osc.play(osc.seek_pos, osc.volume)
        else:
            osc.check_pos()
        sleep(.1)
