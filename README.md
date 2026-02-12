# KITT - Kirizan's Inference Testing Tools

End-to-end testing suite for LLM inference engines. Measures quality consistency and performance across vLLM, TGI, llama.cpp, and Ollama.

[**Full Documentation**](https://kirizan.github.io/kitt/) | [**CLI Reference**](https://kirizan.github.io/kitt/reference/cli/)

## Features

- **Multi-engine support** — benchmark across vLLM, TGI, llama.cpp, and Ollama with a unified interface
- **Docker-only engines** — all engines run in Docker containers, eliminating compatibility issues
- **Quality benchmarks** — MMLU, GSM8K, TruthfulQA, and HellaSwag evaluations
- **Performance benchmarks** — throughput, latency, memory usage, and warmup analysis
- **Hardware fingerprinting** — automatic system identification for reproducible results
- **Database results storage** — SQLite (default) or PostgreSQL with queryable schema and full JSON round-tripping
- **Docker deployment stacks** — composable `docker-compose` stacks via `kitt stack`
- **Web dashboard & REST API** — browse results with TLS and token auth
- **Monitoring** — Prometheus + Grafana + InfluxDB stack generation
- **Custom benchmarks** — define evaluations with YAML configuration files

## Quick Start with Docker

```bash
# Build the KITT image
docker build -t kitt .

# Run a benchmark (mounts Docker socket for sibling containers)
docker run --rm --network host \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /path/to/models:/models:ro \
  -v ./kitt-results:/app/kitt-results \
  kitt run -m /models/llama-7b -e vllm

# Or use docker-compose
MODEL_PATH=/path/to/models docker compose run kitt run -m /models/llama-7b -e vllm
```

Generate a full deployment stack with web UI, database, and monitoring:

```bash
kitt stack generate prod --web --postgres --monitoring
kitt stack start --name prod
```

## Install from Source

```bash
poetry install          # core dependencies
eval $(poetry env activate)
poetry install -E all   # optional: install all extras (web, datasets, TUI)
```

Requires Python 3.10+, [Poetry](https://python-poetry.org/), and [Docker](https://docs.docker.com/get-docker/).

## Basic Usage

```bash
kitt fingerprint                  # detect hardware
kitt engines setup vllm           # pull engine Docker image
kitt engines list                 # check engine status
kitt run -m /models/llama-7b -e vllm -s standard -o ./results
kitt storage init                 # initialize results database
kitt storage list                 # browse stored runs
kitt storage stats                # summary statistics
```

## Documentation

| Section | Description |
|---|---|
| [Getting Started](https://kirizan.github.io/kitt/getting-started/) | Installation, first benchmark tutorial, Docker quickstart |
| [Guides](https://kirizan.github.io/kitt/guides/) | Engines, benchmarks, results, campaigns, deployment, monitoring |
| [Reference](https://kirizan.github.io/kitt/reference/) | CLI reference, config schemas, REST API, environment variables |
| [Concepts](https://kirizan.github.io/kitt/concepts/) | Architecture, fingerprinting, results storage, engine lifecycle |

## Development

```bash
poetry install --with dev
poetry run pytest
poetry run ruff check src/ tests/
```

## License

Apache 2.0
