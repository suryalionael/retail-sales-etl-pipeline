from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pandas as pd
import pendulum
from airflow.decorators import dag, task
from etl.config import database_url, load_config
from etl.extract import download_dataset
from etl.load import get_engine, load_star_schema, run_ddl
from etl.quality import run_warehouse_quality_checks
from etl.transform import (
    apply_incremental_filter,
    build_dimensions_and_fact,
    clean_sales,
    read_source_excel,
    update_incremental_state,
)
from etl.validate import validate_raw_sales, validate_star_schema

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="retail_sales_etl",
    description="Extract, validate, transform, load, and quality-check real retail sales data.",
    schedule="@daily",
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["retail", "etl", "warehouse"],
)
def retail_sales_etl():
    @task(task_id="extract")
    def extract() -> str:
        config = load_config()
        extract_dir = download_dataset(
            config["dataset"]["url"],
            config["dataset"]["archive_path"],
            config["dataset"]["extract_dir"],
        )
        source_files = sorted(Path(extract_dir).glob(config["dataset"]["source_file_pattern"]))
        if not source_files:
            raise FileNotFoundError("No extracted retail source file found")
        return str(source_files[0])

    @task(task_id="validate")
    def validate(source_file: str) -> str:
        config = load_config()
        raw_df = read_source_excel(source_file)
        validate_raw_sales(raw_df, config["quality"]["required_columns"])
        return source_file

    @task(task_id="transform")
    def transform(source_file: str) -> dict[str, str]:
        config = load_config()
        processed_dir = Path(config["paths"]["processed_dir"])
        processed_dir.mkdir(parents=True, exist_ok=True)
        raw_df = read_source_excel(source_file)
        clean_df = clean_sales(raw_df)
        incremental_df = apply_incremental_filter(
            clean_df, config["paths"]["incremental_state_file"]
        )
        tables = build_dimensions_and_fact(incremental_df)
        validate_star_schema(tables)
        outputs = {}
        for name, table in tables.items():
            path = processed_dir / f"{name}.parquet"
            table.to_parquet(path, index=False)
            outputs[name] = str(path)
        return outputs

    @task(task_id="load")
    def load(table_paths: dict[str, str]) -> dict[str, str]:
        config = load_config()
        tables = {name: pd.read_parquet(path) for name, path in table_paths.items()}
        engine = get_engine(database_url())
        run_ddl(engine)
        load_star_schema(engine, tables, config["warehouse"]["batch_size"])
        return table_paths

    @task(task_id="quality_check")
    def quality_check(table_paths: dict[str, str]) -> None:
        engine = get_engine(database_url())
        run_warehouse_quality_checks(engine)
        config = load_config()
        fact = pd.read_parquet(table_paths["fact_sales_stage"])
        update_incremental_state(fact, config["paths"]["incremental_state_file"])

    source = extract()
    validated = validate(source)
    transformed = transform(validated)
    loaded = load(transformed)
    quality_check(loaded)


retail_sales_etl()
