---
primitive: task
status: open
priority: medium
owner: builder
tags: [backtesting, infrastructure]
project: snn-applied-finance
estimate: 1 day
depends_on: [build-equilibrium-snn]
---

# Set Up Two-Phase Backtest Pipeline

Implement the industry-standard two-phase workflow: VectorBT PRO for parameter sweeps → NautilusTrader for production validation.

## Steps
1. Install VectorBT PRO and NautilusTrader
2. Create strategy adapter that works in both frameworks
3. Configure walk-forward validation with purged CV (7+ folds)
4. Add transaction cost modeling (square-root impact)
5. Set up DSR and PBO computation

## References
- [[two-phase-backtest-workflow]]
- quant-infrastructure skill
- quant-workflow skill
