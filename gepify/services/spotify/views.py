from . import spotify_service
from flask import (
    session, render_template, redirect, request, url_for, send_file
)
from .view_decorators import login_required, logout_required
from . import models
from .models import SPOTIFY_CLIENT_ID, SPOTIFY_REDIRECT_URI
from ..util import get_random_str
import urllib
from gepify.providers import songs, playlists
from gepify.providers.songs import SUPPORTED_FORMATS, MIMETYPES
from pprint import pprint


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


@spotify_service.route('/playlist/<id>')
@login_required
def playlist(id):
    playlist = models.get_playlist(id)
    return render_template('show_tracks.html',
                           playlist=playlist,
                           SUPPORTED_FORMATS=SUPPORTED_FORMATS)


@spotify_service.route('/download_playlist', methods=['POST'])
@login_required
def download_playlist():
    playlist_id = request.form['playlist_id']
    format = request.form['format']

    if format not in SUPPORTED_FORMATS:
        # TODO
        return 'Unsupported format'

    if playlists.has_playlist('spotify', playlist_id, format):
        playlist = playlists.get_playlist('spotify', playlist_id, format)
        playlist_name = models.get_playlist_name(playlist_id)
        return send_file(
            '../' + playlist,
            as_attachment=True,
            attachment_filename='{}.zip'.format(playlist_name),
            mimetype='application/zip'
        )

    playlist = models.get_playlist(playlist_id, keep_song_names=True)
    playlists.download_playlist.delay(playlist, 'spotify', format=format)
    return render_template('show_message.html',
                           message='Your playlist is getting downloaded')


@spotify_service.route('/download_song/<song_name>/<format>')
@login_required
def download_song(song_name, format):
    if format not in SUPPORTED_FORMATS:
        # TODO
        return 'Unsupported format'

    if not songs.has_song_format(song_name, format):
        songs.download_song.delay(song_name, format=format)
        return render_template(
            'show_message.html', refresh_after=30,
            message='Your song has started downloading.'
                    'This page will automatically refresh after 30 seconds.')

    song = songs.get_song(song_name)
    return send_file(
        '../' + song['files'][format],
        as_attachment=True,
        attachment_filename=song['name'],
        mimetype=MIMETYPES[format])
