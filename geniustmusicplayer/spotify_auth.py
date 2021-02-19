import random

from jnius import autoclass
from android.runnable import run_on_ui_thread


@run_on_ui_thread
def start_spotify():
    # ConnectionParams = autoclass("com.spotify.android.appremote.api.ConnectionParams")
    # Connector = autoclass("com.spotify.android.appremote.api.Connector")
    mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
    AuthenticationRequestBuilder = autoclass(
        "com.spotify.auth.AuthenticationRequest$Builder"
    )
    AuthenticationResponse = autoclass(
        "com.spotify.sdk.android.authentication.AuthenticationResponse"
    )
    AuthenticationClient = autoclass(
        "com.spotify.sdk.android.authentication.AuthenticationClient"
    )

    CLIENT_ID = "0f3710c5e6654c7983ad32e438f68f9d"
    REDIRECT_URI = "http://gtplayer.org/callback"
    REQUEST_CODE = random.randint(1, 9999)

    builder = AuthenticationRequestBuilder(
        CLIENT_ID,
        AuthenticationResponse.Type.TOKEN,
        REDIRECT_URI
    )
    builder.setScopes(["user-top-read"])
    request = builder.build()
    AuthenticationClient.openLoginActivity(mActivity, REQUEST_CODE, request)
    return REQUEST_CODE
