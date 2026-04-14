/**
 * Codex Cockpit Plugin — V10 Daemonless Direct Render
 *
 * All context goes into prependSystemContext in this order:
 *   1. Supermap — rendered synchronously each turn via scripts/render_supermap.py
 *   2. Legend — condensed Soul identity + "How to Use the Supermap"
 *   3. Scaffold — coordinate mode announcement/warnings
 *
 * Strategy:
 *   - No daemon, no UDS, no /dev/shm dependency
 *   - Render on demand each turn from the canonical workspace
 *   - Fall back softly to legend+scaffold when rendering fails
 */

import { readFileSync, existsSync } from "fs";
import { execFileSync } from "child_process";
import { homedir } from "os";
import { basename, join } from "path";

let renderCount = 0;

function looksLikeWorkspace(candidate: string | null | undefined): candidate is string {
  if (!candidate) return false;
  return existsSync(join(candidate, "scripts", "codex_engine.py"));
}

function resolveWorkspace(currentDir: string | null | undefined, configuredDir: string | null | undefined): string | null {
  if (looksLikeWorkspace(currentDir)) return currentDir;

  const envCandidates = [
    process.env.BELAM_WORKSPACE,
    process.env.OPENCLAW_WORKSPACE,
    process.env.WORKSPACE,
  ];
  for (const candidate of envCandidates) {
    if (looksLikeWorkspace(candidate)) return candidate;
  }

  const home = homedir();
  const fallbacks = [
    configuredDir,
    join(home, ".hermes", "belam-codex"),
    join(home, ".openclaw", "workspace"),
  ];
  for (const candidate of fallbacks) {
    if (looksLikeWorkspace(candidate)) return candidate;
  }
  return configuredDir ?? currentDir ?? null;
}

function renderSupermap(workspace: string): string | null {
  try {
    return execFileSync("python3", ["scripts/render_supermap.py"], {
      cwd: workspace,
      timeout: 8000,
      encoding: "utf-8",
      env: {
        ...process.env,
        BELAM_WORKSPACE: workspace,
        OPENCLAW_WORKSPACE: workspace,
      },
    }).trim();
  } catch {
    return null;
  }
}

export default function register(api: any) {
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
    "⚠️ Shell: pass e-mode args as separate tokens, not one quoted string: `e2 t \"title\"` ✅ `'e2 t \"title\"'` ❌",
  ].join("\n");

  api.on("after_compaction", () => {
    renderCount = 0;
  });

  api.on("before_prompt_build", (_event: any, ctx: any) => {
    const currentDir = ctx?.workspaceDir || api.config?.workspace?.dir;
    if (!currentDir) return;
    const workspace = resolveWorkspace(currentDir, api.config?.workspace?.dir);
    if (!workspace) return;

    // ── Resolve agent identity for mode suffix ──
    const agentId = ctx?.agentId ?? "";
    let resolvedAgent = agentId;
    if (!resolvedAgent && currentDir) {
      const dirName = basename(currentDir);
      const m = dirName.match(/^workspace-(.+)$/);
      resolvedAgent = m ? m[1] : "";
    }
    const modeSuffix = resolvedAgent && resolvedAgent !== "main"
      ? `\nMode: ${resolvedAgent}`
      : "";

    // ── Result register ──
    let registerCtx = "";
    try {
      const regPath = join(currentDir, ".codex_runtime", "register.json");
      const reg = JSON.parse(readFileSync(regPath, 'utf-8'));
      if (reg.latest) registerCtx = `\n\n## Result Register\n_ = ${reg.latest}`;
    } catch {}

    let legend: string | null = null;
    try {
      legend = readFileSync(join(workspace, "codex_legend.md"), "utf-8").trim();
    } catch {}

    // ── Build: legend + scaffold (always present) ──
    const legendBlock = legend ? "\n\n" + legend + modeSuffix : "";
    const tailBlock = legendBlock + "\n\n" + COORD_SCAFFOLD + registerCtx;

    const content = renderSupermap(workspace);
    if (!content) {
      return { prependSystemContext: tailBlock.trim() };
    }

    renderCount++;
    const supermapBlock = [
      `<!-- CODEX R${renderCount} — direct render -->`,
      "```",
      content,
      "```",
    ].join("\n");

    return { prependSystemContext: supermapBlock + tailBlock };
  });
}
