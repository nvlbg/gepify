import gepify
import requests
from . import GepifyTestCase
from flask import url_for, session, g
import spotipy
from werkzeug.contrib.cache import NullCache
from urllib import parse
from pprint import pprint
from unittest import mock
from gepify.services import spotify
import json


class MockResponse:
    def __init__(self, data, status_code):
        self.text = json.dumps(data)
        self.status_code = status_code


def mocked_spotify_api_post(*args, **kwargs):
    url = args[0]
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


class MockSpotipy:
    def __init__(self, auth=None):
        self.auth = auth

    def me(self):
        return {
            'id': 'test_user'
        }

    def user_playlists(self, username):
        return {
            'items': [
                {'id': '1', 'images': [], 'name': 'Playlist 1', 'tracks': {'total': 10}},
                {'id': '2', 'images': [], 'name': 'Playlist 2', 'tracks': {'total': 20}},
            ]
        }

    def current_user_saved_albums(self):
        return {
            'items': [
                {'album': {'name': 'Album 1'}}
            ]
        }


class ProfileMixin():
    def login(self):
        login_response = self.client.get(url_for('spotify.login'))
        spotify_redirect = login_response.location
        self.assertTrue(spotify_redirect.startswith('https://accounts.spotify.com/authorize'))

        params = parse.parse_qs(parse.urlparse(spotify_redirect).query)

        response = self.client.get(url_for(
            'spotify.callback', code='dummy code', state=params['state'][0]
        ))
        self.assertRedirects(response, url_for('spotify.index'))
        return response

    def logout(self):
        logout_response = self.client.get(url_for('spotify.logout'))
        self.assertRedirects(logout_response, url_for('views.index'))
        return logout_response


@mock.patch('requests.post', side_effect=mocked_spotify_api_post)
class SpotifyDecoratorsTestCase(GepifyTestCase, ProfileMixin):
    def test_login_required_decorator(self, post):
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
        self.assertIn(b'You need to be logged out to see this page', response.data)

        self.logout()

        response = self.client.get('/test')
        self.assert200(response)
        self.assertIn(b'You should be logged out to read this', response.data)


class SpotifyModelsTestCase(GepifyTestCase):
    def setUp(self):
        spotify.models.cache = NullCache()
        g.spotipy = mock.Mock(spec=spotipy.Spotify)
        g.spotipy.me = mock.MagicMock(name='me')
        g.spotipy.me.return_value = {'id': 'test_user'}
        g.spotipy.user_playlists = mock.MagicMock(name='user_playlists')
        g.spotipy.user_playlists.return_value = {
            'items': [
                {'id': '1', 'images': [], 'name': 'Playlist 1', 'tracks': {'total': 10}},
                {'id': '2', 'images': [], 'name': 'Playlist 2', 'tracks': {'total': 20}},
            ]
        }
        g.spotipy.user_playlist = mock.MagicMock(name='user_playlist')
        g.spotipy.user_playlist.return_value = {
            'name': 'Playlist 1',
            'description': 'desc',
            'tracks': {
                'items': [
                    {'track':
                        {'name': 'Song 1', 'artists': [{'name': 'Artist 1'}]}},
                    {'track':
                        {'name': 'Song 2', 'artists': [{'name': 'Artist 2'}]}}
                ]
            }
        }

    def tearDown(self):
        g.spotipy = None

    @mock.patch('requests.post', side_effect=mocked_spotify_api_post)
    def test_request_access_token_with_authorization_code_request(self, post):
        payload = {
            'grant_type': 'authorization_code',
            'code': '',
            'redirect_uri': ''
        }

        session['spotify_access_token'] = 'some random test token'
        session['spotify_refresh_token'] = 'some random refresh token'
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

        session['spotify_access_token'] = 'some random test token'
        session['spotify_refresh_token'] = 'some random refresh token'
        self.assertNotIn('spotify_expires_at', session)
        spotify.models.request_access_token(payload)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(session['spotify_access_token'], 'new dummy code')
        self.assertEqual(session['spotify_refresh_token'], 'refresh me again')
        self.assertIn('spotify_expires_at', session)

    def test_get_username(self):
        self.assertEqual(spotify.models.get_username(), 'test_user')
        self.assertEqual(g.spotipy.me.call_count, 1)
        self.assertEqual(spotify.models.get_username(), 'test_user')
        self.assertEqual(g.spotipy.me.call_count, 1)

    def test_get_song_name(self):
        track = {
            'artists': [{'name': 'Artist 1'}, {'name': 'Artist 2'}],
            'name': 'Track name'
        }
        self.assertEqual(spotify.models.get_song_name(track),
                         'Artist 1 & Artist 2 - Track name')

    def test_get_playlists(self):
        playlists = spotify.models.get_playlists()
        self.assertEqual(len(playlists), 2)
        self.assertEqual(playlists[0]['name'], 'Playlist 1')
        self.assertEqual(playlists[1]['name'], 'Playlist 2')

    def test_get_playlist_with_keeping_song_names(self):
        playlist = spotify.models.get_playlist('1', keep_song_names=True)
        self.assertEqual(playlist['id'], '1')
        self.assertEqual(playlist['description'], 'desc')
        self.assertEqual(playlist['name'], 'Playlist 1')
        self.assertIn('tracks', playlist.keys())
        self.assertEqual(len(playlist['tracks']), 2)
        self.assertIn('Artist 1 - Song 1', playlist['tracks'])
        self.assertIn('Artist 2 - Song 2', playlist['tracks'])

    @mock.patch('gepify.providers.songs.get_song',
                side_effect=lambda song_name: {'name': song_name})
    def test_get_playlist_without_keeping_song_names(self, get_song):
        playlist = spotify.models.get_playlist('1')
        self.assertEqual(playlist['id'], '1')
        self.assertEqual(playlist['description'], 'desc')
        self.assertEqual(playlist['name'], 'Playlist 1')
        self.assertIn('tracks', playlist.keys())
        self.assertEqual(len(playlist['tracks']), 2)
        self.assertEqual(get_song.call_count, 2)
        self.assertEqual(playlist['tracks'][0]['name'], 'Artist 1 - Song 1')
        self.assertEqual(playlist['tracks'][1]['name'], 'Artist 2 - Song 2')

    def test_get_playlist_name(self):
        self.assertEqual(spotify.models.get_playlist_name('1'), 'Playlist 1')


@mock.patch('requests.post', side_effect=mocked_spotify_api_post)
class SpotifyViewsTestCase(GepifyTestCase, ProfileMixin):
    def test_index_if_not_logged_in(self, post):
        response = self.client.get(url_for('spotify.index'))
        self.assertRedirects(response, url_for('spotify.login'))

    @mock.patch('spotipy.Spotify', side_effect=MockSpotipy)
    def test_index_if_logged_in(self, post, Spotify):
        self.login()
        response = self.client.get(url_for('spotify.index'))
        self.assert200(response)
        self.assertIn(b'Playlist 1', response.data)
        self.assertIn(b'Playlist 2', response.data)
