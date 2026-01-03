"""
Create 100 sample posts for testing infinite scroll
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import SessionLocal
from services.models import User, Post
from services.auth import hash_password
import logging
from datetime import datetime, timedelta
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample post content
POST_TEMPLATES = [
    "Just finished working on a new project! 🚀",
    "Beautiful day today! ☀️",
    "Learning about distributed systems is fascinating!",
    "Coffee and code, perfect combination ☕💻",
    "Anyone else excited about the new tech releases?",
    "Working on improving my coding skills every day",
    "System design is so interesting once you understand it",
    "Redis makes everything so fast! ⚡",
    "PostgreSQL is such a reliable database",
    "Deploying to production today, wish me luck!",
    "Just solved a really tricky bug 🐛",
    "Reading about microservices architecture",
    "GraphQL or REST? What's your preference?",
    "Docker makes deployment so much easier",
    "Kubernetes is powerful but complex",
    "Love working with Python and FastAPI",
    "JavaScript is everywhere these days",
    "TypeScript makes JavaScript better",
    "React hooks changed everything",
    "Vue.js is so elegant and simple",
    "Testing is important, don't skip it!",
    "Code review best practices matter",
    "Clean code is readable code",
    "Documentation saves lives 📝",
    "Git is an essential skill for developers",
    "Open source is amazing! Contributing today",
    "Pair programming session was productive",
    "Refactoring old code feels so good",
    "Performance optimization is an art",
    "Security first, always! 🔒",
    "API design is harder than it looks",
    "Database normalization vs denormalization",
    "Caching strategies for better performance",
    "Load balancing across multiple servers",
    "Monitoring and observability are crucial",
    "CI/CD pipelines save so much time",
    "Code splitting for better load times",
    "Lazy loading improves user experience",
    "WebSockets for real-time features",
    "OAuth2 authentication implementation",
    "JWT tokens for stateless auth",
    "Rate limiting to prevent abuse",
    "CORS can be tricky sometimes",
    "Environment variables for configuration",
    "Logging everything for debugging",
    "Error handling best practices",
    "Async/await makes code cleaner",
    "Promises vs callbacks debate",
    "Functional programming concepts",
    "Object-oriented design patterns",
]

def create_test_users(db, count=10):
    """Create test users if they don't exist"""
    logger.info(f"Creating {count} test users...")
    
    users = []
    for i in range(1, count + 1):
        username = f"testuser{i}"
        
        # Check if user exists
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            users.append(existing)
            continue
        
        user = User(
            username=username,
            email=f"testuser{i}@pulse.dev",
            hashed_password=hash_password("password123"),
            full_name=f"Test User {i}",
            bio=f"Test account {i} for demo purposes"
        )
        db.add(user)
        users.append(user)
    
    db.commit()
    logger.info(f"✅ Created/verified {len(users)} test users")
    return users

def create_test_posts(db, users, count=100):
    """Create test posts"""
    logger.info(f"Creating {count} test posts...")
    
    posts = []
    base_time = datetime.utcnow()
    
    for i in range(count):
        # Random user
        user = random.choice(users)
        
        # Random content
        content = random.choice(POST_TEMPLATES)
        
        # Add some variety to content
        if random.random() > 0.7:
            content += f" #{random.choice(['tech', 'coding', 'python', 'web', 'api'])}"
        
        if random.random() > 0.8:
            content += f" Post #{i + 1}"
        
        # Create post with staggered timestamps (newest first)
        post = Post(
            author_id=user.id,
            content=content,
            created_at=base_time - timedelta(minutes=i * 2)  # 2 minutes apart
        )
        db.add(post)
        posts.append(post)
        
        if (i + 1) % 20 == 0:
            logger.info(f"  Created {i + 1}/{count} posts...")
    
    db.commit()
    logger.info(f"✅ Created {len(posts)} test posts")
    return posts

def main():
    """Create test data"""
    logger.info("🚀 Starting test data creation...")
    
    db = SessionLocal()
    
    try:
        # Create test users
        users = create_test_users(db, count=10)
        
        # Create test posts
        posts = create_test_posts(db, users, count=100)
        
        logger.info("✅ Test data creation complete!")
        logger.info(f"Created {len(users)} users and {len(posts)} posts")
        logger.info("\nYou can now:")
        logger.info("1. Login as alice or bob")
        logger.info("2. Follow some test users")
        logger.info("3. See 100 posts in your timeline")
        logger.info("4. Test infinite scroll!")
        
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()

