from . import spotify_service
from flask import session, render_template, redirect, request, url_for
from .view_decorators import login_required, logout_required
from . import models
from .models import SPOTIFY_CLIENT_ID, SPOTIFY_REDIRECT_URI
from ..util import get_random_str
import urllib


@spotify_service.route('/')
@login_required
def index():
    playlists = models.get_playlists()
    return render_template('show_playlists.html',
                           title='Spotify playlists',
                           playlists=playlists)


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
            models.request_access_token(payload)
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

    return redirect(url_for('views.index'))
