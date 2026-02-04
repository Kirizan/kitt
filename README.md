# KITT - Kirizan's Inference Testing Tools

End-to-end testing suite for LLM inference engines. Measures quality consistency and performance across local inference engines (vLLM, TGI, llama.cpp, Ollama).

## Features

- **Multi-engine support** - Benchmark across vLLM, TGI, llama.cpp, and Ollama with a unified interface
- **Quality benchmarks** - MMLU, GSM8K, TruthfulQA, and HellaSwag evaluations
- **Performance benchmarks** - Throughput, latency, memory usage, and warmup analysis
- **Hardware fingerprinting** - Automatic system identification for reproducible, hardware-aware result organization
- **KARR integration** - Git-backed results repositories (Kirizan's AI Results Repo) for tracking and comparing runs over time
- **Multiple output formats** - JSON metrics, Markdown summaries, interactive TUI, and a web dashboard
- **Custom benchmarks** - Define your own evaluations with YAML configuration files

## Prerequisites

KITT requires Python 3.10+ and [Poetry](https://python-poetry.org/) for dependency management.

Some dependencies (e.g., `psutil`) include C extensions that must be compiled during install. Ensure your system has the required build tools and Python development headers:

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

Running `poetry install` with no extras installs the core CLI, hardware fingerprinting, and all built-in benchmarks. Inference engines and some UI features require optional extras:

| Extra | What it adds | Required for |
|---|---|---|
| `vllm` | vLLM + Transformers | `kitt run -e vllm` |
| `tgi` | Transformers | `kitt run -e tgi` |
| `datasets` | HuggingFace Datasets | Quality benchmarks using HuggingFace datasets |
| `web` | Flask | `kitt web` |
| `cli_ui` | Textual | `kitt compare` (interactive TUI) |
| `all` | All of the above | Full feature set |

```bash
# Install a specific extra
poetry install -E vllm

# Install multiple extras
poetry install -E vllm -E web

# Install everything
poetry install -E all
```

## Quick Start

```bash
# Check your hardware fingerprint
kitt fingerprint

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

List all registered inference engines and their availability status.

```bash
kitt engines list
```

Displays a table of engines with their status (Available / Not Available) and supported model formats.

#### `kitt engines check`

Check whether a specific engine is available and show detailed diagnostics. The check performs a functional test — importing the Python package for local engines or connecting to the server for HTTP-based engines. When an engine is unavailable, the output shows the exact error and a suggested fix.

For GPU-based engines (`vllm`, `llama_cpp`), also displays the system CUDA version, the PyTorch CUDA version, and flags any mismatch between them.

```bash
kitt engines check <engine_name>
```

**Examples:**

```bash
# Import-based engine with missing dependency
$ kitt engines check vllm
Engine: vllm
  Formats: safetensors, pytorch
  Check: Import check
  Status: Not Available
  Error: vllm is not installed
  Suggested fix:
    pip install vllm
    Or: poetry install -E vllm
  System CUDA: 13.0
  PyTorch CUDA: 12.4
  CUDA mismatch: system CUDA 13.0 vs PyTorch CUDA 12.4
  Fix with:
    pip install torch --force-reinstall --index-url https://download.pytorch.org/whl/cu130
    pip install vllm --force-reinstall --extra-index-url https://download.pytorch.org/whl/cu130
  Or run: kitt engines setup vllm

# Server-based engine that is running
$ kitt engines check ollama
Engine: ollama
  Formats: gguf
  Check: Server check
  Status: Available
  2 model(s) available

# Server-based engine that is not running
$ kitt engines check tgi
Engine: tgi
  Formats: safetensors, pytorch
  Check: Server check
  Status: Not Available
  Error: Cannot connect to TGI server at localhost:8080
  Suggested fix:
    Start a TGI server with:
      docker run --gpus all -p 8080:80 ghcr.io/huggingface/text-generation-inference:latest --model-id <model>
```

#### `kitt engines setup`

Install an engine with CUDA-matched wheels. Detects the system CUDA version and runs `pip install` with the correct `--index-url` so PyTorch and the engine are built for the right CUDA runtime.

```bash
kitt engines setup <engine_name> [--dry-run]
```

| Option | Description |
|---|---|
| `--dry-run` | Show the pip commands that would be run without executing them |
| `--verbose` | Show full pip output (suppressed by default) |

Currently supported engines: `vllm`.

**Examples:**

```bash
# Preview the install commands
$ kitt engines setup --dry-run vllm
Setting up vllm for CUDA 13.0 (cu130)
  would run: /path/to/python -m pip install torch --force-reinstall --no-deps --index-url https://download.pytorch.org/whl/cu130
  would run: /path/to/python -m pip install vllm --force-reinstall --no-deps --extra-index-url https://download.pytorch.org/whl/cu130
  would run: /path/to/python -m pip install torch --index-url https://download.pytorch.org/whl/cu130
  would run: /path/to/python -m pip install vllm --extra-index-url https://download.pytorch.org/whl/cu130
  would run: /path/to/python -m pip install torch --force-reinstall --no-deps --index-url https://download.pytorch.org/whl/cu130

Dry run — no commands were executed.

# Actually install
kitt engines setup vllm
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

| Engine | Key | Description |
|---|---|---|
| vLLM | `vllm` | High-performance Python LLM serving |
| Text Generation Inference | `tgi` | Hugging Face optimized inference server |
| llama.cpp | `llama_cpp` | CPU-optimized quantized inference |
| Ollama | `ollama` | Local LLM runtime |

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
