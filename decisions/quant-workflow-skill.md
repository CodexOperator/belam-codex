---
primitive: decision
status: accepted
date: 2026-03-15
context: "SNN research must follow rigorous quant methodology — overfitting is the #1 risk in financial ML. Agents need shared understanding of statistical hygiene, feature engineering, and the research-to-production pipeline."
alternatives:
  - "Trust agents to know quant methodology (they don't always)"
  - "Embed methodology in critic's knowledge only (architect and builder miss it)"
  - "Shared skill accessible to all agents (chosen)"
rationale: "Statistical hygiene is everyone's responsibility. Architect needs it for experiment design (how many folds? what validation scheme?). Critic needs it for review (is this overfit? did they use purged CV?). Builder needs it for implementation (correct train/test splitting, DSR calculation). A shared skill creates common vocabulary."
consequences:
  - "Deflated Sharpe Ratio (DSR) required for all backtest evaluation"
  - "Purged k-fold CV with embargo mandatory — no information leakage"
  - "Walk-forward validation as primary out-of-sample test"
  - "Fractional differentiation for stationarity while preserving memory"
  - "All agents share same statistical vocabulary and thresholds"
project: quant-knowledge-skills
tags: [methodology, statistics, overfitting, workflow, knowledge]
skill: quant-workflow
---

# Decision: Quant Workflow Skill

## Summary

Extracted quant research methodology into `skills/quant-workflow/`. Covers the research-to-production pipeline (5-stage funnel with ~13% survival rate), statistical hygiene (overfitting prevention), feature engineering for financial ML, model selection, and the daily workflow of production quant researchers.

## Non-Negotiable Statistical Hygiene

1. **Purged k-fold cross-validation** — embargo period between train/test to prevent information leakage through autocorrelated features
2. **Deflated Sharpe Ratio (DSR)** — adjusts for multiple testing. If you tested N strategies, your best Sharpe is inflated by ~√(2·ln(N))
3. **Probability of Backtest Overfitting (PBO)** — combinatorial approach via CSCV. PBO > 0.5 = likely overfit
4. **Walk-forward validation** — expanding or rolling window, never future-peeking
5. **Fractional differentiation** — d ∈ [0.3, 0.5] preserves memory while achieving stationarity

## Role-Specific Usage

| Agent | Uses skill for |
|-------|---------------|
| **Architect** | Experiment design: fold counts, validation schemes, statistical power |
| **Critic** | Review: checking for overfitting, verifying purged CV, DSR thresholds |
| **Builder** | Implementation: correct splitting, DSR calculation, walk-forward logic |

## Key Insight: The ~13% Survival Rate

Industry pipeline: ~28 ideas tested → ~15 pass signal development → ~8 survive backtesting → ~5 pass paper trading → ~3-4 go live. This steep funnel means most SNN experiments SHOULD fail — failure is the expected outcome, not a bug.

## Related

- `lessons/breakeven-accuracy-before-building.md` — calculate breakeven before spending GPU time
- `lessons/analysis-phase2-gate-mandatory.md` — why we analyze before building the next version
- `decisions/skill-extraction-from-reports.md` — extraction process
- `skills/quant-workflow/SKILL.md` — full reference
