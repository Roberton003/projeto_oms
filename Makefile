# Makefile — projeto_oms (WHO GHO → dbt star schema)
# ==============================================
# Targets portáveis para setup, build, test e CI.
# Uso: make setup  → instala dependências
#      make build  → build completo dbt
#      make test   → apenas testes dbt

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Detect OS for python command
PYTHON := python3
UNAME_S := $(shell uname -s)

# Directories
DBT_DIR := dbt
VENV_DIR := venv

# Project-specific env defaults
DBT_RAW_DB ?= $(abspath database/who_gho.db)
DBT_TARGET ?= dev
DBT_PROFILES_DIR ?= $(abspath $(DBT_DIR))

export DBT_RAW_DB
export DBT_PROFILES_DIR

.PHONY: help setup venv deps build test run clean shell full-rebuild ci

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: ## Create Python virtual environment
	test -d $(VENV_DIR) || $(PYTHON) -m venv $(VENV_DIR)

setup: venv deps ## Full setup: venv + Python deps + dbt packages
	@echo "✓ Setup complete. Run 'make build' to build the dbt project."

deps: venv ## Install Python + dbt dependencies
	$(VENV_DIR)/bin/pip install -q --upgrade pip
	$(VENV_DIR)/bin/pip install -q -r requirements.txt
	cd $(DBT_DIR) && $(abspath $(VENV_DIR))/bin/dbt deps

build: ## Run dbt build (models + tests)
	cd $(DBT_DIR) && $(abspath $(VENV_DIR))/bin/dbt build --target $(DBT_TARGET)

test: ## Run dbt tests only
	cd $(DBT_DIR) && $(abspath $(VENV_DIR))/bin/dbt test --target $(DBT_TARGET)

run: ## Run dbt models only
	cd $(DBT_DIR) && $(abspath $(VENV_DIR))/bin/dbt run --target $(DBT_TARGET)

clean: ## Clean dbt artifacts
	rm -rf $(DBT_DIR)/target $(DBT_DIR)/dbt_packages $(DBT_DIR)/logs
	rm -f $(DBT_DIR)/*.duckdb $(DBT_DIR)/*.duckdb.wal
	@echo "✓ Cleaned dbt artifacts"

full-rebuild: clean build ## Clean + full rebuild

ci: ## Run full CI build (target=ci, with test DB init + clean state)
	python3 scripts/init_test_db.py --db-path "$(DBT_RAW_DB)"
	$(MAKE) clean
	$(MAKE) deps
	$(MAKE) build DBT_TARGET=ci

# Nota: make build/test/run/deps executam dbt de dentro do diretório dbt/.
# Isso é necessário porque dbt 1.11 não tem suporte a --project-dir.  

shell: ## Open DuckDB shell on the dbt database (dev target)
	@DB_FILE=$$(grep -A1 '$(DBT_TARGET):' $(DBT_PROFILES_DIR)/profiles.yml | tail -1 | awk '{print $$2}' | sed 's/"//g'); \
	if [ -n "$$DB_FILE" ] && [ -f "$(DBT_DIR)/$$DB_FILE" ]; then \
		echo "Opening $(DBT_DIR)/$$DB_FILE..."; \
		duckdb "$(DBT_DIR)/$$DB_FILE"; \
	elif [ -n "$${DBT_DUCKDB_PATH}" ]; then \
		echo "Opening $${DBT_DUCKDB_PATH}..."; \
		duckdb "$${DBT_DUCKDB_PATH}"; \
	else \
		echo "Could not find DB path. Set DBT_DUCKDB_PATH or place .duckdb in $(DBT_DIR)/"; \
	fi
