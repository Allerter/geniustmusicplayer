from kivy.uix.floatlayout import FloatLayout
from kivymd.app import MDApp
from kivymd.uix.list import OneLineAvatarIconListItem
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import IRightBodyTouch
from kivymd.uix.button import MDRoundFlatButton
from kivymd.uix.menu import MDDropdownMenu
from kivy.properties import (
    NumericProperty,
)
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivy.logger import Logger
from kivymd.uix.list import BaseListItem, ContainerSupport

from utils import switch_screen


class CustomOneLineIconListItem(OneLineAvatarIconListItem):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._txt_left_pad = '10dp'


class Container(IRightBodyTouch, MDBoxLayout):
    adaptive_width = True


class MyBaseListItem(ContainerSupport, BaseListItem):
    _txt_left_pad = NumericProperty("10dp")
    _txt_top_pad = NumericProperty("20dp")
    _txt_bot_pad = NumericProperty("19dp")  # dp(24) - dp(5)
    _height = NumericProperty()
    _num_lines = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.height = dp(56) if not self._height else self._height


class SongModeMenu(MDDropdownMenu):

    def set_item(self, instance_menu, instance_menu_item):
        self.screen.ids.drop_item.set_item(instance_menu_item.text)
        self.menu.dismiss()

class SettingsPage(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        menu_items = [
            {"text": "Any"},
            {"text": "Previews"},
            {"text": "Full Songs"}

        ]

        def unavailable(*args):
            toast('Play mode not available. Try again later.')
            self.menu.dismiss()
        self.menu = MDDropdownMenu(
            caller=self.ids.drop_item,
            items=menu_items,
            position="bottom",
            width_mult=4,
        )
        self.menu.bind(
            on_release=unavailable
            # self.set_play_mode
        )

    def set_play_mode(self, instance_menu, instance_menu_item):
        self.ids.drop_item.set_item(instance_menu_item.text)
        self.menu.dismiss()
        mode = self.ids.drop_item.current_item
        if mode == 'Any':
            mode = 'any_file'
        elif mode == 'Previews':
            mode = 'preview'
        else:
            mode = 'full'
        self.app.db.update_play_mode(mode)
        self.app.play_mode = mode
        Logger.info('PLAY MODE: %s', mode)

    def get_play_mode_text(self, mode):
        if mode == 'any_file':
            mode = 'Any'
        elif mode == 'preview':
            mode = 'Previews'
        else:
            mode = 'Full Songs'
        return mode

    def disable_dark_mode(self):
        # self.app.theme_cls.primary_palette = "Indigo"
        # self.app.theme_cls.accent_palette = "Amber"
        self.app.theme_cls.theme_style = "Light"
        self.app.db.update_dark_mode(False)
        self.app.dark_mode = False

    def enable_dark_mode(self):
        # self.app.theme_cls.primary_palette = "Amber"
        # self.app.theme_cls.accent_palette = "Indigo"
        self.app.theme_cls.theme_style = "Dark"
        # self.ids.dark_mode_checkbox.selected_color = self.app.theme_cls.primary_light
        self.app.db.update_dark_mode(True)
        self.app.dark_mode = True

    def open_genres(self, *args):
        import start_page
        self.genres_dialog = start_page.GenresDialog(
            root=self,
            callback=self.submit_genres,
            genres=self.app.genres,
        )
        self.genres_dialog.select_genres()

    def submit_genres(self, genres):
        Logger.info('GENRES: %s', genres)
        if genres:
            self.genres_dialog.genres_dialog.dismiss()
            self.app.genres = genres
            self.app.db.update_genres(genres)
            toast('Updated Favorite genres.')
        else:
            toast('You must at least choose one genre.')

    def open_artists(self, *args):
        import start_page
        self.artists_screen = artists_screen = Screen(name='artists_page')
        artists_page = start_page.ArtistsPage(
            callback=self.submit_artists,
        )
        artists_page.add_widget(MDRoundFlatButton(
            text='CANCEL',
            pos_hint={'center_x': 0.2, 'center_y': 0.1},
            on_press=self.cancel_artists,
        ))
        artists_screen.add_widget(artists_page)
        self.app.screen_manager.add_widget(artists_screen)
        self.app.screen_manager.current = 'artists_page'

    def submit_artists(self):
        Logger.info('ARTISTS: %s', self.app.artists)
        self.app.db.update_artists(self.app.artists)
        self.app.screen_manager.current = 'settings_page'
        self.app.screen_manager.remove_widget(self.artists_screen)
        toast('Updated favorite artists.')

    def cancel_artists(self, *args):
        self.app.screen_manager.current = 'settings_page'
        self.app.screen_manager.remove_widget(self.artists_screen)

    def on_checkbox_active(self, checkbox, value):
        if value:
            self.enable_dark_mode()
        else:
            self.disable_dark_mode()
        drawer = self.app.nav_drawer.children[0].ids.nav_drawer_list
        drawer.set_color_item(drawer.children[0])

    def show_alert_dialog(self):
        self.reset_dialog = MDDialog(
            text="Reset Preferences?",
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=lambda *args: self.reset_dialog.dismiss(),
                ),
                MDFlatButton(
                    text="RESET",
                    on_release=self.reset_preferences,
                ),
            ],
        )
        self.reset_dialog.open()

    def reset_preferences(self, *args):
        import start_page
        self.reset_dialog.dismiss()
        self.app.db.delete_user()
        switch_screen(start_page.StartPage(), 'start_page')
