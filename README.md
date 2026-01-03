# ⚡ Pulse

**Scalable Social Feed Platform** - A production-style system design project demonstrating distributed systems concepts, event-driven architecture, and cloud-native design patterns.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![AWS](https://img.shields.io/badge/AWS-Ready-orange.svg)](https://aws.amazon.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [Technology Stack](#-technology-stack)
- [Quick Start](#-quick-start)
- [API Documentation](#-api-documentation)
- [System Design Deep Dive](#-system-design-deep-dive)
- [Performance & Scaling](#-performance--scaling)
- [Tradeoffs & Design Decisions](#-tradeoffs--design-decisions)

---

## 🎯 Overview

Pulse is a social feed platform built to demonstrate **real-world system design concepts** used by companies like Twitter, Instagram, and Facebook. It showcases:

- **Hybrid Push-Pull Timeline Architecture**
- **Event-Driven Fan-out Pattern**
- **Celebrity Problem Solution**
- **Multi-tier Caching Strategy**
- **Graceful Degradation**
- **Cloud-Native Design**

### Problem Statement

Modern social platforms must serve **low-latency personalized feeds** while handling:
- High read traffic (millions of timeline requests/sec)
- Write amplification (one post to millions of timelines)
- Hot users (celebrities with millions of followers)
- Service failures without downtime

**Pulse demonstrates production-grade solutions to these challenges.**

---

## 🏗️ System Architecture

```
┌─────────────┐
│   Client    │
│   (Web UI)  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│  ┌─────────┬──────────┬──────────────┐ │
│  │  Auth   │  Users   │    Posts     │ │
│  │ Service │ Service  │   Service    │ │
│  └─────────┴──────────┴──────────────┘ │
│  ┌──────────────────────────────────┐  │
│  │      Timeline Service            │  │
│  │  (Hybrid Push-Pull Strategy)     │  │
│  └──────────────────────────────────┘  │
└───┬──────────────┬──────────────┬──────┘
    │              │              │
    ▼              ▼              ▼
┌─────────┐  ┌──────────┐  ┌──────────┐
│ Redis   │  │   SQS    │  │PostgreSQL│
│ (Cache) │  │ (Queue)  │  │   (DB)   │
└─────────┘  └────┬─────┘  └──────────┘
                  │
                  ▼
           ┌──────────────┐
           │  Fan-out     │
           │   Worker     │
           └──────────────┘
```

### Data Flow

**Write Path (Normal User):**
1. User creates post, saved to PostgreSQL
2. Event published to SQS queue
3. Fan-out worker consumes event
4. Post pushed to all follower timelines in Redis

**Write Path (Celebrity):**
1. User creates post, saved to PostgreSQL
2. **No fan-out** (write amplification avoided)

**Read Path:**
1. Request timeline, check Redis cache
2. If cache hit, return immediately
3. Pull celebrity posts (always fresh)
4. Merge and sort by timestamp
5. If cache miss, fallback to database

---

## ✨ Key Features

### 1. Hybrid Timeline Architecture
- **Push Model**: Fan-out for normal users (fast reads)
- **Pull Model**: On-demand for celebrities (prevents write amplification)
- Best of both worlds

### 2. Celebrity Detection
- Automatic threshold detection (100K+ followers)
- Dynamic flag update
- Separate handling logic

### 3. Event-Driven Fan-out
- Asynchronous processing via SQS
- Retry logic and idempotency
- Decoupled architecture

### 4. Graceful Degradation
- Redis down? Fall back to database
- SQS unavailable? Direct timeline write
- Always operational

### 5. Production-Ready Code
- Type hints and validation (Pydantic)
- Proper error handling
- Logging and observability
- Security (JWT, password hashing)

---

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL** - Primary data store
- **Redis** - Timeline cache and sorted sets
- **Pydantic** - Data validation

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Local orchestration
- **AWS SQS** - Message queue
- **AWS RDS** - Managed PostgreSQL
- **AWS EC2** - Compute

### Frontend
- **Vanilla JavaScript** - Simple, dependency-free UI
- **HTML/CSS** - Modern responsive design

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- AWS Account (optional for cloud features)

### Setup

```bash
# Clone the repository
cd Pulse

# Run automated setup
chmod +x scripts/setup_local.sh
./scripts/setup_local.sh

# Start the API
uvicorn services.main:app --reload

# In another terminal, start the worker
python -m workers.fanout_worker

# Open the UI
open ui/index.html
```

**Demo Users:** alice, bob, celebrity_user (password: password123)

---

## 📚 API Documentation

### Core Endpoints

**Authentication**
- `POST /auth/signup` - Register new user
- `POST /auth/login` - Login and receive JWT token

**Posts**
- `POST /posts` - Create a new post
- `GET /timeline` - Get personalized timeline

**Social**
- `POST /users/follow/{user_id}` - Follow a user
- `GET /users/{user_id}/followers` - Get user followers

**System**
- `GET /system/health` - Health check
- `GET /system/metrics` - System metrics

**Interactive Documentation:** http://localhost:8000/docs

---

## 🎓 System Design Deep Dive

### The Celebrity Problem

**Problem:** A celebrity with 10M followers posts, resulting in 10M timeline writes and database overload.

**Traditional Approach (Push Only):**
- Write amplification: 1 write becomes 10M writes
- Slow: Takes minutes to fan-out
- Expensive: High compute and storage costs

**Our Solution (Hybrid):**
- **Push for normal users** (< 100K followers)
  - Fast reads (cached)
  - Acceptable write cost
- **Pull for celebrities** (> 100K followers)
  - No fan-out
  - Fetched at read time
  - Fresh and accurate

### Timeline Architecture

**Sorted Sets in Redis:**
```
Key: "timeline:{user_id}"
Value: Sorted Set
  - Member: post_id
  - Score: timestamp
```

**Why Sorted Sets?**
- O(log N) insertion
- O(log N) range queries
- Automatic sorting by timestamp
- Memory efficient

### Fan-out Strategy

**Decision Matrix:**
```
User Type    | Follower Count | Strategy      | Write Cost | Read Cost
-------------|----------------|---------------|------------|----------
Normal       | < 100K         | Push (Fan-out)| Medium     | Low (cached)
Celebrity    | > 100K         | Pull (On-read)| Low        | Medium
```

### Caching Strategy

**L1 Cache (Redis):**
- Timeline sorted sets
- Size-limited to 1000 posts per timeline
- Eviction: ZREMRANGEBYRANK

**Cache Invalidation:**
- **On Follow:** Clear follower's timeline
- **On Unfollow:** Clear follower's timeline
- **On Post Delete:** Remove from all timelines (async)

**Fallback Chain:**
```
Request -> Redis Cache -> PostgreSQL -> Return
```

---

## 📊 Performance & Scaling

### Scaling Strategies

**Horizontal Scaling:**
```
Load Balancer
    ├── API Server 1
    ├── API Server 2
    └── API Server 3
         ↓
    (Stateless, share Redis & DB)
```

**Database Scaling:**
- Read replicas for timeline queries
- Sharding by user_id
- Connection pooling

**Cache Scaling:**
- Redis Cluster (16K slots)
- Shard by user_id hash
- Read replicas for hot keys

**Worker Scaling:**
- Multiple workers reading from SQS
- Auto-scaling based on queue depth
- Dead letter queue for failures

### Bottlenecks & Mitigations

| Bottleneck | Symptom | Solution |
|------------|---------|----------|
| DB Writes | Slow post creation | Write buffer, async commits |
| Redis Memory | OOM errors | TTL, size limits, eviction policy |
| Fan-out Lag | Stale timelines | More workers, batch writes |
| Celebrity Reads | Slow timelines | Separate cache, CDN |

---

## ⚖️ Tradeoffs & Design Decisions

### 1. Eventual Consistency

**Decision:** Timelines are eventually consistent

**Why:**
- CAP Theorem: Choose Availability + Partition Tolerance
- Acceptable for social feeds (not financial data)
- Enables horizontal scaling

**Tradeoff:**
- High availability
- Better performance
- Brief inconsistency (seconds)

### 2. Push vs. Pull

**Decision:** Hybrid approach based on follower count

**Why:**
- Best of both worlds
- Optimizes for common case (normal users)
- Handles edge case (celebrities)

**Tradeoff:**
- Balanced write/read costs
- Scalable
- More complexity

### 3. Redis for Timelines

**Decision:** Use Redis sorted sets for timeline cache

**Why:**
- In-memory results in very fast reads
- Sorted sets are natural fit for timelines
- Simple data structure

**Tradeoff:**
- Sub-50ms reads
- Simple implementation
- Memory cost
- Data loss on crash (acceptable)

### 4. SQS for Events

**Decision:** Use message queue for fan-out

**Why:**
- Decouples API from worker
- Built-in retry and DLQ
- Managed service (no ops)

**Tradeoff:**
- Reliability
- Scalability
- AWS dependency
- Latency (seconds)

### 5. Simple Pagination

**Decision:** Simple offset/limit pagination

**Why:**
- Sufficient for demonstration
- Easy to understand

**Production would use:**
- Cursor-based pagination
- Prevents skipped/duplicate posts
- Better for real-time feeds

---

## 📄 License

MIT License - See LICENSE file for details

---

**Built with FastAPI, PostgreSQL, Redis, AWS SQS, Docker**
