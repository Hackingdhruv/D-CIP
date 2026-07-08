# D-CIP developer convenience targets.
# These wrap the most common workflows so contributors don't memorize flags.

COMPOSE := docker compose -f infrastructure/docker/docker-compose.yml

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install JS and Python dependencies
	pnpm install
	cd apps/api && uv sync

.PHONY: dev
dev: ## Run web + api + worker locally via turbo
	pnpm dev

.PHONY: up
up: ## Start the full stack (dev profile) in Docker
	$(COMPOSE) --profile dev up --build

.PHONY: up-prod
up-prod: ## Start the full stack (prod profile) in Docker
	$(COMPOSE) --profile prod up --build -d

.PHONY: down
down: ## Stop the stack and remove containers
	$(COMPOSE) down

.PHONY: down-volumes
down-volumes: ## Stop the stack and delete data volumes (DESTRUCTIVE)
	$(COMPOSE) down -v

.PHONY: logs
logs: ## Tail logs for all services
	$(COMPOSE) logs -f

.PHONY: lint
lint: ## Lint everything
	pnpm lint

.PHONY: typecheck
typecheck: ## Type-check everything
	pnpm typecheck

.PHONY: test
test: ## Run all unit/integration tests
	pnpm test

.PHONY: format
format: ## Auto-format the whole repo
	pnpm format
	cd apps/api && uv run black . && uv run isort . && uv run ruff check --fix .

.PHONY: migrate
migrate: ## Apply database migrations
	cd apps/api && uv run alembic upgrade head
