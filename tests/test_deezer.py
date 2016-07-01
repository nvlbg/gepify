from . import GepifyTestCase
from gepify.services import deezer
from urllib import parse
from unittest import mock
from flask import url_for, session
import json


class MockResponse:
    def __init__(self, data, status_code):
        self.text = json.dumps(data)
        self.status_code = status_code


def mocked_deezer_api_get(*args, **kwargs):
    assert args[0].startswith(
        'https://connect.deezer.com/oauth/access_token.php')
    params = parse.parse_qs(parse.urlparse(args[0]).query)
    assert params['output'][0] == 'json'

    if params['code'][0] == 'dummy code':
        return MockResponse({
            'access_token': 'dummy token',
            'expires': 60
        }, 200)

    return MockResponse({}, 500)


class ProfileMixin():
    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    def login(self, *args):
        login_response = self.client.get(url_for('deezer.login'))
        deezer_redirect = login_response.location
        self.assertTrue(deezer_redirect.startswith(
                            'https://connect.deezer.com/oauth/auth.php'))

        params = parse.parse_qs(parse.urlparse(deezer_redirect).query)

        response = self.client.get(url_for(
            'deezer.callback', code='dummy code', state=params['state'][0]
        ))
        self.assertRedirects(response, url_for('deezer.index'))
        return response

    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    def logout(self, *args):
        logout_response = self.client.get(url_for('deezer.logout'))
        self.assertRedirects(logout_response, url_for('views.index'))
        return logout_response


class DeezerDecoratorsTestCase(GepifyTestCase, ProfileMixin):
    def test_login_required_decorator(self, *args):
        @self.app.route('/test')
        @deezer.view_decorators.login_required
        def test():
            return 'You should be logged in to read this'

        response = self.client.get('/test')
        self.assertRedirects(response, url_for('deezer.login'))

        self.login()
        response = self.client.get('/test')
        self.assert200(response)
        self.assertIn(b'You should be logged in to read this', response.data)

        self.logout()

        response = self.client.get('/test')
        self.assertRedirects(response, url_for('deezer.login'))

        self.login()
        with self.client.session_transaction() as sess:
            sess['deezer_expires_at'] = -1

        response = self.client.get('/test')
        self.assertRedirects(response, url_for('deezer.login'))

    def test_logout_required_decorator(self):
        @self.app.route('/test')
        @deezer.view_decorators.logout_required
        def test():
            return 'You should be logged out to read this'

        response = self.client.get('/test')
        self.assert200(response)
        self.assertIn(b'You should be logged out to read this', response.data)

        self.login()

        response = self.client.get('/test')
        self.assert403(response)
        self.assertIn(
            b'You need to be logged out to see this page', response.data)

        self.logout()

        response = self.client.get('/test')
        self.assert200(response)
        self.assertIn(b'You should be logged out to read this', response.data)


class DeezerModelsTestCase(GepifyTestCase):
    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    def test_request_access_token(self, get):
        self.assertNotIn('deezer_access_token', session)
        self.assertNotIn('deezer_expires_at', session)
        deezer.models.request_access_token('dummy code')
        self.assertEqual(get.call_count, 1)
        self.assertEqual(session['deezer_access_token'], 'dummy token')
        self.assertIn('deezer_expires_at', session)

    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    def test_request_access_token_with_deezer_error(self, get):
        self.assertNotIn('deezer_access_token', session)
        self.assertNotIn('deezer_expires_at', session)
        with self.assertRaises(RuntimeError):
            deezer.models.request_access_token('wrong code')
        self.assertEqual(get.call_count, 1)


class DeezerViewsTestCase(GepifyTestCase, ProfileMixin):
    def test_index_if_not_logged_in(self):
        response = self.client.get(url_for('deezer.index'))
        self.assertRedirects(response, url_for('deezer.login'))

    def test_login(self):
        response = self.client.get(url_for('deezer.login'))
        self.assertTrue(response.location.startswith(
                        'https://connect.deezer.com/oauth/auth.php'))
        self.login()
        response = self.client.get(url_for('deezer.login'))
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'You need to be logged out to see this page',
                      response.data)

    @mock.patch('logging.Logger')
    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    def test_login_callback(self, get, *args):
        response = self.client.get(
            url_for('deezer.callback', error_reason='access_denied'))
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'There was an error while trying to authenticate you.'
                      b'Please, try again.', response.data)
        self.assertEqual(get.call_count, 0)

        with self.client.session_transaction() as sess:
            sess['deezer_auth_state'] = 'some state'

        response = self.client.get(
            url_for('deezer.callback', state='other state', code='dummy code'))
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'There was an error while trying to authenticate you.'
                      b'Please, try again.', response.data)
        self.assertEqual(get.call_count, 0)

        response = self.client.get(
            url_for('deezer.callback', state='some state', code='dummy code'))
        self.assertRedirects(response, url_for('deezer.index'))
        self.assertEqual(get.call_count, 1)

    @mock.patch('logging.Logger')
    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    def test_login_callback_with_deezer_error(self, get, *args):
        with self.client.session_transaction() as sess:
            sess['deezer_auth_state'] = 'some state'

        response = self.client.get(
            url_for('deezer.callback', state='some state', code='wrong code'))
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'There was an error while trying to authenticate you.'
                      b'Please, try again.', response.data)
        self.assertEqual(get.call_count, 1)

    def test_logout(self):
        response = self.client.get(url_for('deezer.logout'))
        self.assertRedirects(response, url_for('views.index'))
        response = self.client.get(url_for('deezer.index'))
        self.assertRedirects(response, url_for('deezer.login'))
        self.login()
        response = self.client.get(url_for('deezer.index'))
        self.assert200(response)
        response = self.client.get(url_for('deezer.logout'))
        self.assertRedirects(response, url_for('views.index'))
        response = self.client.get(url_for('deezer.index'))
        self.assertRedirects(response, url_for('deezer.login'))
