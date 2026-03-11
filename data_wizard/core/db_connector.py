"""SQLAlchemy-based database connector for SQLite, PostgreSQL, and MySQL."""

import pandas as pd
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine


DB_TYPES = {
    "sqlite":     {"label": "SQLite",      "needs_host": False},
    "postgresql": {"label": "PostgreSQL",   "needs_host": True},
    "mysql":      {"label": "MySQL",        "needs_host": True},
}


def build_connection_url(
    db_type: str,
    database: str,
    host: str = "localhost",
    port: Optional[int] = None,
    username: str = "",
    password: str = "",
) -> str:
    """Build a SQLAlchemy connection URL."""
    if db_type == "sqlite":
        return f"sqlite:///{database}"

    if db_type == "postgresql":
        port = port or 5432
        driver = "postgresql+psycopg2"
    elif db_type == "mysql":
        port = port or 3306
        driver = "mysql+pymysql"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    creds = username
    if password:
        creds += f":{password}"
    return f"{driver}://{creds}@{host}:{port}/{database}"


def create_db_engine(connection_url: str) -> Engine:
    """Create a SQLAlchemy engine from a connection URL."""
    return create_engine(connection_url)


def test_connection(engine: Engine) -> bool:
    """Test if the engine can connect. Returns True on success."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def list_tables(engine: Engine) -> List[str]:
    """List all table names in the connected database."""
    inspector = inspect(engine)
    return inspector.get_table_names()


def load_table(
    engine: Engine,
    table_name: str,
    row_limit: Optional[int] = None,
) -> pd.DataFrame:
    """Load a database table into a DataFrame."""
    if row_limit:
        query = f"SELECT * FROM {table_name} LIMIT {row_limit}"
        return pd.read_sql(text(query), engine)
    return pd.read_sql_table(table_name, engine)


def write_table(
    engine: Engine,
    df: pd.DataFrame,
    table_name: str,
    if_exists: str = "replace",
) -> int:
    """Write a DataFrame to a database table.

    Returns number of rows written.
    """
    df.to_sql(table_name, engine, if_exists=if_exists, index=False)
    return len(df)
