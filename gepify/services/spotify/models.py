from flask import session, g
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
        # TODO
        raise Exception()


def get_username():
    sp = g.spotipy
    username = session.get('spotify_username', None)
    if username is None:
        username = sp.me()['id']
        session['spotify_username'] = username

    return username


def get_playlists():
    sp = g.spotipy
    username = get_username()

    results = sp.user_playlists(username)

    playlists = []

    for item in results['items']:
        playlist = {
            'id': item['id'],
            'images': item['images'],
            'name': item['name'],
            'num_tracks': item['tracks']['total']
        }
        playlists.append(playlist)

    # results = sp.current_user_saved_albums()['items']

    # for item in results:
    #     playlists.append(item['album']['name'])

    return playlists


def get_playlist(playlist_id):
    sp = g.spotipy
    username = get_username()

    result = sp.user_playlist(username, playlist_id)
    playlist = {
        'name': result['name'],
        'description': result['description'],
        'tracks': []
    }

    for item in result['tracks']['items']:
        track = item['track']
        playlist['tracks'].append({
            'artists': track['artists'],
            'name': track['name']
        })

    return playlist
