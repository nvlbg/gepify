"""
    gepify.services
    ~~~~~~~~~~~~~~~

    The services gepify supports are submodules of this module.
    Each service provides a flask Blueprint that implements the needed
    functionality for that service.
"""

from .spotify import spotify_service
from .deezer import deezer_service
from .mobile_api import mobile_api_service

services = [
    spotify_service,
    deezer_service,
    mobile_api_service
]

__all__ = ['services']
