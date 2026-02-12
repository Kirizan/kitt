# Results & KARR

Benchmark results can be stored in **KARR (Kirizan's AI Results Repo)**
repositories -- Git-backed directories organized by hardware fingerprint,
model, engine, and timestamp. KARR uses Git LFS for large output files and
gives you a version-controlled history of every run.

## Initialize a KARR Repository

Create a new KARR repo in the current directory (or at a custom path):

```bash
kitt results init
kitt results init --path ./my-results
```

The directory is named `karr-<fingerprint>` by default, where `<fingerprint>`
is derived from the first 40 characters of your hardware fingerprint.

## Run with KARR Storage

Add `--store-karr` to any `kitt run` command and results are automatically
committed to the appropriate KARR repo:

```bash
kitt run -m /models/llama2-7b -e vllm -s standard --store-karr
```

## List Results

Browse stored results with optional model and engine filters:

```bash
kitt results list
kitt results list --model llama --engine vllm
kitt results list --karr ./my-results
```

KITT searches `kitt-results/` in the current directory and any `karr-*`
repositories it finds.

## Import Results

Import an existing results directory into KARR:

```bash
kitt results import ./kitt-results/run1
kitt results import ./kitt-results/run1 --karr ./my-results
```

The source directory must contain a `metrics.json` file.

## Compare Results

### CLI Comparison

Compare metrics across two or more benchmark runs:

```bash
kitt results compare ./run1 ./run2
kitt results compare ./run1 ./run2 --additional ./run3 --format json
```

The table output shows min, max, average, standard deviation, and coefficient
of variation for each metric.

### Interactive TUI

Launch a side-by-side terminal comparison (requires the `cli_ui` extra):

```bash
kitt compare ./run1 ./run2
```

## Submit Results via Pull Request

Package results into a branch and open a pull request against the KARR
repository:

```bash
kitt results submit
kitt results submit --repo ./my-results
```

Git must be configured with a user name and email.

## Clean Up LFS Objects

Over time, Git LFS objects accumulate. Remove objects older than a
threshold to reduce repository size:

```bash
kitt results cleanup --days 60 --dry-run   # preview first
kitt results cleanup --days 60             # actually clean up
kitt results cleanup --repo ./my-results --days 30
```

The default retention period is 90 days.

## KARR Directory Structure

Each KARR repo is organized by model, engine, and timestamp:

```
karr-<fingerprint>/
  <model>/
    <engine>/
      <timestamp>/
        metrics.json      # Full benchmark metrics
        summary.md        # Human-readable summary
        hardware.json     # System information snapshot
        config.json       # Configuration used for the run
        outputs/          # Compressed benchmark outputs (chunked, LFS-tracked)
```

Large output files in `outputs/` are compressed in 50 MB chunks and tracked by
Git LFS. This keeps the repository lightweight for cloning while preserving
full output data for deep analysis.

## Typical Workflow

```bash
# 1. Initialize a KARR repo
kitt results init --path ./my-results

# 2. Run benchmarks with KARR storage
kitt run -m /models/llama2-7b -e vllm -s standard --store-karr

# 3. Run the same model on a different engine
kitt run -m /models/llama2-7b -e tgi -s standard --store-karr

# 4. Compare the two runs
kitt results compare ./my-results/llama2-7b/vllm/2025-* ./my-results/llama2-7b/tgi/2025-*

# 5. Submit results upstream
kitt results submit --repo ./my-results
```
