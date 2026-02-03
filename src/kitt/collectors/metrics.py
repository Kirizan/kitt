"""Base metrics collection utilities."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class MetricsSample:
    """A single metrics sample at a point in time."""

    timestamp: datetime
    values: Dict[str, Any]


@dataclass
class MetricsCollection:
    """Collection of metrics samples over time."""

    name: str
    samples: List[MetricsSample] = field(default_factory=list)

    def add_sample(self, values: Dict[str, Any]) -> None:
        """Add a metrics sample with current timestamp."""
        self.samples.append(
            MetricsSample(timestamp=datetime.now(), values=values)
        )

    def get_latest(self) -> Dict[str, Any]:
        """Get the most recent sample values."""
        if not self.samples:
            return {}
        return self.samples[-1].values

    def get_averages(self) -> Dict[str, float]:
        """Get average values across all samples (numeric only)."""
        if not self.samples:
            return {}

        totals: Dict[str, float] = {}
        counts: Dict[str, int] = {}

        for sample in self.samples:
            for key, value in sample.values.items():
                if isinstance(value, (int, float)):
                    totals[key] = totals.get(key, 0) + value
                    counts[key] = counts.get(key, 0) + 1

        return {
            key: totals[key] / counts[key] for key in totals
        }
