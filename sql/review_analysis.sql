-- ============================================================================
-- Query 8: Customer Experience & Review Score Association with Delays
-- Purpose: Analyze rating distributions and empirically measure the relationship
--          between delivery delay duration and customer dissatisfaction.
-- Caveat: Observational association and does not prove sole causal mechanism.
-- Dialect: ANSI SQL / PostgreSQL / DuckDB
-- ============================================================================

-- Part A: Review Score Distribution & Baseline Metrics
SELECT
    review_score,
    COUNT(order_id) AS total_reviews,
    ROUND(COUNT(order_id) * 100.0 / SUM(COUNT(order_id)) OVER (), 2) AS share_of_reviews_pct,
    CASE 
        WHEN review_score IN (4, 5) THEN 'Positive (Promoter)'
        WHEN review_score = 3 THEN 'Neutral (Passive)'
        ELSE 'Negative (Detractor)'
    END AS sentiment_class
FROM fact_review
GROUP BY review_score
ORDER BY review_score DESC;

-- Part B: On-Time vs Delayed Delivery Review Comparison
SELECT
    CASE 
        WHEN o.is_delivered_on_time = 1 THEN 'On-Time / Early Delivery'
        WHEN o.is_delivered_on_time = 0 THEN 'Delayed Delivery'
        ELSE 'Missing Delivery Timestamp'
    END AS delivery_performance_group,
    COUNT(r.review_id) AS total_reviews,
    ROUND(AVG(r.review_score), 2) AS mean_review_score,
    ROUND(STDDEV(r.review_score), 2) AS std_review_score,
    COUNT(CASE WHEN r.review_score IN (1, 2) THEN 1 END) AS low_rating_count,
    ROUND(
        COUNT(CASE WHEN r.review_score IN (1, 2) THEN 1 END) * 100.0 / COUNT(r.review_id), 
        2
    ) AS low_rating_rate_pct,
    COUNT(CASE WHEN r.review_score = 5 THEN 1 END) AS five_star_count,
    ROUND(
        COUNT(CASE WHEN r.review_score = 5 THEN 1 END) * 100.0 / COUNT(r.review_id), 
        2
    ) AS five_star_rate_pct
FROM fact_order o
JOIN fact_review r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY o.is_delivered_on_time
ORDER BY mean_review_score DESC;

-- Part C: Review Score by Granular Delay Severity Buckets
WITH delay_buckets AS (
    SELECT
        o.order_id,
        r.review_score,
        o.delivery_delay_days,
        CASE
            WHEN o.delivery_delay_days <= -7.0 THEN '1. Early (>7 days)'
            WHEN o.delivery_delay_days <= -2.0 THEN '2. Early (2 to 7 days)'
            WHEN o.delivery_delay_days <= 0.0 THEN '3. On-Time (0 to 1 day early)'
            WHEN o.delivery_delay_days <= 3.0 THEN '4. Minor Delay (1 to 3 days late)'
            WHEN o.delivery_delay_days <= 7.0 THEN '5. Moderate Delay (4 to 7 days late)'
            ELSE '6. Severe Delay (>7 days late)'
        END AS delay_bracket
    FROM fact_order o
    JOIN fact_review r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
      AND o.delivery_delay_days IS NOT NULL
)
SELECT
    delay_bracket,
    COUNT(*) AS order_count,
    ROUND(AVG(delivery_delay_days), 1) AS avg_delay_days_in_bracket,
    ROUND(AVG(review_score), 2) AS mean_review_score,
    COUNT(CASE WHEN review_score IN (1, 2) THEN 1 END) AS low_ratings_count,
    ROUND(COUNT(CASE WHEN review_score IN (1, 2) THEN 1 END) * 100.0 / COUNT(*), 2) AS low_rating_pct
FROM delay_buckets
GROUP BY delay_bracket
ORDER BY delay_bracket ASC;
