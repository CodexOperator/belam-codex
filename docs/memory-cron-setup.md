# Memory & Knowledge Cron Setup

## Session End Detection — Pragmatic Approach

OpenClaw doesn't have native session-end hooks — sessions are persistent and go idle rather than cleanly terminating. Instead we use a layered approach:

1. **Heartbeat** (every cycle) — catches mid-day consolidation needs
2. **Daily cron** (midnight UTC) — acts as "session end" trigger, consolidates the day's memories
3. **Weekly cron** (Monday 3 AM UTC) — deep knowledge sync: lessons → knowledge graph, memory archival

## Cron Commands

### Daily Memory Consolidation (midnight UTC)

```bash
openclaw cron add \
  --name "Daily memory consolidation" \
  --cron "0 0 * * *" \
  --tz "UTC" \
  --session isolated \
  --message "Run daily memory consolidation: python3 /home/ubuntu/.openclaw/workspace/scripts/consolidate_memories.py. Report only if significant entries were consolidated." \
  --no-deliver
```

### Weekly Knowledge Sync (Monday 3 AM UTC)

```bash
openclaw cron add \
  --name "Weekly knowledge sync" \
  --cron "0 3 * * 1" \
  --tz "UTC" \
  --session isolated \
  --message "Run the weekly knowledge sync: python3 /home/ubuntu/.openclaw/workspace/scripts/weekly_knowledge_sync.py. Then update MEMORY.md with any significant new long-term patterns discovered. Post a summary of what was synced and any notable patterns." \
  --announce \
  --channel telegram \
  --to "2091889467"
```

## Manual Triggers

```bash
# Quick log a memory
python3 scripts/log_memory.py "V4 experiment failed because spike-count readout killed gradients"
python3 scripts/log_memory.py --category technical --importance 4 --tags "snn,v4" "Always use membrane potential readout"

# List today's memories
python3 scripts/log_memory.py --list

# Consolidate today
python3 scripts/consolidate_memories.py

# Run weekly sync manually
python3 scripts/weekly_knowledge_sync.py

# Dry runs
python3 scripts/consolidate_memories.py --dry-run
python3 scripts/weekly_knowledge_sync.py --dry-run
```

## Architecture

```
memory/
  YYYY-MM-DD.md          # Daily session logs (manual + consolidated)
  entries/               # Structured memory entries (YAML frontmatter)
    YYYY-MM-DD_HHMMSS_slug.md
  archive/               # Archived memories (>7 days old)
    YYYY-MM/
    entries/YYYY-MM/

knowledge/               # Knowledge graph (internal wiki)
  _index.md              # Master index
  _tags.md               # Tag → topic mapping
  snn-architecture.md    # Topic files (created dynamically)
  gpu-optimization.md
  ...

lessons/                 # Lesson primitives (existing)
  *.md                   # Fed into weekly knowledge sync
```
