from flask import Blueprint, render_template
from gepify.influxdb import count

views = Blueprint('views', __name__)


@views.route('/')
def index():
    count('index_page_visits')

    return render_template('index.html')
