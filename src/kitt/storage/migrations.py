"""Simple version-based migration runner for KITT storage."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Each migration is (version, description, up_sql)
Migration = tuple[int, str, str]

MIGRATIONS: list[Migration] = [
    # Version 1 is the initial schema — applied via schema.py.
    # Future migrations go here:
    # (2, "Add campaigns table", "CREATE TABLE IF NOT EXISTS campaigns (...)"),
]


def get_current_version_sqlite(conn: Any) -> int:
    """Get current schema version from SQLite database."""
    try:
        cursor = conn.execute("SELECT MAX(version) FROM schema_version")
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0
    except Exception:
        return 0


def set_version_sqlite(conn: Any, version: int) -> None:
    """Record a schema version in SQLite."""
    conn.execute(
        "INSERT INTO schema_version (version) VALUES (?)",
        (version,),
    )
    conn.commit()


def run_migrations_sqlite(conn: Any, current_version: int) -> int:
    """Apply pending migrations to a SQLite database.

    Args:
        conn: SQLite connection.
        current_version: Current schema version.

    Returns:
        New schema version after migrations.
    """
    applied = 0
    for version, description, sql in MIGRATIONS:
        if version > current_version:
            logger.info(f"Applying migration v{version}: {description}")
            conn.executescript(sql)
            set_version_sqlite(conn, version)
            applied += 1

    if applied:
        logger.info(f"Applied {applied} migration(s)")
    return get_current_version_sqlite(conn)


def get_current_version_postgres(conn: Any) -> int:
    """Get current schema version from PostgreSQL database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(version) FROM schema_version")
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0
    except Exception:
        conn.rollback()
        return 0


def set_version_postgres(conn: Any, version: int) -> None:
    """Record a schema version in PostgreSQL."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO schema_version (version) VALUES (%s)",
        (version,),
    )
    conn.commit()


def run_migrations_postgres(conn: Any, current_version: int) -> int:
    """Apply pending migrations to a PostgreSQL database.

    Args:
        conn: psycopg2 connection.
        current_version: Current schema version.

    Returns:
        New schema version after migrations.
    """
    applied = 0
    cursor = conn.cursor()
    for version, description, sql in MIGRATIONS:
        if version > current_version:
            logger.info(f"Applying migration v{version}: {description}")
            cursor.execute(sql)
            conn.commit()
            set_version_postgres(conn, version)
            applied += 1

    if applied:
        logger.info(f"Applied {applied} migration(s)")
    return get_current_version_postgres(conn)
