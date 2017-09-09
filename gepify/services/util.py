import string
import random

from flask import send_file as flask_send_file
import unicodedata
from werkzeug.urls import url_quote



def get_random_str(length):
    """Return random string with desired length."""

    return ''.join(
        random.choice(string.ascii_lowercase) for i in range(length))

# TODO: temporary workaround until flask 0.13
def send_file(filename, attachment_filename, mimetype, **kwargs):
    response = flask_send_file(filename, mimetype=mimetype)

    try:
        attachment_filename = attachment_filename.encode('latin-1')
    except UnicodeEncodeError:
        filenames = {
            'filename': unicodedata
                .normalize('NFKD', attachment_filename)
                .encode('latin-1', 'ignore'),
            'filename*': "UTF-8''{}".format(
                url_quote(attachment_filename)),
        }
    else:
        filenames = {'filename': attachment_filename}

    response.headers.set(
        'Content-Disposition', 'attachment', **filenames)
    return response

