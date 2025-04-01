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

# Configure database connection
# For local development with MySQL
is_local_dev = os.environ.get("LOCAL_DEV", "false").lower() == "true"

if is_local_dev:
    # MySQL Configuration for local development
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")
    MYSQL_USER = os.environ.get("MYSQL_USER", "user1")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "user1")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "market_analyzer")
    
    # Build MySQL connection string
    DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    logger.info(f"Using MySQL database at {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")
else:
    # For Replit environment, try PostgreSQL first, then fall back to SQLite
    if os.environ.get('DATABASE_URL'):
        # Use PostgreSQL if provided by Replit
        DATABASE_URL = os.environ.get('DATABASE_URL')
        logger.info("Using PostgreSQL database for Replit environment")
    else:
        # Fall back to SQLite if PostgreSQL is not available
        DATABASE_URL = "sqlite:///instance/forex_analyzer.db"
        logger.info("Using SQLite database for Replit environment")

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