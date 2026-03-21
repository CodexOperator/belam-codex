---
primitive: mode
status: active
coordinate: e3
function: extend
applicable_namespaces: []
tags: [engine, mode, v2]
description: Extend the engine at runtime — register namespaces, scaffold templates, integrate scripts
---

## e3 — Extend Mode

Extends the Codex Engine namespace and capabilities at runtime.
Changes from category/namespace are session-scoped by default;
persistent registration saves to modes/extensions.json.

### Usage
  e3                              — list all active extensions + trail
  e3 category <name>              — register a new category directory
  e3 namespace <prefix> <dir>     — register a new namespace mapping
  e3 template <type_prefix>       — scaffold YAML frontmatter template from existing primitives
  e3 integrate <script_path>      — register script as engine-callable (session)
  e3 run <name> [args...]         — invoke an integrated script

### Subcommands

**category** — Creates a directory and registers a namespace prefix.
  e3 category experiments         — creates experiments/ dir, registers as 'ex'

**namespace** — Maps a custom prefix to an existing directory.
  e3 namespace x experiments      — maps prefix 'x' to experiments/ directory

**template** — Introspects existing primitives to discover common frontmatter
fields, then scaffolds a YAML template.
  e3 template t                   — creates templates/t_template.yaml from task fields
  e3 template d                   — creates templates/d_template.yaml from decision fields

**integrate** — Registers an external Python script for session-scoped execution.
  e3 integrate codex_ram.py       — registers codex_ram as callable
  e3 integrate my_analysis.py     — registers custom script

**run** — Invokes a previously integrated script.
  e3 run codex_ram stats          — runs codex_ram.py with 'stats' arg
  e3 run my_analysis --verbose    — runs custom script with flags

### Extension Trail
All e3 operations are logged in a session trail. View with `e3` (bare).

### Output
Each operation prints an F-label diff showing what changed:
  F7 + namespace 'x' -> experiments/ [session-scoped]
  F8 + template d -> templates/d_template.yaml

### Persistence
- category/namespace: session-scoped (persistent via modes/extensions.json)
- template: creates file on disk (persistent)
- integrate/run: session-scoped only

### Notes
- Persistent namespaces: edit NAMESPACE dict in codex_engine.py or use extensions.json
- V3 will support a full plugin registry
