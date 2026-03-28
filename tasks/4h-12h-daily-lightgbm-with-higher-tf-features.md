---
primitive: task
status: open
priority: high
created: 2026-03-28
owner: belam
depends_on: [higher-timeframe-feature-generation-12h-1d-1w-1m]
upstream: []
downstream: []
tags: [quant, microcap-swing, model-training]
---

## 4h / 12h / Daily LightGBM with Higher-TF Features

### Goal
Run the full LGBM pipeline at 4h, 12h, and daily base timeframes using newly generated higher-TF features (12h, 1d, 1w, 1M).

### Depends On
- t5 (higher-timeframe-feature-generation) MUST complete first

### Test Matrix
| Base TF | Tokens | Cross-Asset Variants | Expected MTF Anchor |
|---|---|---|---|
| 4h | BTC, ETH, SOL | yes/no | 1d RSI, 1w RSI |
| 12h | BTC, ETH, SOL | yes/no | 1w RSI, 1M RSI |  
| 1d | BTC, ETH, SOL | yes/no | 1w RSI, 1M RSI |

### Evaluation
- Compare lift over baseline at each timeframe
- Verify fractal hierarchy: does the model pick weekly RSI as #1 feature at 4h?
- Compare to 30m results (the current best)
- Check if the bear bias persists at higher TFs or flips

### Holding Period Adjustment
- 4h: max_holding_candles needs tuning (currently 24 candles = 4 days at 4h)
- 12h: ~12 days holding period
- Daily: ~24 days holding period
- May need different triple barrier parameters per timeframe

### Success Criteria
- 4h model achieves >1% lift (vs current 0.00%)
- At least one higher TF achieves >2% lift
- Feature importance confirms higher-TF RSI as primary anchor
