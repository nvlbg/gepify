from flask import session, g
import gepify.providers.songs as songs
import os
import base64
import requests
import time
import json

SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI')
SPOTIFY_AUTHORIZATION_DATA = base64.b64encode(bytes(
    SPOTIFY_CLIENT_ID + ':' + SPOTIFY_CLIENT_SECRET, 'utf-8')).decode('utf-8')


def request_access_token(payload):
    headers = {
        'Authorization': 'Basic {}'.format(SPOTIFY_AUTHORIZATION_DATA)
    }

    post_request = requests.post('https://accounts.spotify.com/api/token',
                                 data=payload, headers=headers)

    if post_request.status_code == 200:
        response_data = json.loads(post_request.text)
        access_token = response_data['access_token']
        refresh_token = response_data.get('refresh_token', None)
        expires_at = int(time.time()) + int(response_data['expires_in'])

        session['spotify_access_token'] = access_token
        if refresh_token:
            session['spotify_refresh_token'] = refresh_token
        session['spotify_expires_at'] = expires_at
    else:
        raise RuntimeError('Could not get authentication token')


def get_username():
    username = session.get('spotify_username', None)
    if username is None:
        username = g.spotipy.me()['id']
        session['spotify_username'] = username

    return username


def get_song_name(track):
    return '{} - {}'.format(
        ' & '.join([artist['name'] for artist in track['artists']]),
        track['name'])


def get_playlists():
    username = get_username()
    result = g.spotipy.user_playlists(username)

    playlists = []
    while result is not None:
        for item in result['items']:
            playlist = {
                'id': '{}:{}'.format(item['owner']['id'], item['id']),
                'images': item['images'],
                'name': item['name'],
                'num_tracks': item['tracks']['total']
            }
            playlists.append(playlist)

        result = g.spotipy.next(result) if result['next'] else None

    result = g.spotipy.current_user_saved_albums()
    while result is not None:
        for item in result['items']:
            playlist = {
                'id': 'album:{}'.format(item['album']['id']),
                'images': item['album']['images'],
                'name': item['album']['name'],
                'num_tracks': item['album']['tracks']['total']
            }
            playlists.append(playlist)

        result = g.spotipy.next(result) if result['next'] else None

    return playlists


def _get_playlist(username, playlist_id):
    result = g.spotipy.user_playlist(username, playlist_id,
                                     'name,description,tracks')
    playlist = {
        'id': '{}:{}'.format(username, playlist_id),
        'name': result['name'],
        'description': result['description'],
        'tracks': []
    }

    tracks = result['tracks']
    while tracks is not None:
        for item in tracks['items']:
            playlist['tracks'].append(get_song_name(item['track']))
        tracks = g.spotipy.next(tracks) if tracks['next'] else None

    return playlist


def _get_album(album_id):
    result = g.spotipy.album(album_id)
    playlist = {
        'id': 'album:{}'.format(album_id),
        'name': result['name'],
        'tracks': []
    }

    tracks = result['tracks']
    while tracks is not None:
        for track in tracks['items']:
            playlist['tracks'].append(get_song_name(track))
        tracks = g.spotipy.next(tracks) if tracks['next'] else None

    return playlist


def get_playlist(playlist_id, keep_song_names=False):
    username, playlist_id = playlist_id.split(':')
    if username == 'album':
        playlist = _get_album(playlist_id)
    else:
        playlist = _get_playlist(username, playlist_id)

    # get latest info about the tracks from cache
    # in case a song's files have changed
    if not keep_song_names:
        tracks = []
        for track in playlist['tracks']:
            tracks.append(songs.get_song(track))
        playlist['tracks'] = tracks

    return playlist
