import random

from kivymd.app import MDApp
from jnius import autoclass
from android.runnable import run_on_ui_thread


@run_on_ui_thread
def start_spotify():
    # ConnectionParams = autoclass("com.spotify.android.appremote.api.ConnectionParams")
    # Connector = autoclass("com.spotify.android.appremote.api.Connector")
    mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
    AuthorizationRequestBuilder = autoclass(
        "com.spotify.sdk.android.auth.AuthorizationRequest$Builder"
    )
    AuthorizationResponse = autoclass(
        "com.spotify.sdk.android.auth.AuthorizationResponse"
    )
    AuthorizationClient = autoclass(
        "com.spotify.sdk.android.auth.AuthorizationClient"
    )
    AuthorizationResponseType = autoclass(
        "com.spotify.sdk.android.auth.AuthorizationResponse$Type"
    )
    client_id = "0f3710c5e6654c7983ad32e438f68f9d"
    redirect_uri = "http://gtplayer.org/callback"
    request_code = random.randint(1, 9999)
    MDApp.get_running_app().request_code = request_code

    builder = AuthorizationRequestBuilder(
        client_id,
        AuthorizationResponseType.CODE,
        redirect_uri
    )
    builder.setScopes(["user-top-read"])
    request = builder.build()
    AuthorizationClient.openLoginActivity(mActivity, request_code, request)
