---
primitive: lesson
date: 2026-03-19
source: V2 critic review — population coding (35 inputs) vs delta encoding (14 inputs) confound
confidence: high
project: snn-applied-finance
tags: [snn, encoding, experimental-design]
applies_to: [snn-applied-finance]
---

# Control Input Dimensionality When Comparing Encoding Schemes

V2 showed population coding (Scheme 0) outperforming delta encoding (Scheme A) by ~2pp accuracy. But population coding uses 35 input neurons (7 features × 5 Gaussian neurons) while delta uses 14 (7 features × 2 channels pos/neg). More inputs → more first-layer capacity → potentially better performance regardless of encoding quality.

**This is a critical confound.** Until controlled, the statement "population coding outperforms delta encoding" should be qualified as "population coding with higher input dimensionality outperforms delta encoding with lower input dimensionality."

**Required controls (not yet run):**
1. Scheme 0 with 2 neurons/feature (14 inputs) — matches delta dimensionality
2. Delta encoding with 5 channels/feature (35 inputs) — matches Scheme 0 dimensionality
3. Random projection of Scheme 0 to 14 dims — removes dimensionality advantage

**General principle:** When comparing encoding schemes, always match input dimensionality or include it as an explicit factor in the experimental design. Otherwise you're comparing encoding quality AND model capacity simultaneously.
