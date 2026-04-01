---
primitive: task
status: open
priority: high
created: 2026-03-26
owner: belam
depends_on: []
upstream: []
downstream: []
tags: [quant, infra, self-hosted]
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# Self-Hosted LLM via Colab + TurboQuant

## Description

Set up a self-hosted LLM inference endpoint on Google Colab (A100 40GB, 60 GPU-hours/month) using TurboQuant KV cache compression for extended context. Connect to OpenClaw as a zero-cost model for sub-agent workloads (builders, researchers, batch tasks).

**Key insight:** TurboQuant compresses KV cache to 3-4 bits (not model weights), enabling 4x longer context windows on the same VRAM. Open-source implementation exists with an OpenAI-compatible server built in.

## Architecture

- **GPU:** A100 40GB (Colab Pro)
- **Model candidates:** Qwen 3 32B (4-bit GPTQ/AWQ), Llama 4 Scout (17B active MoE), or best available at launch time
- **KV Cache:** TurboQuant 4-bit (`pip install turboquant`)
- **Server:** `turboquant-server` (OpenAI-compatible) or vLLM with TurboQuant KV
- **Tunnel:** ngrok or cloudflared to expose Colab port
- **OpenClaw integration:** `models.providers.vllm` config pointing at tunnel URL

## Acceptance Criteria

- [ ] Colab notebook that installs turboquant + loads quantized model
- [ ] OpenAI-compatible server running with TurboQuant KV compression
- [ ] Tunnel exposes endpoint externally
- [ ] OpenClaw config snippet tested and working
- [ ] Benchmark: context length, tok/s, quality vs Opus/Sonnet on sample tasks
- [ ] Usage guide: how to start/stop, estimated hours per workload type

## Constraints

- 60 GPU-hours/month (~2 hrs/day average) — not 24/7, on-demand only
- Quality gap vs Opus/Sonnet for complex reasoning — best suited for grunt work
- Colab session timeouts (idle disconnect, 12hr max)

## References

- Blog: https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/
- Paper: https://arxiv.org/abs/2504.19874
- Implementation: https://github.com/back2matching/turboquant (`pip install turboquant`)
- Also in llama.cpp: ggml-org/llama.cpp#20995
- OpenClaw vLLM docs: https://docs.openclaw.ai/providers/vllm
