from setuptools import setup, find_packages

setup(
    name='gepify',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'Flask>=0.12.3',
        'Flask-Testing>=0.4.2',
        'celery>=4.3',
        'amqp>=1.4.9',
        'redis>=2.10.5',
        'coverage>=4.1',
        'Werkzeug>=0.11.9',
        'requests>=2.20.0',
        'urllib3>=1.23',  # pin version, not depending on it
        'spotipy>=2.3.8',
        'soundcloud>=0.5.0',
        'google-api-python-client>=1.5.0',
        'youtube-dl>=2019.04.07',
        'gunicorn>=19.6.0',
        'influxdb>=4.1.1'
    ],
    tests_require=[
        'coverage>=4.1'
    ],
    test_suite='tests',
    author='Nikolai Lazarov',
    description='Download your spotify playlists',
    license='MIT',
)
