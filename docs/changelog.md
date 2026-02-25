# Changelog

All notable changes to KITT are documented on this page.

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
