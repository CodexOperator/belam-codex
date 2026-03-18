---
primitive: project
title: "Active Agent Roster"
type: project
status: active
tags: [agents, infrastructure, roster]
---

# Active Agent Roster

Living reference for all agents in the Belam multi-agent system.
Keep this updated as agents are added, renamed, or reconfigured.

---

## Coordinator (Main)

- **Name:** Belam
- **Model:** Opus (anthropic/claude-opus-4-6)
- **Workspace:** `~/.openclaw/workspace`
- **Role:** Orchestration, memory management, user interface, pipeline oversight
- **Session:** `agent:main`
- **Memory:** `MEMORY.md` + `memory/YYYY-MM-DD.md` (coordinator-only)

---

## Architect

- **Model:** Opus (anthropic/claude-opus-4-6)
- **Workspace:** `~/.openclaw/workspace-architect`
- **Role:** System design, architecture proposals, methodology planning
- **Session:** `agent:architect:main`
- **Symlinks:** Shares `scripts/`, `templates/`, `pipelines/`, `tasks/`, `lessons/`, `decisions/`, `skills/`, `SNN_research/` with main
- **Knowledge:** `ARCHITECT_KNOWLEDGE.md`

---

## Critic

- **Model:** Opus (anthropic/claude-opus-4-6)
- **Workspace:** `~/.openclaw/workspace-critic`
- **Role:** Design review, code review, statistical hygiene, quality gates
- **Session:** `agent:critic:main`
- **Symlinks:** Same as Architect
- **Knowledge:** `CRITIC_KNOWLEDGE.md`

---

## Builder

- **Model:** Opus (anthropic/claude-opus-4-6)
- **Workspace:** `~/.openclaw/workspace-builder`
- **Role:** Implementation, notebook construction, code generation, GPU optimization
- **Session:** `agent:builder:main`
- **Symlinks:** Same as Architect
- **Knowledge:** `BUILDER_KNOWLEDGE.md`

---

## Conventions

- **Session isolation:** Fresh session per handoff (UUID4-based session IDs)
- **Memory crystallization:** Via `--learnings` flag at every handoff boundary
- **Session start:** All agents read their own `memory/` directory at session start
- **Orchestration:** Pipeline orchestrator manages handoff flow (`scripts/pipeline_orchestrate.py`)
- **Workspace isolation:** Agent workspaces do NOT have `MEMORY.md` — that is coordinator-only context
- **Communication:** Filesystem is shared state; Telegram bots for async coordination

---

## Pipeline Flow

```
Belam (Coordinator)
    └─→ Architect   (design phase)
           └─→ Critic  (review / gate)
                  └─→ Builder  (implementation)
                         └─→ Critic  (code review)
                                └─→ Belam  (completion + memory crystallization)
```

---

## Related

- Decision: `decisions/agent-trio-architecture.md`
- Decision: `decisions/agent-session-isolation.md`
- Skill: `skills/pipelines/SKILL.md`
- Skill: `skills/orchestration/SKILL.md`
