#!/usr/bin/env python3
"""Apply Critic code review fixes to validate-scheme-b notebook.

BLOCK-1: Fix KeyError in majority/random baselines (data_dict['labels'] → data_dict['delta']['labels'])
FLAG-1: DSR Lo (2002) non-normal adjustment — compute actual skewness/kurtosis
FLAG-2: hash(exp_id) → hashlib.md5 for deterministic seeds
FLAG-5: Add net_sharpe_abst to baseline results for consistency
S-1: Replace deprecated binom_test with binomtest
"""

import json
import sys
import os

NB_PATH = os.path.expanduser(
    "~/.openclaw/workspace/machinelearning/snn_applied_finance/notebooks/"
    "crypto_validate-scheme-b_predictor.ipynb"
)

def apply_fixes():
    with open(NB_PATH) as f:
        nb = json.load(f)

    fixes_applied = []

    # ── CELL 4: Add hashlib import (FLAG-2) ──
    cell4_src = ''.join(nb['cells'][4]['source'])
    if 'import hashlib' not in cell4_src:
        cell4_src = cell4_src.replace(
            'import math, time, copy, pickle, warnings, json',
            'import math, time, copy, pickle, warnings, json, hashlib'
        )
        nb['cells'][4]['source'] = cell4_src.split('\n')
        nb['cells'][4]['source'] = [line + '\n' for line in cell4_src.split('\n')]
        # Remove trailing \n from last line
        if nb['cells'][4]['source'][-1] == '\n':
            nb['cells'][4]['source'] = nb['cells'][4]['source'][:-1]
        fixes_applied.append("Cell 4: Added hashlib import (FLAG-2)")

    # ── CELL 27: Main experiment cell — BLOCK-1 + FLAG-2 + FLAG-5 ──
    cell27_src = ''.join(nb['cells'][27]['source'])

    # FLAG-2: Replace hash() with hashlib.md5
    old_seed = "seed = MASTER_SEED + hash(exp_id) % 10000 + fold_idx"
    new_seed = "seed = MASTER_SEED + int(hashlib.md5(exp_id.encode()).hexdigest(), 16) % 10000 + fold_idx"
    if old_seed in cell27_src:
        cell27_src = cell27_src.replace(old_seed, new_seed)
        fixes_applied.append("Cell 27: Deterministic seeds via hashlib.md5 (FLAG-2)")

    # BLOCK-1: Fix majority baseline — data_dict['labels'] → data_dict['delta']['labels']
    # Also add net_sharpe_abst (FLAG-5)
    old_majority = """    if scheme == 'majority':
        train_labels = data_dict['labels'][ts:te].numpy()
        val_labels = data_dict['labels'][vs:ve].numpy()
        val_returns = data_dict['returns'][vs:ve].numpy()
        majority = 1 if train_labels.mean() > 0.5 else 0
        preds = np.full(len(val_labels), majority)
        acc = accuracy_score(val_labels, preds)
        fin = compute_financial_metrics(preds, val_returns, config['cost_per_trade'])
        return {
            'experiment_id': exp_id, 'fold': fold_idx + 1,
            'accuracy': acc, 'majority_baseline': majority_baseline_acc(val_labels),
            'accuracy_lift': acc - majority_baseline_acc(val_labels),
            **{k: v for k, v in fin.items() if k not in ('net_pnl', 'gross_pnl')},
            '_predictions': preds, '_labels': val_labels,
            '_returns': val_returns, '_net_pnl': fin['net_pnl'],
            'epochs_run': 0, '_history': None,
        }"""

    new_majority = """    if scheme == 'majority':
        dd_ref = data_dict['delta']  # BLOCK-1 fix: bundle has 'delta'/'pop', not 'labels'
        train_labels = dd_ref['labels'][ts:te].numpy()
        val_labels = dd_ref['labels'][vs:ve].numpy()
        val_returns = dd_ref['returns'][vs:ve].numpy()
        majority = 1 if train_labels.mean() > 0.5 else 0
        preds = np.full(len(val_labels), majority)
        acc = accuracy_score(val_labels, preds)
        fin = compute_financial_metrics(preds, val_returns, config['cost_per_trade'])
        return {
            'experiment_id': exp_id, 'fold': fold_idx + 1,
            'accuracy': acc, 'majority_baseline': majority_baseline_acc(val_labels),
            'accuracy_lift': acc - majority_baseline_acc(val_labels),
            **{k: v for k, v in fin.items() if k not in ('net_pnl', 'gross_pnl')},
            'net_sharpe_abst': fin['net_sharpe'],  # FLAG-5: consistent key for baselines
            '_predictions': preds, '_labels': val_labels,
            '_returns': val_returns, '_net_pnl': fin['net_pnl'],
            'epochs_run': 0, '_history': None,
        }"""

    if old_majority in cell27_src:
        cell27_src = cell27_src.replace(old_majority, new_majority)
        fixes_applied.append("Cell 27: Fixed majority baseline KeyError (BLOCK-1) + added net_sharpe_abst (FLAG-5)")
    else:
        print("WARNING: Could not find majority baseline block to replace")

    # BLOCK-1: Fix random baseline
    old_random = """    if scheme == 'random':
        val_labels = data_dict['labels'][vs:ve].numpy()
        val_returns = data_dict['returns'][vs:ve].numpy()
        rng = np.random.RandomState(seed)
        preds = rng.randint(0, 2, size=len(val_labels))
        acc = accuracy_score(val_labels, preds)
        fin = compute_financial_metrics(preds, val_returns, config['cost_per_trade'])
        return {
            'experiment_id': exp_id, 'fold': fold_idx + 1,
            'accuracy': acc, 'majority_baseline': majority_baseline_acc(val_labels),
            'accuracy_lift': acc - majority_baseline_acc(val_labels),
            **{k: v for k, v in fin.items() if k not in ('net_pnl', 'gross_pnl')},
            '_predictions': preds, '_labels': val_labels,
            '_returns': val_returns, '_net_pnl': fin['net_pnl'],
            'epochs_run': 0, '_history': None,
        }"""

    new_random = """    if scheme == 'random':
        dd_ref = data_dict['delta']  # BLOCK-1 fix: bundle has 'delta'/'pop', not 'labels'
        val_labels = dd_ref['labels'][vs:ve].numpy()
        val_returns = dd_ref['returns'][vs:ve].numpy()
        rng = np.random.RandomState(seed)
        preds = rng.randint(0, 2, size=len(val_labels))
        acc = accuracy_score(val_labels, preds)
        fin = compute_financial_metrics(preds, val_returns, config['cost_per_trade'])
        return {
            'experiment_id': exp_id, 'fold': fold_idx + 1,
            'accuracy': acc, 'majority_baseline': majority_baseline_acc(val_labels),
            'accuracy_lift': acc - majority_baseline_acc(val_labels),
            **{k: v for k, v in fin.items() if k not in ('net_pnl', 'gross_pnl')},
            'net_sharpe_abst': fin['net_sharpe'],  # FLAG-5: consistent key for baselines
            '_predictions': preds, '_labels': val_labels,
            '_returns': val_returns, '_net_pnl': fin['net_pnl'],
            'epochs_run': 0, '_history': None,
        }"""

    if old_random in cell27_src:
        cell27_src = cell27_src.replace(old_random, new_random)
        fixes_applied.append("Cell 27: Fixed random baseline KeyError (BLOCK-1) + added net_sharpe_abst (FLAG-5)")
    else:
        print("WARNING: Could not find random baseline block to replace")

    # Also add net_sharpe_abst to LR/RF return dicts (FLAG-5)
    old_lr_rf_return = """        return {
            'experiment_id': exp_id, 'fold': fold_idx + 1,
            'accuracy': acc, 'majority_baseline': majority_baseline_acc(val_labels),
            'accuracy_lift': acc - majority_baseline_acc(val_labels),
            **{k: v for k, v in fin.items() if k not in ('net_pnl', 'gross_pnl')},
            '_predictions': preds, '_labels': val_labels,
            '_returns': val_returns, '_net_pnl': fin['net_pnl'],
            'epochs_run': 1, '_history': None,
        }"""

    new_lr_rf_return = """        return {
            'experiment_id': exp_id, 'fold': fold_idx + 1,
            'accuracy': acc, 'majority_baseline': majority_baseline_acc(val_labels),
            'accuracy_lift': acc - majority_baseline_acc(val_labels),
            **{k: v for k, v in fin.items() if k not in ('net_pnl', 'gross_pnl')},
            'net_sharpe_abst': fin['net_sharpe'],  # FLAG-5: consistent key for baselines
            '_predictions': preds, '_labels': val_labels,
            '_returns': val_returns, '_net_pnl': fin['net_pnl'],
            'epochs_run': 1, '_history': None,
        }"""

    if old_lr_rf_return in cell27_src:
        cell27_src = cell27_src.replace(old_lr_rf_return, new_lr_rf_return)
        fixes_applied.append("Cell 27: Added net_sharpe_abst to LR/RF returns (FLAG-5)")
    else:
        print("WARNING: Could not find LR/RF return block")

    nb['cells'][27]['source'] = [line + '\n' for line in cell27_src.split('\n')]
    # Fix last line
    if nb['cells'][27]['source'][-1] == '\n':
        nb['cells'][27]['source'] = nb['cells'][27]['source'][:-1]

    # ── CELL 33: Replace deprecated binom_test (S-1) ──
    cell33_src = ''.join(nb['cells'][33]['source'])
    old_binom = "p_sign = stats.binom_test(n_positive, n_total, 0.5, alternative='greater')"
    new_binom = "p_sign = stats.binomtest(n_positive, n_total, 0.5, alternative='greater').pvalue"
    if old_binom in cell33_src:
        cell33_src = cell33_src.replace(old_binom, new_binom)
        nb['cells'][33]['source'] = [line + '\n' for line in cell33_src.split('\n')]
        if nb['cells'][33]['source'][-1] == '\n':
            nb['cells'][33]['source'] = nb['cells'][33]['source'][:-1]
        fixes_applied.append("Cell 33: Replaced deprecated binom_test with binomtest (S-1)")

    # ── CELL 35: DSR Lo (2002) non-normal adjustment (FLAG-1) ──
    cell35_src = ''.join(nb['cells'][35]['source'])
    old_dsr_call = """    psr, e_max = deflated_sharpe_ratio(
        observed_sr, sr_std, CONFIG['n_trials_dsr'], len(all_pnl)
    )

    print("=" * 60)
    print("TEST 2: Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014)")
    print("=" * 60)
    print(f"  Observed pooled Sharpe: {observed_sr:.4f}")
    print(f"  n_trials (V3 search): {CONFIG['n_trials_dsr']}")
    print(f"  Sharpe std across experiments: {sr_std:.4f}")
    print(f"  Expected max Sharpe under null: {e_max:.4f}")
    print(f"  DSR (prob of genuine skill): {psr:.4f}")
    print(f"  DSR > 0.5? {'YES — genuine signal' if psr > 0.5 else 'NO — within random search range'}")"""

    new_dsr_call = """    # FLAG-1: Lo (2002) non-normal adjustment — BTC returns have fat tails
    pnl_skew = stats.skew(all_pnl)
    pnl_kurt = stats.kurtosis(all_pnl) + 3  # scipy returns excess; Lo uses raw kurtosis

    psr, e_max = deflated_sharpe_ratio(
        observed_sr, sr_std, CONFIG['n_trials_dsr'], len(all_pnl),
        skewness=pnl_skew, kurtosis=pnl_kurt
    )

    print("=" * 60)
    print("TEST 2: Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014)")
    print("         with Lo (2002) non-normal SE adjustment")
    print("=" * 60)
    print(f"  Observed pooled Sharpe: {observed_sr:.4f}")
    print(f"  n_trials (V3 search): {CONFIG['n_trials_dsr']}")
    print(f"  Sharpe std across experiments: {sr_std:.4f}")
    print(f"  Expected max Sharpe under null: {e_max:.4f}")
    print(f"  PnL skewness: {pnl_skew:.4f}, kurtosis: {pnl_kurt:.4f}")
    print(f"  DSR (prob of genuine skill): {psr:.4f}")
    print(f"  DSR > 0.5? {'YES — genuine signal' if psr > 0.5 else 'NO — within random search range'}")"""

    if old_dsr_call in cell35_src:
        cell35_src = cell35_src.replace(old_dsr_call, new_dsr_call)
        nb['cells'][35]['source'] = [line + '\n' for line in cell35_src.split('\n')]
        if nb['cells'][35]['source'][-1] == '\n':
            nb['cells'][35]['source'] = nb['cells'][35]['source'][:-1]
        fixes_applied.append("Cell 35: DSR now uses actual BTC skewness/kurtosis via Lo (2002) (FLAG-1)")
    else:
        print("WARNING: Could not find DSR call site to replace")

    # ── CELL 16: Fix make_walk_forward_folds to accept bundle dict ──
    # Cell 16 calls data_dict['labels'] but receives the bundle. Let's check.
    cell16_src = ''.join(nb['cells'][16]['source'])
    if "data_dict['labels']" in cell16_src and 'data_dict.get(' not in cell16_src:
        # This function is called with delta_data directly (not the bundle), so it's fine
        # Let me verify the call site
        pass

    # Write back
    with open(NB_PATH, 'w') as f:
        json.dump(nb, f, indent=1)

    print(f"\n{'='*60}")
    print(f"FIXES APPLIED: {len(fixes_applied)}")
    print(f"{'='*60}")
    for fix in fixes_applied:
        print(f"  ✅ {fix}")
    print(f"\nNotebook saved: {NB_PATH}")

    return len(fixes_applied)

if __name__ == '__main__':
    n = apply_fixes()
    sys.exit(0 if n > 0 else 1)
