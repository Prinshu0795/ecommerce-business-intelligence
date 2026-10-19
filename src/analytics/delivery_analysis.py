"""
Delivery Logistics Analytics Module
Analyzes lead times, on-time delivery percentages, delay distributions,
seller fulfillment performance, and geographic latency patterns.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
from src.database.connection import query_df

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_delivery_summary_metrics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    customer_state: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate core delivery performance KPIs and lead-time averages."""
    where_clauses = ["o.order_status = 'delivered'", "o.is_delivered_on_time IS NOT NULL"]
    params = {}

    if start_date:
        where_clauses.append("o.order_purchase_timestamp >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where_clauses.append("o.order_purchase_timestamp <= :end_date")
        params["end_date"] = end_date
    if customer_state and customer_state != "All":
        where_clauses.append("c.customer_state = :customer_state")
        params["customer_state"] = customer_state

    where_sql = " AND ".join(where_clauses)

    sql = f"""
    SELECT
        COUNT(*) AS evaluable_delivered_orders,
        COUNT(CASE WHEN o.is_delivered_on_time = 1 THEN 1 END) AS on_time_orders,
        COUNT(CASE WHEN o.is_delivered_on_time = 0 THEN 1 END) AS delayed_orders,
        ROUND(AVG(o.delivery_duration_days), 1) AS avg_delivery_duration_days,
        ROUND(AVG(o.estimated_duration_days), 1) AS avg_estimated_duration_days,
        ROUND(AVG(o.carrier_duration_days), 1) AS avg_carrier_transit_days,
        ROUND(AVG(o.approval_duration_hours), 1) AS avg_approval_hours,
        ROUND(AVG(o.delivery_delay_days), 2) AS avg_delivery_delay_days,
        ROUND(AVG(CASE WHEN o.delivery_delay_days > 0 THEN o.delivery_delay_days END), 2) AS avg_delay_when_late,
        ROUND(AVG(CASE WHEN o.delivery_delay_days <= 0 THEN o.delivery_delay_days END), 2) AS avg_early_when_ontime
    FROM fact_order o
    JOIN dim_customer c ON o.customer_id = c.customer_id
    WHERE {where_sql};
    """
    df = query_df(sql, params)
    row = df.iloc[0].to_dict()

    eval_orders = int(row["evaluable_delivered_orders"] or 0)
    ontime_orders = int(row["on_time_orders"] or 0)
    delayed_orders = int(row["delayed_orders"] or 0)

    return {
        "evaluable_delivered_orders": eval_orders,
        "on_time_orders": ontime_orders,
        "delayed_orders": delayed_orders,
        "on_time_rate_pct": round((ontime_orders * 100.0) / eval_orders, 2) if eval_orders else 0.0,
        "late_delivery_rate_pct": round((delayed_orders * 100.0) / eval_orders, 2) if eval_orders else 0.0,
        "avg_delivery_duration_days": float(row["avg_delivery_duration_days"] or 0.0),
        "avg_estimated_duration_days": float(row["avg_estimated_duration_days"] or 0.0),
        "avg_carrier_transit_days": float(row["avg_carrier_transit_days"] or 0.0),
        "avg_approval_hours": float(row["avg_approval_hours"] or 0.0),
        "avg_delivery_delay_days": float(row["avg_delivery_delay_days"] or 0.0),
        "avg_delay_when_late": float(row["avg_delay_when_late"] or 0.0),
        "avg_early_when_ontime": float(row["avg_early_when_ontime"] or 0.0),
    }


def get_delivery_delay_distribution() -> pd.DataFrame:
    """Retrieve delivery delay day distribution for histogram / density visualization."""
    sql = """
    SELECT
        delivery_delay_days,
        delivery_duration_days,
        is_delivered_on_time,
        delivery_status_category
    FROM fact_order
    WHERE order_status = 'delivered'
      AND delivery_delay_days IS NOT NULL
      AND delivery_delay_days BETWEEN -30 AND 40;
    """
    return query_df(sql)


def get_state_delivery_performance() -> pd.DataFrame:
    """Retrieve delivery lead-times and on-time performance by destination state."""
    sql = """
    SELECT
        c.customer_state,
        COUNT(o.order_id) AS delivered_orders,
        ROUND(AVG(o.delivery_duration_days), 1) AS avg_delivery_days,
        ROUND(AVG(o.estimated_duration_days), 1) AS avg_estimated_days,
        ROUND(AVG(o.delivery_delay_days), 2) AS avg_delay_days,
        ROUND(AVG(o.is_delivered_on_time) * 100.0, 2) AS on_time_rate_pct,
        ROUND(AVG(o.review_score), 2) AS avg_review_score
    FROM fact_order o
    JOIN dim_customer c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
      AND o.is_delivered_on_time IS NOT NULL
    GROUP BY c.customer_state
    HAVING COUNT(o.order_id) >= 20
    ORDER BY avg_delivery_days DESC;
    """
    return query_df(sql)


def get_monthly_delivery_trends() -> pd.DataFrame:
    """Retrieve month-over-month on-time rate and average transit duration."""
    sql = """
    SELECT
        d.year_month,
        COUNT(o.order_id) AS delivered_orders,
        ROUND(AVG(o.is_delivered_on_time) * 100.0, 2) AS on_time_rate_pct,
        ROUND(AVG(o.delivery_duration_days), 1) AS avg_delivery_days,
        ROUND(AVG(o.delivery_delay_days), 2) AS avg_delay_days
    FROM fact_order o
    JOIN dim_date d ON o.order_purchase_date_id = d.date_id
    WHERE o.order_status = 'delivered'
      AND o.is_delivered_on_time IS NOT NULL
    GROUP BY d.year_month
    ORDER BY d.year_month ASC;
    """
    return query_df(sql)


def get_seller_delivery_rankings(min_orders: int = 15) -> pd.DataFrame:
    """Retrieve seller fulfillment performance ranked by volume and on-time fulfillment."""
    sql = f"""
    SELECT
        s.seller_id,
        s.seller_state,
        s.seller_city,
        COUNT(DISTINCT oi.order_id) AS eligible_orders_count,
        ROUND(SUM(oi.price), 2) AS total_revenue,
        ROUND(AVG(o.is_delivered_on_time) * 100.0, 2) AS on_time_rate_pct,
        ROUND(AVG(o.delivery_delay_days), 2) AS avg_delay_days,
        ROUND(AVG(o.delivery_duration_days), 1) AS avg_delivery_days,
        ROUND(AVG(o.review_score), 2) AS avg_review_score
    FROM dim_seller s
    JOIN fact_order_item oi ON s.seller_id = oi.seller_id
    JOIN fact_order o ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.is_delivered_on_time IS NOT NULL
    GROUP BY s.seller_id, s.seller_state, s.seller_city
    HAVING COUNT(DISTINCT oi.order_id) >= {min_orders}
    ORDER BY eligible_orders_count DESC;
    """
    return query_df(sql)
