from flask import session, g
import gepify.providers.songs as songs
from werkzeug.contrib.cache import RedisCache
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

cache = RedisCache(key_prefix='spotify_')


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
    sp = g.spotipy
    username = session.get('spotify_username', None)
    if username is None:
        username = sp.me()['id']
        session['spotify_username'] = username

    return username


def get_song_name(track):
    return '{} - {}'.format(
        ' & '.join([artist['name'] for artist in track['artists']]),
        track['name'])


def get_playlists():
    username = get_username()

    playlists = cache.get('user_playlists_{}'.format(username))
    if playlists is None:
        playlists = []
        sp = g.spotipy
        results = sp.user_playlists(username)

        for item in results['items']:
            playlist = {
                'id': '{}:{}'.format(item['owner']['id'], item['id']),
                'images': item['images'],
                'name': item['name'],
                'num_tracks': item['tracks']['total']
            }
            playlists.append(playlist)

        # results = sp.current_user_saved_albums()['items']

        # for item in results:
        #     playlists.append(item['album']['name'])
        cache.set('user_playlists_{}'.format(username),
                  playlists, timeout=5*60)

    return playlists


def get_playlist(playlist_id, keep_song_names=False):
    playlist = cache.get('user_playlist_{}'.format(playlist_id))
    if playlist is None:
        sp = g.spotipy
        username, pid = playlist_id.split(':')
        result = sp.user_playlist(username, pid)
        playlist = {
            'id': playlist_id,
            'name': result['name'],
            'description': result['description'],
            'tracks': []
        }

        for item in result['tracks']['items']:
            track = item['track']
            playlist['tracks'].append(get_song_name(track))

        cache.set('user_playlist_{}'.format(playlist_id),
                  playlist, timeout=5*60)

    # get latest info about the tracks from cache
    # in case a song's files have changed
    if not keep_song_names:
        tracks = []
        for track in playlist['tracks']:
            tracks.append(songs.get_song(track))
        playlist['tracks'] = tracks

    return playlist


def get_playlist_name(playlist_id):
    username = get_username()

    playlist = cache.get('user_playlist_{}'.format(playlist_id))
    if playlist is None:
        playlist = get_playlist(playlist_id, keep_song_names=True)

    return playlist['name']
