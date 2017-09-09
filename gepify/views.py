from flask import Blueprint, render_template
from gepify.influxdb import influxdb

views = Blueprint('views', __name__)


@views.route('/')
def index():
    influxdb.count('index_page_visits')

    return render_template('index.html')
