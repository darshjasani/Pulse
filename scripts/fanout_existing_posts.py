"""
Fan out all existing posts to Redis timelines
This rebuilds the cache from scratch
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import SessionLocal
from services.models import User, Post, Follow
from services.redis_client import redis_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    db = SessionLocal()
    
    try:
        if not redis_client.is_available():
            logger.error("❌ Redis is not available!")
            return
        
        logger.info("🚀 Starting timeline rebuild...")
        
        # Get all posts ordered by creation time (oldest first for proper ordering)
        all_posts = db.query(Post).order_by(Post.created_at.asc()).all()
        logger.info(f"Found {len(all_posts)} total posts")
        
        # Get all users
        all_users = db.query(User).all()
        user_map = {user.id: user for user in all_users}
        
        # Build follower map
        follows = db.query(Follow).all()
        follower_map = {}  # {author_id: [follower_ids]}
        for follow in follows:
            if follow.following_id not in follower_map:
                follower_map[follow.following_id] = []
            follower_map[follow.following_id].append(follow.follower_id)
        
        logger.info(f"Processing {len(all_posts)} posts...")
        
        processed = 0
        for post in all_posts:
            author = user_map.get(post.author_id)
            if not author:
                continue
            
            # Add to author's own timeline
            timestamp = post.created_at.timestamp()
            redis_client.add_to_timeline(author.id, post.id, timestamp)
            
            # Fan out to followers (only if not celebrity)
            if not author.is_celebrity:
                followers = follower_map.get(author.id, [])
                for follower_id in followers:
                    redis_client.add_to_timeline(follower_id, post.id, timestamp)
            
            processed += 1
            if processed % 20 == 0:
                logger.info(f"  Processed {processed}/{len(all_posts)} posts...")
        
        logger.info(f"✅ Successfully fanned out {processed} posts to timelines!")
        logger.info("Refresh your browser to see all posts!")
        
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()

