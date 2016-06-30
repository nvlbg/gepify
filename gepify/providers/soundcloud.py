import soundcloud
import os
from .youtube import downloaders
from . import SUPPORTED_FORMATS

SOUNDCLOUD_CLIENT_ID = os.environ.get('SOUNDCLOUD_CLIENT_ID')

def get_song_id(track):
    client = soundcloud.Client(client_id=SOUNDCLOUD_CLIENT_ID)
    tracks = client.get('/tracks', q=track)
    
    if len(tracks) > 0:
        id = tracks[0].obj['id']
        download_id = '{}/{}'.format(
            tracks[0].obj['user']['permalink'], tracks[0].obj['permalink'])
        return (id, download_id)


    raise Exception('Could not find song')


def download_song(id, format):
    if format not in SUPPORTED_FORMATS:
        raise ValueError('Format not supported: {}'.format(format))

    with downloaders[format] as ydl:
        return ydl.download(['http://soundcloud.com/' + id])
