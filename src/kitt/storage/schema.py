"""Shared database schema definitions for KITT storage backends."""

# SQLite schema — version-tracked for migrations.
SCHEMA_VERSION = 3

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    engine TEXT NOT NULL,
    suite_name TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL,
    passed INTEGER NOT NULL DEFAULT 0,
    total_benchmarks INTEGER NOT NULL DEFAULT 0,
    passed_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    total_time_seconds REAL NOT NULL DEFAULT 0.0,
    kitt_version TEXT NOT NULL DEFAULT '',
    raw_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    test_name TEXT NOT NULL,
    test_version TEXT NOT NULL DEFAULT '1.0.0',
    run_number INTEGER NOT NULL DEFAULT 1,
    passed INTEGER NOT NULL DEFAULT 0,
    timestamp TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    benchmark_id INTEGER NOT NULL REFERENCES benchmarks(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    metric_value REAL
);

CREATE TABLE IF NOT EXISTS hardware (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    gpu_model TEXT,
    gpu_vram_gb INTEGER,
    gpu_count INTEGER DEFAULT 1,
    cpu_model TEXT,
    cpu_cores INTEGER,
    ram_gb INTEGER,
    environment_type TEXT,
    fingerprint TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_model ON runs(model);
CREATE INDEX IF NOT EXISTS idx_runs_engine ON runs(engine);
CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON runs(timestamp);
CREATE INDEX IF NOT EXISTS idx_runs_suite ON runs(suite_name);
CREATE INDEX IF NOT EXISTS idx_benchmarks_run_id ON benchmarks(run_id);
CREATE INDEX IF NOT EXISTS idx_benchmarks_test_name ON benchmarks(test_name);
CREATE INDEX IF NOT EXISTS idx_metrics_benchmark_id ON metrics(benchmark_id);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_hardware_run_id ON hardware(run_id);
"""

# PostgreSQL equivalent (uses SERIAL, BOOLEAN, JSONB)
POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    engine TEXT NOT NULL,
    suite_name TEXT NOT NULL DEFAULT '',
    timestamp TIMESTAMPTZ NOT NULL,
    passed BOOLEAN NOT NULL DEFAULT FALSE,
    total_benchmarks INTEGER NOT NULL DEFAULT 0,
    passed_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    total_time_seconds REAL NOT NULL DEFAULT 0.0,
    kitt_version TEXT NOT NULL DEFAULT '',
    raw_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS benchmarks (
    id SERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    test_name TEXT NOT NULL,
    test_version TEXT NOT NULL DEFAULT '1.0.0',
    run_number INTEGER NOT NULL DEFAULT 1,
    passed BOOLEAN NOT NULL DEFAULT FALSE,
    timestamp TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    benchmark_id INTEGER NOT NULL REFERENCES benchmarks(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS hardware (
    id SERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    gpu_model TEXT,
    gpu_vram_gb INTEGER,
    gpu_count INTEGER DEFAULT 1,
    cpu_model TEXT,
    cpu_cores INTEGER,
    ram_gb INTEGER,
    environment_type TEXT,
    fingerprint TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_model ON runs(model);
CREATE INDEX IF NOT EXISTS idx_runs_engine ON runs(engine);
CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON runs(timestamp);
CREATE INDEX IF NOT EXISTS idx_runs_suite ON runs(suite_name);
CREATE INDEX IF NOT EXISTS idx_benchmarks_run_id ON benchmarks(run_id);
CREATE INDEX IF NOT EXISTS idx_benchmarks_test_name ON benchmarks(test_name);
CREATE INDEX IF NOT EXISTS idx_metrics_benchmark_id ON metrics(benchmark_id);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_hardware_run_id ON hardware(run_id);
"""
