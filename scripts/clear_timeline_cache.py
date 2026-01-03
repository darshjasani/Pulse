"""
Clear Redis timeline cache to force database fallback
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.redis_client import redis_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        if not redis_client.is_available():
            logger.error("❌ Redis is not available!")
            return
        
        # Clear all timeline keys
        client = redis_client.client
        
        # Get all timeline keys
        keys = client.keys("timeline:*")
        
        if keys:
            deleted = client.delete(*keys)
            logger.info(f"✅ Cleared {deleted} timeline cache entries")
        else:
            logger.info("No timeline cache entries found")
        
        logger.info("Timeline cache cleared! Refresh your browser to see all posts from database.")
        
    except Exception as e:
        logger.error(f"❌ Failed: {e}")

if __name__ == "__main__":
    main()

