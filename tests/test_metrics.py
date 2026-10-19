"""
Unit & Business Metrics Tests
Validates KPI calculation formulas, explicit denominators, and boundary conditions.
"""

import pytest
import pandas as pd
import numpy as np

from src.preprocessing.feature_engineering import engineer_delivery_features
from src.analytics.sales_analysis import get_executive_kpis


@pytest.fixture
def sample_delivery_df():
    """Synthetic orders for delivery metrics testing."""
    return pd.DataFrame({
        "order_id": ["o1", "o2", "o3", "o4"],
        "order_status": ["delivered", "delivered", "delivered", "canceled"],
        "order_purchase_timestamp": pd.to_datetime([
            "2018-01-01 10:00:00",
            "2018-01-02 10:00:00",
            "2018-01-03 10:00:00",
            "2018-01-04 10:00:00",
        ]),
        "order_approved_at": pd.to_datetime([
            "2018-01-01 12:00:00",
            "2018-01-02 12:00:00",
            "2018-01-03 12:00:00",
            None,
        ]),
        "order_delivered_carrier_date": pd.to_datetime([
            "2018-01-02 10:00:00",
            "2018-01-04 10:00:00",
            "2018-01-05 10:00:00",
            None,
        ]),
        "order_delivered_customer_date": pd.to_datetime([
            "2018-01-05 10:00:00",  # 5 days before estimate -> on-time
            "2018-01-12 10:00:00",  # 2 days after estimate -> delayed
            None,                   # delivered status but missing customer date -> cannot evaluate
            None,                   # canceled
        ]),
        "order_estimated_delivery_date": pd.to_datetime([
            "2018-01-10 10:00:00",
            "2018-01-10 10:00:00",
            "2018-01-15 10:00:00",
            "2018-01-20 10:00:00",
        ]),
    })


def test_delivery_delay_calculation(sample_delivery_df):
    df_feat = engineer_delivery_features(sample_delivery_df)
    
    # Order 1 delivered 5 days early -> delay is -5.0 days
    assert df_feat.loc[df_feat["order_id"] == "o1", "delivery_delay_days"].values[0] == -5.0
    assert df_feat.loc[df_feat["order_id"] == "o1", "is_delivered_on_time"].values[0] == 1

    # Order 2 delivered 2 days late -> delay is +2.0 days
    assert df_feat.loc[df_feat["order_id"] == "o2", "delivery_delay_days"].values[0] == 2.0
    assert df_feat.loc[df_feat["order_id"] == "o2", "is_delivered_on_time"].values[0] == 0

    # Order 3 missing actual customer delivery date -> is_delivered_on_time must be NaN
    assert np.isnan(df_feat.loc[df_feat["order_id"] == "o3", "is_delivered_on_time"].values[0])


def test_ontime_rate_denominator_exclusion(sample_delivery_df):
    """Ensure un-evaluable delivered orders without timestamps are excluded from on-time denominator."""
    df_feat = engineer_delivery_features(sample_delivery_df)
    
    evaluable = df_feat["is_delivered_on_time"].dropna()
    assert len(evaluable) == 2  # Only o1 and o2 are evaluable
    
    ontime_rate = (evaluable == 1).mean() * 100.0
    assert ontime_rate == 50.0  # 1 on-time out of 2 evaluable


def test_executive_kpi_calculations_on_live_db():
    """Verify live database KPI calculation and boundaries."""
    kpis = get_executive_kpis()
    
    assert kpis["total_orders"] == 99441
    assert kpis["delivered_orders"] == 96478
    assert kpis["canceled_orders"] == 625
    assert 0.0 < kpis["cancellation_rate_pct"] < 2.0
    assert kpis["delivered_gmv"] > 13000000.0
    assert 100.0 < kpis["delivered_aov"] < 200.0
    assert 80.0 < kpis["on_time_delivery_rate_pct"] < 95.0
