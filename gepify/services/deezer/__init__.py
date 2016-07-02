from flask import Blueprint

deezer_service = Blueprint('deezer', __name__, url_prefix='/deezer')

from . import views  # nopep8

__all__ = ['deezer_service']
