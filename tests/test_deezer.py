from . import GepifyTestCase
from gepify.services import deezer
from urllib import parse
from unittest import mock
from flask import url_for, session
import json
import os


class MockResponse:
    def __init__(self, data, status_code):
        self.text = json.dumps(data)
        self.status_code = status_code


def mocked_deezer_api_get(url):
    if url.startswith('https://connect.deezer.com/oauth/access_token.php'):
        params = parse.parse_qs(parse.urlparse(url).query)
        assert params['output'][0] == 'json'

        if params['code'][0] == 'dummy code':
            return MockResponse({
                'access_token': 'dummy token',
                'expires': 60
            }, 200)

        return MockResponse({}, 500)
    elif url.startswith('http://api.deezer.com/user/me'):
        params = parse.parse_qs(parse.urlparse(url).query)
        if params['access_token'][0] == 'dummy token':
            return MockResponse({'id': 'dummy_user'}, 200)
        return MockResponse({}, 403)
    elif url.startswith('http://api.deezer.com/user/dummy_user/playlists'):
        return MockResponse({
            'data': [
                {
                  'id': '1677006641',
                  'title': 'New Urban Pop HITS (Justin Timberlake, Sia...)',
                  'nb_tracks': 48,
                  'type': 'playlist'
                },
                {
                  'id': '164716031',
                  'title': 'Duets',
                  'nb_tracks': 47,
                  'type': 'playlist'
                }
            ]
        }, 200)
    elif url.startswith('http://api.deezer.com/playlist/1'):
        return MockResponse({
            'title': 'Playlist 1',
            'description': '',
            'tracks': {
                'data': [
                    {
                        'title': 'Song 1',
                        'artist': {
                            'name': 'Artist 1'
                        }
                    }
                ]
            }
        }, 200)

    return MockResponse({}, 404)


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


class DeezerModelsTestCase(GepifyTestCase, ProfileMixin):
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

    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    def test_get_user_id(self, get):
        with self.assertRaisesRegex(RuntimeError, 'User not authenticated'):
            deezer.models.get_user_id()

        with self.client:
            self.login()
            self.assertEqual(deezer.models.get_user_id(), 'dummy_user')
            self.assertEqual(get.call_count, 1)
            get.reset_mock()
            self.assertEqual(deezer.models.get_user_id(), 'dummy_user')
            self.assertFalse(get.called)

            with self.assertRaisesRegex(RuntimeError, 'Deezer API error'):
                session['deezer_user_id'] = None
                session['deezer_access_token'] = 'false token'
                deezer.models.get_user_id()

    def test_get_song_name(self):
        track = {
            'artist': {'name': 'Artist'},
            'title': 'Track name'
        }
        self.assertEqual(deezer.models.get_song_name(track),
                         'Artist - Track name')

    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    def test_get_playlists(self, *args):
        with self.client:
            self.login()
            playlists = deezer.models.get_playlists()
            self.assertEqual(len(playlists), 2)
            self.assertEqual(
                playlists[0]['name'],
                'New Urban Pop HITS (Justin Timberlake, Sia...)'
            )
            self.assertEqual(playlists[1]['name'], 'Duets')

            session['deezer_user_id'] = 'wrong user'
            with self.assertRaisesRegex(RuntimeError, 'Deezer API error'):
                deezer.models.get_playlists()

    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    def test_get_playlist_with_keeping_song_names(self, *args):
        with self.client:
            self.login()
            playlist = deezer.models.get_playlist('1', keep_song_names=True)
            self.assertEqual(playlist['id'], '1')
            self.assertEqual(playlist['description'], '')
            self.assertEqual(playlist['name'], 'Playlist 1')
            self.assertEqual(len(playlist['tracks']), 1)
            self.assertIn('Artist 1 - Song 1', playlist['tracks'])

            with self.assertRaisesRegex(RuntimeError, 'Deezer API error'):
                deezer.models.get_playlist('missing id', keep_song_names=True)

    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    @mock.patch('gepify.providers.songs.get_song',
                side_effect=lambda song_name: {'name': song_name})
    def test_get_playlist_without_keeping_song_names(self, get_song, *args):
        with self.client:
            self.login()
            playlist = deezer.models.get_playlist('1')
            self.assertEqual(playlist['id'], '1')
            self.assertEqual(playlist['description'], '')
            self.assertEqual(playlist['name'], 'Playlist 1')
            self.assertEqual(len(playlist['tracks']), 1)
            self.assertEqual(get_song.call_count, len(playlist['tracks']))
            self.assertEqual(playlist['tracks'][0]['name'], 'Artist 1 - Song 1')

            with self.assertRaisesRegex(RuntimeError, 'Deezer API error'):
                deezer.models.get_playlist('missing id')


class DeezerViewsTestCase(GepifyTestCase, ProfileMixin):
    @classmethod
    def tearDownClass(cls):
        if os.path.isfile('test song.mp3'):
            os.remove('test song.mp3')

        if os.path.isfile('playlist.zip'):
            os.remove('playlist.zip')

    def test_index_if_not_logged_in(self):
        response = self.client.get(url_for('deezer.index'))
        self.assertRedirects(response, url_for('deezer.login'))

    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    def test_index_if_logged_in(self, *args):
        self.login()
        response = self.client.get(url_for('deezer.index'))
        self.assert200(response)
        self.assertIn(
            b'New Urban Pop HITS (Justin Timberlake, Sia...)',
            response.data
        )
        self.assertIn(b'Duets', response.data)

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

    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    def test_logout(self, *args):
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

    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    @mock.patch('gepify.providers.songs.get_song',
                side_effect=lambda song_name: {'name': song_name, 'files': {}})
    def test_get_playlist(self, *args):
        self.app.debug = False
        self.login()
        response = self.client.get(url_for('deezer.playlist', id='1'))
        self.assert200(response)
        self.assertIn(b'Playlist 1', response.data)

        response = self.client.get(url_for('deezer.playlist', id='missing id'))
        self.assert500(response)

    @mock.patch('logging.Logger')
    def test_download_song_in_unsupported_format(self, *args):
        self.login()
        response = self.client.get(
            url_for('deezer.download_song',
                    song_name='test song', format='wav'))
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Unsupported format', response.data)

    @mock.patch('gepify.providers.songs.has_song_format',
                side_effect=lambda song, format: False)
    @mock.patch('gepify.providers.songs.download_song.delay')
    def test_download_song_if_song_is_missing(self, download_song, *args):
        self.login()
        response = self.client.get(
            url_for('deezer.download_song',
                    song_name='test song', format='mp3'))
        self.assert200(response)
        self.assertIn(b'Your song has started downloading.', response.data)
        self.assertEqual(download_song.call_count, 1)

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
            url_for('deezer.download_song',
                    song_name='test song', format='mp3'))
        self.assert200(response)
        self.assertEqual(b'some data', response.data)
        self.assertTrue(response.content_type.startswith('audio'))
        response.close()

    @mock.patch('logging.Logger')
    @mock.patch('gepify.providers.songs.has_song_format',
                side_effect=lambda song, format: True)
    @mock.patch('gepify.providers.songs.get_song',
                side_effect=lambda song: {
                    'name': song, 'files': {'mp3': song+'.mp3'}})
    def test_download_song_if_mp3_file_is_missing(self, *args):
        self.login()
        response = self.client.get(
            url_for('deezer.download_song',
                    song_name='no such song', format='mp3'))
        self.assert500(response)
        response.close()

    @mock.patch('logging.Logger')
    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    def test_download_playlist_with_wrong_post_data(self, *args):
        self.login()
        response = self.client.post(url_for('deezer.download_playlist'))
        self.assertEqual(response.status_code, 400)
        response = self.client.post(url_for('deezer.download_playlist'),
                                    data={'playlist_id': 'some id'})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(url_for('deezer.download_playlist'),
                                    data={'format': 'mp3'})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            url_for('deezer.download_playlist'),
            data={'playlist_id': 'some id', 'format': 'wav'})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Unsupported format', response.data)

    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    @mock.patch('gepify.providers.playlists.has_playlist',
                side_effect=lambda *args: False)
    @mock.patch('gepify.providers.playlists.download_playlist.delay')
    def test_download_playlist_if_playlist_is_missing(self, *args):
        self.login()
        response = self.client.post(
            url_for('deezer.download_playlist'),
            data={'playlist_id': '1', 'format': 'mp3'})
        self.assert200(response)
        self.assertIn(b'Your playlist is getting downloaded', response.data)

    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    @mock.patch('gepify.providers.playlists.has_playlist',
                side_effect=lambda *args: True)
    @mock.patch('gepify.providers.playlists.get_playlist',
                side_effect=lambda *args: {
                    'path': 'playlist.zip',
                    'checksum': '7cf74c9cd14481ba46812f80617ad95d'})
    def test_download_playlist_if_playlist_is_not_missing(self, *args):
        with open('playlist.zip', 'w+') as f:
            f.write('some data')

        self.login()
        response = self.client.post(
            url_for('deezer.download_playlist'),
            data={'playlist_id': '1', 'format': 'mp3'})
        self.assert200(response)
        self.assertEqual(b'some data', response.data)
        self.assertEqual(response.content_type, 'application/zip')
        response.close()

    @mock.patch('logging.Logger')
    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    @mock.patch('gepify.providers.playlists.has_playlist',
                side_effect=lambda *args: True)
    @mock.patch('gepify.providers.playlists.get_playlist',
                side_effect=lambda *args: {
                    'path': 'missing.zip',
                    'checksum': '7cf74c9cd14481ba46812f80617ad95d'})
    def test_download_playlist_if_zip_file_is_missing(self, *args):
        self.login()
        response = self.client.post(
            url_for('deezer.download_playlist'),
            data={'playlist_id': '1', 'format': 'mp3'})
        self.assert500(response)
        response.close()

    @mock.patch('requests.get', side_effect=mocked_deezer_api_get)
    @mock.patch('gepify.providers.playlists.has_playlist',
                side_effect=lambda *args: True)
    @mock.patch('gepify.providers.playlists.get_playlist',
                side_effect=lambda *args: {
                    'path': 'playlist.zip',
                    'checksum': 'old checkum'})
    @mock.patch('gepify.providers.playlists.download_playlist.delay')
    def test_download_playlist_if_playlist_has_changed(self, *args):
        self.login()
        response = self.client.post(
            url_for('deezer.download_playlist'),
            data={'playlist_id': '1', 'format': 'mp3'})
        self.assert200(response)
        self.assertIn(b'Your playlist is getting downloaded', response.data)
