"""
Timeline routes - get personalized feed
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from typing import List
from services.database import get_db
from services.schemas import TimelineResponse, PostResponse
from services.models import User, Post, Follow
from services.auth import get_current_user
from services.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/timeline", tags=["Timeline"])


@router.get("", response_model=TimelineResponse)
def get_timeline(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Get personalized timeline for current user
    Hybrid approach: Push (from Redis cache) + Pull (celebrity posts)
    """
    posts = []
    source = "database"
    
    # Try to get from Redis cache first
    cached_post_ids = redis_client.get_timeline(current_user.id, limit, offset)
    
    if cached_post_ids is not None:
        # Cache hit - get posts from database
        if cached_post_ids:
            posts_from_cache = db.query(Post).filter(
                Post.id.in_(cached_post_ids)
            ).all()
            
            # Maintain order from Redis
            post_map = {p.id: p for p in posts_from_cache}
            posts = [post_map[pid] for pid in cached_post_ids if pid in post_map]
            source = "cache"
            logger.info(f"Timeline cache hit for user {current_user.id}")
    
    # Get celebrity posts (always pull these)
    celebrity_ids = db.query(User.id).filter(
        User.id.in_(
            db.query(Follow.following_id).filter(
                Follow.follower_id == current_user.id
            )
        ),
        User.is_celebrity == True
    ).all()
    
    if celebrity_ids:
        celebrity_ids = [cid[0] for cid in celebrity_ids]
        celebrity_posts = db.query(Post).filter(
            Post.author_id.in_(celebrity_ids)
        ).order_by(desc(Post.created_at)).limit(20).all()
        
        posts.extend(celebrity_posts)
        logger.info(f"Added {len(celebrity_posts)} celebrity posts to timeline")
    
    # If cache miss or empty, fall back to database
    if not posts:
        # Get posts from followed users (including current user's own posts)
        following_ids = db.query(Follow.following_id).filter(
            Follow.follower_id == current_user.id
        ).subquery()
        
        posts = db.query(Post).filter(
            or_(
                Post.author_id.in_(following_ids),
                Post.author_id == current_user.id
            )
        ).order_by(desc(Post.created_at)).offset(offset).limit(limit).all()
        
        source = "database"
        logger.info(f"Timeline cache miss for user {current_user.id}, using database")
    
    # Sort by created_at (newest first)
    posts = sorted(posts, key=lambda p: p.created_at, reverse=True)[:limit]
    
    return TimelineResponse(
        posts=posts,
        cursor=None,  # Can implement cursor-based pagination later
        has_more=len(posts) == limit,
        source=source
    )


@router.get("/global", response_model=List[PostResponse])
def get_global_timeline(
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Get global timeline (all posts, newest first)
    """
    posts = db.query(Post).order_by(
        desc(Post.created_at)
    ).offset(offset).limit(limit).all()
    
    return posts

