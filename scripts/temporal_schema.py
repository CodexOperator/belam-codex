#!/usr/bin/env python3
"""
temporal_schema.py — SQLite schema for Orchestration Engine V2-Temporal

Replaces the originally-planned SpacetimeDB Rust module with SQLite+WAL.
Rationale (from Critic S-01): no Rust compiler on ARM64 host, SpacetimeDB 2.0
is cloud-oriented, and we don't need real-time subscriptions yet (agents are
session-based, not long-running). Same Python API, zero new deps.

Tables mirror the Architect's SpacetimeDB design (Section 4):
  - pipeline_state: Current state per pipeline (one row each)
  - state_transition: Immutable append-only log of all transitions
  - handoff: Delivery tracking with lifecycle status
  - agent_context: Persistent cross-session memory per (pipeline, agent)
  - agent_presence: Heartbeat-driven agent status

Additional:
  - schema_version: Migration tracking

Usage:
    python3 scripts/temporal_schema.py              # Initialize DB
    python3 scripts/temporal_schema.py --migrate    # Run pending migrations
    python3 scripts/temporal_schema.py --verify     # Verify schema integrity
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

# Default DB location — alongside pipeline state files
WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
DEFAULT_DB_PATH = WORKSPACE / 'data' / 'temporal.db'

SCHEMA_VERSION = 1

# ─── Schema DDL ──────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
-- Enable WAL mode for concurrent reads during writes
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Migration tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    description TEXT
);

-- Current pipeline state (one row per pipeline)
CREATE TABLE IF NOT EXISTS pipeline_state (
    version         TEXT PRIMARY KEY,
    status          TEXT NOT NULL,           -- phase1_design, phase1_build, etc.
    current_stage   TEXT NOT NULL,           -- architect_design, critic_review, etc.
    current_agent   TEXT NOT NULL,           -- architect, critic, builder
    locked_by       TEXT,
    lock_acquired_at TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    tags            TEXT NOT NULL DEFAULT '[]',  -- JSON array
    priority        TEXT NOT NULL DEFAULT 'medium'
);

-- Immutable append-only log of all state transitions
CREATE TABLE IF NOT EXISTS state_transition (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    version         TEXT NOT NULL,
    from_stage      TEXT NOT NULL,
    to_stage        TEXT NOT NULL,
    agent           TEXT NOT NULL,
    action          TEXT NOT NULL,           -- complete, block, start, resume
    notes           TEXT NOT NULL DEFAULT '',
    artifact        TEXT,
    timestamp       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    session_id      TEXT NOT NULL DEFAULT '',
    duration_seconds INTEGER                 -- Time spent in from_stage
);

CREATE INDEX IF NOT EXISTS idx_transition_version ON state_transition(version);
CREATE INDEX IF NOT EXISTS idx_transition_timestamp ON state_transition(timestamp);
CREATE INDEX IF NOT EXISTS idx_transition_agent ON state_transition(agent);

-- Handoff records with delivery lifecycle tracking
CREATE TABLE IF NOT EXISTS handoff (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    version         TEXT NOT NULL,
    source_agent    TEXT NOT NULL,
    target_agent    TEXT NOT NULL,
    completed_stage TEXT NOT NULL,
    next_stage      TEXT NOT NULL,
    notes           TEXT NOT NULL DEFAULT '',
    dispatched_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    verified_at     TEXT,
    status          TEXT NOT NULL DEFAULT 'dispatched',  -- dispatched, acknowledged, working, completed, blocked, timed_out
    dispatch_payload_hash TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_handoff_version ON handoff(version);
CREATE INDEX IF NOT EXISTS idx_handoff_status ON handoff(status);

-- Persistent agent context within a pipeline lifecycle
-- Addresses Critic FLAG-3: this IS on the filesystem (SQLite DB file),
-- so agent_context is automatically backed up with the DB.
CREATE TABLE IF NOT EXISTS agent_context (
    key             TEXT PRIMARY KEY,       -- "{version}:{agent}" compound key
    version         TEXT NOT NULL,
    agent           TEXT NOT NULL,
    accumulated_context TEXT NOT NULL DEFAULT '{}',  -- JSON blob
    session_count   INTEGER NOT NULL DEFAULT 0,
    total_tokens_used INTEGER NOT NULL DEFAULT 0,
    last_session_id TEXT NOT NULL DEFAULT '',
    last_active_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_context_version ON agent_context(version);
CREATE INDEX IF NOT EXISTS idx_context_agent ON agent_context(agent);

-- Real-time agent presence (heartbeat-driven)
-- Critic FLAG-5 addressed: TTL check done in Python at query time
CREATE TABLE IF NOT EXISTS agent_presence (
    agent           TEXT PRIMARY KEY,
    status          TEXT NOT NULL DEFAULT 'idle',  -- idle, working, blocked, offline
    current_pipeline TEXT,
    current_stage   TEXT,
    last_heartbeat  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    session_id      TEXT
);
"""


def init_db(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Initialize the temporal database with schema.

    Creates parent directories, enables WAL mode, creates all tables.
    Idempotent — safe to call on an existing DB.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)

    # Record schema version if not already present
    existing = conn.execute(
        "SELECT version FROM schema_version WHERE version = ?",
        (SCHEMA_VERSION,)
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO schema_version (version, description) VALUES (?, ?)",
            (SCHEMA_VERSION, "Initial schema: 5 tables + indexes")
        )
    conn.commit()
    return conn


def verify_db(db_path: Path = DEFAULT_DB_PATH) -> dict:
    """Verify schema integrity. Returns status dict."""
    if not db_path.exists():
        return {'ok': False, 'error': 'Database file not found', 'path': str(db_path)}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Check required tables exist
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    required = {'pipeline_state', 'state_transition', 'handoff',
                'agent_context', 'agent_presence', 'schema_version'}
    missing = required - tables

    # Check schema version
    version = None
    if 'schema_version' in tables:
        row = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()
        version = row[0] if row else None

    # Integrity check
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]

    # WAL mode check
    journal = conn.execute("PRAGMA journal_mode").fetchone()[0]

    conn.close()

    return {
        'ok': len(missing) == 0 and integrity == 'ok',
        'path': str(db_path),
        'schema_version': version,
        'tables': sorted(tables),
        'missing_tables': sorted(missing) if missing else [],
        'integrity': integrity,
        'journal_mode': journal,
        'size_bytes': db_path.stat().st_size,
    }


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Get a connection to the temporal DB. Initializes if needed."""
    if not db_path.exists():
        return init_db(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Temporal DB schema manager')
    parser.add_argument('--db', type=Path, default=DEFAULT_DB_PATH,
                        help='Database file path')
    parser.add_argument('--verify', action='store_true',
                        help='Verify schema integrity')
    parser.add_argument('--migrate', action='store_true',
                        help='Run pending migrations')
    parser.add_argument('--json', action='store_true',
                        help='JSON output')
    args = parser.parse_args()

    if args.verify:
        result = verify_db(args.db)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            status = '✅ OK' if result['ok'] else '❌ FAILED'
            print(f"Temporal DB: {status}")
            print(f"  Path: {result['path']}")
            print(f"  Schema version: {result.get('schema_version', 'N/A')}")
            print(f"  Tables: {', '.join(result.get('tables', []))}")
            if result.get('missing_tables'):
                print(f"  Missing: {', '.join(result['missing_tables'])}")
            print(f"  Integrity: {result.get('integrity', 'N/A')}")
            print(f"  Journal: {result.get('journal_mode', 'N/A')}")
            print(f"  Size: {result.get('size_bytes', 0)} bytes")
        sys.exit(0 if result['ok'] else 1)
    elif args.migrate:
        conn = init_db(args.db)
        print(f"✅ Migrations applied (schema v{SCHEMA_VERSION})")
        result = verify_db(args.db)
        print(f"  Tables: {', '.join(result.get('tables', []))}")
        conn.close()
    else:
        conn = init_db(args.db)
        print(f"✅ Temporal DB initialized at {args.db}")
        result = verify_db(args.db)
        print(f"  Schema version: {result.get('schema_version')}")
        print(f"  Tables: {', '.join(result.get('tables', []))}")
        print(f"  Journal mode: {result.get('journal_mode')}")
        conn.close()
