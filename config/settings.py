"""
Global Configuration & Settings
E-Commerce Business Intelligence & Customer Analytics Platform
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Data Directories
CANDIDATE_DATA_DIRS = [
    PROJECT_ROOT / "Brazilian E-Commerce Public Dataset",
    PROJECT_ROOT / "data" / "raw",
    PROJECT_ROOT / "data",
]


def resolve_data_dir() -> Path:
    """Find the first existing data directory containing raw Olist CSVs."""
    env_dir = os.getenv("DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        if p.exists():
            return p

    for candidate in CANDIDATE_DATA_DIRS:
        if candidate.exists() and (candidate / "olist_orders_dataset.csv").exists():
            return candidate

    # Default fallback
    return PROJECT_ROOT / "Brazilian E-Commerce Public Dataset"


RAW_DATA_DIR = resolve_data_dir()
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database Backend Configuration
# Supports both PostgreSQL (production/docker) and DuckDB (local high-performance embedded)
DB_BACKEND = os.getenv("DB_BACKEND", "duckdb").lower()

# PostgreSQL Credentials
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "olist_bi")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

POSTGRES_URL = (
    f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# DuckDB Local Embedded Analytical Database
DUCKDB_PATH = Path(
    os.getenv("DUCKDB_PATH", str(PROCESSED_DATA_DIR / "ecommerce_bi.duckdb"))
)
if not DUCKDB_PATH.is_absolute():
    DUCKDB_PATH = PROJECT_ROOT / DUCKDB_PATH

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

# Business Intelligence Reference Constants
# Dataset spans Sep 2016 - Oct 2018; reference date for RFM is snapshot date
RFM_REFERENCE_DATE = "2018-10-18"
SELLER_MIN_ORDERS_THRESHOLD = 10
DELIVERY_ON_TIME_THRESHOLD_DAYS = 0.0

# Expected Raw Files Mapping
RAW_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}
