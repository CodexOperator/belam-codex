import { execSync } from 'child_process';

export default async (event: any) => {
  if (event?.type !== 'agent:bootstrap') return;

  const ctx = event.context;
  if (!ctx?.workspaceDir) return;

  try {
    const output = execSync('python3 scripts/codex_engine.py --supermap', {
      cwd: ctx.workspaceDir,
      timeout: 10_000,
      encoding: 'utf-8',
    }).trim();

    if (!output) return;

    // Inject as first bootstrap file — hits encoder before everything else
    ctx.bootstrapFiles = ctx.bootstrapFiles || [];
    ctx.bootstrapFiles.unshift({
      name: 'CODEX.codex',
      path: `${ctx.workspaceDir}/CODEX.codex`,
      content: output,
      missing: false,
    });
  } catch {
    // Non-fatal
  }
};
