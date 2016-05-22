import gepify
import requests
from flask.ext.testing import TestCase
from flask import url_for, session
from urllib import parse
from pprint import pprint
from unittest import mock
from gepify.services import spotify


class MockResponse:
    def __init__(self, data, status_code):
        self.text = str(data)
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
        params = parse.parse_qs(parse.urlparse(spotify_redirect).query)

        return self.client.get(url_for('spotify.callback'), data={
            'code': 'dummy code',
            'state': params['state'][0]
        })

    def logout(self):
        return self.client.get(url_for('spotify.logout'))


class SpotifyDecoratorsTestCase(TestCase, ProfileMixin):
    def create_app(self):
        gepify.app.config['TESTING'] = True
        return gepify.app

    def setUp(self):
        self.client = gepify.app.test_client()

    def test_login_required_decorator(self):
        @self.app.route('/test')
        @spotify.view_decorators.login_required
        def test():
            return 'You should be logged in to read this'

        response = self.client.get('/test')
        self.assertRedirects(response, url_for('spotify.login'))

        self.login()

        response = self.client.get('/test')
        self.assert200(response)
        self.assertIn(b'You should be logged in to read this', response.data)

        self.logout()

        response = self.client.get('/test')
        self.assertRedirects(response, url_for('spotify.login'))


class SpotifyTestCase(TestCase, ProfileMixin):
    def create_app(self):
        gepify.app.config['TESTING'] = True
        return gepify.app

    def setUp(self):
        self.client = gepify.app.test_client()

    def test_index_if_not_logged_in(self):
        response = self.client.get(url_for('spotify.index'))
        self.assertRedirects(response, url_for('spotify.login'))

    # @mock.patch('requests.post',
    #             side_effect=mocked_spotify_api)
    # def test_login(self, post):
    #     response = self.client.get(url_for('spotify.login'))
    #     login = self.login()
    #     self.assertIn(b'Error: did not get token', login.data)
