from flask import Flask
from flask_migrate import Migrate
from db import db
from celery import Celery

def create_app():
    app = Flask(__name__, template_folder='templates')
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://webscrape:postgres@localhost:5432/webscrape"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['CELERY_BROKER_URL'] = 'db+postgresql://webscrape:postgres@localhost:5432/webscrape'

    db.init_app(app)

    with app.app_context():
        db.create_all()

    from routes import register_routes
    register_routes(app)

    migrate = Migrate(app, db)

    return app
