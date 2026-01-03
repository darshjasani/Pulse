"""
User routes - profile, follow/unfollow
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from services.database import get_db
from services.schemas import UserResponse, UserProfile, FollowResponse
from services.models import User, Follow
from services.auth import get_current_user
from services.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile
    """
    return current_user


@router.get("/{username}", response_model=UserProfile)
def get_user_profile(username: str, db: Session = Depends(get_db)):
    """
    Get user profile by username
    """
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.post("/follow/{user_id}", response_model=FollowResponse)
def follow_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Follow a user
    """
    # Cannot follow yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself"
        )
    
    # Check if target user exists
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already following
    existing_follow = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id == user_id
    ).first()
    
    if existing_follow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already following this user"
        )
    
    # Create follow relationship
    new_follow = Follow(
        follower_id=current_user.id,
        following_id=user_id
    )
    db.add(new_follow)
    
    # Update counts
    target_user.follower_count = db.query(func.count(Follow.id)).filter(
        Follow.following_id == user_id
    ).scalar() + 1
    
    current_user.following_count = db.query(func.count(Follow.id)).filter(
        Follow.follower_id == current_user.id
    ).scalar() + 1
    
    # Check and update celebrity status
    if target_user.follower_count >= settings.celebrity_follower_threshold:
        target_user.is_celebrity = True
        logger.info(f"User {target_user.username} is now a celebrity!")
    
    db.commit()
    db.refresh(new_follow)
    
    logger.info(f"{current_user.username} followed {target_user.username}")
    return new_follow


@router.delete("/unfollow/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Unfollow a user
    """
    follow = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id == user_id
    ).first()
    
    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not following this user"
        )
    
    # Delete follow relationship
    db.delete(follow)
    
    # Update counts
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user:
        target_user.follower_count = max(0, target_user.follower_count - 1)
        
        # Check celebrity status
        if target_user.follower_count < settings.celebrity_follower_threshold:
            target_user.is_celebrity = False
    
    current_user.following_count = max(0, current_user.following_count - 1)
    
    db.commit()
    
    logger.info(f"{current_user.username} unfollowed user {user_id}")


@router.get("/{user_id}/followers", response_model=List[UserProfile])
def get_followers(
    user_id: int,
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Get list of followers for a user
    """
    followers = db.query(User).join(
        Follow, Follow.follower_id == User.id
    ).filter(
        Follow.following_id == user_id
    ).offset(offset).limit(limit).all()
    
    return followers


@router.get("/{user_id}/following", response_model=List[UserProfile])
def get_following(
    user_id: int,
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Get list of users that a user is following
    """
    following = db.query(User).join(
        Follow, Follow.following_id == User.id
    ).filter(
        Follow.follower_id == user_id
    ).offset(offset).limit(limit).all()
    
    return following

