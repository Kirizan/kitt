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
- Reverted Docker CLI package name in Dockerfiles back to `docker.io` — `docker-cli` does not exist in Debian bookworm repos
- Updated hardcoded `kitt_version` references from `1.1.0` to `1.2.1`
- Fixed `_check_auth()` timing attack — replaced `==` with `hmac.compare_digest` for constant-time token comparison
- Fixed thread safety — write lock now wraps entire SQLite transactions (execute + commit), not just the commit
- Fixed `_find_on_share()` path traversal — resolved candidates are validated against the share mount root
- Fixed result detail 404 — `query()` and `get_result()` now include the database ID in returned results
- Fixed `kitt --version` reporting wrong version — now reads from `kitt.__version__` dynamically
- Fixed cleanup button in agent detail page targeting the wrong endpoint (API instead of blueprint)
- Added `@require_auth` to `GET /api/v1/agents/<id>/settings` endpoint
- Added `kitt_image` to migration v8 defaults for consistency with `AgentManager._DEFAULT_SETTINGS`
- Added CSRF protection (`@csrf_protect`) to all state-changing web blueprint endpoints
- Added SHA-256 integrity verification for agent package downloads and build context
- Added Docker environment variable redaction in container start logs
- Added rotating file logging to agent (`~/.kitt/logs/agent.log`, 5MB per file, 3 backups)
- Fixed preflight server reachability check — tries TLS verification first, falls back to insecure for self-signed certs
- Fixed preflight `URLError`-wrapped SSL errors bypassing the insecure fallback
- Removed unused `verify` and `client_cert` parameters from `_report()` function
- Fixed cleanup endpoints bypassing `_write_lock` — extracted `AgentManager.queue_cleanup_command()` method
- Fixed `register()` TOCTOU race — moved SELECT inside write lock to prevent concurrent duplicate inserts
- Fixed `_find_on_share()` glob results not validated against share root (symlink traversal)
- Fixed `_find_on_share()` path validation to use `relative_to()` instead of `str.startswith()` for robustness
- Fixed `csrf_protect` Bearer token exemption — now validates the token before bypassing CSRF check
- Fixed hardcoded `kitt_version` in `run.py` and `json_reporter.py` — now uses `kitt.__version__` dynamically
- Fixed HTMX storage polling in agent detail page targeting JSON endpoint instead of HTML page
- Fixed `tarfile.extractall(filter="data")` incompatibility with Python 3.10 — guarded with version check
- Removed obsolete `docker/agent/Dockerfile` referencing deleted full agent
- Fixed `docker-cli` references in documentation (`docs/reference/docker-files.md`)
- Replaced f-string logger calls with lazy `%s` formatting across agent package and server
- Refactored API token verification — extracted `check_agent_auth()` and `check_agent_auth_by_name()` methods on `AgentManager`, removing raw `_conn` access from API endpoints
- Fixed `tarfile.extractall(filter="data")` guard to use `try/except TypeError` instead of version check, correctly handling Python 3.11.4+ backport
- Fixed `docs/reference/api.md` auth column for `GET /api/v1/agents/<id>/settings` — was incorrectly listed as unauthenticated
- Removed stale `docker/agent/Dockerfile` row from `docs/reference/docker-files.md`
- Removed dead `docker/agent/Dockerfile` reference in stack generator
- Fixed remaining f-string logger calls in `migrations.py` and `agent_install.py`
- Updated stale `kitt_version` in test fixtures from `1.1.0` to `1.2.1`
- Reverted `docker-cli` back to `docker.io` in Dockerfiles — `docker-cli` does not exist in Debian bookworm repos
- Added `save_result()` method to `ResultService` — `report_result` endpoint no longer accesses private `_store` directly
- Fixed `docs/reference/api.md` auth columns for `PATCH` and `DELETE` agent endpoints — were incorrectly listed as unauthenticated
- Fixed `docs/concepts/architecture.md` result reporting URL from `{name}` to `{id}`
- Fixed install script preflight check — `if [ $? -ne 0 ]` was dead code under `set -euo pipefail`, replaced with `if ! command` pattern
- Fixed Docker container leak on health check timeout — container is now stopped before reporting failure
- Removed unused `--foreground` flag from `kitt agent start` proxy command
- Fixed all `docs/reference/api.md` auth columns to match actual `@require_auth` decorators (results, campaigns, models sections)
- Updated README thin agent architecture description to reflect model resolution, Docker benchmark execution, and heartbeat command dispatch

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
