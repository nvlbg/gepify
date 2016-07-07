"""
    gepify.providers.soundcloud
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Downloader (and converter) for soundcloud songs.
"""

import soundcloud
import os
from .youtube import downloaders
from . import SUPPORTED_FORMATS

SOUNDCLOUD_CLIENT_ID = os.environ.get('SOUNDCLOUD_CLIENT_ID')


def get_song_id(song_name):
    """Get the soundcloud ids of a song.

    Parameters
    ----------
    song_name : str
        The song name.

    Returns
    -------
    tuple
        First element contains the soundcloud id of the song.
        Second element contains the id used for downloading
            the song (used by `download_song`).

    Raises
    ------
    RuntimeError
        If `song_name` id is not found.
    """

    client = soundcloud.Client(client_id=SOUNDCLOUD_CLIENT_ID)
    tracks = client.get('/tracks', q=song_name)

    if len(tracks) > 0:
        id = tracks[0].obj['id']
        download_id = '{}/{}'.format(
            tracks[0].obj['user']['permalink'], tracks[0].obj['permalink'])
        return (id, download_id)

    raise RuntimeError('Could not find song')


def download_song(id, format):
    """Download a song from soundcloud.

    Parameters
    ----------
    id : str
        The song's soundcloud id (download id).
    format : str
        The format in which to convert the song after downloading.

    Raises
    ------
    ValueError
        If `format` is not supported.
    """

    if format not in SUPPORTED_FORMATS:
        raise ValueError('Format not supported: {}'.format(format))

    with downloaders[format] as ydl:
        return ydl.download(['http://soundcloud.com/' + id])
