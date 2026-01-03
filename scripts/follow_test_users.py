"""
Make alice and bob follow all test users
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import SessionLocal
from services.models import User, Follow
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    db = SessionLocal()
    
    try:
        # Get alice and bob
        alice = db.query(User).filter(User.username == "alice").first()
        bob = db.query(User).filter(User.username == "bob").first()
        
        if not alice or not bob:
            logger.error("Alice or Bob not found!")
            return
        
        # Get all test users
        test_users = db.query(User).filter(User.username.like("testuser%")).all()
        
        logger.info(f"Found {len(test_users)} test users")
        
        # Make alice and bob follow all test users
        for user in [alice, bob]:
            for test_user in test_users:
                # Check if already following
                existing = db.query(Follow).filter(
                    Follow.follower_id == user.id,
                    Follow.following_id == test_user.id
                ).first()
                
                if not existing:
                    follow = Follow(
                        follower_id=user.id,
                        following_id=test_user.id
                    )
                    db.add(follow)
                    user.following_count += 1
                    test_user.follower_count += 1
        
        db.commit()
        logger.info("✅ Alice and Bob now follow all test users!")
        logger.info("Login and reload the timeline to see 100+ posts")
        
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()

