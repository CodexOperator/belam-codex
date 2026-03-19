---
primitive: decision
status: accepted
date: 2026-03-15
context: "SNN outputs can be interpreted as prediction market prices — softmax readout IS an LMSR market maker. Understanding market microstructure informs both output design and potential deployment."
alternatives:
  - "Treat prediction markets as pure application layer (miss the architectural insight)"
  - "Build custom AMM logic from scratch (reinventing wheels)"
  - "Encode market microstructure as shared skill (chosen)"
rationale: "The deep connection between softmax and LMSR cost functions means prediction market theory directly informs SNN architecture. Avellaneda-Stoikov market making, VPIN adverse selection, and Almgren-Chriss execution are all relevant to how SNN predictions get consumed. This isn't just application knowledge — it's architectural."
consequences:
  - "LMSR/softmax equivalence available to architect for output layer design"
  - "Market impact models inform how predictions should be sized and executed"
  - "Polymarket/Kalshi architecture patterns available for deployment design"
  - "Combinatorial prediction markets (Hanson's approach) relevant for multi-asset SNN"
project: quant-knowledge-skills
tags: [prediction-markets, microstructure, market-making, knowledge]
knowledge: predictionmarket-specialist
---

# Decision: Prediction Market Specialist Skill

## Summary

Extracted prediction market mechanics and microstructure knowledge into `knowledge/predictionmarket-specialist.md — `. The key architectural insight: **LMSR cost function IS softmax with temperature b** — meaning SNN softmax output layers are literally automated market makers.

## Core Insight: Softmax = LMSR

- LMSR cost: `C(q) = b · ln(Σ exp(qᵢ/b))` — scaled LogSumExp
- Marginal price: `∂C/∂qᵢ = softmax(q/b)ᵢ`
- Binary simplification: sigmoid `p = 1/(1 + exp(-(q₁-q₂)/b))`

This means tuning the softmax temperature in an SNN output layer is equivalent to tuning the liquidity parameter of a prediction market. Higher b = more liquidity = smoother prices = less responsive to new information.

## Knowledge Areas

1. **LMSR mechanics** — cost functions, liquidity, bounded loss
2. **Market microstructure** — CLOB vs AMM, order flow, adverse selection (VPIN)
3. **Market making** — Avellaneda-Stoikov framework, inventory risk
4. **Optimal execution** — Almgren-Chriss, market impact models
5. **Polymarket architecture** — conditional tokens, CTF exchange, hybrid CLOB+AMM

## Related

- `decisions/skill-extraction-from-reports.md` — extraction process
- `knowledge/predictionmarket-specialist.md` — full reference
