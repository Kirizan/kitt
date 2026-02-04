"""Shared HTTP client for OpenAI-compatible /v1/completions endpoints.

Used by vLLM and llama.cpp engines which expose OpenAI-compatible APIs.
Uses urllib.request (no external dependencies).
"""

import json
import logging
import urllib.request
from datetime import datetime
from typing import Any, Dict

from .base import GenerationMetrics, GenerationResult

logger = logging.getLogger(__name__)


def openai_generate(
    base_url: str,
    prompt: str,
    model: str = "default",
    temperature: float = 0.0,
    top_p: float = 1.0,
    top_k: int = 50,
    max_tokens: int = 2048,
) -> Dict[str, Any]:
    """Send a completion request to an OpenAI-compatible endpoint.

    Args:
        base_url: Base URL of the server (e.g. "http://localhost:8000").
        prompt: Input prompt text.
        model: Model name to pass in the request.
        temperature: Sampling temperature.
        top_p: Nucleus sampling parameter.
        top_k: Top-k sampling parameter (ignored by standard OpenAI API).
        max_tokens: Maximum tokens to generate.

    Returns:
        Parsed JSON response dict.

    Raises:
        RuntimeError: If the request fails.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }

    data = json.dumps(payload).encode("utf-8")
    url = f"{base_url.rstrip('/')}/v1/completions"
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"OpenAI API request failed ({e.code}): {body}"
        )
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Cannot connect to engine at {base_url}: {e}"
        )


def parse_openai_result(
    response: Dict[str, Any],
    total_latency_ms: float,
    gpu_tracker: Any,
) -> GenerationResult:
    """Parse an OpenAI completions response into a GenerationResult.

    Args:
        response: Parsed JSON response from the OpenAI API.
        total_latency_ms: Total request latency in milliseconds.
        gpu_tracker: GPUMemoryTracker instance with memory samples.

    Returns:
        GenerationResult with extracted metrics.
    """
    choices = response.get("choices", [])
    output = choices[0]["text"] if choices else ""

    usage = response.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)

    tps = (
        completion_tokens / (total_latency_ms / 1000)
        if total_latency_ms > 0 and completion_tokens > 0
        else 0
    )

    metrics = GenerationMetrics(
        ttft_ms=0,
        tps=tps,
        total_latency_ms=total_latency_ms,
        gpu_memory_peak_gb=gpu_tracker.get_peak_memory_mb() / 1024,
        gpu_memory_avg_gb=gpu_tracker.get_average_memory_mb() / 1024,
        timestamp=datetime.now(),
    )

    return GenerationResult(
        output=output,
        metrics=metrics,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
