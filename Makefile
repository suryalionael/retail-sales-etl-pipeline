.PHONY: install format lint test etl docker-up docker-down airflow-init

install:
	python -m pip install -r requirements.txt

format:
	black etl dags tests
	ruff check etl dags tests --fix

lint:
	ruff check etl dags tests
	black --check etl dags tests

test:
	pytest -q

etl:
	python -m etl.cli run

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v

airflow-init:
	docker compose up airflow-init
