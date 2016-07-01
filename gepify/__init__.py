from flask import Flask, render_template
from .services import services
import os
import logging


def create_app():
    app = Flask(__name__)

    app.secret_key = os.environ.get('FLASK_SECRET_KEY')
    app.debug = os.environ.get('FLASK_DEBUG') == '1'

    if not app.debug:
        file_handler = logging.FileHandler('server.log')
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        app.logger.addHandler(file_handler)

    for service in services:
        app.register_blueprint(service)

    from .views import views  # nopep8

    app.register_blueprint(views)

    return app
