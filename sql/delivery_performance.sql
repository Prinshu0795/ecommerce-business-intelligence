-- ============================================================================
-- Query 6: Delivery Logistics Performance & State Latency
-- Purpose: Analyze on-time delivery rates, lead-time breakdown, and regional delivery delays.
-- Denominator Rules:
--   - On-time delivery rate excludes records without both actual and estimated delivery timestamps.
-- Dialect: ANSI SQL / PostgreSQL / DuckDB
-- ============================================================================

-- Part A: Overall Logistics Lead Times
SELECT
    COUNT(*) AS delivered_evaluable_orders,
    COUNT(CASE WHEN is_delivered_on_time = 1 THEN 1 END) AS on_time_orders,
    COUNT(CASE WHEN is_delivered_on_time = 0 THEN 1 END) AS delayed_orders,
    
    -- Rates
    ROUND(
        COUNT(CASE WHEN is_delivered_on_time = 1 THEN 1 END) * 100.0 / COUNT(*), 
        2
    ) AS on_time_delivery_rate_pct,
    ROUND(
        COUNT(CASE WHEN is_delivered_on_time = 0 THEN 1 END) * 100.0 / COUNT(*), 
        2
    ) AS late_delivery_rate_pct,
    
    -- Lead Times Breakdown (Averages)
    ROUND(AVG(approval_duration_hours), 1) AS avg_approval_hours,
    ROUND(AVG(carrier_duration_days), 1) AS avg_carrier_transit_days,
    ROUND(AVG(delivery_duration_days), 1) AS avg_total_delivery_days,
    ROUND(AVG(estimated_duration_days), 1) AS avg_estimated_delivery_days,
    
    -- Average Delay: Negative = Days Early, Positive = Days Late
    ROUND(AVG(delivery_delay_days), 2) AS overall_avg_delay_days,
    ROUND(AVG(CASE WHEN delivery_delay_days > 0 THEN delivery_delay_days END), 2) AS avg_days_late_when_delayed,
    ROUND(AVG(CASE WHEN delivery_delay_days <= 0 THEN delivery_delay_days END), 2) AS avg_days_early_when_ontime
FROM fact_order
WHERE order_status = 'delivered'
  AND is_delivered_on_time IS NOT NULL;

-- Part B: State-Level Logistics Latency (Destination Customer State)
SELECT
    c.customer_state,
    COUNT(o.order_id) AS total_delivered_orders,
    ROUND(AVG(o.delivery_duration_days), 1) AS avg_delivery_days,
    ROUND(AVG(o.estimated_duration_days), 1) AS avg_estimated_days,
    ROUND(AVG(o.delivery_delay_days), 2) AS avg_delay_relative_to_estimate,
    ROUND(AVG(o.is_delivered_on_time) * 100.0, 2) AS on_time_rate_pct,
    ROUND(AVG(o.review_score), 2) AS state_avg_review_score
FROM fact_order o
JOIN dim_customer c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
  AND o.is_delivered_on_time IS NOT NULL
GROUP BY c.customer_state
HAVING COUNT(o.order_id) >= 50
ORDER BY avg_delivery_days DESC;
