from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PRODUCT_CATEGORY_RULES = {
    "POSTAGE": ("postage",),
    "BAGS": ("bag",),
    "HOMEWARE": ("holder", "box", "sign", "clock", "frame", "rack"),
    "DECOR": ("heart", "decoration", "garland", "candle", "light"),
    "KITCHEN": ("kitchen", "cake", "mug", "teapot", "plate", "bowl"),
    "STATIONERY": ("card", "paper", "pencil", "notebook", "wrap"),
    "APPAREL": ("jumbo", "shirt", "scarf", "hat"),
}


def read_source_excel(source_path: Path | str) -> pd.DataFrame:
    return pd.read_excel(source_path, engine="openpyxl")


def clean_sales(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.copy()
    df.columns = [str(column).strip() for column in df.columns]
    df = df.dropna(subset=["InvoiceNo", "StockCode", "Description", "InvoiceDate", "UnitPrice"])
    df = df[df["Quantity"] > 0]
    df = df[df["UnitPrice"] > 0]
    df = df[~df["InvoiceNo"].astype(str).str.startswith("C", na=False)]
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df = df.dropna(subset=["InvoiceDate"])
    df["CustomerID"] = df["CustomerID"].astype("Int64").astype(str).replace("<NA>", None)
    df["InvoiceNo"] = df["InvoiceNo"].astype(str)
    df["StockCode"] = df["StockCode"].astype(str)
    df["Description"] = df["Description"].astype(str).str.strip()
    df["Country"] = df["Country"].astype(str).str.strip()
    df = df.sort_values(["InvoiceDate", "InvoiceNo", "StockCode"]).reset_index(drop=True)
    df["line_no"] = df.groupby("InvoiceNo").cumcount() + 1
    df["sales_amount"] = df["Quantity"] * df["UnitPrice"]
    return df


def apply_incremental_filter(df: pd.DataFrame, state_file: Path | str) -> pd.DataFrame:
    path = Path(state_file)
    if not path.exists():
        return df
    state = json.loads(path.read_text(encoding="utf-8"))
    last_invoice_ts = state.get("last_invoice_ts")
    if not last_invoice_ts:
        return df
    return df[df["InvoiceDate"] > pd.Timestamp(last_invoice_ts)].copy()


def update_incremental_state(df: pd.DataFrame, state_file: Path | str) -> None:
    if df.empty:
        return
    path = Path(state_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    ts_column = "InvoiceDate" if "InvoiceDate" in df.columns else "invoice_ts"
    state = {"last_invoice_ts": df[ts_column].max().isoformat()}
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def categorize_product(description: str, stock_code: str) -> str:
    text = f"{stock_code} {description}".lower()
    for category, keywords in PRODUCT_CATEGORY_RULES.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "OTHER"


def build_dimensions_and_fact(clean_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = clean_df.copy()
    df["date_key"] = df["InvoiceDate"].dt.strftime("%Y%m%d").astype(int)
    df["full_date"] = df["InvoiceDate"].dt.date
    df["category"] = [
        categorize_product(description, stock_code)
        for description, stock_code in zip(df["Description"], df["StockCode"], strict=False)
    ]

    dim_date = (
        df[["date_key", "full_date"]]
        .drop_duplicates()
        .assign(
            full_date=lambda item: pd.to_datetime(item["full_date"]),
            year=lambda item: item["full_date"].dt.year,
            quarter=lambda item: item["full_date"].dt.quarter,
            month=lambda item: item["full_date"].dt.month,
            month_name=lambda item: item["full_date"].dt.month_name(),
            day=lambda item: item["full_date"].dt.day,
            day_of_week=lambda item: item["full_date"].dt.dayofweek + 1,
            day_name=lambda item: item["full_date"].dt.day_name(),
            week_of_year=lambda item: item["full_date"].dt.isocalendar().week.astype(int),
        )
        .sort_values("date_key")
    )

    dim_store = (
        df[["Country"]]
        .drop_duplicates()
        .rename(columns={"Country": "country"})
        .assign(store_name=lambda item: "Online - " + item["country"], channel="Online")
        .sort_values("country")
        .reset_index(drop=True)
    )

    dim_product = (
        df[["StockCode", "Description", "category"]]
        .drop_duplicates("StockCode")
        .rename(columns={"StockCode": "stock_code", "Description": "product_name"})
        .sort_values("stock_code")
        .reset_index(drop=True)
    )

    fact_sales = df[
        [
            "InvoiceNo",
            "line_no",
            "InvoiceDate",
            "date_key",
            "Country",
            "StockCode",
            "CustomerID",
            "Quantity",
            "UnitPrice",
            "sales_amount",
        ]
    ].rename(
        columns={
            "InvoiceNo": "invoice_no",
            "InvoiceDate": "invoice_ts",
            "Country": "country",
            "StockCode": "stock_code",
            "CustomerID": "customer_id",
            "Quantity": "quantity",
            "UnitPrice": "unit_price",
        }
    )

    return {
        "dim_date": dim_date,
        "dim_store": dim_store,
        "dim_product": dim_product,
        "fact_sales_stage": fact_sales,
    }
