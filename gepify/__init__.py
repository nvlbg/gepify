from flask import Flask, render_template
from .services import services
import os


def create_app():
    app = Flask(__name__)

    app.secret_key = os.environ.get('FLASK_SECRET_KEY')
    app.debug = os.environ.get('FLASK_DEBUG') == '1'

    for service in services:
        app.register_blueprint(service)

    from .views import views  # nopep8

    app.register_blueprint(views)

    return app
