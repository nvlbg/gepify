from . import mobile_api_service
from flask import request, send_file, current_app, jsonify
from .view_decorators import access_key_required
from gepify.providers import (
    songs, SUPPORTED_FORMATS, SUPPORTED_PROVIDERS, MIMETYPES
)


@mobile_api_service.route('/download_song/<song_name>/<format>')
@access_key_required
def download_song(song_name, format):
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

        songs.download_song.delay(song_name, format=format, provider=provider)
        return jsonify(
            refresh_after=30,
            message='Your song has started downloading.')

    song = songs.get_song(song_name)
    return send_file(
        '../' + song['files'][format],
        as_attachment=True,
        attachment_filename=song['name'],
        mimetype=MIMETYPES[format]
    )
