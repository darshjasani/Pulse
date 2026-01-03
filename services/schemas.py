"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


# ============= User Schemas =============

class UserCreate(BaseModel):
    """Schema for user registration"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    bio: Optional[str]
    is_celebrity: bool
    follower_count: int
    following_count: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserProfile(BaseModel):
    """Schema for public user profile"""
    id: int
    username: str
    full_name: Optional[str]
    bio: Optional[str]
    is_celebrity: bool
    follower_count: int
    following_count: int
    
    model_config = ConfigDict(from_attributes=True)


# ============= Auth Schemas =============

class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for decoded JWT token"""
    user_id: int
    username: str


# ============= Post Schemas =============

class PostCreate(BaseModel):
    """Schema for creating a post"""
    content: str = Field(..., min_length=1, max_length=5000)


class PostResponse(BaseModel):
    """Schema for post response"""
    id: int
    author_id: int
    content: str
    created_at: datetime
    author: UserProfile
    
    model_config = ConfigDict(from_attributes=True)


# ============= Follow Schemas =============

class FollowResponse(BaseModel):
    """Schema for follow response"""
    follower_id: int
    following_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============= Timeline Schemas =============

class TimelineResponse(BaseModel):
    """Schema for timeline response"""
    posts: List[PostResponse]
    cursor: Optional[str] = None
    has_more: bool = False
    source: str  # "cache" or "database"


# ============= System Schemas =============

class HealthCheck(BaseModel):
    """Schema for health check response"""
    status: str
    database: str
    redis: str
    timestamp: datetime


class MetricsResponse(BaseModel):
    """Schema for system metrics"""
    total_users: int
    total_posts: int
    total_follows: int
    celebrity_users: int
    redis_available: bool

