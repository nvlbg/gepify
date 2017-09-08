import gepify
from flask.ext.testing import TestCase
from flask import url_for
from unittest import mock


class GepifyTestCase(TestCase):
    def create_app(self):
        self.app = gepify.create_app()
        self.app.config['TESTING'] = True
        self.app.config['DEBUG'] = True
        self.app.config['PROPAGATE_EXCEPTIONS'] = False
        self.app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
        return self.app

    def setUp(self):
        self.client = self.app.test_client()


@mock.patch('influxdb.count')
class GepifyIndexTestCase(GepifyTestCase):
    def test_index(self):
        response = self.client.get(url_for('views.index'))
        self.assert200(response)
