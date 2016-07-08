"""
    gepify.services.spotify
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module contains functionality for connecting users
    to their deezer accounts, getting information about their playlists,
    as well as the functionality for downloading them.
"""

from flask import Blueprint

spotify_service = Blueprint('spotify', __name__, url_prefix='/spotify')

from . import views  # nopep8

__all__ = ['spotify_service']
