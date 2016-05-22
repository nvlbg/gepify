from flask import Blueprint

spotify_service = Blueprint('spotify', __name__, url_prefix='/spotify')

from . import views  # nopep8

__all__ = ['spotify_service']
