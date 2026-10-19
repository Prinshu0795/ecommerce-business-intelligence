-- ============================================================================
-- Query 10: Order Status Funnel & Payment Method Analytics
-- Purpose: Evaluate order fulfillment completion rates, cancellation drivers,
--          and payment installment adoption.
-- Dialect: ANSI SQL / PostgreSQL / DuckDB
-- ============================================================================

-- Part A: Order Lifecycle & Status Distribution
SELECT
    order_status,
    COUNT(order_id) AS total_orders,
    ROUND(COUNT(order_id) * 100.0 / SUM(COUNT(order_id)) OVER (), 2) AS status_share_pct,
    ROUND(SUM(merchandise_value), 2) AS gross_merchandise_value_brl,
    ROUND(AVG(merchandise_value), 2) AS avg_order_value_brl
FROM fact_order
GROUP BY order_status
ORDER BY total_orders DESC;

-- Part B: Payment Method Breakdown & Financing Depth
SELECT
    payment_type,
    COUNT(DISTINCT order_id) AS distinct_orders_paid,
    COUNT(*) AS total_payment_transactions,
    ROUND(SUM(payment_value), 2) AS total_payment_value_brl,
    ROUND(
        SUM(payment_value) * 100.0 / SUM(SUM(payment_value)) OVER (), 
        2
    ) AS payment_value_share_pct,
    ROUND(AVG(payment_value), 2) AS avg_transaction_amount_brl,
    ROUND(AVG(payment_installments), 1) AS avg_installments_count,
    MAX(payment_installments) AS max_installments_count
FROM fact_payment
GROUP BY payment_type
ORDER BY total_payment_value_brl DESC;

-- Part C: Cancellation Timing and Lead Time to Cancel
SELECT
    c.customer_state,
    COUNT(o.order_id) AS total_canceled_orders,
    ROUND(
        COUNT(o.order_id) * 100.0 / 
        (SELECT COUNT(*) FROM fact_order WHERE order_status = 'canceled'), 
        2
    ) AS state_share_of_all_cancellations_pct,
    ROUND(AVG(o.merchandise_value), 2) AS avg_canceled_order_value_brl
FROM fact_order o
JOIN dim_customer c ON o.customer_id = c.customer_id
WHERE o.order_status = 'canceled'
GROUP BY c.customer_state
ORDER BY total_canceled_orders DESC
LIMIT 10;
