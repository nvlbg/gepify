import os
from apiclient.discovery import build
from apiclient.errors import HttpError
import youtube_dl
from . import SUPPORTED_FORMATS

DEVELOPER_KEY = os.environ.get('YOUTUBE_DEVELOPER_KEY')
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

downloaders = {
    'mp3': youtube_dl.YoutubeDL({
        'format': 'bestaudio/best',
        'outtmpl': 'songs/%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }),
    'ogg': youtube_dl.YoutubeDL({
        'format': 'bestaudio/best',
        'outtmpl': 'songs/%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'vorbis',
            'preferredquality': '192',
        }],
    }),
    'opus': youtube_dl.YoutubeDL({
        'format': 'bestaudio/best',
        'outtmpl': 'songs/%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'opus',
            'preferredquality': '192',
        }],
    }),
}


def get_song_id(track):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                    developerKey=DEVELOPER_KEY)

    search_response = youtube.search().list(
            q=track,
            part='id,snippet',
            maxResults=10
        ).execute()

    videos = []

    for search_result in search_response.get('items', []):
        if search_result['id']['kind'] == 'youtube#video':
            return search_result['id']['videoId']

    raise RuntimeError('Could not find song')


def download_song(id, format):
    if format not in SUPPORTED_FORMATS:
        raise ValueError('Format not supported: {}'.format(format))

    with downloaders[format] as ydl:
        return ydl.download(['http://www.youtube.com/watch?v=' + id])
