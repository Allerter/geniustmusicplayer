from jnius import cast, autoclass, java_method, PythonJavaClass
from android import api_version
import logging
# from kivy.core.audio import Sound
# from kivy.logger import Logger
Logger = logging.getLogger('gtplayer')

NativeInvocationHandler = autoclass('org.jnius.NativeInvocationHandler')
MediaPlayer = autoclass("android.media.MediaPlayer")
AudioManager = autoclass("android.media.AudioManager")
PowerManager = autoclass("android.os.PowerManager")
# service = autoclass('org.allerter.geniustmusicplayer.ServiceMyService').mService
# PythonActivity = autoclass('org.kivy.android.PythonActivity')
# currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
# app_context = cast('android.content.Context', currentActivity.getApplicationContext())
if api_version >= 21:
    AudioAttributesBuilder = autoclass("android.media.AudioAttributes$Builder")


class OnCompleteListener(PythonJavaClass):
    __javainterfaces__ = ["android/media/MediaPlayer$OnCompletionListener"]
    __javacontext__ = "app"

    def __init__(self, audio_player, **kwargs):
        super().__init__(**kwargs)
        self.called = False
        self.audio_player = audio_player

    @java_method("(Landroid/media/MediaPlayer;)V")
    def onCompletion(self, mp):
        Logger.info('AUDIO: Playback completed.')
        self.audio_player.is_complete = True
        self.audio_player.state = 'stop'
        # self.audio_player.unload()
        self.audio_player.on_complete_callback()


class SoundAndroidPlayer:
    @staticmethod
    def extensions():
        return ("mp3", "mp4", "aac", "3gp", "flac", "mkv", "wav", "ogg", "m4a",
                "gsm", "mid", "xmf", "mxmf", "rtttl", "rtx", "ota", "imy")

    def __init__(self, on_complete_callback, **kwargs):
        self._mediaplayer = None
        self.on_complete_callback = on_complete_callback
        self._volume = 0
        self.source = None
        self._mediaplayer = MediaPlayer()
        self.is_prepared = False
        self.unloaded = False
        # self._mediaplayer.setWakeMode(app_context, PowerManager.PARTIAL_WAKE_LOCK)
        if api_version >= 21:
            self._mediaplayer.setAudioAttributes(
                AudioAttributesBuilder()
                .setLegacyStreamType(AudioManager.STREAM_MUSIC)
                .build())
        else:
            self._mediaplayer.setAudioStreamType(AudioManager.STREAM_MUSIC)
        self._completion_listener = OnCompleteListener(self)
        self._mediaplayer.setOnCompletionListener(self._completion_listener)

    def load(self, filename):
        self.is_prepared = False
        self.unloaded = False
        self.source = filename
        self._mediaplayer.setDataSource(filename)
        self._mediaplayer.prepare()
        self.is_prepared = True

    def unload(self):
        self._mediaplayer.release()
        self.is_prepared = False
        self.unloaded = True

    def play(self):
        if not self.is_prepared:
            self._mediaplayer.prepare()
        self._mediaplayer.start()

    def stop(self):
        self._mediaplayer.pause()
        self.unload()

    def seek(self, position):
        self._mediaplayer.seekTo(float(position) * 1000)

    def get_pos(self):
        return self._mediaplayer.getCurrentPosition() / 1000.

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, volume):
        volume = float(volume)
        self._mediaplayer.setVolume(volume, volume)
        self._volume = volume

    def _get_length(self):
        return self._mediaplayer.getDuration() / 1000.

    @property
    def length(self):
        return self._get_length()

    @property
    def state(self):
        return 'play' if self._mediaplayer.isPlaying() else 'stop'

    def on_loop(self, instance, loop):
        self._mediaplayer.setLooping(loop)
