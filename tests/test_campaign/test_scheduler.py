"""Tests for campaign scheduler."""

import pytest

from kitt.campaign.models import (
    CampaignConfig,
    CampaignEngineSpec,
    CampaignModelSpec,
    CampaignRunSpec,
    DiskConfig,
)
from kitt.campaign.scheduler import CampaignScheduler
from kitt.campaign.state_manager import CampaignState, RunState


@pytest.fixture
def scheduler():
    return CampaignScheduler(DiskConfig(reserve_gb=50.0))


@pytest.fixture
def sample_config():
    return CampaignConfig(
        campaign_name="test",
        models=[
            CampaignModelSpec(
                name="Llama-8B",
                params="8B",
                safetensors_repo="meta-llama/Llama-3.1-8B",
                gguf_repo="bartowski/Llama-3.1-8B-GGUF",
                ollama_tag="llama3.1:8b",
                estimated_size_gb=16.0,
            ),
            CampaignModelSpec(
                name="Qwen-7B",
                params="7B",
                gguf_repo="Qwen/Qwen2.5-7B-GGUF",
                ollama_tag="qwen2.5:7b",
                estimated_size_gb=14.0,
            ),
        ],
        engines=[
            CampaignEngineSpec(name="vllm"),
            CampaignEngineSpec(name="llama_cpp"),
            CampaignEngineSpec(name="ollama"),
        ],
    )


class TestCampaignScheduler:
    def test_plan_runs(self, scheduler, sample_config):
        runs = scheduler.plan_runs(sample_config)
        # Llama-8B: vllm(bf16) + llama_cpp(discover) + ollama(discover) = 3
        # Qwen-7B: no safetensors_repo so no vllm + llama_cpp(discover) + ollama(discover) = 2
        assert len(runs) == 5

    def test_plan_runs_vllm_only_with_safetensors(self, scheduler, sample_config):
        runs = scheduler.plan_runs(sample_config)
        vllm_runs = [r for r in runs if r.engine_name == "vllm"]
        assert len(vllm_runs) == 1
        assert vllm_runs[0].model_name == "Llama-8B"
        assert vllm_runs[0].quant == "bf16"

    def test_order_by_size(self, scheduler):
        runs = [
            CampaignRunSpec(model_name="Big", engine_name="e", quant="q", estimated_size_gb=70.0),
            CampaignRunSpec(model_name="Small", engine_name="e", quant="q", estimated_size_gb=4.0),
            CampaignRunSpec(model_name="Med", engine_name="e", quant="q", estimated_size_gb=16.0),
        ]
        ordered = scheduler.order_by_size(runs)
        assert ordered[0].model_name == "Small"
        assert ordered[1].model_name == "Med"
        assert ordered[2].model_name == "Big"

    def test_filter_completed(self, scheduler):
        runs = [
            CampaignRunSpec(model_name="M1", engine_name="e1", quant="q1"),
            CampaignRunSpec(model_name="M2", engine_name="e1", quant="q1"),
        ]
        state = CampaignState(campaign_id="t", campaign_name="t")
        state.runs = [RunState("M1", "e1", "q1", "success")]

        remaining = scheduler.filter_completed(runs, state)
        assert len(remaining) == 1
        assert remaining[0].model_name == "M2"

    def test_check_disk_space_passes(self, scheduler):
        """Should pass when disk has plenty of space (checking home dir)."""
        run = CampaignRunSpec(
            model_name="test", engine_name="e", quant="q",
            estimated_size_gb=1.0,
        )
        # This tests against actual disk — should pass in any CI/dev environment
        assert scheduler.check_disk_space(run) is True

    def test_should_skip_returns_false_normally(self, scheduler):
        run = CampaignRunSpec(
            model_name="test", engine_name="e", quant="q",
            estimated_size_gb=0.1,
        )
        assert scheduler.should_skip(run) is False
