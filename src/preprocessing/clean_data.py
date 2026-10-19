"""
Data Cleaning & Normalization Pipeline
Cleans and standardizes raw Olist tables for analytical modeling.
Tracks every transformation and records all cleaning operations.
"""

import logging
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class DataCleaner:
    def __init__(self):
        self.cleaning_audit: Dict[str, Any] = {}

    def clean_customers(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Clean customers table."""
        df = df_raw.copy()
        initial_count = len(df)

        # Standardize strings
        df["customer_city"] = df["customer_city"].astype(str).str.strip().str.title()
        df["customer_state"] = df["customer_state"].astype(str).str.strip().str.upper()
        df["customer_zip_code_prefix"] = pd.to_numeric(
            df["customer_zip_code_prefix"], errors="coerce"
        ).fillna(0).astype(int)

        # Remove duplicate customer_id rows if any
        df = df.drop_duplicates(subset=["customer_id"])

        self.cleaning_audit["customers"] = {
            "initial_rows": initial_count,
            "final_rows": len(df),
            "dropped_duplicates": initial_count - len(df),
            "unique_customers": df["customer_unique_id"].nunique(),
        }
        return df

    def clean_geolocation(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Deduplicate and clean geolocation data into a single representative row
        per zip_code_prefix with mean coordinates and dominant city/state.
        """
        df = df_raw.copy()
        initial_count = len(df)

        # Standardize
        df["geolocation_city"] = df["geolocation_city"].astype(str).str.strip().str.title()
        df["geolocation_state"] = df["geolocation_state"].astype(str).str.strip().str.upper()
        df["geolocation_zip_code_prefix"] = pd.to_numeric(
            df["geolocation_zip_code_prefix"], errors="coerce"
        ).fillna(0).astype(int)

        # Filter coordinates to Brazilian territory roughly (-34 to +6 lat, -74 to -30 lng)
        valid_coords = (
            (df["geolocation_lat"] >= -35.0)
            & (df["geolocation_lat"] <= 6.0)
            & (df["geolocation_lng"] >= -75.0)
            & (df["geolocation_lng"] <= -30.0)
        )
        filtered_df = df[valid_coords]

        # Aggregate coordinates by zip prefix
        geo_agg = (
            filtered_df.groupby("geolocation_zip_code_prefix")
            .agg(
                latitude=("geolocation_lat", "mean"),
                longitude=("geolocation_lng", "mean"),
                city=("geolocation_city", lambda s: s.mode()[0] if not s.empty else "Unknown"),
                state=("geolocation_state", lambda s: s.mode()[0] if not s.empty else "Unknown"),
            )
            .reset_index()
            .rename(columns={"geolocation_zip_code_prefix": "zip_code_prefix"})
        )

        self.cleaning_audit["geolocation"] = {
            "initial_rows": initial_count,
            "valid_coordinate_rows": int(valid_coords.sum()),
            "anomalous_coordinate_rows": initial_count - int(valid_coords.sum()),
            "unique_zip_prefixes": len(geo_agg),
        }
        return geo_agg

    def clean_orders(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Clean orders table and parse all datetime columns."""
        df = df_raw.copy()
        initial_count = len(df)

        # Timestamp columns
        ts_cols = [
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ]
        for col in ts_cols:
            df[col] = pd.to_datetime(df[col], errors="coerce")

        # Standardize status
        df["order_status"] = df["order_status"].astype(str).str.strip().str.lower()

        # Drop any null purchase timestamps (critical grain)
        null_purchase = df["order_purchase_timestamp"].isnull()
        df = df[~null_purchase]

        # Drop duplicate order_id if any
        df = df.drop_duplicates(subset=["order_id"])

        self.cleaning_audit["orders"] = {
            "initial_rows": initial_count,
            "final_rows": len(df),
            "null_purchase_dropped": int(null_purchase.sum()),
            "delivered_orders": int((df["order_status"] == "delivered").sum()),
            "canceled_orders": int((df["order_status"] == "canceled").sum()),
        }
        return df

    def clean_order_items(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Clean order items table."""
        df = df_raw.copy()
        initial_count = len(df)

        # Parse shipping limit date
        df["shipping_limit_date"] = pd.to_datetime(df["shipping_limit_date"], errors="coerce")

        # Numeric bounds
        df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)
        df["freight_value"] = pd.to_numeric(df["freight_value"], errors="coerce").fillna(0.0)

        # Filter out invalid negative monetary amounts
        invalid_price = (df["price"] < 0) | (df["freight_value"] < 0)
        df = df[~invalid_price]

        # Ensure order_item_id is int
        df["order_item_id"] = pd.to_numeric(df["order_item_id"], errors="coerce").fillna(1).astype(int)

        # Drop duplicates on composite primary key (order_id, order_item_id)
        df = df.drop_duplicates(subset=["order_id", "order_item_id"])

        self.cleaning_audit["order_items"] = {
            "initial_rows": initial_count,
            "final_rows": len(df),
            "invalid_price_dropped": int(invalid_price.sum()),
            "total_merchandise_value": float(df["price"].sum()),
            "total_freight_value": float(df["freight_value"].sum()),
        }
        return df

    def clean_payments(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Clean payments table."""
        df = df_raw.copy()
        initial_count = len(df)

        # Standardize strings
        df["payment_type"] = (
            df["payment_type"].astype(str).str.strip().str.lower().replace({"not_defined": "other"})
        )

        df["payment_installments"] = (
            pd.to_numeric(df["payment_installments"], errors="coerce").fillna(1).astype(int)
        )
        df["payment_value"] = pd.to_numeric(df["payment_value"], errors="coerce").fillna(0.0)
        df["payment_sequential"] = (
            pd.to_numeric(df["payment_sequential"], errors="coerce").fillna(1).astype(int)
        )

        # Non-negative payment value
        negative_val = df["payment_value"] < 0
        df = df[~negative_val]

        # Drop duplicates on (order_id, payment_sequential)
        df = df.drop_duplicates(subset=["order_id", "payment_sequential"])

        self.cleaning_audit["payments"] = {
            "initial_rows": initial_count,
            "final_rows": len(df),
            "negative_val_dropped": int(negative_val.sum()),
            "total_payment_value": float(df["payment_value"].sum()),
        }
        return df

    def clean_reviews(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Clean reviews table."""
        df = df_raw.copy()
        initial_count = len(df)

        # Parse timestamps
        df["review_creation_date"] = pd.to_datetime(df["review_creation_date"], errors="coerce")
        df["review_answer_timestamp"] = pd.to_datetime(df["review_answer_timestamp"], errors="coerce")

        # Review score must be integer between 1 and 5
        df["review_score"] = pd.to_numeric(df["review_score"], errors="coerce").fillna(0).astype(int)
        valid_score = (df["review_score"] >= 1) & (df["review_score"] <= 5)
        df = df[valid_score]

        # Clean text
        df["review_comment_title"] = df["review_comment_title"].fillna("").astype(str).str.strip()
        df["review_comment_message"] = df["review_comment_message"].fillna("").astype(str).str.strip()

        # Handle duplicates: keep newest review answer per (review_id, order_id)
        df = df.sort_values("review_answer_timestamp").drop_duplicates(
            subset=["review_id", "order_id"], keep="last"
        )

        self.cleaning_audit["reviews"] = {
            "initial_rows": initial_count,
            "final_rows": len(df),
            "invalid_score_dropped": initial_count - len(df),
            "mean_review_score": float(df["review_score"].mean()),
        }
        return df

    def clean_products(
        self, df_raw: pd.DataFrame, df_trans: pd.DataFrame = None
    ) -> pd.DataFrame:
        """Clean products and translate category names to English."""
        df = df_raw.copy()
        initial_count = len(df)

        if df_trans is not None and not df_trans.empty:
            df = df.merge(df_trans, on="product_category_name", how="left")
            df["product_category_name_english"] = (
                df["product_category_name_english"]
                .fillna(df["product_category_name"])
                .fillna("other_or_unlabeled")
                .str.replace("_", " ")
                .str.title()
            )
        else:
            df["product_category_name_english"] = (
                df["product_category_name"]
                .fillna("other_or_unlabeled")
                .str.replace("_", " ")
                .str.title()
            )

        # Numeric dimensions
        dim_cols = [
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ]
        for col in dim_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        df = df.drop_duplicates(subset=["product_id"])

        self.cleaning_audit["products"] = {
            "initial_rows": initial_count,
            "final_rows": len(df),
            "unique_categories": df["product_category_name_english"].nunique(),
        }
        return df

    def clean_sellers(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Clean sellers table."""
        df = df_raw.copy()
        initial_count = len(df)

        df["seller_city"] = df["seller_city"].astype(str).str.strip().str.title()
        df["seller_state"] = df["seller_state"].astype(str).str.strip().str.upper()
        df["seller_zip_code_prefix"] = pd.to_numeric(
            df["seller_zip_code_prefix"], errors="coerce"
        ).fillna(0).astype(int)

        df = df.drop_duplicates(subset=["seller_id"])

        self.cleaning_audit["sellers"] = {
            "initial_rows": initial_count,
            "final_rows": len(df),
            "unique_sellers": len(df),
        }
        return df

    def generate_dim_date(
        self, start_date: str = "2016-01-01", end_date: str = "2019-12-31"
    ) -> pd.DataFrame:
        """Generate comprehensive analytical calendar dimension."""
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")
        df_date = pd.DataFrame({"full_date": date_range})

        df_date["date_id"] = df_date["full_date"].dt.strftime("%Y%m%d").astype(int)
        df_date["year"] = df_date["full_date"].dt.year
        df_date["quarter"] = df_date["full_date"].dt.quarter
        df_date["month"] = df_date["full_date"].dt.month
        df_date["month_name"] = df_date["full_date"].dt.strftime("%B")
        df_date["day"] = df_date["full_date"].dt.day
        df_date["day_of_week"] = df_date["full_date"].dt.dayofweek + 1  # 1=Monday
        df_date["day_name"] = df_date["full_date"].dt.strftime("%A")
        df_date["is_weekend"] = df_date["day_of_week"].isin([6, 7]).astype(int)
        df_date["year_month"] = df_date["full_date"].dt.strftime("%Y-%m")
        df_date["year_quarter"] = (
            df_date["year"].astype(str) + "-Q" + df_date["quarter"].astype(str)
        )

        self.cleaning_audit["dim_date"] = {
            "date_range_start": start_date,
            "date_range_end": end_date,
            "total_days": len(df_date),
        }
        return df_date

    def clean_all(self, raw_tables: Dict[str, pd.DataFrame]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
        """Run complete cleaning pipeline on all raw tables."""
        logger.info("Executing comprehensive data cleaning pipeline...")
        cleaned = {}

        cleaned["customers"] = self.clean_customers(raw_tables["customers"])
        cleaned["geolocation"] = self.clean_geolocation(raw_tables["geolocation"])
        cleaned["orders"] = self.clean_orders(raw_tables["orders"])
        cleaned["order_items"] = self.clean_order_items(raw_tables["order_items"])
        cleaned["payments"] = self.clean_payments(raw_tables["payments"])
        cleaned["reviews"] = self.clean_reviews(raw_tables["reviews"])

        trans = raw_tables.get("category_translation")
        cleaned["products"] = self.clean_products(raw_tables["products"], trans)
        cleaned["sellers"] = self.clean_sellers(raw_tables["sellers"])
        cleaned["dim_date"] = self.generate_dim_date()

        logger.info("Data cleaning completed successfully.")
        return cleaned, self.cleaning_audit
