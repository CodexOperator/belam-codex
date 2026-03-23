import { execSync } from 'child_process';
import { existsSync, readFileSync, writeFileSync, readdirSync } from 'fs';
import { join } from 'path';

/**
 * Pipeline Dispatch Hook — agent:end handler.
 *
 * When an agent session ends, checks for pending pipeline dispatches
 * in the state JSON files. If a dispatch is pending (written by
 * pipeline_orchestrate.py complete), spawns the next agent natively.
 *
 * State JSON format (written by orchestration_engine.py):
 * {
 *   "pending_action": "critic_code_review",
 *   "current_agent": "critic",
 *   "last_dispatched": "2026-03-23T05:11:00+00:00",
 *   "dispatch_claimed": false
 * }
 *
 * The hook sets dispatch_claimed=true to prevent double-dispatch.
 */

export default async (event: any) => {
  if (event?.type !== 'agent:end') return;

  const ctx = event.context;
  const workspaceDir = ctx?.workspaceDir;
  if (!workspaceDir) return;

  // Research builds dir where state JSONs live
  const buildsDir = join(workspaceDir, 'machinelearning', 'snn_applied_finance',
                         'research', 'pipeline_builds');
  if (!existsSync(buildsDir)) return;

  // Scan for state JSON files with pending dispatches
  const stateFiles = readdirSync(buildsDir).filter(f => f.endsWith('_state.json'));

  for (const stateFile of stateFiles) {
    const statePath = join(buildsDir, stateFile);
    let state: any;

    try {
      state = JSON.parse(readFileSync(statePath, 'utf-8'));
    } catch {
      continue;
    }

    // Skip if no pending action or already claimed
    if (!state.pending_action || state.pending_action === 'none') continue;
    if (state.dispatch_claimed) continue;

    const agent = state.current_agent;
    const stage = state.pending_action;
    const pipeline = stateFile.replace('_state.json', '');

    // Claim this dispatch (prevent double-fire)
    state.dispatch_claimed = true;
    state.dispatch_claimed_at = new Date().toISOString();
    writeFileSync(statePath, JSON.stringify(state, null, 2));

    // Build the handoff message
    const handoffMsg = `Pipeline dispatch: ${pipeline} / ${stage}\n` +
      `Your task is stage \`${stage}\` for pipeline \`${pipeline}\`.\n` +
      `Read the pipeline state and your role context, then complete the stage.\n` +
      `State file: ${statePath}`;

    // Dispatch via openclaw agent CLI (fire-and-forget from hook context)
    try {
      // Use spawn to avoid blocking the hook
      const { spawn } = require('child_process');
      const child = spawn('openclaw', ['agent', '--agent', agent, '--message', handoffMsg], {
        detached: true,
        stdio: 'ignore',
        cwd: workspaceDir,
      });
      child.unref();

      console.log(`[pipeline-dispatch] 🔔 Dispatched ${agent} for ${pipeline}/${stage} (pid=${child.pid})`);
    } catch (err: any) {
      console.error(`[pipeline-dispatch] ❌ Failed to dispatch ${agent}: ${err.message}`);
      // Unclaim so retry can happen
      state.dispatch_claimed = false;
      writeFileSync(statePath, JSON.stringify(state, null, 2));
    }
  }
};
