"""
Sales & Executive Analytics Module
Provides aggregated KPIs, monthly trend analysis, category Pareto distributions,
and geographic sales performance with optional dynamic filtering.
"""

import logging
from typing import Optional, Dict, Any, List
import pandas as pd
from src.database.connection import query_df

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_executive_kpis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    customer_state: Optional[str] = None,
    category_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate executive overview KPIs with explicit denominators.
    Delivered GMV is strictly filtered to order_status = 'delivered'.
    """
    where_clauses = ["1=1"]
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
    if category_name and category_name != "All":
        where_clauses.append(
            "o.order_id IN (SELECT oi.order_id FROM fact_order_item oi "
            "JOIN dim_product p ON oi.product_id = p.product_id "
            "WHERE p.product_category_name_english = :category_name)"
        )
        params["category_name"] = category_name

    where_sql = " AND ".join(where_clauses)

    sql = f"""
    SELECT
        COUNT(o.order_id) AS total_orders,
        COUNT(CASE WHEN o.order_status = 'delivered' THEN 1 END) AS delivered_orders,
        COUNT(CASE WHEN o.order_status = 'canceled' THEN 1 END) AS canceled_orders,
        SUM(CASE WHEN o.order_status = 'delivered' THEN o.merchandise_value ELSE 0 END) AS delivered_gmv,
        SUM(CASE WHEN o.order_status = 'delivered' THEN o.freight_value ELSE 0 END) AS delivered_freight,
        SUM(CASE WHEN o.order_status = 'delivered' THEN o.total_order_value ELSE 0 END) AS delivered_total_value,
        SUM(o.merchandise_value) AS gross_recorded_merchandise_value,
        COUNT(CASE WHEN o.order_status = 'delivered' AND o.is_delivered_on_time IS NOT NULL THEN 1 END) AS eval_orders,
        COUNT(CASE WHEN o.order_status = 'delivered' AND o.is_delivered_on_time = 1 THEN 1 END) AS ontime_orders,
        AVG(o.review_score) AS avg_review_score,
        COUNT(CASE WHEN o.review_score IN (1, 2) THEN 1 END) AS low_review_orders,
        COUNT(CASE WHEN o.review_score IS NOT NULL THEN 1 END) AS reviewed_orders
    FROM fact_order o
    JOIN dim_customer c ON o.customer_id = c.customer_id
    WHERE {where_sql};
    """
    df = query_df(sql, params)
    row = df.iloc[0].to_dict()

    total_orders = int(row["total_orders"] or 0)
    delivered_orders = int(row["delivered_orders"] or 0)
    canceled_orders = int(row["canceled_orders"] or 0)
    delivered_gmv = float(row["delivered_gmv"] or 0.0)
    delivered_freight = float(row["delivered_freight"] or 0.0)
    eval_orders = int(row["eval_orders"] or 0)
    ontime_orders = int(row["ontime_orders"] or 0)
    reviewed_orders = int(row["reviewed_orders"] or 0)
    low_review_orders = int(row["low_review_orders"] or 0)

    return {
        "total_orders": total_orders,
        "delivered_orders": delivered_orders,
        "canceled_orders": canceled_orders,
        "cancellation_rate_pct": round((canceled_orders * 100.0) / total_orders, 2) if total_orders else 0.0,
        "delivered_gmv": round(delivered_gmv, 2),
        "delivered_freight": round(delivered_freight, 2),
        "delivered_total_value": round(float(row["delivered_total_value"] or 0.0), 2),
        "delivered_aov": round(delivered_gmv / delivered_orders, 2) if delivered_orders else 0.0,
        "on_time_delivery_rate_pct": round((ontime_orders * 100.0) / eval_orders, 2) if eval_orders else 0.0,
        "avg_review_score": round(float(row["avg_review_score"] or 0.0), 2),
        "low_review_rate_pct": round((low_review_orders * 100.0) / reviewed_orders, 2) if reviewed_orders else 0.0,
    }


def get_monthly_sales_trends(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    customer_state: Optional[str] = None,
) -> pd.DataFrame:
    """Retrieve monthly order volume, GMV, and MoM growth metrics."""
    where_clauses = ["1=1"]
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
    WITH monthly AS (
        SELECT
            d.year_month,
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
        JOIN dim_customer c ON o.customer_id = c.customer_id
        JOIN dim_date d ON o.order_purchase_date_id = d.date_id
        WHERE {where_sql}
        GROUP BY d.year_month
    )
    SELECT
        year_month,
        total_orders,
        delivered_orders,
        monthly_gmv,
        monthly_freight,
        monthly_aov,
        LAG(delivered_orders, 1) OVER (ORDER BY year_month) AS prev_month_orders,
        LAG(monthly_gmv, 1) OVER (ORDER BY year_month) AS prev_month_gmv,
        ROUND(
            AVG(monthly_gmv) OVER (ORDER BY year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 
            2
        ) AS gmv_3month_ma
    FROM monthly
    ORDER BY year_month ASC;
    """
    df = query_df(sql, params)
    df["mom_order_growth_pct"] = (
        ((df["delivered_orders"] - df["prev_month_orders"]) / df["prev_month_orders"]) * 100.0
    ).round(2)
    df["mom_gmv_growth_pct"] = (
        ((df["monthly_gmv"] - df["prev_month_gmv"]) / df["prev_month_gmv"]) * 100.0
    ).round(2)
    return df


def get_category_pareto_breakdown(top_n: int = 15) -> pd.DataFrame:
    """Retrieve category revenue contribution and Pareto curve."""
    sql = """
    WITH cat_sales AS (
        SELECT
            COALESCE(p.product_category_name_english, 'Other Or Unlabeled') AS category_name,
            COUNT(DISTINCT oi.order_id) AS total_orders,
            COUNT(oi.order_item_id) AS items_sold,
            ROUND(SUM(oi.price), 2) AS category_revenue
        FROM fact_order_item oi
        JOIN fact_order o ON oi.order_id = o.order_id
        JOIN dim_product p ON oi.product_id = p.product_id
        WHERE o.order_status = 'delivered'
        GROUP BY p.product_category_name_english
    )
    SELECT
        category_name,
        total_orders,
        items_sold,
        category_revenue,
        ROUND(category_revenue * 100.0 / SUM(category_revenue) OVER (), 2) AS revenue_share_pct,
        ROUND(
            SUM(category_revenue) OVER (
                ORDER BY category_revenue DESC 
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) * 100.0 / SUM(category_revenue) OVER (), 
            2
        ) AS cumulative_share_pct,
        RANK() OVER (ORDER BY category_revenue DESC) AS category_rank
    FROM cat_sales
    ORDER BY category_rank ASC;
    """
    return query_df(sql)


def get_order_status_distribution() -> pd.DataFrame:
    """Retrieve order count and GMV breakdown across all order statuses."""
    sql = """
    SELECT
        order_status,
        COUNT(order_id) AS order_count,
        ROUND(COUNT(order_id) * 100.0 / SUM(COUNT(order_id)) OVER (), 2) AS share_pct,
        ROUND(SUM(merchandise_value), 2) AS merchandise_value_brl
    FROM fact_order
    GROUP BY order_status
    ORDER BY order_count DESC;
    """
    return query_df(sql)


def get_state_sales_distribution() -> pd.DataFrame:
    """Retrieve geographic demand metrics across Brazilian states."""
    sql = """
    SELECT
        c.customer_state,
        COUNT(DISTINCT o.order_id) AS total_orders,
        COUNT(DISTINCT c.customer_unique_id) AS unique_customers,
        ROUND(SUM(o.merchandise_value), 2) AS total_gmv,
        ROUND(
            SUM(o.merchandise_value) * 100.0 / SUM(SUM(o.merchandise_value)) OVER (), 
            2
        ) AS gmv_share_pct,
        ROUND(
            SUM(o.merchandise_value) / NULLIF(COUNT(DISTINCT o.order_id), 0), 
            2
        ) AS aov,
        ROUND(AVG(o.is_delivered_on_time) * 100.0, 2) AS on_time_rate_pct,
        ROUND(AVG(o.delivery_duration_days), 1) AS avg_delivery_days
    FROM fact_order o
    JOIN dim_customer c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_state
    ORDER BY total_gmv DESC;
    """
    return query_df(sql)
