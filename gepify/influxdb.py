"""InfluxDB configuration.

This module serves as a configuration for a InfluxDB client
used for collecting various statistics and metrics.
"""

from influxdb import InfluxDBClient
import os

host = os.environ.get('INFLUXDB_HOST', 'localhost')
port = os.environ.get('INFLUXDB_PORT', 8086)
username = os.environ.get('INFLUXDB_USER', 'root')
password = os.environ.get('INFLUXDB_PASSWORD', 'root')
database = os.environ.get('INFLUXDB_DATABASE', 'gepify')

client = InfluxDBClient(host, port, username, password, database)
client.create_database(database)

