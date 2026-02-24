# Web Dashboard

The KITT web dashboard provides a browser-based UI for browsing results,
managing agents, running campaigns, and interacting with the REST API.
It requires the `web` extra (`poetry install -E web`).

## Launching the Dashboard

```bash
kitt web --port 8080 --results-dir ./results
```

The full set of options:

| Option | Default | Description |
|---|---|---|
| `--port` | 8080 | Port to serve on |
| `--host` | 0.0.0.0 | Host to bind to |
| `--results-dir` | current directory | Path to results directory |
| `--debug` | off | Enable Flask debug mode with auto-reload |
| `--legacy` | off | Use the legacy read-only dashboard |
| `--insecure` | off | Disable TLS (development only) |
| `--tls-cert` | auto | Path to TLS certificate |
| `--tls-key` | auto | Path to TLS private key |
| `--tls-ca` | auto | Path to CA certificate |
| `--auth-token` | none | Bearer token for API authentication |

## TLS Configuration

By default, KITT auto-generates a self-signed CA and server certificate on
first launch. The CA fingerprint is printed to the console so agents and
clients can verify the server identity.

**Custom certificates**: Supply your own with `--tls-cert` and `--tls-key`:

```bash
kitt web --tls-cert /path/to/cert.pem --tls-key /path/to/key.pem
```

**Development mode**: Disable TLS entirely with `--insecure`. This is
intended only for local development -- do not use it in production:

```bash
kitt web --insecure --debug
```

## Authentication

Enable API authentication with `--auth-token`. Clients must include
`Authorization: Bearer <token>` in API requests:

```bash
kitt web --auth-token my-secret-token
```

The token can also be set via the `KITT_AUTH_TOKEN` environment variable.

## Legacy Mode

The legacy dashboard is a read-only single-page viewer from KITT v1. It
scans `kitt-results/` and legacy `karr-*` directories for `metrics.json` files and
renders a summary table:

```bash
kitt web --legacy --results-dir ./kitt-results
```

Legacy mode does not require a database and does not support agents,
campaigns, or the REST API beyond basic result listing.

## REST API Endpoints

The full dashboard registers API blueprints under `/api/v1/`:

| Endpoint | Description |
|---|---|
| `GET /api/v1/health` | Health check |
| `GET /api/v1/results` | List and query benchmark results |
| `GET /api/v1/agents` | List registered agents |
| `POST /api/v1/agents/register` | Agent registration |
| `GET /api/v1/campaigns` | List campaigns |
| `POST /api/v1/campaigns` | Create a new campaign |
| `GET /api/v1/models` | List known models |
| `POST /api/v1/quicktest` | Submit a quick benchmark run |
| `GET /api/v1/events` | Server-sent events for live updates |

All mutable endpoints require a valid `Authorization` header when
`--auth-token` is set.

## Settings

The **Settings** page lets you configure key paths and integrations
directly from the web UI without restarting the server:

| Setting | Environment Variable | Default |
|---------|---------------------|---------|
| Model Directory | `KITT_MODEL_DIR` | `~/.kitt/models` |
| Devon URL | `DEVON_URL` | *(none)* |
| Results Directory | `--results-dir` CLI flag | Current directory |

Values saved through the UI are stored in the database and take
priority over environment variables. Clearing a field reverts to the
environment variable or default. Changes take effect immediately
without a restart.

The Devon URL can also be configured inline on the **Devon** page when
it hasn't been set yet.

## Database

The full dashboard uses SQLite stored at `~/.kitt/kitt.db`. Schema
migrations run automatically on startup. The database tracks agents,
campaigns, and indexed results.
