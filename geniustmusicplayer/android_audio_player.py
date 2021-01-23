from jnius import autoclass, java_method, PythonJavaClass
from android import api_version
from kivy.core.audio import Sound
from kivy.logger import Logger


MediaPlayer = autoclass("android.media.MediaPlayer")
AudioManager = autoclass("android.media.AudioManager")
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
        self.audio_player._mediaplayer.stop()
        self.audio_player.is_complete = True
        self.audio_player.state = 'stop'
        self.audio_player.unload()
        self.audio_player = None


class SoundAndroidPlayer(Sound):
    @staticmethod
    def extensions():
        return ("mp3", "mp4", "aac", "3gp", "flac", "mkv", "wav", "ogg", "m4a",
                "gsm", "mid", "xmf", "mxmf", "rtttl", "rtx", "ota", "imy")

    def __init__(self, **kwargs):
        self._mediaplayer = None
        self._completion_listener = None
        super(SoundAndroidPlayer, self).__init__(**kwargs)

    def load(self):
        self.unload()
        self._mediaplayer = MediaPlayer()
        if api_version >= 21:
            self._mediaplayer.setAudioAttributes(
                AudioAttributesBuilder()
                .setLegacyStreamType(AudioManager.STREAM_MUSIC)
                .build())
        else:
            self._mediaplayer.setAudioStreamType(AudioManager.STREAM_MUSIC)
        self._mediaplayer.setDataSource(self.source)
        self._mediaplayer.prepare()

    def unload(self):
        if self._mediaplayer:
            self._mediaplayer.release()
            self._mediaplayer = None

    def play(self):
        if not self._mediaplayer:
            return
        self._mediaplayer.start()
        if self._completion_listener is None:
            self._completion_listener = OnCompleteListener(self)
            self._mediaplayer.setOnCompletionListener(self._completion_listener)
        super(SoundAndroidPlayer, self).play()

    def stop(self):
        if not self._mediaplayer:
            return
        self._mediaplayer.stop()
        self._mediaplayer.prepare()
        super(SoundAndroidPlayer, self).stop()

    def seek(self, position):
        if not self._mediaplayer:
            return
        self._mediaplayer.seekTo(float(position) * 1000)

    def get_pos(self):
        if self._mediaplayer:
            return self._mediaplayer.getCurrentPosition() / 1000.
        return super(SoundAndroidPlayer, self).get_pos()

    def on_volume(self, instance, volume):
        if self._mediaplayer:
            volume = float(volume)
            self._mediaplayer.setVolume(volume, volume)

    def _get_length(self):
        if self._mediaplayer:
            return self._mediaplayer.getDuration() / 1000.
        return super(SoundAndroidPlayer, self)._get_length()

    def on_loop(self, instance, loop):
        if self._mediaplayer:
            self._mediaplayer.setLooping(loop)
