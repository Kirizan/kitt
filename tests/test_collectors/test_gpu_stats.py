"""Tests for GPU stats collection (mocked since no GPU on dev machine)."""

import pytest
from unittest.mock import MagicMock, patch

from kitt.collectors.gpu_stats import (
    GPUMemoryStats,
    GPUMemoryTracker,
    GPUMonitor,
)


class TestGPUMemoryStats:
    def test_creation(self):
        stats = GPUMemoryStats(
            used_mb=4096.0,
            free_mb=8192.0,
            total_mb=12288.0,
            utilization_percent=45.0,
        )
        assert stats.used_mb == 4096.0
        assert stats.total_mb == 12288.0


class TestGPUMonitor:
    def test_unavailable_gracefully(self):
        """GPUMonitor gracefully handles missing NVML."""
        monitor = GPUMonitor()
        # On a machine without NVIDIA GPU, should not crash
        stats = monitor.get_memory_stats()
        # Stats will be None if no GPU
        assert stats is None or isinstance(stats, GPUMemoryStats)

    def test_all_gpus_stats_empty_when_unavailable(self):
        monitor = GPUMonitor()
        if not monitor.is_available:
            assert monitor.get_all_gpus_stats() == []


class TestGPUMemoryTracker:
    def test_tracker_no_gpu(self):
        """Tracker works without GPU (returns zeros)."""
        tracker = GPUMemoryTracker(gpu_index=0)
        with tracker:
            pass  # No-op on machine without GPU

        assert tracker.get_peak_memory_mb() == 0.0
        assert tracker.get_average_memory_mb() == 0.0
        assert tracker.get_min_memory_mb() == 0.0

    def test_tracker_with_mocked_samples(self):
        """Test tracker calculations with injected samples."""
        tracker = GPUMemoryTracker()
        tracker.samples = [
            GPUMemoryStats(used_mb=1000, free_mb=3000, total_mb=4000, utilization_percent=25),
            GPUMemoryStats(used_mb=2000, free_mb=2000, total_mb=4000, utilization_percent=50),
            GPUMemoryStats(used_mb=1500, free_mb=2500, total_mb=4000, utilization_percent=37),
        ]
        assert tracker.get_peak_memory_mb() == 2000.0
        assert tracker.get_min_memory_mb() == 1000.0
        assert abs(tracker.get_average_memory_mb() - 1500.0) < 0.01
