import gepify
from flask.ext.testing import TestCase
from flask import url_for


class GepifyTestCase(TestCase):
    def create_app(self):
        self.app = gepify.create_app()
        self.app.config['TESTING'] = True
        return self.app

    def setUp(self):
        self.client = self.app.test_client()

    def test_index(self):
        response = self.client.get(url_for('views.index'))
        self.assert200(response)
