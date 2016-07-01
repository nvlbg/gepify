from . import deezer_service
from flask import (
    session, render_template, redirect, request,
    url_for, send_file, current_app
)
from .view_decorators import login_required, logout_required
from . import models
from .models import DEEZER_APP_ID, DEEZER_REDIRECT_URI
from ..util import get_random_str
import urllib


@deezer_service.route('/')
@login_required
def index():
    return 'deezer'


@deezer_service.route('/login')
@logout_required
def login():
    state = get_random_str(16)
    session['deezer_auth_state'] = state
    query_parameters = {
        'app_id': DEEZER_APP_ID,
        'redirect_uri': DEEZER_REDIRECT_URI,
        'perms': 'basic_access',
        'state': state,
    }

    query_parameters = '&'.join(['{}={}'.format(key, urllib.parse.quote(val))
                                 for key, val in query_parameters.items()])
    auth_url = 'https://connect.deezer.com/oauth/auth.php?' + query_parameters
    return redirect(auth_url)


@deezer_service.route('/callback')
def callback():
    error = request.args.get('error_reason', None)
    code = request.args.get('code', None)
    state = request.args.get('state', None)
    stored_state = session.get('deezer_auth_state', None)

    if error is not None or state is None or state != stored_state:
        current_app.logger.error('Could not authenticate spotify user:\n' +
                                 'error: {}\n'.format(error) +
                                 'state: {}\n'.format(state) +
                                 'stored_state: {}\n'.format(stored_state))
        return render_template(
            'show_message.html',
            message='There was an error while trying to authenticate you.'
                    'Please, try again.'), 503
    else:
        session.pop('deezer_auth_state', None)
        try:
            models.request_access_token(code)
            return redirect(url_for('deezer.index'))
        except Exception as e:
            current_app.logger.error(
                'Could not authenticate deezer user: {}'.format(e))
            return render_template(
                'show_message.html',
                message='There was an error while trying to authenticate you.'
                        'Please, try again.'), 503


@deezer_service.route('/logout')
def logout():
    session.pop('deezer_access_token', None)
    session.pop('deezer_expires_at', None)

    return redirect(url_for('views.index'))
