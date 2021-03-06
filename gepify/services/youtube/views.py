from flask import (
    session, render_template, redirect, request,
    url_for, current_app, jsonify
)
from ..util import send_file
from . import youtube_service
from .view_decorators import login_required, logout_required
from oauth2client import client
from . import models
from .models import (
    YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REDIRECT_URI
)
from gepify.providers import (
    songs, playlists, SUPPORTED_FORMATS, SUPPORTED_PROVIDERS, MIMETYPES
)
from gepify.influxdb import influxdb
from requests.utils import unquote


@youtube_service.route('/')
@login_required
def index():
    influxdb.count('youtube.index_page_visits')

    playlists = models.get_playlists()
    return render_template(
        'show_playlists.html',
        service='youtube',
        title='Youtube playlists',
        playlists=playlists
    )


@youtube_service.route('/login')
@logout_required
def login():
    influxdb.count('youtube.login_attempts')

    flow = client.OAuth2WebServerFlow(
        YOUTUBE_CLIENT_ID,
        YOUTUBE_CLIENT_SECRET,
        scope='https://www.googleapis.com/auth/youtube.readonly',
        redirect_uri=YOUTUBE_REDIRECT_URI
    )

    auth_uri = flow.step1_get_authorize_url()

    return redirect(auth_uri)


@youtube_service.route('/callback')
def callback():
    code = request.args.get('code', None)

    if code is None:
        return render_template(
            'show_message.html',
            message='There was an error while trying to authenticate you.'
                    'Please, try again.'), 503

    flow = client.OAuth2WebServerFlow(
        YOUTUBE_CLIENT_ID,
        YOUTUBE_CLIENT_SECRET,
        scope='https://www.googleapis.com/auth/youtube.readonly',
        redirect_uri=YOUTUBE_REDIRECT_URI
    )
    credentials = flow.step2_exchange(code)
    session['credentials'] = credentials.to_json()
    influxdb.count('youtube.logins')
    return redirect(url_for('youtube.index'))


@youtube_service.route('/logout')
@login_required
def logout():
    session.pop('credentials', None)

    influxdb.count('youtube.logouts')

    return redirect(url_for('views.index'))


@youtube_service.route('/playlist/<id>')
@login_required
def playlist(id):
    playlist = models.get_playlist(id)
    return render_template(
        'show_tracks.html',
        service='youtube',
        playlist=playlist,
        SUPPORTED_FORMATS=SUPPORTED_FORMATS,
        SUPPORTED_PROVIDERS=SUPPORTED_PROVIDERS
    )


@youtube_service.route('/download_song/<path:song_name>/<format>')
@login_required
def download_song(song_name, format):
    influxdb.count('youtube.download_song_requests')

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

        youtube_id = request.args.get('provider_id', None)
        if youtube_id is not None and youtube_id != '':
            song['youtube'] = youtube_id

        songs.download_song.delay(
            song, format=format, provider=provider)
        return render_template(
            'show_message.html', refresh_after=30,
            message='Your song has started downloading.'
                    'This page will automatically refresh after 30 seconds.')

    influxdb.count('youtube.downloaded_songs')
    song = songs.get_song(song_name)
    return send_file(
        song['files'][format],
        as_attachment=True,
        attachment_filename='{}.{}'.format(song['name'], format),
        mimetype=MIMETYPES[format]
    )


@youtube_service.route('/download_playlist', methods=['POST'])
@login_required
def download_playlist():
    influxdb.count('youtube.download_playlist_requests')
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
    if not playlists.has_playlist('youtube', playlist_id, format):
        playlists.download_playlist.delay(
            playlist, 'youtube', format=format, provider=provider)
        return render_template('show_message.html',
                               message='Your playlist is getting downloaded')

    playlist_checksum = playlists.checksum(playlist['tracks'])
    playlist_data = playlists.get_playlist('youtube', playlist_id, format)

    if playlist_data['checksum'] != playlist_checksum:
        playlists.download_playlist.delay(
            playlist, 'youtube', format=format, provider=provider)
        return render_template('show_message.html',
                               message='Your playlist is getting downloaded')

    influxdb.count('youtube.downloaded_playlists')
    return send_file(
        playlist_data['path'],
        as_attachment=True,
        attachment_filename='{}.zip'.format(playlist['name']),
        mimetype='application/zip'
    )


@youtube_service.route('/get_access_token/<code>')
def get_access_token(code):
    influxdb.count('youtube.access_token_requests')

    try:
        code = unquote(code)
        flow = client.OAuth2WebServerFlow(
            YOUTUBE_CLIENT_ID,
            YOUTUBE_CLIENT_SECRET,
            scope='https://www.googleapis.com/auth/youtube.readonly',
            redirect_uri=YOUTUBE_REDIRECT_URI
        )
        credentials = flow.step2_exchange(code)
        return jsonify(
            access_token=credentials.access_token,
            refresh_token=credentials.refresh_token,
            token_expiry=credentials.token_expiry
        )
    except Exception as e:
        current_app.logger.error(
            'Could not authenticate youtube user: {}'.format(e))
        return jsonify(
            error='There was an error while trying to authenticate you.'
                  'Please, try again.'), 503


@youtube_service.route('/refresh_access_token/<refresh_token>')
def refresh_access_token(refresh_token):
    influxdb.count('youtube.refresh_token_requests')

    try:
        refresh_token = unquote(refresh_token)
        credentials = models.refresh_tokens(refresh_token)
        return jsonify(
            access_token=credentials['access_token'],
            expires_in=credentials['expires_in']
        )
    except Exception as e:
        current_app.logger.error(
            'Could not authenticate youtube user: {}'.format(e))
        return jsonify(error='Unable to refresh token.'), 503

