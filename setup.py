from setuptools import setup, find_packages

setup(
    name='gepify',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'Flask>=0.10.1',
        'Flask-Testing>=0.4.2',
        'celery>=3.1.23',
        'amqp>=1.4.9',
        'redis>=2.10.5',
        'coverage>=4.1',
        'Werkzeug>=0.11.9',
        'requests>=2.10.0',
        'spotipy>=2.3.8',
        'google-api-python-client>=1.5.0',
        'youtube-dl>=2016.6.27',
        'gunicorn>=19.6.0'
    ],
    tests_require=[
        'coverage>=4.1'
    ],
    test_suite='tests',
    author='Nikolai Lazarov',
    description='Download your spotify playlists',
    license='MIT',
)
