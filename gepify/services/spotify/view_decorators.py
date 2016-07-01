from flask import session, redirect, url_for, g, render_template, current_app
from .models import request_access_token
import time
import spotipy
from functools import wraps


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = session.get('spotify_access_token', None)
        refresh_token = session.get('spotify_refresh_token', None)
        expires_at = session.get('spotify_expires_at', None)

        if access_token is None or refresh_token is None or expires_at is None:
            return redirect(url_for('spotify.login'))

        now = int(time.time())
        if now >= expires_at:
            payload = {
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }

            try:
                request_access_token(payload)
                access_token = session['spotify_access_token']
            except Exception as e:
                current_app.logger.error(
                    'Could not refresh spotify token: {}'.format(e))
                return render_template(
                    'show_message.html',
                    message='There was an error with authenticating'), 503

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
            return render_template(
                'show_message.html',
                message='You need to be logged out to see this page'), 403

        return f(*args, **kwargs)
    return decorated_function
