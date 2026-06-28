-- Sales over time
SELECT d.month, d.year, SUM(f.sales_amount) AS total_sales
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.date_key
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- Sales by category
SELECT p.category, SUM(f.sales_amount) AS total_sales
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.category
ORDER BY total_sales DESC;

-- Sales by store/country
SELECT s.store_name, SUM(f.sales_amount) AS total_sales
FROM fact_sales f
JOIN dim_store s ON s.store_key = f.store_key
GROUP BY s.store_name
ORDER BY total_sales DESC;

-- Top products
SELECT p.stock_code, p.product_name, SUM(f.quantity) AS units_sold, SUM(f.sales_amount) AS total_sales
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.stock_code, p.product_name
ORDER BY total_sales DESC
LIMIT 20;
