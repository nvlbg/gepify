import gepify
from . import GepifyTestCase
from flask import url_for, session, g
import spotipy
from urllib import parse
from unittest import mock
from gepify.services import spotify
import json
import os


class MockResponse:
    def __init__(self, data, status_code):
        self.text = json.dumps(data)
        self.status_code = status_code


def mocked_spotify_api_post(url, **kwargs):
    data = kwargs.get('data', None)
    headers = kwargs.get('headers', None)

    if url == 'https://accounts.spotify.com/api/token':
        assert 'Authorization' in headers
        assert headers['Authorization'].startswith('Basic')
        assert 'grant_type' in data
        assert data['grant_type'] in ['authorization_code', 'refresh_token']

        if data['grant_type'] == 'authorization_code':
            assert 'code' in data
            assert 'redirect_uri' in data

            return MockResponse({
                'access_token': 'dummy code',
                'refresh_token': 'refresh me',
                'expires_in': 60
            }, 200)
        else:
            assert 'refresh_token' in data
            assert data['refresh_token'] == 'refresh me'

            return MockResponse({
                'access_token': 'new dummy code',
                'refresh_token': 'refresh me again',
                'expires_in': 60
            }, 200)

    return MockResponse({}, 404)


def mocked_spotify_api_404(*args, **kwargs):
    return MockResponse({}, 404)


class MockSpotipy:
    def __init__(self, auth=None):
        self.auth = auth

    def me(self):
        return {
            'id': 'test_user'
        }

    def user_playlists(self, username):
        with open('tests/spotify_dump/spotify_user_playlists.json') as f:
            return json.loads(f.read())

    def user_playlist(self, username, playlist_id, fields=None):
        if username == 'test_user' and playlist_id == '1':
            with open('tests/spotify_dump/spotify_user_playlist.json') as f:
                return json.loads(f.read())

    def current_user_saved_albums(self):
        with open('tests/spotify_dump/'
                  'spotify_current_user_saved_albums.json') as f:
            return json.loads(f.read())

    def album(self, album_id):
        if album_id == '0AYlrY39QmCNwR4r1uzlv3':
            with open('tests/spotify_dump/spotify_album.json') as f:
                return json.loads(f.read())

    def next(self, result):
        if result['next'] == 'https://api.spotify.com/v1/users/aplusk' + \
                             '/playlists/5ExcrV72XoJ6aQT8plfau3/' + \
                             'tracks?offset=100&limit=100':
            with open('tests/spotify_dump/spotify_next.json') as f:
                return json.loads(f.read())


class ProfileMixin():
    @mock.patch('requests.post', side_effect=mocked_spotify_api_post)
    def login(self, *args):
        login_response = self.client.get(url_for('spotify.login'))
        spotify_redirect = login_response.location
        self.assertTrue(spotify_redirect.startswith(
                            'https://accounts.spotify.com/authorize'))

        params = parse.parse_qs(parse.urlparse(spotify_redirect).query)

        response = self.client.get(url_for(
            'spotify.callback', code='dummy code', state=params['state'][0]
        ))
        self.assertRedirects(response, url_for('spotify.index'))
        return response

    @mock.patch('requests.post', side_effect=mocked_spotify_api_post)
    def logout(self, *args):
        logout_response = self.client.get(url_for('spotify.logout'))
        self.assertRedirects(logout_response, url_for('views.index'))
        return logout_response


@mock.patch('requests.post', side_effect=mocked_spotify_api_post)
class SpotifyDecoratorsTestCase(GepifyTestCase, ProfileMixin):
    @mock.patch('logging.Logger')
    def test_login_required_decorator(self, *args):
        @self.app.route('/test')
        @spotify.view_decorators.login_required
        def test():
            return 'You should be logged in to read this'

        response = self.client.get('/test')
        self.assertRedirects(response, url_for('spotify.login'))

        login_response = self.login()

        response = self.client.get('/test')
        self.assert200(response)
        self.assertIn(b'You should be logged in to read this', response.data)

        with self.client.session_transaction() as sess:
            sess['spotify_refresh_token'] = 'false token'
            sess['spotify_expires_at'] = -1

        response = self.client.get('/test')
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'There was an error with authenticating', response.data)

        self.logout()

        response = self.client.get('/test')
        self.assertRedirects(response, url_for('spotify.login'))

    def test_login_required_if_spotify_session_has_expired(self, post):
        @self.app.route('/test')
        @spotify.view_decorators.login_required
        def test():
            return 'You should be logged in to read this'

        with self.client as client:
            self.login()

            old_token = session['spotify_access_token']
            old_refresh_token = session['spotify_refresh_token']

            with client.session_transaction() as sess:
                sess['spotify_expires_at'] = -1

            response = self.client.get('/test')
            new_token = session['spotify_access_token']
            new_refresh_token = session['spotify_refresh_token']

            self.assertEqual(old_token, 'dummy code')
            self.assertEqual(old_refresh_token, 'refresh me')
            self.assertEqual(new_token, 'new dummy code')
            self.assertEqual(new_refresh_token, 'refresh me again')

    def test_logout_required_decorator(self, post):
        @self.app.route('/test')
        @spotify.view_decorators.logout_required
        def test():
            return 'You should be logged out to read this'

        response = self.client.get('/test')
        self.assert200(response)
        self.assertIn(b'You should be logged out to read this', response.data)

        login_response = self.login()

        response = self.client.get('/test')
        self.assert403(response)
        self.assertIn(
            b'You need to be logged out to see this page', response.data)

        self.logout()

        response = self.client.get('/test')
        self.assert200(response)
        self.assertIn(b'You should be logged out to read this', response.data)


class SpotifyModelsTestCase(GepifyTestCase):
    def setUp(self):
        g.spotipy = MockSpotipy()

    def tearDown(self):
        g.spotipy = None

    @mock.patch('requests.post', side_effect=mocked_spotify_api_post)
    def test_request_access_token_with_authorization_code_request(self, post):
        payload = {
            'grant_type': 'authorization_code',
            'code': '',
            'redirect_uri': ''
        }

        with self.client.session_transaction() as sess:
            sess['spotify_access_token'] = 'some random test token'
            sess['spotify_refresh_token'] = 'some random refresh token'
        self.assertNotIn('spotify_expires_at', session)
        spotify.models.request_access_token(payload)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(session['spotify_access_token'], 'dummy code')
        self.assertEqual(session['spotify_refresh_token'], 'refresh me')
        self.assertIn('spotify_expires_at', session)

    @mock.patch('requests.post', side_effect=mocked_spotify_api_post)
    def test_request_access_token_with_refresh_token_request(self, post):
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': 'refresh me'
        }

        with self.client.session_transaction() as sess:
            sess['spotify_access_token'] = 'some random test token'
            sess['spotify_refresh_token'] = 'some random refresh token'
        self.assertNotIn('spotify_expires_at', session)
        spotify.models.request_access_token(payload)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(session['spotify_access_token'], 'new dummy code')
        self.assertEqual(session['spotify_refresh_token'], 'refresh me again')
        self.assertIn('spotify_expires_at', session)

    @mock.patch('requests.post', side_effect=mocked_spotify_api_404)
    def test_request_access_token_with_spotify_error(self, post):
        payload = {
            'grant_type': 'authorization_code',
            'code': '',
            'redirect_uri': ''
        }

        with self.assertRaisesRegex(
                RuntimeError, 'Could not get authentication token'):
            spotify.models.request_access_token(payload)

    def test_get_username(self):
        self.assertEqual(spotify.models.get_username(), 'test_user')
        self.assertEqual(spotify.models.get_username(), 'test_user')

    def test_get_song_name(self):
        track = {
            'artists': [{'name': 'Artist 1'}, {'name': 'Artist 2'}],
            'name': 'Track name'
        }
        self.assertEqual(spotify.models.get_song_name(track),
                         'Artist 1 & Artist 2 - Track name')

    def test_get_playlists(self):
        playlists = spotify.models.get_playlists()
        self.assertEqual(len(playlists), 25)
        self.assertEqual(playlists[0]['name'], 'Starred')
        self.assertEqual(playlists[-1]['name'], 'Bozdugan')

    def test__get_playlist(self):
        playlist = spotify.models._get_playlist('test_user', '1')
        self.assertEqual(playlist['name'], 'Starred')
        self.assertIsNone(playlist['description'])
        self.assertIn('image', playlist)
        self.assertEqual(playlist['id'], 'test_user:1')
        self.assertEqual(len(playlist['tracks']), 200)

    def test__get_album(self):
        album = spotify.models._get_album('0AYlrY39QmCNwR4r1uzlv3')
        self.assertEqual(album['name'], 'Bozdugan')
        self.assertEqual(album['id'], 'album:0AYlrY39QmCNwR4r1uzlv3')
        self.assertIn('image', album)
        self.assertEqual(len(album['tracks']), 13)

    def test_get_playlist_with_keeping_song_names(self):
        playlist = spotify.models.get_playlist('test_user:1',
                                               keep_song_names=True)
        self.assertEqual(playlist['id'], 'test_user:1')
        self.assertIsNone(playlist['description'])
        self.assertEqual(playlist['name'], 'Starred')
        self.assertEqual(len(playlist['tracks']), 200)
        self.assertIn('Leona Lewis - Bleeding Love', playlist['tracks'])
        self.assertIn('The National - Anyone’s Ghost', playlist['tracks'])

        playlist = spotify.models.get_playlist('album:0AYlrY39QmCNwR4r1uzlv3',
                                               keep_song_names=True)
        self.assertEqual(playlist['name'], 'Bozdugan')
        self.assertEqual(playlist['id'], 'album:0AYlrY39QmCNwR4r1uzlv3')
        self.assertEqual(len(playlist['tracks']), 13)

    @mock.patch('gepify.providers.songs.get_song',
                side_effect=lambda song_name: {'name': song_name})
    def test_get_playlist_without_keeping_song_names(self, get_song):
        playlist = spotify.models.get_playlist('test_user:1')
        self.assertEqual(playlist['id'], 'test_user:1')
        self.assertIsNone(playlist['description'])
        self.assertEqual(playlist['name'], 'Starred')
        self.assertEqual(len(playlist['tracks']), 200)
        self.assertEqual(get_song.call_count, len(playlist['tracks']))
        self.assertEqual(playlist['tracks'][25]['name'],
                         'Leona Lewis - Bleeding Love')
        self.assertEqual(playlist['tracks'][42]['name'],
                         'The National - Anyone’s Ghost')

        get_song.reset_mock()
        playlist = spotify.models.get_playlist('album:0AYlrY39QmCNwR4r1uzlv3')
        self.assertEqual(playlist['name'], 'Bozdugan')
        self.assertEqual(playlist['id'], 'album:0AYlrY39QmCNwR4r1uzlv3')
        self.assertEqual(len(playlist['tracks']), 13)
        self.assertEqual(get_song.call_count, len(playlist['tracks']))


class SpotifyViewsTestCase(GepifyTestCase, ProfileMixin):
    @classmethod
    def tearDownClass(cls):
        if os.path.isfile('test song.mp3'):
            os.remove('test song.mp3')

        if os.path.isfile('playlist.zip'):
            os.remove('playlist.zip')

    def test_index_if_not_logged_in(self):
        response = self.client.get(url_for('spotify.index'))
        self.assertRedirects(response, url_for('spotify.login'))

    @mock.patch('spotipy.Spotify', side_effect=MockSpotipy)
    def test_index_if_logged_in(self, *args):
        self.login()
        response = self.client.get(url_for('spotify.index'))
        self.assert200(response)
        self.assertIn(b'Bozdugan', response.data)

    @mock.patch('requests.post', side_effect=mocked_spotify_api_post)
    def test_login(self, *args):
        response = self.client.get(url_for('spotify.login'))
        self.assertTrue(response.location.startswith(
                        'https://accounts.spotify.com/authorize/'))
        self.login()
        response = self.client.get(url_for('spotify.login'))
        self.assertIn(b'You need to be logged out to see this page',
                      response.data)

    @mock.patch('logging.Logger')
    @mock.patch('requests.post', side_effect=mocked_spotify_api_post)
    def test_login_callback(self, post, *args):
        response = self.client.get(
            url_for('spotify.callback', error='access_denied'))
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'There was an error while trying to authenticate you.'
                      b'Please, try again.', response.data)
        self.assertEqual(post.call_count, 0)

        with self.client.session_transaction() as sess:
            sess['spotify_auth_state'] = 'some state'

        response = self.client.get(
            url_for('spotify.callback', state='other state', code='123'))
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'There was an error while trying to authenticate you.'
                      b'Please, try again.', response.data)
        self.assertEqual(post.call_count, 0)

        response = self.client.get(
            url_for('spotify.callback', state='some state', code='123'))
        self.assertRedirects(response, url_for('spotify.index'))
        self.assertEqual(post.call_count, 1)

    @mock.patch('logging.Logger')
    @mock.patch('requests.post', side_effect=mocked_spotify_api_404)
    def test_login_callback_with_spotify_error(self, post, *args):
        with self.client.session_transaction() as sess:
            sess['spotify_auth_state'] = 'some state'
        response = self.client.get(
            url_for('spotify.callback', state='some state', code='123'))
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'There was an error while trying to authenticate you.'
                      b'Please, try again.', response.data)
        self.assertEqual(post.call_count, 1)

    @mock.patch('spotipy.Spotify', side_effect=MockSpotipy)
    def test_logout(self, Spotify):
        response = self.client.get(url_for('spotify.logout'))
        self.assertRedirects(response, url_for('views.index'))
        response = self.client.get(url_for('spotify.index'))
        self.assertRedirects(response, url_for('spotify.login'))
        self.login()
        response = self.client.get(url_for('spotify.index'))
        self.assert200(response)
        response = self.client.get(url_for('spotify.logout'))
        self.assertRedirects(response, url_for('views.index'))
        response = self.client.get(url_for('spotify.index'))
        self.assertRedirects(response, url_for('spotify.login'))

    @mock.patch('spotipy.Spotify', side_effect=MockSpotipy)
    @mock.patch('gepify.providers.songs.get_song',
                side_effect=lambda song_name: {'name': song_name, 'files': {}})
    def test_get_playlist(self, get_song, Spotify):
        self.login()
        response = self.client.get(
            url_for('spotify.playlist', id='test_user:1'))
        self.assert200(response)
        self.assertIn(b'Use Somebody', response.data)

    @mock.patch('logging.Logger')
    def test_download_song_in_unsupported_format(self, *args):
        self.login()
        response = self.client.get(
            url_for('spotify.download_song',
                    song_name='test song', format='wav'))
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Unsupported format', response.data)

    @mock.patch('gepify.providers.songs.has_song_format',
                side_effect=lambda song, format: False)
    @mock.patch('gepify.providers.songs.download_song.delay',
                side_effect=lambda song, format: None)
    def test_download_song_if_song_is_missing(self, *args):
        self.login()
        response = self.client.get(
            url_for('spotify.download_song',
                    song_name='test song', format='mp3'))
        self.assert200(response)
        self.assertIn(b'Your song has started downloading.', response.data)

    @mock.patch('gepify.providers.songs.has_song_format',
                side_effect=lambda song, format: True)
    @mock.patch('gepify.providers.songs.get_song',
                side_effect=lambda song: {
                    'name': song, 'files': {'mp3': song+'.mp3'}})
    def test_download_song_if_song_is_not_missing(self, *args):
        with open('test song.mp3', 'w+') as f:
            f.write('some data')

        self.login()
        response = self.client.get(
            url_for('spotify.download_song',
                    song_name='test song', format='mp3'))
        self.assert200(response)
        self.assertEqual(b'some data', response.data)
        self.assertTrue(response.content_type.startswith('audio'))
        response.close()

    @mock.patch('logging.Logger')
    def test_download_playlist_with_wrong_post_data(self, *args):
        self.login()
        response = self.client.post(url_for('spotify.download_playlist'))
        self.assertEqual(response.status_code, 400)
        response = self.client.post(url_for('spotify.download_playlist'),
                                    data={'playlist_id': 'test_user:some id'})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(url_for('spotify.download_playlist'),
                                    data={'format': 'mp3'})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            url_for('spotify.download_playlist'),
            data={'playlist_id': 'test_user:some id', 'format': 'wav'})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Unsupported format', response.data)

    @mock.patch('gepify.providers.playlists.has_playlist',
                side_effect=lambda *args: False)
    @mock.patch('gepify.providers.playlists.download_playlist.delay')
    @mock.patch('spotipy.Spotify', side_effect=MockSpotipy)
    def test_download_playlist_if_playlist_is_missing(self, *args):
        self.login()
        response = self.client.post(
            url_for('spotify.download_playlist'),
            data={'playlist_id': 'test_user:1', 'format': 'mp3'})
        self.assert200(response)
        self.assertIn(b'Your playlist is getting downloaded', response.data)

    @mock.patch('gepify.providers.playlists.has_playlist',
                side_effect=lambda *args: True)
    @mock.patch('gepify.providers.playlists.get_playlist',
                side_effect=lambda *args: {
                    'path': 'playlist.zip',
                    'checksum': '89c2226a90943679844cdc71693bc543'})
    @mock.patch('spotipy.Spotify', side_effect=MockSpotipy)
    def test_download_playlist_if_playlist_is_not_missing(self, *args):
        with open('playlist.zip', 'w+') as f:
            f.write('some data')

        self.login()
        response = self.client.post(
            url_for('spotify.download_playlist'),
            data={'playlist_id': 'test_user:1', 'format': 'mp3'})
        self.assert200(response)
        self.assertEqual(b'some data', response.data)
        self.assertEqual(response.content_type, 'application/zip')
        response.close()

    @mock.patch('gepify.providers.playlists.has_playlist',
                side_effect=lambda *args: True)
    @mock.patch('gepify.providers.playlists.get_playlist',
                side_effect=lambda *args: {
                    'path': 'playlist.zip',
                    'checksum': 'old checkum'})
    @mock.patch('gepify.providers.playlists.download_playlist.delay')
    @mock.patch('spotipy.Spotify', side_effect=MockSpotipy)
    def test_download_playlist_if_playlist_has_changed(self, *args):
        self.login()
        response = self.client.post(
            url_for('spotify.download_playlist'),
            data={'playlist_id': 'test_user:1', 'format': 'mp3'})
        self.assert200(response)
        self.assertIn(b'Your playlist is getting downloaded', response.data)
