"""Pydantic models for campaign configuration."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CampaignModelSpec(BaseModel):
    """Specification for a model to benchmark in a campaign."""

    name: str
    params: str = ""
    safetensors_repo: Optional[str] = None
    gguf_repo: Optional[str] = None
    ollama_tag: Optional[str] = None
    estimated_size_gb: float = 0.0


class CampaignEngineSpec(BaseModel):
    """Engine configuration for a campaign."""

    name: str
    config: Dict[str, Any] = Field(default_factory=dict)
    suite: str = "standard"
    formats: List[str] = Field(default_factory=list)


class DiskConfig(BaseModel):
    """Disk space management configuration."""

    reserve_gb: float = Field(default=100.0, ge=0.0)
    storage_path: Optional[str] = None
    cleanup_after_run: bool = True


class NotificationConfig(BaseModel):
    """Notification settings for campaign events."""

    webhook_url: Optional[str] = None
    email: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    desktop: bool = False
    on_complete: bool = True
    on_failure: bool = True


class ResourceLimitsConfig(BaseModel):
    """Resource-based skip rules for campaign runs.

    Models/quants whose estimated loaded size exceeds max_model_size_gb
    are skipped automatically. Set to 0 to disable (no limit).
    """

    max_model_size_gb: float = Field(
        default=0.0,
        ge=0.0,
        description="Skip runs where estimated model size exceeds this limit (0 = no limit)",
    )


class QuantFilterConfig(BaseModel):
    """Filter rules for quantization variants."""

    skip_patterns: List[str] = Field(default_factory=list)
    include_only: List[str] = Field(default_factory=list)


class CampaignRunSpec(BaseModel):
    """A single planned benchmark run within a campaign."""

    model_name: str
    engine_name: str
    quant: str
    model_path: Optional[str] = None
    repo_id: Optional[str] = None
    include_pattern: Optional[str] = None
    estimated_size_gb: float = 0.0
    suite: str = "standard"
    engine_config: Dict[str, Any] = Field(default_factory=dict)

    @property
    def key(self) -> str:
        """Unique identifier for this run."""
        return f"{self.model_name}|{self.engine_name}|{self.quant}"


class CampaignConfig(BaseModel):
    """Top-level campaign configuration."""

    campaign_name: str
    description: str = ""
    models: List[CampaignModelSpec] = Field(default_factory=list)
    engines: List[CampaignEngineSpec] = Field(default_factory=list)
    disk: DiskConfig = Field(default_factory=DiskConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    quant_filter: QuantFilterConfig = Field(default_factory=QuantFilterConfig)
    resource_limits: ResourceLimitsConfig = Field(default_factory=ResourceLimitsConfig)
    parallel: bool = False
    devon_managed: bool = True
