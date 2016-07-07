"""
    gepify.providers
    ~~~~~~~~~~~~~~~~

    Provides information about downloaded songs and playlists
    as well as methods for downloading songs and playlists from
    different sources (such as youtube or soundcloud).
"""

SUPPORTED_FORMATS = ('mp3', 'ogg', 'opus', 'aac')
SUPPORTED_PROVIDERS = ('youtube', 'soundcloud')
MIMETYPES = {
    'mp3': 'audio/mpeg',
    'ogg': 'audio/ogg',
    'opus': 'audio/opus',
    'aac': 'audio/aac'
}
