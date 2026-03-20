import { execSync } from 'child_process';

export default async (event: any) => {
  if (event?.type !== 'agent:bootstrap') return;

  const ctx = event.context;
  if (!ctx?.workspaceDir) return;

  const instance = ctx.agentId || 'main';

  try {
    // Run the bash parser — deterministic, fast, zero tokens
    // This creates a parsed transcript + extraction prompt + marker file
    // The agent picks up the marker on boot and spawns the subagent
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

    // Parse output
    const promptMatch = result.match(/PROMPT_FILE=(.+)/);
    const transcriptMatch = result.match(/TRANSCRIPT_FILE=(.+)/);
    const sessionMatch = result.match(/SESSION_ID=(.+)/);
    const exchangeMatch = result.match(/EXCHANGE_COUNT=(\d+)/);

    if (!promptMatch || !sessionMatch) return;

    // Write a pending extraction marker that the agent reads on boot
    const markerContent = JSON.stringify({
      instance,
      sessionId: sessionMatch[1],
      promptFile: promptMatch[1],
      transcriptFile: transcriptMatch?.[1] || '',
      exchangeCount: parseInt(exchangeMatch?.[1] || '0'),
      createdAt: new Date().toISOString(),
    });

    const fs = await import('fs');
    fs.writeFileSync(
      `${ctx.workspaceDir}/memory/pending_extraction.json`,
      markerContent
    );

  } catch {
    // Non-fatal — session starts clean regardless
  }
};
