"""
    gepify.services.deezer
    ~~~~~~~~~~~~~~~~~~~~~~

    This module contains functionality for connecting users
    to their deezer accounts, getting information about their playlists,
    as well as the functionality for downloading them.
"""

from flask import Blueprint

deezer_service = Blueprint('deezer', __name__, url_prefix='/deezer')

from . import views  # nopep8

__all__ = ['deezer_service']
