"""
    gepify.providers.songs
    ~~~~~~~~~~~~~~~~~~~~~~

    Provides information about downloaded songs
    as well as functionality to download songs.
"""

from werkzeug.contrib.cache import RedisCache
from gepify.celery import celery_app
from celery.utils.log import get_task_logger
from . import youtube, soundcloud, SUPPORTED_FORMATS

cache = RedisCache(key_prefix='song_info_', default_timeout=0)
logger = get_task_logger(__name__)


def get_song(song_name):
    """Return information about a song.

    Parameters
    ----------
    song_name : str
        The song name.

    Returns
    -------
    dict
        name - The song name.
        files - Dictionary with downloaded files for this song.
    """

    song = cache.get(song_name)
    if song is None:
        song = {
            'name': song_name,
            'files': {}
        }

        cache.set(song_name, song)

    return song


def add_song_file(song_name, file, format):
    """Mark a song as downloaded in desired format.

    Parameters
    ----------
    song_name : str
        The song name.
    file : str
        The file of the song as a path on the filesystem.
    format : str
        The format of the file.

    Raises
    ------
    ValueError
        If `format` is not supported.
    """

    if format not in SUPPORTED_FORMATS:
        raise ValueError('Format not supported: {}'.format(format))

    song = get_song(song_name)
    song['files'][format] = file
    cache.set(song_name, song)


def has_song_format(song_name, format):
    """Check if a song is already downloaded in the desired format.

    Parameters
    ----------
    song_name : str
        The song name.
    format : str
        The format to check.

    Returns
    -------
    bool
        True if `song_name` is downloaded in `format`, False otherwise.
    """

    song = cache.get(song_name)

    if song is None or format not in song['files'].keys():
        return False

    return song['files'][format] != 'downloading'


@celery_app.task(bind=True)
def download_song(self, song_info, provider='youtube', format='mp3'):
    """Download a song.

    Parameters
    ----------
    song_info : dict
        Contains information about the song.
        name - The song name
        [provider] (optional) - Known id of the song by [provider].
        If present song will not be searched and will be directly
        downloaded by this id.
    provider : str
        The provider which will download the song. Default: 'youtube'
    format : str
        The format in which the song will be saved. Default: 'mp3'

    Raises
    ------
    ValueError
        If either `format` or `provider` is not supported.
    """

    if format not in SUPPORTED_FORMATS:
        raise ValueError('Format not supported: {}'.format(format))

    song = get_song(song_info['name'])

    if format in song['files']:
        if song['files'][format] == 'downloading':
            if self.request.chord is None:
                logger.info(
                    'Attempt to download a song in the process of downloading')
            else:
                logger.info(
                    'Song is aleady downloading. Will retry in 5 seconds.')
                self.retry(countdown=5)
            return
        elif song['files'][format] is not None:
            logger.info('Attempt to download already downloaded song.'
                        'Cache: {}'.format(song['files'][format]))
            return

    song['files'][format] = 'downloading'
    cache.set(song_info['name'], song)

    try:
        song_id = song_info.get(provider)
        if provider == 'youtube':
            if 'youtube' not in song_info:
                song_id = youtube.get_song_id(song_info['name'])
            youtube.download_song(song_id, format)
            add_song_file(
                song_info['name'],
                'songs/{}.{}'.format(song_id, format), format)
        elif provider == 'soundcloud':
            if 'soundcloud' not in song_info:
                song_id, download_id = soundcloud.get_song_id(
                    song_info['name'])
            else:
                song_id, download_id = song_id
            soundcloud.download_song(download_id, format)
            add_song_file(
                song_info['name'],
                'songs/{}.{}'.format(song_id, format), format)
        else:
            raise ValueError('Provider not found: {}'.format(provider))
    except:
        del song['files'][format]
        cache.set(song_info['name'], song)
        raise
