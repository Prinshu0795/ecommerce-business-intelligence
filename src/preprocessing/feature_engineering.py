"""
Feature Engineering Pipeline
Computes delivery performance metrics, customer RFM features, cohort indices,
and order-level financial rollups.
"""

import logging
from typing import Dict, Tuple
import numpy as np
import pandas as pd

from config.settings import RFM_REFERENCE_DATE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def engineer_delivery_features(df_orders: pd.DataFrame) -> pd.DataFrame:
    """
    Compute rigorous logistics & delivery duration features on orders.
    Grain: one row per order.
    """
    df = df_orders.copy()

    # Calculate delivery duration from purchase to customer delivery (days)
    df["delivery_duration_days"] = (
        (df["order_delivered_customer_date"] - df["order_purchase_timestamp"]).dt.total_seconds()
        / 86400.0
    )

    # Calculate carrier shipping duration (days)
    df["carrier_duration_days"] = (
        (df["order_delivered_customer_date"] - df["order_delivered_carrier_date"]).dt.total_seconds()
        / 86400.0
    )

    # Estimated delivery duration (days)
    df["estimated_duration_days"] = (
        (df["order_estimated_delivery_date"] - df["order_purchase_timestamp"]).dt.total_seconds()
        / 86400.0
    )

    # Approval duration (hours)
    df["approval_duration_hours"] = (
        (df["order_approved_at"] - df["order_purchase_timestamp"]).dt.total_seconds()
        / 3600.0
    )

    # Delay relative to estimated delivery date (positive = late, negative/0 = on-time)
    has_both_delivery_dates = (
        df["order_delivered_customer_date"].notnull()
        & df["order_estimated_delivery_date"].notnull()
    )

    df["delivery_delay_days"] = np.where(
        has_both_delivery_dates,
        (df["order_delivered_customer_date"] - df["order_estimated_delivery_date"]).dt.total_seconds()
        / 86400.0,
        np.nan,
    )

    # Explicit on-time binary flag: 1 if delivered on or before estimate, 0 if delayed
    df["is_delivered_on_time"] = np.where(
        has_both_delivery_dates,
        (df["delivery_delay_days"] <= 0.0).astype(int),
        np.nan,
    )

    # Delivery performance categorization
    conditions = [
        ~has_both_delivery_dates & (df["order_status"] == "canceled"),
        ~has_both_delivery_dates & (df["order_status"] != "delivered"),
        has_both_delivery_dates & (df["delivery_delay_days"] <= 0.0),
        has_both_delivery_dates & (df["delivery_delay_days"] > 0.0) & (df["delivery_delay_days"] <= 3.0),
        has_both_delivery_dates & (df["delivery_delay_days"] > 3.0),
    ]
    choices = [
        "Cancelled",
        "In Transit / Pending",
        "On-Time / Early",
        "Minor Delay (1-3 days)",
        "Severe Delay (>3 days)",
    ]
    df["delivery_status_category"] = np.select(conditions, choices, default="Undetermined")

    logger.info(
        f"Delivery features computed. On-time orders: "
        f"{int((df['is_delivered_on_time'] == 1).sum()):,}, "
        f"Delayed: {int((df['is_delivered_on_time'] == 0).sum()):,}"
    )
    return df


def engineer_order_aggregates(
    df_orders: pd.DataFrame,
    df_items: pd.DataFrame,
    df_payments: pd.DataFrame,
    df_reviews: pd.DataFrame,
) -> pd.DataFrame:
    """
    Roll up items, payments, and reviews to order-level grain to prevent fan-out joins.
    Grain: one row per order.
    """
    # 1. Rollup order items
    items_agg = (
        df_items.groupby("order_id")
        .agg(
            item_count=("order_item_id", "count"),
            merchandise_value=("price", "sum"),
            freight_value=("freight_value", "sum"),
            seller_count=("seller_id", "nunique"),
            first_seller_id=("seller_id", "first"),
            primary_product_id=("product_id", "first"),
        )
        .reset_index()
    )
    items_agg["total_order_value"] = items_agg["merchandise_value"] + items_agg["freight_value"]

    # 2. Rollup payments
    payments_agg = (
        df_payments.groupby("order_id")
        .agg(
            payment_records_count=("payment_sequential", "count"),
            total_payment_value=("payment_value", "sum"),
            primary_payment_type=("payment_type", "first"),
            max_installments=("payment_installments", "max"),
        )
        .reset_index()
    )

    # 3. Rollup reviews
    reviews_agg = (
        df_reviews.groupby("order_id")
        .agg(
            review_count=("review_id", "count"),
            review_score=("review_score", "mean"),
            latest_review_date=("review_creation_date", "max"),
        )
        .reset_index()
    )

    # Merge cleanly at 1-to-1 order grain
    df_order_facts = (
        df_orders.merge(items_agg, on="order_id", how="left")
        .merge(payments_agg, on="order_id", how="left")
        .merge(reviews_agg, on="order_id", how="left")
    )

    # Fill numerical zeros where order had no items/payments (e.g. early cancellations)
    for col in ["item_count", "merchandise_value", "freight_value", "total_order_value", "total_payment_value"]:
        df_order_facts[col] = df_order_facts[col].fillna(0.0)

    df_order_facts["has_review"] = df_order_facts["review_score"].notnull().astype(int)
    return df_order_facts


def engineer_rfm_features(
    df_orders: pd.DataFrame,
    df_customers: pd.DataFrame,
    df_items: pd.DataFrame,
    reference_date_str: str = RFM_REFERENCE_DATE,
) -> pd.DataFrame:
    """
    Compute customer-level RFM features using unique customer identifiers.
    Grain: one row per customer_unique_id.
    """
    ref_date = pd.to_datetime(reference_date_str)

    # Merge orders with customers to get customer_unique_id
    orders_cust = df_orders.merge(
        df_customers[["customer_id", "customer_unique_id", "customer_city", "customer_state"]],
        on="customer_id",
        how="inner",
    )

    # Join with items to get merchandise value
    delivered_orders = orders_cust[orders_cust["order_status"] == "delivered"]
    order_items_spend = df_items.groupby("order_id")["price"].sum().reset_index()
    order_spend_df = delivered_orders.merge(order_items_spend, on="order_id", how="left")
    order_spend_df["price"] = order_spend_df["price"].fillna(0.0)

    # Aggregate by customer_unique_id
    rfm = (
        order_spend_df.groupby("customer_unique_id")
        .agg(
            first_purchase_date=("order_purchase_timestamp", "min"),
            last_purchase_date=("order_purchase_timestamp", "max"),
            frequency=("order_id", "nunique"),
            monetary=("price", "sum"),
            customer_city=("customer_city", "first"),
            customer_state=("customer_state", "first"),
        )
        .reset_index()
    )

    # Calculate Recency in days relative to snapshot reference date
    rfm["recency_days"] = (ref_date - rfm["last_purchase_date"]).dt.total_seconds() / 86400.0
    rfm["recency_days"] = rfm["recency_days"].clip(lower=0).round(1)

    # Calculate customer lifespan (days between first and last order)
    rfm["customer_lifespan_days"] = (
        (rfm["last_purchase_date"] - rfm["first_purchase_date"]).dt.total_seconds() / 86400.0
    ).round(1)

    # RFM Scoring: Quintiles 1 to 5
    # Recency: lower days = higher score (5)
    rfm["r_score"] = pd.qcut(
        rfm["recency_days"],
        q=5,
        labels=[5, 4, 3, 2, 1],
        duplicates="drop",
    ).astype(int)

    # Frequency: because >95% have 1 order, we score explicitly:
    # 1 order = 1, 2 orders = 3, 3 orders = 4, 4+ orders = 5
    def score_frequency(freq: int) -> int:
        if freq >= 4:
            return 5
        elif freq == 3:
            return 4
        elif freq == 2:
            return 3
        else:
            return 1

    rfm["f_score"] = rfm["frequency"].apply(score_frequency)

    # Monetary: higher spend = higher score (5)
    rfm["m_score"] = pd.qcut(
        rfm["monetary"].rank(method="first"),
        q=5,
        labels=[1, 2, 3, 4, 5],
    ).astype(int)

    # Combined RFM code (e.g. 515)
    rfm["rfm_code"] = (
        rfm["r_score"].astype(str) + rfm["f_score"].astype(str) + rfm["m_score"].astype(str)
    )

    # Actionable Business Segments Assignment
    def assign_rfm_segment(row) -> str:
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

    rfm["rfm_segment"] = rfm.apply(assign_rfm_segment, axis=1)

    logger.info(
        f"RFM feature engineering complete. {len(rfm):,} unique customers segmented into "
        f"{rfm['rfm_segment'].nunique()} segments."
    )
    return rfm


def engineer_cohort_features(
    df_orders: pd.DataFrame, df_customers: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute customer cohort retention indices.
    """
    orders_cust = df_orders.merge(
        df_customers[["customer_id", "customer_unique_id"]],
        on="customer_id",
        how="inner",
    )
    # Delivered orders only
    delivered = orders_cust[orders_cust["order_status"] == "delivered"].copy()

    delivered["order_month"] = delivered["order_purchase_timestamp"].dt.to_period("M")

    # Determine first purchase month for each customer
    first_purchase = delivered.groupby("customer_unique_id")["order_month"].min().reset_index()
    first_purchase.rename(columns={"order_month": "cohort_month"}, inplace=True)

    delivered = delivered.merge(first_purchase, on="customer_unique_id", how="left")

    # Calculate cohort index (months from cohort month)
    delivered["cohort_index"] = (
        (delivered["order_month"].dt.year - delivered["cohort_month"].dt.year) * 12
        + (delivered["order_month"].dt.month - delivered["cohort_month"].dt.month)
    )

    # Build cohort matrix
    cohort_data = (
        delivered.groupby(["cohort_month", "cohort_index"])["customer_unique_id"]
        .nunique()
        .reset_index()
    )
    cohort_matrix = cohort_data.pivot(
        index="cohort_month", columns="cohort_index", values="customer_unique_id"
    )

    # Retention percentage matrix
    cohort_sizes = cohort_matrix.iloc[:, 0]
    retention_matrix = cohort_matrix.divide(cohort_sizes, axis=0) * 100.0

    return delivered, retention_matrix
