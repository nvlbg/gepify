from unittest import mock, TestCase
import gepify
from gepify.providers import songs, playlists, youtube
from werkzeug.contrib.cache import SimpleCache
import json


class SongsTestCase(TestCase):
    def setUp(cls):
        songs.cache = SimpleCache()

    @mock.patch('gepify.providers.songs.cache.get',
                side_effect=lambda song: None)
    @mock.patch('gepify.providers.songs.cache.set')
    def test_get_song_if_song_is_not_in_cache(self, cache_set, cache_get):
        song = songs.get_song('some song')
        self.assertEqual(song['name'], 'some song')
        self.assertEqual(song['files'], {})
        self.assertTrue(cache_get.called)
        self.assertTrue(cache_set.called)

    @mock.patch('gepify.providers.songs.cache.get',
                side_effect=lambda song: {'name': song, 'files': {}})
    @mock.patch('gepify.providers.songs.cache.set')
    def test_get_song_if_song_is_in_cache(self, cache_set, cache_get):
        song = songs.get_song('some song')
        self.assertEqual(song['name'], 'some song')
        self.assertEqual(song['files'], {})
        self.assertTrue(cache_get.called)
        self.assertFalse(cache_set.called)

    def test_add_song_file_if_format_is_unsupported(self):
        with self.assertRaises(Exception):
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


class PlaylistsTestCase(TestCase):
    def setUp(cls):
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
        with self.assertRaises(Exception):
            youtube.get_song_id('missing song')
