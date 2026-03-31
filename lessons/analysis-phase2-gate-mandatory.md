---
primitive: lesson
status: active
priority: critical
tags: [pipeline, methodology, analysis, gate]
project: snn-applied-finance
source: Shael directive 2026-03-17
downstream: []
promotion_status: exploratory
doctrine_richness: 8
contradicts: []
---

# Lesson: Analysis Phase 2 is a Mandatory Gate Before New Versions

## The Rule
Never start a new implementation pipeline (notebook version) until the analysis pipeline for the current version completes **both** Phase 1 (autonomous) and Phase 2 (human-directed) at minimum.

## Why It Matters
- Phase 1 autonomous analysis surfaces patterns and apparent failures
- Phase 2 human-directed analysis applies Shael's perspective and domain intuition
- The **interference pattern** between Phase 1 findings and Shael's Phase 2 input often yields surprising results
- What appears to be a total failure (e.g., V4 dead neurons) may contain hidden signal visible only through human-directed deeper analysis
- Premature conclusions from Phase 1 alone cause version jumps that skip critical synthesis

## Where It's Encoded
- `templates/analysis_pipeline.md` — ⚠️ MANDATORY GATE section
- `templates/pipeline.md` — ⚠️ MANDATORY GATE section  
- `research/ANALYSIS_AGENT_ROLES.md` — ⚠️ MANDATORY GATE section
- `MEMORY.md` — long-term memory entry

## Anti-Pattern
❌ Phase 1 analysis says "total failure" → immediately launch v5 with fix
✅ Phase 1 analysis says "total failure" → Phase 2 Shael asks "but what about X?" → discover hidden signal → informed v5 design
