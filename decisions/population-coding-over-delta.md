---
primitive: decision
status: accepted
date: 2026-03-15
context: V2 and V3 experiments compared population coding vs delta encoding for SNN financial prediction
alternatives: [pure delta encoding, hybrid delta+absolute, multi-scale delta]
rationale: Population coding (35 inputs) beats delta encoding (14 inputs) by +2.11pp accuracy. Delta encoding destroys regime context — absolute feature levels (RSI, Bollinger position) carry information that delta discards. Dimensionality confound not fully resolved but the information argument is strong.
consequences: [Population coding is default for V4+, Delta encoding reserved for specialist sub-networks (crash/rally detection), Hybrid encode remains worth exploring]
project: snn-applied-finance
tags: [encoding, snn, decision]
promotion_status: exploratory
doctrine_richness: 0
contradicts: []
---

# Population Coding Over Delta Encoding (Default)

Delta encoding aligns with SNN biology (change-detectors) but destroys regime context. Markets where absolute levels matter (RSI overbought, Bollinger squeeze) lose that signal under pure delta.

Population coding with Gaussian tuning curves at [-3, -1.5, 0, 1.5, 3] preserves both level and distribution information.

Exception: specialist micro-networks for event detection (crash, rally, vol-spike) may benefit from delta encoding since they care about change magnitude, not regime.
