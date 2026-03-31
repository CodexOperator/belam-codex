---
primitive: lesson
date: 2026-03-14
source: Multi-agent Telegram setup
confidence: high
project: multi-agent-infrastructure
tags: [telegram, agents, infrastructure]
applies_to: [multi-agent-infrastructure]
promotion_status: exploratory
doctrine_richness: 0
contradicts: []
---

# Telegram Bots Cannot See Other Bots' Messages

In group chats, Telegram bots are invisible to each other. This breaks any architecture that assumes bots can read each other's messages.

Solution: Use `sessions_send` for inter-agent communication. Group chat becomes Shael's dashboard only. Filesystem is the canonical shared state.

Future: OpenClaw-native group chat sessions with a single relay bot that surfaces all agent messages with identity prefixes.
