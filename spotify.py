from flask import Blueprint, render_template, redirect, session, request
import urllib
import os
import base64
import requests
import json
import spotipy
from util import get_random_str

SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI')

spotify_provider = Blueprint('spotify', __name__)


@spotify_provider.route('/login/spotify')
def spotify_login():
    state = get_random_str(16)
    session['spotify_auth_state'] = state
    query_parameters = {
        'response_type': 'code',
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'scope': 'user-library-read',
        'state': state,
        'client_id': SPOTIFY_CLIENT_ID
    }

    query_parameters = '&'.join(['{}={}'.format(key, urllib.parse.quote(val))
                                 for key, val in query_parameters.items()])
    auth_url = 'https://accounts.spotify.com/authorize/?' + query_parameters
    return redirect(auth_url)


@spotify_provider.route('/callback/spotify')
def spotify_callback():
    error = request.args.get('error', None)
    code = request.args.get('code', None)
    state = request.args.get('state', None)
    stored_state = session.get('spotify_auth_state', None)

    if error is not None:
        # TODO
        pass
    elif state is None or state != stored_state:
        # TODO
        # return redirect()
        return 'Error: state mismatch'
    else:
        del session['spotify_auth_state']
        code_payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': SPOTIFY_REDIRECT_URI
        }
        authorization_data = base64.b64encode(bytes(
            SPOTIFY_CLIENT_ID + ':' + SPOTIFY_CLIENT_SECRET, 'utf-8')).decode('utf-8')
        headers = {
            'Authorization': 'Basic {}'.format(authorization_data)
        }
        post_request = requests.post('https://accounts.spotify.com/api/token', data=code_payload, headers=headers)

        if post_request.status_code == 200:
            response_data = json.loads(post_request.text)
            access_token = response_data['access_token']
            refresh_token = response_data['refresh_token']

            session['spotify_access_token'] = access_token
            session['spotify_refresh_token'] = refresh_token

            sp = spotipy.Spotify(auth=access_token)
            results = sp.current_user_saved_tracks()
            response = []
            for item in results['items']:
                track = item['track']
                response.append(track['name'] + ' - ' + track['artists'][0]['name'])

            return '\n'.join(response)
        else:
            # TODO
            return 'Error: did not get token'

