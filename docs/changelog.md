# Changelog

All notable changes to KITT are documented on this page.

## 1.2.1

- Fixed agent benchmark results never reaching the server — `_execute_test()` now reads `metrics.json` from the output directory and forwards it as `result_data` in `_report()`
- Fixed `PermissionError` when `kitt run` defaults to relative `kitt-results/` inside a Docker container — agent now passes `-o` with a writable temp directory to `kitt run`
- Changed default output directory for `kitt run` from relative `kitt-results/` to `~/.kitt/results/` for robustness across environments
- Temp output directories (`/tmp/kitt-results-*`) are cleaned up after agent benchmarks complete
- Fixed architecture mismatch in agent Docker image selection — now checks image arch against host arch before use, falling back to locally-built `kitt:latest` when the registry image is the wrong platform
- Fixed `_report()` using agent name instead of agent ID in URL, causing 404 on result submission
- Fixed Docker entrypoint override for benchmark containers — added `--entrypoint kitt` since the KITT image has `ENTRYPOINT ["kitt", "web"]`
- Fixed Docker CLI package name in Dockerfiles — `docker.io` on Debian bookworm ARM64 only installs daemon, changed to `docker-cli`
- Updated hardcoded `kitt_version` references from `1.1.0` to `1.2.1`

## 1.2.0

- Agent model workflow: copy models from NFS share to local storage, benchmark, cleanup
- Per-agent settings configurable from the web UI (model storage, share mount, cleanup, heartbeat interval)
- Agent settings synced to agents via heartbeat response
- NFS share mounting support with fstab and explicit mount fallback
- Preflight prerequisite checks (`kitt-agent preflight`) — Docker, GPU, drivers, NFS, disk space, connectivity
- Install script runs preflight before completing installation
- Heartbeat throttling during benchmarks (auto-increases interval to 60s minimum)
- `cleanup_storage` command for remote model cleanup via heartbeat dispatch
- Storage usage reporting in heartbeat payload
- Removed full agent (`src/kitt/agent/`) — thin agent (`agent-package/`) is now the only agent
- `kitt agent` CLI commands now proxy to `kitt-agent` binary
- Agent settings REST API endpoints (`GET`/`PUT /api/v1/agents/<id>/settings`)
- Storage cleanup REST API (`POST /api/v1/agents/<id>/cleanup`)
- DB migration v8: `agent_settings` key-value table per agent
- Daemon refactored — consolidated duplicated run methods into shared helpers
- Version policy: every PR must increment version going forward
- `kitt-agent build` command for native-arch Docker image building
- Docker container is the preferred benchmark execution method (local CLI is fallback)
- Build context API endpoint (`/api/v1/agent/build-context`)
- Install script auto-builds Docker image during agent installation
- Preflight check for KITT Docker image availability

## 1.1.0

- Added composable Docker deployment stacks (`kitt stack`)
- Added web UI and distributed agent architecture
- Added monitoring stack generation and remote deployment
- Added documentation site with MkDocs Material
- Added UI-configurable settings — Model Directory, Devon URL, and Results Directory can be edited from the Settings page with live updates
- Added inline Devon URL setup form on the Devon page
- Added searchable model dropdown to Quick Test — loads from Devon's `manifest.json` with fuzzy search
- Added heartbeat-based command dispatch — agents pull queued quick tests via heartbeat response
- Added live SSE log streaming to Quick Test — real-time output with status progression
- Added Quick Test API endpoints for log forwarding and status updates
- Added Quick Test history page with status filtering and pagination
- Added Quick Test detail page with SSE live logs and stored log retrieval
- Added persistent log storage — log lines are saved to the database for post-run viewing
- Added `kitt-agent test list` and `kitt-agent test stop` CLI commands for managing tests from the agent host
- Fixed thin agent (`kitt-agent`) log forwarding and command dispatch — heartbeat now processes queued commands, `run_test`/`run_container` extract `test_id` and forward logs and status updates to the server
- Added `agent_name` query parameter to the quick test list API endpoint

## 1.0.0

- Initial release
- Multi-engine support: vLLM, TGI, llama.cpp, Ollama
- Quality benchmarks: MMLU, GSM8K, TruthfulQA, HellaSwag
- Performance benchmarks: throughput, latency, memory, warmup
- Hardware fingerprinting
- KARR results storage
- Web dashboard and REST API
- CI integration
