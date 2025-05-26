.PHONY: help install install-dev test test-backend test-frontend lint format clean docker-build docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  test         - Run all tests"
	@echo "  test-backend - Run backend tests"
	@echo "  test-frontend- Run frontend tests"
	@echo "  lint         - Run linters"
	@echo "  format       - Format code"
	@echo "  clean        - Clean build artifacts"
	@echo "  docker-build - Build Docker images"
	@echo "  docker-up    - Start services with Docker Compose"
	@echo "  docker-down  - Stop services"

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm ci --only=production

install-dev:
	cd backend && pip install -r requirements.txt -r requirements-dev.txt
	cd frontend && npm ci
	pre-commit install

test: test-backend test-frontend

test-backend:
	cd backend && pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-frontend:
	cd frontend && npm test -- --coverage --watchAll=false

lint:
	cd backend && flake8 app tests
	cd backend && mypy app
	cd frontend && npm run lint

format:
	cd backend && black app tests
	cd backend && isort app tests
	cd frontend && npm run lint:fix

clean:
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	cd backend && rm -rf .coverage htmlcov/ .pytest_cache/
	cd frontend && rm -rf build/ coverage/
	docker system prune -f

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

dev-start:
	./scripts/dev-start.sh

deploy-prod:
	docker-compose -f docker-compose.prod.yml up -d --build

health-check:
	./scripts/health-check.sh