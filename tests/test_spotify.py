import gepify
import requests
from flask.ext.testing import TestCase
from flask import url_for, session
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
class SpotifyDecoratorsTestCase(TestCase, ProfileMixin):
    def create_app(self):
        self.app = gepify.create_app()
        self.app.config['TESTING'] = True
        self.app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
        return self.app

    def setUp(self):
        self.client = self.app.test_client()

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
        self.assertIn(b'You need to be logged out to see this page', response.data)

        self.logout()

        response = self.client.get('/test')
        self.assert200(response)
        self.assertIn(b'You should be logged out to read this', response.data)


@mock.patch('requests.post', side_effect=mocked_spotify_api_post)
class SpotifyTestCase(TestCase, ProfileMixin):
    def create_app(self):
        self.app = gepify.create_app()
        self.app.config['TESTING'] = False
        self.app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
        return self.app

    def setUp(self):
        self.client = self.app.test_client()

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
