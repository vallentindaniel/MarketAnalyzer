import os
import sys
import logging
from dotenv import load_dotenv
import pymysql

# Add the parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def init_postgresql():
    """Initialize PostgreSQL database and create tables"""
    from app import app, db
    
    logger.info("Initializing PostgreSQL database...")
    
    # Use the app context to create tables
    with app.app_context():
        # Import models to ensure tables are created
        import models  # noqa: F401
        # Import routes
        from app_routes import register_routes
        
        # Create all tables
        db.create_all()
        
    logger.info("PostgreSQL database initialization complete")

def main():
    """Main function to initialize the database"""
    try:
        init_postgresql()
    except Exception as e:
        logger.error(f"Error initializing PostgreSQL database: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()