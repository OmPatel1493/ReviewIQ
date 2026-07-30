# ReviewIQ developer shortcuts. Run `make` or `make help` to see targets.
# NOTE: recipe lines are indented with TABS (Make requirement).

BACKEND := backend
FRONTEND := frontend

.DEFAULT_GOAL := help

.PHONY: help install install-api install-web dev-api dev-web test lint fmt \
        up down logs build ps clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: install-api install-web ## Install backend + frontend deps

install-api: ## Sync backend Python deps (uv)
	cd $(BACKEND) && uv sync

install-web: ## Install frontend node deps (npm)
	cd $(FRONTEND) && npm install

dev-api: ## Run FastAPI with autoreload on :8000
	cd $(BACKEND) && uv run uvicorn app.main:app --reload --port 8000

dev-web: ## Run the Vite dev server on :5173
	cd $(FRONTEND) && npm run dev

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
