/**
 * Codex Cockpit Plugin — V10 Daemonless Direct Render
 *
 * All context goes into prependSystemContext in this order:
 *   1. Supermap — rendered synchronously each turn via scripts/render_supermap.py
 *   2. Startup docs — loaded from AGENTS.md "Injection Template"
 *   3. Scaffold — coordinate mode announcement/warnings
 *
 * Strategy:
 *   - No daemon, no UDS, no /dev/shm dependency
 *   - Render on demand each turn from the canonical workspace
 *   - Fall back softly to startup docs + scaffold when rendering fails
 */

import { readFileSync, existsSync } from "fs";
import { execFileSync } from "child_process";
import { homedir } from "os";
import { basename, join } from "path";

let renderCount = 0;

const DEFAULT_INJECT_FILES = ["SOUL.md", "IDENTITY.md", "USER.md", "codex_legend.md"];

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

function loadInjectionTemplate(workspace: string): string[] {
  try {
    const agents = readFileSync(join(workspace, "AGENTS.md"), "utf-8");
    const marker = "## Injection Template";
    const index = agents.indexOf(marker);
    if (index === -1) return [...DEFAULT_INJECT_FILES];
    const section = agents.slice(index + marker.length);
    const files: string[] = [];
    for (const rawLine of section.split("\n")) {
      const line = rawLine.trim();
      if (line.startsWith("## ")) break;
      if (!line.startsWith("-")) continue;
      let item = line.slice(1).trim();
      if (item.includes("—")) item = item.split("—", 1)[0].trim();
      if (item.toUpperCase().endsWith("MAIN SESSION ONLY") && item.includes("-")) {
        item = item.slice(0, item.lastIndexOf("-")).trim();
      }
      const tickMatch = item.match(/`([^`]+)`/);
      if (tickMatch) item = tickMatch[1].trim();
      if (item) files.push(item);
    }
    return files.length ? files : [...DEFAULT_INJECT_FILES];
  } catch {
    return [...DEFAULT_INJECT_FILES];
  }
}

function readInjectedDocs(workspace: string): string {
  const blocks: string[] = [];
  for (const relPath of loadInjectionTemplate(workspace)) {
    const absPath = join(workspace, relPath);
    if (!existsSync(absPath)) continue;
    try {
      const content = readFileSync(absPath, "utf-8").trim();
      if (!content) continue;
      let heading = basename(relPath).replace(/\.md$/i, "").replace(/[_-]/g, " ");
      heading = heading.replace(/\b\w/g, (c) => c.toUpperCase());
      if (basename(relPath) === "codex_legend.md") heading = "Legend";
      blocks.push(`## ${heading}\n${content}`);
    } catch {}
  }
  return blocks.join("\n\n");
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

    const injectedDocs = readInjectedDocs(workspace);

    // ── Build: AGENTS-driven startup docs + scaffold (always present) ──
    const docsBlock = injectedDocs ? "\n\n" + injectedDocs + modeSuffix : modeSuffix;
    const tailBlock = docsBlock + "\n\n" + COORD_SCAFFOLD + registerCtx;

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
