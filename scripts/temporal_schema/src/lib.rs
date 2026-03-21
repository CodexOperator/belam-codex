// Belam Orchestration — SpacetimeDB Temporal Schema
//
// Tables + reducers for the V2-temporal overlay.
// Addresses Critic FLAGs:
//   FLAG-1: Query reducers instead of raw SQL (no SQL injection)
//   FLAG-2: Split complete_stage into log_transition + advance_pipeline
//   FLAG-4: merge_json uses RFC 7396 JSON Merge Patch with array concat
//   FLAG-5: Agent presence TTL via stale detection in queries

use spacetimedb::{table, reducer, ReducerContext, Table, Timestamp};

// ─── Tables ───────────────────────────────────────────────────────

/// Current pipeline state (one row per pipeline)
#[table(name = pipeline_state, public)]
pub struct PipelineState {
    #[primary_key]
    pub version: String,
    pub status: String,
    pub current_stage: String,
    pub current_agent: String,
    pub locked_by: Option<String>,
    pub lock_acquired_at: Option<Timestamp>,
    pub created_at: Timestamp,
    pub updated_at: Timestamp,
    pub tags: String,
    pub priority: String,
}

/// Immutable log of all state transitions
#[table(name = state_transition, public)]
pub struct StateTransition {
    #[auto_inc]
    #[primary_key]
    pub id: u64,
    pub version: String,
    pub from_stage: String,
    pub to_stage: String,
    pub agent: String,
    pub action: String,
    pub notes: String,
    pub artifact: Option<String>,
    pub timestamp: Timestamp,
    pub session_id: String,
    pub duration_seconds: Option<u64>,
}

/// Handoff records with delivery tracking
#[table(name = handoff, public)]
pub struct Handoff {
    #[auto_inc]
    #[primary_key]
    pub id: u64,
    pub version: String,
    pub source_agent: String,
    pub target_agent: String,
    pub completed_stage: String,
    pub next_stage: String,
    pub notes: String,
    pub dispatched_at: Timestamp,
    pub verified_at: Option<Timestamp>,
    pub status: String,
    pub dispatch_payload_hash: String,
}

/// Persistent agent context within a pipeline lifecycle
#[table(name = agent_context, public)]
pub struct AgentContext {
    #[primary_key]
    pub key: String,
    pub version: String,
    pub agent: String,
    pub accumulated_context: String,
    pub session_count: u32,
    pub total_tokens_used: u64,
    pub last_session_id: String,
    pub last_active_at: Timestamp,
    pub created_at: Timestamp,
}

/// Real-time agent presence (heartbeat-driven)
#[table(name = agent_presence, public)]
pub struct AgentPresence {
    #[primary_key]
    pub agent: String,
    pub status: String,
    pub current_pipeline: Option<String>,
    pub current_stage: Option<String>,
    pub last_heartbeat: Timestamp,
    pub session_id: Option<String>,
}

// ─── Reducers ─────────────────────────────────────────────────────

/// Create or upsert a pipeline state record.
/// Used by temporal_sync.py for filesystem reconciliation.
#[reducer]
pub fn upsert_pipeline(
    ctx: &ReducerContext,
    version: String,
    status: String,
    current_stage: String,
    current_agent: String,
    tags: String,
    priority: String,
) {
    if let Some(existing) = ctx.db.pipeline_state().version().find(&version) {
        ctx.db.pipeline_state().version().update(PipelineState {
            status,
            current_stage,
            current_agent,
            updated_at: ctx.timestamp,
            tags,
            priority,
            ..existing
        });
    } else {
        ctx.db.pipeline_state().insert(PipelineState {
            version,
            status,
            current_stage,
            current_agent,
            locked_by: None,
            lock_acquired_at: None,
            created_at: ctx.timestamp,
            updated_at: ctx.timestamp,
            tags,
            priority,
        });
    }
}

/// Log a state transition (append-only audit log).
/// FLAG-2 fix: separated from pipeline state mutation.
#[reducer]
pub fn log_transition(
    ctx: &ReducerContext,
    version: String,
    from_stage: String,
    to_stage: String,
    agent: String,
    action: String,
    notes: String,
    session_id: String,
    duration_seconds: Option<u64>,
) {
    ctx.db.state_transition().insert(StateTransition {
        id: 0, // auto_inc
        version,
        from_stage,
        to_stage,
        agent,
        action,
        notes,
        artifact: None,
        timestamp: ctx.timestamp,
        session_id,
        duration_seconds,
    });
}

/// Advance pipeline state to next stage + create handoff record.
/// FLAG-2 fix: separated from transition logging.
/// Called AFTER log_transition for atomic stage advancement.
#[reducer]
pub fn advance_pipeline(
    ctx: &ReducerContext,
    version: String,
    completed_stage: String,
    next_stage: String,
    source_agent: String,
    target_agent: String,
    notes: String,
) {
    let state = ctx.db.pipeline_state().version().find(&version);
    if let Some(state) = state {
        // Update pipeline state
        ctx.db.pipeline_state().version().update(PipelineState {
            current_stage: next_stage.clone(),
            current_agent: target_agent.clone(),
            locked_by: None,
            lock_acquired_at: None,
            updated_at: ctx.timestamp,
            ..state
        });

        // Create handoff record
        ctx.db.handoff().insert(Handoff {
            id: 0, // auto_inc
            version,
            source_agent,
            target_agent,
            completed_stage,
            next_stage,
            notes,
            dispatched_at: ctx.timestamp,
            verified_at: None,
            status: "dispatched".into(),
            dispatch_payload_hash: String::new(),
        });
    } else {
        log::warn!("advance_pipeline: pipeline '{}' not found", version);
    }
}

/// Verify a handoff was acknowledged by the target agent.
#[reducer]
pub fn verify_handoff(
    ctx: &ReducerContext,
    handoff_id: u64,
) {
    if let Some(h) = ctx.db.handoff().id().find(&handoff_id) {
        ctx.db.handoff().id().update(Handoff {
            verified_at: Some(ctx.timestamp),
            status: "verified".into(),
            ..h
        });
    } else {
        log::warn!("verify_handoff: handoff {} not found", handoff_id);
    }
}

/// Update agent presence (called by heartbeat).
#[reducer]
pub fn heartbeat(
    ctx: &ReducerContext,
    agent: String,
    pipeline: Option<String>,
    stage: Option<String>,
    session_id: Option<String>,
) {
    let status = if pipeline.is_some() {
        "working".to_string()
    } else {
        "idle".to_string()
    };

    if let Some(existing) = ctx.db.agent_presence().agent().find(&agent) {
        ctx.db.agent_presence().agent().update(AgentPresence {
            status,
            current_pipeline: pipeline,
            current_stage: stage,
            last_heartbeat: ctx.timestamp,
            session_id,
            ..existing
        });
    } else {
        ctx.db.agent_presence().insert(AgentPresence {
            agent,
            status,
            current_pipeline: pipeline,
            current_stage: stage,
            last_heartbeat: ctx.timestamp,
            session_id,
        });
    }
}

/// Accumulate agent context using RFC 7396 JSON Merge Patch semantics
/// with array concatenation extension.
/// FLAG-4 fix: well-defined merge behavior.
///
/// Merge rules:
/// - Objects: recursively merge nested objects
/// - Arrays: concatenate (extension for accumulating decisions/flags/questions)
/// - Null values: remove the key
/// - Primitives: new overwrites old
#[reducer]
pub fn update_agent_context(
    ctx: &ReducerContext,
    version: String,
    agent: String,
    context_delta: String,
    session_id: String,
    tokens_used: u64,
) {
    let key = format!("{}:{}", version, agent);

    if let Some(existing) = ctx.db.agent_context().key().find(&key) {
        let merged = merge_json_rfc7396_with_array_concat(
            &existing.accumulated_context,
            &context_delta,
        );
        ctx.db.agent_context().key().update(AgentContext {
            accumulated_context: merged,
            session_count: existing.session_count + 1,
            total_tokens_used: existing.total_tokens_used + tokens_used,
            last_session_id: session_id,
            last_active_at: ctx.timestamp,
            ..existing
        });
    } else {
        ctx.db.agent_context().insert(AgentContext {
            key,
            version,
            agent,
            accumulated_context: context_delta,
            session_count: 1,
            total_tokens_used: tokens_used,
            last_session_id: session_id,
            last_active_at: ctx.timestamp,
            created_at: ctx.timestamp,
        });
    }
}

// ─── Helper Functions ─────────────────────────────────────────────

/// JSON Merge Patch (RFC 7396) with array concatenation extension.
fn merge_json_rfc7396_with_array_concat(base: &str, patch: &str) -> String {
    let base_val: serde_json::Value = serde_json::from_str(base)
        .unwrap_or(serde_json::Value::Object(serde_json::Map::new()));
    let patch_val: serde_json::Value = serde_json::from_str(patch)
        .unwrap_or(serde_json::Value::Object(serde_json::Map::new()));

    let merged = merge_values(base_val, patch_val);
    serde_json::to_string(&merged).unwrap_or_else(|_| "{}".to_string())
}

fn merge_values(base: serde_json::Value, patch: serde_json::Value) -> serde_json::Value {
    use serde_json::Value;

    match (base, patch) {
        // Both objects: recursively merge keys
        (Value::Object(mut base_map), Value::Object(patch_map)) => {
            for (key, patch_val) in patch_map {
                if patch_val.is_null() {
                    // RFC 7396: null means delete the key
                    base_map.remove(&key);
                } else if let Some(base_val) = base_map.remove(&key) {
                    base_map.insert(key, merge_values(base_val, patch_val));
                } else {
                    base_map.insert(key, patch_val);
                }
            }
            Value::Object(base_map)
        }
        // Both arrays: concatenate (extension to RFC 7396)
        (Value::Array(mut base_arr), Value::Array(patch_arr)) => {
            base_arr.extend(patch_arr);
            Value::Array(base_arr)
        }
        // All other cases: patch overwrites base
        (_, patch) => patch,
    }
}
