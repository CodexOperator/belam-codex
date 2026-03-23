/**
 * Codex Cockpit Plugin — V4 RAM-First UDS Edition
 *
 * Injects always-fresh supermap context on every agent turn via before_prompt_build.
 *
 * V4 Strategy:
 *   - All engine communication via native UDS socket (no subprocess spawning)
 *   - First turn (or post-compaction): supermap + anchor_reset via UDS
 *   - Subsequent turns: my_diff (per-session anchor) via UDS (S1: per-agent diffs)
 *   - codexExec() retained as fallback only (engine not running)
 *   - ~180× speedup: ~900ms→~5ms first turn, ~350ms→~2ms subsequent
 *
 * What agents see:
 *   - First turn: Full supermap with coordinate nav instructions
 *   - Subsequent turns: Only what changed (R-label diff)
 *   - Post-compaction: Full re-render (anchor is reset)
 */

import { execSync } from "child_process";
import { readFileSync, existsSync, mkdirSync } from "fs";
import { basename, join } from "path";
import { createConnection } from "net";

let renderCount = 0;
let hasAnchor = false;
let pluginSessionId: string | null = null;

// ── UDS Client ─────────────────────────────────────────────────────────────

/**
 * D4: Native UDS query — replaces execSync subprocess calls.
 * Returns parsed JSON response or null on any failure.
 */
function udsQuery(sockPath: string, cmd: object, timeoutMs = 2000): Promise<any> {
  return new Promise((resolve, reject) => {
    const conn = createConnection(sockPath, () => {
      conn.write(JSON.stringify(cmd) + '\n');
    });

    let buf = '';
    conn.on('data', (chunk: Buffer) => {
      buf += chunk.toString();
      const nl = buf.indexOf('\n');
      if (nl >= 0) {
        try { resolve(JSON.parse(buf.slice(0, nl))); }
        catch { reject(new Error('bad JSON from engine')); }
        conn.destroy();
      }
    });

    conn.on('error', reject);
    const timer = setTimeout(() => { conn.destroy(); reject(new Error('uds timeout')); }, timeoutMs);
    conn.on('close', () => clearTimeout(timer));
  });
}

/**
 * D4: UDS health check — native ping/pong (replaces Python subprocess ping).
 * Returns true if engine is healthy, false otherwise.
 */
async function udsPing(sockPath: string): Promise<boolean> {
  try {
    const resp = await udsQuery(sockPath, { cmd: 'ping' }, 1000);
    return resp?.ok === true && resp?.msg === 'pong';
  } catch {
    return false;
  }
}

// ── Fallback: subprocess exec (only when engine is down) ───────────────────

/**
 * Run codex_engine.py with given flag. Fallback only — used when UDS unavailable.
 */
function codexExec(flag: string, cwd: string): string | null {
  try {
    return execSync(`python3 scripts/codex_engine.py ${flag}`, {
      cwd, timeout: 10_000, encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    }).trim() || null;
  } catch { return null; }
}

// ── Engine Lifecycle ───────────────────────────────────────────────────────

/**
 * Ensure render engine is running. D4: uses native UDS ping (not subprocess).
 */
async function ensureRenderEngine(cwd: string): Promise<string> {
  const runtimeDir = join(cwd, '.codex_runtime');
  const sockPath = join(runtimeDir, 'render.sock');

  try { mkdirSync(runtimeDir, { recursive: true }); } catch {}

  // D4: Native UDS ping (replaces Python subprocess ping — ~500ms → ~1ms)
  if (existsSync(sockPath)) {
    if (await udsPing(sockPath)) return sockPath;
    // Stale socket — remove it
    try { execSync(`rm -f "${sockPath}"`, { cwd, stdio: "ignore" }); } catch {}
  }

  // Start render engine in background
  try {
    execSync(
      `nohup python3 scripts/codex_render.py > /dev/null 2>&1 &`,
      { cwd, stdio: "ignore", timeout: 3000 }
    );
    // Brief wait for socket to appear
    await new Promise(r => setTimeout(r, 500));
  } catch {}

  return sockPath;
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
    pluginSessionId = null;
  });

  api.on("before_prompt_build", async (_event: any, ctx: any) => {
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

    // ── Result register injection (Phase 1 FLAG-1 fix: direct file read, not subprocess) ──
    let registerCtx = "";
    try {
      const regPath = join(cwd, '.codex_runtime', 'register.json');
      const reg = JSON.parse(readFileSync(regPath, 'utf-8'));
      if (reg.latest) registerCtx = `\n\n## Result Register\n_ = ${reg.latest}`;
    } catch {
      // No register file — try subprocess fallback
      const registerOutput = codexExec("--register-show", cwd);
      if (registerOutput) registerCtx = `\n\n## Result Register\n${registerOutput}`;
    }

    // Helper: merge legend + register into result
    const withLegend = (append?: string) => {
      const out: Record<string, any> = {};
      if (prependCtx) out.prependSystemContext = prependCtx;
      const combined = (append || "") + registerCtx;
      if (combined) out.appendSystemContext = combined;
      return Object.keys(out).length > 0 ? out : undefined;
    };

    // ── D4: Ensure render engine + get UDS socket path ──
    const sockPath = await ensureRenderEngine(cwd);
    const engineUp = existsSync(sockPath) && await udsPing(sockPath);

    // ── First turn or post-compaction: anchor + full render ──
    if (!hasAnchor) {
      let output: string | null = null;

      if (engineUp) {
        // D4: UDS-only path — attach + anchor_reset + supermap (~5ms total)
        try {
          // Attach to get a session ID for per-agent diffs (S1)
          if (!pluginSessionId) {
            const attachResp = await udsQuery(sockPath, {
              cmd: 'attach', agent: 'cockpit'
            });
            if (attachResp?.ok) pluginSessionId = attachResp.session_id;
          }
          // Reset anchor
          await udsQuery(sockPath, { cmd: 'anchor_reset' });
          // Get full supermap from RAM
          const smResp = await udsQuery(sockPath, { cmd: 'supermap' });
          if (smResp?.ok && smResp.content) output = smResp.content;
        } catch {
          // UDS failed — fall through to subprocess fallback
        }
      }

      if (!output) {
        // Fallback: subprocess (V3 behavior, ~600ms)
        codexExec("--render-anchor-reset", cwd);
        output = codexExec("--supermap-anchor", cwd);
      }

      if (!output) return withLegend();

      hasAnchor = true;
      renderCount++;
      return withLegend([
        `<!-- CODEX R${renderCount} — fresh from RAM -->`,
        "",
        "Navigate: `t1` `d5` `m103`. Edit: `e1 t1 status active`. Create: `e2 l \"title\"`.",
        "Modes: `e0` orchestrate, `e1` edit, `e2` create, `e3` extend.",
        "",
        "```",
        output,
        "```",
      ].join("\n"));
    }

    // ── Subsequent turns: diff via UDS (S1: my_diff for per-agent anchor) ──
    let diff: string | null = null;

    if (engineUp) {
      try {
        // S1: Use my_diff for per-session anchor-aware diffs
        const diffResp = pluginSessionId
          ? await udsQuery(sockPath, { cmd: 'my_diff', session_id: pluginSessionId })
          : await udsQuery(sockPath, { cmd: 'diff' });

        if (diffResp?.ok && diffResp.delta) {
          // delta is an array of diff entries — format them
          const entries = Array.isArray(diffResp.delta) ? diffResp.delta : [];
          if (entries.length > 0) {
            diff = entries.map((d: any) => {
              const kind = d.kind === 'added' ? '+' : d.kind === 'removed' ? '−' : 'Δ';
              const fields = (d.field_diffs || [])
                .map((f: any) => `${f[0]}: ${f[1] ?? '∅'} → ${f[2] ?? '∅'}`)
                .join(', ');
              return `  ${kind} ${d.coord || '?'} ${d.slug || ''} ${fields}`.trim();
            }).join('\n');
          }
        }
      } catch {
        // UDS failed — fall through to subprocess fallback
      }
    }

    if (!diff) {
      // Fallback: subprocess diff (V3 behavior)
      diff = codexExec("--render-diff", cwd) || codexExec("--supermap-diff", cwd);
    }

    if (!diff) return withLegend(); // Nothing changed — legend only

    renderCount++;
    const lines = diff.split("\n");
    const isFullRender = !lines[0].startsWith("  ");

    if (isFullRender) {
      return withLegend([
        `<!-- CODEX R${renderCount} — full render (anchor reset) -->`,
        "```",
        diff,
        "```",
      ].join("\n"));
    }

    return withLegend(`<!-- CODEX R${renderCount}Δ (${lines.length} shifted) -->\n${diff}`);
  });
}
