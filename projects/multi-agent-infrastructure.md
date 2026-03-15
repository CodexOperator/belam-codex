---
primitive: project
status: active
priority: high
owner: belam
tags: [agents, infrastructure, telegram]
start_date: 2026-03-14
---

# Multi-Agent Infrastructure

Architect/Critic/Builder agent trio with Telegram bots and shared workspace.

## Setup
- 3 Telegram bots: @BelamArchitectBot, @BelamCriticBot, @BelamBuilderBot
- Group chat ID: -5243763228
- Inter-agent comms via `sessions_send` (bots can't see each other in Telegram groups)
- Filesystem is canonical shared state

## TODO
- OpenClaw-native group chat sessions with Telegram relay bot
- True shared context, single relay bot with identity prefixes
