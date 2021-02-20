from kivymd.app import MDApp
from kivy.uix.floatlayout import FloatLayout
from kivymd.uix.list import TwoLineAvatarIconListItem
from kivymd.uix.menu import MDDropdownMenu
from kivymd.toast import toast


class FavoriteSongListItem(TwoLineAvatarIconListItem):
    def __init__(self, **kwargs):
        song = kwargs.pop('song')
        super().__init__(**kwargs)
        self.text = song.name
        self.secondary_text = song.artist
        self._txt_left_pad = '10dp'
        self.song = song

    def create_song_menu(self):
        from kivymd.uix.bottomsheet import MDListBottomSheet
        song = self.song
        app = MDApp.get_running_app()
        self.song_menu = MDListBottomSheet(radius_from='top')

        # Play song
        if song != app.song.song_object:
            self.song_menu.add_item(
                text="Play",
                callback=lambda *args, song=song: app.favorites_page.play_song(song),
                icon='play')

        # Add to playlist
        self.song_menu.add_item(
            text="Add to playlist",
            callback=lambda *args, song=song: app.favorites_page.playlist_add(song),
            icon='playlist-plus')

        # Spotify
        if song.id_spotify:
            self.song_menu.add_item(
                text="Listen on Spotify",
                callback=lambda x, song=song: toast(repr(song)),
                icon="spotify")

        # Remove from favorites
        self.song_menu.add_item(
            text="Remove from favorites",
            callback=lambda *args, song=song: app.favorites_page.remove_song(song),
            icon='close')


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
        disabled_hint_text_color = self.app.theme_cls.disabled_hint_text_color
        if self.ids.sort_descending.text_color != disabled_hint_text_color:
            descending = True
        else:
            descending = False
        songs = self.app.db.get_favorites()

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
                FavoriteSongListItem(song=song, size_hint=(1, None))
            )

    def playlist_add(self, song, index=-1):
        self.app.playlist = self.app.db.get_playlist()
        if song not in self.app.playlist.tracks:
            if index == -1:
                self.app.playlist.tracks.append(song)
            else:
                self.app.playlist.tracks.insert(index, song)
            self.app.db.add_playlist_track(song, index)
            toast('Song added to playlist')
        else:
            toast('Song already in playlist')

    def play_song(self, song):
        self.app.playlist = self.app.db.get_playlist()
        if song not in self.app.playlist.tracks:
            self.playlist_add(song, index=self.app.playlist.current_track_index + 1)
        self.app.main_page.play_from_playlist(song)

    def remove_song(self, song):
        if song == self.app.song.song_object:
            self.app.main_page.favorite_button.favorited = False
        self.app.favorites.remove(song)
        self.app.db.remove_favorites_track(song)
        self.set_songs()
