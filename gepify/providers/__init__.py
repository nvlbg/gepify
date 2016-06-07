from werkzeug.contrib.cache import RedisCache
from . import youtube

SUPPORTED_FORMATS = ['mp3']
cache = RedisCache(key_prefix='song_info_')


def get_song(song_name):
    song = cache.get(song_name)
    if song is None:
        song = {
            'name': song_name,
            'files': {}
        }

        cache.set(song_name, song)

    return song
