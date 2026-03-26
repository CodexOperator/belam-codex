---
primitive: task
status: open
priority: medium
project: multi-agent-infrastructure
depends_on: []
tags: [research, gaming, llm, world-model, multiplayer, fun]
created: 2026-03-26
---

# LLM-Human Interactive Gaming

## Description
Design and build interactive games where LLMs and humans play together in asymmetric roles — not LLM-as-NPC, but LLM-as-opponent/collaborator with genuine agency, resource management, and strategic planning. The LLM isn't just narrating — it's *playing*.

## World Model Foundation
**LeWorldModel (LeWM)** — a JEPA that learns stable world models from raw pixels with only two loss terms (prediction + Gaussian regularizer). Key properties for gaming:
- ~15M params, trainable on single GPU in hours
- Plans 48x faster than foundation-model world models
- Latent space encodes meaningful physical structure (probeable)
- Surprise detection: reliably flags physically implausible events (anti-cheat potential)
- Paper: https://arxiv.org/abs/2603.19312v1

LeWM could serve as the shared world state backbone — both LLM and human players interact through the same latent world model, with different render engines (text for LLM, visual for human).

## Game Directions

### 1. Dungeon Keeper vs Heroes (Asymmetric Strategy)
**LLM role:** Dungeon master / keeper — designs rooms, spawns monsters, sets traps, manages dungeon resources (mana, gold, minion population)
**Human role:** Hero party — explores, fights, loots, levels up, manages health/inventory/abilities

Core mechanics:
- **Resource tension:** LLM has a mana budget per turn — spending on a dragon means fewer traps elsewhere. Heroes have limited potions, torches, spell slots
- **Information asymmetry:** LLM sees full map, heroes see fog of war. But heroes can scout/detect traps
- **Escalation curve:** Dungeon gets harder as heroes get stronger. LLM adapts strategy based on hero behavior patterns
- **Win conditions:** Heroes reach the vault / LLM depletes all hero lives
- Render: text-based for LLM reasoning, tile map or ASCII for humans (upgradeable to visual later)

### 2. Civilization-Lite (Symmetric 4X)
**LLM role:** Rival civilization leader with same rules as human players
**Human role:** Civilization leader

Core mechanics:
- **Shared map:** Hex grid with fog of war, resources, terrain
- **Turn-based economy:** Gather, build, research, expand — both sides follow identical resource rules
- **Diplomacy channel:** LLM can negotiate, bluff, form/break alliances through natural language
- **Tech tree:** Simple branching choices (military vs economic vs cultural)
- **Win conditions:** Domination, economic, or cultural victory
- Interesting because the LLM has to reason about long-term strategy, not just react

### 3. Heist Planner vs Security Director (Co-op/Versus)
**LLM role:** Either the heist planner OR the security director (player picks)
**Human role:** The other side

Core mechanics:
- **Planning phase:** Both sides secretly allocate resources (guards/cameras vs tools/disguises)
- **Execution phase:** Turn-by-turn resolution — human moves through the building, LLM responds with security
- **Bluffing:** LLM can set fake cameras, humans can create diversions
- **Resource pools:** Security budget (guards, tech, reinforcements) vs heist budget (gadgets, team members, escape routes)
- **Replayability:** Procedural building layouts, multiple heist objectives

### 4. Ecosystem Architect (Collaborative Sandbox)
**LLM role:** Nature/physics engine — controls weather, animal behavior, geological events, ecosystem balance
**Human role:** Settlement builder — places structures, manages population, harvests resources

Core mechanics:
- **Not adversarial** — LLM isn't trying to destroy the settlement, it's running a realistic ecosystem
- **Emergent challenge:** Overharvest wood → erosion → flooding. Overhunt → prey population collapse → predators move to settlement
- **LLM as world model:** This is where LeWM shines — the LLM maintains physical plausibility of the world state
- **Surprise detection:** LeWM flags when player actions would create physically impossible states
- **Win condition:** Sustainable thriving settlement (score-based)

### 5. Time Loop Detective (Narrative + Puzzle)
**LLM role:** Controls all NPCs, maintains world state, tracks causality chains
**Human role:** Detective stuck in a time loop — must solve a mystery by repeating the same day

Core mechanics:
- **Persistent knowledge:** Human retains info across loops, world resets each time
- **LLM consistency:** Must keep NPC behavior deterministic unless human's actions change inputs
- **Branching consequences:** Confront suspect A early → suspect B changes behavior
- **Resource:** Time itself — each loop is N turns, can't be everywhere at once
- **Win condition:** Identify culprit + method + motive with evidence

## Architecture Considerations

### State Management
- LeWM latent space as world state backbone (physical plausibility built in)
- SpacetimeDB for explicit game state (inventories, HP, positions) — temporal subscriptions for turn resolution
- Hybrid: LeWM handles world physics, SpacetimeDB handles game rules/resources

### Render Engines
- **LLM player:** State diffs injected via OpenClaw hooks (text/structured data)
- **Human player:** ASCII/tile-based initially, upgradeable to visual (web canvas, terminal UI)
- Both render from same underlying state — no information advantage from render engine

### Turn Resolution
- Async turns via temporal store (no need for real-time)
- OpenClaw `before_prompt_build` hooks inject "what happened since your last turn"
- Actions validated against resource pools before committing to state

### Anti-Cheat / Fairness
- LeWM surprise detection for physically implausible moves
- Resource validation layer — neither side can spend what they don't have
- Replay/audit log via SpacetimeDB temporal queries

## Prior Work
- `tasks/temporal-interaction-llm-gaming.md` — original temporal interaction research (done)
- SpacetimeDB evaluation from codex-engine-v2 research
- OpenClaw hook architecture from research-openclaw-internals pipeline

## Acceptance Criteria
- [ ] Pick one game direction and write detailed game design doc
- [ ] Prototype: single game session (LLM vs human, 10+ turns)
- [ ] Resource tracking working for both sides
- [ ] State persistence across turns
- [ ] Playable and fun (the actual test)
