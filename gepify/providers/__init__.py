"""
    gepify.providers
    ~~~~~~~~~~~~~~~~

    Provides information about downloaded songs and playlists
    as well as methods for downloading songs and playlists from
    different sources (such as youtube or soundcloud).
"""

import os

DATA_DIRECTORY = os.environ.get('DATA_DIRECTORY', '.')
SONGS_DIRECTORY = '{}/songs'.format(DATA_DIRECTORY)
PLAYLISTS_DIRECTORY = '{}/playlists'.format(DATA_DIRECTORY)
SUPPORTED_FORMATS = ('mp3', 'ogg', 'opus', 'aac')
SUPPORTED_PROVIDERS = ('youtube', 'soundcloud')
MIMETYPES = {
    'mp3': 'audio/mpeg',
    'ogg': 'audio/ogg',
    'opus': 'audio/opus',
    'aac': 'audio/aac'
}
