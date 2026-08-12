# ReviewIQ developer shortcuts. Run `make` or `make help` to see targets.
# NOTE: recipe lines are indented with TABS (Make requirement).

BACKEND := backend
FRONTEND := frontend

.DEFAULT_GOAL := help

.PHONY: help install install-api install-web infra dev dev-api dev-web worker review test lint fmt \
        up down logs build ps clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: install-api install-web ## Install backend + frontend deps

install-api: ## Sync backend Python deps (uv)
	cd $(BACKEND) && uv sync

install-web: ## Install frontend node deps (npm)
	cd $(FRONTEND) && npm install

infra: ## Start ONLY the data services (Postgres + Redis + Qdrant) for local dev
	docker compose up -d db redis qdrant

dev: infra ## Data services + API + worker + frontend together (Ctrl-C stops all). Ollama app must be running for review/ask.
	@echo "▶ API :8000 · worker · frontend :5173 — Ctrl-C stops all three."
	@echo "  (review/ask also need the Ollama app running)"
	@trap 'kill 0' INT TERM; \
	( cd $(BACKEND) && uv run uvicorn app.main:app --reload --port 8000 ) & \
	( cd $(BACKEND) && uv run celery -A app.workers.celery_app worker --loglevel=info ) & \
	( cd $(FRONTEND) && npm run dev ) & \
	wait

dev-api: ## Run FastAPI with autoreload on :8000
	cd $(BACKEND) && uv run uvicorn app.main:app --reload --port 8000

dev-web: ## Run the Vite dev server on :5173
	cd $(FRONTEND) && npm run dev

worker: ## Run the Celery worker (needed for indexing + reviews)
	cd $(BACKEND) && uv run celery -A app.workers.celery_app worker --loglevel=info

review: ## Trigger a review from the CLI: REVIEWIQ_TOKEN=<jwt> make review REPO=<uuid> PR=<n>
	./scripts/review.sh $(REPO) $(PR)

test: ## Run backend tests
	cd $(BACKEND) && uv run pytest

lint: ## Lint backend (ruff + mypy) and frontend
	cd $(BACKEND) && uv run ruff check . && uv run mypy app
	cd $(FRONTEND) && npm run lint

fmt: ## Auto-format / auto-fix backend
	cd $(BACKEND) && uv run ruff format . && uv run ruff check --fix .

up: ## Start the Docker stack (Postgres, Redis, Qdrant, API)
	docker compose up -d

down: ## Stop the Docker stack
	docker compose down

logs: ## Tail Docker logs
	docker compose logs -f

build: ## Build Docker images
	docker compose build

ps: ## Show running containers
	docker compose ps

clean: ## Remove caches and build artifacts
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache $(BACKEND)/.mypy_cache
	rm -rf $(FRONTEND)/dist
