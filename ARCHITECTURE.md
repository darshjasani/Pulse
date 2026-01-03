# 🏗️ Pulse Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Models](#data-models)
4. [API Design](#api-design)
5. [Timeline Architecture](#timeline-architecture)
6. [Fan-out Strategy](#fan-out-strategy)
7. [Scaling Strategy](#scaling-strategy)
8. [Failure Handling](#failure-handling)

---

## System Overview

Pulse is a distributed social feed platform designed to handle high read and write throughput while maintaining low latency and high availability.

### Core Requirements

**Functional:**
- User authentication & profiles
- Post creation and retrieval
- Social graph (follow/unfollow)
- Personalized timeline generation
- Celebrity user detection

**Non-Functional:**
- Latency: P95 < 200ms for timeline reads
- Availability: 99.9% uptime
- Consistency: Eventual consistency acceptable
- Scalability: Horizontal scaling capability

---

## Component Architecture

### 1. API Layer (FastAPI)

**Responsibilities:**
- Request validation & authentication
- Business logic orchestration
- Response formatting

**Design Patterns:**
- Dependency Injection (FastAPI's Depends)
- Repository pattern (database access)
- Middleware (CORS, logging)

**Key Files:**
```
services/
├── routers/
│   ├── auth.py      # Authentication endpoints
│   ├── users.py     # User management & social graph
│   ├── posts.py     # Post CRUD operations
│   ├── timeline.py  # Timeline generation
│   └── system.py    # Health & metrics
└── main.py          # Application entry point
```

### 2. Data Layer

#### PostgreSQL (Primary Store)
```sql
Tables:
- users         # User accounts & metadata
- posts         # All posts
- follows       # Social graph relationships
```

**Indexes:**
- `users.username` (unique, B-tree)
- `users.email` (unique, B-tree)
- `posts.author_id` (B-tree)
- `posts.created_at` (B-tree)
- `follows(follower_id, following_id)` (composite, unique)

#### Redis (Cache Layer)
```
Data Structures:
- Sorted Sets: timeline:{user_id} → {post_id: timestamp}
- Strings: cache:{key} → JSON values
```

**Memory Management:**
- Per-timeline limit: 1000 posts
- Eviction: ZREMRANGEBYRANK (keep latest)
- No TTL (size-limited instead)

### 3. Worker Layer

**Fan-out Worker:**
```python
Process Flow:
1. Poll SQS queue (long polling, 20s)
2. Receive post_created events
3. Query followers from database
4. Write to each follower's timeline (Redis)
5. Delete message from queue
```

**Error Handling:**
- SQS visibility timeout: 30s
- Max retries: 3
- Dead letter queue for failures
- Idempotent writes

### 4. Message Queue (AWS SQS)

**Queue Configuration:**
```yaml
Queue Name: pulse-post-created
Type: Standard (at-least-once delivery)
Visibility Timeout: 30 seconds
Message Retention: 4 days
Max Message Size: 256 KB
```

**Message Format:**
```json
{
  "event_type": "post_created",
  "post_id": 12345,
  "author_id": 678,
  "is_celebrity": false,
  "timestamp": 1704268800.0
}
```

---

## Data Models

### User Model
```python
class User:
    id: int                          # Primary key
    username: str                    # Unique, indexed
    email: str                       # Unique, indexed
    hashed_password: str             # bcrypt hash
    full_name: Optional[str]
    bio: Optional[str]
    is_active: bool = True
    is_celebrity: bool = False       # Auto-updated
    follower_count: int = 0          # Denormalized
    following_count: int = 0         # Denormalized
    created_at: datetime
    updated_at: datetime
```

**Design Decision:**
- Denormalized counts for performance
- Updated transactionally with follow/unfollow
- Alternative: COUNT query (slower)

### Post Model
```python
class Post:
    id: int                          # Primary key
    author_id: int                   # Foreign key → users.id
    content: str                     # Max 5000 chars
    created_at: datetime             # Indexed
    
    # Relationship
    author: User
```

**Design Decision:**
- Simple flat structure (no nested comments)
- Immutable after creation (no edits)
- Soft delete possible (add `deleted_at`)

### Follow Model
```python
class Follow:
    id: int                          # Primary key
    follower_id: int                 # Foreign key → users.id
    following_id: int                # Foreign key → users.id
    created_at: datetime
    
    # Unique constraint: (follower_id, following_id)
    # Indexes: follower_id, following_id
```

**Design Decision:**
- Bidirectional queries supported
- Prevents duplicate follows
- No "mutual follow" flag (computed)

---

## API Design

### RESTful Principles

```
Resource-based URLs:
✅ POST /posts
✅ GET /timeline
✅ POST /users/follow/{user_id}

❌ POST /createPost
❌ GET /getTimeline
```

### Authentication

**JWT-based:**
```
Header: Authorization: Bearer <token>
Token Payload:
{
  "user_id": 123,
  "username": "alice",
  "exp": 1704268800
}
```

**Token Lifecycle:**
1. Login → Generate token (24h expiry)
2. Include in requests → Validate & extract user
3. Expired → 401 Unauthorized (re-login)

### Error Responses

**Standardized Format:**
```json
{
  "detail": "User not found",
  "type": "NotFoundError"
}
```

**HTTP Status Codes:**
- 200: Success
- 201: Created
- 204: No Content (delete)
- 400: Bad Request (validation)
- 401: Unauthorized (auth)
- 404: Not Found
- 500: Internal Server Error

---

## Timeline Architecture

### Hybrid Push-Pull Model

#### Push Model (Fan-out on Write)
```
Trigger: User creates post
Process:
1. Save post to database
2. Publish event to SQS
3. Worker fans out to followers
4. Write to Redis timelines

Pros: Fast reads (cached)
Cons: Write amplification
Best for: Normal users (<100K followers)
```

#### Pull Model (Fetch on Read)
```
Trigger: User requests timeline
Process:
1. Query posts from followed celebrities
2. Merge with cached timeline
3. Sort by timestamp

Pros: No write amplification
Cons: Slower reads
Best for: Celebrities (>100K followers)
```

### Timeline Generation Algorithm

```python
def get_timeline(user_id, limit=50):
    # 1. Get cached timeline (pushed posts)
    cached_posts = redis.zrevrange(f"timeline:{user_id}", 0, limit)
    
    # 2. Get celebrity posts (pulled posts)
    celebrity_ids = get_followed_celebrities(user_id)
    celebrity_posts = db.query(Post).filter(
        Post.author_id.in_(celebrity_ids)
    ).order_by(Post.created_at.desc()).limit(20)
    
    # 3. Merge and sort
    all_posts = merge_sort_by_timestamp(cached_posts, celebrity_posts)
    
    # 4. Return top N
    return all_posts[:limit]
```

**Complexity:**
- Cache hit: O(log N) - Redis sorted set range
- Celebrity query: O(M log M) - M = celebrity count
- Merge: O((N+M) log(N+M))
- Total: O((N+M) log(N+M)) ≈ O(N log N)

### Cache Strategy

**Write-through Cache:**
```python
# On post creation (via worker)
def add_to_timeline(user_id, post_id, timestamp):
    redis.zadd(f"timeline:{user_id}", {post_id: timestamp})
    redis.zremrangebyrank(f"timeline:{user_id}", 0, -1001)  # Keep 1000
```

**Cache Invalidation:**
```python
# On follow/unfollow
def on_follow(follower_id, following_id):
    # Option 1: Clear cache (simple)
    redis.delete(f"timeline:{follower_id}")
    
    # Option 2: Backfill (complex, better UX)
    recent_posts = get_user_posts(following_id, limit=100)
    for post in recent_posts:
        redis.zadd(f"timeline:{follower_id}", {post.id: post.timestamp})
```

**Current Implementation:** Option 1 (clear cache) for simplicity

---

## Fan-out Strategy

### Decision Matrix

```python
CELEBRITY_THRESHOLD = 100_000

def should_fanout(user):
    return user.follower_count < CELEBRITY_THRESHOLD
```

### Fan-out Implementation

**Synchronous vs. Asynchronous:**

❌ **Synchronous (naive):**
```python
def create_post(user, content):
    post = save_post(user, content)
    followers = get_followers(user.id)
    for follower in followers:
        add_to_timeline(follower.id, post.id)  # Blocking!
    return post
```
Problem: High follower count = timeout

✅ **Asynchronous (our approach):**
```python
def create_post(user, content):
    post = save_post(user, content)
    if not user.is_celebrity:
        sqs.publish("post_created", post.id)  # Non-blocking
    return post
```
Advantage: API returns immediately, worker handles fan-out

### Batch Processing

```python
# Worker optimization
def fan_out_to_followers(post_id, follower_ids):
    BATCH_SIZE = 1000
    for i in range(0, len(follower_ids), BATCH_SIZE):
        batch = follower_ids[i:i+BATCH_SIZE]
        pipeline = redis.pipeline()
        for follower_id in batch:
            pipeline.zadd(f"timeline:{follower_id}", {post_id: timestamp})
        pipeline.execute()  # Single network round-trip
```

**Performance:**
- Without batching: 10K followers = 10K Redis calls
- With batching: 10K followers = 10 Redis calls

---

## Scaling Strategy

### Horizontal Scaling

#### API Layer
```yaml
Load Balancer (ALB)
  ├── API Instance 1
  ├── API Instance 2
  └── API Instance 3

Auto-scaling triggers:
- CPU > 70%
- Request count > 1000/min
```

**Stateless Design:**
- No in-memory session storage
- JWT for authentication
- All state in Redis/Database

#### Worker Layer
```yaml
SQS Queue
  ├── Worker Instance 1
  ├── Worker Instance 2
  └── Worker Instance 3

Auto-scaling triggers:
- Queue depth > 1000 messages
- Oldest message age > 5 minutes
```

**Parallel Processing:**
- Multiple workers reading same queue
- SQS ensures no duplicate processing (visibility timeout)

### Database Scaling

#### Read Replicas
```
┌──────────┐
│  Primary │ (writes)
└────┬─────┘
     │ Replication
     ├─────────┬─────────┐
     ▼         ▼         ▼
  Replica1  Replica2  Replica3
  (reads)   (reads)   (reads)
```

**Query Routing:**
```python
# Writes
post = Post(...)
primary_db.add(post)

# Reads
posts = read_replica_db.query(Post).all()
```

#### Sharding
```
Shard by user_id:
- Shard 0: user_id % 4 == 0
- Shard 1: user_id % 4 == 1
- Shard 2: user_id % 4 == 2
- Shard 3: user_id % 4 == 3
```

**Challenges:**
- Cross-shard queries (followers on different shards)
- Rebalancing (add/remove shards)

### Cache Scaling

#### Redis Cluster
```
16,384 hash slots
Slot assignment: CRC16(key) % 16384

Example:
- Node 1: slots 0-5460
- Node 2: slots 5461-10922
- Node 3: slots 10923-16383
```

**Key Distribution:**
```python
key = f"timeline:{user_id}"
slot = crc16(key) % 16384
node = get_node_for_slot(slot)
```

---

## Failure Handling

### Redis Failure

**Detection:**
```python
def is_available():
    try:
        redis.ping()
        return True
    except:
        return False
```

**Fallback:**
```python
def get_timeline(user_id):
    # Try cache first
    if redis.is_available():
        return redis.get_timeline(user_id)
    
    # Fallback to database
    return db.query(Post).filter(...).all()
```

**Impact:**
- Latency: 50ms → 200ms
- Load: Database sees more queries
- Recovery: Automatic (cache gradually rebuilds)

### Database Failure

**Connection Pool:**
```python
engine = create_engine(
    url,
    pool_size=10,           # 10 persistent connections
    max_overflow=20,        # 20 temporary connections
    pool_pre_ping=True      # Verify before using
)
```

**Retry Logic:**
```python
from tenacity import retry, stop_after_attempt

@retry(stop=stop_after_attempt(3))
def save_post(post):
    db.add(post)
    db.commit()
```

### SQS Failure

**Message Visibility:**
```
1. Worker receives message
2. Visibility timeout starts (30s)
3. If worker crashes, message becomes visible again
4. Another worker processes it
```

**Dead Letter Queue:**
```
Max receives: 3
If failed 3 times → Move to DLQ
Manual intervention required
```

### Worker Failure

**Graceful Shutdown:**
```python
def signal_handler(sig, frame):
    logger.info("Shutting down gracefully...")
    # Finish current message
    # Don't receive new messages
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
```

**Recovery:**
- In-flight messages: Reprocessed after visibility timeout
- New messages: Picked up by other workers

---

## Performance Optimizations

### Database Query Optimization

**Before:**
```python
# N+1 query problem
posts = db.query(Post).all()
for post in posts:
    author = db.query(User).get(post.author_id)  # N queries!
```

**After:**
```python
# Eager loading
posts = db.query(Post).options(
    joinedload(Post.author)
).all()  # 1 query with JOIN
```

### Connection Pooling

```python
# Reuse database connections
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Per-request session
@app.get("/posts")
def get_posts(db: Session = Depends(get_db)):
    return db.query(Post).all()
    # Session returned to pool automatically
```

### Redis Pipelining

```python
# Bad: Multiple round-trips
for user_id in user_ids:
    redis.get(f"timeline:{user_id}")

# Good: Single round-trip
pipeline = redis.pipeline()
for user_id in user_ids:
    pipeline.get(f"timeline:{user_id}")
results = pipeline.execute()
```

---

## Monitoring & Observability

### Key Metrics

**API Layer:**
- Request rate (requests/sec)
- Error rate (4xx, 5xx)
- Latency (P50, P95, P99)

**Database:**
- Query time
- Connection pool usage
- Slow queries (>100ms)

**Redis:**
- Hit rate
- Memory usage
- Evictions

**Worker:**
- Messages processed/sec
- Processing time
- Queue depth

### Health Checks

```python
@app.get("/system/health")
def health_check():
    return {
        "database": check_database(),
        "redis": check_redis(),
        "sqs": check_sqs()
    }
```

**Usage:**
- Load balancer health checks
- Monitoring alerts
- Deployment verification

---

## Security Considerations

### Authentication
- JWT with expiration
- Bcrypt password hashing (cost=12)
- HTTPS only (production)

### Authorization
- User can only modify own resources
- Admin endpoints (if added) require role check

### Input Validation
- Pydantic models validate all inputs
- SQL injection: SQLAlchemy parameterized queries
- XSS: Escaped output (if HTML rendering)

### Rate Limiting
- Not implemented (TODO)
- Production: Use Redis for rate limit counters

---

## Future Enhancements

1. **Cursor-based Pagination**
   - Better for real-time feeds
   - Prevents duplicate/skipped posts

2. **Post Reactions** (likes, comments)
   - New tables: `reactions`, `comments`
   - Counter cache in Redis

3. **Real-time Updates** (WebSocket)
   - New posts appear without refresh
   - AWS AppSync or WebSocket API

4. **Content Delivery Network**
   - Cache static content
   - Reduce API load

5. **Machine Learning**
   - Personalized ranking
   - Spam detection
   - Recommendation engine

---

**This architecture balances simplicity with production-readiness, demonstrating key distributed systems concepts while remaining demo-friendly.**

