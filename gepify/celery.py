from celery import Celery
from datetime import timedelta
import os

celery_app = Celery('gepify')

celery_app.conf.update(
    BROKER_URL=os.environ.get('CELERY_BROKER_URL'),
    CELERY_RESULT_BACKEND=os.environ.get('CELERY_BACKEND'),
    CELERY_TASK_SERIALIZER='json',
    CELERY_ACCEPT_CONTENT=['json'],
    CELERY_RESULT_SERIALIZER='json',
    CELERYBEAT_SCHEDULE={
        'clean-playlists': {
            'task': 'gepify.providers.playlists.clean_playlists',
            'schedule': timedelta(hours=1)
        }
    }
)
