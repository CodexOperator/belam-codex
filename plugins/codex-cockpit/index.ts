/**
 * Codex Cockpit Plugin
 *
 * Diff-aware supermap injection via before_prompt_build.
 *
 * Injection strategy — R-labels only:
 *   - First turn (or post-compaction): Full supermap render (R1, R2, ...)
 *   - Subsequent turns, nothing changed: Nothing injected
 *   - Subsequent turns, coordinates shifted: R-label diff (added/removed/changed coords)
 *
 * R-labels track the supermap landscape — coordinates appearing, disappearing,
 * status/priority shifting. This is the soul instance's natural view.
 *
 * F-labels (field-level primitive mutations) are NOT injected here. Those belong
 * to the orchestration layer and get injected by pipeline_orchestrate.py when
 * handing context to builder/architect/critic agents.
 *
 * The plugin is harness-aware: ctx.agentId determines injection depth.
 * Currently all agents get R-labels. F-label injection is a future extension
 * point for pipeline sub-agents.
 */

import { execSync } from "child_process";

// ── Session state (persists across turns within gateway lifecycle) ──
let lastCoords: Map<string, string> | null = null;
let renderCount = 0;

/**
 * Parse the supermap into a coordinate → display-text map.
 * Keys are coordinate ids (t1, d5, p1, m103, mw1, md2, etc.)
 * and section headers (_s:p, _s:t, _s:m).
 * Values are the trimmed display text after the coordinate.
 */
function parseCoords(raw: string): Map<string, string> {
  const map = new Map<string, string>();
  for (const line of raw.split("\n")) {
    // Coordinate lines: "│  ╶─ t1    build-codex-engine  complete/critical  ←d26"
    const cm = line.match(/╶─\s+([a-z]+\d+)\s+(.*)/);
    if (cm) {
      map.set(cm[1], cm[2].trim());
      continue;
    }
    // Section headers: "╶─ t   tasks (19)"
    const sm = line.match(/╶─\s+([a-z])\s+(.*)/);
    if (sm) {
      map.set(`_s:${sm[1]}`, sm[2].trim());
    }
  }
  return map;
}

/**
 * Compute R-label diff between two coordinate maps.
 * Returns formatted diff string or null if nothing changed.
 */
function rDiff(
  prev: Map<string, string>,
  curr: Map<string, string>
): string | null {
  const lines: string[] = [];

  // Changed or added
  for (const [coord, text] of curr) {
    if (coord.startsWith("_s:")) continue; // section headers tracked separately
    const old = prev.get(coord);
    if (!old) {
      lines.push(`  + ${coord}  ${text}`);
    } else if (old !== text) {
      lines.push(`  Δ ${coord}  ${text}`);
    }
  }

  // Removed
  for (const [coord] of prev) {
    if (coord.startsWith("_s:")) continue;
    if (!curr.has(coord)) {
      lines.push(`  − ${coord}`);
    }
  }

  // Section count changes (e.g. "tasks (19)" → "tasks (20)")
  for (const [key, text] of curr) {
    if (!key.startsWith("_s:")) continue;
    const old = prev.get(key);
    if (old && old !== text) {
      lines.push(`  § ${key.slice(3)}  ${text}`);
    }
  }

  return lines.length > 0 ? lines.join("\n") : null;
}

export default function register(api: any) {
  const workspaceDir = api.config?.workspace?.dir;

  // After compaction the full supermap in history may be gone — force full re-render
  api.on("after_compaction", () => {
    lastCoords = null;
  });

  api.on("before_prompt_build", async (_event: any, ctx: any) => {
    const cwd = ctx?.workspaceDir || workspaceDir;
    if (!cwd) return;

    // ── Harness awareness ──
    // Cockpit (main/coordinator): R-labels only — landscape view
    // Pipeline agents (architect/critic/builder): receive both R-labels
    // (from this plugin) AND F-labels (from orchestration engine via
    // dispatch payloads and handoff context). F-labels flow between
    // pipeline agents through the orchestration engine, not this plugin.
    // const agentId = ctx?.agentId ?? "main";

    try {
      const output = execSync("python3 scripts/codex_engine.py --supermap", {
        cwd,
        timeout: 10_000,
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
      }).trim();

      if (!output) return;

      const coords = parseCoords(output);

      // ── First turn or post-compaction: full R-label render ──
      if (!lastCoords) {
        lastCoords = coords;
        renderCount++;

        return {
          appendSystemContext: [
            `# CODEX.codex — Live Supermap R${renderCount} (auto-injected by codex-cockpit)`,
            "",
            "Navigate with coordinates: `t1` (view task), `d5` (view decision), `m103` (view memory entry).",
            "Edit with: `e1 t1 status active` (set field), `e2 l \"new lesson\"` (create).",
            "Modes: `e0` (orchestrate), `e1` (edit), `e2` (create), `e3` (extend).",
            "",
            "```",
            output,
            "```",
          ].join("\n"),
        };
      }

      // ── Subsequent turns: R-label diff ──
      const diff = rDiff(lastCoords, coords);
      lastCoords = coords;

      if (!diff) return; // Nothing changed — inject nothing

      // If diff is huge (>60% of coords changed), full re-render is cheaper
      const changedCount = diff.split("\n").length;
      if (changedCount > coords.size * 0.6) {
        renderCount++;
        return {
          appendSystemContext: [
            `# CODEX.codex R${renderCount} (full re-render — large delta)`,
            "",
            "```",
            output,
            "```",
          ].join("\n"),
        };
      }

      // Small delta — R-label diff only
      renderCount++;
      return {
        appendSystemContext: `CODEX.codex R${renderCount}Δ (${changedCount} coord${changedCount !== 1 ? "s" : ""} shifted)\n${diff}`,
      };
    } catch {
      return;
    }
  });
}
