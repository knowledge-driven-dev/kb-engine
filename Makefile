.PHONY: help install install-dev lint format type-check test test-unit test-integration test-api run dev clean docker-up docker-down migrate

# Default target
help:
	@echo "KB-Engine Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install production dependencies"
	@echo "  make install-dev    Install development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           Run linter (ruff)"
	@echo "  make format         Format code (ruff)"
	@echo "  make type-check     Run type checker (mypy)"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run all tests"
	@echo "  make test-unit      Run unit tests only"
	@echo "  make test-integration Run integration tests"
	@echo "  make test-api       Run API tests"
	@echo "  make test-cov       Run tests with coverage"
	@echo ""
	@echo "Running:"
	@echo "  make run            Run the API server"
	@echo "  make dev            Run with auto-reload"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      Start Docker services"
	@echo "  make docker-down    Stop Docker services"
	@echo ""
	@echo "Database:"
	@echo "  make migrate        Run database migrations"
	@echo "  make migrate-create Create new migration"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          Remove build artifacts"

# =============================================================================
# Setup
# =============================================================================

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# =============================================================================
# Code Quality
# =============================================================================

lint:
	ruff check src tests
	ruff format --check src tests

format:
	ruff check --fix src tests
	ruff format src tests

type-check:
	mypy src

# =============================================================================
# Testing
# =============================================================================

test:
	pytest

test-unit:
	pytest -m unit tests/unit

test-integration:
	pytest -m integration tests/integration

test-api:
	pytest -m api tests/api

test-cov:
	pytest --cov=kb_engine --cov-report=html --cov-report=term

# =============================================================================
# Running
# =============================================================================

run:
	uvicorn kb_engine.api.main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn kb_engine.api.main:app --host 0.0.0.0 --port 8000 --reload

# =============================================================================
# Docker
# =============================================================================

docker-up:
	docker compose -f docker/docker-compose.yml up -d

docker-down:
	docker compose -f docker/docker-compose.yml down

docker-logs:
	docker compose -f docker/docker-compose.yml logs -f

# =============================================================================
# Database
# =============================================================================

migrate:
	alembic upgrade head

migrate-create:
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

# =============================================================================
# Cleanup
# =============================================================================

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
