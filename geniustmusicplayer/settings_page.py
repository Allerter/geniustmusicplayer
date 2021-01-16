from kivy.uix.floatlayout import FloatLayout
from kivymd.app import MDApp
from kivymd.uix.list import OneLineAvatarIconListItem
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.toast import toast
from kivy.properties import (
    NumericProperty,
)
from kivy.metrics import dp
from kivymd.uix.list import BaseListItem, ContainerSupport

from utils import save_keys, switch_screen


class CustomOneLineIconListItem(OneLineAvatarIconListItem):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._txt_left_pad = '10dp'


class MyBaseListItem(ContainerSupport, BaseListItem):
    _txt_left_pad = NumericProperty("10dp")
    _txt_top_pad = NumericProperty("20dp")
    _txt_bot_pad = NumericProperty("19dp")  # dp(24) - dp(5)
    _height = NumericProperty()
    _num_lines = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.height = dp(56) if not self._height else self._height


class SettingsPage(FloatLayout):
    reset_dialog = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()

    def disable_dark_mode(self):
        # self.app.theme_cls.primary_palette = "Indigo"
        # self.app.theme_cls.accent_palette = "Amber"
        self.app.theme_cls.theme_style = "Light"
        save_keys(dark_mode=False)

    def enable_dark_mode(self):
        # self.app.theme_cls.primary_palette = "Amber"
        # self.app.theme_cls.accent_palette = "Indigo"
        self.app.theme_cls.theme_style = "Dark"
        # self.ids.dark_mode_checkbox.selected_color = self.app.theme_cls.primary_light
        save_keys(dark_mode=True)

    def on_checkbox_active(self, checkbox, value):
        if value:
            self.enable_dark_mode()
        else:
            self.disable_dark_mode()
        drawer = self.app.nav_drawer.children[0].ids.nav_drawer_list
        drawer.set_color_item(drawer.children[0])

    def show_alert_dialog(self):
        if not self.reset_dialog:
            self.reset_dialog = MDDialog(
                text="Reset Preferences?",
                md_bg_color=(1, 1, 1, 1),
                buttons=[
                    MDFlatButton(
                        text="CANCEL", text_color=(0, 0, 0, 0),
                        on_release=lambda *args: self.reset_dialog.dismiss()
                    ),
                    MDFlatButton(
                        text="RESET", text_color=(0, 0, 0, 0),
                        on_release=self.reset_preferences,
                    ),
                ],
            )
        self.reset_dialog.open()

    def reset_preferences(self, *args):
        import start_page
        self.reset_dialog.dismiss()
        self.app.store['user'] = {}
        switch_screen(start_page.StartPage(), 'start_page')
