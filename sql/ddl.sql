CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    week_of_year INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_store (
    store_key BIGSERIAL PRIMARY KEY,
    country VARCHAR(100) NOT NULL UNIQUE,
    store_name VARCHAR(160) NOT NULL,
    channel VARCHAR(40) NOT NULL DEFAULT 'Online'
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_key BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(50) NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    category VARCHAR(80) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_sales (
    sales_key BIGSERIAL PRIMARY KEY,
    invoice_no VARCHAR(50) NOT NULL,
    line_no INTEGER NOT NULL,
    invoice_ts TIMESTAMP NOT NULL,
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
    store_key BIGINT NOT NULL REFERENCES dim_store(store_key),
    product_key BIGINT NOT NULL REFERENCES dim_product(product_key),
    customer_id VARCHAR(50),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12, 4) NOT NULL,
    sales_amount NUMERIC(14, 4) NOT NULL,
    source_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (invoice_no, line_no)
);

CREATE INDEX IF NOT EXISTS idx_fact_sales_invoice_ts ON fact_sales(invoice_ts);
CREATE INDEX IF NOT EXISTS idx_fact_sales_date_key ON fact_sales(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_store_key ON fact_sales(store_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product_key ON fact_sales(product_key);
