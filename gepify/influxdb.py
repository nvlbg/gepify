"""InfluxDB configuration.

This module serves as a configuration for a InfluxDB client
used for collecting various statistics and metrics.
"""

from influxdb import InfluxDBClient
import os


class Client:
    def __init__(self):
        host = os.environ.get('INFLUXDB_HOST')
        port = os.environ.get('INFLUXDB_PORT', 8086)
        username = os.environ.get('INFLUXDB_USER', 'root')
        password = os.environ.get('INFLUXDB_PASSWORD', 'root')
        database = os.environ.get('INFLUXDB_DATABASE', 'gepify')

        self.client = None
        if host:
            self.client = InfluxDBClient(
                    host, port, username, password, database)
            self.client.create_database(database)

    def count(self, metric):
        if self.client:
            self.client.write_points([{
                'measurement': metric,
                'fields': {
                    'value': 1
                }
            }])

influxdb = Client()

