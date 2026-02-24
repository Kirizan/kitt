# Agent Daemon

The KITT agent daemon runs on GPU servers and receives benchmark jobs from a
central KITT server. This distributed model lets you manage a fleet of GPU
machines from a single control plane -- the server dispatches work and agents
execute it.

---

## How It Works

The agent is a lightweight Flask application that listens for commands over
HTTPS. When the server sends a `run_test` command, the agent starts a benchmark
in a background thread and streams logs back via Server-Sent Events (SSE). A
heartbeat thread runs alongside the daemon, reporting status and GPU utilization
to the server at a configurable interval (default 30 seconds).

---

## Initializing the Agent

Before starting the agent you must register it with a KITT server:

```bash
kitt-agent init --server https://server:8080
```

This command:

1. Writes `~/.kitt/agent.yaml` with the server URL, token, and agent name.
2. If the server uses HTTPS, generates an agent TLS certificate signed by the
   server CA (requires `ca.pem` in `~/.kitt/certs/`).

Optional flags:

| Flag | Default | Description |
|------|---------|-------------|
| `--token` | *(empty)* | Bearer token for server authentication |
| `--name` | hostname | Friendly agent name |
| `--port` | 8090 | Port the agent listens on |

---

## Starting the Agent

```bash
kitt agent start
```

On startup the agent:

1. Loads `~/.kitt/agent.yaml` (override with `--config`).
2. Registers with the server via `POST /api/v1/agents/register`.
3. Starts a `HeartbeatThread` that sends periodic status, GPU utilization, and
   memory usage to the server.
4. Launches the Flask app on the configured port with optional TLS.

Use `--foreground` to keep the process in the foreground (useful for debugging).
Use `--insecure` to skip TLS verification during development.

---

## mTLS Communication

When the server uses HTTPS, agent-server communication is secured with mutual
TLS. During `kitt agent init` KITT generates a client certificate and stores the
paths in `agent.yaml` under the `tls` key:

```yaml
tls:
  cert: /home/user/.kitt/certs/agent.pem
  key: /home/user/.kitt/certs/agent-key.pem
  ca: /home/user/.kitt/certs/ca.pem
```

Both the heartbeat and the registration request present the client certificate.
The server validates it against the same CA.

---

## Systemd Service

For production deployments, install the agent as a systemd service:

```bash
~/.kitt/agent-venv/bin/kitt-agent service install
```

This generates a systemd unit file, installs it via `sudo`, and starts the
service. The agent will survive reboots and restart automatically on failure.

Manage the service:

```bash
kitt-agent service status      # check service status
kitt-agent service uninstall   # stop, disable, and remove the service
```

---

## Heartbeat and Health Monitoring

The `HeartbeatThread` sends a JSON payload to
`/api/v1/agents/<agent_id>/heartbeat` every 30 seconds (configurable by the
server response at registration). The payload includes:

- Agent status (`idle`, `running`, `error`)
- Current task identifier
- GPU utilization percentage (via pynvml)
- GPU memory used in GB
- Agent uptime

---

## Log Streaming

When a benchmark runs, the agent captures output through a `LogStreamer` and
exposes it as an SSE endpoint at `/api/logs/<command_id>`. The server or any
authorized client can subscribe to this stream for real-time log output.

---

## Checking Status

```bash
kitt agent status
```

This reads `~/.kitt/agent.yaml` and probes the local agent at
`http://127.0.0.1:<port>/api/status` to report whether the daemon is running
and whether a benchmark is currently active.

---

## Stopping the Agent

```bash
kitt agent stop
```

Sends `SIGTERM` to the agent process using the PID stored in
`~/.kitt/agent.pid`.
