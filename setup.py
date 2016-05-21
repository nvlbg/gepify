from setuptools import setup, find_packages

setup(
    name='gepify',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'Flask>=0.10.1',
        'google-api-python-client>=1.5.0',
        'spotipy>=2.3.8',
        'youtube-dl>=2016.5.10'
    ],
    author='Nikolai Lazarov',
    description='Download your spotify playlists',
    license='MIT',
)
