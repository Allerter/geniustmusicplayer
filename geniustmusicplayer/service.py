from os import environ
from time import sleep
import logging
from oscpy.server import OSCThreadServer

from android_audio_player import SoundAndroidPlayer
from utils import save_song, Playlist
from api import API
from db import Database

logging.basicConfig(format="%(levelname)s - %(message)s")
Logger = logging.getLogger('gtplayer')
Logger.setLevel(logging.DEBUG)


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
        if self.song.length - self.song.get_pos() < 20:
            next_song = self.playlist.preview_next()
            if next_song is None or next_song.preview_file is None:
                if next_song is None:
                    self.playlist = self.get_new_playlist()
                    next_song = self.playlist.preview_next()
                Logger.debug('SERVICE: Preloading next song.')
                self.download_song(next_song)

    def download_song(self, song):
        Logger.debug('SERVICE: Downloading song.')
        res = self.api.download_preview(song)
        song.preview_file = save_song(self.songs_path, song, res)
        self.db.update_track(song, 'preview_file', song.preview_file)
        Logger.debug('SERVICE: Downloading song finished.')

    def get_new_playlist(self):
        Logger.debug('SERVICE: getting new playlist.')
        req = self.api.get_recommendations(
            self.genres,
            self.artists,
            song_type='preview',
        )
        playlist = Playlist(req)
        self.db.update_playlist(playlist)
        self.osc.send_message(b'/update_playlist',
                              [],
                              *self.activity_server_address)
        return playlist

    def get_pos(self, *values):
        pos = self.song.get_pos() if self.song else 0
        Logger.debug('SERVICE -> ACTIVITY: /pos %s', pos)
        self.osc.answer(b'/pos', [pos])

    def getaddress(self):
        return self.osc.getaddress()

    def load(self, id):
        Logger.debug('SERVICE: Loading song.')
        song = self.db.get_track(id)
        if song.preview_file is None:
            Logger.debug('SERVICE: Downlaoding song in load.')
            self.download_song(song)
        self.song = SoundAndroidPlayer(song.preview_file, self.on_complete)
        self.song.song_object = song
        self.db.update_current_track(song)
        self.playlist = self.db.get_playlist()
        Logger.debug('SERVICE: Song loaded.')

    def load_play(self, id, volume=None):
        Logger.debug('SERVICE: Loading and playing song.')
        self.song.stop()
        self.load(id)
        Logger.debug('SERVICE -> ACTIVITY: /playing 0.')
        values = [id]
        self.osc.send_message(b'/playing',
                              values,
                              *self.activity_server_address)
        self.play(0, volume if volume is not None else self.volume)

    def play(self, seek, volume):
        self.song.play()
        self.song.seek(seek)
        self.song.set_volume(volume)
        if self.event:
            self.event.cancel()
        # self.event = Clock.schedule_interval(self.check_pos, .5)
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
        Logger.debug('SERVICE: setting song volume %s.', value)
        self.volume = value
        self.song.set_volume(value)

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
            self.download_song(song)
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
        if self.song.length - self.song.get_pos() < 0.2:
            self.on_complete()

    def unload(self, *values):
        pass  # self.song.unload()


"""
import random
import string
from jnius import autoclass
from android import api_version
# Given a media session and its context (usually the component containing the session)
# Create a NotificationCompat.Builder

# Get the session's metadata

RDrawable = autoclass('android.R$drawable')
RString = autoclass('android.R$string')
NotificationCompat = autoclass("androidx.core.app.NotificationCompat")
# MediaButtonReceiver = autoclass('androidx.media.session.MediaButtonReceiver')
MediaSession = autoclass('android.media.session.MediaSession')
NotificationCompatAction = autoclass("androidx.core.app.NotificationCompat$Action")
NotificationCompatBuilder = autoclass("androidx.core.app.NotificationCompat$Builder")
PlaybackStateCompat = autoclass("android.support.v4.media.session.PlaybackStateCompat")
PythonActivity = autoclass('org.kivy.android.PythonActivity')

mediaSession = MediaSession()
controller = mediaSession.getController()
mediaMetadata = controller.getMetadata()
description = mediaMetadata.getDescription()

service = autoclass('org.allerter.geniustmusicplayer.ServiceGtplayer').mService
app_context = service.getApplication().getApplicationContext()
Logger.debug("ANDROID: api version %s", api_version)
if api_version >= 26:
    NotificationChannel = autoclass('android.app.NotificationChannel')
    NotificationManager = autoclass("android.app.NotificationManager")
    channel_id = ''.join(random.choices(string.ascii_letters, k=10))
    channel_name = 'GTPlayer'
    channel_importance = NotificationManager.IMPORTANCE_DEFAULT
    channel = NotificationChannel(channel_id, channel_name, channel_importance)
    channel.setDescription('GeniusT Music Player')
    NotificationManagerClass = autoclass('android.app.NotificationManager.class')
    notificationManager = service.getSystemService(NotificationManagerClass)
    notificationManager.createNotificationChannel(channel)
    builder = NotificationCompatBuilder(app_context, channel_id)
else:
    builder = NotificationCompatBuilder(app_context)

IconDrawable = autoclass("{}.R$drawable".format(service.getPackageName()))
icon = getattr(IconDrawable, 'icon')
(builder
    # Add the metadata for the currently playing track
    .setContentTitle('Lane Boy')
    .setContentText('Twenty One Pilots')
    .setSubText('Song')
    .setLargeIcon(icon)

    # Enable launching the player by clicking the notification
    .setContentIntent(controller.getSessionActivity())

    # Stop the service when the notification is swiped away
    # .setDeleteIntent(MediaButtonReceiver.buildMediaButtonPendingIntent(
    #    context,
    #    PlaybackStateCompat.ACTION_STOP))

    # Make the transport controls visible on the lockscreen
    .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)

    # Add an app icon and set its accent color
    # Be careful about the color
    .setSmallIcon(icon)
    # .setColor(ContextCompat.getColor(context, R.color.primaryDark))
 )
# Add a pause button
# pause_intent = MediaButtonReceiver.buildMediaButtonPendingIntent(
#    app_context,
#    PlaybackStateCompat.ACTION_PLAY_PAUSE
# )
# action = NotificationCompatAction(
#    RDrawable.pause, 'Pause',  # getString(R.string.pause),
#    pause_intent
# )
# builder.addAction(action)

# Take advantage of MediaStyle features
# .setStyle(new MediaStyle()
#          .setMediaSession(mediaSession.getSessionToken())
#          .setShowActionsInCompactView(0)

#          # Add a cancel button
#          .setShowCancelButton(true)
#          .setCancelButtonIntent(MediaButtonReceiver.buildMediaButtonPendingIntent(
#          context,
#          PlaybackStateCompat.ACTION_STOP)))

# Display the notification and place the service in the foreground
 service.startForeground(1, builder.build())
"""
Logger.debug('SERVICE: Starting %s', __name__)
args = environ.get('PYTHON_SERVICE_ARGUMENT', '').split(',')
Logger.debug('SERVICE: received args: %s', args)
if args:
    activity_ip, activity_port, service_port = args[0], int(args[1]), int(args[2])
    activity_address = (activity_ip, activity_port)
else:
    activity_address = ('127.0.0.1', 4999)
    service_port = 5000
osc = OSCSever(activity_address, service_port)
Logger.debug('SERVICE: Started OSC server.')
while True:
    osc.check_pos()
    sleep(.1)
