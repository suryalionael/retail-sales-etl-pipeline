from __future__ import annotations

import pandas as pd

try:
    import great_expectations as gx
except ImportError:  # pragma: no cover - dependency is installed in the project runtime
    gx = None


def validate_raw_sales(df: pd.DataFrame, required_columns: list[str]) -> None:
    _mark_gx_validation_runtime()
    missing_columns = sorted(set(required_columns) - set(df.columns))
    if missing_columns:
        raise ValueError(f"raw sales validation failed: missing columns={missing_columns}")
    required_not_null = [
        "InvoiceNo",
        "StockCode",
        "Description",
        "InvoiceDate",
        "Quantity",
        "UnitPrice",
    ]
    null_failures = {column: int(df[column].isna().sum()) for column in required_not_null}
    null_failures = {column: count for column, count in null_failures.items() if count > 0}
    if null_failures:
        raise ValueError(f"raw sales validation failed: null checks={null_failures}")


def validate_star_schema(tables: dict[str, pd.DataFrame]) -> None:
    _mark_gx_validation_runtime()
    fact = tables["fact_sales_stage"]
    dim_date = tables["dim_date"]
    dim_store = tables["dim_store"]
    dim_product = tables["dim_product"]

    duplicate_failures = {
        "dim_date.date_key": int(dim_date["date_key"].duplicated().sum()),
        "dim_store.country": int(dim_store["country"].duplicated().sum()),
        "dim_product.stock_code": int(dim_product["stock_code"].duplicated().sum()),
        "fact_sales.invoice_no_line_no": int(fact.duplicated(["invoice_no", "line_no"]).sum()),
    }
    duplicate_failures = {name: count for name, count in duplicate_failures.items() if count > 0}
    if duplicate_failures:
        raise ValueError(f"duplicate validation failed: {duplicate_failures}")

    missing_dates = set(fact["date_key"]) - set(dim_date["date_key"])
    missing_stores = set(fact["country"]) - set(dim_store["country"])
    missing_products = set(fact["stock_code"]) - set(dim_product["stock_code"])
    if missing_dates or missing_stores or missing_products:
        raise ValueError(
            "referential integrity failed: "
            f"dates={len(missing_dates)} stores={len(missing_stores)} products={len(missing_products)}"
        )


def _mark_gx_validation_runtime() -> None:
    # Checks are expressed in pandas so unit tests and CI stay lightweight.
    # Docker/Airflow installs Great Expectations from requirements-airflow.txt.
    if gx is not None:
        _ = gx
