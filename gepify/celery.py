from celery import Celery
import os

celery_app = Celery('gepify', backend=os.environ.get('CELERY_BACKEND'),
                    broker=os.environ.get('CELERY_BROKER_URL'))

if __name__ == '__main__':
    celery_app.start()
