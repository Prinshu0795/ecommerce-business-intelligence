"""
SQL Reconciliation & Database Integrity Tests
Validates that database star schema tables match source files with 100% fidelity.
"""

import pytest
from src.database.connection import query_df


def test_database_table_record_counts():
    """Verify exact dimensional record counts in the live analytical database."""
    counts = query_df("""
        SELECT 'fact_order' AS tbl, COUNT(*) AS cnt FROM fact_order
        UNION ALL
        SELECT 'fact_order_item', COUNT(*) FROM fact_order_item
        UNION ALL
        SELECT 'fact_payment', COUNT(*) FROM fact_payment
        UNION ALL
        SELECT 'fact_review', COUNT(*) FROM fact_review
        UNION ALL
        SELECT 'dim_customer', COUNT(*) FROM dim_customer
        UNION ALL
        SELECT 'dim_product', COUNT(*) FROM dim_product
        UNION ALL
        SELECT 'dim_seller', COUNT(*) FROM dim_seller;
    """)
    count_map = dict(zip(counts["tbl"], counts["cnt"]))

    assert count_map["fact_order"] == 99441
    assert count_map["fact_order_item"] == 112650
    assert count_map["fact_payment"] == 103886
    assert count_map["fact_review"] == 99224
    assert count_map["dim_customer"] == 99441
    assert count_map["dim_product"] == 32951
    assert count_map["dim_seller"] == 3095


def test_financial_reconciliation_totals():
    """Verify exact financial monetary reconciliation."""
    fin_df = query_df("""
        SELECT
            ROUND(SUM(price), 2) AS total_item_price,
            ROUND(SUM(freight_value), 2) AS total_item_freight
        FROM fact_order_item;
    """)
    assert float(fin_df["total_item_price"].iloc[0]) == 13591643.70
    assert float(fin_df["total_item_freight"].iloc[0]) == 2251909.54

    delivered_df = query_df("""
        SELECT
            ROUND(SUM(oi.price), 2) AS delivered_gmv,
            ROUND(SUM(oi.freight_value), 2) AS delivered_freight
        FROM fact_order_item oi
        JOIN fact_order o ON oi.order_id = o.order_id
        WHERE o.order_status = 'delivered';
    """)
    assert float(delivered_df["delivered_gmv"].iloc[0]) == 13221498.11
    assert float(delivered_df["delivered_freight"].iloc[0]) == 2198275.64


def test_order_status_integrity():
    """Verify order status counts."""
    status_df = query_df("""
        SELECT order_status, COUNT(*) AS cnt
        FROM fact_order
        GROUP BY order_status;
    """)
    status_map = dict(zip(status_df["order_status"], status_df["cnt"]))

    assert status_map["delivered"] == 96478
    assert status_map["canceled"] == 625
    assert status_map["shipped"] == 1107
    assert status_map["unavailable"] == 609
