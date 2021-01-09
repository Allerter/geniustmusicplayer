from time import time
import secrets
from datetime import timedelta

import requests
import ffmpeg
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.properties import ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.uix.textinput import TextInput
from kivy.logger import Logger
from kivymd.app import MDApp
from kivymd.uix.button import MDRectangleFlatButton, MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineListItem
from kivymd.uix.textfield import MDTextField
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.snackbar import Snackbar

from utils import log, switch_screen


class StartPage(FloatLayout):
    welcome_label = ObjectProperty(None)

    @log
    def select_choice(self, button):
        # self.ids.separator.canvas.clear()
        if button.text == 'Enter Preferences':
            switch_screen(ManualInfoPage(), 'manual_page')
        else:
            unique_value = secrets.token_urlsafe().replace("_", "-")
            if 'Genius' in button.text:
                state = f'genius_android_{unique_value}'
                url = ('https://api.genius.com/oauth/authorize?'
                       'client_id=VnApM3tX-j1YzGOTu5pUjs9lzR-2-9'
                       'qmOeuxHuqTZO0bNFuYEyTZhEjn3K7Aa8Fe'
                       '&redirect_uri=https%3A%2F%2Fgeniust.herokuapp.com%2Fcallback'
                       '&response_type=code'
                       '&scope=me+vote'
                       f'&state={state}')
            else:
                state = f'spotify_android_{unique_value}'
                url = ('https://accounts.spotify.com/authorize?'
                       'client_id=0f3710c5e6654c7983ad32e438f68f9d'
                       '&redirect_uri=http%3A%2F%2Fgeniust.herokuapp.com%2Fcallback'
                       '&response_type=code'
                       '&scope=user-top-read'
                       '&show_dialog=true'
                       f'&state={state}')
            print('sending state to webserver')
            # webbrowser.open(url)
            switch_screen(OAuthInfoPage(), 'auth_page')


# -------------------- Manual Info --------------------


class ManualInfoPage(FloatLayout):
    original_color = ListProperty([])
    error_label = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        self.genres_displayed = False
        self.input_displayed = False

    @log
    def enter_age(self, button):

        def button_pos(widget, button, values):
            button.pos = (values[0] + widget.size[0] + 15,
                          values[1])

        if self.input_displayed:
            text = self.input_widget.text
            try:
                age = int(text)
            except ValueError:
                if self.error_label is None:
                    self.error_label = MDLabel(
                        pos_hint={'center_x': .51, 'center_y': .55},
                        text='Invalid age. Try again.',
                        theme_text_color='Custom',
                        text_color=get_color_from_hex('ff0000'),)
                    self.add_widget(self.error_label)
                return

            def get_and_save_genres(*args):
                self.app.genres = req.response['genres']
                Logger.debug(self.app.genres)
            trigger = Clock.create_trigger(get_and_save_genres)
            req = self.app.api.get_genres(age=age, trigger=trigger)
            switch_screen(ArtistsPage(), 'artists_page')
        else:
            self.input_displayed = True
            self.ids.age_genre_text.text = 'Enter your age, e.g. 24'
            self.remove_widget(self.button_grid)
            self.input_widget = input_widget = TextInput(
                pos_hint={'center_x': .35, 'center_y': .6},
                size_hint=(0.6, 0.05),
                # required=True,
                # helper_text_mode="on_error",
                on_text_validate=self.enter_age,
                multiline=False,
            )
            submit_button = MDRaisedButton(
                text='Submit',
                on_release=self.enter_age
            )
            input_widget.bind(focus=self.delete_error_label)
            input_widget.bind(
                pos=lambda widget, values: button_pos(widget, submit_button, values))
            self.add_widget(input_widget)
            self.add_widget(submit_button)

            @log
            def show_keyboard(event):
                input_widget.focus = True
            Clock.schedule_once(show_keyboard, 0.2)

    @log
    def delete_error_label(self, *_):
        if self.error_label:
            self.remove_widget(self.error_label)
            self.error_label = None

    @log
    def select_genres(self, button):
        if self.genres_displayed:
            if self.app.genres:
                switch_screen(ArtistsPage(), 'artists_page')
            else:
                if self.error_label is None:
                    self.error_label = MDLabel(
                        pos_hint={'center_x': .51, 'center_y': .25},
                        text='You must at least choose one genre.',
                        theme_text_color='Custom',
                        text_color=get_color_from_hex('ff0000'),
                    )
                    self.add_widget(self.error_label)
        else:
            def retry(*args):
                self.snackbar.dismiss()
                self.select_genres(None)

            def create_genres_grid(*args):
                self.remove_widget(self.loading)
                genres = req.response.get('genres')
                Logger.debug('Fetched Genres: %s', genres)
                if not genres:
                    self.snackbar = snackbar = Snackbar(
                        text="Couldn't get genres.",
                        snackbar_x="10dp",
                        snackbar_y="10dp",
                    )
                    snackbar.size_hint_x = (
                        Window.width - (snackbar.snackbar_x * 2)
                    ) / Window.width
                    snackbar.buttons = [
                        MDFlatButton(
                            text="RETRY",
                            text_color=(1, 1, 1, 1),
                            on_release=retry,
                        ),
                    ]
                    snackbar.open()
                    return

                genres_grid = GridLayout(
                    cols=3,
                    spacing=15,
                    size_hint_y=None,
                    size_hint=(0.9, None),
                    pos_hint={'center_x': .5, 'center_y': .5}
                )
                for genre in genres:
                    button = MDRectangleFlatButton(text=genre.capitalize(),
                                                   on_press=self.genre_selected,
                                                   size_hint=(.3, None))
                    genres_grid.add_widget(button)
                self.original_color = genres_grid.children[0].md_bg_color
                self.add_widget(genres_grid)
                self.genres_displayed = True

            # Get genres from server
            trigger = Clock.create_trigger(create_genres_grid)
            req = self.app.api.get_genres(trigger=trigger)
            if button is not None:
                self.loading = MDSpinner(
                    size_hint=(None, None),
                    size=('30dp', '30dp'),
                    pos_hint={'center_x': .5, 'center_y': .5},
                    size_hint_y=None,
                    active=True,
                )
                self.add_widget(self.loading)

                # Edit button
                button.text = 'Submit'
                # button.fade_out()
                self.button_grid.remove_widget(self.age_button)

    @log
    def genre_selected(self, button):
        genre = button.text
        if genre in self.app.genres:
            button.md_bg_color = self.original_color
            self.app.genres.remove(genre)
        else:
            if self.error_label:
                self.remove_widget(self.error_label)
                self.error_label = None
            button.md_bg_color = get_color_from_hex('0eea4c')
            self.app.genres.append(genre)


class ArtistsPage(FloatLayout):
    search_hits = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        self.app.artists_page = self

    def finish(self):
        import main

        # save user preferences
        self.app.store.put(
            'user',
            genres=self.app.genres,
            artists=self.app.artists,
            volume=self.app.volume,
            playlist=self.app.playlist.tracks,
        )
        switch_screen(main.LoadingPage(), 'loading_page')
        # get playlist
        tracks = self.app.api.get_recommendations(
            self.app.genres,
            self.app.artists,
            has_preview_url=True,
            async_request=False,
        ).response
        self.app.playlist = main.Playlist(tracks)
        self.app.main_page = main.MainPage()
        song = self.app.playlist.next()
        self.app.play_button.load_song(song)
        self.app.main_page.edit_ui_for_song()
        switch_screen(self.app.main_page, 'main_page')

class CustomOneLineListItem(OneLineListItem):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()

    @log
    def add_artist(self, artist):
        if artist not in self.app.artists:
            self.app.artists.append(artist)
        page = self.app.artists_page

        page.search_layout.ids.search_field.text = ''
        page.search_layout.ids.rv.data = []
        page.artists_label.text = f"[b]Artists:[/b] {', '.join(self.app.artists)}"

class Search(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        self.last_input = time()
        self.current_input = time()
        self.event = Clock.schedule_interval(self.search_artists, 0.1)
        self.loading = MDSpinner(
            size_hint=(None, None),
            size=('30dp', '30dp'),
            pos_hint={'center_x': .5, 'center_y': .5},
            size_hint_y=None,
            active=False,
        )

    def register_input(self):
        self.current_input = time()

    @log
    def search_artists(self, *args):
        def add_items(*args):
            self.loading.active = False
            self.ids.rv.data = []
            for artist in req.response['artists']:
                self.ids.rv.data.append(
                    {
                        "viewclass": "CustomOneLineListItem",
                        "text": artist,
                    }
                )
        text = self.ids.search_field.text
        # start the search when the user stops typing
        if len(text) > 2 and self.current_input - self.last_input > 0.3:
            if self.loading.active is False:
                self.loading.active = True
            self.last_input = time()
            trigger = Clock.create_trigger(add_items)
            req = self.app.api.search_artists(text, trigger=trigger)

# -------------------- OAuth Info --------------------


class OAuthInfoPage(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress_bar.start()
