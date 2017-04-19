"""
    gepify.services.youtube
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module contains functionality for connecting users
    to their youtube accounts, getting information about their playlists,
    as well as the functionality for downloading them.
"""

from flask import Blueprint

youtube_service = Blueprint('youtube', __name__, url_prefix='/youtube')

from . import views  # nopep8

__all__ = ['youtube_service']
