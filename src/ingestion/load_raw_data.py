"""
Raw Data Loader
Loads and profiles raw CSV files from the Brazilian E-Commerce dataset.
"""

import logging
from pathlib import Path
from typing import Dict, Any
import pandas as pd

from config.settings import RAW_DATA_DIR, RAW_FILES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_raw_table(table_name: str, data_dir: Path = RAW_DATA_DIR) -> pd.DataFrame:
    """Load a single raw table by identifier name."""
    if table_name not in RAW_FILES:
        raise ValueError(f"Unknown table '{table_name}'. Valid options: {list(RAW_FILES.keys())}")

    file_path = data_dir / RAW_FILES[table_name]
    if not file_path.exists():
        raise FileNotFoundError(f"Required raw dataset file not found: {file_path}")

    logger.info(f"Loading raw table '{table_name}' from {file_path.name}...")
    return pd.read_csv(file_path)


def load_all_raw_data(data_dir: Path = RAW_DATA_DIR) -> Dict[str, pd.DataFrame]:
    """Load all 9 raw tables into a dictionary of DataFrames."""
    raw_tables = {}
    for table_name in RAW_FILES:
        raw_tables[table_name] = load_raw_table(table_name, data_dir)
        logger.info(
            f"Loaded {table_name}: {len(raw_tables[table_name]):,} rows, "
            f"{len(raw_tables[table_name].columns)} columns"
        )
    return raw_tables


def audit_raw_data(raw_tables: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Generate an audit summary of raw datasets including row count, column names,
    missing values, and memory footprint.
    """
    audit = {}
    total_memory_mb = 0.0

    for name, df in raw_tables.items():
        mem_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
        total_memory_mb += mem_mb

        null_counts = df.isnull().sum()
        cols_with_nulls = null_counts[null_counts > 0].to_dict()

        audit[name] = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "memory_mb": round(mem_mb, 2),
            "columns_with_nulls": cols_with_nulls,
        }

    audit["_summary"] = {
        "total_tables": len(raw_tables),
        "total_rows": sum(a["row_count"] for k, a in audit.items() if k != "_summary"),
        "total_memory_mb": round(total_memory_mb, 2),
    }

    return audit


if __name__ == "__main__":
    tables = load_all_raw_data()
    summary = audit_raw_data(tables)
    print("=== RAW DATA AUDIT SUMMARY ===")
    print(f"Total tables: {summary['_summary']['total_tables']}")
    print(f"Total records: {summary['_summary']['total_rows']:,}")
    print(f"Total memory: {summary['_summary']['total_memory_mb']} MB")
    for tbl, info in summary.items():
        if tbl != "_summary":
            print(f"- {tbl}: {info['row_count']:,} rows, nulls in {list(info['columns_with_nulls'].keys())}")
