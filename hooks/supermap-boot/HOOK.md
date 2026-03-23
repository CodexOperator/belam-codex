---
name: supermap-boot
description: "Regenerate Codex Engine supermap in AGENTS.md before each session bootstrap"
metadata:
  openclaw:
    emoji: "🗺️"
    events: ["agent:bootstrap"]
    requires:
      config: ["workspace.dir"]
---

# Supermap Boot Hook

Runs `R boot` on every `agent:bootstrap` event to regenerate the Codex Engine 
supermap section in AGENTS.md. This ensures the coordinate-addressable primitive map 
is always fresh in context without relying on separate embed_primitives runs.
