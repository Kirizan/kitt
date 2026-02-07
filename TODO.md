# KITT — Feature Backlog

Planned features and ideas for future development.

## Campaign System

First-class support for defining, running, and managing multi-model benchmark campaigns.

- [ ] **YAML campaign definitions** — Declare models, engines, quant levels, and suites in a single config file (e.g., `configs/campaigns/dgx-spark-full.yaml`) instead of writing custom scripts
- [ ] **`kitt campaign run`** CLI command — Load a campaign config, orchestrate the download-benchmark-delete pipeline, and track progress with automatic resume on failure
- [ ] **`kitt campaign status`** — Show live progress of a running campaign (completed/failed/remaining runs, disk usage, estimated time remaining)
- [ ] **`kitt campaign list`** — List past and active campaigns with summary statistics
- [ ] **Disk-aware scheduling** — Automatically order runs by model size to stay within a configurable disk reserve, and skip quants that would exceed available space
- [ ] **Devon integration** — Call Devon's download/remove APIs directly (Python, not subprocess) for model lifecycle management during campaigns
- [ ] **GGUF quant discovery** — Auto-discover available quantization files from HuggingFace repos and Ollama tags, with filtering (e.g., skip IQ1/IQ2 ultra-low quants)
- [ ] **Campaign results rollup** — Aggregate all runs from a campaign into a single comparison report (Markdown table, JSON, or web dashboard view)
- [ ] **Parallel engine runs** — Optionally run non-GPU benchmarks (e.g., download next model) while the current benchmark is executing
- [ ] **Notification hooks** — Send a notification (webhook, email, desktop) when a campaign completes or a run fails

## Engine Improvements

- [ ] **Engine health recovery** — Automatically restart a container if the health check fails mid-benchmark instead of aborting the run
- [ ] **Engine config profiles** — Named engine configs (e.g., `llama_cpp-high-ctx.yaml`) that can be referenced by name in suite or campaign configs
- [ ] **ExLlamaV2 engine** — Add support for ExLlamaV2 as a fifth inference engine (GPTQ/EXL2 formats)
- [ ] **MLX engine** — Apple Silicon native inference via MLX for macOS benchmarking

## Benchmark System

- [ ] **Custom prompt datasets** — Allow users to supply their own prompt files for throughput/latency benchmarks
- [ ] **Streaming latency** — Measure time-to-first-token and inter-token latency for streaming responses
- [ ] **Multi-turn benchmarks** — Evaluate conversation consistency across multiple turns
- [ ] **Long-context benchmarks** — Test quality degradation at high context lengths (16K, 32K, 128K)

## Results & Reporting

- [ ] **Cross-campaign comparison** — Compare results across different campaigns (e.g., before/after a hardware upgrade)
- [ ] **Regression detection** — Flag when a model/engine combination performs significantly worse than a previous run
- [ ] **Export to CSV/Parquet** — Machine-readable exports for analysis in notebooks or dashboards
- [ ] **Web dashboard filtering** — Filter results by model family, parameter count, quant level, or engine in the web UI
