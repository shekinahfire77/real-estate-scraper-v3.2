# Makefile for Real Estate Scraper

.PHONY: help install test clean run docker-up docker-down dashboard cli export

# Default target
help:
	@echo "Real Estate Scraper - Available Commands"
	@echo "========================================"
	@echo "make install        - Install dependencies"
	@echo "make test          - Run tests"
	@echo "make clean         - Clean temporary files"
	@echo "make run           - Run scraper"
	@echo "make dashboard     - Start monitoring dashboard"
	@echo "make cli           - Run CLI tool"
	@echo "make export        - Export data"
	@echo "make docker-up     - Start Docker containers"
	@echo "make docker-down   - Stop Docker containers"
	@echo "make format        - Format code with black"
	@echo "make lint          - Run linting checks"

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	pytest -v --cov=src --cov-report=html

# Clean temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf htmlcov
	rm -rf .coverage

# Run scraper
run:
	python -m src.main_with_db

# Run scraper with limit
run-test:
	python -m src.main_with_db --limit 5

# Start dashboard
dashboard:
	python dashboard.py

# CLI commands
cli:
	python -m src.cli --help

cli-stats:
	python -m src.cli stats

cli-search:
	python -m src.cli search

cli-export:
	python -m src.cli export

# Export data in different formats
export-csv:
	python -m src.cli export --format csv

export-json:
	python -m src.cli export --format json

export-excel:
	python -m src.cli export --format excel

export-parquet:
	python -m src.cli export --format parquet

# Docker commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-clean:
	docker-compose down -v

# Code formatting
format:
	black src tests
	isort src tests

# Linting
lint:
	flake8 src tests
	black --check src tests
	isort --check-only src tests

# Database migrations
db-init:
	alembic init migrations

db-migrate:
	alembic revision --autogenerate -m "Auto migration"

db-upgrade:
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

# Development setup
dev-setup: install
	pre-commit install
	cp .env.example .env
	@echo "Development environment ready!"
	@echo "Edit .env file with your settings"

# Production deployment
deploy:
	@echo "Deploying to production..."
	docker-compose -f docker-compose.yml up -d --build
	@echo "Deployment complete!"

# Backup database
backup:
	@echo "Backing up database..."
	python -c "from src.database.connection import DatabaseConnection; db = DatabaseConnection(); db.backup_database()"
	@echo "Backup complete!"
