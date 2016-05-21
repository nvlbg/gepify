from flask import Flask
from spotify import spotify_provider
import os

app = Flask(__name__)
app.register_blueprint(spotify_provider)

app.secret_key = os.environ.get('FLASK_SECRET_KEY')
app.debug = os.environ.get('FLASK_DEBUG') == '1'


@app.route('/')
def home():
    return 'Hello'

if __name__ == "__main__":
    app.run()
