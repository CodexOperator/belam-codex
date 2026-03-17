---
topic: Financial Data Encoding
tags: [bitcoin, candle, delta encoding, financial, ohlcv, population coding, price, rate coding]
created: 2026-03-17
updated: 2026-03-17
sources: [lessons/beta-convergence-is-market-determined.md, lessons/breakeven-accuracy-before-building.md, lessons/confident-abstention-is-signal.md, lessons/event-detection-not-state-classification.md, lessons/pipeline-table-separator-required.md, lessons/snn-treats-like-weird-cnn.md, lessons/tiny-snn-gpu-parallelism.md]
related: [agent-coordination, experiment-methodology, research-workflow, snn-architecture]
---

# Financial Data Encoding

## Key Findings

- Confidence thresholding (trade top-30% signals only) *(lessons/breakeven-accuracy-before-building.md)*
- Daily resolution (breakeven drops to ~55.1%) *(lessons/breakeven-accuracy-before-building.md)*
- Maker orders (0.02% cost → breakeven ~50.7%) *(lessons/breakeven-accuracy-before-building.md)*
- Always calculate the minimum accuracy required for profitability at your target resolution and cost structure BEFORE committing to a model architecture. *(lessons/breakeven-accuracy-before-building.md)*
- 50-neuron specialist micro-networks show genuine signal for event detection (CrashDetector, RallyDetector, VolSpikeDetector) but fail completely for state classification (SidewaysDetector, TrendFollower). *(lessons/event-detection-not-state-classification.md)*
- Root cause: T=20 temporal window insufficient for sustained-state detection. Events are transient spikes — perfect for SNN change-detection. States require persistent temporal context beyond the window. *(lessons/event-detection-not-state-classification.md)*
- `pipeline_update.py` parses stage history tables by looking for `| Stage |` followed immediately by a `|---|---|---|---|` separator row on the next line. If the markdown separator row is missing, the parser silently fails and only updates the state JSON — the markdown file gets no stage history entries. *(lessons/pipeline-table-separator-required.md)*
- `pipeline_update.py <version> show` works (reads JSON state) *(lessons/pipeline-table-separator-required.md)*
- But `pipelines/<version>.md` stage history table stays empty *(lessons/pipeline-table-separator-required.md)*
- No error message — silent fallback to JSON-only update *(lessons/pipeline-table-separator-required.md)*
- The pipeline template (`templates/pipeline.md`) should include the separator row *(lessons/pipeline-table-separator-required.md)*
- When creating new pipeline primitives, verify table structure before first update *(lessons/pipeline-table-separator-required.md)*
- Consider hardening `pipeline_update.py` to warn (not silently skip) when separator is missing *(lessons/pipeline-table-separator-required.md)*
- Static window encoding (batch of features → spike pattern → classify) wastes the SNN's temporal advantage completely. V1 collapsed to majority-class because rate coding on 1h candles gave the SNN nothing a logistic regression couldn't do. *(lessons/snn-treats-like-weird-cnn.md)*
- SNNs are fundamentally change-detectors, not classifiers. Use them for what they're good at. *(lessons/snn-treats-like-weird-cnn.md)*
- 5. **Explicit cleanup:** `del model` + `gc.collect()` + `torch.cuda.empty_cache()` after every fold. Without this, VRAM climbs ~50-100MB per experiment and never comes back. *(lessons/tiny-snn-gpu-parallelism.md)*
- **fp16/mixed precision:** BCELoss produces NaN/Inf under autocast. Models are too small to benefit anyway. *(lessons/tiny-snn-gpu-parallelism.md)*
- **Conservative worker counts:** 3-6 workers on a T4 leaves >60% of GPU idle between kernel launches. *(lessons/tiny-snn-gpu-parallelism.md)*
- **Relying on Python GC alone:** PyTorch's CUDA caching allocator holds memory even after Python objects are collected. Must explicitly call `torch.cuda.empty_cache()`. *(lessons/tiny-snn-gpu-parallelism.md)*

## Notes

*(Add contextual notes here as patterns emerge)*

## See Also

- [→ Daily 2026-03-17](../memory/2026-03-17.md)
