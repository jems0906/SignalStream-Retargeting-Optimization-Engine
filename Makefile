# Makefile for Real-Time Retargeting & Optimization Signals Service

.PHONY: help setup install test lint format run clean docker-up docker-down

# Default target
help:
	@echo "Available commands:"
	@echo "  setup     - Setup development environment"
	@echo "  install   - Install dependencies" 
	@echo "  test      - Run tests"
	@echo "  lint      - Run code linting"
	@echo "  format    - Format code"
	@echo "  run       - Start the service"
	@echo "  clean     - Clean up generated files"
	@echo "  docker-up - Start Redis with Docker"
	@echo "  docker-down - Stop Docker services"

# Setup development environment
setup:
	python -m venv .venv
	@echo "Virtual environment created. Activate with:"
	@echo "  Windows: .venv\\Scripts\\activate"
	@echo "  Unix/Mac: source .venv/bin/activate"

# Install dependencies
install:
	pip install --upgrade pip
	pip install -r requirements.txt

# Install development dependencies
install-dev: install
	pip install black flake8 mypy isort

# Run tests
test:
	pytest tests/ -v

# Run tests with coverage
test-coverage:
	pytest tests/ --cov=src --cov-report=html --cov-report=term

# Code linting
lint:
	flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503
	mypy src/ --ignore-missing-imports

# Format code
format:
	black src/ tests/ --line-length=100
	isort src/ tests/ --profile black

# Start the service
run:
	python start.py

# Start with demo
run-demo:
	python start.py --demo

# Start Redis with Docker
docker-up:
	docker-compose up -d redis

# Stop Docker services
docker-down:
	docker-compose down

# Clean up generated files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache/

# Development workflow
dev-setup: setup install
	@echo "Development environment ready!"

# Production build
build:
	@echo "Building production image..."
	docker build -t retargeting-service .

# Run all checks
check: lint test
	@echo "All checks passed!"