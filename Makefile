.PHONY: setup start stop clean test migrate db-reset validate test-api

setup:
	@bash setup.sh

validate:
	@python validate.py

verify:
	@python verify_setup.py

test-api:
	@bash test_api.sh

test-step-two:
	@bash test_step_two.sh

test-step-three:
	@bash test_step_three.sh

test-step-six:
	@bash test_step_six.sh

start:
	@uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

start-prod:
	@uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

start-worker:
	@bash start_worker.sh

start-worker-dev:
	@celery -A app.celery_app.celery_app worker --loglevel=DEBUG

start-web:
	@cd web && npm run dev

start-web-install:
	@cd web && npm install

infra-up:
	@docker-compose up -d

infra-down:
	@docker-compose down

infra-logs:
	@docker-compose logs -f

migrate:
	@alembic upgrade head

migration:
	@alembic revision --autogenerate -m "$(msg)"

db-reset:
	@docker-compose down -v
	@docker-compose up -d
	@sleep 5
	@alembic upgrade head

clean:
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*.coverage" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +

help:
	@echo "Available commands:"
	@echo "  make setup             - Initial setup (runs setup.sh)"
	@echo "  make verify            - Verify all dependencies and system status"
	@echo "  make validate          - Validate system configuration"
	@echo "  make test-api          - Test API endpoints (requires server running)"
	@echo "  make test-step-two     - Test Step Two orchestration (requires server + worker)"
	@echo "  make test-step-three   - Test Step Three Scrapy extraction (requires server + worker)"
	@echo "  make test-step-six     - Test Step Six complete API (requires server + worker)"
	@echo "  make start             - Start API development server"
	@echo "  make start-worker      - Start Celery worker"
	@echo "  make start-worker-dev  - Start Celery worker (debug mode)"
	@echo "  make start-web         - Start Next.js web UI (requires npm install)"
	@echo "  make start-web-install - Install web UI dependencies"
	@echo "  make start-prod        - Start production API server"
	@echo "  make infra-up          - Start PostgreSQL and Redis"
	@echo "  make infra-down        - Stop PostgreSQL and Redis"
	@echo "  make infra-logs        - View infrastructure logs"
	@echo "  make migrate           - Run database migrations"
	@echo "  make migration         - Create new migration (msg='description')"
	@echo "  make db-reset          - Reset database (WARNING: destroys data)"
	@echo "  make clean             - Clean Python cache files"
