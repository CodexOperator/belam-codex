import { execSync } from 'child_process';
import { readFileSync } from 'fs';
import { spawn } from 'child_process';

export default async (event: any) => {
  if (event?.type !== 'agent:bootstrap') return;

  const ctx = event.context;
  if (!ctx?.workspaceDir) return;

  const instance = ctx.agentId || 'main';
  const timestamp = Date.now();

  try {
    // Run the bash parser — deterministic, fast, zero tokens
    // Returns file paths via stdout lines like PROMPT_FILE=...
    const result = execSync(
      `bash scripts/extract_session_memory.sh --instance ${instance}`,
      {
        cwd: ctx.workspaceDir,
        timeout: 15_000,
        encoding: 'utf-8',
        env: {
          ...process.env,
          WORKSPACE: ctx.workspaceDir,
        },
      }
    ).trim();

    if (!result) return;

    // Parse PROMPT_FILE from output
    const promptMatch = result.match(/PROMPT_FILE=(.+)/);
    if (!promptMatch) return;

    const promptFile = promptMatch[1].trim();
    const promptContent = readFileSync(promptFile, 'utf-8');

    // Spawn sage agent as detached background process (fire-and-forget)
    // Sage is NOT the main agent — no session lock contention
    const sessionId = `mem-extract-${timestamp}`;
    const child = spawn(
      'openclaw',
      ['agent', '--agent', 'sage', '--session-id', sessionId, '--message', promptContent],
      {
        detached: true,
        stdio: 'ignore',
        cwd: ctx.workspaceDir,
        env: {
          ...process.env,
          WORKSPACE: ctx.workspaceDir,
        },
      }
    );
    child.unref();

  } catch {
    // Non-fatal — session starts clean regardless
  }
};
