# KITT - Kirizan's Inference Testing Tools

End-to-end testing suite for LLM inference engines. Measures quality consistency and performance across vLLM, TGI, llama.cpp, and Ollama.

[**Full Documentation**](https://kirizan.github.io/kitt/) | [**CLI Reference**](https://kirizan.github.io/kitt/reference/cli/)

## Features

- **Multi-engine support** — benchmark across vLLM, TGI, llama.cpp, and Ollama with a unified interface
- **Docker-only engines** — all engines run in Docker containers, eliminating compatibility issues
- **Quality benchmarks** — MMLU, GSM8K, TruthfulQA, and HellaSwag evaluations
- **Performance benchmarks** — throughput, latency, memory usage, and warmup analysis
- **Hardware fingerprinting** — automatic system identification for reproducible results
- **[KARR results storage](https://kirizan.github.io/kitt/concepts/karr/)** — Kitt's AI Results Repository. SQLite (default) or PostgreSQL with queryable schema and full JSON round-tripping
- **Docker deployment stacks** — composable `docker-compose` stacks via `kitt stack`
- **Devon integration** — embedded [Devon](https://github.com/kirizan/devon) web UI tab for model management, with automatic fallback to local Devon
- **Web dashboard & REST API** — browse results, manage agents, and configure settings with TLS and token auth
- **Local model browser** — scan and display models from a local directory
- **Remote agents** — deploy thin agents to GPU servers via `curl | bash`; agents receive Docker commands from the server
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
poetry install -E all   # optional: install all extras (web, datasets, TUI, devon)
poetry install -E devon # optional: just remote Devon support (httpx)
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
kitt web                         # launch web dashboard
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `KITT_MODEL_DIR` | `~/.kitt/models` | Directory the Models tab scans for local model files |
| `DEVON_URL` | *(none)* | Devon server URL for the Devon tab iframe |
| `DEVON_API_KEY` | *(none)* | Bearer token for remote Devon (optional) |
| `KITT_AUTH_TOKEN` | *(none)* | Bearer token for KITT API authentication |

## Documentation

| Section | Description |
|---|---|
| [Getting Started](https://kirizan.github.io/kitt/getting-started/) | Installation, first benchmark tutorial, Docker quickstart |
| [Guides](https://kirizan.github.io/kitt/guides/) | Engines, benchmarks, results, campaigns, deployment, monitoring |
| [Reference](https://kirizan.github.io/kitt/reference/) | CLI reference, config schemas, REST API, environment variables |
| [Concepts](https://kirizan.github.io/kitt/concepts/) | Architecture, fingerprinting, results storage, engine lifecycle |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KITT_MODEL_DIR` | Directory to scan for local model files (Models tab) | `~/.kitt/models` |
| `DEVON_URL` | Devon web UI URL for iframe embedding and API access | _(none)_ |
| `DEVON_API_KEY` | API key for authenticating with remote Devon | _(none)_ |
| `KITT_AUTH_TOKEN` | Bearer token for web dashboard and agent API auth | _(none)_ |

## Remote Devon Integration

KITT can connect to a containerized [Devon](https://github.com/kirizan/devon) instance for model management — search, download, list, and delete models on a remote server without installing Devon locally.

**Resolution order:** Remote Devon (HTTP) → Local DevonBridge (Python import) → Devon CLI (subprocess)

### Campaign config

Add `devon_url` and `devon_api_key` to your campaign YAML:

```yaml
devon_managed: true
devon_url: "http://192.168.1.50:8000"
devon_api_key: "your-token"  # omit if Devon has no auth
```

### Web dashboard

Set environment variables to embed the Devon web UI in a dedicated "Devon" tab:

```bash
export DEVON_URL="http://192.168.1.50:8000"
export DEVON_API_KEY="your-token"  # omit if Devon has no auth
kitt web
```

The Devon tab displays the Devon web UI in an iframe. When `DEVON_URL` is not set, the tab shows setup instructions. You can hide the Devon tab from **Settings > Devon Integration > Show Devon Tab**.

## Agent Installation

KITT agents run on remote GPU servers and receive Docker orchestration commands from the KITT server. The agent is installed via `curl` from the running KITT instance, ensuring version compatibility.

### One-line install

```bash
curl -sfL https://your-kitt-server:8080/api/v1/agent/install.sh \
  -H "Authorization: Bearer YOUR_TOKEN" | bash
```

This creates a virtual environment at `~/.kitt/agent-venv`, downloads the agent package from the KITT server, and configures the agent. The agent version always matches the server.

### Start the agent

```bash
~/.kitt/agent-venv/bin/kitt-agent start
```

### Systemd service (persistent)

The install script prints systemd instructions at the end. Follow them to run the agent as a system service that survives reboots.

### Thin agent architecture

The agent is a lightweight daemon (`kitt-agent`) that:

- Registers with the KITT server and sends periodic heartbeats
- Receives Docker commands (pull image, run container, stop container) from the server
- Streams container logs back via SSE
- Reports hardware capabilities (GPU, CPU, RAM) during registration
- Does **not** include the full KITT benchmarking suite — all orchestration happens server-side

## Development

```bash
poetry install --with dev
poetry run pytest
poetry run ruff check src/ tests/
```

## License

Apache 2.0
