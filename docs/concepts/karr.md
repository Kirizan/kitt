# KARR Repositories

KARR (Kirizan's AI Results Repo) is KITT's system for storing, versioning, and sharing benchmark results using Git repositories. Every benchmark run produces structured output that is committed to a KARR repository, giving you full version history, diff-able results, and the ability to collaborate on benchmark data through standard Git workflows.

## Why Git-Backed Storage?

Benchmark results are valuable data that accumulate over time. Storing them in a Git repository provides several benefits:

- **Version history** -- Every run is a commit. You can see exactly when results changed and what caused regressions.
- **Collaboration** -- Share results by pushing to a remote. Review benchmark changes via pull requests.
- **Diff-able** -- JSON and Markdown result files are text-based, so `git diff` shows exactly what changed between runs.
- **Reproducibility** -- The full hardware configuration and test parameters are stored alongside results.
- **Portability** -- Clone a KARR repo to any machine to analyze results locally.

## Initialization

Create a new KARR repository with `kitt results init`:

```bash
kitt results init --path ./my-results
```

This creates a Git repository with the appropriate `.gitattributes` for LFS tracking and an initial directory structure.

## Directory Structure

Results are organized by hardware fingerprint, model, engine, and timestamp:

```
karr-{fingerprint[:40]}/
  └── {model}/
      └── {engine}/
          └── {timestamp}/
              ├── metrics.json
              ├── summary.md
              ├── hardware.json
              ├── config.json
              └── outputs/
                  └── *.jsonl.gz
```

### Path Components

| Component | Example | Description |
|-----------|---------|-------------|
| `fingerprint[:40]` | `rtx4090-24gb_i9-13900k-24c_64gb-ddr` | Truncated [hardware fingerprint](hardware-fingerprinting.md) |
| `model` | `meta-llama--Llama-3.1-8B` | Model identifier (slashes replaced with `--`) |
| `engine` | `vllm` | Inference engine name |
| `timestamp` | `20250115-143022` | Run timestamp in `YYYYMMDD-HHMMSS` format |

### Files Per Run

| File | Contents |
|------|----------|
| `metrics.json` | Quantitative benchmark results (throughput, latency, accuracy scores) |
| `summary.md` | Human-readable Markdown summary of the run |
| `hardware.json` | Full `SystemInfo` snapshot including the complete hardware fingerprint |
| `config.json` | Exact configuration used for this run (suite, engine settings, test parameters) |
| `outputs/` | Raw model outputs, compressed as `.jsonl.gz` files |

## Git LFS

Large result files (particularly raw model outputs in `*.jsonl.gz` format) are tracked by Git LFS to keep the repository size manageable. The `.gitattributes` file is configured during `kitt results init` to automatically route these files through LFS.

## Compression

Raw outputs are compressed using gzip and split into 50MB chunks. This ensures that individual files stay within Git LFS and hosting platform limits while preserving the full output data.

## Git Operations

KARR uses GitPython for all Git operations:

- **Committing results** -- After a benchmark run completes, results are staged and committed automatically when the `--store-karr` flag is used.
- **Listing results** -- `kitt results list` reads the directory structure to enumerate stored runs, with optional `--model` and `--engine` filters.
- **Comparing results** -- `kitt results compare` loads `metrics.json` from multiple runs for side-by-side comparison.

## KARRRepoManager

The `KARRRepoManager` class in `git_ops/repo_manager.py` handles all interactions with KARR repositories. It provides methods for:

- Initializing new repositories with proper LFS configuration
- Writing result files to the correct directory path
- Committing results with descriptive commit messages
- Querying the repository for stored runs

## Workflow Example

A typical workflow using KARR:

```bash
# Initialize a results repository
kitt results init --path ./karr-results

# Run benchmarks and store results
kitt run -m meta-llama/Llama-3.1-8B -e vllm -s standard --store-karr ./karr-results

# List stored results
kitt results list --path ./karr-results

# Compare two runs
kitt results compare ./karr-results/karr-*/meta-llama--Llama-3.1-8B/vllm/20250115-*/ \
                     ./karr-results/karr-*/meta-llama--Llama-3.1-8B/tgi/20250115-*/
```

## Next Steps

- [Hardware Fingerprinting](hardware-fingerprinting.md) -- how the fingerprint directory name is generated
- [Benchmark System](benchmark-system.md) -- what produces the results stored in KARR
