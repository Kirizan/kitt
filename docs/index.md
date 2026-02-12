# KITT Documentation

**End-to-end testing suite for LLM inference engines.**

KITT (Kirizan's Inference Testing Tools) measures quality consistency and
performance across LLM inference engines -- vLLM, TGI, llama.cpp, and Ollama --
so you can make informed deployment decisions backed by reproducible data.

Every engine runs in a Docker container. You supply a model path, pick an engine,
and KITT handles the rest: container lifecycle, benchmark execution, metric
collection, and result storage.

---

## Feature Highlights

<div class="grid cards" markdown>

- :material-engine: **Multi-Engine Support** -- vLLM, TGI, llama.cpp, Ollama
- :material-docker: **Docker-Only Engines** -- every engine runs in a container, no host installs
- :material-check-decagram: **Quality Benchmarks** -- MMLU, GSM8K, TruthfulQA, HellaSwag
- :material-speedometer: **Performance Benchmarks** -- throughput, latency, memory, warmup analysis
- :material-cpu-64-bit: **Hardware Fingerprinting** -- automatic GPU/CPU/RAM/storage detection
- :material-git: **KARR Git-Backed Results** -- version-controlled benchmark history
- :material-file-export: **Multiple Output Formats** -- JSON, Markdown, comparison tables
- :material-file-cog: **Custom YAML Benchmarks** -- define your own test cases in YAML
- :material-layers-triple: **Docker Deployment Stacks** -- composable `docker-compose.yaml` generation
- :material-monitor-dashboard: **Web Dashboard + REST API** -- Flask-powered UI and endpoints
- :material-chart-line: **Monitoring** -- Prometheus metrics with Grafana dashboards
- :material-pipe: **CI Integration** -- JSON output and exit codes for automated pipelines

</div>

---

## Quick Links

### [Getting Started](getting-started/index.md)

Install KITT, run your first benchmark, and explore Docker deployment workflows.

- [Installation](getting-started/installation.md) -- Docker and source install
- [Tutorial: First Benchmark](getting-started/first-benchmark.md) -- end-to-end walkthrough
- [Tutorial: Docker Quickstart](getting-started/docker-quickstart.md) -- container-based usage

### [Guides](guides/index.md)

In-depth guides for engines, benchmarks, results management, deployment, and more.

### [Reference](reference/index.md)

CLI reference, configuration schema, REST API, Docker files, and environment
variables.

### [Concepts](concepts/index.md)

Architecture overview, hardware fingerprinting, KARR repositories, engine
lifecycle, and the benchmark system.

---

## How It Works

```
 You                    KITT                     Docker
 ───                    ────                     ──────
  │  kitt run             │                        │
  │ ─────────────────────>│  docker run engine     │
  │                       │ ──────────────────────>│
  │                       │  health-check loop     │
  │                       │ <─────────────────────>│
  │                       │  run benchmarks        │
  │                       │ ──────────────────────>│
  │                       │  collect metrics       │
  │                       │ <──────────────────────│
  │  results + summary    │  docker stop           │
  │ <─────────────────────│ ──────────────────────>│
```

KITT is purpose-built for **generative LLMs** (Llama, Qwen, Mistral, and
similar). Encoder-only models such as BERT are not supported because they cannot
produce text through the inference engine APIs.
