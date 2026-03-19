#!/usr/bin/env python3
"""
Local Experiment Results Analyzer.

Reads experiment results (pkl + logs), generates comprehensive analysis markdown
with embedded plot references, statistical tables, and deeper analysis plots.

Output lives in the pipeline's local_results/{version}/ directory alongside
the experiment artifacts.

Usage:
    python3 scripts/analyze_local_results.py <version>
    python3 scripts/analyze_local_results.py <version> --skip-plots    # MD only, reuse existing plots
    python3 scripts/analyze_local_results.py <version> --extra-plots   # Generate additional deep analysis plots
"""

import argparse
import json
import os
import pickle
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

WORKSPACE = Path(os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace')))
ML_DIR = WORKSPACE / 'machinelearning' / 'snn_applied_finance'
RESULTS_BASE = ML_DIR / 'notebooks' / 'local_results'
PIPELINES_DIR = WORKSPACE / 'pipelines'


def load_pipeline_frontmatter(version: str) -> dict:
    """Load frontmatter from pipeline primitive."""
    path = PIPELINES_DIR / f'{version}.md'
    if not path.exists():
        return {}
    content = path.read_text()
    if not content.startswith('---'):
        return {}
    end = content.index('---', 3)
    result = {}
    for line in content[3:end].strip().split('\n'):
        if ':' in line and not line.startswith(' '):
            key, _, val = line.partition(':')
            val = val.strip().strip('"').strip("'")
            result[key.strip()] = val
    return result


def load_results(version: str) -> tuple:
    """Load results pickle and histories pickle for a pipeline version."""
    results_dir = RESULTS_BASE / version
    if not results_dir.exists():
        # Check for non-versioned results
        results_dir = RESULTS_BASE
    
    results = None
    histories = None
    
    # Find results pkl
    for pattern in [f'{version}_results.pkl', '*_results.pkl', 'equilibrium_v2_results.pkl']:
        matches = list(results_dir.glob(pattern))
        if matches:
            with open(matches[0], 'rb') as f:
                results = pickle.load(f)
            break
    
    # Also check parent for non-versioned results
    if results is None:
        for pattern in ['*_results.pkl']:
            matches = list(RESULTS_BASE.glob(pattern))
            if matches:
                with open(matches[0], 'rb') as f:
                    results = pickle.load(f)
                break
    
    # Find histories pkl
    for pattern in [f'{version}_histories.pkl', '*_histories.pkl', 'equilibrium_v2_histories.pkl']:
        matches = list(results_dir.glob(pattern))
        if matches:
            with open(matches[0], 'rb') as f:
                histories = pickle.load(f)
            break
    
    if histories is None:
        for pattern in ['*_histories.pkl']:
            matches = list(RESULTS_BASE.glob(pattern))
            if matches:
                with open(matches[0], 'rb') as f:
                    histories = pickle.load(f)
                break
    
    return results, histories, results_dir


def build_results_dataframe(results: list) -> pd.DataFrame:
    """Convert results list to a structured DataFrame."""
    if isinstance(results, pd.DataFrame):
        return results
    
    rows = []
    for r in results:
        if isinstance(r, dict):
            rows.append(r)
        elif hasattr(r, '_asdict'):
            rows.append(r._asdict())
        else:
            rows.append({'value': r})
    
    df = pd.DataFrame(rows)
    # Drop large array columns that break analysis
    drop_cols = [c for c in df.columns if c in ('raw_probs', 'predictions', 'actuals', 'final_spike_rates')]
    if drop_cols:
        df = df.drop(columns=drop_cols)
    return df


def compute_pooled_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute pooled (mean across folds) statistics per experiment."""
    # Identify fold column
    fold_col = None
    for col in ['fold', 'fold_id', 'Fold']:
        if col in df.columns:
            fold_col = col
            break
    
    # Identify experiment ID column
    exp_col = None
    for col in ['exp_id', 'experiment', 'experiment_id', 'Experiment', 'name', 'Name']:
        if col in df.columns:
            exp_col = col
            break
    
    if exp_col is None or fold_col is None:
        return df
    
    # Numeric columns for aggregation
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if fold_col in numeric_cols:
        numeric_cols.remove(fold_col)
    
    # Non-numeric metadata (take first value)
    meta_cols = [c for c in df.columns if c not in numeric_cols and c != exp_col and c != fold_col]
    
    agg_dict = {c: 'mean' for c in numeric_cols}
    for c in meta_cols:
        agg_dict[c] = 'first'
    
    pooled = df.groupby(exp_col).agg(agg_dict).reset_index()
    
    # Add fold count and std
    fold_counts = df.groupby(exp_col)[fold_col].count().reset_index()
    fold_counts.columns = [exp_col, 'n_folds']
    pooled = pooled.merge(fold_counts, on=exp_col)
    
    # Add std for key metrics
    for metric in ['accuracy', 'Accuracy', 'net_sharpe', 'Net Sharpe', 'val_accuracy', 'sharpe']:
        if metric in df.columns:
            std_df = df.groupby(exp_col)[metric].std().reset_index()
            std_df.columns = [exp_col, f'{metric}_std']
            pooled = pooled.merge(std_df, on=exp_col)
    
    return pooled


def categorize_experiments(pooled: pd.DataFrame) -> dict:
    """Categorize experiments by type for structured reporting."""
    categories = {
        'snn_primary': [],
        'snn_ablation': [],
        'baselines': [],
        'other': [],
    }
    
    exp_col = None
    for col in ['exp_id', 'experiment', 'experiment_id', 'Experiment', 'name', 'Name']:
        if col in pooled.columns:
            exp_col = col
            break
    
    type_col = None
    for col in ['type', 'Type', 'model_type']:
        if col in pooled.columns:
            type_col = col
            break
    
    for _, row in pooled.iterrows():
        name = str(row.get(exp_col, ''))
        exp_type = str(row.get(type_col, '')) if type_col else ''
        
        if 'ABL' in name.upper() or 'ablation' in exp_type.lower():
            categories['snn_ablation'].append(row)
        elif 'BL' in name.upper() or any(t in exp_type.lower() for t in ['ann', 'sklearn', 'majority', 'baseline']):
            categories['baselines'].append(row)
        elif 'EQ' in name.upper() or 'snn' in exp_type.lower():
            categories['snn_primary'].append(row)
        else:
            categories['other'].append(row)
    
    return categories


def generate_extra_plots(df: pd.DataFrame, pooled: pd.DataFrame, histories: dict,
                          output_dir: Path) -> list:
    """Generate additional deep analysis plots beyond the basic ones."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    
    generated = []
    
    exp_col = None
    for col in ['exp_id', 'experiment', 'experiment_id', 'Experiment', 'name', 'Name']:
        if col in df.columns:
            exp_col = col
            break
    
    acc_col = None
    for col in ['accuracy', 'Accuracy', 'val_accuracy']:
        if col in df.columns:
            acc_col = col
            break
    
    sharpe_col = None
    for col in ['net_sharpe', 'Net Sharpe', 'sharpe']:
        if col in df.columns:
            sharpe_col = col
            break
    
    fold_col = None
    for col in ['fold', 'fold_id', 'Fold']:
        if col in df.columns:
            fold_col = col
            break
    
    # 1. Accuracy distribution by experiment type
    try:
        type_col = None
        for col in ['type', 'Type', 'model_type']:
            if col in df.columns:
                type_col = col
                break
        
        if type_col and acc_col:
            fig, ax = plt.subplots(figsize=(10, 6))
            types = df[type_col].unique()
            data = [df[df[type_col] == t][acc_col].values for t in types]
            bp = ax.boxplot(data, labels=types, patch_artist=True)
            colors = ['#4C72B0', '#55A868', '#C44E52', '#8172B3', '#CCB974', '#64B5CD']
            for patch, color in zip(bp['boxes'], colors[:len(types)]):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            ax.set_title('Accuracy Distribution by Model Type', fontsize=14, fontweight='bold')
            ax.set_ylabel('Accuracy')
            ax.axhline(y=0.5, color='red', linestyle='--', alpha=0.5, label='Random baseline')
            ax.legend()
            ax.grid(axis='y', alpha=0.3)
            path = output_dir / 'accuracy_by_type.png'
            plt.tight_layout()
            plt.savefig(path, dpi=150)
            plt.close()
            generated.append(('accuracy_by_type.png', 'Accuracy Distribution by Model Type'))
    except Exception as e:
        print(f"  ⚠️  accuracy_by_type plot failed: {e}")
    
    # 2. Accuracy vs Sharpe scatter
    try:
        if acc_col and sharpe_col and exp_col:
            fig, ax = plt.subplots(figsize=(10, 8))
            for _, row in pooled.iterrows():
                name = str(row[exp_col])
                acc = row.get(acc_col, 0)
                sharpe = row.get(sharpe_col, 0)
                color = '#4C72B0' if 'EQ-' in name and 'ABL' not in name else \
                        '#55A868' if 'ABL' in name else '#C44E52'
                ax.scatter(acc, sharpe, c=color, s=100, alpha=0.7, edgecolors='white', linewidth=0.5)
                ax.annotate(name, (acc, sharpe), fontsize=7, ha='left', va='bottom', alpha=0.8)
            
            ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            ax.axvline(x=0.5, color='gray', linestyle='--', alpha=0.5)
            ax.set_xlabel('Accuracy (pooled mean)')
            ax.set_ylabel('Net Sharpe (pooled mean)')
            ax.set_title('Accuracy vs Net Sharpe — All Experiments', fontsize=14, fontweight='bold')
            ax.grid(alpha=0.3)
            
            # Add quadrant labels
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            ax.text(xlim[1]*0.98, ylim[1]*0.95, 'High Acc + Positive Sharpe\n(Best)', 
                    ha='right', va='top', fontsize=8, color='green', alpha=0.6)
            ax.text(xlim[0]*1.02, ylim[0]*1.05, 'Low Acc + Negative Sharpe\n(Worst)', 
                    ha='left', va='bottom', fontsize=8, color='red', alpha=0.6)
            
            path = output_dir / 'accuracy_vs_sharpe.png'
            plt.tight_layout()
            plt.savefig(path, dpi=150)
            plt.close()
            generated.append(('accuracy_vs_sharpe.png', 'Accuracy vs Net Sharpe Scatter'))
    except Exception as e:
        print(f"  ⚠️  accuracy_vs_sharpe plot failed: {e}")
    
    # 3. Fold variance analysis
    try:
        if fold_col and acc_col and exp_col:
            fold_var = df.groupby(exp_col)[acc_col].agg(['mean', 'std', 'min', 'max']).reset_index()
            fold_var['range'] = fold_var['max'] - fold_var['min']
            fold_var = fold_var.sort_values('range', ascending=True)
            
            fig, ax = plt.subplots(figsize=(10, max(6, len(fold_var) * 0.35)))
            y_pos = range(len(fold_var))
            ax.barh(y_pos, fold_var['range'], color='#4C72B0', alpha=0.7)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(fold_var[exp_col], fontsize=8)
            ax.set_xlabel('Accuracy Range (max - min across folds)')
            ax.set_title('Cross-Fold Stability (lower = more stable)', fontsize=14, fontweight='bold')
            ax.grid(axis='x', alpha=0.3)
            path = output_dir / 'fold_stability.png'
            plt.tight_layout()
            plt.savefig(path, dpi=150)
            plt.close()
            generated.append(('fold_stability.png', 'Cross-Fold Stability'))
    except Exception as e:
        print(f"  ⚠️  fold_stability plot failed: {e}")
    
    # 4. Scale analysis (if scale column exists)
    try:
        scale_col = None
        for col in ['scale', 'Scale', 'hidden_size', 'model_scale']:
            if col in pooled.columns:
                scale_col = col
                break
        
        if scale_col and acc_col:
            # Filter to SNN experiments only
            snn_mask = pooled[exp_col].str.contains('EQ-', case=False) & ~pooled[exp_col].str.contains('ABL', case=False)
            snn_data = pooled[snn_mask].copy()
            
            if len(snn_data) > 2:
                fig, ax = plt.subplots(figsize=(10, 6))
                scales = snn_data[scale_col].unique()
                scale_means = snn_data.groupby(scale_col)[acc_col].agg(['mean', 'std']).reset_index()
                
                ax.bar(range(len(scale_means)), scale_means['mean'], 
                       yerr=scale_means['std'], capsize=5,
                       color='#4C72B0', alpha=0.7, edgecolor='white')
                ax.set_xticks(range(len(scale_means)))
                ax.set_xticklabels(scale_means[scale_col], rotation=45, ha='right')
                ax.set_ylabel('Accuracy (mean ± std)')
                ax.set_title('Accuracy by Model Scale (SNN only)', fontsize=14, fontweight='bold')
                ax.axhline(y=0.5, color='red', linestyle='--', alpha=0.5, label='Random')
                ax.legend()
                ax.grid(axis='y', alpha=0.3)
                path = output_dir / 'scale_analysis.png'
                plt.tight_layout()
                plt.savefig(path, dpi=150)
                plt.close()
                generated.append(('scale_analysis.png', 'Accuracy by Model Scale'))
    except Exception as e:
        print(f"  ⚠️  scale_analysis plot failed: {e}")
    
    # 5. Training dynamics comparison (if histories available)
    try:
        if histories and len(histories) > 0:
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            
            # Sort histories by final accuracy (top 5 + bottom 5)
            final_accs = {}
            for key, h in histories.items():
                if 'val_accuracy' in h and len(h['val_accuracy']) > 0:
                    final_accs[key] = h['val_accuracy'][-1]
            
            sorted_keys = sorted(final_accs.keys(), key=lambda k: final_accs[k], reverse=True)
            top_keys = sorted_keys[:5]
            bottom_keys = sorted_keys[-3:] if len(sorted_keys) > 5 else []
            show_keys = top_keys + bottom_keys
            
            colors_top = ['#2ecc71', '#27ae60', '#1abc9c', '#16a085', '#3498db']
            colors_bottom = ['#e74c3c', '#c0392b', '#e67e22']
            
            for idx, key in enumerate(show_keys):
                h = histories[key]
                color = colors_top[idx] if idx < len(top_keys) else colors_bottom[idx - len(top_keys)]
                alpha = 0.8 if idx < len(top_keys) else 0.5
                label = key.replace('_fold', '/f')
                
                if 'train_loss' in h:
                    axes[0, 0].plot(h['train_loss'], label=label, color=color, alpha=alpha, linewidth=0.8)
                if 'val_accuracy' in h:
                    axes[0, 1].plot(h['val_accuracy'], label=label, color=color, alpha=alpha, linewidth=0.8)
                if 'val_sharpe' in h and h['val_sharpe']:
                    axes[1, 0].plot(h['val_sharpe'], label=label, color=color, alpha=alpha, linewidth=0.8)
                if 'lr' in h:
                    axes[1, 1].plot(h['lr'], label=label, color=color, alpha=alpha, linewidth=0.8)
            
            axes[0, 0].set_title('Training Loss (top 5 + bottom 3)')
            axes[0, 0].set_xlabel('Epoch')
            axes[0, 1].set_title('Validation Accuracy')
            axes[0, 1].set_xlabel('Epoch')
            axes[0, 1].axhline(y=0.5, color='red', linestyle='--', alpha=0.3)
            axes[1, 0].set_title('Validation Sharpe')
            axes[1, 0].set_xlabel('Epoch')
            axes[1, 0].axhline(y=0, color='red', linestyle='--', alpha=0.3)
            axes[1, 1].set_title('Learning Rate Schedule')
            axes[1, 1].set_xlabel('Epoch')
            
            for ax in axes.flat:
                ax.legend(fontsize=6, ncol=2)
                ax.grid(alpha=0.3)
            
            plt.suptitle('Training Dynamics — Top 5 vs Bottom 3', fontsize=14, fontweight='bold')
            path = output_dir / 'training_dynamics_comparison.png'
            plt.tight_layout()
            plt.savefig(path, dpi=150)
            plt.close()
            generated.append(('training_dynamics_comparison.png', 'Training Dynamics Comparison'))
    except Exception as e:
        print(f"  ⚠️  training_dynamics plot failed: {e}")
    
    # 6. Statistical significance heatmap (pairwise)
    try:
        if fold_col and acc_col and exp_col:
            from scipy import stats
            experiments = df[exp_col].unique()
            n = len(experiments)
            if n <= 20:  # Don't make massive heatmaps
                p_matrix = np.ones((n, n))
                for i in range(n):
                    for j in range(i+1, n):
                        vals_i = df[df[exp_col] == experiments[i]][acc_col].values
                        vals_j = df[df[exp_col] == experiments[j]][acc_col].values
                        if len(vals_i) >= 2 and len(vals_j) >= 2:
                            _, p = stats.ttest_ind(vals_i, vals_j)
                            p_matrix[i, j] = p
                            p_matrix[j, i] = p
                
                fig, ax = plt.subplots(figsize=(max(10, n * 0.6), max(8, n * 0.5)))
                im = ax.imshow(p_matrix, cmap='RdYlGn', vmin=0, vmax=0.1)
                ax.set_xticks(range(n))
                ax.set_yticks(range(n))
                ax.set_xticklabels(experiments, rotation=90, fontsize=7)
                ax.set_yticklabels(experiments, fontsize=7)
                plt.colorbar(im, label='p-value (t-test)')
                ax.set_title('Pairwise Statistical Significance\n(green = p > 0.05, red = p < 0.05)', 
                           fontsize=12, fontweight='bold')
                path = output_dir / 'significance_heatmap.png'
                plt.tight_layout()
                plt.savefig(path, dpi=150)
                plt.close()
                generated.append(('significance_heatmap.png', 'Pairwise Statistical Significance'))
    except ImportError:
        print(f"  ⚠️  significance_heatmap skipped (scipy not available)")
    except Exception as e:
        print(f"  ⚠️  significance_heatmap plot failed: {e}")
    
    return generated


def generate_analysis_markdown(version: str, df: pd.DataFrame, pooled: pd.DataFrame,
                                 categories: dict, histories: dict, extra_plots: list,
                                 results_dir: Path, frontmatter: dict) -> str:
    """Generate comprehensive analysis markdown document."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    
    # Detect column names
    exp_col = None
    for col in ['exp_id', 'experiment', 'experiment_id', 'Experiment', 'name', 'Name']:
        if col in pooled.columns:
            exp_col = col
            break
    
    acc_col = None
    for col in ['accuracy', 'Accuracy', 'val_accuracy']:
        if col in pooled.columns:
            acc_col = col
            break
    
    sharpe_col = None
    for col in ['net_sharpe', 'Net Sharpe', 'sharpe']:
        if col in pooled.columns:
            sharpe_col = col
            break
    
    type_col = None
    for col in ['type', 'Type', 'model_type']:
        if col in pooled.columns:
            type_col = col
            break
    
    scale_col = None
    for col in ['scale', 'Scale', 'hidden_size', 'model_scale']:
        if col in pooled.columns:
            scale_col = col
            break
    
    # Sort pooled by accuracy
    if acc_col:
        pooled_sorted = pooled.sort_values(acc_col, ascending=False)
    else:
        pooled_sorted = pooled
    
    n_experiments = len(pooled_sorted)
    n_results = len(df)
    n_folds = df[next((c for c in ['fold', 'fold_id', 'Fold'] if c in df.columns), None)].nunique() if any(c in df.columns for c in ['fold', 'fold_id', 'Fold']) else 1
    
    # Read run.log for timing
    run_log = results_dir / 'run.log'
    elapsed_min = 0
    if run_log.exists():
        log_text = run_log.read_text()
        import re
        m = re.search(r'COMPLETE: \d+ results in ([\d.]+) minutes', log_text)
        if m:
            elapsed_min = float(m.group(1))
    
    # --- Build the document ---
    md = f"""---
title: "Experiment Analysis Report: {version}"
date: "{now}"
pipeline: {version}
n_experiments: {n_experiments}
n_folds: {n_folds}
total_runs: {n_results}
elapsed_minutes: {elapsed_min:.1f}
status: pending_review
---

# Experiment Analysis Report: {version}

**Generated:** {now}  
**Pipeline:** `{version}` | Priority: {frontmatter.get('priority', 'N/A')}  
**Total:** {n_experiments} experiments × {n_folds} folds = {n_results} runs in {elapsed_min:.1f} minutes  
**Platform:** Local CPU (ARM64, 4 cores)

---

## Executive Summary

"""
    
    # Top performers
    if acc_col and len(pooled_sorted) > 0:
        top3 = pooled_sorted.head(3)
        md += "### Top 3 Experiments (by accuracy)\n\n"
        md += "| Rank | Experiment | Type | Accuracy | Net Sharpe |\n"
        md += "|------|-----------|------|----------|------------|\n"
        for i, (_, row) in enumerate(top3.iterrows()):
            acc = row.get(acc_col, 0)
            sharpe = row.get(sharpe_col, 0) if sharpe_col else 0
            exp_type = row.get(type_col, 'N/A') if type_col else 'N/A'
            md += f"| {i+1} | **{row[exp_col]}** | {exp_type} | {acc:.4f} | {sharpe:.4f} |\n"
        md += "\n"
    
    # Overall assessment
    if acc_col:
        mean_acc = pooled_sorted[acc_col].mean()
        max_acc = pooled_sorted[acc_col].max()
        above_50 = (pooled_sorted[acc_col] > 0.5).sum()
        md += f"""### Key Findings

- **Mean accuracy across all experiments:** {mean_acc:.4f}
- **Best single experiment:** {max_acc:.4f} ({pooled_sorted.iloc[0][exp_col]})
- **Experiments above 50% (random baseline):** {above_50}/{n_experiments}
"""
        if sharpe_col:
            positive_sharpe = (pooled_sorted[sharpe_col] > 0).sum()
            md += f"- **Experiments with positive net Sharpe:** {positive_sharpe}/{n_experiments}\n"
        md += "\n"
    
    # Accuracy summary plot
    if (results_dir / 'accuracy_summary.png').exists():
        md += f"![Accuracy Summary — All Experiments](accuracy_summary.png)\n\n"
    
    md += "---\n\n"
    
    # --- Detailed Results by Category ---
    md += "## Detailed Results\n\n"
    
    category_names = {
        'snn_primary': 'SNN Primary Experiments',
        'snn_ablation': 'SNN Ablation Studies', 
        'baselines': 'Baseline Comparisons',
        'other': 'Other Experiments',
    }
    
    for cat_key, cat_name in category_names.items():
        rows = categories.get(cat_key, [])
        if not rows:
            continue
        
        md += f"### {cat_name}\n\n"
        
        # Build table
        headers = ['Experiment']
        if scale_col:
            headers.append('Scale')
        headers.extend(['Accuracy', 'Acc Std'])
        if sharpe_col:
            headers.extend(['Net Sharpe'])
        headers.append('Folds')
        
        md += "| " + " | ".join(headers) + " |\n"
        md += "| " + " | ".join(['---'] * len(headers)) + " |\n"
        
        # Sort by accuracy
        rows_sorted = sorted(rows, key=lambda r: r.get(acc_col, 0) if acc_col else 0, reverse=True)
        
        for row in rows_sorted:
            vals = [f"**{row[exp_col]}**"]
            if scale_col:
                vals.append(str(row.get(scale_col, 'N/A')))
            
            acc = row.get(acc_col, 0)
            acc_std_col = f'{acc_col}_std'
            acc_std = row.get(acc_std_col, 0)
            vals.append(f"{acc:.4f}")
            vals.append(f"±{acc_std:.4f}" if acc_std else "—")
            
            if sharpe_col:
                sharpe = row.get(sharpe_col, 0)
                vals.append(f"{sharpe:.4f}")
            
            vals.append(str(int(row.get('n_folds', n_folds))))
            md += "| " + " | ".join(vals) + " |\n"
        
        md += "\n"
    
    # --- Plots Section ---
    md += "---\n\n## Analysis Plots\n\n"
    
    # Standard plots
    standard_plots = [
        ('accuracy_summary.png', 'Accuracy Summary — All Experiments'),
        ('eq04_learning_curves.png', 'Learning Curves — Best SNN (EQ-04)'),
        ('threshold_spike_rates.png', 'Threshold & Spike Rate Evolution'),
    ]
    
    for filename, caption in standard_plots:
        if (results_dir / filename).exists():
            md += f"### {caption}\n\n"
            md += f"![{caption}]({filename})\n\n"
    
    # Extra analysis plots
    if extra_plots:
        md += "### Deep Analysis Plots\n\n"
        for filename, caption in extra_plots:
            md += f"#### {caption}\n\n"
            md += f"![{caption}]({filename})\n\n"
    
    # --- Statistical Analysis ---
    md += "---\n\n## Statistical Analysis\n\n"
    
    # SNN vs Baselines comparison
    snn_rows = categories.get('snn_primary', [])
    bl_rows = categories.get('baselines', [])
    
    if snn_rows and bl_rows and acc_col:
        snn_accs = [r[acc_col] for r in snn_rows if acc_col in r]
        bl_accs = [r[acc_col] for r in bl_rows if acc_col in r]
        
        md += "### SNN vs Baselines\n\n"
        md += f"- **SNN mean accuracy:** {np.mean(snn_accs):.4f} (n={len(snn_accs)})\n"
        md += f"- **Baseline mean accuracy:** {np.mean(bl_accs):.4f} (n={len(bl_accs)})\n"
        md += f"- **SNN advantage:** {np.mean(snn_accs) - np.mean(bl_accs):+.4f}\n"
        
        try:
            from scipy import stats
            t_stat, p_val = stats.ttest_ind(snn_accs, bl_accs)
            md += f"- **t-test:** t={t_stat:.3f}, p={p_val:.4f} "
            md += f"({'significant' if p_val < 0.05 else 'not significant'} at α=0.05)\n"
        except ImportError:
            pass
        md += "\n"
    
    # Scale analysis
    if scale_col and acc_col and snn_rows:
        md += "### Scale Analysis\n\n"
        scale_groups = {}
        for r in snn_rows:
            s = str(r.get(scale_col, 'unknown'))
            if s not in scale_groups:
                scale_groups[s] = []
            scale_groups[s].append(r[acc_col])
        
        md += "| Scale | Mean Acc | Std | N |\n"
        md += "|-------|---------|-----|---|\n"
        for scale in sorted(scale_groups.keys()):
            accs = scale_groups[scale]
            md += f"| {scale} | {np.mean(accs):.4f} | {np.std(accs):.4f} | {len(accs)} |\n"
        md += "\n"
    
    # Ablation analysis
    abl_rows = categories.get('snn_ablation', [])
    if abl_rows and acc_col:
        md += "### Ablation Insights\n\n"
        for r in sorted(abl_rows, key=lambda x: x.get(acc_col, 0), reverse=True):
            name = r[exp_col]
            acc = r.get(acc_col, 0)
            md += f"- **{name}:** {acc:.4f}\n"
        md += "\n"
    
    # --- Agent Instructions ---
    md += """---

## Agent Instructions for Deeper Analysis

The following tasks require judgment and domain expertise. The **architect** (with extended thinking/reasoning enabled) should:

1. **Interpret the results** — What do the accuracy patterns tell us about the SNN architecture's ability to learn from financial time series?
2. **Analyze the ablation gap** — Which component ablations had the biggest impact? What does this reveal about the architecture?
3. **Assess the Sharpe discrepancy** — Why do high-accuracy experiments often have negative Sharpe? Is this a cost model issue, position sizing, or signal timing?
4. **Scale-performance relationship** — Is there evidence of underfitting (bigger models help) or overfitting (smaller models generalize better)?
5. **Propose follow-up experiments** — Based on patterns here, what specific experiments should Phase 3 explore?

The **builder** (with extended thinking/reasoning enabled) should:
1. **Run any additional statistical tests** not covered above (e.g., bootstrap confidence intervals, permutation tests)
2. **Generate any additional plots** that would strengthen the analysis (e.g., prediction calibration curves, per-fold learning curves for top experiments)
3. **Build the LaTeX report** from this analysis document
4. **Compile to PDF** in this same results directory

### Scripts Available for Deeper Analysis

```bash
# Load results programmatically
python3 -c "
import pickle
with open('RESULTS_DIR/equilibrium_v2_results.pkl', 'rb') as f:
    results = pickle.load(f)
# results is a list of dicts with: experiment, fold, accuracy, net_sharpe, type, scale, etc.
"

# Run additional statistical analysis
python3 scripts/analyze_local_results.py VERSION --extra-plots

# Build LaTeX report and compile to PDF
python3 scripts/build_report.py VERSION
```

"""
    
    md = md.replace('RESULTS_DIR', str(results_dir))
    md = md.replace('VERSION', version)
    
    return md


def main():
    parser = argparse.ArgumentParser(description='Analyze local experiment results')
    parser.add_argument('version', help='Pipeline version')
    parser.add_argument('--skip-plots', action='store_true', help='Skip plot generation, reuse existing')
    parser.add_argument('--extra-plots', action='store_true', default=True, help='Generate deep analysis plots (default: on)')
    parser.add_argument('--no-extra-plots', action='store_true', help='Skip extra analysis plots')
    args = parser.parse_args()
    
    version = args.version
    print(f"\n{'═' * 70}")
    print(f"  📊 LOCAL RESULTS ANALYZER — {version}")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'═' * 70}\n")
    
    # Load pipeline info
    fm = load_pipeline_frontmatter(version)
    
    # Load results
    results, histories, results_dir = load_results(version)
    if results is None:
        print(f"❌ No results found for {version}")
        print(f"   Checked: {RESULTS_BASE / version}/ and {RESULTS_BASE}/")
        sys.exit(1)
    
    print(f"  📂 Results dir: {results_dir}")
    
    # Build dataframe
    df = build_results_dataframe(results)
    print(f"  📊 Loaded {len(df)} result records")
    
    # Compute pooled stats
    pooled = compute_pooled_stats(df)
    print(f"  📈 {len(pooled)} experiments (pooled across folds)")
    
    # Categorize
    categories = categorize_experiments(pooled)
    for cat, rows in categories.items():
        if rows:
            print(f"    {cat}: {len(rows)}")
    
    # Generate extra plots
    extra_plots = []
    if not args.skip_plots and not args.no_extra_plots:
        print(f"\n  🎨 Generating analysis plots...")
        extra_plots = generate_extra_plots(df, pooled, histories, results_dir)
        print(f"  ✅ Generated {len(extra_plots)} analysis plots")
    
    # Generate analysis markdown
    print(f"\n  📝 Generating analysis document...")
    md_content = generate_analysis_markdown(
        version, df, pooled, categories, histories,
        extra_plots, results_dir, fm
    )
    
    # Write to results directory
    analysis_path = results_dir / f'{version}_analysis.md'
    analysis_path.write_text(md_content)
    print(f"  ✅ Analysis written to: {analysis_path.relative_to(WORKSPACE)}")
    
    # Also write a summary for the pipeline builds dir
    builds_dir = ML_DIR / 'research' / 'pipeline_builds'
    builds_dir.mkdir(parents=True, exist_ok=True)
    summary_link = builds_dir / f'{version}_local_analysis.md'
    summary_link.write_text(f"""---
type: analysis_reference
version: {version}
generated: {datetime.now(timezone.utc).isoformat()}
---

# Local Experiment Analysis — {version}

Full analysis document: `{analysis_path.relative_to(WORKSPACE)}`
Results directory: `{results_dir.relative_to(WORKSPACE)}`

To build the PDF report:
```bash
python3 scripts/build_report.py {version}
```
""")
    
    print(f"\n{'═' * 70}")
    print(f"  ✅ ANALYSIS COMPLETE — {version}")
    print(f"  📄 {analysis_path.relative_to(WORKSPACE)}")
    print(f"  Next: python3 scripts/build_report.py {version}")
    print(f"{'═' * 70}\n")


if __name__ == '__main__':
    main()
