-- ============================================================================
-- Query 9: Geographic Regional Sales & Logistics Flow Analysis
-- Purpose: Analyze demand concentration by Brazilian state and inter-state trade flows.
-- Dialect: ANSI SQL / PostgreSQL / DuckDB
-- ============================================================================

-- Part A: Customer State Demand Concentration
SELECT
    c.customer_state,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT c.customer_unique_id) AS unique_customers,
    ROUND(SUM(o.merchandise_value), 2) AS state_gmv_brl,
    ROUND(SUM(o.freight_value), 2) AS state_freight_brl,
    ROUND(
        SUM(o.merchandise_value) * 100.0 / SUM(SUM(o.merchandise_value)) OVER (), 
        2
    ) AS gmv_share_pct,
    ROUND(
        SUM(o.merchandise_value) / NULLIF(COUNT(DISTINCT o.order_id), 0), 
        2
    ) AS state_aov_brl,
    ROUND(AVG(o.is_delivered_on_time) * 100.0, 2) AS state_on_time_rate_pct,
    ROUND(AVG(o.delivery_duration_days), 1) AS state_avg_delivery_duration_days
FROM fact_order o
JOIN dim_customer c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY state_gmv_brl DESC;

-- Part B: Intra-State vs Inter-State Shipping Performance
WITH order_shipping_routes AS (
    SELECT
        o.order_id,
        c.customer_state,
        s.seller_state,
        CASE WHEN c.customer_state = s.seller_state THEN 'Intra-State (Same State)' ELSE 'Inter-State (Cross-Country)' END AS route_type,
        o.delivery_duration_days,
        o.freight_value,
        o.is_delivered_on_time,
        o.review_score
    FROM fact_order o
    JOIN dim_customer c ON o.customer_id = c.customer_id
    JOIN fact_order_item oi ON o.order_id = oi.order_id
    JOIN dim_seller s ON oi.seller_id = s.seller_id
    WHERE o.order_status = 'delivered'
      AND o.delivery_duration_days IS NOT NULL
)
SELECT
    route_type,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(AVG(freight_value), 2) AS avg_freight_cost_brl,
    ROUND(AVG(delivery_duration_days), 1) AS avg_delivery_days,
    ROUND(AVG(is_delivered_on_time) * 100.0, 2) AS on_time_rate_pct,
    ROUND(AVG(review_score), 2) AS avg_review_score
FROM order_shipping_routes
GROUP BY route_type;
