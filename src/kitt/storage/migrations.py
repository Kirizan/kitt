"""Simple version-based migration runner for KITT storage."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Each migration is (version, description, up_sql)
Migration = tuple[int, str, str]

MIGRATIONS: list[Migration] = [
    # Version 1 is the initial schema — applied via schema.py.
    (
        2,
        "Add agents, web_campaigns, quick_tests, events tables",
        """
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            hostname TEXT NOT NULL,
            port INTEGER NOT NULL DEFAULT 8090,
            token TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'offline',
            gpu_info TEXT DEFAULT '',
            gpu_count INTEGER DEFAULT 0,
            cpu_info TEXT DEFAULT '',
            ram_gb INTEGER DEFAULT 0,
            environment_type TEXT DEFAULT '',
            fingerprint TEXT DEFAULT '',
            kitt_version TEXT DEFAULT '',
            last_heartbeat TEXT DEFAULT '',
            registered_at TEXT NOT NULL DEFAULT (datetime('now')),
            notes TEXT DEFAULT '',
            tags TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS web_campaigns (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            config_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            agent_id TEXT REFERENCES agents(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            started_at TEXT DEFAULT '',
            completed_at TEXT DEFAULT '',
            total_runs INTEGER DEFAULT 0,
            succeeded INTEGER DEFAULT 0,
            failed INTEGER DEFAULT 0,
            skipped INTEGER DEFAULT 0,
            error TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS quick_tests (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL REFERENCES agents(id),
            model_path TEXT NOT NULL,
            engine_name TEXT NOT NULL,
            benchmark_name TEXT NOT NULL,
            suite_name TEXT DEFAULT 'quick',
            status TEXT NOT NULL DEFAULT 'queued',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            started_at TEXT DEFAULT '',
            completed_at TEXT DEFAULT '',
            result_id TEXT REFERENCES runs(id),
            error TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_agents_name ON agents(name);
        CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
        CREATE INDEX IF NOT EXISTS idx_web_campaigns_status ON web_campaigns(status);
        CREATE INDEX IF NOT EXISTS idx_web_campaigns_agent ON web_campaigns(agent_id);
        CREATE INDEX IF NOT EXISTS idx_quick_tests_agent ON quick_tests(agent_id);
        CREATE INDEX IF NOT EXISTS idx_quick_tests_status ON quick_tests(status);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_source ON events(source_id);
        """,
    ),
    (
        3,
        "Add web_settings key-value table",
        """
        CREATE TABLE IF NOT EXISTS web_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """,
    ),
    (
        4,
        "Add per-agent token hashing columns",
        """
        ALTER TABLE agents ADD COLUMN token_hash TEXT DEFAULT '';
        ALTER TABLE agents ADD COLUMN token_prefix TEXT DEFAULT '';
        """,
    ),
    (
        5,
        "Add hardware_details JSON column to agents",
        """
        ALTER TABLE agents ADD COLUMN hardware_details TEXT DEFAULT '';
        """,
    ),
    (
        6,
        "Add command_id column to quick_tests for heartbeat dispatch",
        """
        ALTER TABLE quick_tests ADD COLUMN command_id TEXT DEFAULT '';
        """,
    ),
    (
        7,
        "Add quick_test_logs table for persistent log storage",
        """
        CREATE TABLE IF NOT EXISTS quick_test_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id TEXT NOT NULL REFERENCES quick_tests(id),
            line TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX idx_quick_test_logs_test ON quick_test_logs(test_id);
        """,
    ),
    (
        8,
        "Add agent_settings key-value table",
        """
        CREATE TABLE IF NOT EXISTS agent_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            key TEXT NOT NULL,
            value TEXT NOT NULL DEFAULT '',
            UNIQUE(agent_id, key)
        );
        CREATE INDEX IF NOT EXISTS idx_agent_settings_agent ON agent_settings(agent_id);
        """,
    ),
]


def _migrate_token_hashes(conn: Any) -> None:
    """One-time migration: hash existing raw tokens in the agents table."""
    import hashlib

    rows = conn.execute(
        "SELECT id, token FROM agents WHERE token != '' AND token_hash = ''"
    ).fetchall()
    for row in rows:
        token_hash = hashlib.sha256(row["token"].encode()).hexdigest()
        token_prefix = row["token"][:8]
        conn.execute(
            "UPDATE agents SET token_hash = ?, token_prefix = ?, token = '' WHERE id = ?",
            (token_hash, token_prefix, row["id"]),
        )
    if rows:
        conn.commit()
        logger.info("Migrated %d agent token(s) to hashed storage", len(rows))


_DEFAULT_AGENT_SETTINGS = {
    "model_storage_dir": "~/.kitt/models",
    "model_share_source": "",
    "model_share_mount": "",
    "auto_cleanup": "true",
    "heartbeat_interval_s": "30",
    "kitt_image": "",
}


def _insert_default_agent_settings(conn: Any) -> None:
    """Insert default settings for all existing agents that lack them."""
    rows = conn.execute("SELECT id FROM agents").fetchall()
    for row in rows:
        agent_id = row["id"] if hasattr(row, "keys") else row[0]
        for key, value in _DEFAULT_AGENT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO agent_settings (agent_id, key, value) VALUES (?, ?, ?)",
                (agent_id, key, value),
            )
    if rows:
        conn.commit()
        logger.info("Inserted default settings for %d agent(s)", len(rows))


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
            logger.info("Applying migration v%d: %s", version, description)
            conn.executescript(sql)
            set_version_sqlite(conn, version)
            applied += 1
            # Hash existing raw tokens after v4 schema change
            if version == 4:
                _migrate_token_hashes(conn)
            # Insert default agent settings for all existing agents
            if version == 8:
                _insert_default_agent_settings(conn)

    if applied:
        logger.info("Applied %d migration(s)", applied)
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
            logger.info("Applying migration v%d: %s", version, description)
            cursor.execute(sql)
            conn.commit()
            set_version_postgres(conn, version)
            applied += 1

    if applied:
        logger.info("Applied %d migration(s)", applied)
    return get_current_version_postgres(conn)
