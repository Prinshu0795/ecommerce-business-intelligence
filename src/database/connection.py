"""
Database Connection Manager
Provides unified, resilient access to PostgreSQL and DuckDB analytical engines.
"""

import logging
from typing import Optional, Any
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import duckdb

from config.settings import (
    DB_BACKEND,
    POSTGRES_URL,
    DUCKDB_PATH,
    PROCESSED_DATA_DIR,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


import re

class DatabaseManager:
    """Manages database engines and connections with automatic fallback."""

    def __init__(self, backend: Optional[str] = None, read_only: bool = True):
        self.requested_backend = (backend or DB_BACKEND).lower()
        self.read_only = read_only
        self.active_backend: str = "duckdb"
        self._pg_engine: Optional[Engine] = None
        self._duck_conn: Optional[duckdb.DuckDBPyConnection] = None
        self._init_connection()

    def _init_connection(self):
        """Initialize connection based on configuration and availability."""
        if self.requested_backend in ("postgres", "postgresql"):
            try:
                engine = create_engine(POSTGRES_URL, pool_pre_ping=True, connect_args={"connect_timeout": 3})
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1;"))
                self._pg_engine = engine
                self.active_backend = "postgresql"
                logger.info("Successfully connected to PostgreSQL database.")
                return
            except Exception as e:
                logger.warning(
                    f"PostgreSQL connection to {POSTGRES_URL} failed ({e}). "
                    f"Falling back to embedded DuckDB engine at {DUCKDB_PATH}."
                )

        # Fallback to DuckDB
        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        if DUCKDB_PATH.exists() and self.read_only:
            try:
                self._duck_conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)
            except Exception:
                self._duck_conn = duckdb.connect(str(DUCKDB_PATH), read_only=False)
        else:
            self._duck_conn = duckdb.connect(str(DUCKDB_PATH), read_only=False)

        self.active_backend = "duckdb"
        logger.info(f"Active database backend: DuckDB ({DUCKDB_PATH})")

    def execute_query(self, sql: str, params: Optional[dict] = None) -> Any:
        """Execute a DDL or DML statement."""
        if self.active_backend == "postgresql" and self._pg_engine:
            with self._pg_engine.begin() as conn:
                return conn.execute(text(sql), params or {})
        else:
            if params:
                sql_duck = re.sub(r':([a-zA-Z0-9_]+)', r'$\1', sql)
                return self._duck_conn.execute(sql_duck, params)
            return self._duck_conn.execute(sql)

    def query_to_dataframe(self, sql: str, params: Optional[dict] = None) -> pd.DataFrame:
        """Execute a SELECT query and return results as a pandas DataFrame."""
        if self.active_backend == "postgresql" and self._pg_engine:
            with self._pg_engine.connect() as conn:
                return pd.read_sql_query(text(sql), conn, params=params)
        else:
            if params:
                sql_duck = re.sub(r':([a-zA-Z0-9_]+)', r'$\1', sql)
                return self._duck_conn.execute(sql_duck, params).df()
            return self._duck_conn.execute(sql).df()

    def get_duckdb_connection(self) -> duckdb.DuckDBPyConnection:
        """Return raw DuckDB connection."""
        if self._duck_conn is None:
            self._duck_conn = duckdb.connect(str(DUCKDB_PATH))
        return self._duck_conn

    def close(self):
        """Close connections."""
        if self._pg_engine:
            self._pg_engine.dispose()
        if self._duck_conn:
            self._duck_conn.close()


# Module-level singleton instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(read_only: bool = True) -> DatabaseManager:
    """Get or initialize singleton DatabaseManager instance."""
    global _db_manager
    if _db_manager is None or getattr(_db_manager, "read_only", True) != read_only:
        _db_manager = DatabaseManager(read_only=read_only)
    return _db_manager


def query_df(sql: str, params: Optional[dict] = None) -> pd.DataFrame:
    """Convenience function to run SQL query and return DataFrame."""
    return get_db_manager().query_to_dataframe(sql, params)


def execute_sql(sql: str, params: Optional[dict] = None) -> Any:
    """Convenience function to execute SQL DDL/DML."""
    return get_db_manager().execute_query(sql, params)
