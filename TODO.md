# KITT — Feature Backlog

Planned features and ideas for future development.

## Campaign System

First-class support for defining, running, and managing multi-model benchmark campaigns.

- [x] **YAML campaign definitions** — Declare models, engines, quant levels, and suites in a single config file (e.g., `configs/campaigns/dgx-spark-full.yaml`) instead of writing custom scripts
- [x] **`kitt campaign run`** CLI command — Load a campaign config, orchestrate the download-benchmark-delete pipeline, and track progress with automatic resume on failure
- [x] **`kitt campaign status`** — Show live progress of a running campaign (completed/failed/remaining runs, disk usage, estimated time remaining)
- [x] **`kitt campaign list`** — List past and active campaigns with summary statistics
- [x] **Disk-aware scheduling** — Automatically order runs by model size to stay within a configurable disk reserve, and skip quants that would exceed available space
- [x] **Devon integration** — Call Devon's download/remove APIs directly (Python, not subprocess) for model lifecycle management during campaigns
- [x] **GGUF quant discovery** — Auto-discover available quantization files from HuggingFace repos and Ollama tags, with filtering (e.g., skip IQ1/IQ2 ultra-low quants)
- [x] **Campaign results rollup** — Aggregate all runs from a campaign into a single comparison report (Markdown table, JSON, or web dashboard view)
- [x] **Grafana dashboards** — Export campaign metrics to Prometheus/InfluxDB and provide pre-built Grafana dashboards for live campaign monitoring (run progress, throughput over time, quality scores by quant, GPU memory heatmaps) and historical comparison across campaigns
- [x] **Parallel engine runs** — Optionally run non-GPU benchmarks (e.g., download next model) while the current benchmark is executing
- [x] **Campaign from existing runs** — Generate a campaign config from previous benchmark results (e.g., `kitt campaign create --from-results ./kitt-results/`) to re-run the same model/engine/quant combinations on new hardware or after engine updates
- [x] **Notification hooks** — Send a notification (webhook, email, desktop) when a campaign completes or a run fails

## Engine Improvements

- [x] **Engine health recovery** — Automatically restart a container if the health check fails mid-benchmark instead of aborting the run
- [x] **Engine config profiles** — Named engine configs (e.g., `llama_cpp-high-ctx.yaml`) that can be referenced by name in suite or campaign configs
- [x] **ExLlamaV2 engine** — Add support for ExLlamaV2 as a fifth inference engine (GPTQ/EXL2 formats)
- [x] **MLX engine** — Apple Silicon native inference via MLX for macOS benchmarking

## Benchmark System

- [x] **Custom prompt datasets** — Allow users to supply their own prompt files for throughput/latency benchmarks
- [x] **Streaming latency** — Measure time-to-first-token and inter-token latency for streaming responses
- [x] **Multi-turn benchmarks** — Evaluate conversation consistency across multiple turns
- [x] **Long-context benchmarks** — Test quality degradation at high context lengths (16K, 32K, 128K)

## Results & Reporting

- [x] **Cross-campaign comparison** — Compare results across different campaigns (e.g., before/after a hardware upgrade)
- [x] **Regression detection** — Flag when a model/engine combination performs significantly worse than a previous run
- [x] **Export to CSV/Parquet** — Machine-readable exports for analysis in notebooks or dashboards
- [x] **Web dashboard filtering** — Filter results by model family, parameter count, quant level, or engine in the web UI

---

## Future Ideas

Longer-term ideas that aren't yet planned for a specific release.

### Multi-GPU and Distributed

- [ ] **Tensor parallel benchmarks** — Benchmark models across multiple GPUs with configurable tensor parallel size, measuring scaling efficiency and inter-GPU communication overhead
- [ ] **Speculative decoding** — Benchmark draft-model speculative decoding setups (small model proposes, large model verifies) and measure acceptance rates, speedup, and quality impact
- [ ] **Batch inference** — Measure offline/batch throughput with configurable concurrency levels, queue depths, and continuous batching vs. static batching comparisons

### CI/CD and Automation

- [ ] **GitHub Actions integration** — Provide a reusable GitHub Action that runs KITT benchmarks on self-hosted GPU runners and posts regression reports as PR comments
- [ ] **Scheduled campaigns** — Cron-like scheduling for nightly or weekly benchmark campaigns with automatic result comparison against the previous run
- [ ] **Slack/Discord bot** — Interactive bot that can trigger campaigns, report results, and answer queries about historical performance

### Cloud and Remote Execution

- [ ] **Cloud GPU support** — Run campaigns on cloud GPU instances (Lambda Labs, RunPod, AWS) with automatic provisioning, benchmark execution, and teardown
- [ ] **Cost tracking** — Track and report cloud GPU cost per benchmark run, per model, and per campaign to help optimize spend
- [ ] **Remote agent** — Lightweight agent that runs on a remote machine and accepts campaign jobs from a central KITT coordinator

### Advanced Benchmarks

- [ ] **Function calling** — Evaluate tool-use and function-calling accuracy across structured output formats
- [ ] **Vision-language benchmarks** — Benchmark multimodal models on image understanding tasks (requires VLM engine support)
- [ ] **Coding benchmarks** — HumanEval / MBPP pass@k for code generation quality
- [ ] **RAG pipeline benchmarks** — End-to-end retrieval-augmented generation latency and accuracy with configurable chunk sizes and retriever backends
- [ ] **Prompt robustness** — Measure output stability across paraphrased prompts to evaluate sensitivity to prompt phrasing

### Developer Experience

- [ ] **Plugin marketplace** — Allow community-contributed engines, benchmarks, and reporters to be installed via `kitt plugin install <name>`
- [ ] **Interactive TUI campaign builder** — Textual-based wizard for building campaign configs interactively instead of writing YAML by hand
- [ ] **Jupyter integration** — `%kitt` magic commands and result visualization widgets for notebook-based analysis workflows
- [ ] **Model recommendation engine** — Given hardware constraints and quality requirements, recommend the best model/quant/engine combination from historical results

### Smart Campaigns and Data Management

- [ ] **Metadata-driven custom campaigns** — Create dynamic campaigns by querying any combination of run metadata (engine, model, quant, suite, hardware fingerprint, date range, pass/fail status, etc.). For example, `kitt campaign create --where "engine=vllm AND model LIKE 'Qwen%'"` or `kitt campaign create --where "quant IN (Q4_K_M, Q5_K_M, Q6_K)"` would generate a campaign covering all matching historical runs. Custom campaigns should also define matching rules so that new runs fitting the criteria are automatically included in the campaign's dashboards and rollup reports
- [ ] **Database backend** — Migrate result storage from flat JSON files to SQLite (local) or PostgreSQL (shared) to support indexed queries, metadata filtering, and efficient aggregation across thousands of runs. Flat-file export/import should remain supported for portability. This is a prerequisite for metadata-driven campaigns at scale

### Data and Visualization

- [ ] **Power consumption tracking** — Monitor and report GPU/system power draw during benchmarks for energy efficiency comparisons
- [ ] **Quant quality curves** — Auto-generate quality-vs-size tradeoff charts showing how each quantization level affects accuracy and throughput for a given model family
