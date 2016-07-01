import os
import requests
import json
import time
from flask import session

DEEZER_APP_ID = os.environ.get('DEEZER_APP_ID')
DEEZER_SECRET = os.environ.get('DEEZER_SECRET')
DEEZER_REDIRECT_URI = os.environ.get('DEEZER_REDIRECT_URI')


def request_access_token(code):
    auth_request = requests.get(
        'https://connect.deezer.com/oauth/access_token.php' +
        '?output=json'
        '&app_id={}'.format(DEEZER_APP_ID) +
        '&secret={}'.format(DEEZER_SECRET) +
        '&code={}'.format(code))

    if auth_request.status_code == 200:
        response_data = json.loads(auth_request.text)
        access_token = response_data['access_token']
        expires_at = int(time.time()) + int(response_data['expires'])

        session['deezer_access_token'] = access_token
        session['deezer_expires_at'] = expires_at
    else:
        raise RuntimeError('Could not get authentication token')
