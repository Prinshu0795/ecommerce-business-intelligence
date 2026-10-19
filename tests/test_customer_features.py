"""
Unit Tests for Customer RFM & Cohort Feature Calculations
"""

import pytest
import pandas as pd
import numpy as np

from src.preprocessing.feature_engineering import (
    engineer_rfm_features,
    engineer_cohort_features,
)


@pytest.fixture
def sample_customer_orders():
    """Synthetic customer orders dataset."""
    df_orders = pd.DataFrame({
        "order_id": ["o1", "o2", "o3", "o4"],
        "customer_id": ["c1", "c2", "c3", "c4"],
        "order_status": ["delivered", "delivered", "delivered", "delivered"],
        "order_purchase_timestamp": pd.to_datetime([
            "2018-01-10 10:00:00",
            "2018-06-15 12:00:00",
            "2018-09-20 14:00:00",
            "2018-09-25 16:00:00",
        ]),
    })

    df_customers = pd.DataFrame({
        "customer_id": ["c1", "c2", "c3", "c4"],
        "customer_unique_id": ["u1", "u1", "u2", "u3"],  # u1 has 2 orders
        "customer_city": ["Sao Paulo", "Sao Paulo", "Rio", "Curitiba"],
        "customer_state": ["SP", "SP", "RJ", "PR"],
    })

    df_items = pd.DataFrame({
        "order_id": ["o1", "o2", "o3", "o4"],
        "order_item_id": [1, 1, 1, 1],
        "product_id": ["p1", "p2", "p3", "p4"],
        "seller_id": ["s1", "s2", "s3", "s4"],
        "price": [150.0, 250.0, 50.0, 800.0],
        "freight_value": [15.0, 20.0, 10.0, 30.0],
    })

    return df_orders, df_customers, df_items


def test_customer_rfm_frequency_and_monetary(sample_customer_orders):
    df_orders, df_customers, df_items = sample_customer_orders
    rfm = engineer_rfm_features(df_orders, df_customers, df_items, reference_date_str="2018-10-18")
    
    # Customer u1 has 2 orders: o1 (150) + o2 (250) = 400.0
    u1_row = rfm[rfm["customer_unique_id"] == "u1"].iloc[0]
    assert u1_row["frequency"] == 2
    assert u1_row["monetary"] == 400.0
    assert u1_row["f_score"] == 3  # 2 orders maps to score 3

    # Customer u3 has 1 order: 800.0
    u3_row = rfm[rfm["customer_unique_id"] == "u3"].iloc[0]
    assert u3_row["frequency"] == 1
    assert u3_row["monetary"] == 800.0


def test_cohort_index_calculation(sample_customer_orders):
    df_orders, df_customers, _ = sample_customer_orders
    delivered, matrix = engineer_cohort_features(df_orders, df_customers)
    
    # Customer u1 first bought in 2018-01 (cohort_index 0) and second in 2018-06 (cohort_index 5)
    u1_orders = delivered[delivered["customer_unique_id"] == "u1"].sort_values("order_purchase_timestamp")
    assert u1_orders.iloc[0]["cohort_index"] == 0
    assert u1_orders.iloc[1]["cohort_index"] == 5
