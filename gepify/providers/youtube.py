import os
from apiclient.discovery import build
from apiclient.errors import HttpError
import youtube_dl

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

    raise Exception('Could not find song')


def get_song_ids(tracks):
    return {track: get_song_id(track) for track in tracks}


def download_song(id, format):
    with downloaders[format] as ydl:
        return ydl.download(['http://www.youtube.com/watch?v=' + id])
