from . import deezer_service
from flask import (
    session, render_template, redirect, request,
    url_for, send_file, current_app
)
from .view_decorators import login_required, logout_required
from . import models
from .models import DEEZER_APP_ID, DEEZER_REDIRECT_URI
from ..util import get_random_str
import urllib
from gepify.providers import (
    songs, playlists, SUPPORTED_FORMATS, MIMETYPES
)


@deezer_service.route('/')
@login_required
def index():
    playlists = models.get_playlists()
    return render_template(
        'show_playlists.html',
        service='deezer',
        title='Deezer playlists',
        playlists=playlists
    )


@deezer_service.route('/login')
@logout_required
def login():
    state = get_random_str(16)
    session['deezer_auth_state'] = state
    query_parameters = {
        'app_id': DEEZER_APP_ID,
        'redirect_uri': DEEZER_REDIRECT_URI,
        'perms': 'basic_access',
        'state': state,
    }

    query_parameters = '&'.join(['{}={}'.format(key, urllib.parse.quote(val))
                                 for key, val in query_parameters.items()])
    auth_url = 'https://connect.deezer.com/oauth/auth.php?' + query_parameters
    return redirect(auth_url)


@deezer_service.route('/callback')
def callback():
    error = request.args.get('error_reason', None)
    code = request.args.get('code', None)
    state = request.args.get('state', None)
    stored_state = session.get('deezer_auth_state', None)

    if error is not None or state is None or state != stored_state:
        current_app.logger.error('Could not authenticate deezer user:\n' +
                                 'error: {}\n'.format(error) +
                                 'state: {}\n'.format(state) +
                                 'stored_state: {}\n'.format(stored_state))
        return render_template(
            'show_message.html',
            message='There was an error while trying to authenticate you.'
                    'Please, try again.'), 503
    else:
        session.pop('deezer_auth_state', None)
        try:
            models.request_access_token(code)
            return redirect(url_for('deezer.index'))
        except Exception as e:
            current_app.logger.error(
                'Could not authenticate deezer user: {}'.format(e))
            return render_template(
                'show_message.html',
                message='There was an error while trying to authenticate you.'
                        'Please, try again.'), 503


@deezer_service.route('/logout')
def logout():
    session.pop('deezer_access_token', None)
    session.pop('deezer_expires_at', None)
    session.pop('deezer_user_id', None)

    return redirect(url_for('views.index'))


@deezer_service.route('/playlist/<id>')
@login_required
def playlist(id):
    playlist = models.get_playlist(id)
    return render_template(
        'show_tracks.html',
        service='deezer',
        playlist=playlist,
        SUPPORTED_FORMATS=SUPPORTED_FORMATS
    )


@deezer_service.route('/download_song/<song_name>/<format>')
@login_required
def download_song(song_name, format):
    if format not in SUPPORTED_FORMATS:
        current_app.logger.warning(
            'User tried to download a song in unsupported format.' +
            'Song: {}'.format(song_name) +
            'Format: {}'.format(format))
        return render_template(
            'show_message.html', message='Unsupported format'), 400

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
        mimetype=MIMETYPES[format]
    )


@deezer_service.route('/download_playlist', methods=['POST'])
@login_required
def download_playlist():
    playlist_id = request.form['playlist_id']
    format = request.form['format']

    if format not in SUPPORTED_FORMATS:
        current_app.logger.warning(
            'User tried to download a playlist in unsupported format.' +
            'Playlist: {}'.format(playlist_id) +
            'Format: {}'.format(format))
        return render_template(
            'show_message.html', message='Unsupported format'), 400

    playlist = models.get_playlist(playlist_id, keep_song_names=True)
    if not playlists.has_playlist('deezer', playlist_id, format):
        playlists.download_playlist.delay(playlist, 'deezer', format=format)
        return render_template('show_message.html',
                               message='Your playlist is getting downloaded')

    playlist_checksum = playlists.checksum(playlist['tracks'])
    playlist_data = playlists.get_playlist('deezer', playlist_id, format)

    if playlist_data['checksum'] != playlist_checksum:
        playlists.download_playlist.delay(playlist, 'deezer', format=format)
        return render_template('show_message.html',
                               message='Your playlist is getting downloaded')

    return send_file(
        '../' + playlist_data['path'],
        as_attachment=True,
        attachment_filename='{}.zip'.format(playlist['name']),
        mimetype='application/zip'
    )
