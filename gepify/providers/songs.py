from werkzeug.contrib.cache import RedisCache
from gepify.celery import celery_app
from celery.utils.log import get_task_logger
from . import youtube, soundcloud, SUPPORTED_FORMATS, MIMETYPES

cache = RedisCache(key_prefix='song_info_', default_timeout=0)
logger = get_task_logger(__name__)


def get_song(song_name):
    song = cache.get(song_name)
    if song is None:
        song = {
            'name': song_name,
            'files': {}
        }

        cache.set(song_name, song)

    return song


def add_song_file(song_name, file, format):
    if format not in SUPPORTED_FORMATS:
        raise ValueError('Format not supported: {}'.format(format))

    song = get_song(song_name)
    song['files'][format] = file
    cache.set(song_name, song)


def has_song_format(song_name, format):
    song = cache.get(song_name)

    if song is None or format not in song['files'].keys():
        return False

    return song['files'][format] != 'downloading'


@celery_app.task(bind=True)
def download_song(self, song_name, provider='youtube', format='mp3'):
    if format not in SUPPORTED_FORMATS:
        raise ValueError('Format not supported: {}'.format(format))

    song = get_song(song_name)

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
    cache.set(song_name, song)

    try:
        if provider == 'youtube':
            song_id = youtube.get_song_id(song_name)
            youtube.download_song(song_id, format)
            add_song_file(
                song_name, 'songs/{}.{}'.format(song_id, format), format)
        elif provider == 'soundcloud':
            song_id, download_id = soundcloud.get_song_id(song_name)
            soundcloud.download_song(download_id, format)
            add_song_file(
                song_name, 'songs/{}.{}'.format(song_id, format), format)
        else:
            raise ValueError('Provider not found: {}'.format(provider))
    except:
        del song['files'][format]
        cache.set(song_name, song)
        raise
