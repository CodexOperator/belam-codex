---
primitive: lesson
date: 2026-04-14
source: (add source)
confidence: high
upstream: []
downstream: []
tags: [instance:main, openclaw, oauth, openai, configuration]
---

# openclaw-oauth-provider-reuses-codex-cli-chatgpt-tokens

## Context

Needed to switch OpenClaw from Anthropic Claude to OpenAI GPT-5.4 as default model. No OpenAI API key available, but ChatGPT subscription credits and Codex CLI OAuth tokens existed via Hermes install.

## What Happened

OpenClaw `models.providers` config supports `auth: "oauth"` mode. ChatGPT OAuth access tokens from Codex CLI auth storage (`~/.codex/auth.json` or `~/.hermes/auth.json` under `providers.openai-codex.tokens.access_token`) can be placed directly as the `apiKey` value in the provider config. The `api` field should be `openai-responses` (not `openai-codex-responses` which is for Codex-specific API). Multiple config validation errors occurred before discovering that `baseUrl` is required even with OAuth, and the `models` array must be provided to register specific model ids.

## Lesson

OpenClaw can route through ChatGPT subscription credits using OAuth JWT tokens extracted from Codex CLI auth — no separate OpenAI API key needed. Tokens expire (~72h) and need periodic refresh.

## Application

- When switching OpenClaw to OpenAI models without API key: extract access_token from Codex CLI auth, set `auth: "oauth"`, `api: "openai-responses"`, provide `baseUrl` and `models` array
- Token refresh must be handled externally (Hermes gateway daemon auto-refreshes, or manual re-extraction)
- `openai-codex-responses` API type is distinct from `openai-responses` — use the latter for general OpenAI model routing
