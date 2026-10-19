"""
Data Quality Validation Suite
Implements comprehensive assertion checks and automated reports for dimensional integrity.
"""

import logging
from typing import Dict, List, Any
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class DataQualityValidator:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def _record(self, check_name: str, table_name: str, passed: bool, severity: str, details: str, failed_count: int = 0):
        self.results.append({
            "check": check_name,
            "table": table_name,
            "status": "PASS" if passed else ("FAIL" if severity == "FATAL" else "WARNING"),
            "severity": severity,
            "failed_count": failed_count,
            "details": details,
        })

    def validate_pk_uniqueness(self, df: pd.DataFrame, table_name: str, pk_cols: List[str]):
        """Ensure primary key has zero duplicates and zero nulls."""
        # Null check
        null_mask = df[pk_cols].isnull().any(axis=1)
        null_count = int(null_mask.sum())
        self._record(
            check_name=f"PK_NOT_NULL ({','.join(pk_cols)})",
            table_name=table_name,
            passed=(null_count == 0),
            severity="FATAL",
            details=f"{null_count} null primary keys found.",
            failed_count=null_count,
        )

        # Duplicate check
        dup_mask = df.duplicated(subset=pk_cols)
        dup_count = int(dup_mask.sum())
        self._record(
            check_name=f"PK_UNIQUENESS ({','.join(pk_cols)})",
            table_name=table_name,
            passed=(dup_count == 0),
            severity="FATAL",
            details=f"{dup_count} duplicate primary key rows found.",
            failed_count=dup_count,
        )

    def validate_referential_integrity(
        self,
        child_df: pd.DataFrame,
        parent_df: pd.DataFrame,
        child_table: str,
        parent_table: str,
        foreign_key: str,
        parent_key: str = None,
    ):
        """Validate that all foreign keys in child table exist in parent table."""
        parent_key = parent_key or foreign_key
        parent_keys_set = set(parent_df[parent_key].dropna())
        unmatched = ~child_df[foreign_key].isin(parent_keys_set)
        unmatched_count = int(unmatched.sum())

        self._record(
            check_name=f"FK_INTEGRITY ({child_table}.{foreign_key} -> {parent_table}.{parent_key})",
            table_name=child_table,
            passed=(unmatched_count == 0),
            severity="WARNING" if unmatched_count < 100 else "FATAL",
            details=f"{unmatched_count} orphan records found.",
            failed_count=unmatched_count,
        )

    def validate_non_negative_values(self, df: pd.DataFrame, table_name: str, num_cols: List[str]):
        """Enforce monetary and count columns are >= 0."""
        for col in num_cols:
            if col in df.columns:
                neg_count = int((df[col] < 0).sum())
                self._record(
                    check_name=f"NON_NEGATIVE_VALUES ({col})",
                    table_name=table_name,
                    passed=(neg_count == 0),
                    severity="FATAL",
                    details=f"{neg_count} negative values found in {col}.",
                    failed_count=neg_count,
                )

    def validate_temporal_logic(self, df_orders: pd.DataFrame):
        """Ensure order timestamps follow chronological sequence."""
        # Delivered carrier should be >= purchase
        has_carrier = (
            df_orders["order_delivered_carrier_date"].notnull()
            & df_orders["order_purchase_timestamp"].notnull()
        )
        invalid_carrier = (
            df_orders.loc[has_carrier, "order_delivered_carrier_date"]
            < df_orders.loc[has_carrier, "order_purchase_timestamp"]
        )
        self._record(
            check_name="TEMPORAL_PURCHASE_BEFORE_CARRIER",
            table_name="orders",
            passed=(int(invalid_carrier.sum()) == 0),
            severity="WARNING",
            details=f"{int(invalid_carrier.sum())} orders where carrier date precedes purchase date.",
            failed_count=int(invalid_carrier.sum()),
        )

        # Delivered customer should be >= purchase
        has_delivery = (
            df_orders["order_delivered_customer_date"].notnull()
            & df_orders["order_purchase_timestamp"].notnull()
        )
        invalid_delivery = (
            df_orders.loc[has_delivery, "order_delivered_customer_date"]
            < df_orders.loc[has_delivery, "order_purchase_timestamp"]
        )
        self._record(
            check_name="TEMPORAL_PURCHASE_BEFORE_DELIVERED",
            table_name="orders",
            passed=(int(invalid_delivery.sum()) == 0),
            severity="FATAL",
            details=f"{int(invalid_delivery.sum())} orders where customer delivery date precedes purchase date.",
            failed_count=int(invalid_delivery.sum()),
        )

    def validate_order_statuses(self, df_orders: pd.DataFrame):
        """Validate order statuses are within standard Olist domain."""
        valid_statuses = {
            "delivered", "shipped", "canceled", "unavailable",
            "invoiced", "processing", "created", "approved"
        }
        invalid_mask = ~df_orders["order_status"].isin(valid_statuses)
        invalid_count = int(invalid_mask.sum())
        self._record(
            check_name="VALID_ORDER_STATUS_DOMAIN",
            table_name="orders",
            passed=(invalid_count == 0),
            severity="FATAL",
            details=f"{invalid_count} unexpected order statuses found.",
            failed_count=invalid_count,
        )

    def run_all_checks(self, tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Run complete suite of checks across all dimensional tables."""
        self.results = []
        logger.info("Executing Data Quality Validation Suite...")

        # Resolve tables (support both star-schema and stage names)
        df_orders = tables.get("fact_order", tables.get("orders"))
        df_customers = tables.get("dim_customer", tables.get("customers"))
        df_products = tables.get("dim_product", tables.get("products"))
        df_sellers = tables.get("dim_seller", tables.get("sellers"))
        df_items = tables.get("fact_order_item", tables.get("order_items"))
        df_payments = tables.get("fact_payment", tables.get("payments"))

        # 1. Primary Keys
        self.validate_pk_uniqueness(df_orders, "fact_order", ["order_id"])
        self.validate_pk_uniqueness(df_customers, "dim_customer", ["customer_id"])
        self.validate_pk_uniqueness(df_products, "dim_product", ["product_id"])
        self.validate_pk_uniqueness(df_sellers, "dim_seller", ["seller_id"])
        self.validate_pk_uniqueness(df_items, "fact_order_item", ["order_id", "order_item_id"])
        self.validate_pk_uniqueness(df_payments, "fact_payment", ["order_id", "payment_sequential"])

        # 2. Referential Integrity
        self.validate_referential_integrity(
            df_items, df_orders, "fact_order_item", "fact_order", "order_id"
        )
        self.validate_referential_integrity(
            df_items, df_products, "fact_order_item", "dim_product", "product_id"
        )
        self.validate_referential_integrity(
            df_items, df_sellers, "fact_order_item", "dim_seller", "seller_id"
        )
        self.validate_referential_integrity(
            df_orders, df_customers, "fact_order", "dim_customer", "customer_id"
        )

        # 3. Non-Negative Monetary
        self.validate_non_negative_values(df_items, "fact_order_item", ["price", "freight_value"])
        self.validate_non_negative_values(df_payments, "fact_payment", ["payment_value"])

        # 4. Temporal & Status Logic
        self.validate_temporal_logic(df_orders)
        self.validate_order_statuses(df_orders)

        df_report = pd.DataFrame(self.results)
        fail_count = int((df_report["status"] == "FAIL").sum())
        warn_count = int((df_report["status"] == "WARNING").sum())
        pass_count = int((df_report["status"] == "PASS").sum())

        logger.info(
            f"Data Quality Suite Finished: {pass_count} PASSED, "
            f"{warn_count} WARNINGS, {fail_count} CRITICAL FAILS."
        )
        return df_report
