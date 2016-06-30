from werkzeug.contrib.cache import RedisCache
from gepify.celery import celery_app
from . import youtube, songs
from .songs import SUPPORTED_FORMATS
from celery import chord
import zipfile
from hashlib import md5

cache = RedisCache(key_prefix='playlist_', default_timeout=0)


def get_playlist(service, playlist, format):
    playlist = cache.get('{}_{}_{}'.format(service, playlist, format))
    if playlist == 'downloading':
        return None
    return playlist


def has_playlist(service, playlist, format):
    playlist = cache.get('{}_{}_{}'.format(service, playlist, format))
    return playlist is not None and playlist != 'downloading'


def checksum(tracks):
    return md5(''.join(sorted(tracks)).encode('utf-8')).hexdigest()


@celery_app.task
def create_zip_playlist(playlist, service, checksum, format='mp3'):
    playlist_cache_key = '{}_{}_{}'.format(service, playlist['id'], format)
    playlist_zip_filename = 'playlists/{}.zip'.format(playlist_cache_key)
    playlist_zip = zipfile.ZipFile(playlist_zip_filename, 'w')

    for song_name in playlist['tracks']:
        song = songs.get_song(song_name)
        playlist_zip.write(song['files'][format],
                           '{}.{}'.format(song['name'], format))

    playlist_zip.close()
    cache.set(playlist_cache_key, {
        'path': playlist_zip_filename,
        'checksum': checksum
    })


@celery_app.task
def download_playlist(playlist, service, provider='youtube', format='mp3'):
    if format not in SUPPORTED_FORMATS:
        raise Exception('Unsupported format')

    playlist_cache_key = '{}_{}_{}'.format(service, playlist['id'], format)
    playlist_checksum = checksum(playlist['tracks'])
    playlist_data = cache.get(playlist_cache_key)

    if (playlist_data is not None and playlist_data['checksum'] ==
            playlist_checksum) or playlist_data == 'downloading':
        return

    cache.set(playlist_cache_key, 'downloading')

    download_song_tasks = []
    for song_name in playlist['tracks']:
        if not songs.has_song_format(song_name, format):
            download_song_tasks.append(
                songs.download_song.s(song_name, provider, format))

    if len(download_song_tasks) == 0:
        create_zip_playlist.delay(
            playlist, service, playlist_checksum, format)
    else:
        chord(download_song_tasks,
              create_zip_playlist.si(
                  playlist, service, playlist_checksum, format)).delay()
