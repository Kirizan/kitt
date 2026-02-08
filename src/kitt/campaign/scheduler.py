"""Campaign run scheduling with disk-awareness."""

import logging
import shutil
from pathlib import Path
from typing import List, Optional

from .models import CampaignConfig, CampaignRunSpec, DiskConfig
from .state_manager import CampaignState

logger = logging.getLogger(__name__)


class CampaignScheduler:
    """Schedule campaign runs with disk space awareness.

    Orders runs by estimated size and skips runs that would exceed
    the configured disk reserve.
    """

    def __init__(self, disk_config: DiskConfig) -> None:
        self.disk_config = disk_config

    def plan_runs(self, config: CampaignConfig) -> List[CampaignRunSpec]:
        """Generate ordered list of runs from campaign config.

        Produces one CampaignRunSpec per (model, engine, quant) combination.
        For safetensors models, quant is "bf16". For GGUF/Ollama, quants
        are discovered dynamically at runtime — here we produce placeholders
        that the runner will expand.
        """
        runs: List[CampaignRunSpec] = []

        for model in config.models:
            for engine in config.engines:
                if engine.name == "vllm" and model.safetensors_repo:
                    runs.append(CampaignRunSpec(
                        model_name=model.name,
                        engine_name=engine.name,
                        quant="bf16",
                        repo_id=model.safetensors_repo,
                        estimated_size_gb=model.estimated_size_gb,
                        suite=engine.suite,
                        engine_config=engine.config,
                    ))
                elif engine.name in ("llama_cpp", "exllamav2") and model.gguf_repo:
                    # Placeholder — actual quants discovered at runtime
                    runs.append(CampaignRunSpec(
                        model_name=model.name,
                        engine_name=engine.name,
                        quant="__discover_gguf__",
                        repo_id=model.gguf_repo,
                        estimated_size_gb=model.estimated_size_gb,
                        suite=engine.suite,
                        engine_config=engine.config,
                    ))
                elif engine.name == "ollama" and model.ollama_tag:
                    # Placeholder — actual tags discovered at runtime
                    runs.append(CampaignRunSpec(
                        model_name=model.name,
                        engine_name=engine.name,
                        quant="__discover_ollama__",
                        repo_id=model.ollama_tag,
                        estimated_size_gb=model.estimated_size_gb,
                        suite=engine.suite,
                        engine_config=engine.config,
                    ))

        return runs

    def order_by_size(self, runs: List[CampaignRunSpec]) -> List[CampaignRunSpec]:
        """Order runs by estimated size (smallest first) to maximize throughput."""
        return sorted(runs, key=lambda r: r.estimated_size_gb)

    def filter_completed(
        self, runs: List[CampaignRunSpec], state: CampaignState
    ) -> List[CampaignRunSpec]:
        """Remove runs that are already completed (for resume)."""
        return [r for r in runs if r.key not in state.completed_keys]

    def check_disk_space(
        self, run: CampaignRunSpec, storage_path: Optional[str] = None
    ) -> bool:
        """Check if there's enough disk space for a run."""
        path = storage_path or str(Path.home())
        try:
            usage = shutil.disk_usage(path)
            free_gb = usage.free / (1024 ** 3)
        except OSError:
            logger.warning(f"Could not check disk space at {path}")
            return True

        required = self.disk_config.reserve_gb + run.estimated_size_gb
        if free_gb < required:
            logger.warning(
                f"Insufficient disk space for {run.key}: "
                f"{free_gb:.1f}GB free, need {required:.1f}GB "
                f"(reserve={self.disk_config.reserve_gb}GB + "
                f"model={run.estimated_size_gb}GB)"
            )
            return False
        return True

    def should_skip(self, run: CampaignRunSpec) -> bool:
        """Check if a run should be skipped based on disk constraints."""
        return not self.check_disk_space(
            run, self.disk_config.storage_path
        )
