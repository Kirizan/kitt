"""Web settings persistence service.

Stores key-value UI settings in the web_settings SQLite table.
"""

import logging
import sqlite3

logger = logging.getLogger(__name__)

# Defaults applied when a key has no stored value.
_DEFAULTS: dict[str, str] = {
    "devon_tab_visible": "true",
}


class SettingsService:
    """Read/write web UI settings backed by SQLite."""

    def __init__(self, db_conn: sqlite3.Connection) -> None:
        self._conn = db_conn

    def get(self, key: str, default: str | None = None) -> str:
        """Get a setting value, falling back to built-in defaults."""
        row = self._conn.execute(
            "SELECT value FROM web_settings WHERE key = ?", (key,)
        ).fetchone()
        if row is not None:
            return row["value"] if isinstance(row, sqlite3.Row) else row[0]
        if default is not None:
            return default
        return _DEFAULTS.get(key, "")

    def set(self, key: str, value: str) -> None:
        """Upsert a setting value."""
        self._conn.execute(
            "INSERT INTO web_settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self._conn.commit()

    def get_all(self) -> dict[str, str]:
        """Return all stored settings merged with defaults."""
        settings = dict(_DEFAULTS)
        rows = self._conn.execute("SELECT key, value FROM web_settings").fetchall()
        for row in rows:
            k = row["key"] if isinstance(row, sqlite3.Row) else row[0]
            v = row["value"] if isinstance(row, sqlite3.Row) else row[1]
            settings[k] = v
        return settings

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a setting as a boolean."""
        val = self.get(key, str(default).lower())
        return val.lower() in ("true", "1", "yes")
