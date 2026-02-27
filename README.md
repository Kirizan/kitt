# KITT - Kirizan's Inference Testing Tools

End-to-end testing suite for LLM inference engines. Measures quality consistency and performance across vLLM, TGI, llama.cpp, and Ollama.

[**Full Documentation**](https://kirizan.github.io/kitt/) | [**CLI Reference**](https://kirizan.github.io/kitt/reference/cli/)

## Features

- **Multi-engine support** — benchmark across vLLM, TGI, llama.cpp, and Ollama with a unified interface
- **ARM64 and multi-arch support** — platform-aware image selection for ARM64 boards (DGX Spark, Jetson Orin) with automatic KITT-managed builds for engines that lack multi-arch images
- **Docker-only engines** — all engines run in Docker containers, eliminating compatibility issues
- **Quality benchmarks** — MMLU, GSM8K, TruthfulQA, and HellaSwag evaluations
- **Performance benchmarks** — throughput, latency, memory usage, and warmup analysis
- **Hardware fingerprinting** — automatic system identification for reproducible results
- **[KARR results storage](https://kirizan.github.io/kitt/concepts/karr/)** — Kitt's AI Results Repository. SQLite (default) or PostgreSQL with queryable schema and full JSON round-tripping
- **Docker deployment stacks** — composable `docker-compose` stacks via `kitt stack`
- **Devon integration** — embedded [Devon](https://github.com/kirizan/devon) web UI via server-side reverse proxy, with automatic fallback to local Devon
- **Model format validation** — preflight checks prevent launching containers with incompatible model formats (e.g. safetensors on llama.cpp)
- **Web dashboard & REST API** — browse results, manage agents, and configure settings with TLS and per-agent token auth
- **Local model browser** — scan and display models from a local directory, with engine compatibility filtering in the quick test form
- **Remote agents** — deploy thin agents to GPU servers via `curl | bash`; agents copy models from NFS shares, run benchmarks locally, and clean up. Per-agent settings are configurable from the web UI and synced via heartbeat
- **Configurable engine images** — override default Docker images per engine via `~/.kitt/engines.yaml`
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
kitt run -m /models/model.gguf -e llama_cpp --auto-pull  # auto-pull engine image if missing
kitt storage init                 # initialize results database
kitt storage list                 # browse stored runs
kitt storage stats                # summary statistics
kitt web                         # launch web dashboard
```

### Model format validation

KITT validates model format compatibility before launching containers. Each engine declares the formats it supports:

| Engine | Supported Formats |
|--------|------------------|
| vLLM | safetensors, pytorch |
| TGI | safetensors, pytorch |
| llama.cpp | gguf |
| Ollama | gguf |

If you attempt to run a safetensors model with llama.cpp (or a GGUF model with vLLM), KITT exits with a clear error before any container starts. The web UI quick test form also filters models by engine compatibility.

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

## Engine Image Configuration

### Overriding default images

Create `~/.kitt/engines.yaml` to override the default Docker images for any engine:

```yaml
image_overrides:
  vllm: "vllm/vllm-openai:latest"
  llama_cpp: "ghcr.io/ggml-org/llama.cpp:server-cuda"
```

User overrides take the highest priority, followed by KITT's hardware-aware image selection, then the engine's built-in default.

### Platform-aware image selection

KITT automatically selects the best Docker image for the host CPU architecture and GPU compute capability. This is transparent — no user configuration is needed.

| Platform | Engine | Image Selected |
|----------|--------|---------------|
| x86_64 + Blackwell (cc >= 10.0) | vLLM | NGC `nvcr.io/nvidia/vllm` |
| x86_64 + Blackwell | llama.cpp | `kitt/llama-cpp:spark` (built locally) |
| ARM64 + Blackwell (DGX Spark, Jetson Orin) | llama.cpp | `kitt/llama-cpp:arm64` (built locally) |
| Any architecture | Ollama | Default image (bundles its own llama.cpp) |

KITT-managed images (prefixed `kitt/`) are built locally from Dockerfiles in `docker/`. The first run on a new platform may take 10-20 minutes to compile. Subsequent runs use the cached image.

### Auto-pull

The `--auto-pull` flag on `kitt run` automatically pulls (or builds) the engine image if it's not available locally:

```bash
kitt run -m /models/llama-7b -e vllm --auto-pull
```

When running tests via a remote agent, `--auto-pull` is passed automatically.

## Remote Host Management

Manage remote GPU servers via SSH for direct campaign execution (separate from the agent-based workflow).

```bash
kitt remote setup user@spark.local              # register a remote host
kitt remote list                                 # list configured hosts
kitt remote test spark.local                     # test SSH connectivity
kitt remote engines setup vllm --host spark.local           # pull/build engine image
kitt remote engines setup llama_cpp --host spark.local --dry-run  # dry-run
kitt remote run campaign.yaml --host spark.local --wait      # run a campaign
kitt remote status --host spark.local            # check campaign status
kitt remote logs --host spark.local              # view campaign logs
kitt remote sync --host spark.local -o ./results # sync results locally
kitt remote remove spark.local                   # remove a host
```

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

### Agent resilience

Agents automatically recover from transient server issues:

- If a heartbeat receives HTTP 404 (e.g. after server restart or database reset), the agent re-registers and syncs its canonical agent ID
- The server falls back to hostname-based lookup when an agent ID is not found, so heartbeats and results are not lost during recovery
- Engine images are auto-pulled during remote test execution, so agents don't fail on missing images

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
- Reports full hardware fingerprint during registration (GPU, CPU, CPU architecture, RAM, storage, CUDA, driver, environment type, compute capability)
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
