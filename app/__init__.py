from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__, static_url_path='/static')
    app.debug = False
    app.config.from_pyfile('config.py')

    db.init_app(app)

    with app.app_context():
        from .routes import init_app_routes
        init_app_routes(app)
        from .spiders import hindawi, sciendo
        db.create_all()

    migrate = Migrate(app, db)

    return app
