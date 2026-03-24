#!/usr/bin/env python3
"""D1: World State API — shared world state backed by SQLite+WAL.

Provides CRUD + event log + cursor-based diffs for temporal interaction.
Used by hooks (diff injection), coordinate tools (w.set/get/events), and
demo games (tic-tac-toe).

Concurrency: retry with exponential backoff on SQLITE_BUSY (Q3 answer).
FLAG-1 fix: Uses INSERT ON CONFLICT DO UPDATE to increment version correctly.
"""

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
DEFAULT_DB_PATH = WORKSPACE / 'data' / 'temporal.db'

# Retry config for SQLITE_BUSY (Q3)
MAX_RETRIES = 3
RETRY_BASE_MS = 50  # 50ms, 100ms, 200ms


def _retry_on_busy(func):
    """Decorator: retry writes on SQLITE_BUSY with exponential backoff."""
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e) and attempt < MAX_RETRIES:
                    wait = (RETRY_BASE_MS * (2 ** attempt)) / 1000.0
                    time.sleep(wait)
                else:
                    raise
    return wrapper


class WorldState:
    """Shared world state backed by SQLite+WAL.

    Each instance is scoped to a namespace (e.g. 'game:tictactoe', 'default').
    Multiple namespaces share the same DB file but are logically isolated.
    """

    def __init__(self, db_path: Path = None, namespace: str = 'default'):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.namespace = namespace
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path), timeout=5)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def initialize(self):
        """Create world state tables if they don't exist.

        Can be called standalone (for tests) or relies on temporal_schema.py
        migration in production.
        """
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS world_state (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                namespace   TEXT NOT NULL,
                entity      TEXT NOT NULL,
                key         TEXT NOT NULL,
                value       TEXT NOT NULL,
                version     INTEGER NOT NULL DEFAULT 1,
                written_by  TEXT NOT NULL,
                written_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                UNIQUE(namespace, entity, key)
            );
            CREATE TABLE IF NOT EXISTS world_event (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                namespace   TEXT NOT NULL,
                entity      TEXT NOT NULL,
                key         TEXT NOT NULL,
                old_value   TEXT,
                new_value   TEXT NOT NULL,
                written_by  TEXT NOT NULL,
                written_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                turn_id     TEXT
            );
            CREATE TABLE IF NOT EXISTS agent_cursor (
                agent_id    TEXT NOT NULL,
                namespace   TEXT NOT NULL,
                last_event_id INTEGER NOT NULL DEFAULT 0,
                updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                PRIMARY KEY(agent_id, namespace)
            );
            CREATE INDEX IF NOT EXISTS idx_world_event_namespace ON world_event(namespace, id);
            CREATE INDEX IF NOT EXISTS idx_world_state_ns_entity ON world_state(namespace, entity);
        """)
        conn.commit()

    def get(self, entity: str, key: str) -> Optional[str]:
        """Get current value for entity.key in this namespace."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT value FROM world_state WHERE namespace=? AND entity=? AND key=?",
            (self.namespace, entity, key)
        ).fetchone()
        return row['value'] if row else None

    def get_entity(self, entity: str) -> dict:
        """Get all key-value pairs for an entity as a dict."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT key, value, version, written_by, written_at FROM world_state "
            "WHERE namespace=? AND entity=?",
            (self.namespace, entity)
        ).fetchall()
        return {r['key']: {
            'value': r['value'],
            'version': r['version'],
            'written_by': r['written_by'],
            'written_at': r['written_at'],
        } for r in rows}

    def get_all(self) -> dict:
        """Get entire namespace state as {entity: {key: value, ...}, ...}."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT entity, key, value FROM world_state WHERE namespace=?",
            (self.namespace,)
        ).fetchall()
        result = {}
        for r in rows:
            result.setdefault(r['entity'], {})[r['key']] = r['value']
        return result

    @_retry_on_busy
    def set(self, entity: str, key: str, value: str, agent_id: str,
            turn_id: str = None) -> int:
        """Set value, log event, return new version.

        FLAG-1 fix: Uses INSERT ON CONFLICT DO UPDATE to correctly increment
        version instead of INSERT OR REPLACE which resets version to 1.
        """
        conn = self._get_conn()

        # Get old value for event log
        old_row = conn.execute(
            "SELECT value, version FROM world_state WHERE namespace=? AND entity=? AND key=?",
            (self.namespace, entity, key)
        ).fetchone()
        old_value = old_row['value'] if old_row else None

        # Upsert with correct version increment (FLAG-1)
        conn.execute("""
            INSERT INTO world_state (namespace, entity, key, value, version, written_by)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(namespace, entity, key)
            DO UPDATE SET
                value = excluded.value,
                version = world_state.version + 1,
                written_by = excluded.written_by,
                written_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        """, (self.namespace, entity, key, value, agent_id))

        # Log event
        conn.execute("""
            INSERT INTO world_event (namespace, entity, key, old_value, new_value, written_by, turn_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (self.namespace, entity, key, old_value, value, agent_id, turn_id))

        conn.commit()

        # Return new version
        row = conn.execute(
            "SELECT version FROM world_state WHERE namespace=? AND entity=? AND key=?",
            (self.namespace, entity, key)
        ).fetchone()
        return row['version'] if row else 1

    def get_events_since(self, agent_id: str) -> list[dict]:
        """Get all events since this agent's last read cursor."""
        conn = self._get_conn()

        # Get cursor position
        cursor_row = conn.execute(
            "SELECT last_event_id FROM agent_cursor WHERE agent_id=? AND namespace=?",
            (agent_id, self.namespace)
        ).fetchone()
        last_id = cursor_row['last_event_id'] if cursor_row else 0

        rows = conn.execute(
            "SELECT id, entity, key, old_value, new_value, written_by, written_at, turn_id "
            "FROM world_event WHERE namespace=? AND id > ? ORDER BY id",
            (self.namespace, last_id)
        ).fetchall()

        return [{
            'id': r['id'],
            'entity': r['entity'],
            'key': r['key'],
            'old_value': r['old_value'],
            'new_value': r['new_value'],
            'written_by': r['written_by'],
            'written_at': r['written_at'],
            'turn_id': r['turn_id'],
        } for r in rows]

    @_retry_on_busy
    def advance_cursor(self, agent_id: str) -> None:
        """Advance agent's read cursor to latest event."""
        conn = self._get_conn()
        max_row = conn.execute(
            "SELECT MAX(id) as max_id FROM world_event WHERE namespace=?",
            (self.namespace,)
        ).fetchone()
        max_id = max_row['max_id'] if max_row and max_row['max_id'] else 0

        conn.execute("""
            INSERT INTO agent_cursor (agent_id, namespace, last_event_id)
            VALUES (?, ?, ?)
            ON CONFLICT(agent_id, namespace)
            DO UPDATE SET
                last_event_id = excluded.last_event_id,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        """, (agent_id, self.namespace, max_id))
        conn.commit()

    def get_diff(self, agent_id: str) -> str:
        """Get human-readable diff since agent's last read. For prompt injection."""
        events = self.get_events_since(agent_id)
        if not events:
            return ''

        lines = [f"## World State Changes ({len(events)} events)"]
        for e in events:
            old = e['old_value'] or '(new)'
            lines.append(f"  {e['entity']}.{e['key']}: {old} → {e['new_value']} (by {e['written_by']})")

        return '\n'.join(lines)

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# ── CLI dispatch for w.* coordinates (used by codex_lm_platform.py) ──────────

def execute_world(sub: str, args: list[str], agent_id: str = 'unknown') -> str:
    """Handle w.set, w.get, w.events, w.state commands.

    Called from codex_lm_platform.py execute_platform() via FLAG-3 routing.
    """
    ws = WorldState()

    if sub == 'set':
        # w.set entity.key value
        if len(args) < 2:
            return "Usage: w.set {entity.key} {value}"
        entity_key = args[0]
        value = ' '.join(args[1:])
        if '.' not in entity_key:
            return f"Invalid entity.key format: {entity_key}. Use: w.set player.health 100"
        entity, key = entity_key.split('.', 1)
        version = ws.set(entity, key, value, agent_id=agent_id)
        ws.close()
        return f"✅ {entity}.{key} = {value} (v{version})"

    elif sub == 'get':
        # w.get entity
        if not args:
            return "Usage: w.get {entity}"
        entity = args[0]
        data = ws.get_entity(entity)
        ws.close()
        if not data:
            return f"No state for entity '{entity}'"
        lines = [f"## {entity}"]
        for k, v in data.items():
            lines.append(f"  {k}: {v['value']} (v{v['version']}, by {v['written_by']})")
        return '\n'.join(lines)

    elif sub == 'events':
        events = ws.get_events_since(agent_id)
        ws.close()
        if not events:
            return "No new events since last read."
        lines = [f"## Events ({len(events)} new)"]
        for e in events:
            old = e['old_value'] or '(new)'
            lines.append(f"  [{e['written_at']}] {e['entity']}.{e['key']}: {old} → {e['new_value']} (by {e['written_by']})")
        return '\n'.join(lines)

    elif sub == 'state':
        # w.state — dump entire namespace
        state = ws.get_all()
        ws.close()
        if not state:
            return "World state is empty."
        lines = ["## World State"]
        for entity, keys in sorted(state.items()):
            lines.append(f"  **{entity}:**")
            for k, v in sorted(keys.items()):
                lines.append(f"    {k}: {v}")
        return '\n'.join(lines)

    else:
        ws.close()
        return f"Unknown world command: w.{sub}. Available: w.set, w.get, w.events, w.state"


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='World State API CLI')
    parser.add_argument('command', choices=['get', 'set', 'events', 'state', 'diff', 'init'],
                        help='Command to execute')
    parser.add_argument('args', nargs='*', help='Command arguments')
    parser.add_argument('--namespace', '-n', default='default', help='Namespace')
    parser.add_argument('--agent', '-a', default='cli', help='Agent ID')
    parser.add_argument('--db', type=Path, default=DEFAULT_DB_PATH, help='DB path')
    args = parser.parse_args()

    ws = WorldState(db_path=args.db, namespace=args.namespace)

    if args.command == 'init':
        ws.initialize()
        print("✅ World state tables initialized")
    elif args.command == 'set':
        if len(args.args) < 3:
            print("Usage: world_api.py set entity key value")
        else:
            v = ws.set(args.args[0], args.args[1], ' '.join(args.args[2:]), agent_id=args.agent)
            print(f"✅ {args.args[0]}.{args.args[1]} = {' '.join(args.args[2:])} (v{v})")
    elif args.command == 'get':
        if args.args:
            data = ws.get_entity(args.args[0])
            print(json.dumps(data, indent=2, default=str))
        else:
            print("Usage: world_api.py get entity")
    elif args.command == 'events':
        events = ws.get_events_since(args.agent)
        for e in events:
            print(f"  {e['written_at']} {e['entity']}.{e['key']}: {e['old_value']} → {e['new_value']}")
    elif args.command == 'diff':
        print(ws.get_diff(args.agent))
    elif args.command == 'state':
        state = ws.get_all()
        print(json.dumps(state, indent=2))

    ws.close()
