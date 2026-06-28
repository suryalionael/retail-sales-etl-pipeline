from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from etl.transform import (
    apply_incremental_filter,
    build_dimensions_and_fact,
    categorize_product,
    clean_sales,
    update_incremental_state,
)
from etl.validate import validate_star_schema


def _raw_sales() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "InvoiceNo": ["1001", "1001", "C1002", "1003"],
            "StockCode": ["A1", "B2", "A1", "C3"],
            "Description": ["RED MUG", "PAPER CARD", "RED MUG", "WOODEN HEART"],
            "Quantity": [2, 1, -1, 3],
            "InvoiceDate": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-03"]),
            "UnitPrice": [5.0, 2.5, 5.0, 4.0],
            "CustomerID": [12345, 12345, 12345, None],
            "Country": ["United Kingdom", "United Kingdom", "France", "France"],
        }
    )


def test_clean_sales_removes_returns_and_calculates_line_amounts() -> None:
    clean = clean_sales(_raw_sales())

    assert list(clean["InvoiceNo"]) == ["1001", "1001", "1003"]
    assert clean["sales_amount"].tolist() == [10.0, 2.5, 12.0]
    assert clean["line_no"].tolist() == [1, 2, 1]


def test_build_dimensions_and_fact_produces_valid_star_schema() -> None:
    tables = build_dimensions_and_fact(clean_sales(_raw_sales()))

    assert set(tables) == {"dim_date", "dim_store", "dim_product", "fact_sales_stage"}
    assert len(tables["dim_store"]) == 2
    assert len(tables["fact_sales_stage"]) == 3
    validate_star_schema(tables)


def test_incremental_state_filters_newer_records(tmp_path: Path) -> None:
    clean = clean_sales(_raw_sales())
    state_file = tmp_path / "state.json"
    update_incremental_state(clean.iloc[:2], state_file)

    incremental = apply_incremental_filter(clean, state_file)

    assert len(incremental) == 1
    assert incremental.iloc[0]["InvoiceNo"] == "1003"


def test_incremental_state_accepts_fact_stage_column(tmp_path: Path) -> None:
    tables = build_dimensions_and_fact(clean_sales(_raw_sales()))
    state_file = tmp_path / "state.json"

    update_incremental_state(tables["fact_sales_stage"], state_file)

    assert json.loads(state_file.read_text(encoding="utf-8"))["last_invoice_ts"]


def test_product_category_rules_are_deterministic() -> None:
    assert categorize_product("RED MUG", "A1") == "KITCHEN"
    assert categorize_product("PAPER CARD", "B2") == "STATIONERY"
    assert categorize_product("UNMATCHED ITEM", "Z9") == "OTHER"
