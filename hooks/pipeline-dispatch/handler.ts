import { execSync } from 'child_process';
import { existsSync, readFileSync, writeFileSync, readdirSync } from 'fs';
import { join } from 'path';
import { spawn } from 'child_process';

/**
 * Pipeline Dispatch Hook — agent:end handler.
 *
 * When an agent session ends, checks for pending pipeline dispatches
 * in state JSON files. Handles two cases:
 *
 * 1. NORMAL COMPLETION: agent completed its stage → dispatch next agent
 *    (dispatch_claimed prevents double-fire with fire_and_forget_dispatch)
 *
 * 2. TIMEOUT/FAILURE: agent ended without completing → retry same agent
 *    with sage-generated lessons from the failed session.
 *    Max 3 retries before marking pipeline as stalled.
 *
 * State JSON fields used:
 *   pending_action   — the stage being worked on
 *   current_agent    — which agent is assigned
 *   dispatch_claimed — set by fire_and_forget_dispatch or this hook
 *   retry_count      — number of timeout retries (0-3)
 *   last_error       — description of why last attempt failed
 */

const MAX_RETRIES = 3;

export default async (event: any) => {
  if (event?.type !== 'agent:end') return;

  const ctx = event.context;
  const workspaceDir = ctx?.workspaceDir;
  if (!workspaceDir) return;

  const buildsDir = join(workspaceDir, 'pipeline_builds');
  if (!existsSync(buildsDir)) return;

  // Get session end metadata
  const endReason = ctx?.endReason || 'unknown';  // 'completed', 'timeout', 'error'
  const agentId = ctx?.agentId || '';
  const sessionId = ctx?.sessionId || '';

  const stateFiles = readdirSync(buildsDir).filter(f => f.endsWith('_state.json'));

  for (const stateFile of stateFiles) {
    const statePath = join(buildsDir, stateFile);
    let state: any;

    try {
      state = JSON.parse(readFileSync(statePath, 'utf-8'));
    } catch {
      continue;
    }

    if (!state.pending_action || state.pending_action === 'none') continue;

    const agent = state.current_agent;
    const stage = state.pending_action;
    const pipeline = stateFile.replace('_state.json', '');
    const retryCount = state.retry_count || 0;

    // ── Case 1: Normal completion (dispatch_claimed by fire_and_forget) ──
    // The completing agent already called pipeline_orchestrate.py complete,
    // which called fire_and_forget_dispatch for the NEXT agent.
    // dispatch_claimed=true means it's already handled.
    if (state.dispatch_claimed) continue;

    // ── Case 2: Agent matches current_agent and ended ──
    // This means the agent ended WITHOUT completing the stage.
    // Could be timeout, error, or crash.
    if (agent !== agentId) continue;

    // Check retry limit
    if (retryCount >= MAX_RETRIES) {
      console.log(`[pipeline-dispatch] ❌ ${pipeline}/${stage}: ${agent} failed ${MAX_RETRIES} times — marking stalled`);

      // Mark pipeline as stalled
      state.stalled = true;
      state.stalled_at = new Date().toISOString();
      state.stalled_reason = `Agent ${agent} timed out/failed ${MAX_RETRIES} times on stage ${stage}`;
      writeFileSync(statePath, JSON.stringify(state, null, 2));

      // Update pipeline primitive status
      try {
        execSync(
          `python3 scripts/pipeline_update.py ${pipeline} update ${stage} --agent ${agent} --notes "STALLED: ${agent} failed ${MAX_RETRIES} times"`,
          { cwd: workspaceDir, timeout: 15000, stdio: 'pipe' }
        );
      } catch {}

      // Notify group
      try {
        execSync(
          `python3 scripts/pipeline_update.py ${pipeline} notify "⚠️ Pipeline STALLED: ${agent} failed ${MAX_RETRIES} times on ${stage}. Manual intervention needed."`,
          { cwd: workspaceDir, timeout: 10000, stdio: 'pipe' }
        );
      } catch {}

      continue;
    }

    // ── Timeout retry: sage analysis → retry same agent ──
    console.log(`[pipeline-dispatch] 🔄 ${pipeline}/${stage}: ${agent} ended (${endReason}), retry ${retryCount + 1}/${MAX_RETRIES}`);

    // Update state for retry
    state.retry_count = retryCount + 1;
    state.last_retry_at = new Date().toISOString();
    state.last_error = endReason;
    state.dispatch_claimed = false;
    writeFileSync(statePath, JSON.stringify(state, null, 2));

    // Gather basic context (non-blocking)
    let partialArtifacts = '';
    try {
      partialArtifacts = readdirSync(buildsDir)
        .filter(f => f.startsWith(pipeline) && !f.endsWith('_state.json'))
        .join(', ');
    } catch {}

    // Sage lessons file path — sage writes here, retry agent reads it
    const lessonsFile = join(buildsDir, `${pipeline}_retry_lessons.md`);

    // Fire-and-forget sage to analyze the failure and write lessons
    const sageTask = [
      `Analyze why agent ${agent} failed/timed out on pipeline ${pipeline}, stage ${stage}.`,
      `End reason: ${endReason}. Retry attempt: ${retryCount + 1}/${MAX_RETRIES}.`,
      `Partial artifacts: ${partialArtifacts || 'none found'}.`,
      ``,
      `Check these for context:`,
      `- ${buildsDir}/${pipeline}_* (partial build artifacts)`,
      `- memory/entries/ (recent logs from ${agent})`,
      ``,
      `Write your analysis to: ${lessonsFile}`,
      `Format: 3-5 bullet points covering:`,
      `1. What was accomplished before failure`,
      `2. What remained to be done`,
      `3. Why it likely failed (timeout? complexity? missing context?)`,
      `4. Specific advice for the retry attempt`,
      `Keep it concise — under 500 chars total.`,
    ].join('\n');

    try {
      const sageChild = spawn('openclaw', ['agent', '--agent', 'sage', '--message', sageTask], {
        detached: true,
        stdio: 'ignore',
        cwd: workspaceDir,
      });
      sageChild.unref();
      console.log(`[pipeline-dispatch] 🦉 Sage analyzing failure (pid=${sageChild.pid})`);
    } catch (err: any) {
      console.log(`[pipeline-dispatch] ⚠️ Sage dispatch failed: ${err.message}`);
    }

    // Small delay to let sage start (but don't block on completion)
    await new Promise(resolve => setTimeout(resolve, 3000));

    // Build retry message — agent checks for sage lessons file
    const retryMsg = [
      `Pipeline RETRY dispatch: ${pipeline} / ${stage} (attempt ${retryCount + 2}/${MAX_RETRIES + 1})`,
      ``,
      `Your task is stage \`${stage}\` for pipeline \`${pipeline}\`.`,
      ``,
      `⚠️ PREVIOUS ATTEMPT FAILED (${endReason}).`,
      ``,
      `Before starting, check for sage analysis: ${lessonsFile}`,
      `If it exists, read the lessons and apply them. If not, sage may still be writing — proceed with caution.`,
      ``,
      `Partial artifacts: ${partialArtifacts || 'none'}`,
      `Check pipeline_builds/ for partial work — resume from where the previous attempt left off.`,
      `Do NOT start from scratch if partial artifacts exist.`,
      ``,
      `When complete: python3 scripts/pipeline_orchestrate.py ${pipeline} complete ${stage} --agent ${agent} --notes "your summary"`,
    ].join('\n');

    // Fire and forget retry dispatch
    try {
      const child = spawn('openclaw', ['agent', '--agent', agent, '--message', retryMsg], {
        detached: true,
        stdio: 'ignore',
        cwd: workspaceDir,
      });
      child.unref();

      console.log(`[pipeline-dispatch] 🔔 Retried ${agent} for ${pipeline}/${stage} (attempt ${retryCount + 2}, pid=${child.pid})`);
    } catch (err: any) {
      console.error(`[pipeline-dispatch] ❌ Retry dispatch failed: ${err.message}`);
    }
  }
};
