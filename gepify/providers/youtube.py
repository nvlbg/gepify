"""
    gepify.providers.youtube
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Downloader (and converter) for youtube videos.
"""

import os
from apiclient.discovery import build
from apiclient.errors import HttpError
import youtube_dl
from . import SUPPORTED_FORMATS, SONGS_DIRECTORY

DEVELOPER_KEY = os.environ.get('YOUTUBE_DEVELOPER_KEY')
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

downloaders = {
    'mp3': youtube_dl.YoutubeDL({
        'format': 'bestaudio/best',
        'outtmpl': '{}/%(id)s.%(ext)s'.format(SONGS_DIRECTORY),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }),
    'ogg': youtube_dl.YoutubeDL({
        'format': 'bestaudio/best',
        'outtmpl': '{}/%(id)s.%(ext)s'.format(SONGS_DIRECTORY),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'vorbis',
            'preferredquality': '192',
        }],
    }),
    'opus': youtube_dl.YoutubeDL({
        'format': 'bestaudio/best',
        'outtmpl': '{}/%(id)s.%(ext)s'.format(SONGS_DIRECTORY),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'opus',
            'preferredquality': '192',
        }],
    }),
    'aac': youtube_dl.YoutubeDL({
        'format': 'bestaudio/best',
        'outtmpl': '{}/%(id)s.%(ext)s'.format(SONGS_DIRECTORY),
        'postprocessor_args': ['-strict', '-2'],
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'aac',
            'preferredquality': '192',
        }],
    }),
}


def get_song_id(song_name):
    """Get the youtube id of a song.

    Parameters
    ----------
    song_name : str
        The song name.

    Returns
    -------
    str
        The youtube if for `song_name`.

    Raises
    ------
    RuntimeError
        If `song_name` id is not found.
    """

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                    developerKey=DEVELOPER_KEY)

    search_response = youtube.search().list(
            q=song_name,
            part='id,snippet',
            maxResults=10
        ).execute()

    videos = []

    for search_result in search_response.get('items', []):
        if search_result['id']['kind'] == 'youtube#video':
            return search_result['id']['videoId']

    raise RuntimeError('Could not find song')


def download_song(id, format):
    """Download a song from youtube.

    Parameters
    ----------
    id : str
        The song's youtube id.
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
        return ydl.download(['http://www.youtube.com/watch?v=' + id])
