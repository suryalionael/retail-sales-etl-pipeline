from __future__ import annotations

import pandas as pd
import pytest
from etl.transform import apply_incremental_filter, update_incremental_state
from etl.validate import validate_raw_sales, validate_star_schema


def _raw_sales() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "InvoiceNo": ["1001"],
            "StockCode": ["A1"],
            "Description": ["RED MUG"],
            "Quantity": [1],
            "InvoiceDate": pd.to_datetime(["2024-01-01"]),
            "UnitPrice": [5.0],
            "CustomerID": [12345],
            "Country": ["United Kingdom"],
        }
    )


def test_validate_raw_sales_passes_with_required_columns() -> None:
    validate_raw_sales(_raw_sales(), list(_raw_sales().columns))


def test_validate_raw_sales_fails_on_missing_columns() -> None:
    df = _raw_sales().drop(columns=["Country"])
    with pytest.raises(ValueError, match="missing columns"):
        validate_raw_sales(df, list(_raw_sales().columns))


def test_validate_raw_sales_fails_on_null_required_fields() -> None:
    df = _raw_sales()
    df.loc[0, "InvoiceNo"] = None
    with pytest.raises(ValueError, match="null checks"):
        validate_raw_sales(df, list(_raw_sales().columns))


def test_validate_star_schema_fails_on_duplicate_fact_keys() -> None:
    fact = pd.DataFrame(
        {
            "invoice_no": ["1001", "1001"],
            "line_no": [1, 1],
            "invoice_ts": pd.to_datetime(["2024-01-01", "2024-01-01"]),
            "date_key": [20240101, 20240101],
            "country": ["United Kingdom", "United Kingdom"],
            "stock_code": ["A1", "A1"],
            "customer_id": ["12345", "12345"],
            "quantity": [1, 1],
            "unit_price": [5.0, 5.0],
            "sales_amount": [5.0, 5.0],
        }
    )
    tables = {
        "dim_date": pd.DataFrame({"date_key": [20240101]}),
        "dim_store": pd.DataFrame({"country": ["United Kingdom"]}),
        "dim_product": pd.DataFrame({"stock_code": ["A1"]}),
        "fact_sales_stage": fact,
    }
    with pytest.raises(ValueError, match="duplicate validation failed"):
        validate_star_schema(tables)


def test_incremental_filter_returns_no_rows_after_successful_batch(tmp_path) -> None:
    df = pd.DataFrame({"InvoiceDate": pd.to_datetime(["2024-01-01", "2024-01-02"])})
    state_file = tmp_path / "state.json"
    update_incremental_state(df, state_file)

    assert apply_incremental_filter(df, state_file).empty


def test_empty_incremental_batch_does_not_advance_state(tmp_path) -> None:
    df = pd.DataFrame({"InvoiceDate": pd.to_datetime(["2024-01-01"])})
    state_file = tmp_path / "state.json"
    update_incremental_state(df, state_file)
    original_state = state_file.read_text(encoding="utf-8")

    update_incremental_state(
        pd.DataFrame({"InvoiceDate": pd.Series(dtype="datetime64[ns]")}), state_file
    )

    assert state_file.read_text(encoding="utf-8") == original_state
