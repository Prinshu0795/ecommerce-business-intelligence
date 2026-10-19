-- ============================================================================
-- Query 4: Customer Cohort Retention & Repeat Purchase Analysis
-- Purpose: Track customer acquisition cohorts and monthly retention rates over time.
-- Advanced Techniques: Multi-CTE, Window Functions, Date Arithmetic, Pivot/Aggregation
-- Dialect: ANSI SQL / PostgreSQL / DuckDB
-- ============================================================================

-- Step 1: Identify each customer's first purchase month (Cohort Month)
WITH customer_orders AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        o.order_purchase_timestamp,
        d.year_month AS order_year_month,
        d.year AS order_year,
        d.month AS order_month
    FROM fact_order o
    JOIN dim_customer c ON o.customer_id = c.customer_id
    JOIN dim_date d ON o.order_purchase_date_id = d.date_id
    WHERE o.order_status = 'delivered'
),
customer_cohorts AS (
    SELECT
        customer_unique_id,
        MIN(order_purchase_timestamp) AS first_order_date,
        MIN(order_year_month) AS cohort_month,
        MIN(order_year) AS cohort_year,
        MIN(order_month) AS cohort_month_num
    FROM customer_orders
    GROUP BY customer_unique_id
),
cohort_activity AS (
    SELECT
        co.customer_unique_id,
        cc.cohort_month,
        co.order_year_month,
        -- Calculate month difference (Cohort Index: 0, 1, 2...)
        (co.order_year - cc.cohort_year) * 12 + (co.order_month - cc.cohort_month_num) AS cohort_index
    FROM customer_orders co
    JOIN customer_cohorts cc ON co.customer_unique_id = cc.customer_unique_id
),
cohort_summary AS (
    SELECT
        cohort_month,
        cohort_index,
        COUNT(DISTINCT customer_unique_id) AS active_customers
    FROM cohort_activity
    GROUP BY cohort_month, cohort_index
),
cohort_base AS (
    SELECT
        cohort_month,
        active_customers AS cohort_size
    FROM cohort_summary
    WHERE cohort_index = 0
)
SELECT
    cs.cohort_month,
    cb.cohort_size,
    cs.cohort_index,
    cs.active_customers,
    ROUND((cs.active_customers * 100.0) / cb.cohort_size, 2) AS retention_rate_pct
FROM cohort_summary cs
JOIN cohort_base cb ON cs.cohort_month = cb.cohort_month
ORDER BY cs.cohort_month ASC, cs.cohort_index ASC;

-- Repeat Purchase Behavior Summary
WITH customer_order_counts AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS order_count,
        ROUND(SUM(o.merchandise_value), 2) AS customer_lifetime_spend
    FROM fact_order o
    JOIN dim_customer c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT
    COUNT(*) AS total_unique_customers,
    COUNT(CASE WHEN order_count = 1 THEN 1 END) AS one_time_buyers,
    COUNT(CASE WHEN order_count >= 2 THEN 1 END) AS repeat_buyers,
    ROUND(COUNT(CASE WHEN order_count >= 2 THEN 1 END) * 100.0 / COUNT(*), 2) AS repeat_customer_rate_pct,
    ROUND(AVG(customer_lifetime_spend), 2) AS overall_avg_clv_brl,
    ROUND(AVG(CASE WHEN order_count >= 2 THEN customer_lifetime_spend END), 2) AS repeat_buyer_avg_clv_brl,
    ROUND(AVG(CASE WHEN order_count = 1 THEN customer_lifetime_spend END), 2) AS one_time_buyer_avg_clv_brl
FROM customer_order_counts;
