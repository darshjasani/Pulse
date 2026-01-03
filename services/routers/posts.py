"""
Post routes - create, read posts
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from services.database import get_db
from services.schemas import PostCreate, PostResponse
from services.models import User, Post
from services.auth import get_current_user
from services.sqs_client import sqs_client
from services.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/posts", tags=["Posts"])


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new post
    """
    # Create post
    new_post = Post(
        author_id=current_user.id,
        content=post_data.content
    )
    
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    # Get timestamp
    timestamp = new_post.created_at.timestamp()
    
    # If not a celebrity, try to publish to SQS for fan-out
    # If celebrity, skip fan-out (will be pulled at read time)
    if not current_user.is_celebrity:
        published = sqs_client.publish_post_created(
            post_id=new_post.id,
            author_id=current_user.id,
            is_celebrity=current_user.is_celebrity,
            timestamp=timestamp
        )
        
        if not published:
            # Fallback: add to author's own timeline directly
            logger.warning(f"SQS unavailable, using direct timeline write for post {new_post.id}")
            redis_client.add_to_timeline(current_user.id, new_post.id, timestamp)
    else:
        logger.info(f"Celebrity post created, skipping fan-out: {new_post.id}")
    
    logger.info(f"Post created: {new_post.id} by {current_user.username}")
    
    # Fetch complete post with author info
    db.refresh(new_post)
    return new_post


@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    """
    Get a specific post by ID
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    return post


@router.get("/user/{user_id}", response_model=List[PostResponse])
def get_user_posts(
    user_id: int,
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Get all posts by a specific user
    """
    posts = db.query(Post).filter(
        Post.author_id == user_id
    ).order_by(
        Post.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return posts

