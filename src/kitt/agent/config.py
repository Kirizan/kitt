"""Agent daemon configuration model."""

from pathlib import Path

from pydantic import BaseModel, Field

from kitt.security.tls_config import AgentTLSConfig


class AgentDaemonConfig(BaseModel):
    """Configuration for a KITT agent daemon."""

    name: str = ""
    server_url: str = ""
    token: str = ""
    port: int = 8090
    heartbeat_interval_s: int = 30
    tls: AgentTLSConfig = Field(default_factory=AgentTLSConfig)
    config_path: Path = Field(
        default_factory=lambda: Path.home() / ".kitt" / "agent.yaml"
    )
