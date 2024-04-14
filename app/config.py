SQLALCHEMY_DATABASE_URI = "postgresql://webscrape:postgres@localhost:5432/webscrape"
SQLALCHEMY_TRACK_MODIFICATIONS = False
TEMPLATES_AUTO_RELOAD = True
CELERY_BROKER_URL = "postgresql://webscrape:postgres@localhost:5432/webscrape"
CELERY_RESULT_BACKEND = "db+postgresql://webscrape:postgres@localhost:5432/webscrape"
