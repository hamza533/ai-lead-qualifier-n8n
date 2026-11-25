# Standard commands for humans and AI tools (CONVENTIONS 3a).
# All logic lives in Python scripts so the targets behave the same on Linux,
# macOS and Windows (GNU make + Git Bash).

UV      ?= uv
RUN     := $(UV) run
COMPOSE := docker compose
TEST_COMPOSE := $(COMPOSE) -f docker-compose.yml -f docker-compose.test.yml --profile test

.PHONY: help setup dev down logs check lint test test-e2e e2e-up e2e-down eval seed \
        export import credentials hubspot-setup tunnel

help: ## List targets
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-15s %s\n", $$1, $$2}'

setup: ## Install Python deps and create .env with generated secrets
	$(UV) sync
	$(RUN) python -m scripts.init_env

dev: ## Start n8n + Postgres (http://localhost:5678)
	$(COMPOSE) up -d
	$(RUN) python -m scripts.n8n_admin wait

down: ## Stop all containers (data volumes are kept)
	$(TEST_COMPOSE) down

logs: ## Follow n8n logs
	$(COMPOSE) logs -f n8n

lint: ## ruff + mypy + workflow JSON lint
	$(RUN) ruff check .
	$(RUN) ruff format --check .
	$(RUN) mypy
	$(RUN) python -m scripts.lint_workflows

test: ## Unit tests (no containers needed)
	$(RUN) pytest

check: lint test ## lint + test; must pass before every commit

e2e-up: ## Start n8n + Postgres + mock server in test mode, then import workflows
	$(TEST_COMPOSE) up -d --build
	$(RUN) python -m scripts.n8n_admin wait
	$(RUN) python -m scripts.n8n_admin credentials
	$(RUN) python -m scripts.n8n_admin import

e2e-down: ## Stop the test stack and delete its data
	$(TEST_COMPOSE) down -v

test-e2e: e2e-up ## End-to-end tests against mocks (DRY_RUN=true)
	$(RUN) pytest -m e2e

export: ## Export workflows from the running n8n into /workflows
	$(RUN) python -m scripts.n8n_admin export
	$(RUN) python -m scripts.lint_workflows

import: ## Import /workflows into the running n8n and activate them
	$(RUN) python -m scripts.n8n_admin import

credentials: ## Create n8n credentials from .env (fixed IDs, nothing exported)
	$(RUN) python -m scripts.n8n_admin credentials

hubspot-setup: ## Create the ai_* custom contact properties in HubSpot
	$(RUN) python -m scripts.hubspot_setup

eval: ## Run the 30-lead evaluation; writes eval/results.md and .json
	$(RUN) python -m eval.run

seed: ## Post the sample leads to the signed webhook
	$(RUN) python -m scripts.seed

tunnel: ## Public HTTPS URL for forms, webhooks and Slack (needs cloudflared)
	cloudflared tunnel --url http://localhost:5678
