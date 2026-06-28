from __future__ import annotations

import argparse
from pathlib import Path

from etl.config import database_url, load_config
from etl.extract import download_dataset
from etl.load import get_engine, load_star_schema, run_ddl
from etl.logging_utils import get_logger
from etl.quality import run_warehouse_quality_checks
from etl.transform import (
    apply_incremental_filter,
    build_dimensions_and_fact,
    clean_sales,
    read_source_excel,
    update_incremental_state,
)
from etl.validate import validate_raw_sales, validate_star_schema

logger = get_logger(__name__)


def run_pipeline() -> None:
    config = load_config()
    dataset_config = config["dataset"]
    paths = config["paths"]

    extract_dir = download_dataset(
        dataset_config["url"],
        dataset_config["archive_path"],
        dataset_config["extract_dir"],
    )
    source_files = sorted(Path(extract_dir).glob(dataset_config["source_file_pattern"]))
    if not source_files:
        raise FileNotFoundError(f"No source files found in {extract_dir}")

    raw_df = read_source_excel(source_files[0])
    validate_raw_sales(raw_df, config["quality"]["required_columns"])
    clean_df = clean_sales(raw_df)
    incremental_df = apply_incremental_filter(clean_df, paths["incremental_state_file"])
    tables = build_dimensions_and_fact(incremental_df)
    validate_star_schema(tables)

    engine = get_engine(database_url())
    run_ddl(engine)
    load_star_schema(engine, tables, config["warehouse"]["batch_size"])
    run_warehouse_quality_checks(engine)
    update_incremental_state(incremental_df, paths["incremental_state_file"])
    logger.info("ETL pipeline completed successfully with %s rows", len(incremental_df))


def main() -> None:
    parser = argparse.ArgumentParser(description="Retail sales ETL pipeline")
    parser.add_argument("command", choices=["run"])
    args = parser.parse_args()
    if args.command == "run":
        run_pipeline()


if __name__ == "__main__":
    main()
