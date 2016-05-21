from flask import Blueprint, render_template, redirect, session, \
    request, g, url_for
from functools import wraps
import urllib
import os
import base64
import requests
import json
import time
import spotipy
from ..util import get_random_str
from pprint import pprint

SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI')
SPOTIFY_AUTHORIZATION_DATA = authorization_data = base64.b64encode(bytes(
    SPOTIFY_CLIENT_ID + ':' + SPOTIFY_CLIENT_SECRET, 'utf-8')).decode('utf-8')

spotify_service = Blueprint('spotify', __name__, template_folder='templates',
                            url_prefix='/spotify')


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


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = session.get('spotify_access_token', None)
        refresh_token = session.get('spotify_refresh_token', None)
        expires_at = session.get('spotify_expires_at', None)

        if access_token is None or refresh_token is None or expires_at is None:
            return redirect(url_for('spotify.login'))

        now = int(time.time())
        if expires_at >= now:
            payload = {
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }

            try:
                request_access_token(payload)
                access_token = session['spotify_access_token']
            except:
                # TODO
                raise

        g.spotipy = spotipy.Spotify(auth=access_token)
        return f(*args, **kwargs)
    return decorated_function


def logout_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = session.get('spotify_access_token', None)
        refresh_token = session.get('spotify_refresh_token', None)
        expires_at = session.get('spotify_expires_at', None)

        if access_token is not None or \
                refresh_token is not None or expires_at is not None:
            # TODO
            pass

        return f(*args, **kwargs)
    return decorated_function


@spotify_service.route('/')
@login_required
def index():
    sp = g.spotipy
    username = session.get('spotify_username', None)
    if username is None:
        username = sp.me()['id']
        session['spotify_username'] = username
    
    results = sp.user_playlists(username)

    playlists = []

    for item in results['items']:
        playlist = item['name']
        playlists.append(playlist)

    results = sp.current_user_saved_albums()['items']

    for item in results:
        playlists.append(item['album']['name'])

    return render_template('show_playlists.html', playlists=playlists)


@spotify_service.route('/login')
@logout_required
def login():
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


@spotify_service.route('/callback')
def callback():
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
        session.pop('spotify_auth_state', None)
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': SPOTIFY_REDIRECT_URI
        }

        try:
            request_access_token(payload)
            return redirect(url_for('spotify.index'))
        except:
            # TODO
            return 'Error: did not get token'


@spotify_service.route('/logout')
def logout():
    session.pop('spotify_access_token', None)
    session.pop('spotify_refresh_token', None)
    session.pop('spotify_expires_at', None)
    session.pop('spotify_username', None)

    return redirect(url_for('index'))
