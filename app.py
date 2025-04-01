import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "market_analyzer_secret_key")

# configure the database to use SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///forex_analyzer.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

with app.app_context():
    # Register routes
    from routes import register_routes
    register_routes(app)
    
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401

    db.create_all()