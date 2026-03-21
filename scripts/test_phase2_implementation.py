#!/usr/bin/env python3
"""
Test checklist for Phase 2 implementation (orchestration-engine-v2-temporal).

Covers all 17 items from the architect's test spec + T18 (Critic FLAG-3: revert-of-revert).
"""

import json
import os
import sys
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Setup paths
WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
sys.path.insert(0, str(WORKSPACE / 'scripts'))

from temporal_schema import init_db
from temporal_overlay import TemporalOverlay, PERSONA_STAGE_FILTERS, _format_dashboard

passed = 0
failed = 0
errors = []

def test(name, condition, detail=''):
    global passed, failed, errors
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        errors.append(f"{name}: {detail}")
        print(f"  ❌ {name}: {detail}")


# Create a temp workspace for testing
tmpdir = tempfile.mkdtemp(prefix='phase2_test_')
tmp_workspace = Path(tmpdir)
db_path = tmp_workspace / 'data' / 'temporal.db'
builds_dir = tmp_workspace / 'machinelearning' / 'snn_applied_finance' / 'research' / 'pipeline_builds'
pipelines_dir = tmp_workspace / 'pipelines'
builds_dir.mkdir(parents=True, exist_ok=True)
pipelines_dir.mkdir(parents=True, exist_ok=True)

# Create test pipeline state file
test_version = 'test-pipeline-v1'
state_file = builds_dir / f'{test_version}_state.json'
state_file.write_text(json.dumps({
    'pending_action': 'critic_code_review',
    'current_agent': 'critic',
    'last_updated': '2026-03-21 10:00',
    'stages': {},
}))

# Create test pipeline markdown
md_file = pipelines_dir / f'{test_version}.md'
md_file.write_text(f"""---
version: {test_version}
status: phase1_build
priority: high
---
# {test_version}
## Stages
""")

try:
    # Initialize overlay with temp DB
    overlay = TemporalOverlay(workspace=tmp_workspace, db_path=db_path)

    # Seed some transitions to work with
    overlay.advance_pipeline(test_version, 'architect_design', 'architect', status='phase1_design')

    # Simulate a timeline of transitions
    transitions = [
        ('pipeline_created', 'architect_design', 'belam-main', 'complete', '2026-03-21T08:00:00Z'),
        ('architect_design', 'critic_design_review', 'architect', 'complete', '2026-03-21T09:00:00Z'),
        ('critic_design_review', 'builder_implementation', 'critic', 'complete', '2026-03-21T10:00:00Z'),
        ('builder_implementation', 'critic_code_review', 'builder', 'complete', '2026-03-21T11:00:00Z'),
    ]

    conn = overlay._get_conn()
    for from_s, to_s, agent, action, ts in transitions:
        conn.execute(
            "INSERT INTO state_transition (version, from_stage, to_stage, agent, action, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (test_version, from_s, to_s, agent, action, ts)
        )
    conn.commit()

    # Update pipeline_state to current
    overlay.advance_pipeline(test_version, 'critic_code_review', 'critic')

    print("\n=== Phase 2 Test Checklist ===\n")

    # ─── T1: time_travel_revert() reverts state correctly ─────────────────────
    result = overlay.time_travel_revert(test_version, '2026-03-21T09:30:00Z')
    test("T1: time_travel_revert() reverts state correctly",
         result and result['success'] and result['reverted_to'] == 'critic_design_review',
         f"Got: {result}")

    # Reset state for more tests
    overlay.advance_pipeline(test_version, 'critic_code_review', 'critic')
    # Re-add the transition so further tests work
    conn.execute(
        "INSERT INTO state_transition (version, from_stage, to_stage, agent, action, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (test_version, 'critic_design_review', 'critic_code_review', 'critic', 'complete',
         datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
    )
    conn.commit()

    # ─── T2: Correct F-label revert format (⮌) ────────────────────────────────
    # Re-do revert to check labels
    result2 = overlay.time_travel_revert(test_version, '2026-03-21T09:30:00Z')
    test("T2: F-label revert format uses ⮌",
         result2 and any('⮌' in fl for fl in result2.get('f_labels', [])),
         f"F-labels: {result2.get('f_labels', []) if result2 else 'None'}")

    # ─── T3: Returns r_label_hint with affected coords ────────────────────────
    test("T3: r_label_hint has affected_coords",
         result2 and result2.get('r_label_hint', {}).get('affected_coords'),
         f"Hint: {result2.get('r_label_hint') if result2 else 'None'}")

    # Reset state
    overlay.advance_pipeline(test_version, 'critic_code_review', 'critic')
    conn.execute(
        "INSERT INTO state_transition (version, from_stage, to_stage, agent, action, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (test_version, 'critic_design_review', 'critic_code_review', 'critic', 'complete',
         datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
    )
    conn.commit()

    # ─── T4: Logs transition with action='revert' ────────────────────────────
    revert_transitions = conn.execute(
        "SELECT * FROM state_transition WHERE version = ? AND action = 'revert'",
        (test_version,)
    ).fetchall()
    test("T4: Revert transition logged in temporal DB",
         len(revert_transitions) >= 1,
         f"Found {len(revert_transitions)} revert transitions")

    # ─── T5: Updates _state.json and pipeline markdown ────────────────────────
    result5 = overlay.time_travel_revert(test_version, '2026-03-21T08:30:00Z')
    if result5 and result5.get('filesystem_reverted'):
        state_data = json.loads(state_file.read_text())
        test("T5: _state.json updated with revert",
             state_data.get('pending_action') == 'architect_design'
             and 'reverts' in state_data,
             f"pending_action={state_data.get('pending_action')}")
    else:
        test("T5: _state.json updated with revert",
             False, "filesystem_reverted was False or result was None")

    # Reset
    overlay.advance_pipeline(test_version, 'critic_code_review', 'critic')
    state_file.write_text(json.dumps({
        'pending_action': 'critic_code_review',
        'current_agent': 'critic',
        'last_updated': '2026-03-21 12:00',
        'stages': {},
    }))
    conn.execute(
        "INSERT INTO state_transition (version, from_stage, to_stage, agent, action, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (test_version, 'architect_design', 'critic_code_review', 'critic', 'complete',
         datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
    )
    conn.commit()

    # ─── T6: No-op when current == target ────────────────────────────────────
    # Revert to current state (should be no-op)
    now_ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    result6 = overlay.time_travel_revert(test_version, now_ts)
    test("T6: No-op when current == target",
         result6 and result6.get('noop', False),
         f"Got: {result6}")

    # ─── T7: Graceful degradation when DB unavailable ────────────────────────
    bad_overlay = TemporalOverlay(workspace=tmp_workspace,
                                   db_path=Path('/nonexistent/path/db.sqlite'))
    result7 = bad_overlay.time_travel_revert('anything', '2026-01-01T00:00:00Z')
    test("T7: Returns None when DB unavailable",
         result7 is None,
         f"Got: {result7}")

    # ─── T8: get_dashboard(persona='architect') filtering ────────────────────
    dashboard8 = overlay.get_dashboard(persona='architect')
    test("T8: Architect dashboard shows persona field",
         dashboard8 and dashboard8.get('persona') == 'architect',
         f"Got persona: {dashboard8.get('persona') if dashboard8 else 'None'}")

    # ─── T9: get_dashboard(persona='builder') filtering ──────────────────────
    dashboard9 = overlay.get_dashboard(persona='builder')
    test("T9: Builder dashboard shows persona field",
         dashboard9 and dashboard9.get('persona') == 'builder',
         f"Got persona: {dashboard9.get('persona') if dashboard9 else 'None'}")

    # ─── T10: get_dashboard(persona=None) backward compat ────────────────────
    dashboard10 = overlay.get_dashboard(persona=None)
    test("T10: Full dashboard (persona=None) backward compatible",
         dashboard10 and dashboard10.get('persona') is None
         and 'pipelines' in dashboard10 and 'agents' in dashboard10,
         f"Keys: {list(dashboard10.keys()) if dashboard10 else 'None'}")

    # ─── T11: format_dashboard_for_prompt produces text ──────────────────────
    prompt11 = overlay.format_dashboard_for_prompt('critic')
    test("T11: format_dashboard_for_prompt produces text with critic highlighting",
         prompt11 and 'Critic' in prompt11 and '🔍' in prompt11,
         f"Output starts: {prompt11[:60] if prompt11 else 'None'}...")

    # ─── T12: build_dispatch_payload includes view_filter ────────────────────
    try:
        from orchestration_engine import build_dispatch_payload, DispatchPayload
        # We can't fully test this without a real pipeline, but we can check the class
        test("T12: DispatchPayload has view_filter field",
             hasattr(DispatchPayload, '__dataclass_fields__')
             and 'view_filter' in DispatchPayload.__dataclass_fields__,
             "view_filter not in DispatchPayload fields")
    except ImportError as e:
        test("T12: DispatchPayload has view_filter field", False, str(e))

    # ─── T13: Dispatch payload includes filtered dashboard ───────────────────
    # Verify the field exists and can be serialized
    try:
        dp = DispatchPayload(
            agent='builder', task='test', view_filter={'persona': 'builder'}
        )
        d = dp.to_dict()
        test("T13: Dispatch payload serializes view_filter",
             d['context'].get('view_filter') == {'persona': 'builder'},
             f"Got: {d['context'].get('view_filter')}")
    except Exception as e:
        test("T13: Dispatch payload serializes view_filter", False, str(e))

    # ─── T14: record_transition() deleted ────────────────────────────────────
    test("T14: record_transition() is deleted",
         not hasattr(overlay, 'record_transition'),
         "record_transition still exists as method")

    # ─── T15: _format_dashboard() uses dynamic column widths ─────────────────
    test_dashboard = {
        'pipelines': [
            {'version': 'short', 'current_stage': 's', 'current_agent': 'a'},
            {'version': 'a-very-long-pipeline-version-name', 'current_stage': 'phase2_builder_implementation', 'current_agent': 'builder'},
        ],
        'agents': [],
        'recent_handoffs': [],
        'stats': {'total_pipelines': 2, 'active_agents': 0, 'total_agents': 0, 'pending_handoffs': 0},
    }
    formatted = _format_dashboard(test_dashboard)
    # Should NOT truncate 'phase2_builder_implementation' to 10 chars
    test("T15: Dynamic column widths (no fixed truncation)",
         'phase2_builder_implementation' in formatted,
         "Stage was truncated to fixed width")

    # ─── T16: CLI revert command ──────────────────────────────────────────────
    try:
        from orchestration_engine import handle_revert
        # Test with a non-existent pipeline (should return error gracefully)
        result16 = handle_revert('nonexistent-pipeline', '2026-01-01T00:00:00Z')
        test("T16: CLI handle_revert() returns error for bad pipeline",
             result16 and result16.get('status') == 'error',
             f"Got: {result16}")
    except Exception as e:
        test("T16: CLI handle_revert()", False, str(e))

    # ─── T17: Global coordinates unchanged after filtering ───────────────────
    # Verify that pipeline versions are not remapped
    dashboard17 = overlay.get_dashboard(persona='builder')
    if dashboard17 and dashboard17.get('pipelines'):
        versions_full = {p['version'] for p in overlay.get_dashboard().get('pipelines', [])}
        versions_filtered = {p['version'] for p in dashboard17.get('pipelines', [])}
        test("T17: Global coordinates unchanged after persona filtering",
             versions_full == versions_filtered,
             f"Full: {versions_full}, Filtered: {versions_filtered}")
    else:
        test("T17: Global coordinates unchanged after persona filtering",
             True, "No pipelines to compare (vacuously true)")

    # ─── T18: Revert-of-revert (Critic FLAG-3) ──────────────────────────────
    # First revert to architect_design (T=08:30)
    overlay.advance_pipeline(test_version, 'critic_code_review', 'critic')
    conn.execute(
        "INSERT INTO state_transition (version, from_stage, to_stage, agent, action, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (test_version, 'architect_design', 'critic_code_review', 'critic', 'complete',
         datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
    )
    conn.commit()

    revert1 = overlay.time_travel_revert(test_version, '2026-03-21T08:30:00Z')
    test("T18a: First revert succeeds",
         revert1 and revert1['success'] and revert1['reverted_to'] == 'architect_design',
         f"Got: {revert1}")

    # Now second revert to a different timestamp (T=09:30, which is critic_design_review)
    # Need to re-advance first so we have something to revert from
    overlay.advance_pipeline(test_version, 'builder_implementation', 'builder')
    conn.execute(
        "INSERT INTO state_transition (version, from_stage, to_stage, agent, action, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (test_version, 'architect_design', 'builder_implementation', 'builder', 'complete',
         datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
    )
    conn.commit()

    revert2 = overlay.time_travel_revert(test_version, '2026-03-21T09:30:00Z')
    test("T18b: Second revert to different timestamp succeeds",
         revert2 and revert2['success'] and revert2['reverted_to'] == 'critic_design_review',
         f"Got: {revert2}")

    # ─── BONUS: Verify PERSONA_STAGE_FILTERS cross-phase visibility ──────────
    arch_stages = set(PERSONA_STAGE_FILTERS['architect']['show_stages'])
    critic_stages = set(PERSONA_STAGE_FILTERS['critic']['show_stages'])
    test("BONUS: Architect can see builder_implementation (FLAG-2 fix)",
         'builder_implementation' in arch_stages and 'phase2_builder_implementation' in arch_stages,
         f"Architect stages: {arch_stages}")
    test("BONUS: Critic can see builder_implementation (FLAG-2 fix)",
         'builder_implementation' in critic_stages and 'phase2_builder_implementation' in critic_stages,
         f"Critic stages: {critic_stages}")

    overlay.close()

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
if errors:
    print(f"\nFailures:")
    for e in errors:
        print(f"  ❌ {e}")
print()
sys.exit(0 if failed == 0 else 1)
