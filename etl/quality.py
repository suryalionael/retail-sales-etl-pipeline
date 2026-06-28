from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def run_warehouse_quality_checks(engine: Engine) -> None:
    checks = {
        "fact rows": "SELECT COUNT(*) FROM fact_sales",
        "missing dates": """
            SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_date d ON d.date_key = f.date_key
            WHERE d.date_key IS NULL
        """,
        "missing stores": """
            SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_store s ON s.store_key = f.store_key
            WHERE s.store_key IS NULL
        """,
        "missing products": """
            SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_product p ON p.product_key = f.product_key
            WHERE p.product_key IS NULL
        """,
        "duplicate facts": """
            SELECT COUNT(*) FROM (
                SELECT invoice_no, line_no
                FROM fact_sales
                GROUP BY invoice_no, line_no
                HAVING COUNT(*) > 1
            ) duplicates
        """,
        "null measures": """
            SELECT COUNT(*) FROM fact_sales
            WHERE quantity IS NULL OR unit_price IS NULL OR sales_amount IS NULL
        """,
    }

    with engine.begin() as connection:
        for name, sql in checks.items():
            value = connection.execute(text(sql)).scalar_one()
            if name == "fact rows" and value == 0:
                raise ValueError("warehouse quality failed: fact_sales is empty")
            if name != "fact rows" and value != 0:
                raise ValueError(f"warehouse quality failed: {name}={value}")
