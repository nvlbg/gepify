from . import mobile_api_service
from flask import request, send_file, current_app, jsonify
from .view_decorators import access_key_required
from gepify.providers import (
    songs, SUPPORTED_FORMATS, SUPPORTED_PROVIDERS, MIMETYPES
)
from gepify.services.spotify.models import (
    SPOTIFY_AUTHORIZATION_DATA
)
import requests
import json
from gepify.influxdb import count

SPOTIFY_REDIRECT_URI = 'spotify-auth://callback'


@mobile_api_service.route('/get_access_token/<code>')
def get_access_token(code):
    count('mobile_api.access_token_requests')
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': SPOTIFY_REDIRECT_URI
    }

    headers = {
        'Authorization': 'Basic {}'.format(SPOTIFY_AUTHORIZATION_DATA)
    }

    try:
        post_request = requests.post('https://accounts.spotify.com/api/token',
                                     data=payload, headers=headers)

        if post_request.status_code == 200:
            response_data = json.loads(post_request.text)
            access_token = response_data['access_token']
            refresh_token = response_data.get('refresh_token', None)
            expires_in = response_data['expires_in']

            return jsonify(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in)
        else:
            raise RuntimeError('Could not get authentication token')
    except Exception as e:
        current_app.logger.error(
            'Could not authenticate spotify user: {}'.format(e))
        return jsonify(
            error='There was an error while trying to authenticate you.'
                  'Please, try again.'), 503


@mobile_api_service.route('/refresh_access_token/<refresh_token>')
def refresh_access_token(refresh_token):
    count('mobile_api.refresh_access_token_requests')
    payload = {
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }

    headers = {
        'Authorization': 'Basic {}'.format(SPOTIFY_AUTHORIZATION_DATA)
    }

    try:
        post_request = requests.post('https://accounts.spotify.com/api/token',
                                     data=payload, headers=headers)

        if post_request.status_code == 200:
            response_data = json.loads(post_request.text)
            access_token = response_data['access_token']
            expires_in = response_data['expires_in']

            return jsonify(
                access_token=access_token,
                expires_in=expires_in)
        else:
            raise RuntimeError('Could not get authentication token')
    except Exception as e:
        current_app.logger.error(
            'Could not authenticate spotify user: {}'.format(e))
        return jsonify(
            error='There was an error while trying to authenticate you.'
                  'Please, try again.'), 503


@mobile_api_service.route('/download_song/<path:song_name>/<format>')
@access_key_required
def download_song(song_name, format):
    count('mobile_api.download_song_requests')

    if format not in SUPPORTED_FORMATS:
        current_app.logger.warning(
            'User tried to download a song in unsupported format.\n' +
            'Song: {}\n'.format(song_name) +
            'Format: {}\n'.format(format)
        )
        return jsonify(reason='Unsupported format'), 400

    if not songs.has_song_format(song_name, format):
        provider = request.args.get('provider', SUPPORTED_PROVIDERS[0])
        if provider not in SUPPORTED_PROVIDERS:
            current_app.logger.warning(
                'User tried to download a song with unsupported provider.\n' +
                'Song: {}\n'.format(song_name) +
                'Format: {}\n'.format(format) +
                'Provider: {}\n'.format(provider)
            )
            return jsonify(reason='Unsupported provider'), 400

        song = {'name': song_name}
        songs.download_song.delay(song, format=format, provider=provider)
        return jsonify(
            refresh_after=30,
            message='Your song has started downloading.')

    count('mobile_api.downloaded_songs')
    song = songs.get_song(song_name)
    # TODO: temporary workaround with filename (until Flask 0.13 is released)
    return send_file(
        '../' + song['files'][format],
        as_attachment=True,
        # attachment_filename=song['name'],
        mimetype=MIMETYPES[format]
    )
