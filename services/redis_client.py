"""
Redis client for caching and timeline management
"""
import redis
from typing import Optional, List
from services.config import settings
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper with error handling"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._connect()
    
    def _connect(self):
        """Establish Redis connection"""
        try:
            self.client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            self.client.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except:
            return False
    
    def add_to_timeline(self, user_id: int, post_id: int, timestamp: float) -> bool:
        """
        Add post to user's timeline (sorted set by timestamp)
        Returns True if successful, False if Redis unavailable
        """
        if not self.is_available():
            return False
        
        try:
            key = f"timeline:{user_id}"
            self.client.zadd(key, {str(post_id): timestamp})
            # Keep only latest 1000 posts
            self.client.zremrangebyrank(key, 0, -1001)
            return True
        except Exception as e:
            logger.error(f"Failed to add to timeline: {e}")
            return False
    
    def get_timeline(
        self, 
        user_id: int, 
        limit: int = 50, 
        offset: int = 0
    ) -> Optional[List[int]]:
        """
        Get post IDs from user's timeline (newest first)
        Returns None if Redis unavailable OR timeline key doesn't exist (cache miss)
        Returns empty list [] if timeline exists but has no posts
        """
        if not self.is_available():
            return None
        
        try:
            key = f"timeline:{user_id}"
            
            # Check if key exists - if not, it's a cache miss
            if not self.client.exists(key):
                return None
            
            # Get posts in reverse order (newest first)
            post_ids = self.client.zrevrange(
                key, 
                offset, 
                offset + limit - 1
            )
            return [int(pid) for pid in post_ids]
        except Exception as e:
            logger.error(f"Failed to get timeline: {e}")
            return None
    
    def clear_timeline(self, user_id: int) -> bool:
        """Clear user's timeline"""
        if not self.is_available():
            return False
        
        try:
            key = f"timeline:{user_id}"
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to clear timeline: {e}")
            return False
    
    def get_cache(self, key: str) -> Optional[str]:
        """Get cached value"""
        if not self.is_available():
            return None
        
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Failed to get cache: {e}")
            return None
    
    def set_cache(self, key: str, value: str, expiration: int = 300) -> bool:
        """Set cached value with expiration (default 5 minutes)"""
        if not self.is_available():
            return False
        
        try:
            self.client.setex(key, expiration, value)
            return True
        except Exception as e:
            logger.error(f"Failed to set cache: {e}")
            return False


# Global Redis client instance
redis_client = RedisClient()

