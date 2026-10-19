-- ============================================================================
-- Query 1: Executive Sales KPIs
-- Purpose: Compute high-level business performance metrics with explicit grains.
-- Business Logic:
--   - Delivered GMV explicitly filters on order_status = 'delivered'
--   - Delivered AOV = Delivered GMV / Delivered Orders
--   - Cancellation Rate = Canceled Orders / Total Eligible Orders
-- Dialect: ANSI SQL / PostgreSQL / DuckDB
-- ============================================================================

WITH order_metrics AS (
    SELECT
        COUNT(order_id) AS total_orders,
        COUNT(CASE WHEN order_status = 'delivered' THEN 1 END) AS delivered_orders,
        COUNT(CASE WHEN order_status = 'canceled' THEN 1 END) AS canceled_orders,
        COUNT(CASE WHEN order_status = 'shipped' THEN 1 END) AS shipped_orders,
        COUNT(CASE WHEN order_status = 'unavailable' THEN 1 END) AS unavailable_orders,
        
        -- Monetary totals
        SUM(CASE WHEN order_status = 'delivered' THEN merchandise_value ELSE 0 END) AS delivered_merchandise_value,
        SUM(CASE WHEN order_status = 'delivered' THEN freight_value ELSE 0 END) AS delivered_freight_value,
        SUM(CASE WHEN order_status = 'delivered' THEN total_order_value ELSE 0 END) AS delivered_total_gross_value,
        
        -- All-order gross volume (for reconciliation disclosure)
        SUM(merchandise_value) AS total_recorded_merchandise_value,
        SUM(freight_value) AS total_recorded_freight_value,
        
        -- Delivery timeliness (delivered orders with valid delivery timestamps only)
        COUNT(CASE WHEN order_status = 'delivered' AND is_delivered_on_time IS NOT NULL THEN 1 END) AS delivered_evaluable_orders,
        COUNT(CASE WHEN order_status = 'delivered' AND is_delivered_on_time = 1 THEN 1 END) AS on_time_orders,
        
        -- Review score aggregate
        AVG(review_score) AS average_review_score,
        COUNT(CASE WHEN review_score IN (1, 2) THEN 1 END) AS low_review_orders,
        COUNT(CASE WHEN review_score IS NOT NULL THEN 1 END) AS reviewed_orders
    FROM fact_order
)
SELECT
    total_orders,
    delivered_orders,
    canceled_orders,
    
    -- Calculated KPI rates
    ROUND((canceled_orders * 100.0) / NULLIF(total_orders, 0), 2) AS cancellation_rate_pct,
    ROUND(delivered_merchandise_value, 2) AS delivered_gmv_brl,
    ROUND(delivered_freight_value, 2) AS delivered_freight_brl,
    ROUND(delivered_total_gross_value, 2) AS delivered_total_value_brl,
    
    -- Average Order Value
    ROUND(delivered_merchandise_value / NULLIF(delivered_orders, 0), 2) AS delivered_aov_brl,
    
    -- On-Time Delivery Rate
    ROUND((on_time_orders * 100.0) / NULLIF(delivered_evaluable_orders, 0), 2) AS on_time_delivery_rate_pct,
    
    -- Customer Satisfaction
    ROUND(average_review_score, 2) AS overall_avg_review_score,
    ROUND((low_review_orders * 100.0) / NULLIF(reviewed_orders, 0), 2) AS low_review_rate_pct
FROM order_metrics;
