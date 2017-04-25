from flask import g
import os
import gepify.providers.songs as songs

YOUTUBE_CLIENT_ID = os.environ.get('YOUTUBE_CLIENT_ID')
YOUTUBE_CLIENT_SECRET = os.environ.get('YOUTUBE_CLIENT_SECRET')
YOUTUBE_REDIRECT_URI = os.environ.get('YOUTUBE_REDIRECT_URI')


def get_playlists():
    playlist_data = g.youtube.playlists().list(
        part='id,snippet,contentDetails',
        mine=True
    ).execute()

    playlists = []

    for item in playlist_data['items']:
        playlist = {
            'id': item['id'],
            'name': item['snippet']['title'],
            'num_tracks': item['contentDetails']['itemCount'],
            'image': item['snippet']['thumbnails']['medium']['url']
        }
        playlists.append(playlist)

    return playlists


def get_playlist(playlist_id):
    playlist_data = g.youtube.playlists().list(
        part='snippet',
        id=playlist_id
    ).execute()['items'][0]

    playlist = {
        'id': playlist_id,
        'name': playlist_data['snippet']['title'],
        'description': playlist_data['snippet']['description'],
        'tracks': [],
        'image': playlist_data['snippet']['thumbnails']['medium']['url']
    }

    playlist_songs = g.youtube.playlistItems().list(
        part='snippet,contentDetails',
        playlistId=playlist_id,
        maxResults=50
    ).execute()['items']

    for track in playlist_songs:
        song = songs.get_song(track['snippet']['title'])
        song['youtube'] = track['contentDetails']['videoId']
        playlist['tracks'].append(song)

    return playlist
