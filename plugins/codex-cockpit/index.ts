/**
 * Codex Cockpit Plugin — V6 Sync File-Based Edition
 *
 * Injects always-fresh supermap context on every agent turn via before_prompt_build.
 *
 * V6 Strategy (fully synchronous — zero async, zero UDS, zero Promises):
 *   - Reads supermap from .codex_runtime/supermap.txt (written by codex_render.py)
 *   - On first turn (or post-compaction): read full supermap file and inject
 *   - On subsequent turns: check statSync mtime — if unchanged, inject legend only
 *     (nothing changed); if changed, re-read and inject full supermap
 *   - If supermap.txt doesn't exist: inject legend only (engine not started yet)
 *   - All other injections (legend, register) are already sync file reads
 *
 * What agents see:
 *   - First turn: Full supermap with coordinate nav instructions
 *   - Subsequent turns: Full supermap only if file changed (mtime diff), else legend only
 *   - Post-compaction: Full re-render (state is reset)
 *   - Engine down / file missing: Legend + scaffold only (no error, no spawn)
 */

import { readFileSync, existsSync, statSync } from "fs";
import { basename, join } from "path";

let renderCount = 0;
let hasAnchor = false;
let lastSupermapMtime = 0;
let lastSupermapContent: string | null = null;

const SUPERMAP_PATH = "/dev/shm/openclaw/supermap.txt";

// R-label only agents: coordinator sees summary diffs only.
// Pipeline agents (architect, critic, builder, sage) see R+F labels.
const R_LABEL_ONLY_AGENTS = new Set(["main", "cockpit", ""]);

function shouldIncludeContent(agentId: string): boolean {
  return !R_LABEL_ONLY_AGENTS.has(agentId);
}

export default function register(api: any) {
  const workspaceDir = api.config?.workspace?.dir;

  // ── Legend injection: read dense legend once at plugin load ──
  let legend: string | null = null;
  if (workspaceDir) {
    try {
      legend = readFileSync(join(workspaceDir, "codex_legend.md"), "utf-8").trim();
    } catch {}
  }

  api.on("after_compaction", () => {
    hasAnchor = false;
    lastSupermapMtime = 0;
    lastSupermapContent = null;
  });

  api.on("before_prompt_build", (_event: any, ctx: any) => {
    const cwd = ctx?.workspaceDir || workspaceDir;
    if (!cwd) return;

    // ── D6: Coordinate Mode Boot Scaffold (static, cacheable) ──
    const COORD_SCAFFOLD = [
      "## ⚡ Coordinate Mode Active",
      "Navigate: {coord} (t1, p3, d5) | Edit: e1{coord} {f} {v} | Create: e2 {ns} \"title\"",
      "Orchestrate: e0 (sweep) | e0 t{n} (launch) | e0 p{n} (status/archive/complete)",
      "Extend: e3 {ns}.{sub} (register new sub-namespace when actions are missing)",
      "Diff: .d | Anchor: .a | Filter: --tag {t} --since {d} --as {role}",
      "Shell: !{cmd} (escape hatch only) | Pipe: cmd |> cmd",
      "🔧 Missing a coord? Create it: e2 for primitives, e3 for new action namespaces.",
      "🚀 Need work done? e0 t{n} to launch a pipeline, sessions_spawn for sub-agents.",
      "❌ Do NOT use grep/cat/echo/ls on workspace files — there is a coordinate for it.",
    ].join("\n");

    // ── Build legend prepend (scaffold first, then legend) ──
    let prependCtx: string | undefined;
    if (legend) {
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
      prependCtx = COORD_SCAFFOLD + "\n\n" + legend + modeSuffix;
    } else {
      prependCtx = COORD_SCAFFOLD;
    }

    // ── Result register injection (direct file read) ──
    let registerCtx = "";
    try {
      const regPath = join(cwd, '.codex_runtime', 'register.json');
      const reg = JSON.parse(readFileSync(regPath, 'utf-8'));
      if (reg.latest) registerCtx = `\n\n## Result Register\n_ = ${reg.latest}`;
    } catch {
      // No register file — skip silently
    }

    // Helper: merge legend + register into result
    const withLegend = (append?: string) => {
      const out: Record<string, any> = {};
      if (prependCtx) out.prependSystemContext = prependCtx;
      const combined = (append || "") + registerCtx;
      if (combined) out.appendSystemContext = combined;
      return Object.keys(out).length > 0 ? out : undefined;
    };

    // ── Read supermap.txt synchronously ──
    const supermapPath = SUPERMAP_PATH;

    // First turn or post-compaction: always try to read
    if (!hasAnchor) {
      let content: string | null = null;

      if (existsSync(supermapPath)) {
        try {
          const st = statSync(supermapPath);
          content = readFileSync(supermapPath, 'utf-8');
          lastSupermapMtime = st.mtimeMs;
          lastSupermapContent = content;
        } catch {
          content = null;
        }
      }

      if (!content) {
        // Engine not started or file missing — legend only
        return withLegend();
      }

      hasAnchor = true;
      renderCount++;
      return withLegend([
        `<!-- CODEX R${renderCount} — fresh from disk -->`,
        "",
        "Navigate: `t1` `d5` `m103`. Edit: `e1 t1 status active`. Create: `e2 l \"title\"`.",
        "Modes: `e0` orchestrate, `e1` edit, `e2` create, `e3` extend.",
        "",
        "```",
        content,
        "```",
      ].join("\n"));
    }

    // ── Subsequent turns: check mtime for changes ──
    if (!existsSync(supermapPath)) {
      // File disappeared — legend only, reset state
      hasAnchor = false;
      lastSupermapMtime = 0;
      lastSupermapContent = null;
      return withLegend();
    }

    let currentMtime = 0;
    try {
      currentMtime = statSync(supermapPath).mtimeMs;
    } catch {
      return withLegend();
    }

    if (currentMtime === lastSupermapMtime) {
      // Nothing changed — inject legend only
      return withLegend();
    }

    // File changed — re-read and inject full supermap
    let content: string | null = null;
    try {
      content = readFileSync(supermapPath, 'utf-8');
      lastSupermapMtime = currentMtime;
      lastSupermapContent = content;
    } catch {
      return withLegend();
    }

    renderCount++;
    return withLegend([
      `<!-- CODEX R${renderCount} — updated supermap -->`,
      "",
      "Navigate: `t1` `d5` `m103`. Edit: `e1 t1 status active`. Create: `e2 l \"title\"`.",
      "Modes: `e0` orchestrate, `e1` edit, `e2` create, `e3` extend.",
      "",
      "```",
      content,
      "```",
    ].join("\n"));
  });
}
