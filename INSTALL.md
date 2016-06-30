Installing Gepify
=================

These instructions will lead you through the process of installing gepify and its dependencies.
It is aimed at linux/unix users and windows users will probable have some minor differences in the process.

Requirements
------------

Gepify requires Python 3, pip, Redis and Rabbit-MQ.

Python 3.5.x is recommended, as it is the version I use for developping.
You can use Redis or some other alternative to Rabbit-MQ (see the
[Setting up the enviroment variables](#setting-up-the-enviroment-variables) section below).
After you have everything installed, make sure you have started the Redis and Rabbit-MQ services started.
Here is how to do it in Ubuntu:

    sudo service start redis-server
    sudo service start rabbitmq-server

Installing dependencies
-----------------------

(Optional) Before installing the dependencies, it is strongly recommended to create a [virtual enviroment](http://docs.python-guide.org/en/latest/dev/virtualenvs/). Here is how to do it with virtualenvwrapper:

    mkvirtualenv gepify

Now you can install the dependencies:

    pip install -r requirements.txt

Setting up the enviroment variables
-----------------------------------

In order for gepify to run you have to set up some enviroment variables.

If you are using [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/)
you can edit your enviroment's `bin/postactivate` and `bin/predeactivate` to respectively create and delete
these variables so you don't pollute your global space.

Here are the configuration options:

 - YOUTUBE_DEVELOPER_KEY: your youtube developper key. You can see instructions how to get one from 
   [here](https://developers.google.com/youtube/v3/getting-started#intro). It is needed for searching
   youtube for the song videos.
 - SPOTIFY_CLIENT_ID: your spotify client id. You can get one from [spotify's developpers page](https://developer.spotify.com/).
   This option, along with the next two, are used to allow users to log in to their spotify profiles
   and give access to gepify to their playlists. If you are interested in the what these options mean
   you can see the [OAuth2 specification](http://oauth.net/2/).
 - SPOTIFY_CLIENT_SECRET: the spotify client secret.
 - SPOTIFY_REDIRECT_URI: the redirect uri, as described in the OAuth2 specification.
 - FLASK_SECRET_KEY: some random secret string. It is needed for the sessions.
   [Here](http://flask.pocoo.org/docs/0.11/quickstart/#sessions) you can find some instructions how to
   generate good keys.
 - FLASK_DEBUG *(optional)*: set it to 1 to see debug messages and more helpful stuff for development.
 - CELERY_BACKEND: [this is where celery keeps the results](http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html#keeping-results).
   If you use Redis on you machine with default options you can set it to `redis://localhost`.
 - CELERY_BROKER_URL: [the broker used by celery](http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html#choosing-a-broker).
   If you use Rabbit-MQ on you machine with default options you can set it to `amqp://localhost`.

Running the server
------------------

Before running the web server you need to run the [celery](http://www.celeryproject.org/) task runner.
You should have it installed after installing the dependencies. Open a new terminal (don't forget to `workon`
your virtualenv if you created one):

    celery -A gepify.celery worker --loglevel=info

You also need to run celery beat to run periodic tasks, so open another terminal and run:

    celery -A gepify beat

Now you can start the webserver in a new terminal:

    python3 runserver.py

In the terminal you will see something like:

    $ python3 runserver.py 
     * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
     * Restarting with stat
     * Debugger is active!
     * Debugger pin code: 166-095-336

Now you can navigate your browser to `http://127.0.0.1:5000/` and see the webpage.

Running the tests
-----------------

To run the tests make sure you completed the [Installing dependencies](#installing-dependencies) and
[Setting up the enviroment variables](#setting-up-the-enviroment-variables) steps above. Then run:

    python3 -m unittest discover

Alternatively, you can run:

    python3 setup.py test

To create the test coverage, first make sure you have [coverage](https://pypi.python.org/pypi/coverage)
installed. Then you can run:

    coverage run -m unittest discover
    coverage html

Now you should see a new folder in the project named `htmlcov/`. You can open `htmlcov/index.html` to
check out the generated test coverage.
