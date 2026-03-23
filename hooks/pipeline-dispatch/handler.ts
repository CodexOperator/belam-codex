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

  const buildsDir = join(workspaceDir, 'machinelearning', 'snn_applied_finance',
                         'research', 'pipeline_builds');
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

    // ── Sage analysis of failed session ──
    console.log(`[pipeline-dispatch] 🔄 ${pipeline}/${stage}: ${agent} ended (${endReason}), retry ${retryCount + 1}/${MAX_RETRIES}`);

    let sageLessons = `Agent ${agent} ended with reason: ${endReason}. Retry ${retryCount + 1}/${MAX_RETRIES}.`;

    // Try to get sage to analyze the failed session
    try {
      const sagePrompt = `Analyze why agent ${agent} failed/timed out on pipeline ${pipeline}, stage ${stage}. ` +
        `Session ID: ${sessionId}. End reason: ${endReason}. ` +
        `Check the pipeline build artifacts in ${buildsDir} for partial work. ` +
        `Check memory/entries/ for any logs from this session. ` +
        `Summarize in 3-5 bullet points: what was accomplished, what remained, why it likely failed, and specific advice for the retry attempt. Keep it under 500 chars.`;

      sageLessons = execSync(
        `openclaw agent --agent sage --message ${JSON.stringify(sagePrompt)} --timeout 30`,
        { cwd: workspaceDir, timeout: 45000, encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }
      ).trim() || sageLessons;
    } catch {
      // Sage unavailable — use basic context
      console.log(`[pipeline-dispatch] ⚠️ Sage analysis unavailable, using basic retry context`);

      // Fallback: check for partial build artifacts
      try {
        const artifacts = readdirSync(buildsDir)
          .filter(f => f.startsWith(pipeline) && !f.endsWith('_state.json'))
          .join(', ');
        if (artifacts) {
          sageLessons += ` Partial artifacts found: ${artifacts}. Resume from where the previous attempt left off.`;
        }
      } catch {}
    }

    // ── Update state and retry ──
    state.retry_count = retryCount + 1;
    state.last_retry_at = new Date().toISOString();
    state.last_error = endReason;
    state.dispatch_claimed = false;  // Allow fire_and_forget to claim
    writeFileSync(statePath, JSON.stringify(state, null, 2));

    // Build retry message with lessons
    const retryMsg = `Pipeline RETRY dispatch: ${pipeline} / ${stage} (attempt ${retryCount + 2}/${MAX_RETRIES + 1})\n\n` +
      `Your task is stage \`${stage}\` for pipeline \`${pipeline}\`.\n\n` +
      `⚠️ PREVIOUS ATTEMPT FAILED (${endReason}). Lessons from last session:\n${sageLessons}\n\n` +
      `Check for partial work in pipeline_builds/ — resume from where the previous attempt left off.\n` +
      `Do NOT start from scratch if partial artifacts exist.\n\n` +
      `When complete: python3 scripts/pipeline_orchestrate.py ${pipeline} complete ${stage} --agent ${agent} --notes "your summary"`;

    // Fire and forget dispatch
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
