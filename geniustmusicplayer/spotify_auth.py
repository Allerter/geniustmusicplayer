import logging

from jnius import autoclass, java_method, PythonJavaClass

logging.basicConfig(format="%(levelname)s - %(message)s")
Logger = logging.getLogger('spotify')
Logger.setLevel(logging.DEBUG)


class ConnectionListener(PythonJavaClass):
    __javainterfaces__ = ["com/spotify/android/appremote/api/"
                          "Connector$ConnectionListener"]
    __javacontext__ = "app"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Logger.debug('SP: Initialized.')

    @java_method("(Lcom/spotify/android/appremote/api/SpotifyAppRemote;)V")
    def onConnected(self, spotifyAppRemote):
        Logger.info('SP: Connected.')
        print(spotifyAppRemote)
        print(dir(spotifyAppRemote))

    @java_method("(Ljava/lang/Throwable;)V")
    def onFailure(self, throwable):
        Logger.info('SP: Failure. Reason: %s', throwable.getMessage())


# ConnectionParams = autoclass("com.spotify.android.appremote.api.ConnectionParams")
# Connector = autoclass("com.spotify.android.appremote.api.Connector")
mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
ConnectionParamsBuilder = autoclass(
    "com.spotify.android.appremote.api.ConnectionParams$Builder"
)
SpotifyAppRemote = autoclass("com.spotify.android.appremote.api.SpotifyAppRemote")

CLIENT_ID = "0f3710c5e6654c7983ad32e438f68f9d"
REDIRECT_URI = "org.allerter.geniustmusicplayer://callback"

mSpotifyAppRemote = SpotifyAppRemote()
connectionParams = (
    ConnectionParamsBuilder(CLIENT_ID)
    .setRedirectUri(REDIRECT_URI)
    .showAuthView(True)
    .build()
)
connection_listener = ConnectionListener()
SpotifyAppRemote.connect(mActivity, connectionParams, connection_listener)
