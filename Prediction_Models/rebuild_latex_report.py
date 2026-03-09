"""
Quick script to rebuild prediction_models_report.pdf with corrected figure references.
Reuses existing data and plots without rerunning the full analysis.
"""

import sys
from pathlib import Path
import pandas as pd
import pickle

# Add parent directory to path to import from loocv_model_comparison
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import the function we need
from loocv_model_comparison import (
    create_combined_latex_report,
    OUTPUT_ROOT,
    OUTPUT_DIRS,
    PROJECT_ROOT
)

print("=" * 80)
print("Rebuilding prediction_models_report.pdf with corrected figure references")
print("=" * 80)

# Load existing Stage 1 results
performance_dir = OUTPUT_DIRS['performance']
loocv_results_path = performance_dir / 'loocv_results.csv'

if not loocv_results_path.exists():
    print(f"Error: Could not find {loocv_results_path}")
    print("Please run the full loocv_model_comparison.py first to generate results.")
    sys.exit(1)

stage1_results = pd.read_csv(loocv_results_path)
print(f"Loaded Stage 1 results: {stage1_results.shape}")

# Load existing Stage 2 results
stage2_3fold_path = performance_dir / 'stage2_results_3fold.csv'
stage2_4fold_path = performance_dir / 'stage2_results_4fold.csv'
stage2_5fold_path = performance_dir / 'stage2_results_5fold.csv'

stage2_results = {}

for n_folds, path in [(3, stage2_3fold_path), (4, stage2_4fold_path), (5, stage2_5fold_path)]:
    if path.exists():
        df = pd.read_csv(path)
        # Reconstruct the nested dictionary structure expected by create_combined_latex_report
        fold_results = {}
        for target in ['Arrhythmia', 'heart_damage', 'Concern']:
            target_df = df[df['Target'] == target]
            if not target_df.empty:
                fold_results[target] = {
                    'accuracies': target_df['Accuracy'].tolist(),
                    'aucs': target_df['AUC'].tolist(),
                    'f1s': target_df['F1'].tolist(),
                    'mccs': target_df['MCC'].tolist(),
                }
        stage2_results[n_folds] = fold_results
        print(f"Loaded Stage 2 {n_folds}-fold results: {df.shape}")
    else:
        print(f"Warning: {path} not found, skipping {n_folds}-fold results")

if not stage2_results:
    print("Error: No Stage 2 results found. Please run the full pipeline first.")
    sys.exit(1)

# Rebuild the LaTeX report with corrected figure references
print("\nRebuilding LaTeX PDF...")
create_combined_latex_report(stage1_results, stage2_results)

print("\n" + "=" * 80)
print("PDF rebuild complete!")
print("=" * 80)
print(f"Updated PDF: {OUTPUT_DIRS['latex'] / 'prediction_models_report.pdf'}")
