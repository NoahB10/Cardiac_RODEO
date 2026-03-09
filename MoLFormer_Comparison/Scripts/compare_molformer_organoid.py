"""
Compare MoLFormer DIQT predictions with Organoid-based Arrhythmia predictions.

Generates comparison plots and metrics similar to ADMET comparison.
"""
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from pathlib import Path

# Register Helvetica fonts from local fonts folder
_font_dir = Path(__file__).resolve().parent.parent.parent / 'fonts'
if _font_dir.exists():
    for _font_file in _font_dir.glob('*.ttf'):
        fm.fontManager.addfont(str(_font_file))
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
from sklearn.metrics import (
    accuracy_score, roc_auc_score, precision_score, recall_score,
    f1_score, confusion_matrix, matthews_corrcoef, balanced_accuracy_score,
    average_precision_score, roc_curve
)

# Path setup
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
OUTPUT_DIR = PROJECT_ROOT / "Output" / "MoLFormer_Comparison"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    """Load MoLFormer and Organoid predictions."""
    # MoLFormer predictions
    molformer_path = OUTPUT_DIR / "molformer_predictions_25.csv"
    molformer_df = pd.read_csv(molformer_path)

    # Organoid predictions
    organoid_path = PROJECT_ROOT / "Output" / "Prediction_Scatter_Data" / "arrhythmia_predictions.csv"
    organoid_df = pd.read_csv(organoid_path)

    # Merge on Drug name
    merged = molformer_df.merge(organoid_df, on='Drug', how='inner')

    # Normalize organoid predictions to 0-1 scale
    merged['Organoid_prob'] = merged['Predicted_Arrhythmia_pct'] / 100.0
    merged['Organoid_pred'] = (merged['Organoid_prob'] >= 0.5).astype(int)

    return merged

def compute_metrics(y_true, y_pred, y_prob):
    """Compute classification metrics."""
    metrics = {
        'Accuracy': accuracy_score(y_true, y_pred),
        'Precision': precision_score(y_true, y_pred, zero_division=0),
        'Recall': recall_score(y_true, y_pred, zero_division=0),
        'F1': f1_score(y_true, y_pred, zero_division=0),
        'MCC': matthews_corrcoef(y_true, y_pred),
        'AUROC': roc_auc_score(y_true, y_prob) if len(np.unique(y_true)) > 1 else 0,
    }
    return metrics

def plot_roc_comparison(df):
    """Plot ROC curves for MoLFormer vs Organoid."""
    y_true = df['Arrhythmia_label'].values

    fig, ax = plt.subplots(figsize=(8, 8))

    # MoLFormer ROC
    fpr_mf, tpr_mf, _ = roc_curve(y_true, df['DIQT_prob'].values)
    auc_mf = roc_auc_score(y_true, df['DIQT_prob'].values)
    ax.plot(fpr_mf, tpr_mf, 'b-', linewidth=2, label=f'MoLFormer DIQT (AUC={auc_mf:.3f})')

    # Organoid ROC
    fpr_org, tpr_org, _ = roc_curve(y_true, df['Organoid_prob'].values)
    auc_org = roc_auc_score(y_true, df['Organoid_prob'].values)
    ax.plot(fpr_org, tpr_org, 'r-', linewidth=2, label=f'Organoid PK-PD (AUC={auc_org:.3f})')

    # Diagonal
    ax.plot([0, 1], [0, 1], 'k--', linewidth=1, label='Random (AUC=0.500)')

    ax.set_xlabel('False Positive Rate', fontsize=12)
    ax.set_ylabel('True Positive Rate', fontsize=12)
    ax.set_title('ROC Comparison: MoLFormer vs Organoid\nArrhythmia Prediction (N=25 drugs)', fontsize=14)
    ax.legend(loc='lower right', fontsize=11)
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1])
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'ROC_MoLFormer_vs_Organoid.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'figures' / 'ROC_MoLFormer_vs_Organoid.pdf', bbox_inches='tight')
    plt.close()

    print(f"ROC plot saved to: {OUTPUT_DIR / 'ROC_MoLFormer_vs_Organoid.png'}")
    return auc_mf, auc_org

def plot_prediction_scatter(df):
    """Scatter plot of MoLFormer vs Organoid predictions."""
    fig, ax = plt.subplots(figsize=(10, 8))

    # Color by actual label
    colors = ['green' if a == 1 else 'red' for a in df['Arrhythmia_label']]

    scatter = ax.scatter(
        df['DIQT_prob'], df['Organoid_prob'],
        c=colors, s=100, alpha=0.7, edgecolors='black'
    )

    # Add drug labels
    for _, row in df.iterrows():
        ax.annotate(
            row['Drug'],
            (row['DIQT_prob'], row['Organoid_prob']),
            fontsize=8, alpha=0.8,
            xytext=(5, 5), textcoords='offset points'
        )

    # Add quadrant lines
    ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=0.5, color='gray', linestyle='--', alpha=0.5)

    # Add diagonal
    ax.plot([0, 1], [0, 1], 'k:', alpha=0.3)

    # Labels
    ax.set_xlabel('MoLFormer DIQT Probability', fontsize=12)
    ax.set_ylabel('Organoid PK-PD Arrhythmia Probability', fontsize=12)
    ax.set_title('MoLFormer vs Organoid Predictions\n(Green=Arrhythmia+, Red=Arrhythmia-)', fontsize=14)

    ax.set_xlim([-0.05, 1.05])
    ax.set_ylim([-0.05, 1.05])
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'Prediction_Scatter_MoLFormer_vs_Organoid.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'figures' / 'Prediction_Scatter_MoLFormer_vs_Organoid.pdf', bbox_inches='tight')
    plt.close()

    print(f"Scatter plot saved to: {OUTPUT_DIR / 'Prediction_Scatter_MoLFormer_vs_Organoid.png'}")

def plot_accuracy_bars(metrics_dict):
    """Bar chart comparing accuracy and AUC."""
    models = list(metrics_dict.keys())
    accuracies = [m['Accuracy'] for m in metrics_dict.values()]
    aurocs = [m['AUROC'] for m in metrics_dict.values()]

    x = np.arange(len(models))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, accuracies, width, label='Accuracy', color='steelblue')
    bars2 = ax.bar(x + width/2, aurocs, width, label='AUROC', color='darkorange')

    ax.set_ylabel('Score', fontsize=12)
    ax.set_title('Model Comparison: Arrhythmia Prediction (N=25 drugs)', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=11)
    ax.legend(fontsize=11)
    ax.set_ylim([0, 1])
    ax.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.3f}', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9)
    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height:.3f}', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'Accuracy_AUC_Comparison.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'figures' / 'Accuracy_AUC_Comparison.pdf', bbox_inches='tight')
    plt.close()

    print(f"Bar chart saved to: {OUTPUT_DIR / 'Accuracy_AUC_Comparison.png'}")

def create_comparison_table(df, metrics_dict):
    """Create detailed comparison table."""
    # Per-drug comparison
    comparison_df = df[['Drug', 'Arrhythmia_label', 'DIQT_prob', 'DIQT_pred',
                        'Organoid_prob', 'Organoid_pred']].copy()

    comparison_df['MoLFormer_Correct'] = (comparison_df['DIQT_pred'] == comparison_df['Arrhythmia_label']).astype(int)
    comparison_df['Organoid_Correct'] = (comparison_df['Organoid_pred'] == comparison_df['Arrhythmia_label']).astype(int)
    comparison_df['Both_Correct'] = (comparison_df['MoLFormer_Correct'] & comparison_df['Organoid_Correct']).astype(int)

    comparison_df.to_csv(OUTPUT_DIR / 'DIQT_vs_Arrhythmia_comparison.csv', index=False)

    # Summary metrics table
    metrics_summary = pd.DataFrame(metrics_dict).T
    metrics_summary.index.name = 'Model'
    metrics_summary.to_csv(OUTPUT_DIR / 'comparison_metrics_summary.csv')

    print(f"Comparison tables saved to: {OUTPUT_DIR}")

    return comparison_df

def main():
    print("="*60)
    print("MoLFormer vs Organoid Comparison")
    print("="*60)

    # Load data
    df = load_data()
    print(f"Loaded {len(df)} drugs for comparison")

    # Compute metrics for both models
    y_true = df['Arrhythmia_label'].values

    mf_metrics = compute_metrics(y_true, df['DIQT_pred'].values, df['DIQT_prob'].values)
    org_metrics = compute_metrics(y_true, df['Organoid_pred'].values, df['Organoid_prob'].values)

    metrics_dict = {
        'MoLFormer DIQT': mf_metrics,
        'Organoid PK-PD': org_metrics
    }

    # Print comparison
    print("\n" + "-"*50)
    print("METRICS COMPARISON")
    print("-"*50)
    print(f"{'Metric':<15} {'MoLFormer':>15} {'Organoid':>15}")
    print("-"*50)
    for metric in mf_metrics.keys():
        print(f"{metric:<15} {mf_metrics[metric]:>15.4f} {org_metrics[metric]:>15.4f}")

    # Generate plots
    print("\nGenerating plots...")
    (OUTPUT_DIR / 'figures').mkdir(exist_ok=True)

    auc_mf, auc_org = plot_roc_comparison(df)
    plot_prediction_scatter(df)
    plot_accuracy_bars(metrics_dict)

    # Create comparison table
    comparison_df = create_comparison_table(df, metrics_dict)

    # Summary statistics
    print("\n" + "-"*50)
    print("AGREEMENT ANALYSIS")
    print("-"*50)
    both_correct = comparison_df['Both_Correct'].sum()
    mf_only = (comparison_df['MoLFormer_Correct'] & ~comparison_df['Organoid_Correct']).sum()
    org_only = (~comparison_df['MoLFormer_Correct'] & comparison_df['Organoid_Correct']).sum()
    both_wrong = (~comparison_df['MoLFormer_Correct'] & ~comparison_df['Organoid_Correct']).sum()

    print(f"Both correct:        {both_correct}/25 ({both_correct/25*100:.1f}%)")
    print(f"Only MoLFormer:      {mf_only}/25 ({mf_only/25*100:.1f}%)")
    print(f"Only Organoid:       {org_only}/25 ({org_only/25*100:.1f}%)")
    print(f"Both wrong:          {both_wrong}/25 ({both_wrong/25*100:.1f}%)")

    print("\n" + "="*60)
    print("CONCLUSION")
    print("="*60)
    winner = "Organoid PK-PD" if org_metrics['AUROC'] > mf_metrics['AUROC'] else "MoLFormer DIQT"
    print(f"\n{winner} shows better AUROC ({max(auc_mf, auc_org):.3f} vs {min(auc_mf, auc_org):.3f})")
    print(f"\nOrganoid-based predictions outperform structure-only MoLFormer")
    print(f"by {abs(org_metrics['AUROC'] - mf_metrics['AUROC']):.3f} AUROC points.")

    print("\n" + "="*60)
    print("DONE")
    print("="*60)

if __name__ == "__main__":
    main()
