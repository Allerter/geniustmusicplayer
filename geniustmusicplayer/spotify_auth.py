from kivy.logger import Logger
from jnius import autoclass, java_method, PythonJavaClass
from android.runnable import run_on_ui_thread


class ConnectionListener(PythonJavaClass):
    __javainterfaces__ = ["com/spotify/android/appremote/api/"
                          "Connector$ConnectionListener"]
    __javacontext__ = "app"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @java_method("(Lcom/spotify/android/appremote/api/SpotifyAppRemote;)V")
    def onConnected(self, spotifyAppRemote):
        Logger.info('SP: Connected.')
        print(spotifyAppRemote)
        print(dir(spotifyAppRemote))

    @java_method("(Ljava/lang/Throwable;)V")
    def onFailure(self, throwable):
        Logger.info('SP: Failure. Reason: %s', throwable.getMessage())


@run_on_ui_thread
def start_spotify():
    # ConnectionParams = autoclass("com.spotify.android.appremote.api.ConnectionParams")
    # Connector = autoclass("com.spotify.android.appremote.api.Connector")
    mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
    ConnectionParamsBuilder = autoclass(
        "com.spotify.android.appremote.api.ConnectionParams$Builder"
    )
    SpotifyAppRemote = autoclass("com.spotify.android.appremote.api.SpotifyAppRemote")

    CLIENT_ID = "0f3710c5e6654c7983ad32e438f68f9d"
    REDIRECT_URI = "http://gtplayer.org/callback"

    # mSpotifyAppRemote = SpotifyAppRemote()
    connectionParams = (
        ConnectionParamsBuilder(CLIENT_ID)
        .setRedirectUri(REDIRECT_URI)
        .showAuthView(True)
        .build()
    )
    connection_listener = ConnectionListener()
    SpotifyAppRemote.connect(mActivity, connectionParams, connection_listener)
