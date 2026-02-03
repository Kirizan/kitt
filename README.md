# KITT - Kirby's Inference Testing Tools

End-to-end testing suite for LLM inference engines. Measures quality consistency and performance across local inference engines (vLLM, TGI, llama.cpp, Ollama).

## Quick Start

```bash
# Install
poetry install

# Check hardware fingerprint
kitt fingerprint

# List available engines
kitt engines list

# Run a benchmark suite
kitt run --model /path/to/model --engine vllm --suite standard
```

## Results

Test results are stored in **KARR (Kirby's AI Results Repo)** repositories, organized by hardware configuration.
