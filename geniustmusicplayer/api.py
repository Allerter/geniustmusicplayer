from typing import Optional, List
from urllib import parse

from kivy.logger import Logger
from kivy.network.urlrequest import UrlRequest


class Song:
    def __init__(self, id, name, artist, genres=None,
                 id_spotify=None, isrc=None, cover_art=None,
                 preview_url=None, download_url=None, preview_file=None,
                 download_file=None, date_favorited=None,):
        self.id = id
        self.name = name
        self.artist = artist
        self.genres = genres if genres else []
        self.id_spotify = id_spotify
        self.isrc = isrc
        self.cover_art = (cover_art
                          if cover_art is not None
                          else 'images/empty_coverart.png'
                          )
        self.preview_url = preview_url
        self.download_url = download_url
        self.preview_file = preview_file
        self.download_file = download_file
        self.date_favorited = date_favorited

    def to_dict(self):
        return dict(
            id=self.id,
            name=self.name,
            artist=self.artist,
            id_spotify=self.id_spotify,
            isrc=self.isrc,
            cover_art=self.cover_art,
            preview_url=self.preview_url,
            download_url=self.download_url,
            preview_file=self.preview_file,
            download_file=self.download_file,
            date_favorited=self.date_favorited,
        )

    def __eq__(self, other):
        if isinstance(other, Song) and self.id == other.id:
            return True
        else:
            return False

    def __repr__(self):
        return f'Song(artist={self.artist!r}, song={self.name!r})'

class Response:

    def __init__(self, trigger, context: dict = None):
        self.response = None
        self.is_finished = False
        self.status_code = 0
        self.trigger = trigger
        self.context = context if context else {}
        Logger.debug('Response: Response object with trigger %s', trigger)

    def on_finish(self, req, result):
        Logger.debug('%s status code for %s', req.resp_status, req.url)
        self.is_finished = True
        self.status_code = req.resp_status
        if self.status_code == 200:
            if req.url.startswith('https://geniust.herokuapp.com/api/recommendations'):
                self.response = [Song(**x) for x in result['response']['tracks']]
            elif not req.url.startswith(Sender.API_ROOT):
                # self.context['song'].preview_raw = result.content
                self.response = result
            else:
                self.response = result['response']
        else:
            pass
            Logger.debug('request payload: %s', result)

        if self.trigger is not None:
            Logger.debug('Trigger: Activated for %s', req.url)
            self.trigger()

    def __repr__(self):
        return (f'Response(is_finished={self.is_finished},'
                f' trigger={True if self.trigger else False}')


class Sender:
    """Sends HTTP requests."""
    # Create a persistent requests connection
    API_ROOT = 'https://geniust.herokuapp.com/api/'

    def __init__(
        self,
        timeout=5,
        sleep_time=0.2,
        retries=0
    ):
        self.headers = {
            'application': 'GeniusT Music Player',
        }
        self.timeout = timeout
        self.sleep_time = sleep_time
        self.retries = retries

    def make_request(
        self,
        path,
        params=None,
        method='GET',
        web=False,
        trigger=None,
        async_request: bool = True,
        api: bool = True,
        timeout=None,
        **kwargs
    ):
        """Makes a request to Genius."""
        if api:
            url = self.API_ROOT + path
        else:
            url = path

        params = params if params else {}

        for key in list(params):
            if params[key] is None:
                params.pop(key)
        url_parse = parse.urlparse(url)
        query = url_parse.query
        url_dict = dict(parse.parse_qsl(query))
        url_dict.update(params)
        url_new_query = parse.urlencode(url_dict)
        url_parse = url_parse._replace(query=url_new_query)
        new_url = parse.urlunparse(url_parse)

        # Make the request
        response = Response(trigger, context=kwargs)
        req = UrlRequest(new_url,
                         on_success=response.on_finish,
                         on_failure=response.on_finish,
                         on_error=response.on_finish,
                         req_headers=self.headers,
                         timeout=timeout or self.timeout,
                         debug=True,
                         verify=False,
                         )
        response.is_finished = req.is_finished
        # #Logger.debug('request to %s', new_url)

        # Enforce rate limiting
        # time.sleep(self.sleep_time)

        if not async_request:
            req.wait()

        return response


class API():
    def __init__(self):
        timeout = 7
        retries = 2
        sleep_time = 0.2
        self.sender = Sender(sleep_time=sleep_time, timeout=timeout, retries=retries)

    def get_genres(
        self,
        age: Optional[int] = None,
        trigger=None,
        async_request: bool = True
    ) -> List[str]:
        params = {'age': age}
        res = self.sender.make_request(
            'genres',
            params=params,
            trigger=trigger,
            async_request=async_request
        )

        return res

    def get_recommendations(
        self,
        genres: List[str],
        artists: Optional[List[str]] = None,
        song_type='any_file',
        trigger=None,
        async_request: bool = True,
        timeout=None,
    ) -> List[str]:
        params = {
            'genres': ','.join(genres),
        }
        if artists:
            params['artists'] = ','.join(artists)
        params['song_type'] = 'preview'  # song_type
        res = self.sender.make_request(
            'recommendations',
            params=params,
            trigger=trigger,
            async_request=async_request,
            timeout=timeout,
        )

        return res

    def search_artists(
        self,
        artist: str,
        trigger=None,
        async_request: bool = True
    ) -> List[str]:
        params = {'artist': artist}
        res = self.sender.make_request(
            'search',
            params=params,
            trigger=trigger,
            async_request=async_request
        )

        return res

    def download_preview(
        self,
        song: Song,
        trigger=None,
        async_request: bool = True
    ) -> List[str]:
        res = self.sender.make_request(
            song.preview_url,
            # song=song,
            trigger=trigger,
            async_request=async_request,
            api=False,
        )

        return res
