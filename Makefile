.PHONY: install install-dev format lint test ci etl reset-state docker-up docker-down airflow-init

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -r requirements.txt

install-dev:
	$(PYTHON) -m pip install -r requirements-dev.txt

format:
	$(PYTHON) -m black etl dags tests
	$(PYTHON) -m ruff check etl dags tests --fix

lint:
	$(PYTHON) -m ruff check etl dags tests
	$(PYTHON) -m black --check etl dags tests

test:
	$(PYTHON) -m pytest -q

ci: lint test

etl:
	$(PYTHON) -m etl.cli run

reset-state:
	rm -f data/processed/incremental_state.json

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v

airflow-init:
	docker compose up airflow-init
