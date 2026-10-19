-- ============================================================================
-- Query 5: Customer RFM Segmentation & Value Distribution
-- Purpose: Classify customers by Recency, Frequency, and Monetary scores.
-- Snapshot Date: 2018-10-18 (Fixed reference snapshot for reproducible scoring)
-- Advanced Techniques: NTILE Window Functions, CASE Logic, Conditional Aggregation
-- Dialect: ANSI SQL / PostgreSQL / DuckDB
-- ============================================================================

WITH customer_rfm_raw AS (
    SELECT
        c.customer_unique_id,
        MIN(o.order_purchase_timestamp) AS first_purchase_date,
        MAX(o.order_purchase_timestamp) AS last_purchase_date,
        COUNT(DISTINCT o.order_id) AS frequency,
        ROUND(SUM(o.merchandise_value), 2) AS monetary
    FROM fact_order o
    JOIN dim_customer c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
customer_rfm_metrics AS (
    SELECT
        customer_unique_id,
        first_purchase_date,
        last_purchase_date,
        frequency,
        monetary,
        -- Recency in days relative to snapshot date (2018-10-18)
        ROUND(
            DATE_DIFF('day', CAST(last_purchase_date AS DATE), DATE '2018-10-18'), 
            0
        ) AS recency_days
    FROM customer_rfm_raw
),
customer_scored AS (
    SELECT
        customer_unique_id,
        recency_days,
        frequency,
        monetary,
        
        -- Recency Score: NTILE 1-5 where lowest recency_days gets highest score 5
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        
        -- Frequency Score: Tailored for e-commerce distribution
        CASE 
            WHEN frequency >= 4 THEN 5
            WHEN frequency = 3 THEN 4
            WHEN frequency = 2 THEN 3
            ELSE 1
        END AS f_score,
        
        -- Monetary Score: NTILE 1-5 where highest spend gets score 5
        NTILE(5) OVER (ORDER BY monetary ASC) AS m_score
    FROM customer_rfm_metrics
),
customer_segmented AS (
    SELECT
        customer_unique_id,
        recency_days,
        frequency,
        monetary,
        r_score,
        f_score,
        m_score,
        (CAST(r_score AS VARCHAR) || CAST(f_score AS VARCHAR) || CAST(m_score AS VARCHAR)) AS rfm_code,
        CASE
            WHEN r_score >= 4 AND f_score >= 3 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score >= 1 AND m_score >= 3 THEN 'Potential Loyalists'
            WHEN r_score >= 4 AND f_score = 1 THEN 'New / Recent Customers'
            WHEN r_score = 3 AND f_score = 1 THEN 'Promising / Developing'
            WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 4 THEN 'Cannot Lose Them'
            WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score = 1 AND m_score >= 3 THEN 'About to Sleep'
            WHEN r_score <= 2 AND f_score = 1 AND m_score < 3 THEN 'Hibernating'
            ELSE 'Lost / Inactive'
        END AS rfm_segment
    FROM customer_scored
)
-- Aggregate by Segment
SELECT
    rfm_segment,
    COUNT(customer_unique_id) AS customer_count,
    ROUND(COUNT(customer_unique_id) * 100.0 / SUM(COUNT(customer_unique_id)) OVER (), 2) AS customer_share_pct,
    ROUND(SUM(monetary), 2) AS total_segment_revenue_brl,
    ROUND(SUM(monetary) * 100.0 / SUM(SUM(monetary)) OVER (), 2) AS revenue_share_pct,
    ROUND(AVG(monetary), 2) AS avg_monetary_spend_brl,
    ROUND(AVG(frequency), 2) AS avg_purchase_frequency,
    ROUND(AVG(recency_days), 1) AS avg_recency_days
FROM customer_segmented
GROUP BY rfm_segment
ORDER BY total_segment_revenue_brl DESC;
