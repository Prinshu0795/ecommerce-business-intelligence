"""
Unit & Data Quality Tests
Tests for cleaning functions, schema validation, timestamp parsing, and duplicate handling.
"""

import pytest
import pandas as pd
import numpy as np

from src.preprocessing.clean_data import DataCleaner
from src.validation.data_quality import DataQualityValidator


@pytest.fixture
def sample_raw_orders():
    """Synthetic orders fixture for isolated unit testing."""
    return pd.DataFrame({
        "order_id": ["ord_1", "ord_2", "ord_3", "ord_1"],  # includes duplicate
        "customer_id": ["c1", "c2", "c3", "c1"],
        "order_status": ["delivered", "shipped", "canceled", "delivered"],
        "order_purchase_timestamp": [
            "2018-01-01 10:00:00",
            "2018-01-02 12:00:00",
            "2018-01-03 14:00:00",
            "2018-01-01 10:00:00",
        ],
        "order_approved_at": ["2018-01-01 11:00:00", "2018-01-02 13:00:00", None, "2018-01-01 11:00:00"],
        "order_delivered_carrier_date": ["2018-01-02 09:00:00", None, None, "2018-01-02 09:00:00"],
        "order_delivered_customer_date": ["2018-01-05 16:00:00", None, None, "2018-01-05 16:00:00"],
        "order_estimated_delivery_date": [
            "2018-01-10 00:00:00",
            "2018-01-15 00:00:00",
            "2018-01-20 00:00:00",
            "2018-01-10 00:00:00",
        ],
    })


@pytest.fixture
def sample_raw_items():
    """Synthetic items fixture for negative value and duplicate testing."""
    return pd.DataFrame({
        "order_id": ["ord_1", "ord_1", "ord_2", "ord_3"],
        "order_item_id": [1, 2, 1, 1],
        "product_id": ["p1", "p2", "p1", "p3"],
        "seller_id": ["s1", "s1", "s2", "s1"],
        "shipping_limit_date": ["2018-01-05", "2018-01-05", "2018-01-07", "2018-01-10"],
        "price": [100.0, 50.0, -10.0, 25.0],  # negative price record to drop
        "freight_value": [15.0, 10.0, 5.0, 0.0],
    })


def test_order_cleaning_and_deduplication(sample_raw_orders):
    cleaner = DataCleaner()
    df_clean = cleaner.clean_orders(sample_raw_orders)
    
    # Assert duplicates removed
    assert len(df_clean) == 3
    assert df_clean["order_id"].nunique() == 3
    # Assert timestamp parsing
    assert pd.api.types.is_datetime64_any_dtype(df_clean["order_purchase_timestamp"])
    assert pd.api.types.is_datetime64_any_dtype(df_clean["order_delivered_customer_date"])


def test_order_items_negative_price_filtering(sample_raw_items):
    cleaner = DataCleaner()
    df_clean = cleaner.clean_order_items(sample_raw_items)
    
    # Negative price record ord_2 should be dropped
    assert len(df_clean) == 3
    assert (df_clean["price"] >= 0).all()
    assert (df_clean["freight_value"] >= 0).all()


def test_date_dimension_generator():
    cleaner = DataCleaner()
    dim_date = cleaner.generate_dim_date("2018-01-01", "2018-01-31")
    
    assert len(dim_date) == 31
    assert "date_id" in dim_date.columns
    assert "year_month" in dim_date.columns
    assert dim_date["date_id"].iloc[0] == 20180101
    assert dim_date["year_month"].iloc[0] == "2018-01"


def test_data_quality_pk_uniqueness():
    validator = DataQualityValidator()
    df_valid = pd.DataFrame({"id": ["a", "b", "c"], "val": [1, 2, 3]})
    validator.validate_pk_uniqueness(df_valid, "test_tbl", ["id"])
    
    report = pd.DataFrame(validator.results)
    assert (report["status"] == "PASS").all()
