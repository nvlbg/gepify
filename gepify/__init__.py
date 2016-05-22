from flask import Flask, render_template
from .services import services
import os

app = Flask(__name__)

for service in services:
    app.register_blueprint(service)

app.secret_key = os.environ.get('FLASK_SECRET_KEY')
app.debug = os.environ.get('FLASK_DEBUG') == '1'

from . import views  # nopep8
