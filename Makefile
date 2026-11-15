.DEFAULT_GOAL := help
RUN    := uv run
MANAGE := $(RUN) python manage.py

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make \033[36m<target>\033[0m\n"} \
		/^[a-zA-Z0-9_-]+:.*##/ { printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2 } \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Setup & run
.PHONY: setup
setup: env ## First-time setup: deps, .env, git hooks, migrations (PostgreSQL must be running)
	uv sync --frozen
	$(RUN) pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
	$(MANAGE) migrate

.PHONY: env
env: ## Create .env from .env.example with a generated SECRET_KEY (keeps an existing .env)
	@if [ -f .env ]; then echo ".env already exists - leaving it untouched"; else \
		cp .env.example .env && python3 -c "import pathlib,secrets; p=pathlib.Path('.env'); p.write_text(p.read_text().replace('change-me-generate-with-make-env', secrets.token_urlsafe(50)))" \
		&& echo "Created .env"; fi

.PHONY: run
run: ## Run the development server on http://localhost:8000
	$(MANAGE) runserver

.PHONY: migrate
migrate: ## Apply database migrations
	$(MANAGE) migrate

.PHONY: makemigrations
makemigrations: ## Generate migrations from model changes
	$(MANAGE) makemigrations

##@ Quality
.PHONY: format
format: ## Auto-format and auto-fix lint issues
	$(RUN) ruff format .
	$(RUN) ruff check . --fix

.PHONY: lint
lint: ## Lint + format check (no changes)
	$(RUN) ruff check .
	$(RUN) ruff format --check .

.PHONY: typecheck
typecheck: ## Static type check (mypy strict)
	$(RUN) mypy .

.PHONY: security
security: ## Bandit static scan + dependency CVE audit
	$(RUN) bandit -c pyproject.toml -r apps common config -q
	uv export --frozen --no-dev --group prod --no-emit-project -o /tmp/prod-requirements.txt >/dev/null
	$(RUN) pip-audit -r /tmp/prod-requirements.txt --no-deps --disable-pip

.PHONY: test
test: ## Run the test-suite (unit, integration, performance)
	$(RUN) pytest

.PHONY: cov
cov: ## Run tests with branch coverage (fails under 90%)
	$(RUN) pytest --cov --cov-report=term-missing --cov-report=xml

.PHONY: migrations-check
migrations-check: ## Fail if models and migrations are out of sync
	$(MANAGE) makemigrations --check --dry-run

.PHONY: ci
ci: lint typecheck security migrations-check cov ## Everything CI runs

##@ Docker
.PHONY: up
up: ## Run the API in Docker (connects to your PostgreSQL via DOCKER_DATABASE_URL)
	docker compose up --build -d --wait
	@echo "API: http://localhost:8000/api/v1"

.PHONY: down
down: ## Stop the Docker stack
	docker compose down

.PHONY: logs
logs: ## Tail API logs
	docker compose logs -f api

##@ Housekeeping
.PHONY: clean
clean: ## Remove caches and build artefacts
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) \
		-not -path "./.venv/*" -prune -exec rm -rf {} +
	rm -rf .coverage coverage.xml
