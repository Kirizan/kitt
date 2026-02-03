# KITT - Kirby's Inference Testing Tools

End-to-end testing suite for LLM inference engines. Measures quality consistency and performance across local inference engines (vLLM, TGI, llama.cpp, Ollama).

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

## Quick Start

```bash
# Install dependencies
poetry install

# Activate the virtual environment
poetry shell
```

Poetry installs KITT into an isolated virtual environment. After running `poetry shell`, the `kitt` command is available directly:

```bash
# Check hardware fingerprint
kitt fingerprint

# List available engines
kitt engines list

# Run a benchmark suite
kitt run --model /path/to/model --engine vllm --suite standard
```

Alternatively, you can run commands without activating the shell by prefixing with `poetry run`:

```bash
poetry run kitt fingerprint
```

## Results

Test results are stored in **KARR (Kirby's AI Results Repo)** repositories, organized by hardware configuration.
