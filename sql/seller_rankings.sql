-- ============================================================================
-- Query 7: Marketplace Seller Performance & Quality Leaderboard
-- Purpose: Rank sellers by revenue, fulfillment speed, on-time rate, and review ratings.
-- Minimum Sample Size: HAVING COUNT(DISTINCT oi.order_id) >= 10 (filters out low-volume noise)
-- Advanced Techniques: Multi-table joins, Window functions (RANK), Conditional Aggregation
-- Dialect: ANSI SQL / PostgreSQL / DuckDB
-- ============================================================================

WITH seller_orders AS (
    SELECT
        s.seller_id,
        s.seller_state,
        s.seller_city,
        oi.order_id,
        oi.order_item_id,
        oi.price,
        oi.shipping_limit_date,
        o.order_delivered_carrier_date,
        o.is_delivered_on_time,
        o.delivery_delay_days,
        o.review_score,
        -- Check if seller dispatched to carrier before shipping limit date
        CASE 
            WHEN o.order_delivered_carrier_date IS NOT NULL AND oi.shipping_limit_date IS NOT NULL THEN
                CASE WHEN o.order_delivered_carrier_date <= oi.shipping_limit_date THEN 1 ELSE 0 END
            ELSE NULL
        END AS is_dispatched_on_time
    FROM dim_seller s
    JOIN fact_order_item oi ON s.seller_id = oi.seller_id
    JOIN fact_order o ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
),
seller_aggregates AS (
    SELECT
        seller_id,
        seller_state,
        seller_city,
        COUNT(DISTINCT order_id) AS total_orders_fulfilled,
        COUNT(order_item_id) AS total_units_sold,
        ROUND(SUM(price), 2) AS total_merchandise_value_brl,
        ROUND(AVG(price), 2) AS avg_item_price_brl,
        ROUND(AVG(is_dispatched_on_time) * 100.0, 2) AS seller_on_time_dispatch_rate_pct,
        ROUND(AVG(is_delivered_on_time) * 100.0, 2) AS customer_on_time_delivery_rate_pct,
        ROUND(AVG(delivery_delay_days), 2) AS avg_delivery_delay_days,
        ROUND(AVG(review_score), 2) AS avg_seller_review_score
    FROM seller_orders
    GROUP BY seller_id, seller_state, seller_city
    HAVING COUNT(DISTINCT order_id) >= 10  -- Enforce minimum statistical sample size
)
SELECT
    RANK() OVER (ORDER BY total_merchandise_value_brl DESC) AS revenue_rank,
    DENSE_RANK() OVER (ORDER BY avg_seller_review_score DESC, total_orders_fulfilled DESC) AS quality_rank,
    seller_id,
    seller_state,
    seller_city,
    total_orders_fulfilled,
    total_units_sold,
    total_merchandise_value_brl,
    avg_item_price_brl,
    seller_on_time_dispatch_rate_pct,
    customer_on_time_delivery_rate_pct,
    avg_delivery_delay_days,
    avg_seller_review_score
FROM seller_aggregates
ORDER BY revenue_rank ASC;
