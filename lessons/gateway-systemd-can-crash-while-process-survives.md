---
primitive: lesson
date: 2026-03-23
source: gateway debugging session 2026-03-23
confidence: high
importance: 3
upstream: []
downstream: []
tags: [instance:main, gateway, systemd, telegram, debugging]
---

# gateway-systemd-can-crash-while-process-survives

## Context

Telegram stopped responding. Checked systemd: `openclaw-gateway.service` showed as
`inactive (dead)` — failed with `Missing config. Run openclaw setup`. 12 restart attempts.

## What Happened

The **systemd service wrapper** crashed (exit-code 1) due to a config issue in the restarted
process. But the **original gateway process** (pid 2934107) had been started separately and was
still alive and running — handling Telegram, sessions, and plugins normally. A `sendMessage ok`
appeared in logs at 18:17 UTC while systemd showed the service as dead.

## Lesson

`systemctl status openclaw-gateway` showing dead/inactive does NOT mean the gateway is down —
the actual process may still be running if it was started outside of systemd (e.g., manually or
by a prior service instance).

## Application

- Before concluding gateway is down, check `ps aux | grep openclaw-gateway` directly.
- The systemd service and the running process are separate — `systemctl` only tracks processes
  it started itself.
- Investigate with `journalctl` + `ps` together; don't rely on systemd status alone.
