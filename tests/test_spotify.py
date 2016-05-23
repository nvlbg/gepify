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


def mocked_spotify_api(*args, **kwargs):
    if args[0] == 'https://accounts.spotify.com/api/token':
        return MockResponse({
            'access_token': 'dummy code',
            'refresh_token': 'refresh me',
            'expires_in': 60
        }, 200)


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
        self.assertRedirects(logout_response, url_for('index'))
        return logout_response


@mock.patch('requests.post', side_effect=mocked_spotify_api)
class SpotifyDecoratorsTestCase(TestCase, ProfileMixin):
    def create_app(self):
        gepify.app.config['TESTING'] = True
        return gepify.app

    def setUp(self):
        self.client = gepify.app.test_client()

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

        self.logout()

        response = self.client.get('/test')
        self.assertRedirects(response, url_for('spotify.login'))


@mock.patch('requests.post', side_effect=mocked_spotify_api)
class SpotifyTestCase(TestCase, ProfileMixin):
    def create_app(self):
        gepify.app.config['TESTING'] = True
        gepify.app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
        return gepify.app

    def setUp(self):
        self.client = gepify.app.test_client()

    def test_index_if_not_logged_in(self, post):
        response = self.client.get(url_for('spotify.index'))
        self.assertRedirects(response, url_for('spotify.login'))

    # def test_index_if_logged_in(self, post):
    #     self.login()
    #     response = self.client.get(url_for('spotify.index'))
    #     print(response.data)
    #     pass
