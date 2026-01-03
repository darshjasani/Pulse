"""
Seed database with demo data for testing and demos
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import SessionLocal
from services.models import User, Post, Follow
from services.auth import hash_password
from services.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_demo_users(db):
    """Create demo users"""
    users = [
        {
            "username": "alice",
            "email": "alice@pulse.dev",
            "password": "password123",
            "full_name": "Alice Johnson",
            "bio": "Tech enthusiast 🚀",
        },
        {
            "username": "bob",
            "email": "bob@pulse.dev",
            "password": "password123",
            "full_name": "Bob Smith",
            "bio": "Love building things 💻",
        },
        {
            "username": "celebrity_user",
            "email": "celebrity@pulse.dev",
            "password": "password123",
            "full_name": "Celebrity User",
            "bio": "Famous person with many followers ⭐",
            "is_celebrity": True,
            "follower_count": settings.celebrity_follower_threshold,
        },
        {
            "username": "charlie",
            "email": "charlie@pulse.dev",
            "password": "password123",
            "full_name": "Charlie Brown",
            "bio": "Just here to connect 🌍",
        },
        {
            "username": "diana",
            "email": "diana@pulse.dev",
            "password": "password123",
            "full_name": "Diana Prince",
            "bio": "Designer & Creator 🎨",
        },
    ]
    
    created_users = []
    for user_data in users:
        is_celeb = user_data.pop("is_celebrity", False)
        follower_count = user_data.pop("follower_count", 0)
        password = user_data.pop("password")
        
        user = User(
            **user_data,
            hashed_password=hash_password(password),
            is_celebrity=is_celeb,
            follower_count=follower_count
        )
        db.add(user)
        created_users.append(user)
    
    db.commit()
    logger.info(f"✅ Created {len(created_users)} demo users")
    return created_users


def create_demo_follows(db, users):
    """Create demo follow relationships"""
    # Alice follows everyone
    # Bob follows Alice and celebrity
    # Charlie follows Alice and Bob
    # Diana follows celebrity
    
    follows = [
        (users[0], users[1]),  # Alice -> Bob
        (users[0], users[2]),  # Alice -> Celebrity
        (users[0], users[3]),  # Alice -> Charlie
        (users[0], users[4]),  # Alice -> Diana
        (users[1], users[0]),  # Bob -> Alice
        (users[1], users[2]),  # Bob -> Celebrity
        (users[3], users[0]),  # Charlie -> Alice
        (users[3], users[1]),  # Charlie -> Bob
        (users[4], users[2]),  # Diana -> Celebrity
    ]
    
    for follower, following in follows:
        follow = Follow(follower_id=follower.id, following_id=following.id)
        db.add(follow)
        
        # Update counts
        following.follower_count += 1
        follower.following_count += 1
    
    db.commit()
    logger.info(f"✅ Created {len(follows)} follow relationships")


def create_demo_posts(db, users):
    """Create demo posts"""
    posts_data = [
        (users[0], "Just joined Pulse! Excited to be here 🎉"),
        (users[0], "Working on a new project today. System design is fascinating!"),
        (users[1], "Hello world! First post on Pulse 👋"),
        (users[1], "Learning about distributed systems and fan-out patterns"),
        (users[2], "Celebrity here! This should not fan-out to all my followers ⭐"),
        (users[2], "Another celebrity post. Read-time pull optimization in action!"),
        (users[3], "Great to connect with everyone here!"),
        (users[4], "Designing the future, one pixel at a time 🎨"),
        (users[0], "The hybrid push-pull model is really elegant when you think about it"),
        (users[1], "Redis caching makes everything so fast! ⚡"),
    ]
    
    for user, content in posts_data:
        post = Post(author_id=user.id, content=content)
        db.add(post)
    
    db.commit()
    logger.info(f"✅ Created {len(posts_data)} demo posts")


def main():
    """Seed demo data"""
    logger.info("Starting demo data seeding...")
    
    db = SessionLocal()
    
    try:
        # Check if data already exists
        user_count = db.query(User).count()
        if user_count > 0:
            logger.warning(f"⚠️  Database already has {user_count} users. Skipping seed.")
            response = input("Delete existing data and reseed? (yes/no): ")
            if response.lower() != "yes":
                logger.info("Seeding cancelled")
                return
            
            # Clear existing data
            db.query(Follow).delete()
            db.query(Post).delete()
            db.query(User).delete()
            db.commit()
            logger.info("Cleared existing data")
        
        # Create demo data
        users = create_demo_users(db)
        create_demo_follows(db, users)
        create_demo_posts(db, users)
        
        logger.info("✅ Demo data seeding complete!")
        logger.info("\nDemo credentials:")
        logger.info("  Username: alice, Password: password123")
        logger.info("  Username: bob, Password: password123")
        logger.info("  Username: celebrity_user, Password: password123")
        
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

