"""
    gepify.services
    ~~~~~~~~~~~~~~~

    The services gepify supports are submodules of this module.
    Each service provides a flask Blueprint that implements the needed
    functionality for that service.
"""

from .spotify import spotify_service
from .deezer import deezer_service
from .youtube import youtube_service

services = [
    spotify_service,
    deezer_service,
    youtube_service
]

__all__ = ['services']
