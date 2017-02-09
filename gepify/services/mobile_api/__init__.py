"""
    gepify.services.mobile_api
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module contains functionality for downloading songs and playlists
    for users of the mobile app.
"""

from flask import Blueprint

mobile_api_service = Blueprint('mobile_api', __name__, url_prefix='/api')

from . import views  # nopep8

__all__ = ['mobile_api_service']
