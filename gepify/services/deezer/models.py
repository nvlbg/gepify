from flask import session
import gepify.providers.songs as songs
import os
import requests
import json
import time

DEEZER_APP_ID = os.environ.get('DEEZER_APP_ID')
DEEZER_SECRET = os.environ.get('DEEZER_SECRET')
DEEZER_REDIRECT_URI = os.environ.get('DEEZER_REDIRECT_URI')


def request_access_token(code):
    """Request access token from auth code and save it in the session.

    Parameters
    ----------
    code : str
        The authentication code.

    Raises
    ------
    RuntimeError
        If deezer API gives an error.
    """

    auth_request = requests.get(
        'https://connect.deezer.com/oauth/access_token.php' +
        '?output=json'
        '&app_id={}'.format(DEEZER_APP_ID) +
        '&secret={}'.format(DEEZER_SECRET) +
        '&code={}'.format(code))

    if auth_request.status_code == 200:
        response_data = json.loads(auth_request.text)
        access_token = response_data['access_token']
        expires_at = int(time.time()) + int(response_data['expires'])

        session['deezer_access_token'] = access_token
        session['deezer_expires_at'] = expires_at
    else:
        raise RuntimeError('Could not get authentication token')


def get_access_token():
    """Get access token from the session if it exists.

    Raises
    ------
    RuntimeError
        If the user is not authenticated yet.
    """

    access_token = session.get('deezer_access_token', None)
    if access_token is None:
        raise RuntimeError('User not authenticated')
    return access_token


def get_song_name(track):
    return '{} - {}'.format(track['artist']['name'], track['title'])


def get_playlists():
    """Get the playlists of the user.

    Returns
    -------
    list
        Each item represents a playlist and has the following information:
        id - The deezer playlist id.
        name - The name of the playlist.
        num_tracks - Total tracks in the playlist.
        image - A url for an image of the playlist.

    Raises
    ------
    RuntimeError
        If deezer API gives an error.
    """

    access_token = get_access_token()

    playlists_request = requests.get(
        'http://api.deezer.com/user/me/playlists' +
        '?access_token={}'.format(access_token)
    )

    if playlists_request.status_code != 200:
        raise RuntimeError('Deezer API error')

    playlists_data = json.loads(playlists_request.text)
    playlists = []

    for item in playlists_data['data']:
        if item['type'] == 'playlist':
            playlist = {
                'id': item['id'],
                'name': item['title'],
                'num_tracks': item['nb_tracks'],
                'image': item['picture_medium']
            }
            playlists.append(playlist)

    return playlists


def get_playlist(playlist_id, keep_song_names=False):
    """Get a playlist by its id.

    Parameters
    ----------
    playlist_id : str
        The id of the playlist.
    keep_song_names : bool
        If True the tracks will be returned as list of song names.
        If False tracks will be returned as dicts with information
        taken from `gepify.providers.songs`.

    Returns
    -------
    dict
        id - The deezer playlist id.
        name - The name of the playlist.
        description - The description of the playlist.
        image - A url for an image of the playlist.
        tracks - List of the tracks of the playlist.

    Raises
    ------
    RuntimeError
        If deezer API gives an error.
    """

    access_token = get_access_token()

    playlist_request = requests.get(
        'http://api.deezer.com/playlist/{}'.format(playlist_id) +
        '?access_token={}'.format(access_token)
    )

    if playlist_request.status_code != 200:
        raise RuntimeError('Deezer API error')

    playlist_data = json.loads(playlist_request.text)

    playlist = {
        'id': playlist_id,
        'name': playlist_data['title'],
        'description': playlist_data['description'],
        'tracks': [],
        'image': playlist_data['picture_medium']
    }

    for track in playlist_data['tracks']['data']:
        playlist['tracks'].append(get_song_name(track))

    # get latest info about the tracks from cache
    # in case a song's files have changed
    if not keep_song_names:
        tracks = []
        for track in playlist['tracks']:
            tracks.append(songs.get_song(track))
        playlist['tracks'] = tracks

    return playlist
