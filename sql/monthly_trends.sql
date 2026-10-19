-- ============================================================================
-- Query 2: Monthly Trends & Growth Analytics
-- Purpose: Evaluate historical sales volume, GMV, MoM growth, and rolling averages.
-- Advanced Techniques: Multi-table joins, Window functions (LAG, SUM OVER, AVG OVER)
-- Dialect: ANSI SQL / PostgreSQL / DuckDB
-- ============================================================================

WITH monthly_aggregates AS (
    SELECT
        d.year_month,
        MIN(d.full_date) AS month_start_date,
        COUNT(DISTINCT o.order_id) AS total_orders,
        COUNT(DISTINCT CASE WHEN o.order_status = 'delivered' THEN o.order_id END) AS delivered_orders,
        ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN o.merchandise_value ELSE 0 END), 2) AS monthly_gmv,
        ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN o.freight_value ELSE 0 END), 2) AS monthly_freight,
        ROUND(
            SUM(CASE WHEN o.order_status = 'delivered' THEN o.merchandise_value ELSE 0 END) / 
            NULLIF(COUNT(DISTINCT CASE WHEN o.order_status = 'delivered' THEN o.order_id END), 0), 
            2
        ) AS monthly_aov
    FROM fact_order o
    JOIN dim_date d ON o.order_purchase_date_id = d.date_id
    GROUP BY d.year_month
),
growth_window AS (
    SELECT
        year_month,
        total_orders,
        delivered_orders,
        monthly_gmv,
        monthly_freight,
        monthly_aov,
        
        -- Previous month metrics for MoM calculation
        LAG(delivered_orders, 1) OVER (ORDER BY year_month) AS prev_month_delivered_orders,
        LAG(monthly_gmv, 1) OVER (ORDER BY year_month) AS prev_month_gmv,
        
        -- 3-Month Moving Average of GMV
        ROUND(
            AVG(monthly_gmv) OVER (
                ORDER BY year_month 
                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
            ), 
            2
        ) AS gmv_3month_moving_avg,
        
        -- Cumulative Running Total of Delivered GMV
        ROUND(
            SUM(monthly_gmv) OVER (
                ORDER BY year_month 
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ), 
            2
        ) AS cumulative_running_gmv
    FROM monthly_aggregates
)
SELECT
    year_month,
    total_orders,
    delivered_orders,
    monthly_gmv,
    monthly_aov,
    
    -- MoM Delivered Orders Growth Rate %
    ROUND(
        ((delivered_orders - prev_month_delivered_orders) * 100.0) / 
        NULLIF(prev_month_delivered_orders, 0), 
        2
    ) AS mom_order_growth_pct,
    
    -- MoM Delivered GMV Growth Rate %
    ROUND(
        ((monthly_gmv - prev_month_gmv) * 100.0) / 
        NULLIF(prev_month_gmv, 0), 
        2
    ) AS mom_gmv_growth_pct,
    
    gmv_3month_moving_avg,
    cumulative_running_gmv
FROM growth_window
ORDER BY year_month ASC;
