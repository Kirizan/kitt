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
- **Devon integration** — embedded [Devon](https://github.com/kirizan/devon) web UI via server-side reverse proxy, with automatic fallback to local Devon
- **Web dashboard & REST API** — browse results, manage agents, and configure settings with TLS and per-agent token auth
- **Local model browser** — scan and display models from a local directory
- **Remote agents** — deploy thin agents to GPU servers via `curl | bash`; agents copy models from NFS shares, run benchmarks locally, and clean up. Per-agent settings are configurable from the web UI and synced via heartbeat
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
| `DEVON_URL` | *(none)* | Devon server URL (proxied server-side for the Devon tab) |
| `DEVON_API_KEY` | *(none)* | API key injected server-side when proxying Devon requests |
| `KITT_AUTH_TOKEN` | *(none)* | Bearer token for web dashboard API authentication |

`KITT_MODEL_DIR`, `DEVON_URL`, and `--results-dir` can also be configured from the web UI **Settings** page. UI-saved values take priority over environment variables.

Agent authentication uses **per-agent tokens** provisioned during installation — see [Agent Installation](#agent-installation) below.

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
| `DEVON_URL` | Devon server URL — proxied server-side for the Devon tab | _(none)_ |
| `DEVON_API_KEY` | API key injected server-side when proxying Devon requests | _(none)_ |
| `KITT_AUTH_TOKEN` | Bearer token for web dashboard API authentication | _(none)_ |

## Remote Devon Integration

KITT can connect to a containerized [Devon](https://github.com/kirizan/devon) instance for model management — search, download, list, and delete models on a remote server without installing Devon locally.

**Resolution order:** Remote Devon (HTTP) → Local DevonBridge (Python import) → Devon CLI (subprocess)

### Server-side proxy

KITT proxies all Devon requests server-side at `/devon-app/`, injecting the Devon API key automatically. The browser never sees or needs Devon's credentials — no cross-origin issues, no re-authentication on page navigation.

Configure the Devon URL and API key via environment variables or the web UI:

```bash
export DEVON_URL="http://192.168.1.50:8000"
export DEVON_API_KEY="your-token"  # omit if Devon has no auth
kitt web
```

Or set them from **Settings > Devon Integration** in the web dashboard. UI-saved settings override environment variables. You can hide the Devon tab from **Settings > Devon Integration > Show Devon Tab**.

### Campaign config

Add `devon_url` and `devon_api_key` to your campaign YAML:

```yaml
devon_managed: true
devon_url: "http://192.168.1.50:8000"
devon_api_key: "your-token"  # omit if Devon has no auth
```

## Agent Installation

KITT agents run on remote GPU servers and receive Docker orchestration commands from the KITT server. The agent is installed via `curl` from the running KITT instance, ensuring version compatibility.

### One-line install

```bash
curl -fL https://your-kitt-server:8080/api/v1/agent/install.sh | bash
```

This creates a virtual environment at `~/.kitt/agent-venv`, downloads the agent package from the KITT server, provisions a unique authentication token, and configures the agent. The agent version always matches the server.

### Start the agent

```bash
~/.kitt/agent-venv/bin/kitt-agent start
```

### Update the agent

```bash
~/.kitt/agent-venv/bin/kitt-agent update            # download & install latest from server
~/.kitt/agent-venv/bin/kitt-agent update --restart   # update and restart in one step
```

The update command downloads the latest agent package from the KITT server and reinstalls it into the agent's virtual environment. Use `--restart` to automatically stop the running agent and start the new version.

### Systemd service (persistent)

```bash
~/.kitt/agent-venv/bin/kitt-agent service install
```

This generates a systemd unit file, installs it, and starts the service. The agent will survive reboots and restart automatically on failure. Use `kitt-agent service uninstall` to remove it.

### Per-agent authentication

Each agent receives a unique 256-bit random token during installation:

- The install script provisions the token at download time — each `curl | bash` generates a new token
- The server stores only the **SHA-256 hash** of each token, never the raw value
- Compromising one agent does not affect other agents
- Tokens can be rotated via the API (`POST /api/v1/agents/<id>/rotate-token`)

Agent configuration is stored at `~/.kitt/agent.yaml` and includes the server URL, agent name, port, and token.

### Managing tests from the agent

```bash
kitt-agent test list                    # list tests for this agent
kitt-agent test list --status running   # filter by status
kitt-agent test stop <test_id>          # cancel a running test
```

### Thin agent architecture

The agent is a lightweight daemon (`kitt-agent`) that:

- Registers with the KITT server and sends periodic heartbeats
- Authenticates with its unique per-agent token
- Receives commands via heartbeat dispatch (run benchmark, stop container, cleanup storage)
- Resolves models from NFS shares, copies to local storage, runs benchmarks, and cleans up
- Runs benchmarks inside a locally-built KITT Docker container (falls back to local CLI)
- Streams container logs back via SSE
- Reports full hardware fingerprint during registration (GPU, CPU, RAM, storage, CUDA, driver, environment type, compute capability)
- Handles unified memory architectures (e.g. DGX Spark GB10) where dedicated VRAM is shared with system RAM
- Self-updates from the server via `kitt-agent update`
- Does **not** install the full KITT Python package — benchmarks run inside a Docker container built from the KITT source

## Development

```bash
poetry install --with dev
poetry run pytest
poetry run ruff check src/ tests/
```

## License

Apache 2.0
