# Power BI Dashboard

Connect Power BI Desktop to PostgreSQL:

- Server: `localhost:5432`
- Database: `retail_warehouse`
- Mode: Import or DirectQuery
- Tables: `fact_sales`, `dim_date`, `dim_store`, `dim_product`

Recommended visuals:

- Line chart: `dim_date.full_date` vs `SUM(fact_sales.sales_amount)`
- Bar chart: `dim_product.category` vs `SUM(fact_sales.sales_amount)`
- Map or bar chart: `dim_store.store_name` vs `SUM(fact_sales.sales_amount)`
- Table/bar chart: top `dim_product.product_name` by `SUM(fact_sales.sales_amount)`

The repository keeps instructions instead of a `.pbix` binary so the dashboard can be recreated and connected to the local warehouse without committing large proprietary artifacts.
