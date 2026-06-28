from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from etl.logging_utils import get_logger

logger = get_logger(__name__)


def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, future=True)


def run_ddl(engine: Engine, ddl_path: Path | str = "sql/ddl.sql") -> None:
    ddl = Path(ddl_path).read_text(encoding="utf-8")
    with engine.begin() as connection:
        for statement in [item.strip() for item in ddl.split(";") if item.strip()]:
            connection.execute(text(statement))


def load_star_schema(
    engine: Engine, tables: dict[str, pd.DataFrame], batch_size: int = 5000
) -> None:
    if tables["fact_sales_stage"].empty:
        logger.info("No incremental rows to load")
        return
    with engine.begin() as connection:
        _upsert_dim_date(connection, tables["dim_date"])
        _upsert_dim_store(connection, tables["dim_store"])
        _upsert_dim_product(connection, tables["dim_product"])
        _load_fact(connection, tables["fact_sales_stage"], batch_size)


def _upsert_dim_date(connection, df: pd.DataFrame) -> None:
    rows = df.to_dict("records")
    connection.execute(
        text(
            """
            INSERT INTO dim_date (
                date_key, full_date, year, quarter, month, month_name, day,
                day_of_week, day_name, week_of_year
            )
            VALUES (
                :date_key, :full_date, :year, :quarter, :month, :month_name, :day,
                :day_of_week, :day_name, :week_of_year
            )
            ON CONFLICT (date_key) DO NOTHING
            """
        ),
        rows,
    )


def _upsert_dim_store(connection, df: pd.DataFrame) -> None:
    connection.execute(
        text(
            """
            INSERT INTO dim_store (country, store_name, channel)
            VALUES (:country, :store_name, :channel)
            ON CONFLICT (country) DO UPDATE
            SET store_name = EXCLUDED.store_name,
                channel = EXCLUDED.channel
            """
        ),
        df.to_dict("records"),
    )


def _upsert_dim_product(connection, df: pd.DataFrame) -> None:
    connection.execute(
        text(
            """
            INSERT INTO dim_product (stock_code, product_name, category)
            VALUES (:stock_code, :product_name, :category)
            ON CONFLICT (stock_code) DO UPDATE
            SET product_name = EXCLUDED.product_name,
                category = EXCLUDED.category
            """
        ),
        df.to_dict("records"),
    )


def _load_fact(connection, fact_df: pd.DataFrame, batch_size: int) -> None:
    staged = fact_df.copy()
    staged.to_sql(
        "_fact_sales_stage",
        connection,
        if_exists="replace",
        index=False,
        chunksize=batch_size,
        method="multi",
    )
    connection.execute(
        text(
            """
            INSERT INTO fact_sales (
                invoice_no, line_no, invoice_ts, date_key, store_key, product_key,
                customer_id, quantity, unit_price, sales_amount
            )
            SELECT
                st.invoice_no,
                st.line_no,
                st.invoice_ts,
                st.date_key,
                ds.store_key,
                dp.product_key,
                st.customer_id,
                st.quantity,
                st.unit_price,
                st.sales_amount
            FROM _fact_sales_stage st
            JOIN dim_store ds ON ds.country = st.country
            JOIN dim_product dp ON dp.stock_code = st.stock_code
            ON CONFLICT (invoice_no, line_no) DO UPDATE
            SET invoice_ts = EXCLUDED.invoice_ts,
                date_key = EXCLUDED.date_key,
                store_key = EXCLUDED.store_key,
                product_key = EXCLUDED.product_key,
                customer_id = EXCLUDED.customer_id,
                quantity = EXCLUDED.quantity,
                unit_price = EXCLUDED.unit_price,
                sales_amount = EXCLUDED.sales_amount,
                source_updated_at = CURRENT_TIMESTAMP
            """
        )
    )
    connection.execute(text("DROP TABLE IF EXISTS _fact_sales_stage"))
