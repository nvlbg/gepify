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


def _get_token(payload):
    headers = {
        'Authorization': 'Basic {}'.format(SPOTIFY_AUTHORIZATION_DATA)
    }

    post_request = requests.post('https://accounts.spotify.com/api/token',
                                 data=payload, headers=headers)

    if post_request.status_code == 200:
        response_data = json.loads(post_request.text)
        access_token = response_data['access_token']
        refresh_token = response_data.get('refresh_token', None)
        expires_in = response_data['expires_in']

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': expires_in
        }
    else:
        raise RuntimeError('Could not get authentication token')


def get_access_token_from_code(code, redirect_uri=SPOTIFY_REDIRECT_URI):
    """Request access and refresh tokens from auth code

    Parameters
    ----------
    code : str
        The authentication code.
    redirect_uri : (optional) str
        The redirect uri used when getting the code

    Raises
    ------
    RuntimeError
        If spotify API gives an error.
    """
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri
    }

    return _get_token(payload)


def get_access_token_from_refresh_token(refresh_token):
    """Request access and refresh tokens from refresh token

    Parameters
    ----------
    refresh_token : str
        The refresh token from previous authentication.

    Raises
    ------
    RuntimeError
        If spotify API gives an error.
    """
    payload = {
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }

    return _get_token(payload)


def save_token_data_in_session(access_token_data):
    """Saves token data in session

    Parameters
    ----------
    access_token_data : dict
        The token data from get_access_token_from_code
        or get_access_token_from_refresh_token
    """
    access_token = access_token_data['access_token']
    refresh_token = access_token_data['refresh_token']
    expires_at = int(time.time()) + int(access_token_data['expires_in'])

    session['spotify_access_token'] = access_token
    if refresh_token:
        session['spotify_refresh_token'] = refresh_token
    session['spotify_expires_at'] = expires_at


def get_username():
    """Get current user's username."""

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
    """Get the playlists and saved albums of the user.

    Returns
    -------
    list
        Each item represents a playlist and has the following information:
        id - The spotify playlist (or album) id.
        name - The name of the playlist (album).
        num_tracks - Total tracks in the playlist (album).
        image - A url for an image of the playlist (album).
    """

    username = get_username()
    result = g.spotipy.user_playlists(username)

    playlists = []
    while result is not None:
        for item in result['items']:
            playlist = {
                'id': '{}:{}'.format(item['owner']['id'], item['id']),
                'image': item['images'][0]['url'],
                'name': item['name'],
                'num_tracks': item['tracks']['total']
            }

            for image in item['images']:
                if image['width'] == 300:
                    playlist['image'] = image['url']
                    break

            playlists.append(playlist)

        result = g.spotipy.next(result) if result['next'] else None

    result = g.spotipy.current_user_saved_albums()
    while result is not None:
        for item in result['items']:
            playlist = {
                'id': 'album:{}'.format(item['album']['id']),
                'image': item['album']['images'][0]['url'],
                'name': item['album']['name'],
                'num_tracks': item['album']['tracks']['total']
            }

            for image in item['album']['images']:
                if image['width'] == 300:
                    playlist['image'] = image['url']
                    break

            playlists.append(playlist)

        result = g.spotipy.next(result) if result['next'] else None

    return playlists


def _get_playlist(username, playlist_id):
    result = g.spotipy.user_playlist(username, playlist_id,
                                     'name,description,tracks,images')
    playlist = {
        'id': '{}:{}'.format(username, playlist_id),
        'name': result['name'],
        'description': result['description'],
        'image': result['images'][0]['url'],
        'tracks': []
    }

    for image in result['images']:
        if image['width'] == 300:
            playlist['image'] = image['url']
            break

    tracks = result['tracks']
    while tracks is not None:
        for item in tracks['items']:
            song = songs.get_song(get_song_name(item['track']))
            playlist['tracks'].append(song)
        tracks = g.spotipy.next(tracks) if tracks['next'] else None

    return playlist


def _get_album(album_id):
    result = g.spotipy.album(album_id)
    playlist = {
        'id': 'album:{}'.format(album_id),
        'name': result['name'],
        'image': result['images'][0]['url'],
        'tracks': []
    }

    for image in result['images']:
        if image['width'] == 300:
            playlist['image'] = image['url']
            break

    tracks = result['tracks']
    while tracks is not None:
        for track in tracks['items']:
            song = songs.get_song(get_song_name(track))
            playlist['tracks'].append(song)
        tracks = g.spotipy.next(tracks) if tracks['next'] else None

    return playlist


def get_playlist(playlist_id):
    """Get a playlist (or album) by its id.

    Parameters
    ----------
    playlist_id : str
        The id of the playlist (album).

    Returns
    -------
    dict
        id - The spotify playlist (album) id.
        name - The name of the playlist (album).
        description - The description of the playlist (album).
        image - A url for an image of the playlist (album).
        tracks - List of the tracks of the playlist (album).
    """

    username, playlist_id = playlist_id.split(':')
    if username == 'album':
        playlist = _get_album(playlist_id)
    else:
        playlist = _get_playlist(username, playlist_id)

    return playlist
