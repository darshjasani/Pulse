.PHONY: help install setup start stop clean test logs

help:
	@echo "Pulse - Development Commands"
	@echo ""
	@echo "  make install    - Install Python dependencies"
	@echo "  make setup      - Full local setup (Docker + DB + seed)"
	@echo "  make start      - Start all services (Docker Compose)"
	@echo "  make stop       - Stop all services"
	@echo "  make clean      - Stop and remove volumes"
	@echo "  make logs       - View logs"
	@echo "  make test       - Run tests"
	@echo "  make dev-api    - Start API in development mode"
	@echo "  make dev-worker - Start worker"
	@echo "  make shell-db   - Open PostgreSQL shell"
	@echo "  make shell-redis- Open Redis CLI"

install:
	pip install -r requirements.txt

setup:
	@echo "Setting up Pulse..."
	chmod +x scripts/setup_local.sh
	./scripts/setup_local.sh

start:
	docker-compose up -d

stop:
	docker-compose stop

clean:
	docker-compose down -v

logs:
	docker-compose logs -f

test:
	pytest tests/ -v

dev-api:
	uvicorn services.main:app --reload --log-level info

dev-worker:
	python -m workers.fanout_worker

shell-db:
	docker-compose exec postgres psql -U pulse_user -d pulse_db

shell-redis:
	docker-compose exec redis redis-cli

format:
	black services/ workers/

init-db:
	python scripts/init_db.py

seed-db:
	python scripts/seed_demo_data.py

aws-setup:
	chmod +x scripts/setup_aws.sh
	./scripts/setup_aws.sh

aws-cleanup:
	chmod +x scripts/cleanup_aws.sh
	./scripts/cleanup_aws.sh

build:
	docker-compose build

health:
	@curl -s http://localhost:8000/system/health | python -m json.tool

metrics:
	@curl -s http://localhost:8000/system/metrics | python -m json.tool

