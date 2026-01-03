"""
System routes - health check, metrics
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from services.database import get_db
from services.schemas import HealthCheck, MetricsResponse
from services.models import User, Post, Follow
from services.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["System"])


@router.get("/health", response_model=HealthCheck)
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint
    """
    # Check database
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Check Redis
    redis_status = "healthy" if redis_client.is_available() else "unavailable"
    
    overall_status = "healthy" if db_status == "healthy" else "degraded"
    
    return HealthCheck(
        status=overall_status,
        database=db_status,
        redis=redis_status,
        timestamp=datetime.utcnow()
    )


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(db: Session = Depends(get_db)):
    """
    Get system metrics
    """
    total_users = db.query(func.count(User.id)).scalar()
    total_posts = db.query(func.count(Post.id)).scalar()
    total_follows = db.query(func.count(Follow.id)).scalar()
    celebrity_users = db.query(func.count(User.id)).filter(
        User.is_celebrity == True
    ).scalar()
    
    return MetricsResponse(
        total_users=total_users or 0,
        total_posts=total_posts or 0,
        total_follows=total_follows or 0,
        celebrity_users=celebrity_users or 0,
        redis_available=redis_client.is_available()
    )

