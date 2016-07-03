from unittest import mock, TestCase
import gepify
from gepify.providers import songs, playlists, youtube, soundcloud
from werkzeug.contrib.cache import SimpleCache
import json
import time


class SongsTestCase(TestCase):
    def setUp(self):
        songs.cache = SimpleCache()

    def test_get_song_if_song_is_not_in_cache(self):
        song = songs.get_song('some song')
        self.assertEqual(song['name'], 'some song')
        self.assertEqual(song['files'], {})

    def test_get_song_if_song_is_in_cache(self):
        song = songs.get_song('some song')
        self.assertEqual(song['name'], 'some song')
        self.assertEqual(song['files'], {})

    def test_add_song_file_if_format_is_unsupported(self):
        with self.assertRaises(ValueError):
            songs.add_song_file('some song', 'some song.mp3', 'wav')

    def test_add_song_file(self):
        song = songs.get_song('some song')
        self.assertNotIn('mp3', song['files'])
        songs.add_song_file('some song', 'some song.mp3', 'mp3')
        song = songs.get_song('some song')
        self.assertEqual(song['files']['mp3'], 'some song.mp3')

    def test_has_song_format(self):
        self.assertFalse(songs.has_song_format('some song', 'mp3'))
        songs.add_song_file('some song', 'some song.mp3', 'mp3')
        self.assertTrue(songs.has_song_format('some song', 'mp3'))

    def test_has_song_format_if_song_is_being_downloaded(self):
        self.assertFalse(songs.has_song_format('some song', 'mp3'))
        song = songs.get_song('some song')
        song['files']['mp3'] = 'downloading'
        songs.cache.set('some song', song)
        self.assertFalse(songs.has_song_format('some song', 'mp3'))


class SongsTasksTestCase(TestCase):
    def setUp(self):
        songs.cache = SimpleCache()

    def test_download_song_in_unsupported_format(self):
        with self.assertRaisesRegex(ValueError, 'Format not supported: wav'):
            songs.download_song('song', format='wav')

    @mock.patch('logging.Logger.info')
    def test_download_song_if_song_is_already_downloaded(self, log_info):
        songs.add_song_file('song', 'song.mp3', 'mp3')
        songs.download_song('song', format='mp3')
        log_info.assert_called_with(
            'Attempt to download already downloaded song.'
            'Cache: song.mp3'
        )

    @mock.patch('logging.Logger.info')
    def test_download_song_if_song_is_being_downloaded(self, log_info):
        song = songs.get_song('song')
        song['files']['mp3'] = 'downloading'
        songs.cache.set('song', song)
        songs.download_song('song', format='mp3')
        log_info.assert_called_with(
            'Attempt to download a song in the process of downloading')

    def test_download_song_with_unsupported_provider(self):
        with self.assertRaisesRegex(ValueError, 'Provider not found: zamunda'):
            songs.download_song('song', provider='zamunda')
        song = songs.get_song('song')
        self.assertNotIn('mp3', song['files'])

    @mock.patch('gepify.providers.youtube.get_song_id',
                side_effect=lambda name: 'dQw4w9WgXcQ')
    @mock.patch('gepify.providers.youtube.download_song')
    def test_download_song_with_youtube(self, download_song, *args):
        songs.download_song('song')
        download_song.assert_called_with('dQw4w9WgXcQ', 'mp3')
        song = songs.get_song('song')
        self.assertEqual(song['files']['mp3'], 'songs/dQw4w9WgXcQ.mp3')

    @mock.patch('gepify.providers.soundcloud.get_song_id',
                side_effect=lambda name: (1234, 'song id'))
    @mock.patch('gepify.providers.soundcloud.download_song')
    def test_download_song_with_soundcloud(self, download_song, *args):
        songs.download_song('song', provider='soundcloud')
        download_song.assert_called_with('song id', 'mp3')
        song = songs.get_song('song')
        self.assertEqual(song['files']['mp3'], 'songs/1234.mp3')


class PlaylistsTestCase(TestCase):
    def setUp(self):
        playlists.cache = SimpleCache()

    @mock.patch('gepify.providers.playlists.cache.get')
    def test_get_playlist(self, cache_get):
        playlists.get_playlist('spotify', 'some playlist', 'mp3')
        cache_get.assert_called_with('spotify_some playlist_mp3')

    def test_get_playlist_if_playlist_is_being_downloaded(self):
        playlists.cache.set('spotify_some playlist_mp3', 'downloading')
        playlist = playlists.get_playlist('spotify', 'some playlist', 'mp3')
        self.assertIsNone(playlist)

    def test_has_playlist(self):
        self.assertFalse(
            playlists.has_playlist('spotify', 'some playlist', 'mp3'))
        playlists.cache.set('spotify_some playlist_mp3', {})
        self.assertTrue(
            playlists.has_playlist('spotify', 'some playlist', 'mp3'))
        playlists.cache.set('spotify_some playlist_mp3', 'downloading')
        self.assertFalse(
            playlists.has_playlist('spotify', 'some playlist', 'mp3'))


def mocked_list_dir(dir):
    return ['1.zip', '2.zip']


def mocked_getmtime(file):
    if file == 'playlists/1.zip':
        return time.time() - 60*60
    if file == 'playlists/2.zip':
        return time.time() - 42


class PlaylistsTasksTestCase(TestCase):
    def setUp(self):
        playlists.cache = mock.MagicMock()

    def tearDown(self):
        playlists.cache.reset_mock()

    @mock.patch('os.listdir', side_effect=mocked_list_dir)
    @mock.patch('os.path.getmtime', side_effect=mocked_getmtime)
    @mock.patch('logging.Logger')
    @mock.patch('os.remove')
    def test_clean_playlists(self, os_remove, *args):
        playlists.clean_playlists()
        self.assertEqual(os_remove.call_count, 1)
        os_remove.assert_called_with('playlists/1.zip')


class mocked_Resource():
    def __init__(self, *args, **kwargs):
        self.result = []

    def search(self):
        return self

    def list(self, *args, **kwargs):
        if kwargs['q'] == 'existing song':
            with open('tests/youtube_dump.json') as f:
                self.result = json.loads(f.read())
        return self

    def execute(self):
        return self

    def get(self, *args, **kwargs):
        return self.result


class YoutubeTestCase(TestCase):
    @mock.patch('googleapiclient.discovery.Resource',
                side_effect=mocked_Resource)
    def test_get_song_id(self, Resource):
        song_id = youtube.get_song_id('existing song')
        self.assertEqual(song_id, 'OV5_LQArLa0')

    @mock.patch('googleapiclient.discovery.Resource',
                side_effect=mocked_Resource)
    def test_get_song_id_if_no_song_is_found(self, Resource):
        with self.assertRaises(RuntimeError):
            youtube.get_song_id('missing song')

    def test_download_song_with_unsupported_format(self):
        with self.assertRaises(ValueError):
            youtube.download_song('song id', 'wav')

    @mock.patch('youtube_dl.YoutubeDL.download')
    def test_download_song(self, download):
        youtube.download_song('song id', 'mp3')
        self.assertEqual(download.call_count, 1)
        download.assert_called_with(['http://www.youtube.com/watch?v=song id'])


class mocked_Response():
    def __init__(self, obj):
        self.obj = obj


class mocked_Client():
    def __init__(self, *args, **kwargs):
        pass

    def get(self, resource, q):
        if q == 'existing song':
            return [mocked_Response({
                'id': '1234',
                'permalink': 'song_permalink',
                'user': {
                    'permalink': 'user_permalink'
                }
            })]

        return []


class SoundcloudTestCase(TestCase):
    @mock.patch('soundcloud.Client', side_effect=mocked_Client)
    def test_get_song_id(self, Client):
        song_id, download_id = soundcloud.get_song_id('existing song')
        self.assertEqual(song_id, '1234')
        self.assertEqual(download_id, 'user_permalink/song_permalink')

    @mock.patch('soundcloud.Client', side_effect=mocked_Client)
    def test_get_song_id_if_no_song_is_found(self, Client):
        with self.assertRaises(RuntimeError):
            soundcloud.get_song_id('missing song')

    def test_download_song_with_unsupported_format(self):
        with self.assertRaises(ValueError):
            soundcloud.download_song('song id', 'wav')

    @mock.patch('youtube_dl.YoutubeDL.download')
    def test_download_song(self, download):
        soundcloud.download_song('song id', 'mp3')
        self.assertEqual(download.call_count, 1)
        download.assert_called_with(['http://soundcloud.com/song id'])
