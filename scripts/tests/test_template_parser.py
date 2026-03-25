#!/usr/bin/env python3
"""Tests for phase-based template parser."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from template_parser import parse_template, clear_cache, resolve_stage_name, LEGACY_STAGE_MAP


def test_builder_first_parses():
    """Builder-first template parses without error."""
    clear_cache()
    result = parse_template('builder-first')
    assert result is not None, "builder-first template failed to parse"
    assert result['first_agent'] == 'builder'
    assert result['pipeline_fields']['type'] == 'builder-first'


def test_research_parses():
    """Research template parses without error."""
    clear_cache()
    result = parse_template('research')
    assert result is not None, "research template failed to parse"
    assert result['first_agent'] == 'architect'
    assert result['pipeline_fields']['type'] == 'research'


def test_builder_first_stage_names():
    """Builder-first template generates correct phase-based stage names."""
    clear_cache()
    result = parse_template('builder-first')
    stages = result['pipeline_fields']['stages']
    
    assert 'p1_builder_implement' in stages
    assert 'p1_builder_bugfix' in stages
    assert 'p1_critic_review' in stages
    assert 'p1_complete' in stages
    assert 'p2_architect_design' in stages
    assert 'p2_builder_implement' in stages
    assert 'p2_builder_bugfix' in stages
    assert 'p2_critic_review' in stages
    assert 'p2_complete' in stages


def test_research_stage_names():
    """Research template generates correct phase-based stage names."""
    clear_cache()
    result = parse_template('research')
    stages = result['pipeline_fields']['stages']
    
    assert 'p1_architect_design' in stages
    assert 'p1_critic_design_review' in stages
    assert 'p1_builder_implement' in stages
    assert 'p1_builder_verify' in stages
    assert 'p1_critic_code_review' in stages
    assert 'p1_complete' in stages
    assert 'p2_system_experiment_run' in stages
    assert 'p2_architect_analysis' in stages
    assert 'p2_complete' in stages
    assert 'p3_architect_design' in stages
    assert 'p3_complete' in stages
    assert 'p4_architect_design' in stages
    assert 'p4_complete' in stages


def test_pipeline_created_transition():
    """pipeline_created transitions to first stage of phase 1."""
    clear_cache()
    
    bf = parse_template('builder-first')
    assert 'pipeline_created' in bf['transitions']
    next_stage = bf['transitions']['pipeline_created'][0]
    assert next_stage == 'p1_builder_implement'
    
    res = parse_template('research')
    assert 'pipeline_created' in res['transitions']
    next_stage = res['transitions']['pipeline_created'][0]
    assert next_stage == 'p1_architect_design'


def test_human_gates():
    """Human gates are correctly identified."""
    clear_cache()
    
    bf = parse_template('builder-first')
    assert 'p1_complete' in bf['human_gates']
    assert 'p2_complete' in bf['human_gates']
    
    res = parse_template('research')
    assert 'p2_complete' in res['human_gates']
    assert 'p3_complete' in res['human_gates']
    assert 'p4_complete' in res['human_gates']
    # Phase 1 is auto gate in research
    assert 'p1_complete' not in res['human_gates']


def test_auto_gate_transitions():
    """Auto gates transition to next phase without human intervention."""
    clear_cache()
    
    res = parse_template('research')
    # p1_complete should auto-transition to p2_system_experiment_run
    assert 'p1_complete' in res['transitions']
    next_stage = res['transitions']['p1_complete'][0]
    assert next_stage == 'p2_system_experiment_run'


def test_session_modes():
    """Session modes (fresh/continue) are correctly parsed."""
    clear_cache()
    
    bf = parse_template('builder-first')
    # builder_implement → builder_bugfix should be 'continue'
    trans = bf['transitions']['p1_builder_implement']
    assert trans[3] == 'continue', f"Expected 'continue', got '{trans[3]}'"
    
    # critic_review should have 'fresh' session for its transition
    trans = bf['transitions']['p1_critic_review']
    assert trans[3] == 'fresh', f"Expected 'fresh', got '{trans[3]}'"


def test_block_transitions():
    """Block routing generates correct block transitions."""
    clear_cache()
    
    bf = parse_template('builder-first')
    # critic review block should route to builder fix
    assert 'p1_critic_review' in bf['block_transitions']
    block = bf['block_transitions']['p1_critic_review']
    assert block[1] == 'builder'  # fix role
    
    assert 'p2_critic_review' in bf['block_transitions']
    block = bf['block_transitions']['p2_critic_review']
    assert block[1] == 'builder'
    
    res = parse_template('research')
    # design_review block should route to architect
    assert 'p1_critic_design_review' in res['block_transitions']
    block = res['block_transitions']['p1_critic_design_review']
    assert block[1] == 'architect'
    
    # code_review block should route to builder
    assert 'p1_critic_code_review' in res['block_transitions']
    block = res['block_transitions']['p1_critic_code_review']
    assert block[1] == 'builder'


def test_status_bumps():
    """Status bumps are generated for all stages."""
    clear_cache()
    
    bf = parse_template('builder-first')
    assert 'p1_builder_implement' in bf['status_bumps']
    assert 'p1_complete' in bf['status_bumps']
    assert 'p2_complete' in bf['status_bumps']
    
    res = parse_template('research')
    assert 'p1_architect_design' in res['status_bumps']
    assert 'p2_system_experiment_run' in res['status_bumps']
    assert 'p4_complete' in res['status_bumps']


def test_transition_chain_builder_first():
    """Full transition chain works for builder-first phase 1."""
    clear_cache()
    
    bf = parse_template('builder-first')
    trans = bf['transitions']
    
    # Follow the chain
    stage = 'pipeline_created'
    chain = [stage]
    while stage in trans:
        next_stage = trans[stage][0]
        chain.append(next_stage)
        if next_stage in bf['human_gates'] or next_stage not in trans:
            break
        stage = next_stage
    
    expected = ['pipeline_created', 'p1_builder_implement', 'p1_builder_bugfix',
                'p1_critic_review', 'p1_complete']
    assert chain == expected, f"Chain mismatch: {chain}"


def test_transition_chain_research_phase1():
    """Full transition chain works for research phase 1 (auto-gate to phase 2)."""
    clear_cache()
    
    res = parse_template('research')
    trans = res['transitions']
    
    stage = 'pipeline_created'
    chain = [stage]
    seen = set()
    while stage in trans and stage not in seen:
        seen.add(stage)
        next_stage = trans[stage][0]
        chain.append(next_stage)
        if next_stage in res['human_gates'] or next_stage not in trans:
            break
        stage = next_stage
    
    # Should go through phase 1, auto-gate, into phase 2
    assert 'p1_architect_design' in chain
    assert 'p1_complete' in chain
    assert 'p2_system_experiment_run' in chain


def test_resolve_stage_name_legacy():
    """Legacy stage names resolve to new phase-based names."""
    clear_cache()
    
    bf = parse_template('builder-first')
    trans = bf['transitions']
    
    # Legacy builder-first names should resolve
    resolved = resolve_stage_name('builder_implement', trans)
    assert resolved == 'p1_builder_implement', f"Got {resolved}"
    
    # builder_bugfix maps to p1_builder_bugfix (builder-first specific)
    resolved = resolve_stage_name('builder_bugfix', trans)
    assert resolved == 'p1_builder_bugfix', f"Got {resolved}"
    
    # Research template legacy names
    res = parse_template('research')
    res_trans = res['transitions']
    
    resolved = resolve_stage_name('architect_design', res_trans)
    assert resolved == 'p1_architect_design', f"Got {resolved}"


def test_resolve_stage_name_new():
    """New stage names resolve directly."""
    clear_cache()
    
    bf = parse_template('builder-first')
    trans = bf['transitions']
    
    resolved = resolve_stage_name('p1_builder_implement', trans)
    assert resolved == 'p1_builder_implement'


def test_block_fix_transitions_back():
    """Block fix stages transition back to the blocking critic stage."""
    clear_cache()
    
    bf = parse_template('builder-first')
    trans = bf['transitions']
    
    # p1_builder_fix_blocks should route back to p1_critic_review
    assert 'p1_builder_fix_blocks' in trans
    assert trans['p1_builder_fix_blocks'][0] == 'p1_critic_review'


def test_research_four_phases():
    """Research template has 4 phases."""
    clear_cache()
    
    res = parse_template('research')
    stages = res['pipeline_fields']['stages']
    
    # Check we have stages from all 4 phases
    p1 = [s for s in stages if s.startswith('p1_')]
    p2 = [s for s in stages if s.startswith('p2_')]
    p3 = [s for s in stages if s.startswith('p3_')]
    p4 = [s for s in stages if s.startswith('p4_')]
    
    assert len(p1) > 0, "No Phase 1 stages"
    assert len(p2) > 0, "No Phase 2 stages"
    assert len(p3) > 0, "No Phase 3 stages"
    assert len(p4) > 0, "No Phase 4 stages"


def test_nonexistent_template():
    """Nonexistent template returns None."""
    clear_cache()
    result = parse_template('nonexistent-pipeline-type')
    assert result is None


if __name__ == '__main__':
    # Run all tests
    import inspect
    tests = [(name, obj) for name, obj in inspect.getmembers(sys.modules[__name__])
             if name.startswith('test_') and callable(obj)]
    
    passed = 0
    failed = 0
    for name, test_fn in sorted(tests):
        try:
            test_fn()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1
    
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
