"""
Customer Intelligence & RFM Segmentation Module
Implements RFM scoring, rule-based customer segments, K-Means clustering comparison,
and monthly cohort retention matrices.
"""

import logging
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from src.database.connection import query_df
from config.settings import RFM_REFERENCE_DATE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_customer_rfm_dataset() -> pd.DataFrame:
    """
    Fetch customer-level Recency, Frequency, and Monetary metrics from database.
    Grain: one row per unique customer (customer_unique_id).
    """
    sql = f"""
    WITH cust_orders AS (
        SELECT
            c.customer_unique_id,
            c.customer_state,
            c.customer_city,
            o.order_id,
            o.order_purchase_timestamp,
            o.merchandise_value
        FROM fact_order o
        JOIN dim_customer c ON o.customer_id = c.customer_id
        WHERE o.order_status = 'delivered'
    )
    SELECT
        customer_unique_id,
        MIN(customer_state) AS customer_state,
        MIN(customer_city) AS customer_city,
        COUNT(DISTINCT order_id) AS frequency,
        ROUND(SUM(merchandise_value), 2) AS monetary,
        MIN(order_purchase_timestamp) AS first_order_date,
        MAX(order_purchase_timestamp) AS last_order_date,
        ROUND(
            DATE_DIFF('day', CAST(MAX(order_purchase_timestamp) AS DATE), DATE '{RFM_REFERENCE_DATE}'), 
            0
        ) AS recency_days
    FROM cust_orders
    GROUP BY customer_unique_id;
    """
    df = query_df(sql)

    # Calculate scores
    df["r_score"] = pd.qcut(
        df["recency_days"],
        q=5,
        labels=[5, 4, 3, 2, 1],
        duplicates="drop",
    ).astype(int)

    def score_frequency(freq: int) -> int:
        if freq >= 4:
            return 5
        elif freq == 3:
            return 4
        elif freq == 2:
            return 3
        else:
            return 1

    df["f_score"] = df["frequency"].apply(score_frequency)

    df["m_score"] = pd.qcut(
        df["monetary"].rank(method="first"),
        q=5,
        labels=[1, 2, 3, 4, 5],
    ).astype(int)

    df["rfm_code"] = (
        df["r_score"].astype(str) + df["f_score"].astype(str) + df["m_score"].astype(str)
    )

    def assign_segment(row) -> str:
        r, f, m = row["r_score"], row["f_score"], row["m_score"]
        if r >= 4 and f >= 3 and m >= 4:
            return "Champions"
        elif r >= 3 and f >= 3:
            return "Loyal Customers"
        elif r >= 4 and f >= 1 and m >= 3:
            return "Potential Loyalists"
        elif r >= 4 and f == 1:
            return "New / Recent Customers"
        elif r == 3 and f == 1:
            return "Promising / Developing"
        elif r <= 2 and f >= 3 and m >= 4:
            return "Cannot Lose Them"
        elif r <= 2 and f >= 3:
            return "At Risk"
        elif r <= 2 and f == 1 and m >= 3:
            return "About to Sleep"
        elif r <= 2 and f == 1 and m < 3:
            return "Hibernating"
        else:
            return "Lost / Inactive"

    df["rfm_segment"] = df.apply(assign_segment, axis=1)
    return df


def get_rfm_segment_summary(df_rfm: pd.DataFrame) -> pd.DataFrame:
    """Summarize customer count, monetary contribution, and average stats by segment."""
    summary = (
        df_rfm.groupby("rfm_segment")
        .agg(
            customer_count=("customer_unique_id", "count"),
            total_revenue=("monetary", "sum"),
            avg_recency_days=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
        )
        .reset_index()
    )

    total_customers = summary["customer_count"].sum()
    total_revenue = summary["total_revenue"].sum()

    summary["customer_share_pct"] = (summary["customer_count"] / total_customers * 100.0).round(2)
    summary["revenue_share_pct"] = (summary["total_revenue"] / total_revenue * 100.0).round(2)
    summary["avg_recency_days"] = summary["avg_recency_days"].round(1)
    summary["avg_frequency"] = summary["avg_frequency"].round(2)
    summary["avg_monetary"] = summary["avg_monetary"].round(2)
    summary["total_revenue"] = summary["total_revenue"].round(2)

    return summary.sort_values("total_revenue", ascending=False)


def run_kmeans_clustering(
    df_rfm: pd.DataFrame, n_clusters: int = 4, sample_size: int = 15000
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Perform K-Means clustering on log-transformed and standardized RFM features.
    Computes silhouette score on a representative sample for performance.
    """
    # Sample if needed to guarantee sub-second interactive response
    if len(df_rfm) > sample_size:
        df_sample = df_rfm.sample(n=sample_size, random_state=42).copy()
    else:
        df_sample = df_rfm.copy()

    # Log transform to manage heavy skewness in Recency, Frequency, and Monetary
    features_log = np.log1p(df_sample[["recency_days", "frequency", "monetary"]])

    scaler = StandardScaler()
    scaled_matrix = scaler.fit_transform(features_log)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(scaled_matrix)
    df_sample["cluster"] = cluster_labels

    # Silhouette evaluation (on up to 5,000 points for speed)
    eval_sample_size = min(5000, len(scaled_matrix))
    eval_indices = np.random.choice(len(scaled_matrix), eval_sample_size, replace=False)
    score = silhouette_score(scaled_matrix[eval_indices], cluster_labels[eval_indices])

    cluster_profiles = (
        df_sample.groupby("cluster")
        .agg(
            customer_count=("customer_unique_id", "count"),
            avg_recency=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
            total_revenue=("monetary", "sum"),
        )
        .round(2)
        .reset_index()
    )

    cluster_profiles["customer_share_pct"] = (
        cluster_profiles["customer_count"] / cluster_profiles["customer_count"].sum() * 100.0
    ).round(2)
    cluster_profiles["revenue_share_pct"] = (
        cluster_profiles["total_revenue"] / cluster_profiles["total_revenue"].sum() * 100.0
    ).round(2)

    metadata = {
        "n_clusters": n_clusters,
        "silhouette_score": round(float(score), 4),
        "cluster_profiles": cluster_profiles,
        "sample_size_evaluated": len(df_sample),
    }

    return df_sample, metadata


def get_cohort_retention_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Retrieve cohort retention size and percentage matrices from database."""
    sql = """
    WITH customer_orders AS (
        SELECT
            c.customer_unique_id,
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
            (co.order_year - cc.cohort_year) * 12 + (co.order_month - cc.cohort_month_num) AS cohort_index
        FROM customer_orders co
        JOIN customer_cohorts cc ON co.customer_unique_id = cc.customer_unique_id
    )
    SELECT
        cohort_month,
        cohort_index,
        COUNT(DISTINCT customer_unique_id) AS active_customers
    FROM cohort_activity
    WHERE cohort_month >= '2017-01' AND cohort_month <= '2018-08'
    GROUP BY cohort_month, cohort_index
    ORDER BY cohort_month ASC, cohort_index ASC;
    """
    df = query_df(sql)

    # Pivot into matrices
    cohort_matrix = df.pivot(index="cohort_month", columns="cohort_index", values="active_customers").fillna(0)
    cohort_sizes = cohort_matrix.iloc[:, 0]
    retention_matrix = cohort_matrix.divide(cohort_sizes, axis=0) * 100.0

    return cohort_matrix, retention_matrix.round(2)
