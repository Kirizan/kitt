# REST API

KITT exposes a REST API through the `kitt web` command. The API is served
by Flask and provides endpoints for managing results, agents, campaigns,
models, quick tests, and real-time event streaming.

## Base URL

```
https://<host>:<port>/api/v1/
```

Default: `https://0.0.0.0:8080/api/v1/`

TLS is enabled by default. Pass `--insecure` to disable it during
development. Pass `--legacy` for the read-only v1 dashboard which does
not require TLS.

## Authentication

Protected endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <token>
```

Set the token with `--auth-token` on the CLI or the `KITT_AUTH_TOKEN`
environment variable. Agent registration, heartbeat, and result-reporting
endpoints all require authentication.

## Endpoints

### Health and version

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health` | No | Health check (returns `{"status": "ok"}`) |
| GET | `/api/v1/version` | No | Version info |
| GET | `/api/health` | No | Legacy health endpoint |

### Results

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/results/` | No | List results (query: `model`, `engine`, `suite_name`, `page`, `per_page`) |
| GET | `/api/v1/results/<id>` | No | Get a single result |
| DELETE | `/api/v1/results/<id>` | No | Delete a result |
| GET | `/api/v1/results/aggregate` | No | Aggregate results (query: `group_by`, `metric`) |
| POST | `/api/v1/results/compare` | No | Compare results (body: `{"ids": [...]}`) |

### Agents

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/agents/` | No | List all agents |
| GET | `/api/v1/agents/<id>` | No | Get agent details |
| POST | `/api/v1/agents/register` | Yes | Register a new agent |
| POST | `/api/v1/agents/<id>/heartbeat` | Yes | Agent heartbeat |
| POST | `/api/v1/agents/<id>/results` | Yes | Report benchmark result |
| PATCH | `/api/v1/agents/<id>` | No | Update agent fields |
| DELETE | `/api/v1/agents/<id>` | No | Remove an agent |

### Campaigns

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/campaigns/` | No | List campaigns (query: `status`, `page`, `per_page`) |
| POST | `/api/v1/campaigns/` | No | Create a campaign |
| GET | `/api/v1/campaigns/<id>` | No | Get campaign details |
| DELETE | `/api/v1/campaigns/<id>` | No | Delete a campaign |
| POST | `/api/v1/campaigns/<id>/launch` | No | Launch a campaign |
| POST | `/api/v1/campaigns/<id>/cancel` | No | Cancel a running campaign |
| PUT | `/api/v1/campaigns/<id>/config` | No | Update campaign config (draft only) |

### Models

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/models/search` | No | Search models via Devon (query: `q`, `limit`) |
| GET | `/api/v1/models/local` | No | List locally available models |
| POST | `/api/v1/models/download` | No | Download a model (body: `{"repo_id": "..."}`) |
| DELETE | `/api/v1/models/<repo_id>` | No | Remove a local model |

### Quick tests

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/quicktest/` | No | Launch a quick test (body: `agent_id`, `model_path`, `engine_name`) |
| GET | `/api/v1/quicktest/<id>` | No | Get quick test status |

### Events (SSE)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/events/stream` | No | Global SSE event stream |
| GET | `/api/v1/events/stream/<source_id>` | No | Filtered SSE stream by source |

## Response format

All endpoints return JSON. List endpoints support pagination with `page`
and `per_page` query parameters and return results in an envelope:

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "per_page": 25
}
```

Error responses use a standard structure:

```json
{
  "error": "Description of the problem"
}
```

HTTP status codes follow REST conventions: 200 for success, 201 for
created, 202 for accepted (async), 400 for bad request, 401 for
unauthorized, 403 for forbidden, 404 for not found.
