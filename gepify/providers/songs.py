from werkzeug.contrib.cache import RedisCache
from gepify.celery import celery_app
from . import youtube

SUPPORTED_FORMATS = ['mp3']
MIMETYPES = {
    'mp3': 'audio/mpeg'
}

cache = RedisCache(key_prefix='song_info_', default_timeout=0)


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
        # TODO
        pass

    song = get_song(song_name)
    song['files'][format] = file
    cache.set(song_name, song)


def has_song_format(song_name, format):
    song = cache.get(song_name)

    if song is None or format not in song['files'].keys():
        return False

    return song['files'][format] != 'downloading'


@celery_app.task
def download_song(song_name, provider='youtube', format='mp3'):
    if format not in SUPPORTED_FORMATS:
        # TODO
        pass

    song = get_song(song_name)

    if format in song['files'] and song['files'][format] == 'downloading':
        return

    song['files'][format] = 'downloading'
    cache.set(song_name, song)

    if provider == 'youtube':
        song_id = youtube.get_song_id(song_name)
        youtube.download_song(song_id)
        add_song_file(song_name, 'songs/{}.{}'.format(song_id, format), format)
    else:
        del song['files'][format]
        cache.set(song_name, song)
        # TODO: throw some exception
