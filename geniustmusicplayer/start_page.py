from time import time

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock, mainthread
from kivy.logger import Logger
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton
from kivymd.uix.list import OneLineListItem
from kivymd.toast import toast
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineAvatarIconListItem
from android.runnable import run_on_ui_thread

from utils import switch_screen, create_snackbar


class AgeDialogContent(BoxLayout):
    pass


class GenreItem(OneLineAvatarIconListItem):
    divider = None

    def set_icon(self, instance_check):
        instance_check.active = True if not instance_check.active else False


def loading_spinner(pos_hint, active=False):
    from kivymd.uix.spinner import MDSpinner
    loading = MDSpinner(
        size_hint=(None, None),
        size=('30dp', '30dp'),
        pos_hint=pos_hint,
        size_hint_y=None,
    )

    def deactivate_loading(*args):
        loading.active = False
    if not active:
        Clock.schedule_once(deactivate_loading)
    return loading


@run_on_ui_thread
def start_spotify_auth():
    from jnius import autoclass
    app = MDApp.get_running_app()
    mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
    AuthorizationRequestBuilder = autoclass(
        "com.spotify.sdk.android.auth.AuthorizationRequest$Builder"
    )
    AuthorizationClient = autoclass(
        "com.spotify.sdk.android.auth.AuthorizationClient"
    )
    AuthorizationResponseType = autoclass(
        "com.spotify.sdk.android.auth.AuthorizationResponse$Type"
    )
    client_id = "0f3710c5e6654c7983ad32e438f68f9d"
    redirect_uri = "https://geniust.herokuapp.com/callback"
    request_code = app.start_page.request_code

    builder = AuthorizationRequestBuilder(
        client_id,
        AuthorizationResponseType.CODE,
        redirect_uri
    )
    builder.setScopes(["user-top-read"])
    request = builder.build()
    AuthorizationClient.openLoginActivity(mActivity, request_code, request)


@run_on_ui_thread
def start_genius_auth():
    from jnius import autoclass
    app = MDApp.get_running_app()
    mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
    AuthorizationRequestBuilder = autoclass(
        "com.genius.sdk.android.auth.AuthorizationRequest$Builder"
    )
    AuthorizationClient = autoclass(
        "com.genius.sdk.android.auth.AuthorizationClient"
    )
    AuthorizationResponseType = autoclass(
        "com.genius.sdk.android.auth.AuthorizationResponse$Type"
    )
    client_id = "VnApM3tX-j1YzGOTu5pUjs9lzR-2-9qmOeuxHuqTZO0bNFuYEyTZhEjn3K7Aa8Fe"
    redirect_uri = "https://geniust.herokuapp.com/callback"
    request_code = app.start_page.request_code

    builder = AuthorizationRequestBuilder(
        client_id,
        AuthorizationResponseType.CODE,
        redirect_uri
    )
    builder.setScopes(["me"])
    request = builder.build()
    AuthorizationClient.openLoginActivity(mActivity, request_code, request)


@mainthread
def activity_data(requestCode, resultCode, intent):
    from jnius import autoclass
    Logger.debug("ACTIVITY: activity result received.")
    app = MDApp.get_running_app()
    if app.start_page.request_code == requestCode:
        AuthenticationClient = autoclass(
            f"com.{app.start_page.platform}.sdk.android.auth.AuthorizationClient"
        )
        response = AuthenticationClient.getResponse(resultCode, intent)
        if code := response.getCode():
            app.start_page.get_preferences(code, app.start_page.platform)


class GenresDialog:

    def __init__(self, root, callback, genres=None):
        self.root = root
        self.callback = callback
        self.genres = genres if genres is not None else []
        self.genres_dialog = None
        self.app = MDApp.get_running_app()
        self.get_genres_trigger = None
        self.select_genres()

    def select_genres(self):
        if not self.genres_dialog:
            def retry(*args):
                self.retry_event.cancel()
                self.snackbar.dismiss()
                self.select_genres()

            def create_genres_grid(*args):
                if req.status_code != 200:
                    msg = "Failed to get genres. Reyting in 3 seconds."
                    self.snackbar = create_snackbar(msg, retry)
                    self.retry_event = Clock.schedule_once(retry, 3)
                    self.snackbar.open()
                    return
                genres = req.response.get('genres')
                items = []
                for genre in genres:
                    item = GenreItem(text=genre.capitalize())
                    for user_genre in self.genres:
                        if user_genre == genre:
                            item.check.active = True
                    items.append(item)
                self.genres_dialog = MDDialog(
                    title="Favorite Genres",
                    type="confirmation",
                    items=items,
                    buttons=[
                        MDFlatButton(
                            text="CANCEL", text_color=self.app.theme_cls.primary_color,
                            on_release=lambda *args: self.genres_dialog.dismiss()
                        ),
                        MDFlatButton(
                            text="OK", text_color=self.app.theme_cls.primary_color,
                            on_release=lambda *args: self.submit_genres(
                                [x.text.lower()
                                 for x in self.genres_dialog.items
                                 if x.check.active])
                        ),
                    ],
                )
                self.root.remove_widget(self.loading)
                self.genres_dialog.open()

            # Get genres from server
            if self.get_genres_trigger is None:
                self.get_genres_trigger = Clock.create_trigger(create_genres_grid)
            req = self.app.api.get_genres(trigger=self.get_genres_trigger)
            self.loading = loading_spinner(pos_hint={'center_x': .5, 'center_y': .2},
                                           active=True)
            self.root.add_widget(self.loading)
        else:
            self.genres_dialog.open()

    def submit_genres(self, genres):
        self.callback(genres)


class StartPage(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from android.activity import bind
        self.app = MDApp.get_running_app()
        self.age_dialog = None
        self.genres_dialog = None
        self.get_genres_trigger = None
        self.get_preferences_trigger = None
        bind(on_activity_result=activity_data)

    def get_preferences(self, code, platform):
        page = OAuthInfoPage()
        page_name = 'oauth_page'
        switch_screen(page, page_name)

        def retry(*args):
            self.snackbar.dismiss()
            self.retry_event.cancel()
            self.get_preferences(code, platform)
            return

        def get_and_save_preferences(*args):
            if req.status_code == 200:
                self.app.genres = req.response['genres']
                self.app.artists = req.response['artists']
                Logger.debug(self.app.genres)
                if self.app.genres:
                    ArtistsPage().finish()
                else:
                    msg = (f"Sorry, couldn't guess "
                           f"preferences from {platform.capitalize()}")
                    self.snackbar = create_snackbar(msg, callback=None)
                    self.app.screen_manager.switch_to(self.parent)
                    self.snackbar.open()
            else:
                msg = "Failed to get preferences. Retrying in 3 seconds."
                self.snackbar = create_snackbar(msg, retry)
                self.retry_event = Clock.schedule_once(retry, 3)
                self.snackbar.open()

        if self.get_preferences_trigger is None:
            self.get_preferences_trigger = Clock.create_trigger(
                get_and_save_preferences
            )
        req = self.app.api.get_preferences(
            code=code,
            platform=platform,
            trigger=self.get_preferences_trigger
        )

    def select_choice(self, button):
        import random
        self.request_code = random.randint(1, 9999)
        if 'Genius' in button.text:
            self.platform = "genius"
            start_genius_auth()
        else:
            self.platform = "spotify"
            start_spotify_auth()

    def enter_age(self):
        if not self.age_dialog:
            self.age_dialog = MDDialog(
                title="Enter age",
                text="Enter your age and I'll guess your favorite genres.",
                type="custom",
                content_cls=AgeDialogContent(),
                buttons=[
                    MDFlatButton(
                        text="CANCEL", text_color=self.app.theme_cls.primary_color,
                        on_release=lambda *args: self.age_dialog.dismiss()
                    ),
                    MDFlatButton(
                        text="OK", text_color=self.app.theme_cls.primary_color,
                        on_release=lambda *args: self.submit_age(
                            self.age_dialog.content_cls.ids.age_textfield.text)
                    ),
                ],
            )
            self.loading = loading_spinner(pos_hint={'center_x': .5, 'center_y': .2})
            self.age_dialog.add_widget(self.loading)
        self.age_dialog.open()

    def submit_age(self, age):
        try:
            age = int(age)
        except ValueError:
            toast('Invalid age. Try again.')
            return

        def retry(*args):
            self.snackbar.dismiss()
            self.retry_event.cancel()
            self.submit_age(age)
            return

        def get_and_save_genres(*args):
            self.loading.active = False
            if req.status_code == 200:
                self.app.genres = req.response['genres']
                Logger.debug(self.app.genres)
                self.age_dialog.dismiss()
                switch_screen(ArtistsPage(), 'artists_page')
            else:
                msg = "Failed to get genrs. Retrying in 3 seconds."
                self.snackbar = create_snackbar(msg, retry)
                self.retry_event = Clock.schedule_once(retry, 3)
                self.snackbar.open()

        self.loading.active = True
        if self.get_genres_trigger is None:
            self.get_genres_trigger = Clock.create_trigger(get_and_save_genres)
        req = self.app.api.get_genres(age=age, trigger=self.get_genres_trigger)

    def select_genres(self, *args):
        self.genres_dialog = GenresDialog(root=self, callback=self.submit_genres)

    def submit_genres(self, genres):
        Logger.info('GENRES: %s', genres)
        if len(genres) >= 1:
            self.genres_dialog.genres_dialog.dismiss()
            self.app.genres = genres
            switch_screen(ArtistsPage(), 'artists_page')
        else:
            toast('You must at least choose one genre.')


class ArtistsPage(FloatLayout):
    search_hits = None

    def __init__(self, callback=None, **kwargs):
        from kivymd.uix.chip import MDChip
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        self.app.artists_page = self
        self.loading = loading_spinner(pos_hint={'center_x': .5, 'center_y': .5})
        self.finish = callback if callback is not None else self.finish
        self.get_track_trigger = None
        self.add_widget(self.loading)
        for artist in self.app.artists:
            artist_chip = MDChip(
                text=artist,
                text_color=(1, 1, 1, 0.87),
                icon_color=(1, 1, 1, 0.87),
                icon='close',
                on_release=self.remove_artist,
            )
            self.selected_artists.add_widget(artist_chip)

    def save_preferences(self, playlist):
        self.app.db.initialize(
            self.app.genres,
            self.app.artists,
            self.app.songs_path,
            playlist)

    def finish(self):
        def retry(*args):
            self.snackbar.dismiss()
            self.retry_event.cancel()
            self.finish()

        def get_tracks(*args):
            if req.status_code == 200:
                from utils import Playlist
                tracks = req.response
                self.app.playlist = Playlist(tracks, current=0)
                self.save_preferences(self.app.playlist)
                self.app.load_first_page()
            else:
                msg = "Failed to get playlist. Retrying in 3 seconds."
                self.snackbar = create_snackbar(msg, retry)
                self.retry_event = Clock.schedule_once(retry, 3)
                self.snackbar.open()

        self.loading.active = True
        # get playlist
        if self.get_track_trigger is None:
            self.get_track_trigger = Clock.create_trigger(get_tracks)
        req = self.app.api.get_recommendations(
            self.app.genres,
            self.app.artists,
            trigger=self.get_track_trigger,
            async_request=True,
        )

    def remove_artist(self, artist_chip):
        self.app.artists.remove(artist_chip.text)
        self.selected_artists.remove_widget(artist_chip)
        Logger.info("ARTISTS: %s", self.app.artists)

class CustomOneLineListItem(OneLineListItem):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()

    def add_artist(self, artist):
        from kivymd.uix.chip import MDChip
        page = self.app.artists_page
        page.search_layout.ids.search_field.text = ''
        page.search_layout.ids.hits.clear_widgets()

        if artist not in self.app.artists:
            self.app.artists.append(artist)
            artist_chip = MDChip(
                text=artist,
                text_color=(1, 1, 1, 0.87),
                icon_color=(1, 1, 1, 0.87),
                icon='close',
                on_release=page.remove_artist,
            )
            page.selected_artists.add_widget(artist_chip)
        else:
            toast('Artist already selected.')
        Logger.info("ARTISTS: %s", self.app.artists)


class Search(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        self.last_input = time()
        self.current_input = time()
        self.event = Clock.schedule_interval(self.search_artists, 0.01)
        self.loading = loading_spinner(pos_hint={'center_x': .5, 'center_y': .5})
        self.snackbar_retry = False
        self.add_widget(self.loading)

    def register_input(self):
        self.current_input = time()

    def search_artists(self, *args):
        def add_items(*args):
            self.loading.active = False
            self.ids.hits.clear_widgets()
            if req.status_code == 200:
                for artist in req.response['artists']:
                    self.ids.hits.add_widget(CustomOneLineListItem(text=artist))
            else:
                Logger.error('search_artists: failed payload: %s', req.response)
                create_snackbar("Search failed.", self.search_artists).open()
                self.snackbar_retry = True

        text = self.ids.search_field.text
        # start the search when the user stops typing
        if (self.snackbar_retry
                or (len(text) > 2 and self.current_input - self.last_input > 0.3)):
            if self.loading.active is False:
                self.loading.active = True
            self.snackbar_retry = False
            self.last_input = time()
            trigger = Clock.create_trigger(add_items)
            req = self.app.api.search_artists(text, trigger=trigger)
        elif len(text) == 0:
            self.ids.hits.clear_widgets()

# -------------------- OAuth Info --------------------


class OAuthInfoPage(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress_bar.start()
