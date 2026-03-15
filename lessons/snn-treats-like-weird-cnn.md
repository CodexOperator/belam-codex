---
primitive: lesson
date: 2026-03-14
source: V1-V3 experiment results + stock predictor analysis
confidence: high
project: snn-applied-finance
tags: [snn, architecture, critical]
applies_to: [snn-applied-finance, equilibrium-snn]
---

# Don't Treat SNNs Like Weird CNNs

Static window encoding (batch of features → spike pattern → classify) wastes the SNN's temporal advantage completely. V1 collapsed to majority-class because rate coding on 1h candles gave the SNN nothing a logistic regression couldn't do.

The paradigm shift: **continuous spike streaming** (Equilibrium SNN). Network maintains persistent state across candles. No reset between observations. Streaming inference where each new candle modulates ongoing state.

SNNs are fundamentally change-detectors, not classifiers. Use them for what they're good at.
