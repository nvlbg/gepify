from flask import Flask, render_template, redirect, session, request
import random
import string
import os
import urllib
import base64
import requests
import json
import spotipy
import youtube_dl


SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI')

ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': 'static/mp3/%(id)s.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

app = Flask(__name__)

app.secret_key = os.environ.get('FLASK_SECRET_KEY')
app.debug = os.environ.get('FLASK_DEBUG') == '1'


def get_random_str(length):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


@app.route('/')
def home():
    return 'Hello'


@app.route('/login/spotify')
def spotify_login():
    state = get_random_str(16)
    session['spotify_auth_state'] = state
    query_parameters = {
        'response_type': 'code',
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'scope': 'user-library-read',
        'state': state,
        'client_id': SPOTIFY_CLIENT_ID
    }

    query_parameters = '&'.join(['{}={}'.format(key, urllib.parse.quote(val)) for key, val in query_parameters.items()])
    auth_url = 'https://accounts.spotify.com/authorize/?' + query_parameters
    return redirect(auth_url)


@app.route('/callback/spotify')
def spotify_callback():
    error = request.args.get('error', None)
    code = request.args.get('code', None)
    state = request.args.get('state', None)
    stored_state = session.get('spotify_auth_state', None)

    if error != None:
        # TODO
        pass
    elif state == None or state != stored_state:
        # TODO
        # return redirect()
        return 'Error: state mismatch'
    else:
        del session['spotify_auth_state']
        code_payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': SPOTIFY_REDIRECT_URI
        }
        base64encoded = base64.b64encode(bytes(
            SPOTIFY_CLIENT_ID + ':' + SPOTIFY_CLIENT_SECRET, 'utf-8')).decode('utf-8')
        headers = {
            'Authorization': 'Basic {}'.format(base64encoded)
        }
        post_request = requests.post('https://accounts.spotify.com/api/token', data=code_payload, headers=headers)

        if post_request.status_code == 200:
            response_data = json.loads(post_request.text)
            access_token = response_data['access_token']
            refresh_token = response_data['refresh_token']

            session['spotify_access_token'] = access_token
            session['spotify_refresh_token'] = refresh_token

            sp = spotipy.Spotify(auth=access_token)
            results = sp.current_user_saved_tracks()
            response = []
            for item in results['items']:
                track = item['track']
                response.append(track['name'] + ' - ' + track['artists'][0]['name'])

            return '\n'.join(response)
        else:
            # TODO
            return 'Error: did not get token'


@app.route("/download/<video_id>")
def download(video_id):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        print(ydl.download(['http://www.youtube.com/watch?v=' + video_id]))

    # return render_template('play.html', file=video_id)
    return redirect('/static/mp3/{}.mp3'.format(video_id))


if __name__ == "__main__":
    app.run()
