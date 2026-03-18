---
primitive: decision
status: accepted
date: 2026-03-15
context: "Agents need derivatives pricing knowledge for SNN output interpretation, vol surface construction, and Greeks computation in crypto markets"
alternatives:
  - "Inline derivatives knowledge in agent KNOWLEDGE.md files (not discoverable by other agents)"
  - "External API calls to pricing libraries (latency, dependency)"
  - "OpenClaw skill with progressive disclosure (chosen)"
rationale: "Derivatives pricing is cross-cutting — architect needs it for output layer design (what are we predicting?), critic needs it for validating financial assumptions, builder needs it for implementing pricing logic. A shared skill ensures consistent methodology."
consequences:
  - "All agents can access vol surface construction (SVI/SSVI), Greeks (AAD), stochastic vol (Heston, SABR)"
  - "Arbitrage-free constraints are non-negotiable — encoded as hard rules in the skill"
  - "GARCH calibration and Monte Carlo patterns available for experiment design"
  - "QuantLib is the reference implementation for validation"
project: quant-knowledge-skills
tags: [derivatives, pricing, volatility, knowledge]
skill: derivative-specialist
cli: "belam lessons (for derivative-related findings)"
---

# Decision: Derivative Specialist Skill

## Summary

Extracted derivatives pricing domain knowledge into `skills/derivative-specialist/` as a shared OpenClaw skill. Covers the full pricing stack: volatility surface construction (SVI/SSVI with arbitrage-free constraints), Greeks computation (AAD preferred over finite differences), stochastic volatility models (Heston, SABR), Monte Carlo pricing with GPU acceleration and variance reduction, and GARCH calibration.

## Key Principles Encoded

1. **Arbitrage-free constraints are non-negotiable** — calendar spread (total variance non-decreasing), butterfly (non-negative Dupire density)
2. **AAD over finite differences** for Greeks — single backward pass vs 2N forward passes
3. **SVI Jump-Wings parameterization** for production vol surfaces — parameters nearly independent of expiration
4. **GARCH for volatility forecasting** — EGARCH and GJR-GARCH capture leverage effects in crypto

## Relevance to SNN Research

SNN output layers that predict financial quantities need to respect derivatives pricing constraints. The skill ensures agents designing output decoders understand what "predicting volatility" actually means in a pricing context — it's not just a number, it's a surface with strict no-arbitrage requirements.

## Related

- `decisions/skill-extraction-from-reports.md` — the process that created this skill
- `skills/derivative-specialist/SKILL.md` — full reference
