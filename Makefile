.PHONY: help fmt validate plan apply lint test clean

# Default environment
ENV ?= prod

# Terraform directories
TF_BOOTSTRAP_DIR := terraform/bootstrap
TF_ENV_DIR := terraform/envs/$(ENV)
TF_MODULES_DIR := terraform/modules

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# -----------------------------------------------------------------------------
# Terraform Commands
# -----------------------------------------------------------------------------

fmt: ## Format all Terraform files
	terraform fmt -recursive terraform/

fmt-check: ## Check Terraform formatting
	terraform fmt -check -recursive terraform/

validate: validate-bootstrap validate-env ## Validate all Terraform configurations

validate-bootstrap: ## Validate bootstrap Terraform
	cd $(TF_BOOTSTRAP_DIR) && terraform init -backend=false && terraform validate

validate-env: ## Validate environment Terraform (use ENV=prod)
	cd $(TF_ENV_DIR) && terraform init -backend=false && terraform validate

plan: ## Run terraform plan (use ENV=prod)
	cd $(TF_ENV_DIR) && terraform plan

apply: ## Run terraform apply (use ENV=prod)
	cd $(TF_ENV_DIR) && terraform apply

init: ## Initialize Terraform backend (use ENV=prod)
	cd $(TF_ENV_DIR) && terraform init

# -----------------------------------------------------------------------------
# Linting
# -----------------------------------------------------------------------------

lint: lint-tf ## Run all linters

lint-tf: ## Run TFLint on all Terraform code
	@echo "Linting bootstrap..."
	cd $(TF_BOOTSTRAP_DIR) && tflint
	@echo "Linting $(ENV) environment..."
	cd $(TF_ENV_DIR) && tflint
	@echo "Linting modules..."
	@for dir in $(TF_MODULES_DIR)/*; do \
		if [ -d "$$dir" ]; then \
			echo "Linting $$dir..."; \
			cd "$$dir" && tflint && cd -; \
		fi \
	done

lint-python: ## Run Python linters (ruff)
	ruff check .
	ruff format --check .

# -----------------------------------------------------------------------------
# Testing
# -----------------------------------------------------------------------------

test: lint-python test-unit ## Run linters and unit tests

test-unit: ## Run unit tests
	pytest -q tests/unit

eval: ## Run eval harness (COLLECTION=complex-systems, FAST=1, GOLDEN=golden_live.jsonl)
	python3 evals/run.py --collection $(COLLECTION) $(if $(FAST),--fast,) $(if $(GOLDEN),--golden $(GOLDEN),)

test-integration: ## Run integration tests
	@echo "TODO: pytest tests/integration"

test-eval: ## Run fast eval subset
	@echo "TODO: python evals/run.py --fast"

# -----------------------------------------------------------------------------
# Pre-commit
# -----------------------------------------------------------------------------

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

pre-commit-run: ## Run pre-commit on all files
	pre-commit run --all-files

# -----------------------------------------------------------------------------
# Development
# -----------------------------------------------------------------------------

dev-setup: ## Set up development environment
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "Installing Python dependencies..."
	@if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
	@if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
	@echo "Done!"

clean: ## Clean up temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".terraform" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.tfplan" -delete 2>/dev/null || true
	find . -type f -name ".terraform.lock.hcl" -delete 2>/dev/null || true

# -----------------------------------------------------------------------------
# Docker (for local development)
# -----------------------------------------------------------------------------

docker-up: ## Start local development services (Postgres + pgvector)
	docker compose up -d

docker-down: ## Stop local development services
	docker compose down

docker-logs: ## View local development service logs
	docker compose logs -f
