from kivy.properties import StringProperty
from kivymd.app import MDApp
from kivy.uix.floatlayout import FloatLayout
from kivymd.uix.list import OneLineAvatarIconListItem
from kivymd.uix.menu import RightContent
from kivymd.uix.button import MDIconButton
from kivymd.uix.menu import MDDropdownMenu
from kivymd.toast import toast
from kivy.utils import rgba

from utils import create_snackbar, save_favorites


class CustomOneLineIconListItem(OneLineAvatarIconListItem):
    def __init__(self, **kwargs):
        song = kwargs.pop('song')
        super().__init__(**kwargs)
        self.text = song.name
        self.right_content = FavoriteItemRightContent(song=song)
        self.add_widget(self.right_content)
        self._txt_left_pad = '10dp'


class FavoriteItemRightContent(RightContent):
    def __init__(self, **kwargs):
        app = MDApp.get_running_app()
        song = kwargs.pop('song')
        super().__init__(**kwargs)

        add_button = MDIconButton(
            size_hint=(None, None),
            user_font_size='16sp',
            pos_hint={'center_y': 0.5},
            icon='playlist-plus',
            on_release=lambda *args: app.favorites_page.playlist_add(song)
        )
        self.add_widget(add_button)

        remove_button = MDIconButton(
            icon='close-box',
            user_font_size="16sp",
            pos_hint={"center_y": .5},
            on_release=lambda *args: app.favorites_page.remove_song(song),
        )
        self.add_widget(remove_button)

class SortMenu(MDDropdownMenu):

    def set_item(self, instance_menu, instance_menu_item):
        self.screen.ids.drop_item.set_item(instance_menu_item.text)
        self.menu.dismiss()


class FavoritesPage(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        menu_items = [
            {"text": "Date Added"},
            {"text": "Song Title"},
            {"text": "Artist Name"}

        ]
        self.menu = MDDropdownMenu(
            caller=self.ids.drop_item,
            items=menu_items,
            position="bottom",
            width_mult=4,
        )
        self.menu.bind(on_release=self.set_sort)
        self.set_songs()

    def set_sort(self, instance_menu, instance_menu_item):
        self.ids.drop_item.set_item(instance_menu_item.text)
        self.menu.dismiss()
        self.set_songs()

    def set_songs(self):
        sort = self.ids.drop_item.current_item
        if self.ids.sort_descending.text_color == self.app.theme_cls.primary_color:
            descending = True
        else:
            descending = False
        songs = self.app.favorites

        def sort_by(song):
            if sort == 'Date Added':
                return song.date_favorited
            elif sort == 'Song Title':
                return song.name
            else:
                return song.artist
        songs.sort(reverse=descending, key=lambda x: sort_by(x))
        self.ids.favorites_list.clear_widgets()
        for song in songs:
            self.ids.favorites_list.add_widget(
                CustomOneLineIconListItem(song=song)
            )

    def playlist_add(self, song):
        if song not in self.app.playlist.tracks:
            self.app.playlist.tracks.append(song)
            toast('Song added to playlist')
        else:
            toast('Song already in playlist')

    def remove_song(self, song):
        if song == self.app.song.song_object:
            self.app.main_page.favorite_button.favorited = False
        self.app.favorites.remove(song)
        save_favorites(self.app.favorites)
        self.set_songs()
