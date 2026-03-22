import { execSync } from 'child_process';
import { basename } from 'path';

/**
 * Supermap boot hook — agent:bootstrap handler.
 *
 * 1. Injects CODEX.codex supermap as first bootstrap file
 * 2. Replaces SOUL/IDENTITY/USER/TOOLS with [Legend active] stubs
 *    (legend is injected via prependSystemContext by codex-cockpit plugin)
 * 3. Replaces AGENTS.md with minimal startup pointer
 * 4. Replaces MEMORY.md with compressed boot index
 *
 * FLAG-1 addressed: supermap + memory-boot-index bundled into single exec
 *   with separator, halving Python startup overhead (~1s instead of ~2s).
 * FLAG-2 addressed: agentId from ctx, fallback to workspace dir parsing.
 */

// Files replaced with a simple legend-active stub
const LEGEND_STUB_FILES = new Set([
  'SOUL.md',
  'IDENTITY.md',
  'USER.md',
  'TOOLS.md',
]);

const MEMORY_FALLBACK_STUB = 'Memory: check memory/ directory for today + yesterday.';

export default async (event: any) => {
  if (event?.type !== 'agent:bootstrap') return;

  const ctx = event.context;
  if (!ctx?.workspaceDir) return;

  // ── Resolve agentId (FLAG-2) ──
  // Try ctx.agentId first, fall back to parsing workspace directory name
  let agentId: string = ctx.agentId ?? '';
  if (!agentId) {
    const dirName = basename(ctx.workspaceDir);
    const match = dirName.match(/^workspace-(.+)$/);
    agentId = match ? match[1] : 'main';
  }

  // ── Phase 1: Exec supermap + memory-boot-index in single call (FLAG-1) ──
  let supermapOutput = '';
  let memoryIndex = MEMORY_FALLBACK_STUB;

  try {
    // Bundle both commands with a separator to halve Python startup cost
    const SEPARATOR = '---CODEX_SPLIT---';
    const combined = execSync(
      `python3 scripts/codex_engine.py --supermap && echo '${SEPARATOR}' && python3 scripts/codex_engine.py --memory-boot-index`,
      {
        cwd: ctx.workspaceDir,
        timeout: 15_000,
        encoding: 'utf-8',
        stdio: ['pipe', 'pipe', 'pipe'],
      }
    ).trim();

    const splitIdx = combined.indexOf(SEPARATOR);
    if (splitIdx >= 0) {
      supermapOutput = combined.slice(0, splitIdx).trim();
      memoryIndex = combined.slice(splitIdx + SEPARATOR.length).trim() || MEMORY_FALLBACK_STUB;
    } else {
      // No separator found — treat entire output as supermap
      supermapOutput = combined;
    }
  } catch {
    // Non-fatal — degrade gracefully
  }

  // ── Phase 2: Inject supermap as first bootstrap file ──
  if (supermapOutput) {
    ctx.bootstrapFiles = ctx.bootstrapFiles || [];
    ctx.bootstrapFiles.unshift({
      name: 'CODEX.codex',
      path: `${ctx.workspaceDir}/CODEX.codex`,
      content: supermapOutput,
      missing: false,
    });
  }

  // ── Phase 3: Replace workspace file contents with stubs ──
  const agentsStub = `# Codex Layer Active
Read your role primitive: agents/${agentId}.md
Session startup: Read memory/, then pipeline context from handoff.
Orchestrator: python3 scripts/pipeline_orchestrate.py
Group chat: -5243763228`;

  if (Array.isArray(ctx.bootstrapFiles)) {
    for (const file of ctx.bootstrapFiles) {
      if (!file?.name) continue;

      if (LEGEND_STUB_FILES.has(file.name)) {
        file.content = '[Legend active — injected via before_prompt_build]';
      } else if (file.name === 'AGENTS.md') {
        file.content = agentsStub;
      } else if (file.name === 'MEMORY.md') {
        file.content = memoryIndex;
      }
      // HEARTBEAT.md, CODEX.codex, BOOTSTRAP.md — left untouched
    }
  }
};
