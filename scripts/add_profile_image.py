"""
Migration script to add profile_image column to users table
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from services.database import engine, SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_profile_image_column():
    """Add profile_image column to users table"""
    db = SessionLocal()
    
    try:
        # Check if column already exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='profile_image';
        """))
        
        if result.fetchone():
            logger.info("Column 'profile_image' already exists")
            return
        
        # Add the column
        logger.info("Adding profile_image column to users table...")
        db.execute(text("""
            ALTER TABLE users 
            ADD COLUMN profile_image VARCHAR(255) DEFAULT 'avatar1';
        """))
        
        # Update existing users with default avatar
        db.execute(text("""
            UPDATE users 
            SET profile_image = 'avatar1' 
            WHERE profile_image IS NULL;
        """))
        
        db.commit()
        logger.info("Successfully added profile_image column!")
        
    except Exception as e:
        logger.error(f"Error adding column: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_profile_image_column()

