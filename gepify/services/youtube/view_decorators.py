from flask import session, redirect, url_for, render_template, g
from functools import wraps
import httplib2
from oauth2client import client
from apiclient.discovery import build


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        credentials = session.get('credentials', None)

        if credentials is None:
            return redirect(url_for('youtube.login'))

        credentials = client.OAuth2Credentials.from_json(credentials)

        if credentials.access_token_expired:
            return redirect(url_for('youtube.login'))

        http_auth = credentials.authorize(httplib2.Http())
        g.youtube = build('youtube', 'v3', http=http_auth)
        return f(*args, **kwargs)
    return decorated_function


def logout_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        credentials = session.get('credentials', None)

        if (credentials is not None):
            credentials = client.OAuth2Credentials.from_json(credentials)

            if not credentials.access_token_expired:
                return render_template(
                    'show_message.html',
                    message='You need to be logged out to see this page'), 403

        return f(*args, **kwargs)
    return decorated_function
