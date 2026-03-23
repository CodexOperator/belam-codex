/**
 * Codex Cockpit Plugin — Render Engine Edition
 *
 * Connects to the Codex Render Engine daemon via UDS for zero-latency
 * context injection on every agent turn via before_prompt_build.
 *
 * Strategy:
 *   - Render engine running → UDS query for assembled context + diff
 *   - Render engine down → fallback to codex_engine.py --supermap (cold exec)
 *   - Graceful degradation at every layer
 *
 * What agents see:
 *   - First turn: Full assembled context (supermap + orientation)
 *   - Subsequent turns: R-label diff only (what coordinates shifted)
 *   - Post-compaction: Full re-render (history may be gone)
 *
 * R-labels = coordinate landscape changes (add/remove/shift).
 * F-labels = field-level mutations, injected by orchestration engine
 * in pipeline dispatch payloads — NOT this plugin's responsibility.
 */

import { execSync } from "child_process";
import { createConnection } from "net";
import { readFileSync } from "fs";
import { basename } from "path";
import { homedir } from "os";
import { join } from "path";

// D4: Socket path moved to .codex_runtime/ under workspace (resolved per-call)
let SOCKET_PATH = join(homedir(), ".openclaw", "workspace", ".codex_runtime", "render.sock");

// ── Session state ──
let lastCoords: Map<string, string> | null = null;
let renderCount = 0;
let lastAnchorTime = 0;

/**
 * Send a JSON command to the render engine via UDS.
 * Returns parsed response or null on failure.
 */
function renderQuery(cmd: Record<string, any>, timeoutMs = 5000): Promise<Record<string, any> | null> {
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      sock.destroy();
      resolve(null);
    }, timeoutMs);

    const sock = createConnection(SOCKET_PATH);
    let buf = "";

    sock.on("connect", () => {
      sock.write(JSON.stringify(cmd) + "\n");
    });

    sock.on("data", (data) => {
      buf += data.toString();
      const nl = buf.indexOf("\n");
      if (nl >= 0) {
        clearTimeout(timer);
        try {
          resolve(JSON.parse(buf.slice(0, nl)));
        } catch {
          resolve(null);
        }
        sock.destroy();
      }
    });

    sock.on("error", () => {
      clearTimeout(timer);
      resolve(null);
    });
  });
}

/**
 * Parse supermap text into coordinate → display-text map.
 */
function parseCoords(raw: string): Map<string, string> {
  const map = new Map<string, string>();
  for (const line of raw.split("\n")) {
    const cm = line.match(/╶─\s+([a-z]+\d+)\s+(.*)/);
    if (cm) { map.set(cm[1], cm[2].trim()); continue; }
    const sm = line.match(/╶─\s+([a-z])\s+(.*)/);
    if (sm) { map.set(`_s:${sm[1]}`, sm[2].trim()); }
  }
  return map;
}

/**
 * Compute R-label diff between two coordinate maps.
 */
function rDiff(prev: Map<string, string>, curr: Map<string, string>): string | null {
  const lines: string[] = [];
  for (const [coord, text] of curr) {
    if (coord.startsWith("_s:")) continue;
    const old = prev.get(coord);
    if (!old) lines.push(`  + ${coord}  ${text}`);
    else if (old !== text) lines.push(`  Δ ${coord}  ${text}`);
  }
  for (const [coord] of prev) {
    if (coord.startsWith("_s:")) continue;
    if (!curr.has(coord)) lines.push(`  − ${coord}`);
  }
  for (const [key, text] of curr) {
    if (!key.startsWith("_s:")) continue;
    const old = prev.get(key);
    if (old && old !== text) lines.push(`  § ${key.slice(3)}  ${text}`);
  }
  return lines.length > 0 ? lines.join("\n") : null;
}

/**
 * Fallback: exec codex_engine.py --supermap (cold path).
 */
function fallbackSupermap(cwd: string): string | null {
  try {
    return execSync("python3 scripts/codex_engine.py --supermap", {
      cwd, timeout: 10_000, encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    }).trim() || null;
  } catch { return null; }
}

export default function register(api: any) {
  const workspaceDir = api.config?.workspace?.dir;

  // ── Legend injection: read dense legend once at plugin load ──
  // Legend changes require gateway restart to take effect (S-2 documented).
  let legend: string | null = null;
  if (workspaceDir) {
    const legendPath = join(workspaceDir, "codex_legend.md");
    try {
      legend = readFileSync(legendPath, "utf-8").trim();
    } catch {
      // Legend file missing — degrade gracefully, raw workspace files still work
    }
  }

  api.on("after_compaction", () => {
    lastCoords = null;
    lastAnchorTime = 0;
  });

  api.on("before_prompt_build", async (_event: any, ctx: any) => {
    const cwd = ctx?.workspaceDir || workspaceDir;
    if (!cwd) return;

    // ── Build legend prepend context ──
    let prependCtx: string | undefined;
    if (legend) {
      // Add agent mode suffix if not main workspace
      const agentId = ctx?.agentId ?? "";
      let resolvedAgent = agentId;
      if (!resolvedAgent && cwd) {
        const dirName = basename(cwd);
        const m = dirName.match(/^workspace-(.+)$/);
        resolvedAgent = m ? m[1] : "";
      }
      const modeSuffix = resolvedAgent && resolvedAgent !== "main"
        ? `\nMode: ${resolvedAgent}`
        : "";
      prependCtx = legend + modeSuffix;
    }

    // Helper: merge supermap (prepend, first in context) + legend (append, ambient)
    const withContext = (result?: Record<string, any>) => {
      const out: Record<string, any> = {};
      // Supermap + LM lands FIRST — action grammar before identity
      if (result?.supermapContext) out.prependSystemContext = result.supermapContext;
      // Legend is ambient identity — append after workspace files
      if (prependCtx) out.appendSystemContext = prependCtx;
      return Object.keys(out).length > 0 ? out : undefined;
    };

    // ── Try render engine first (hot path: ~5ms UDS round-trip) ──
    // Use 'supermap' command (not 'context' — that includes SOUL/IDENTITY/memory,
    // which are already injected by OpenClaw's own context system)
    const resp = await renderQuery({ cmd: "supermap" });

    if (resp?.ok && resp.content) {
      const supermap = resp.content as string;

      // Also grab diff since our last anchor for primitive-level changes
      let diffText: string | null = null;
      if (lastAnchorTime > 0) {
        const diffResp = await renderQuery({ cmd: "diff_since", timestamp: lastAnchorTime });
        if (diffResp?.ok && diffResp.delta) {
          diffText = diffResp.delta as string;
        }
      }
      lastAnchorTime = Date.now() / 1000;

      // First turn or post-compaction: full supermap
      if (!lastCoords) {
        lastCoords = parseCoords(supermap);
        renderCount++;
        return withContext({
          supermapContext: [
            `<!-- CODEX R${renderCount} — live render engine (${lastCoords.size} coords) -->`,
            "```",
            supermap,
            "```",
          ].join("\n"),
        });
      }

      // Subsequent turns: R-label diff
      const currCoords = parseCoords(supermap);
      const rDiffText = rDiff(lastCoords, currCoords);
      lastCoords = currCoords;

      if (!rDiffText && !diffText) return withContext(); // Nothing changed — still inject legend

      renderCount++;
      const parts: string[] = [];
      if (rDiffText) parts.push(rDiffText);
      if (diffText && diffText !== "(no changes)") parts.push(diffText);

      const changedCount = (rDiffText?.split("\n").length ?? 0);

      // Large delta → full re-render
      if (changedCount > currCoords.size * 0.6) {
        return withContext({
          supermapContext: [
            `<!-- CODEX R${renderCount} — full re-render (large delta) -->`,
            "```",
            supermap,
            "```",
          ].join("\n"),
        });
      }

      return withContext({
        supermapContext: `<!-- CODEX R${renderCount}Δ (${changedCount} shifted) -->\n${parts.join("\n")}`,
      });
    }

    // ── Fallback: cold exec path (render engine not running) ──
    const output = fallbackSupermap(cwd);
    if (!output) return withContext(); // No supermap — still inject legend if available

    const coords = parseCoords(output);

    if (!lastCoords) {
      lastCoords = coords;
      renderCount++;
      return withContext({
        supermapContext: [
          `# CODEX.codex — Supermap R${renderCount} (fallback — render engine not running)`,
          "```",
          output,
          "```",
        ].join("\n"),
      });
    }

    const diff = rDiff(lastCoords, coords);
    lastCoords = coords;
    if (!diff) return withContext(); // No diff — still inject legend

    const changedCount = diff.split("\n").length;
    if (changedCount > coords.size * 0.6) {
      renderCount++;
      return withContext({
        supermapContext: `# CODEX.codex R${renderCount} (full re-render)\n\`\`\`\n${output}\n\`\`\``,
      });
    }

    renderCount++;
    return withContext({
      supermapContext: `CODEX.codex R${renderCount}Δ (${changedCount} shifted)\n${diff}`,
    });
  });
}
