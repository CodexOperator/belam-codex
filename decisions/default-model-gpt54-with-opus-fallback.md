---
primitive: decision
status: accepted
date: 2026-04-14
context: (add context)
alternatives: []
rationale: (add rationale)
consequences: []
upstream: []
downstream: []
tags: [instance:main, openclaw, openai, model-routing, configuration]
---

# default-model-gpt54-with-opus-fallback

## Context

Claude API credits running low. Codex CLI credits available via ChatGPT subscription. Need to reduce Anthropic spend while maintaining agent capabilities.

## Options Considered

- **Option A:** Keep Opus as default, route only coding tasks through Codex CLI
- **Option B:** Switch default to GPT-5.4 with Opus fallback, Codex CLI as default ACP harness
- **Option C:** Full switch to GPT-5.4, no Anthropic fallback

## Decision

Option B: Default model set to `openai/gpt-5.4` with `anthropic/claude-opus-4-6` as fallback. Individual agents (main, sage, architect, builder, critic) retain their per-agent Opus overrides for now. Codex CLI configured as default ACP harness (`acp.defaultAgent: "codex"`).

## Consequences

- Main orchestration model is GPT-5.4 unless per-agent override specifies otherwise
- ACP coding tasks route through Codex CLI with OpenAI's models by default
- OAuth token refresh dependency on Hermes gateway daemon (tokens expire ~72h)
- Anthropic remains available as fallback for billing-exhaustion or outage scenarios
- Per-agent model fields need updating separately if full migration desired
