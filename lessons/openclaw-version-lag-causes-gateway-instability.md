---
primitive: lesson
date: 2026-03-24
source: main session 36029da4
confidence: confirmed
upstream: [disable-watchdog-until-systemd-service-fixed]
downstream: []
tags: [instance:main, openclaw, gateway, telegram, stability, updates]
importance: 3
---

# openclaw-version-lag-causes-gateway-instability

## Context

Gateway was freezing and Telegram was unreachable. Cron jobs were suspected first, then the gateway process itself.

## What Happened

OpenClaw was 11 days behind (2026.3.12 vs 2026.3.23-1 latest). Gateway freeze and Telegram instability symptoms aligned with known session handling and Telegram connection fixes expected in recent releases. After updating, gateway stability was restored.

## Lesson

Running OpenClaw significantly behind the latest version is a likely cause of gateway freezes and Telegram connectivity issues. Keep the install current — the project releases frequently and stability fixes land regularly.

## Application

When diagnosing gateway instability: check `openclaw --version` against latest early in the investigation. If more than a week behind, update before deep-diving into config or process issues.
