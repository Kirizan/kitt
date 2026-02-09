# KITT - Kirizan's Inference Testing Tools

End-to-end testing suite for LLM inference engines. Measures quality consistency and performance across local inference engines (vLLM, TGI, llama.cpp, Ollama).

## Features

- **Multi-engine support** - Benchmark across vLLM, TGI, llama.cpp, and Ollama with a unified interface
- **Docker-only engines** - All engines run in Docker containers, eliminating CUDA/pip compatibility issues
- **Quality benchmarks** - MMLU, GSM8K, TruthfulQA, and HellaSwag evaluations
- **Performance benchmarks** - Throughput, latency, memory usage, and warmup analysis
- **Hardware fingerprinting** - Automatic system identification for reproducible, hardware-aware result organization
- **KARR integration** - Git-backed results repositories (Kirizan's AI Results Repo) for tracking and comparing runs over time
- **Multiple output formats** - JSON metrics, Markdown summaries, interactive TUI, and a web dashboard
- **Custom benchmarks** - Define your own evaluations with YAML configuration files

## Prerequisites

KITT requires:

- **Python 3.10+** and [Poetry](https://python-poetry.org/) for dependency management
- **Docker** for running inference engines — all engines run inside Docker containers

### System Build Tools

Some dependencies (e.g., `psutil`) include C extensions that must be compiled during install:

**Ubuntu / Debian (including DGX Spark OS):**

```bash
sudo apt-get install gcc python3-dev
```

**Arch Linux:**

```bash
sudo pacman -S --needed base-devel
```

**macOS:**

```bash
xcode-select --install
```

### Docker

Install Docker from [docs.docker.com/get-docker](https://docs.docker.com/get-docker/). Verify it's running:

```bash
docker info
```

For GPU support, install the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html):

```bash
# Ubuntu/Debian
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

## Installation

```bash
# Install core dependencies
poetry install

# Activate the virtual environment
eval $(poetry env activate)
```

Poetry installs KITT into an isolated virtual environment. After activating it, the `kitt` command is available directly. Alternatively, prefix any command with `poetry run`:

```bash
poetry run kitt fingerprint
```

### Optional Dependencies

Running `poetry install` with no extras installs the core CLI, hardware fingerprinting, and all built-in benchmarks:

| Extra | What it adds | Required for |
|---|---|---|
| `datasets` | HuggingFace Datasets | Quality benchmarks using HuggingFace datasets |
| `web` | Flask | `kitt web` |
| `cli_ui` | Textual | `kitt compare` (interactive TUI) |
| `all` | All of the above | Full feature set |

```bash
# Install a specific extra
poetry install -E web

# Install everything
poetry install -E all
```

## Quick Start

```bash
# Check your hardware fingerprint
kitt fingerprint

# Pull Docker images for the engines you want to use
kitt engines setup vllm
kitt engines setup ollama

# List available inference engines
kitt engines list

# List available benchmarks
kitt test list

# Run benchmarks
kitt run --model /path/to/model --engine vllm --suite standard
```

## Commands

### `kitt run`

Run benchmarks against a model using a specified inference engine.

```bash
kitt run --model <path> --engine <engine> [OPTIONS]
```

| Option | Short | Description |
|---|---|---|
| `--model` | `-m` | Path to model or model identifier (required) |
| `--engine` | `-e` | Inference engine: `vllm`, `tgi`, `llama_cpp`, `ollama` (required) |
| `--suite` | `-s` | Test suite to run: `quick`, `standard`, `performance` (default: `quick`) |
| `--output` | `-o` | Output directory for results |
| `--skip-warmup` | | Skip the warmup phase for all benchmarks |
| `--runs` | | Override the number of runs per benchmark |
| `--config` | | Path to a custom engine configuration YAML file |
| `--store-karr` | | Store results in a KARR repository |

**Examples:**

```bash
# Quick throughput test with Ollama
kitt run -m llama3 -e ollama

# Full standard suite with vLLM, saving to a specific directory
kitt run -m /models/llama2-7b -e vllm -s standard -o ./my-results

# Performance suite with custom engine config, stored in KARR
kitt run -m /models/mistral-7b -e llama_cpp -s performance --config ./my-engine.yaml --store-karr
```

When you run `kitt run`, KITT automatically:

1. Starts a Docker container for the chosen engine
2. Mounts the model directory into the container
3. Waits for the engine to become healthy
4. Runs the benchmarks via HTTP API
5. Stops and removes the container

**Output artifacts** (written to the output directory):

| File | Description |
|---|---|
| `metrics.json` | Full benchmark metrics in JSON format |
| `hardware.json` | Detected hardware information |
| `config.json` | Configuration used for the run |
| `summary.md` | Human-readable Markdown summary |
| `outputs/` | Compressed benchmark outputs (chunked) |

### `kitt fingerprint`

Display a unique hardware fingerprint for the current system. This fingerprint is used to organize results by hardware configuration.

```bash
kitt fingerprint [--verbose]
```

| Option | Description |
|---|---|
| `--verbose` | Show detailed hardware information (CPU, GPU, RAM, storage, OS, CUDA, driver) |

**Example:**

```bash
$ kitt fingerprint --verbose

System Information
  Environment: bare-metal
  OS: Linux 6.18.3-arch1-1
  Kernel: 6.18.3-arch1-1
  GPU: NVIDIA GH200 (96GB) x1
  CPU: ARM Neoverse V2 (72c/72t)
  RAM: 128GB DDR5
  Storage: Samsung PM9A3 (NVMe)
  CUDA: 12.8
  Driver: 570.133.20

Hardware Fingerprint: gh200-96gb_neoverse-v2-72c_128gb
```

### `kitt engines`

Manage and inspect inference engines.

#### `kitt engines list`

List all registered inference engines, their Docker images, and availability status.

```bash
kitt engines list
```

Displays a table of engines with their Docker image, status (Ready / Not Pulled), and supported model formats.

#### `kitt engines check`

Check whether a specific engine is available and show detailed diagnostics.

```bash
kitt engines check <engine_name>
```

**Examples:**

```bash
# Engine with image pulled
$ kitt engines check vllm
Engine: vllm
  Image: vllm/vllm-openai:latest
  Formats: safetensors, pytorch
  Status: Available

# Engine without image pulled
$ kitt engines check ollama
Engine: ollama
  Image: ollama/ollama:latest
  Formats: gguf
  Status: Not Available
  Error: Docker image not pulled: ollama/ollama:latest
  Fix: Pull with: kitt engines setup ollama

# Docker not running
$ kitt engines check tgi
Engine: tgi
  Image: ghcr.io/huggingface/text-generation-inference:latest
  Formats: safetensors, pytorch
  Status: Not Available
  Error: Docker is not installed or not running
  Fix: Install Docker: https://docs.docker.com/get-docker/
```

#### `kitt engines setup`

Pull the Docker image for an engine.

```bash
kitt engines setup <engine_name> [--dry-run]
```

| Option | Description |
|---|---|
| `--dry-run` | Show the docker pull command without executing it |

All engines are supported: `vllm`, `tgi`, `llama_cpp`, `ollama`.

**Examples:**

```bash
# Pull the vLLM image
kitt engines setup vllm

# Preview without pulling
kitt engines setup --dry-run ollama
```

### `kitt test`

Manage benchmark definitions.

#### `kitt test list`

List all available benchmarks, including both built-in and YAML-defined benchmarks.

```bash
kitt test list [--category <category>]
```

| Option | Short | Description |
|---|---|---|
| `--category` | `-c` | Filter benchmarks by category (e.g., `performance`, `quality`) |

#### `kitt test new`

Create a new custom benchmark definition from a template.

```bash
kitt test new <name> [--category <category>]
```

| Option | Short | Description |
|---|---|---|
| `--category` | `-c` | Benchmark category (default: `quality_custom`) |

Creates a YAML template at `configs/tests/quality/custom/<name>.yaml` that you can edit to define your benchmark's dataset, sampling parameters, and run configuration.

### `kitt results`

Manage benchmark results and KARR repositories.

#### `kitt results init`

Initialize a new KARR (Kirizan's AI Results Repo) repository for storing benchmark results.

```bash
kitt results init [--path <path>]
```

| Option | Short | Description |
|---|---|---|
| `--path` | `-p` | Directory path for the KARR repo (default: `karr-<fingerprint>` in the current directory) |

#### `kitt results list`

List benchmark results from local directories and KARR repositories.

```bash
kitt results list [OPTIONS]
```

| Option | Description |
|---|---|
| `--model` | Filter results by model name |
| `--engine` | Filter results by engine name |
| `--karr` | Path to a specific KARR repo to search |

Searches `kitt-results/` in the current directory and any `karr-*` repositories.

#### `kitt results compare`

Compare metrics across two or more benchmark runs. Shows min, max, average, standard deviation, and coefficient of variation for each metric.

```bash
kitt results compare <run1> <run2> [OPTIONS]
```

| Option | Description |
|---|---|
| `--additional` | Additional run paths to include (can be specified multiple times) |
| `--format` | Output format: `table` (default) or `json` |

**Examples:**

```bash
# Compare two runs as a table
kitt results compare ./results/run1 ./results/run2

# Compare three runs, output as JSON
kitt results compare ./run1 ./run2 --additional ./run3 --format json
```

#### `kitt results import`

Import a results directory into a KARR repository.

```bash
kitt results import <source> [--karr <path>]
```

| Option | Description |
|---|---|
| `--karr` | Target KARR repo path (default: auto-detect or create based on hardware fingerprint) |

The source directory must contain a `metrics.json` file.

#### `kitt results submit`

Submit results via pull request. Requires Git to be configured with a user name and email.

```bash
kitt results submit [--repo <path>]
```

| Option | Description |
|---|---|
| `--repo` | Path to the results repository |

#### `kitt results cleanup`

Clean up old Git LFS objects to reduce KARR repository size.

```bash
kitt results cleanup [OPTIONS]
```

| Option | Description |
|---|---|
| `--repo` | Path to the results repository (default: current directory) |
| `--days` | Keep objects from the last N days (default: 90) |
| `--dry-run` | Show what would be deleted without making changes |

### `kitt compare`

Launch an interactive TUI (terminal user interface) for side-by-side comparison of benchmark results. Requires the `cli_ui` extra.

```bash
kitt compare <run_path> [<run_path> ...]
```

Pass paths to result directories or `metrics.json` files.

```bash
kitt compare ./results/run1 ./results/run2
```

### `kitt web`

Launch a web dashboard for browsing and visualizing benchmark results. Requires the `web` extra.

```bash
kitt web [OPTIONS]
```

| Option | Description |
|---|---|
| `--port` | Port to serve on (default: 8080) |
| `--host` | Host to bind to (default: 127.0.0.1) |
| `--results-dir` | Path to results directory to display |
| `--debug` | Enable Flask debug mode |

**Example:**

```bash
kitt web --port 9090 --results-dir ./kitt-results
```

### `kitt monitoring`

Manage a Prometheus + Grafana + InfluxDB monitoring stack for tracking campaign metrics on local or remote hardware. KITT can generate customized stacks with configurable scrape targets, deploy them to remote hosts via SSH, and manage their full lifecycle.

#### Local stack (`start` / `stop` / `status`)

Start, stop, or check the built-in monitoring stack from `docker/monitoring/`, or target a generated stack by name.

```bash
kitt monitoring start [--compose-dir PATH] [--name STACK]
kitt monitoring stop  [--compose-dir PATH] [--name STACK]
kitt monitoring status [--compose-dir PATH] [--name STACK]
```

| Option | Description |
|---|---|
| `--compose-dir` | Path to docker-compose directory (auto-detected by default) |
| `--name` | Name of a generated monitoring stack to target |

#### `kitt monitoring generate`

Generate a customized docker-compose monitoring stack at `~/.kitt/monitoring/<name>/`.

```bash
kitt monitoring generate <name> -t <host:port> [-t ...] [OPTIONS]
```

| Option | Description |
|---|---|
| `<name>` | Stack name (required, positional) |
| `-t` / `--target` | Scrape target `host:port` (repeatable, required) |
| `--grafana-port` | Grafana port (default: 3000) |
| `--prometheus-port` | Prometheus port (default: 9090) |
| `--influxdb-port` | InfluxDB port (default: 8086) |
| `--grafana-password` | Grafana admin password (default: kitt) |
| `--influxdb-token` | InfluxDB admin token |
| `--deploy` | Deploy to remote host after generation |
| `--host` | Remote host name (from `~/.kitt/hosts.yaml`) |

#### Remote lifecycle (`deploy` / `remote-start` / `remote-stop` / `remote-status`)

Deploy a generated stack to a remote host and manage it via SSH.

```bash
kitt monitoring deploy <name> --host <host>
kitt monitoring remote-start <name> --host <host>
kitt monitoring remote-stop <name> --host <host>
kitt monitoring remote-status <name> --host <host>
```

| Option | Description |
|---|---|
| `<name>` | Stack name (required, positional) |
| `--host` | Remote host name from `~/.kitt/hosts.yaml` (required) |

#### `kitt monitoring list-stacks` / `remove-stack`

List all generated stacks or remove one by name.

```bash
kitt monitoring list-stacks
kitt monitoring remove-stack <name> [--delete-files]
```

#### Example workflow

```bash
# Generate a stack targeting two hosts
kitt monitoring generate lab -t 192.168.1.10:9100 -t 192.168.1.11:9100

# Deploy to a remote DGX host
kitt monitoring deploy lab --host dgx01

# Check status on the remote host
kitt monitoring remote-status lab --host dgx01

# Stop when done
kitt monitoring remote-stop lab --host dgx01
```

## Engine Architecture

All engines run inside Docker containers. KITT manages the full container lifecycle automatically:

```
Host (KITT CLI)                         Docker Container
+-------------------+                  +------------------+
| kitt run           |   HTTP/JSON      | Engine Server    |
|   engine.generate()| <==============> |   API endpoint   |
|   GPUMemoryTracker |  localhost:PORT  |   /health        |
+-------------------+                  |   --gpus all     |
                                       |   /models (mount)|
                                       +------------------+
```

### Engine Docker Images

| Engine | Docker Image | API Format | Health Endpoint | Default Port |
|---|---|---|---|---|
| vLLM | `vllm/vllm-openai:latest` | OpenAI `/v1/completions` | `/health` | 8000 |
| TGI | `ghcr.io/huggingface/text-generation-inference:latest` | HuggingFace `/generate` | `/info` | 8080 |
| Ollama | `ollama/ollama:latest` | Ollama `/api/generate` | `/api/tags` | 11434 |
| llama.cpp | `ghcr.io/ggerganov/llama.cpp:server` | OpenAI `/v1/completions` | `/health` | 8081 |

### Running KITT from Docker

KITT itself can also run inside a container, managing engine containers as siblings via the Docker socket:

```bash
# Build KITT image
docker build -t kitt .

# Run from container
docker run --rm --network host \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /path/to/models:/models:ro \
  -v ./kitt-results:/app/kitt-results \
  kitt run -m /models/llama-7b -e vllm

# Or via docker-compose
MODEL_PATH=/path/to/models docker compose run kitt run -m /models/llama-7b -e vllm
```

## Test Suites

KITT ships with three predefined test suites:

| Suite | Description | Benchmarks |
|---|---|---|
| `quick` | Smoke test | Throughput only (1 run) |
| `standard` | Full evaluation | All quality + performance benchmarks |
| `performance` | Performance-focused | Throughput, latency, memory, warmup analysis |

## Benchmarks

### Quality

| Benchmark | Description |
|---|---|
| MMLU | Massive Multitask Language Understanding |
| GSM8K | Grade school math reasoning |
| TruthfulQA | Factual consistency evaluation |
| HellaSwag | Commonsense reasoning |

### Performance

| Benchmark | Description |
|---|---|
| Throughput | Requests per second |
| Latency | Response time measurement |
| Memory | VRAM and CPU memory usage |
| Warmup Analysis | Warm-up effect isolation |

## Supported Engines

| Engine | Key | Docker Image | Formats |
|---|---|---|---|
| vLLM | `vllm` | `vllm/vllm-openai:latest` | safetensors, pytorch |
| Text Generation Inference | `tgi` | `ghcr.io/huggingface/text-generation-inference:latest` | safetensors, pytorch |
| llama.cpp | `llama_cpp` | `ghcr.io/ggerganov/llama.cpp:server` | gguf |
| Ollama | `ollama` | `ollama/ollama:latest` | gguf |

## Results Storage (KARR)

Test results are stored in **KARR (Kirizan's AI Results Repo)** repositories — Git-backed directories organized by hardware fingerprint, model, engine, and timestamp.

```bash
# Initialize a KARR repo
kitt results init --path ./my-results-repo

# Run benchmarks and store directly in KARR
kitt run -m /models/llama2-7b -e vllm --store-karr

# Import existing results into KARR
kitt results import ./kitt-results/llama2-7b/vllm/2025-01-15_120000

# List all stored results
kitt results list

# Clean up old LFS objects
kitt results cleanup --days 60 --dry-run
```

## Development

```bash
# Install with dev dependencies
poetry install --with dev

# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov
```

## License

Apache 2.0
