from . import spotify_service
from flask import (
    session, render_template, redirect,
    request, url_for, current_app, jsonify
)
from .view_decorators import login_required, logout_required
from . import models
from .models import SPOTIFY_CLIENT_ID, SPOTIFY_REDIRECT_URI
from ..util import (get_random_str, send_file)
import urllib
from gepify.providers import (
    songs, playlists, SUPPORTED_FORMATS, SUPPORTED_PROVIDERS, MIMETYPES
)
from gepify.influxdb import influxdb
from requests.utils import unquote


@spotify_service.route('/')
@login_required
def index():
    influxdb.count('spotify.index_page_visits')

    playlists = models.get_playlists()
    return render_template(
        'show_playlists.html',
        service='spotify',
        title='Spotify playlists',
        playlists=playlists
    )


@spotify_service.route('/login')
@logout_required
def login():
    influxdb.count('spotify.login_attempts')

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

    if error is not None or state is None or state != stored_state:
        current_app.logger.error('Could not authenticate spotify user:\n' +
                                 'error: {}\n'.format(error) +
                                 'state: {}\n'.format(state) +
                                 'stored_state: {}\n'.format(stored_state))
        return render_template(
            'show_message.html',
            message='There was an error while trying to authenticate you.'
                    'Please, try again.'), 503
    else:
        session.pop('spotify_auth_state', None)

        try:
            token_data = models.get_access_token_from_code(code)
            models.save_token_data_in_session(token_data)
            influxdb.count('spotify.logins')
            return redirect(url_for('spotify.index'))
        except Exception as e:
            current_app.logger.error(
                'Could not authenticate spotify user: {}'.format(e))
            return render_template(
                'show_message.html',
                message='There was an error while trying to authenticate you.'
                        'Please, try again.'), 503


@spotify_service.route('/logout')
def logout():
    session.pop('spotify_access_token', None)
    session.pop('spotify_refresh_token', None)
    session.pop('spotify_expires_at', None)
    session.pop('spotify_username', None)

    influxdb.count('spotify.logouts')

    return redirect(url_for('views.index'))


@spotify_service.route('/playlist/<id>')
@login_required
def playlist(id):
    playlist = models.get_playlist(id)
    return render_template(
        'show_tracks.html',
        service='spotify',
        playlist=playlist,
        SUPPORTED_FORMATS=SUPPORTED_FORMATS,
        SUPPORTED_PROVIDERS=SUPPORTED_PROVIDERS
    )


@spotify_service.route('/download_song/<path:song_name>/<format>')
@login_required
def download_song(song_name, format):
    influxdb.count('spotify.download_song_requests')

    if format not in SUPPORTED_FORMATS:
        current_app.logger.warning(
            'User tried to download a song in unsupported format.\n' +
            'Song: {}\n'.format(song_name) +
            'Format: {}\n'.format(format)
        )
        return render_template(
            'show_message.html', message='Unsupported format'), 400

    if not songs.has_song_format(song_name, format):
        provider = request.args.get('provider', SUPPORTED_PROVIDERS[0])
        if provider not in SUPPORTED_PROVIDERS:
            current_app.logger.warning(
                'User tried to download a song with unsupported provider.\n' +
                'Song: {}\n'.format(song_name) +
                'Format: {}\n'.format(format) +
                'Provider: {}\n'.format(provider)
            )
            return render_template(
                'show_message.html', message='Unsupported provider'), 400

        song = {'name': song_name}
        songs.download_song.delay(song, format=format, provider=provider)
        return render_template(
            'show_message.html', refresh_after=30,
            message='Your song has started downloading.'
                    'This page will automatically refresh after 30 seconds.')

    influxdb.count('spotify.downloaded_songs')
    song = songs.get_song(song_name)
    return send_file(
        '../' + song['files'][format],
        as_attachment=True,
        attachment_filename='{}.{}'.format(song['name'], format),
        mimetype=MIMETYPES[format]
    )


@spotify_service.route('/download_playlist', methods=['POST'])
@login_required
def download_playlist():
    influxdb.count('spotify.download_playlist_requests')

    playlist_id = request.form['playlist_id']
    format = request.form.get('format', SUPPORTED_FORMATS[0])
    provider = request.form.get('provider', SUPPORTED_PROVIDERS[0])

    if format not in SUPPORTED_FORMATS:
        current_app.logger.warning(
            'User tried to download a playlist in unsupported format.\n' +
            'Playlist: {}\n'.format(playlist_id) +
            'Format: {}\n'.format(format)
        )
        return render_template(
            'show_message.html', message='Unsupported format'), 400

    if provider not in SUPPORTED_PROVIDERS:
        current_app.logger.warning(
            'User tried to download a playlist with unsupported provider.\n' +
            'Playlist: {}\n'.format(playlist_id) +
            'Format: {}\n'.format(format) +
            'Provider: {}\n'.format(provider)
        )
        return render_template(
            'show_message.html', message='Unsupported provider'), 400

    playlist = models.get_playlist(playlist_id)
    if not playlists.has_playlist('spotify', playlist_id, format):
        playlists.download_playlist.delay(
            playlist, 'spotify', format=format, provider=provider)
        return render_template('show_message.html',
                               message='Your playlist is getting downloaded')

    playlist_checksum = playlists.checksum(playlist['tracks'])
    playlist_data = playlists.get_playlist('spotify', playlist_id, format)

    if playlist_data['checksum'] != playlist_checksum:
        playlists.download_playlist.delay(
            playlist, 'spotify', format=format, provider=provider)
        return render_template('show_message.html',
                               message='Your playlist is getting downloaded')

    influxdb.count('spotify.downloaded_playlists')
    return send_file(
        '../' + playlist_data['path'],
        as_attachment=True,
        attachment_filename='{}.zip'.format(playlist['name']),
        mimetype='application/zip'
    )


@spotify_service.route('/get_access_token/<code>')
def get_access_token(code):
    influxdb.count('spotify.access_token_requests')

    try:
        tokens = models.get_access_token_from_code(
                code, 'spotify-auth://callback')
        return jsonify(**tokens)
    except Exception as e:
        current_app.logger.error(
            'Could not authenticate spotify user: {}'.format(e))
        return jsonify(
            error='There was an error while trying to authenticate you.'
                  'Please, try again.'), 401

@spotify_service.route('/refresh_access_token/<refresh_token>')
def refresh_access_token(refresh_token):
    influxdb.count('spotify.refresh_token_requests')

    try:
        refresh_token = unquote(refresh_token)
        tokens = models.get_access_token_from_refresh_token(refresh_token)
        return jsonify(**tokens)
    except Exception as e:
        current_app.logger.error(
            'Could not refresh access token: {}'.format(e))
        return jsonify(error='Unable to refresh token.'), 401

