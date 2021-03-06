"""
    gepify.providers.playlists
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Provides information about downloaded playlists
    as well as functionality to download playlists.
"""

from werkzeug.contrib.cache import RedisCache
from gepify.celery import celery_app
from . import songs, PLAYLISTS_DIRECTORY
from .songs import SUPPORTED_FORMATS
from celery import chord
from celery.utils.log import get_task_logger
import zipfile
from hashlib import md5
import os
import time

cache = RedisCache(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=os.environ.get('REDIS_PORT', 6379),
    password=os.environ.get('REDIS_PASS', ''),
    key_prefix='playlist_',
    default_timeout=0
)
logger = get_task_logger(__name__)


def get_playlist(service, playlist, format):
    """Return information about a playlists if it exists.

    Parameters
    ----------
    service : str
        The service which provided the playlist (e.g. spotify).
    playlist : str
        The id of the playlist.
    format : str
        The format of the songs in the playlist.

    Returns
    -------
    dict
        If the playlist exists with the following information:
        path - The path on the filesystem where the playlist is located.
        checksum - The `checksum` of the tracks in the playlist.
    None
        If the playlist does not exist.
    """

    playlist = cache.get('{}_{}_{}'.format(service, playlist, format))
    if playlist == 'downloading':
        return None
    return playlist


def has_playlist(service, playlist, format):
    """Check if a playlist exists.

    Parameters
    ----------
    service : str
        The service which provided the playlist (e.g. spotify).
    playlist : str
        The id of the playlist.
    format : str
        The format of the songs in the playlist.

    Returns
    -------
    bool
        True if the playlist is downloaded and exists, False otherwise.
    """

    playlist = cache.get('{}_{}_{}'.format(service, playlist, format))
    return playlist is not None and playlist != 'downloading'


def checksum(tracks):
    """Return the checksum of the tracks.

    Parameters
    ----------
    tracks : list
        List of song names.

    Returns
    -------
    str
        A checksum for the given tracks.
    """

    track_names = sorted([track['name'] for track in tracks])
    return md5(''.join(track_names).encode('utf-8')).hexdigest()


@celery_app.task
def handle_error(playlist_cache_key):
    logger.error('An error occured while trying to download a playlist.'
                 ' Cache key: {}'.format(playlist_cache_key))
    cache.delete(playlist_cache_key)


@celery_app.task
def create_zip_playlist(playlist, service, checksum, format='mp3'):
    playlist_cache_key = '{}_{}_{}'.format(service, playlist['id'], format)
    playlist_zip_filename = '{}/{}.zip'.format(PLAYLISTS_DIRECTORY, playlist_cache_key)
    playlist_zip = zipfile.ZipFile(playlist_zip_filename, 'w')
    playlist_m3u_contents = ['#EXTM3U']

    for song_info in playlist['tracks']:
        song = songs.get_song(song_info['name'])
        playlist_zip.write(
            song['files'][format], '{}.{}'.format(song['name'], format))
        playlist_m3u_contents.append(
            '#EXTINF:{},{}\n{}.{}\n'.format(
                -1, song['name'], song['name'], format)
        )

    playlist_zip.writestr(
        '{}.m3u'.format(playlist['name']),
        bytes('\n'.join(playlist_m3u_contents), 'utf-8')
    )

    playlist_zip.close()
    cache.set(playlist_cache_key, {
        'path': playlist_zip_filename,
        'checksum': checksum
    })


@celery_app.task
def download_playlist(playlist, service, provider='youtube', format='mp3'):
    """Download a playlist.

    Parameters
    ----------
    playlist : dict
        Contains information about the playlist:
        id - The id of the playlist.
        tracks - List of dicts with information about songs.
        Each dict should have:
            name - The song name
            [provider] (optional) - Known id of the song by [provider].
            If present song will not be searched and will be directly
            downloaded by this id.
    service : str
        The service which provided the playlist (e.g. spotify).
    provider : str
        The provider to use when downloading the songs.
    format : str
        The format in which to convert the songs after downloading.

    Raises
    ------
    ValueError
        If `format` is not supported.
    """

    if format not in SUPPORTED_FORMATS:
        raise ValueError('Format not supported: {}'.format(format))

    playlist_cache_key = '{}_{}_{}'.format(service, playlist['id'], format)
    playlist_data = cache.get(playlist_cache_key)

    if playlist_data == 'downloading':
        logger.info(
            'Attempt to download a playlist in the process of downloading')
        return

    playlist_checksum = checksum(playlist['tracks'])

    if (playlist_data is not None and
            playlist_data['checksum'] == playlist_checksum):
        logger.info('Attempt to download an already downloaded playlist')
        return

    cache.set(playlist_cache_key, 'downloading')

    download_song_tasks = []
    for song in playlist['tracks']:
        if not songs.has_song_format(song['name'], format):
            download_song_tasks.append(
                songs.download_song.si(
                    song, provider, format
                )
            )

    if len(download_song_tasks) == 0:
        create_zip_playlist.apply_async(
            args=(playlist, service, playlist_checksum, format),
            link_error=handle_error.si(playlist_cache_key)
        )
    else:
        chord(
            download_song_tasks,
            create_zip_playlist.si(
                playlist, service, playlist_checksum, format
            ),
            link_error=handle_error.si(playlist_cache_key)
        ).delay()


@celery_app.task(ignore_result=True)
def clean_playlists():
    """Delete old playlist files."""

    for playlist in os.listdir(PLAYLISTS_DIRECTORY):
        path_to_playlist = '{}/{}'.format(PLAYLISTS_DIRECTORY, playlist)
        last_modified = os.path.getmtime(path_to_playlist)
        now = time.time()

        if now - last_modified > 30 * 60:  # 30 minutes
            os.remove(path_to_playlist)
            cache.delete(playlist[:-4])
            logger.info('Deleting old playlist: {}'.format(path_to_playlist))
