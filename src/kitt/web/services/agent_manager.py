"""Agent lifecycle management service.

Manages agent registration, heartbeats, command dispatch,
and status tracking.
"""

import hashlib
import hmac
import logging
import secrets
import sqlite3
import time
import uuid
from datetime import datetime
from typing import Any

from kitt.web.models.agent import AgentHeartbeat, AgentRegistration
from kitt.web.services.event_bus import event_bus

logger = logging.getLogger(__name__)

# Agent is considered offline if no heartbeat for this many seconds
HEARTBEAT_TIMEOUT_S = 90


class AgentManager:
    """Manages agent lifecycle and command dispatch."""

    def __init__(self, db_conn: sqlite3.Connection) -> None:
        self._conn = db_conn

    @staticmethod
    def _hash_token(token: str) -> str:
        """Compute SHA-256 hash of a token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    def provision(self, name: str, port: int = 8090) -> dict[str, Any]:
        """Provision a new agent with a unique token.

        If an agent with the same name already exists, rotates its token.

        Returns:
            Dict with agent_id, raw token (one-time), and token_prefix.
        """
        raw_token = secrets.token_hex(32)
        token_hash = self._hash_token(raw_token)
        token_prefix = raw_token[:8]
        now = datetime.now().isoformat()

        row = self._conn.execute(
            "SELECT id FROM agents WHERE name = ?", (name,)
        ).fetchone()

        if row:
            agent_id = row["id"]
            self._conn.execute(
                "UPDATE agents SET token_hash = ?, token_prefix = ?, port = ? WHERE id = ?",
                (token_hash, token_prefix, port, agent_id),
            )
            logger.info(f"Rotated token for existing agent: {name} ({agent_id})")
        else:
            agent_id = uuid.uuid4().hex[:16]
            self._conn.execute(
                """INSERT INTO agents
                   (id, name, hostname, port, token, token_hash, token_prefix,
                    status, registered_at)
                   VALUES (?, ?, ?, ?, '', ?, ?, 'provisioned', ?)""",
                (agent_id, name, name, port, token_hash, token_prefix, now),
            )
            logger.info(f"Provisioned new agent: {name} ({agent_id})")

        self._conn.commit()
        self._ensure_default_settings(agent_id)
        return {
            "agent_id": agent_id,
            "token": raw_token,
            "token_prefix": token_prefix,
        }

    def register(self, reg: AgentRegistration, token: str) -> dict[str, Any]:
        """Register a new agent or update an existing one.

        Returns:
            Dict with agent_id and heartbeat_interval_s.
        """
        # Check if agent with this name already exists
        row = self._conn.execute(
            "SELECT id FROM agents WHERE name = ?", (reg.name,)
        ).fetchone()

        now = datetime.now().isoformat()
        token_hash = self._hash_token(token) if token else ""

        if row:
            agent_id = row["id"]
            self._conn.execute(
                """UPDATE agents SET
                    hostname = ?, port = ?, status = 'online',
                    gpu_info = ?, gpu_count = ?, cpu_info = ?, ram_gb = ?,
                    environment_type = ?, fingerprint = ?, kitt_version = ?,
                    hardware_details = ?,
                    last_heartbeat = ?
                   WHERE id = ?""",
                (
                    reg.hostname,
                    reg.port,
                    reg.gpu_info,
                    reg.gpu_count,
                    reg.cpu_info,
                    reg.ram_gb,
                    reg.environment_type,
                    reg.fingerprint,
                    reg.kitt_version,
                    reg.hardware_details,
                    now,
                    agent_id,
                ),
            )
        else:
            agent_id = uuid.uuid4().hex[:16]
            self._conn.execute(
                """INSERT INTO agents
                   (id, name, hostname, port, token, token_hash, token_prefix,
                    status, gpu_info, gpu_count,
                    cpu_info, ram_gb, environment_type, fingerprint, kitt_version,
                    hardware_details,
                    last_heartbeat, registered_at)
                   VALUES (?, ?, ?, ?, '', ?, ?, 'online', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    agent_id,
                    reg.name,
                    reg.hostname,
                    reg.port,
                    token_hash,
                    token[:8] if token else "",
                    reg.gpu_info,
                    reg.gpu_count,
                    reg.cpu_info,
                    reg.ram_gb,
                    reg.environment_type,
                    reg.fingerprint,
                    reg.kitt_version,
                    reg.hardware_details,
                    now,
                    now,
                ),
            )

        self._conn.commit()
        self._ensure_default_settings(agent_id)
        event_bus.publish(
            "agent_status",
            agent_id,
            {
                "name": reg.name,
                "status": "online",
            },
        )

        return {"agent_id": agent_id, "heartbeat_interval_s": 30}

    def heartbeat(self, agent_id: str, hb: AgentHeartbeat) -> dict[str, Any]:
        """Process agent heartbeat.

        Checks for pending quick_tests assigned to this agent and returns
        them as commands for the agent to execute.

        Returns:
            Dict with ack and any pending commands.
        """
        now = datetime.now().isoformat()
        self._conn.execute(
            """UPDATE agents SET
                status = ?, last_heartbeat = ?
               WHERE id = ?""",
            (hb.status or "idle", now, agent_id),
        )
        self._conn.commit()

        # Check for queued quick_tests assigned to this agent
        commands: list[dict[str, Any]] = []
        rows = self._conn.execute(
            """SELECT id, command_id, model_path, engine_name, benchmark_name,
                      suite_name
               FROM quick_tests
               WHERE agent_id = ? AND status = 'queued'
               ORDER BY created_at
               LIMIT 1""",
            (agent_id,),
        ).fetchall()

        for row in rows:
            test_id = row["id"]
            # Determine command type: cleanup rows use engine_name='cleanup'
            if row["engine_name"] == "cleanup":
                cmd_type = "cleanup_storage"
            else:
                cmd_type = "run_test"
            commands.append(
                {
                    "command_id": row["command_id"],
                    "test_id": test_id,
                    "type": cmd_type,
                    "payload": {
                        "model_path": row["model_path"],
                        "engine_name": row["engine_name"],
                        "benchmark_name": row["benchmark_name"],
                        "suite_name": row["suite_name"],
                    },
                }
            )
            # Mark as dispatched
            self._conn.execute(
                "UPDATE quick_tests SET status = 'dispatched' WHERE id = ?",
                (test_id,),
            )
            event_bus.publish(
                "status",
                test_id,
                {"status": "dispatched", "test_id": test_id},
            )

        if commands:
            self._conn.commit()
            logger.info(
                "Dispatched %d command(s) to agent %s via heartbeat",
                len(commands),
                agent_id,
            )

        settings = self.get_agent_settings(agent_id)
        return {"ack": True, "commands": commands, "settings": settings}

    # Fields that must never appear in API responses.
    _SENSITIVE_FIELDS = {"token", "token_hash"}

    def _sanitize(self, row: dict[str, Any]) -> dict[str, Any]:
        """Strip sensitive fields from an agent dict before returning."""
        return {k: v for k, v in row.items() if k not in self._SENSITIVE_FIELDS}

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        """Get full agent details."""
        row = self._conn.execute(
            "SELECT * FROM agents WHERE id = ?", (agent_id,)
        ).fetchone()
        if row is None:
            return None
        return self._sanitize(dict(row))

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents."""
        self._check_stale_agents()
        rows = self._conn.execute("SELECT * FROM agents ORDER BY name").fetchall()
        return [self._sanitize(dict(r)) for r in rows]

    def delete_agent(self, agent_id: str) -> bool:
        """Remove an agent registration."""
        cursor = self._conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def update_agent(self, agent_id: str, updates: dict[str, Any]) -> bool:
        """Update agent fields (notes, tags, etc.)."""
        allowed = {"notes", "tags"}
        to_set = {k: v for k, v in updates.items() if k in allowed}
        if not to_set:
            return False

        clauses = ", ".join(f"{k} = ?" for k in to_set)
        values = list(to_set.values()) + [agent_id]
        self._conn.execute(f"UPDATE agents SET {clauses} WHERE id = ?", values)
        self._conn.commit()
        return True

    def verify_token(self, agent_id: str, token: str) -> bool:
        """Verify that a token matches the registered agent.

        Checks token_hash first (new hashed storage), falls back to
        legacy raw token column for backward compatibility.
        Returns True if the agent has no token configured (empty hash and token).
        """
        row = self._conn.execute(
            "SELECT token, token_hash FROM agents WHERE id = ?", (agent_id,)
        ).fetchone()
        if row is None:
            return False

        stored_hash = row["token_hash"] or ""
        stored_raw = row["token"] or ""

        # No token configured on this agent — allow (dev/migration compat)
        if not stored_hash and not stored_raw:
            return True

        # Prefer hash-based verification
        if stored_hash:
            provided_hash = self._hash_token(token)
            return hmac.compare_digest(provided_hash, stored_hash)

        # Fall back to legacy raw token comparison
        return hmac.compare_digest(token, stored_raw)

    def rotate_token(self, agent_id: str) -> dict[str, Any] | None:
        """Generate a new token for an existing agent.

        Returns:
            Dict with raw token and prefix, or None if agent not found.
        """
        row = self._conn.execute(
            "SELECT id FROM agents WHERE id = ?", (agent_id,)
        ).fetchone()
        if row is None:
            return None

        raw_token = secrets.token_hex(32)
        token_hash = self._hash_token(raw_token)
        token_prefix = raw_token[:8]

        self._conn.execute(
            "UPDATE agents SET token_hash = ?, token_prefix = ?, token = '' WHERE id = ?",
            (token_hash, token_prefix, agent_id),
        )
        self._conn.commit()
        logger.info(f"Rotated token for agent {agent_id}")

        return {"token": raw_token, "token_prefix": token_prefix}

    # --- Agent settings ---

    _DEFAULT_SETTINGS = {
        "model_storage_dir": "~/.kitt/models",
        "model_share_source": "",
        "model_share_mount": "",
        "auto_cleanup": "true",
        "heartbeat_interval_s": "30",
    }

    def _ensure_default_settings(self, agent_id: str) -> None:
        """Insert default settings for an agent if they don't exist."""
        for key, value in self._DEFAULT_SETTINGS.items():
            self._conn.execute(
                "INSERT OR IGNORE INTO agent_settings (agent_id, key, value) VALUES (?, ?, ?)",
                (agent_id, key, value),
            )
        self._conn.commit()

    def get_agent_settings(self, agent_id: str) -> dict[str, str]:
        """Get all settings for an agent as a flat dict."""
        rows = self._conn.execute(
            "SELECT key, value FROM agent_settings WHERE agent_id = ?",
            (agent_id,),
        ).fetchall()
        return {row["key"]: row["value"] for row in rows}

    def update_agent_settings(self, agent_id: str, updates: dict[str, str]) -> bool:
        """Upsert agent settings. Returns True if any rows were affected."""
        # Validate keys against known settings
        valid_keys = set(self._DEFAULT_SETTINGS.keys())
        filtered = {k: str(v) for k, v in updates.items() if k in valid_keys}
        if not filtered:
            return False

        for key, value in filtered.items():
            self._conn.execute(
                """INSERT INTO agent_settings (agent_id, key, value)
                   VALUES (?, ?, ?)
                   ON CONFLICT(agent_id, key) DO UPDATE SET value = excluded.value""",
                (agent_id, key, value),
            )
        self._conn.commit()
        return True

    def _check_stale_agents(self) -> None:
        """Mark agents as offline if heartbeat is stale."""
        rows = self._conn.execute(
            "SELECT id, last_heartbeat FROM agents WHERE status != 'offline'"
        ).fetchall()

        now = time.time()
        for row in rows:
            if row["last_heartbeat"]:
                try:
                    hb_time = datetime.fromisoformat(row["last_heartbeat"])
                    age = now - hb_time.timestamp()
                    if age > HEARTBEAT_TIMEOUT_S:
                        self._conn.execute(
                            "UPDATE agents SET status = 'offline' WHERE id = ?",
                            (row["id"],),
                        )
                except (ValueError, OSError):
                    pass

        self._conn.commit()
