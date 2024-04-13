from celery import Celery
from .spiders.hindawi import Hindawi
from .spiders.sciendo import Sciendo
from app import create_app

app = create_app()
celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])


@celery.task
def scrape_hindawi(word):
    with app.app_context():
        hindawi = Hindawi(word)
        hindawi.scrape_links()


@celery.task
def scrape_sciendo(word):
    with app.app_context():
        sciendo = Sciendo(word)
        sciendo.scrape_links()
