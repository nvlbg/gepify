from flask import session, redirect, url_for, render_template, current_app
import time
from functools import wraps


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = session.get('deezer_access_token', None)
        expires_at = session.get('deezer_expires_at', None)
        now = int(time.time())

        if access_token is None or expires_at is None or now >= expires_at:
            session.pop('deezer_access_token', None)
            session.pop('deezer_expires_at', None)
            session.pop('deezer_user_id', None)
            return redirect(url_for('deezer.login'))

        return f(*args, **kwargs)
    return decorated_function


def logout_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = session.get('deezer_access_token', None)
        expires_at = session.get('deezer_expires_at', None)
        now = int(time.time())

        if (access_token is not None and
                expires_at is not None and
                expires_at > now):
            return render_template(
                'show_message.html',
                message='You need to be logged out to see this page'), 403

        return f(*args, **kwargs)
    return decorated_function
