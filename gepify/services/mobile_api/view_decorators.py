from flask import request, jsonify
from functools import wraps


def access_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_key = request.args.get('access_key', None)

        # TODO: check if access_key is a valid key
        if access_key is None:
            return jsonify(reason='Invalid access key'), 403

        return f(*args, **kwargs)
    return decorated_function
