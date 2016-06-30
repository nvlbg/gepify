from .spotify import spotify_service
from .deezer import deezer_service

services = [
    spotify_service,
    deezer_service
]

__all__ = ['services']
