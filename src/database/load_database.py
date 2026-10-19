"""
ETL & Database Loader Pipeline
Orchestrates cleaning, feature engineering, schema creation, and database loading.
Ensures idempotent execution and executes automated quality validation.
"""

import time
import logging
from pathlib import Path
from typing import Dict, Any
import pandas as pd

from config.settings import PROJECT_ROOT, RAW_DATA_DIR
from src.ingestion.load_raw_data import load_all_raw_data
from src.preprocessing.clean_data import DataCleaner
from src.preprocessing.feature_engineering import (
    engineer_delivery_features,
    engineer_order_aggregates,
    engineer_rfm_features,
)
from src.database.connection import get_db_manager, DatabaseManager
from src.validation.data_quality import DataQualityValidator
from src.validation.reconciliation import run_reconciliation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def prepare_dimensional_tables(
    cleaned_tables: Dict[str, pd.DataFrame]
) -> Dict[str, pd.DataFrame]:
    """
    Assemble the star schema dimensional and fact DataFrames from cleaned data.
    """
    logger.info("Preparing dimensional and fact tables for database load...")

    # 1. Dimensions
    dim_date = cleaned_tables["dim_date"]
    dim_geography = cleaned_tables["geolocation"]
    dim_customer = cleaned_tables["customers"]
    dim_product = cleaned_tables["products"]
    dim_seller = cleaned_tables["sellers"]

    # 2. Enrich orders with delivery features and order-level aggregates
    orders_with_delivery = engineer_delivery_features(cleaned_tables["orders"])
    fact_order = engineer_order_aggregates(
        orders_with_delivery,
        cleaned_tables["order_items"],
        cleaned_tables["payments"],
        cleaned_tables["reviews"],
    )

    # Add foreign key date_id
    fact_order["order_purchase_date_id"] = (
        fact_order["order_purchase_timestamp"].dt.strftime("%Y%m%d").astype(int)
    )

    # 3. Fact order items
    fact_order_item = cleaned_tables["order_items"].copy()
    fact_order_item["total_item_value"] = fact_order_item["price"] + fact_order_item["freight_value"]

    # 4. Fact payments & reviews
    fact_payment = cleaned_tables["payments"].copy()
    fact_review = cleaned_tables["reviews"].copy()

    return {
        "dim_date": dim_date,
        "dim_geography": dim_geography,
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_seller": dim_seller,
        "fact_order": fact_order,
        "fact_order_item": fact_order_item,
        "fact_payment": fact_payment,
        "fact_review": fact_review,
    }


def load_to_database(
    tables: Dict[str, pd.DataFrame],
    db: DatabaseManager,
) -> Dict[str, int]:
    """
    Load DataFrames into the database idempotently.
    Supports both PostgreSQL and DuckDB engines.
    """
    schema_sql_path = PROJECT_ROOT / "src" / "database" / "schema.sql"
    with open(schema_sql_path, "r", encoding="utf-8") as f:
        ddl_script = f.read()

    logger.info(f"Applying schema DDL on backend '{db.active_backend}'...")

    if db.active_backend == "duckdb":
        conn = db.get_duckdb_connection()
        # For DuckDB, we can register dataframes directly and create persistent tables
        for table_name, df in tables.items():
            logger.info(f"Loading table '{table_name}' ({len(df):,} rows)...")
            conn.register(f"temp_{table_name}", df)
            conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM temp_{table_name};")
            conn.unregister(f"temp_{table_name}")

        # Create views on DuckDB
        logger.info("Creating analytical views in DuckDB...")
        # Split views from schema.sql
        view_queries = [
            """
            CREATE OR REPLACE VIEW vw_order_summary AS
            SELECT 
                o.order_id,
                o.order_status,
                o.order_purchase_timestamp,
                d.year,
                d.month,
                d.year_month,
                c.customer_unique_id,
                c.customer_state,
                c.customer_city,
                o.item_count,
                o.merchandise_value,
                o.freight_value,
                o.total_order_value,
                o.total_payment_value,
                o.delivery_duration_days,
                o.delivery_delay_days,
                o.is_delivered_on_time,
                o.delivery_status_category,
                o.review_score
            FROM fact_order o
            JOIN dim_customer c ON o.customer_id = c.customer_id
            LEFT JOIN dim_date d ON o.order_purchase_date_id = d.date_id;
            """,
            """
            CREATE OR REPLACE VIEW vw_monthly_sales AS
            SELECT 
                d.year_month,
                d.year,
                d.month,
                COUNT(DISTINCT o.order_id) AS total_orders,
                SUM(CASE WHEN o.order_status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders,
                SUM(CASE WHEN o.order_status = 'canceled' THEN 1 ELSE 0 END) AS canceled_orders,
                ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN o.merchandise_value ELSE 0 END), 2) AS delivered_merchandise_value,
                ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN o.freight_value ELSE 0 END), 2) AS delivered_freight_value,
                ROUND(
                    SUM(CASE WHEN o.order_status = 'delivered' THEN o.merchandise_value ELSE 0 END) / 
                    NULLIF(SUM(CASE WHEN o.order_status = 'delivered' THEN 1 ELSE 0 END), 0), 
                    2
                ) AS delivered_aov,
                ROUND(
                    AVG(CASE WHEN o.order_status = 'delivered' THEN o.is_delivered_on_time END) * 100.0, 
                    2
                ) AS on_time_delivery_rate_pct,
                ROUND(AVG(o.review_score), 2) AS avg_review_score
            FROM fact_order o
            JOIN dim_date d ON o.order_purchase_date_id = d.date_id
            GROUP BY d.year_month, d.year, d.month;
            """,
            """
            CREATE OR REPLACE VIEW vw_seller_kpis AS
            SELECT 
                s.seller_id,
                s.seller_state,
                s.seller_city,
                COUNT(DISTINCT oi.order_id) AS total_orders,
                COUNT(oi.order_item_id) AS total_items_sold,
                ROUND(SUM(oi.price), 2) AS total_merchandise_value,
                ROUND(AVG(oi.price), 2) AS avg_item_price,
                ROUND(AVG(o.is_delivered_on_time) * 100.0, 2) AS on_time_delivery_rate_pct,
                ROUND(AVG(o.delivery_delay_days), 2) AS avg_delivery_delay_days,
                ROUND(AVG(o.review_score), 2) AS avg_seller_review_score
            FROM dim_seller s
            JOIN fact_order_item oi ON s.seller_id = oi.seller_id
            JOIN fact_order o ON oi.order_id = o.order_id
            GROUP BY s.seller_id, s.seller_state, s.seller_city;
            """
        ]
        for vq in view_queries:
            conn.execute(vq)

    else:
        # PostgreSQL bulk loading
        logger.info("Executing DDL in PostgreSQL...")
        db.execute_query(ddl_script)
        engine = db._pg_engine
        for table_name, df in tables.items():
            logger.info(f"Loading {table_name} into PostgreSQL ({len(df):,} rows)...")
            df.to_sql(
                table_name,
                con=engine,
                if_exists="append",
                index=False,
                chunksize=5000,
                method="multi",
            )

    row_counts = {name: len(df) for name, df in tables.items()}
    logger.info("All tables successfully loaded into database.")
    return row_counts


def run_etl_pipeline(data_dir: Path = RAW_DATA_DIR) -> Dict[str, Any]:
    """Execute complete end-to-end ETL and validation pipeline."""
    start_time = time.time()
    logger.info("=== STARTING E-COMMERCE ETL PIPELINE ===")

    # 1. Ingestion
    raw_tables = load_all_raw_data(data_dir)

    # 2. Cleaning
    cleaner = DataCleaner()
    cleaned_tables, cleaning_audit = cleaner.clean_all(raw_tables)

    # 3. Dimensional transformation
    star_schema_tables = prepare_dimensional_tables(cleaned_tables)

    # 4. Database Loading
    db = get_db_manager(read_only=False)
    row_counts = load_to_database(star_schema_tables, db)

    # 5. Data Quality Validation
    validator = DataQualityValidator()
    dq_report = validator.run_all_checks(star_schema_tables)

    # 6. Source-to-Target Reconciliation
    recon_report = run_reconciliation(raw_tables, star_schema_tables)

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"=== ETL PIPELINE COMPLETED IN {elapsed}s ===")

    return {
        "status": "SUCCESS",
        "elapsed_seconds": elapsed,
        "row_counts": row_counts,
        "cleaning_audit": cleaning_audit,
        "data_quality_report": dq_report,
        "reconciliation_report": recon_report,
    }


if __name__ == "__main__":
    result = run_etl_pipeline()
    print("\n=== LOAD RESULTS ===")
    for tbl, count in result["row_counts"].items():
        print(f"  {tbl}: {count:,} rows")
    print(f"\nExecution Time: {result['elapsed_seconds']} seconds")
    print("\n=== DATA QUALITY SUMMARY ===")
    print(result["data_quality_report"]["status"].value_counts().to_string())
    print("\n=== RECONCILIATION SUMMARY ===")
    print(result["reconciliation_report"][["metric", "source_raw", "target_transformed", "pct_reconciled"]].to_string())
