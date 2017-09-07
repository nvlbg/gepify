from flask import Blueprint, render_template
from gepify.influxdb import client as influxdb

views = Blueprint('views', __name__)


@views.route('/')
def index():
    influxdb.write_points([{
        'measurement': 'index_page_loads',
        'fields': {
            'value': 1
        }
    }])

    return render_template('index.html')
