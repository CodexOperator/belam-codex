/**
 * Codex Cockpit Plugin — V7 Prepend-Only Edition
 *
 * All context goes into prependSystemContext in this order:
 *   1. Supermap (with LM entries at top) — the coordinate tree
 *   2. Legend — condensed Soul identity + "How to Use the Supermap"
 *   3. Scaffold — coordinate mode announcement/warnings
 *
 * V7 Strategy (fully synchronous — zero async, zero UDS, zero Promises):
 *   - Reads supermap from /dev/shm/openclaw/supermap.txt (written by codex_render.py)
 *   - First turn (or post-compaction): read full supermap, inject everything
 *   - Subsequent turns: check mtime — if unchanged, inject legend+scaffold only
 *   - File missing: legend+scaffold only (engine not started)
 */

import { readFileSync, existsSync, statSync } from "fs";
import { execFileSync } from "child_process";
import { basename, join } from "path";

let renderCount = 0;
let hasAnchor = false;
let lastSupermapMtime = 0;
let lastSupermapContent: string | null = null;

const SUPERMAP_PATH = "/dev/shm/openclaw/supermap.txt";

export default function register(api: any) {
  const workspaceDir = api.config?.workspace?.dir;

  // ── Legend: read once at plugin load ──
  let legend: string | null = null;
  if (workspaceDir) {
    try {
      legend = readFileSync(join(workspaceDir, "codex_legend.md"), "utf-8").trim();
    } catch {}
  }

  // ── Scaffold: coordinate mode announcement (static) ──
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

  api.on("after_compaction", () => {
    hasAnchor = false;
    lastSupermapMtime = 0;
    lastSupermapContent = null;
  });

  api.on("before_prompt_build", (_event: any, ctx: any) => {
    const cwd = ctx?.workspaceDir || workspaceDir;
    if (!cwd) return;

    // ── Resolve agent identity for mode suffix ──
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

    // ── Result register ──
    let registerCtx = "";
    try {
      const regPath = join(cwd, '.codex_runtime', 'register.json');
      const reg = JSON.parse(readFileSync(regPath, 'utf-8'));
      if (reg.latest) registerCtx = `\n\n## Result Register\n_ = ${reg.latest}`;
    } catch {}

    // ── Build: legend + scaffold (always present) ──
    const legendBlock = legend ? "\n\n" + legend + modeSuffix : "";
    const tailBlock = legendBlock + "\n\n" + COORD_SCAFFOLD + registerCtx;

    // ── Read supermap.txt synchronously ──
    const supermapPath = SUPERMAP_PATH;

    // First turn or post-compaction: poke render engine for fresh supermap, then read
    if (!hasAnchor) {
      // Trigger render engine flush + file write via UDS
      try {
        execFileSync("python3", ["-c", [
          "import socket, json, os",
          "s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)",
          "s.settimeout(3)",
          "s.connect(os.path.expanduser('~/.openclaw/workspace/.codex_runtime/render.sock'))",
          "s.sendall(json.dumps({'cmd':'supermap'}).encode() + b'\\n')",
          "s.recv(65536)",
          "s.close()",
        ].join("; ")], { timeout: 5000, stdio: "ignore" });
      } catch {
        // Engine not running — fall through to file read
      }

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
        // Engine not started — legend + scaffold only
        return { prependSystemContext: tailBlock.trim() };
      }

      hasAnchor = true;
      renderCount++;
      const supermapBlock = [
        `<!-- CODEX R${renderCount} — fresh from disk -->`,
        "```",
        content,
        "```",
      ].join("\n");

      return { prependSystemContext: supermapBlock + tailBlock };
    }

    // ── Subsequent turns: check mtime for changes ──
    if (!existsSync(supermapPath)) {
      hasAnchor = false;
      lastSupermapMtime = 0;
      lastSupermapContent = null;
      return { prependSystemContext: tailBlock.trim() };
    }

    let currentMtime = 0;
    try {
      currentMtime = statSync(supermapPath).mtimeMs;
    } catch {
      return { prependSystemContext: tailBlock.trim() };
    }

    if (currentMtime === lastSupermapMtime) {
      // Nothing changed — legend + scaffold only (supermap already seen)
      return { prependSystemContext: tailBlock.trim() };
    }

    // File changed — re-read and inject full supermap
    let content: string | null = null;
    try {
      content = readFileSync(supermapPath, 'utf-8');
      lastSupermapMtime = currentMtime;
      lastSupermapContent = content;
    } catch {
      return { prependSystemContext: tailBlock.trim() };
    }

    renderCount++;
    const supermapBlock = [
      `<!-- CODEX R${renderCount} — updated supermap -->`,
      "```",
      content,
      "```",
    ].join("\n");

    return { prependSystemContext: supermapBlock + tailBlock };
  });
}
