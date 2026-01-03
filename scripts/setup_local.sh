#!/bin/bash

# Setup script for local development

set -e

echo "🚀 Setting up Pulse for local development..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    
    # Generate a random JWT secret
    JWT_SECRET=$(openssl rand -hex 32)
    
    # Update .env with generated secret (macOS/Linux compatible)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/your-secret-key-change-in-production/$JWT_SECRET/" .env
    else
        sed -i "s/your-secret-key-change-in-production/$JWT_SECRET/" .env
    fi
    
    echo "✅ .env file created with secure JWT secret"
else
    echo "✅ .env file already exists"
fi

# Start Docker containers
echo "🐳 Starting Docker containers..."
docker-compose up -d postgres redis

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if postgres is ready
until docker-compose exec -T postgres pg_isready -U pulse_user > /dev/null 2>&1; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
echo "✅ PostgreSQL is ready"

# Check if redis is ready
until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    echo "Waiting for Redis..."
    sleep 2
done
echo "✅ Redis is ready"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
python3 -m pip install -r requirements.txt

# Initialize database
echo "🗄️  Initializing database..."
python3 scripts/init_db.py

# Seed demo data
echo "🌱 Seeding demo data..."
python3 scripts/seed_demo_data.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "  1. Start the API:     uvicorn services.main:app --reload"
echo "  2. Start the worker:  python -m workers.fanout_worker"
echo "  3. Visit API docs:    http://localhost:8000/docs"
echo ""
echo "📝 Demo credentials:"
echo "  Username: alice,  Password: password123"
echo "  Username: bob,    Password: password123"
echo ""

