import { execSync } from 'child_process';
import { readFileSync, writeFileSync, appendFileSync, mkdirSync, readdirSync } from 'fs';
import { spawn } from 'child_process';
import * as path from 'path';
import * as os from 'os';

// ── Logging ──────────────────────────────────────────────────────────────────
const LOG_DIR = path.join(os.homedir(), '.openclaw/workspace/logs');
const LOG_FILE = path.join(LOG_DIR, 'memory-extract.log');

function log(level: string, msg: string, data?: Record<string, unknown>) {
  const ts = new Date().toISOString();
  const extra = data ? ' ' + JSON.stringify(data) : '';
  try {
    mkdirSync(LOG_DIR, { recursive: true });
    appendFileSync(LOG_FILE, `${ts} [${level}] ${msg}${extra}\n`);
  } catch { /* can't log — nothing we can do */ }
}

// ── Session context save (replaces bundled session-memory) ───────────────────

function findSessionFile(sessionsDir: string, sessionId?: string, currentFile?: string): string | undefined {
  try {
    const files = readdirSync(sessionsDir);
    const fileSet = new Set(files);

    // If we have a reset file reference, find the original
    if (currentFile) {
      const base = path.basename(currentFile);
      const resetIdx = base.indexOf('.reset.');
      if (resetIdx !== -1) {
        const original = base.slice(0, resetIdx);
        if (fileSet.has(original)) return path.join(sessionsDir, original);
      }
    }

    // Try canonical session file
    if (sessionId) {
      const canonical = `${sessionId.trim()}.jsonl`;
      if (fileSet.has(canonical)) return path.join(sessionsDir, canonical);
    }

    // Fallback: latest non-reset JSONL
    const candidates = files
      .filter(f => f.endsWith('.jsonl') && !f.includes('.reset.'))
      .sort()
      .reverse();
    if (candidates.length > 0) return path.join(sessionsDir, candidates[0]);
  } catch {}
  return undefined;
}

function getRecentMessages(filePath: string, count = 15): string | null {
  try {
    const lines = readFileSync(filePath, 'utf-8').trim().split('\n');
    const messages: string[] = [];
    for (const line of lines) {
      try {
        const entry = JSON.parse(line);
        if (entry.type !== 'message' || !entry.message) continue;
        const { role, content } = entry.message;
        if (role !== 'user' && role !== 'assistant') continue;
        const text = Array.isArray(content)
          ? content.find((c: any) => c.type === 'text')?.text
          : content;
        if (text && !text.startsWith('/')) messages.push(`${role}: ${text}`);
      } catch {}
    }
    return messages.slice(-count).join('\n') || null;
  } catch { return null; }
}

function getRecentMessagesWithResetFallback(filePath: string, count = 15): string | null {
  const primary = getRecentMessages(filePath, count);
  if (primary) return primary;
  try {
    const dir = path.dirname(filePath);
    const prefix = `${path.basename(filePath)}.reset.`;
    const resets = readdirSync(dir).filter(f => f.startsWith(prefix)).sort();
    if (resets.length === 0) return primary;
    return getRecentMessages(path.join(dir, resets[resets.length - 1]), count) || primary;
  } catch { return primary; }
}

async function saveSessionContext(event: any, workspaceDir: string): Promise<void> {
  const context = event.context || {};
  const sessionEntry = context.previousSessionEntry || context.sessionEntry || {};
  const sessionId = sessionEntry.sessionId || 'unknown';
  const sessionKey = event.sessionKey || 'unknown';

  const memoryDir = path.join(workspaceDir, 'memory');
  mkdirSync(memoryDir, { recursive: true });

  const now = new Date(event.timestamp || Date.now());
  const dateStr = now.toISOString().split('T')[0];
  const timeStr = now.toISOString().split('T')[1].split('.')[0];

  // Find the session file for content extraction
  let sessionFile = sessionEntry.sessionFile || undefined;
  if (!sessionFile || sessionFile.includes('.reset.')) {
    const sessionsDir = sessionFile
      ? path.dirname(sessionFile)
      : path.join(workspaceDir, 'sessions');
    sessionFile = findSessionFile(sessionsDir, sessionId, sessionFile) || sessionFile;
  }

  // Get session content for the summary
  let sessionContent: string | null = null;
  if (sessionFile) {
    sessionContent = getRecentMessagesWithResetFallback(sessionFile, 15);
  }

  // Build the slug (simple timestamp-based — no LLM call to keep it fast)
  const slug = timeStr.replace(/:/g, '').slice(0, 4);
  const filename = `${dateStr}-${slug}.md`;

  const source = context.commandSource || 'unknown';
  const parts = [
    `# Session: ${dateStr} ${timeStr} UTC`,
    '',
    `- **Session Key**: ${sessionKey}`,
    `- **Session ID**: ${sessionId}`,
    `- **Source**: ${source}`,
    '',
  ];
  if (sessionContent) {
    parts.push('## Conversation Summary', '', sessionContent, '');
  }

  const filePath = path.join(memoryDir, filename);
  writeFileSync(filePath, parts.join('\n'), 'utf-8');
  log('info', `Session context saved to ${filePath.replace(os.homedir(), '~')}`);
}

// ── Memory extraction (spawn sage) ──────────────────────────────────────────

function resolveSessionFile(event: any, workspaceDir: string, instance: string): string | undefined {
  const ctx = event.context || {};
  const sessionEntry = ctx.previousSessionEntry || ctx.sessionEntry || {};

  // Try the direct session file from the event context
  const eventFile = sessionEntry.sessionFile;
  if (eventFile) {
    // Might be original path or already .reset.* — check both
    try {
      readFileSync(eventFile, { flag: 'r' });
      return eventFile;
    } catch {}
    // If renamed, find the reset version
    try {
      const dir = path.dirname(eventFile);
      const base = path.basename(eventFile);
      const resets = readdirSync(dir)
        .filter((f: string) => f.startsWith(`${base}.reset.`))
        .sort();
      if (resets.length > 0) return path.join(dir, resets[resets.length - 1]);
    } catch {}
  }

  // Fallback: find by session ID
  const sessionId = sessionEntry.sessionId;
  if (sessionId) {
    const agentDir = instance === 'main'
      ? path.join(os.homedir(), '.openclaw/agents/main/sessions')
      : path.join(os.homedir(), `.openclaw/agents/${instance}/sessions`);
    const canonical = path.join(agentDir, `${sessionId}.jsonl`);
    try { readFileSync(canonical, { flag: 'r' }); return canonical; } catch {}
    // Check for reset version
    try {
      const resets = readdirSync(agentDir)
        .filter((f: string) => f.startsWith(`${sessionId}.jsonl.reset.`))
        .sort();
      if (resets.length > 0) return path.join(agentDir, resets[resets.length - 1]);
    } catch {}
  }

  return undefined;
}

function spawnMemoryExtraction(event: any, workspaceDir: string, instance: string): void {
  const timestamp = Date.now();

  // Resolve session file from event context (avoids race with .reset.* rename)
  const sessionFile = resolveSessionFile(event, workspaceDir, instance);
  const sessionFileArgs = sessionFile ? ` --session-file "${sessionFile}"` : '';

  // Step 1: Run the bash parser (deterministic, fast, zero tokens)
  let result: string;
  try {
    result = execSync(
      `bash scripts/extract_session_memory.sh --instance ${instance}${sessionFileArgs}`,
      {
        cwd: workspaceDir,
        timeout: 30_000,
        encoding: 'utf-8',
        env: { ...process.env, WORKSPACE: workspaceDir },
      }
    ).trim();
  } catch (err: any) {
    log('error', 'Extraction script failed', {
      message: err?.message?.slice(0, 500),
      stderr: err?.stderr?.slice(0, 500),
      status: err?.status,
    });
    return;
  }

  if (!result) {
    log('warn', 'Extraction script returned empty');
    return;
  }

  // Step 2: Parse PROMPT_FILE
  const promptMatch = result.match(/PROMPT_FILE=(.+)/);
  if (!promptMatch) {
    log('warn', 'No PROMPT_FILE in output', { output: result.slice(0, 300) });
    return;
  }

  const promptFile = promptMatch[1].trim();
  let promptContent: string;
  try {
    promptContent = readFileSync(promptFile, 'utf-8');
  } catch (err: any) {
    log('error', 'Failed to read prompt file', { promptFile, message: err?.message });
    return;
  }

  log('info', `Prompt loaded (${promptContent.length} bytes), spawning sage`);

  // Step 3: Spawn sage as detached background process
  const sessionId = `mem-extract-${timestamp}`;
  try {
    const child = spawn(
      'openclaw',
      ['agent', '--agent', 'sage', '--session-id', sessionId, '--message', promptContent],
      {
        detached: true,
        stdio: 'ignore',
        cwd: workspaceDir,
        env: { ...process.env, WORKSPACE: workspaceDir },
      }
    );
    child.on('error', (err) => {
      log('error', 'Sage spawn error event', { message: err?.message });
    });
    child.unref();
    log('info', 'Sage spawned', { sessionId, pid: child.pid });
  } catch (err: any) {
    log('error', 'Failed to spawn sage', { message: err?.message });
  }
}

// ── Main handler ────────────────────────────────────────────────────────────

export default async (event: any) => {
  // Fire on command (new/reset) — same trigger as bundled session-memory
  if (event?.type !== 'command') return;
  if (event.action !== 'new' && event.action !== 'reset') return;

  const ctx = event.context || {};
  const workspaceDir = ctx.workspaceDir;
  if (!workspaceDir) {
    log('warn', 'No workspaceDir in context');
    return;
  }

  const instance = ctx.agentId || 'main';
  log('info', `Hook fired: ${event.action}`, { instance, workspaceDir });

  // Step 1: Save session context (what bundled session-memory does)
  try {
    await saveSessionContext(event, workspaceDir);
  } catch (err: any) {
    log('error', 'Failed to save session context', { message: err?.message, stack: err?.stack?.slice(0, 500) });
    // Continue to extraction even if save fails
  }

  // Step 2: Extract memories via sage (fire-and-forget)
  try {
    spawnMemoryExtraction(event, workspaceDir, instance);
  } catch (err: any) {
    log('error', 'Failed to spawn extraction', { message: err?.message, stack: err?.stack?.slice(0, 500) });
  }
};
