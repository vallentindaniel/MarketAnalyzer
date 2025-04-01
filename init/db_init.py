"""
Database initialization module

This module initializes the database connection and creates tables.
It supports both PostgreSQL and MySQL databases.
"""
import os
import sys
from pathlib import Path
import time
import sqlalchemy
import sqlalchemy.exc
from dotenv import load_dotenv

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Load environment variables from .env file
load_dotenv()

def get_database_url():
    """
    Get the database URL from environment variables
    
    Supports PostgreSQL (default) and MySQL configurations
    """
    db_type = os.environ.get("DB_TYPE", "postgresql")
    
    if db_type.lower() == "postgresql":
        # Use PostgreSQL
        return os.environ.get("DATABASE_URL")
    elif db_type.lower() == "mysql":
        # Use MySQL
        host = os.environ.get("MYSQL_HOST", "localhost")
        port = os.environ.get("MYSQL_PORT", "3306")
        user = os.environ.get("MYSQL_USER")
        password = os.environ.get("MYSQL_PASSWORD")
        database = os.environ.get("MYSQL_DATABASE")
        
        if not all([user, password, database]):
            raise ValueError("MYSQL_USER, MYSQL_PASSWORD, and MYSQL_DATABASE environment variables are required")
        
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    else:
        raise ValueError(f"Unsupported DB_TYPE: {db_type}. Must be 'postgresql' or 'mysql'")

def init_database():
    """Initialize database connection and create tables"""
    # Get the app and db instances
    from app import app, db
    
    print("Initializing database...")
    
    # Database creation logic
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Tables created successfully.")
        
        # Verify tables exist
        inspector = sqlalchemy.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Database tables: {', '.join(tables)}")
        
        # Check database schema version or state
        if 'candles' in tables and 'price_action_patterns' in tables and 'fair_value_gaps' in tables and 'trade_opportunities' in tables:
            print("All required tables are present.")
        else:
            print("Warning: Some required tables are missing.")
            print("Missing tables:", ', '.join(
                [table for table in ['candles', 'price_action_patterns', 'fair_value_gaps', 'trade_opportunities'] 
                 if table not in tables]
            ))

def main():
    """Main function to initialize the database"""
    # Retry initialization with exponential backoff
    max_retries = 5
    retry_count = 0
    backoff_factor = 1.5
    wait_time = 1
    
    while retry_count < max_retries:
        try:
            init_database()
            print("Database initialization successful.")
            return
        except sqlalchemy.exc.OperationalError as e:
            print(f"Database connection failed (attempt {retry_count + 1}/{max_retries}): {e}")
            if retry_count < max_retries - 1:
                print(f"Retrying in {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                wait_time *= backoff_factor
            retry_count += 1
        except Exception as e:
            print(f"Error initializing database: {e}")
            break
    
    print("Database initialization failed after multiple attempts.")

if __name__ == "__main__":
    main()