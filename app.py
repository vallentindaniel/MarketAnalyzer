"""
Market Analyzer - Application Configuration

This module initializes the Flask application and the database connection.
"""
import os
import logging
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Load environment variables
load_dotenv()

# Set up logger
logger = logging.getLogger(__name__)

# Create base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Create the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "market_analyzer_secret_key")

# Configure database with support for both PostgreSQL and MySQL
# Get database connection URL from the environment variable
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    logger.warning("DATABASE_URL environment variable not set, using fallback")
    DATABASE_URL = "sqlite:///instance/forex_analyzer.db"

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL

# Common configuration
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Import models - must be imported after db is initialized
with app.app_context():
    import models  # noqa: F401
    db.create_all()

# Import and register routes - must be done after models are imported
from app_routes import register_routes
register_routes(app)

logger.info("Application initialized successfully")