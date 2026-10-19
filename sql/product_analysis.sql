-- ============================================================================
-- Query 3: Product Category & Pareto Analysis
-- Purpose: Quantify category revenue contribution, 80/20 Pareto distribution,
--          and top-selling products per category.
-- Advanced Techniques: CTEs, SUM() OVER (), DENSE_RANK() OVER (PARTITION BY ...)
-- Dialect: ANSI SQL / PostgreSQL / DuckDB
-- ============================================================================

-- Part A: Category Performance & Pareto 80/20 Curve
WITH category_sales AS (
    SELECT 
        COALESCE(p.product_category_name_english, 'Other Or Unlabeled') AS category_name,
        COUNT(DISTINCT oi.order_id) AS distinct_orders,
        COUNT(oi.order_item_id) AS total_items_sold,
        ROUND(SUM(oi.price), 2) AS category_revenue,
        ROUND(SUM(oi.freight_value), 2) AS category_freight,
        ROUND(AVG(oi.price), 2) AS avg_item_price
    FROM fact_order_item oi
    JOIN fact_order o ON oi.order_id = o.order_id
    JOIN dim_product p ON oi.product_id = p.product_id
    WHERE o.order_status = 'delivered'
    GROUP BY p.product_category_name_english
),
category_ranking AS (
    SELECT
        category_name,
        distinct_orders,
        total_items_sold,
        category_revenue,
        category_freight,
        avg_item_price,
        ROUND(category_revenue * 100.0 / SUM(category_revenue) OVER (), 2) AS revenue_share_pct,
        ROUND(
            SUM(category_revenue) OVER (
                ORDER BY category_revenue DESC 
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) * 100.0 / SUM(category_revenue) OVER (),
            2
        ) AS cumulative_revenue_share_pct,
        RANK() OVER (ORDER BY category_revenue DESC) AS category_rank
    FROM category_sales
)
SELECT 
    category_rank,
    category_name,
    distinct_orders,
    total_items_sold,
    category_revenue,
    revenue_share_pct,
    cumulative_revenue_share_pct,
    CASE 
        WHEN cumulative_revenue_share_pct <= 80.0 THEN 'Core 80% (Pareto Head)'
        ELSE 'Long Tail (Pareto Tail)'
    END AS pareto_classification
FROM category_ranking
ORDER BY category_rank ASC;

-- Part B: Top 3 Revenue-Generating Products Per Category (Rank Partitioning)
WITH product_sales AS (
    SELECT
        COALESCE(p.product_category_name_english, 'Other Or Unlabeled') AS category_name,
        p.product_id,
        COUNT(oi.order_item_id) AS units_sold,
        ROUND(SUM(oi.price), 2) AS product_revenue,
        ROUND(AVG(oi.price), 2) AS avg_unit_price
    FROM fact_order_item oi
    JOIN fact_order o ON oi.order_id = o.order_id
    JOIN dim_product p ON oi.product_id = p.product_id
    WHERE o.order_status = 'delivered'
    GROUP BY p.product_category_name_english, p.product_id
),
ranked_products AS (
    SELECT
        category_name,
        product_id,
        units_sold,
        product_revenue,
        avg_unit_price,
        DENSE_RANK() OVER (
            PARTITION BY category_name 
            ORDER BY product_revenue DESC
        ) AS rank_in_category
    FROM product_sales
)
SELECT
    category_name,
    rank_in_category,
    product_id,
    units_sold,
    product_revenue,
    avg_unit_price
FROM ranked_products
WHERE rank_in_category <= 3
ORDER BY category_name ASC, rank_in_category ASC;
